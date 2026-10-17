#!/usr/bin/env python
# coding: utf-8
"""beeg.com downloader adapter.

Pipeline (verified 2026-08):
  1. Video URL looks like https://beeg.com/-<id>  (id may have leading zeros).
     File key = numeric id with leading '-'/'0' stripped.
  2. GET https://store.externulls.com/facts/file/<key>   (Referer/Origin beeg.com)
     -> file.data[0].cd_value = title, file.fl_duration = seconds,
        file.hls_resources.fl_cdn_multi = signed master-playlist URI.
  3. Master playlist: https://video.externulls.com/<fl_cdn_multi>
     (_TPL_ is left as-is; the server returns a real master playlist with
      per-resolution variants). All requests need Origin: https://beeg.com.
"""

import re

import config
from M3U8Sites.M3U8Crawler import M3U8Crawler, _http_get

BEEG_HOME = 'https://beeg.com/'
_STORE = 'https://store.externulls.com/facts/file/'
_VIDEO_HOST = 'https://video.externulls.com/'

_BEEG_HEADERS = {
    'Origin': 'https://beeg.com',
    'Referer': BEEG_HOME,
}


class SiteBeeg(M3U8Crawler):
    """Download adapter for beeg.com video pages (HLS via externulls store)."""
    website_pattern = r'https?://(?:www\.)?beeg\.\w+/video/.*|https?://(?:www\.)?beeg\.\w+/-\d+'
    website_dirname_pattern = r'/(-?\d+)'

    def __init__(self, url, savepath="", silence=False, max_workers=None):
        # Signed stream URIs carry limit=3; high parallelism gets segments
        # rejected, leaving the job "incomplete". Keep it low.
        super().__init__(url, savepath=savepath, silence=silence,
                         max_workers=2)

    @classmethod
    def validate_url(cls, url):
        if not url:
            return None
        url = str(url).strip()
        m = re.match(r'^https?://(?:www\.)?beeg\.[a-z.]+/(?:video/)?-?(\d+)',
                     url, re.I)
        if not m:
            return None
        # Store API key: strip leading zeros/dash exactly like the site's player.
        return m.group(1).lstrip('0') or '0'

    def is_url_vaildate(self):
        return bool(self._m3u8url)

    def _create_m3u8(self):
        super()._create_m3u8()
        ts_list = getattr(self, '_tsList', None)
        if not ts_list:
            return
        # The variant playlist lists its first couple of segments on the
        # externulls origin, where they 404 ("No such file"). The very same
        # files exist under the signed ahcdn.com base used by the other
        # segments - rewrite those entries onto the CDN.
        cdn_base = None
        for u in ts_list:
            if isinstance(u, str) and u.startswith('http') \
                    and '.ahcdn.com/' in u:
                cdn_base = u.rsplit('/', 1)[0]
                break
        if not cdn_base:
            return
        fixed = False
        out = []
        for u in ts_list:
            if isinstance(u, str) and (not u.startswith('http')
                                       or 'externulls.com/' in u):
                out.append(cdn_base + '/' + u.rsplit('/', 1)[-1])
                fixed = True
            else:
                out.append(u)
        if fixed:
            self._tsList = out

    def get_url_infos(self):
        self._m3u8url = None
        key = self._dirName
        resp = _http_get(
            _STORE + key,
            {**_BEEG_HEADERS,
             'Accept': 'application/json, text/plain, */*',
             'User-Agent': config.headers['User-Agent']},
            timeout=25,
        )
        if getattr(resp, 'status_code', 0) != 200:
            raise Exception(
                f'beeg API request failed (HTTP {resp.status_code}) for id {key}')
        try:
            data = resp.json()
        except Exception:
            raise Exception('beeg API returned invalid JSON '
                            f'for id {key} (video removed?)')
        file_data = data.get('file') or {}
        records = file_data.get('data') or []
        hls_uri = ((file_data.get('hls_resources') or {}).get('fl_cdn_multi'))
        title = ''
        for rec in records:
            val = (rec.get('cd_value') or '').strip()
            if val:
                title = str(val)
                break
        duration = file_data.get('fl_duration')
        if not hls_uri:
            raise Exception(f'beeg video has no HLS stream available (id {key})')

        self._targetName = title or f'beeg_{key}'
        self._imageUrl = None
        try:
            self._duration = int(duration)
        except (TypeError, ValueError):
            self._duration = None
        self._m3u8url = _VIDEO_HOST + hls_uri.lstrip('/')
        self._extra_headers = dict(_BEEG_HEADERS)

    def _m3u8_headers(self):
        return {
            **config.headers,
            **(getattr(self, '_extra_headers', None) or _BEEG_HEADERS),
        }

    def apply_quality(self, preference=None):
        pass

    def stream_links(self):
        if not self._m3u8url:
            return {}
        return {'HLS master': self._m3u8url}


