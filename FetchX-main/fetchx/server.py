# -*- coding: utf-8 -*-
"""FetchX FastAPI server: browse/search via the site fetchers + downloads."""
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel

import M3U8Sites
from M3U8Sites.M3U8Crawler import MirrorsBlockedError
from M3U8Sites.SiteJableTV import JableTVBrowser
from M3U8Sites.SiteMissAV import MissAVBrowser
from M3U8Sites.SiteSupJav import SupJavBrowser
from M3U8Sites.SiteHanime1 import Hanime1Browser
from M3U8Sites.SiteHanimeTV import HanimeTVBrowser
from M3U8Sites.SiteTnaFlix import TnaFlixBrowser

from fetchx import __version__, jobs

SITES = {
    'JableTV': {'browser': JableTVBrowser,
                'home': 'https://jable.tv/'},
    'MissAV': {'browser': MissAVBrowser,
               'home': 'https://missav.ai/'},
    'SupJav': {'browser': SupJavBrowser,
               'home': 'https://supjav.com/'},
    'Hanime1': {'browser': Hanime1Browser,
                'home': 'https://hanime1.me/'},
    'HanimeTV': {'browser': HanimeTVBrowser,
                 'home': 'https://hanime.tv/'},
    'TnaFlix': {'browser': TnaFlixBrowser,
                'home': 'https://www.tnaflix.com/'},
}

WEB_DIR = os.path.join(os.path.dirname(__file__), 'web')

app = FastAPI(title='FetchX', version=__version__,
              docs_url='/api/docs', openapi_url='/api/openapi.json')


class DownloadRequest(BaseModel):
    url: str


def _browser(site_key: str):
    info = SITES.get(site_key)
    if not info:
        raise HTTPException(404, f'unknown site: {site_key}')
    return info['browser'], info['home']


@app.get('/api/health')
def health():
    return {'ok': True, 'version': __version__}


@app.get('/api/sites')
def sites():
    out = []
    for key, info in SITES.items():
        b = info['browser']
        out.append({
            'key': key,
            'search': hasattr(b, 'search'),
            'categories': hasattr(b, 'fetch_categories'),
        })
    return {'sites': out}


def _clean(videos):
    out = []
    for v in videos or []:
        if not isinstance(v, dict) or not v.get('url'):
            continue
        out.append({
            'url': v.get('url', ''),
            'title': v.get('title') or '',
            'thumbnail': v.get('thumbnail') or '',
            'duration': v.get('duration') or '',
        })
    return out


@app.get('/api/browse')
def browse(site: str = Query(...), url: str = Query(''),
           page: int = Query(1, ge=1, le=500)):
    browser, home = _browser(site)
    target = url or home
    if page > 1 and not url:
        pager = getattr(browser, 'page_url', None)
        if pager:
            try:
                target = pager(home, page)
            except Exception:
                target = home
    try:
        videos = browser.fetch_page(target)
    except MirrorsBlockedError:
        raise HTTPException(502, 'all mirrors blocked — try again later')
    except Exception as exc:
        raise HTTPException(502, f'browse failed: {exc}'[:200])
    return {'site': site, 'url': target, 'page': page,
            'videos': _clean(videos)}


@app.get('/api/search')
def search(site: str = Query(...), q: str = Query(..., min_length=1)):
    browser, _ = _browser(site)
    if not hasattr(browser, 'search'):
        raise HTTPException(400, f'{site} has no search support')
    try:
        videos = browser.search(q)
    except MirrorsBlockedError:
        raise HTTPException(502, 'all mirrors blocked — try again later')
    except Exception as exc:
        raise HTTPException(502, f'search failed: {exc}'[:200])
    return {'site': site, 'query': q, 'videos': _clean(videos)}


@app.post('/api/downloads')
def start_download(req: DownloadRequest):
    url = req.url.strip()
    if not M3U8Sites.M3U8Crawler or not url.lower().startswith(('http://', 'https://')):
        raise HTTPException(400, 'a valid http(s) video URL is required')
    job = jobs.create(url)
    if not job:
        raise HTTPException(500, 'failed to queue download')
    return job


@app.get('/api/downloads')
def list_downloads():
    return {'jobs': jobs.list_all()}


@app.get('/api/downloads/{job_id}')
def get_download(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, 'no such job')
    return job


class WatchLaterRequest(BaseModel):
    url: str
    title: str = ''
    thumbnail: str = ''
    duration: str = ''
    site_name: str = ''


@app.get('/api/watch_later')
def get_watch_later():
    import config
    return {'videos': config.get_saved_videos()}


@app.post('/api/watch_later')
def add_watch_later(req: WatchLaterRequest):
    import config
    ok = config.add_saved_video(req.dict())
    return {'ok': ok, 'videos': config.get_saved_videos()}


@app.delete('/api/watch_later')
def delete_watch_later(url: str = Query(...)):
    import config
    ok = config.remove_saved_video(url)
    return {'ok': ok, 'videos': config.get_saved_videos()}


@app.get('/api/announcements')
def get_announcements():
    import config, requests
    url = config.get_remote_announcements_url()
    cached = config.get_cached_announcements().get('payload') or {}
    if not config.get_announcements_enabled() or not url:
        return {'enabled': False, 'announcements': []}
    try:
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            data = resp.json()
            config.save_cached_announcements(data)
            return data
    except Exception:
        pass
    return cached or {'enabled': False, 'announcements': []}


@app.get('/')
def index():
    return FileResponse(os.path.join(WEB_DIR, 'index.html'))
