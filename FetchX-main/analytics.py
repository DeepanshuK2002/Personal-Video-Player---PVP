#!/usr/bin/env python
# coding: utf-8
"""Lightweight GA4 telemetry for the FetchX desktop app.

Sends events to Google Analytics 4 via the Measurement Protocol
(https://developers.google.com/analytics/devguides/collection/protocol/ga4).

Requirements
------------
- ``MEASUREMENT_ID``  : G-K1X0BNY3D5  (from GA4 > Admin > Data Streams)
- ``API_SECRET``      : create one at GA4 > Admin > Data Streams > your stream
                        > "Measurement Protocol API secrets".

Until ``API_SECRET`` is filled in, every send is a safe no-op (returns False)
so the app never breaks and no network call fires.

All work happens on a daemon background thread so the UI is never blocked.
A per-install anonymous client id is persisted under the user config folder so
sessions stay reasonably stable without collecting any PII.
"""

import json
import os
import sys
import threading
import time
import uuid
import urllib.request
import urllib.error

# ── Configuration ─────────────────────────────────────────────────────────────
# Measurement ID is public (safe to commit). The API secret is private and is
# NEVER stored in this repo or baked into the packaged .exe — it is read at
# runtime from a local, git-ignored file.
#
# To enable tracking, create the secret at:
#   GA4 > Admin > Data Streams > (your stream) > Measurement Protocol API secrets
# then save it (a single line, no quotes) to the local secret file below.
MEASUREMENT_ID = 'G-K1X0BNY3D5'

# Local, git-ignored file holding the private API secret (one line, raw value).
# Default: ~/.fetchx/ga_api.txt  (can be overridden with the FETCHX_GA_SECRET env var)
API_SECRET_FILES = (
    os.getenv('FETCHX_GA_SECRET'),
    os.path.join(os.path.expanduser('~'), '.fetchx', 'ga_api.txt'),
)
_ENDPOINT = ('https://www.google-analytics.com/mp/collect'
             '?measurement_id={mid}&api_secret={secret}')


def _load_api_secret():
    """Read the private API secret from the local file (never from source)."""
    for path in API_SECRET_FILES:
        if not path:
            continue
        try:
            if os.path.isfile(path):
                with open(path, 'r', encoding='utf-8') as fh:
                    val = fh.read().strip()
                    if val:
                        return val
        except Exception:
            continue
    return ''

# ── Serialised background sender ──────────────────────────────────────────────
_lock = threading.Lock()
_queue = []


def _anon_client_id():
    """Return a stable, anonymous per-install id (no PII)."""
    cfg = os.path.join(os.path.expanduser('~'), '.fetchx', 'ga_client.id')
    try:
        if os.path.isfile(cfg):
            with open(cfg, 'r', encoding='utf-8') as fh:
                val = fh.read().strip()
                if len(val) > 8:
                    return val
        val = str(uuid.uuid4())
        os.makedirs(os.path.dirname(cfg), exist_ok=True)
        with open(cfg, 'w', encoding='utf-8') as fh:
            fh.write(val)
        return val
    except Exception:
        return str(uuid.uuid4())


_CLIENT_ID = _anon_client_id()


def _user_agent():
    try:
        import platform
        return ('FetchX-Bridge/1.0 (Windows; {ver}; x64) '
                'Python/{py}').format(
                    ver=getattr(platform, 'win32_ver', lambda: ('', '', '', ''))()[0] or '10',
                    py=sys.version.split()[0])
    except Exception:
        return 'FetchX-Bridge/1.0'


def _worker():
    """Drain the queue in a background thread, one batched request at a time."""
    while True:
        batch = []
        with _lock:
            if _queue:
                batch = [q for q in _queue]
                del _queue[:]
        if not batch:
            time.sleep(1.0)
            continue
        if not (MEASUREMENT_ID and _load_api_secret()):
            # Not configured yet (no local secret file) — drop silently.
            time.sleep(5.0)
            continue
        payload = {
            'client_id': _CLIENT_ID,
            'events': batch,
        }
        url = _ENDPOINT.format(mid=MEASUREMENT_ID, secret=_load_api_secret())
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url, data=data, method='POST',
            headers={'Content-Type': 'application/json',
                     'User-Agent': _user_agent()})
        try:
            urllib.request.urlopen(req, timeout=5).read()
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            pass
        except Exception:
            pass


def track(event_name, **params):
    """Queue a GA4 event (non-blocking). Missing config => silent no-op."""
    event = {'name': event_name}
    if params:
        # GA4 only accepts string params via Measurement Protocol.
        event['params'] = {str(k): str(v)[:500] for k, v in params.items()}
    with _lock:
        _queue.append(event)
    # Lazily spawn the daemon worker on first use.
    if not getattr(track, '_started', False):
        track._started = True
        threading.Thread(target=_worker, daemon=True, name='ga-sender').start()