class BeegBrowser:
    """Browse adapter for beeg.com via the externulls store API.

    Listing:  GET https://store.externulls.com/tag/videos/<slug>?limit=&offset=
              -> JSON array of units; unit.file.id is the video id, title in
              unit.file.data[0].cd_value, duration fl_duration (seconds).
    Thumbs:   https://thumbs.externulls.com/videos/<fileId>/<n>.webp?w=320
    Search exists only over WebSocket - not used here.
    """

    STORE = 'https://store.externulls.com'
    THUMBS = 'https://thumbs.externulls.com'
    LIMIT = 24

    CATEGORIES = (
        ('Teen', 'teen'), ('Anal', 'anal'), ('MILF', 'milf'),
        ('Asian', 'asian'), ('Big Tits', 'bigtits'), ('Big Ass', 'bigass'),
        ('Blonde', 'blonde'), ('Brunette', 'brunette'),
        ('Latina', 'latina'), ('Ebony', 'ebony'),
        ('Lesbian', 'lesbian'), ('Amateur', 'amateur'),
        ('HD', 'hd'), ('Creampie', 'creampie'),
        ('Blowjob', 'bj'), ('Cumshot', 'cumshot'),
        ('Interracial', 'interracial'), ('Mature', 'mature'),
        ('Redhead', 'redhead'), ('Solo', 'solo'),
        ('Threesome', 'threesome'), ('POV', 'pov'),
    )

    def __init__(self):
        import requests
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': config.headers['User-Agent'],
            'Accept': 'application/json',
            **_BEEG_HEADERS,
        })

    @staticmethod
    def page_url(base_slug_or_url, page):
        """Virtual listing URL for a tag slug at 1-based `page`."""
        slug = str(base_slug_or_url).rstrip('/')
        slug = slug.rsplit('/', 1)[-1].lower()
        offset = (max(int(page), 1) - 1) * BeegBrowser.LIMIT
        return f'{BeegBrowser.STORE}/tag/videos/{slug}?limit={BeegBrowser.LIMIT}&offset={offset}'

    def fetch_page(self, url):
        try:
            resp = self._session.get(url, timeout=12)
        except Exception:
            return []
        if resp.status_code != 200:
            return []
        try:
            units = resp.json()
        except Exception:
            return []
        out = []
        for unit in units or []:
            f = (unit or {}).get('file') or {}
            fid = f.get('id')
            if not fid:
                continue
            records = f.get('data') or []
            title = ''
            for rec in records:
                val = str((rec or {}).get('cd_value') or '').strip()
                if val:
                    title = val
                    break
            try:
                secs = int(f.get('fl_duration') or 0)
            except (TypeError, ValueError):
                secs = 0
            duration = f'{secs // 60}:{secs % 60:02d}' if secs else ''
            qualities = (f.get('qualities') or {}).get('h264') or []
            max_q = max([q.get('quality') or 0 for q in qualities] or [0])
            out.append({
                'url': f'https://beeg.com/-{fid}',
                'title': title or f'beeg_{fid}',
                'duration': duration,
                'thumbnail': f'{self.THUMBS}/videos/{fid}/0.webp?w=320',
                'site_name': 'Beeg',
                'is_4k': False,
                'is_hd': bool(max_q and max_q >= 720),
            })
        return out
