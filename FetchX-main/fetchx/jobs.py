# -*- coding: utf-8 -*-
"""Background download job registry for FetchX.

Each job wraps one M3U8Sites crawler run in a worker thread from a small
pool, exposing live progress (segments done / total + speed) to the API.
"""
import os
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import M3U8Sites

_lock = threading.Lock()
_jobs = {}
_pool = None


def download_dir() -> str:
    d = os.environ.get('FETCHX_DOWNLOAD_DIR') or os.path.join(
        os.getcwd(), 'downloads')
    os.makedirs(d, exist_ok=True)
    return d


def concurrency() -> int:
    try:
        return max(1, int(os.environ.get('FETCHX_CONCURRENCY', '2')))
    except ValueError:
        return 2


def _pool_get() -> ThreadPoolExecutor:
    global _pool
    if _pool is None:
        _pool = ThreadPoolExecutor(max_workers=concurrency(),
                                   thread_name_prefix='fetchx-dl')
    return _pool


def snapshot(job: dict) -> dict:
    with _lock:
        return dict(job)


def create(url: str) -> dict:
    job = {
        'id': uuid.uuid4().hex[:12],
        'url': url,
        'name': '',
        'status': 'queued',
        'progress': -1,
        'speed': 0,
        'error': '',
        'file_path': '',
        'created_at': time.time(),
        'finished_at': 0,
    }
    with _lock:
        _jobs[job['id']] = job
    _pool_get().submit(_run, job)
    return snapshot(job)


def _set(job: dict, **kw):
    with _lock:
        job.update(kw)


def _run(job: dict):
    try:
        res = os.environ.get('RESOLUTION')
        if res:
            try:
                M3U8Sites.M3U8Crawler.set_resolution_pref(res)
            except Exception:
                pass
        site = M3U8Sites.CreateSite(job['url'], download_dir())
        if site is None:
            raise ValueError('unsupported URL (no fetcher matches this host)')
        if not site.is_url_vaildate():
            raise ValueError('could not resolve video '
                             '(layout change / Cloudflare / removed)')
        name = ''
        try:
            name = site.target_name() or ''
        except Exception:
            pass
        _set(job, status='downloading', name=name)

        def _progress(done, total, speed):
            pct = int(done * 100 / total) if total else -1
            _set(job, progress=pct, speed=int(speed or 0))

        try:
            site._progress_callback = _progress
        except Exception:
            pass

        site.start_download()
        path = ''
        try:
            path = os.path.join(download_dir(), site.target_name())
        except Exception:
            pass
        _set(job, status='done', progress=100, speed=0,
             file_path=path if os.path.exists(path) else '', finished_at=time.time())
    except Exception as exc:
        _set(job, status='error', error=str(exc)[:300], speed=0,
             finished_at=time.time())


def get(job_id: str):
    with _lock:
        job = _jobs.get(job_id)
    return snapshot(job) if job else None


def list_all(limit: int = 100):
    with _lock:
        items = sorted(_jobs.values(),
                       key=lambda j: j['created_at'], reverse=True)
        return [dict(j) for j in items[:limit]]
