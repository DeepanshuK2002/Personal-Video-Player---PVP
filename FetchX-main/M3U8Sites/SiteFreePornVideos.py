#!/usr/bin/env python
# coding: utf-8
"""KVS-engine sites (freepornvideos.xxx / 1porn.tv) - direct MP4 + browse.

Both sites run the same KVS template:
  * video pages embed signed ``get_file/.../<id>_<h>m.mp4/`` links
    (heights 2160m/720m/480m); the trailing slash is REQUIRED.
  * listings are ``<div class="item">`` cards; pagination appends
    ``/{page}/`` (also with trailing slash).
  * /tags/, /models/ and studio (/sites/) pages share one markup family,
    so a single parser set serves both domains.

The download adapter extends SiteSupJav, reusing its direct-MP4 engine
(parallel HTTP ranges with serial fallback). The browser adapter powers
the GUI's home feed, sidebar and unified tag listings.
"""

import html
import re
import threading
import time
from urllib.parse import quote, urljoin

import requests

from M3U8Sites.M3U8Crawler import request_headers, get_resolution_pref
from M3U8Sites.SiteSupJav import SiteSupJav

FPV_ROOT = 'https://www.freepornvideos.xxx'
FPV_HOME = FPV_ROOT + '/'
FPV_HOST = 'www.freepornvideos.xxx'


_GET_FILE_RE_CACHE = {}
_CLEAN_RE1 = re.compile(r'\s*\|\s*Free\s*Porn.*$', re.I)
_CLEAN_RE2 = re.compile(r'\s*[-\u2013]\s*Free\s*Porn\s*Videos.*$', re.I)
_OG_TITLE_RE = re.compile(r'<meta[^>]+property="og:title"[^>]+content="([^"]*)"', re.I)
_TITLE_TAG_RE = re.compile(r'<title>(.*?)</title>', re.I | re.S)
_HM_RE = re.compile(r'_(\d{3,4})m\.mp4/')


def make_get_file_re(host):
    """Regex matching signed KVS get_file MP4 URLs for `host`."""
    cached = _GET_FILE_RE_CACHE.get(host)
    if cached is None:
        cached = re.compile(
            r'https?://(?:www\.)?' + re.escape(host.replace('www.', '')) +
            r'/get_file/[^\'"\s<>\\]+', re.I)
        _GET_FILE_RE_CACHE[host] = cached
    return cached


def _clean(title):
    """Strip KVS page-title chrome ('| Free Porn' etc)."""
    title = html.unescape(str(title or '')).strip()
    title = _CLEAN_RE1.sub('', title)
    title = _CLEAN_RE2.sub('', title)
    return title.strip()


def parse_video_page(page_html, host):
    """Extract {title, sources:[{url,height},...]} from a KVS video page."""
    m = _OG_TITLE_RE.search(page_html)
    if not m:
        m = _TITLE_TAG_RE.search(page_html)
    title = _clean(m.group(1)) if m else ''

    sources = {}
    for match in make_get_file_re(host).finditer(page_html):
        url = html.unescape(match.group(0))
        base = url.split('?', 1)[0].split('#', 1)[0]
        if not base.endswith('/'):
            base += '/'
        hm = _HM_RE.search(base)
        if not hm:
            continue
        height = int(hm.group(1))
        if height not in sources:      # first signed link per quality wins
            sources[height] = {'url': base, 'height': height}
    if not sources:
        return None
    ordered = [sources[h] for h in sorted(sources, reverse=True)]
    return {'title': title, 'sources': ordered}


def select_source(sources, pref='highest'):
    """Pick one source honouring the global resolution preference."""
    if not sources:
        return None
    heights = sorted((s['height'] for s in sources), reverse=True)

    def pick(cands):
        for s in sources:
            if s['height'] == cands[0]:
                return s
        return None

    if pref == 'lowest':
        return next(s for s in sources if s['height'] == heights[-1])
    if pref in ('1080', '720', '480'):
        cap = int(pref)
        fitting = [h for h in heights if h <= cap]
        target = fitting[0] if fitting else heights[-1]
        return next(s for s in sources if s['height'] == target)
    # 'highest' (and anything else) -> best available
    return next(s for s in sources if s['height'] == heights[0])


_CARD_BLOCK_RE = re.compile(r'<div class="item">.*?</div>\s*</a>', re.S)
_URL_FULL_RE = re.compile(r'<a[^>]+href="(https?://[^"]*/videos/[^"]+)"')
_URL_REL_RE = re.compile(r'<a[^>]+href="(/videos/[^"]+)"')
_TITLE_THUMB_RE = re.compile(r'class="thumb_img"[^>]*title="([^"]*)"')
_TITLE_A_RE = re.compile(r'<a[^>]+title="([^"]*)"')
_IMG_DATA_RE = re.compile(r'data-(?:src|original)="([^"]+)"')
_IMG_SRC_RE = re.compile(r'<img[^>]+src="([^"]+)"')
_DUR_CLASS_RE = re.compile(r'class="duration"[^>]*>(?:Full\s*Video\s*)?(\d{1,2}:\d{2}(?::\d{2})?)')
_DUR_END_RE = re.compile(r'\b(\d{1,2}:\d{2}(?::\d{2})?)\s*$')


def parse_cards(html_text, listing_url='', host=FPV_HOST,
                site_label='FreePornVideos'):
    """Parse a KVS listing page into video-card dicts."""
    out = []
    seen = set()
    for block in _CARD_BLOCK_RE.findall(html_text):
        m_url = _URL_FULL_RE.search(block)
        if not m_url:
            m_url = _URL_REL_RE.search(block)
        if not m_url:
            continue
        video_url = html.unescape(m_url.group(1))
        if not video_url.startswith('http'):
            video_url = urljoin(f'https://{host}/', video_url)
        if not video_url.endswith('/'):
            video_url += '/'
        if video_url in seen:
            continue
        seen.add(video_url)

        m_title = _TITLE_THUMB_RE.search(block) or _TITLE_A_RE.search(block)
        title = _clean(m_title.group(1)) if m_title else ''

        m_img = _IMG_DATA_RE.search(block) or _IMG_SRC_RE.search(block)
        thumbnail = html.unescape(m_img.group(1)) if m_img else ''

        duration = ''
        m_dur = _DUR_CLASS_RE.search(block)
        if m_dur:
            duration = m_dur.group(1)
        else:
            m_dur = _DUR_END_RE.search(block)
            if m_dur:
                duration = m_dur.group(1)

        out.append({
            'url': video_url,
            'title': title or 'Video',
            'thumbnail': thumbnail,
            'duration': duration,
            'site_name': site_label,
            'is_hd': True,
        })
    return out


_browser_local = threading.local()


def _make_session(host=None):
    session = requests.Session()
    headers = {
        'User-Agent': request_headers.get(
            'User-Agent',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
            '(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36',
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
    if host:
        headers['Referer'] = f'https://{host}/'
    session.headers.update(headers)
    return session


def _request(session, url):
    return session.get(url, timeout=12)


class KvsDirectSite(SiteSupJav):
    """Direct-MP4 download adapter shared by both KVS sites.

    Subclasses set `_ROOT`/`_HOST` plus the URL patterns. Resolution
    selection, signed-link parsing and the parallel-range downloader all
    come from here / SiteSupJav.
    """
    _ROOT = FPV_ROOT
    _HOST = FPV_HOST
    _direct_url = None

    @classmethod
    def validate_url(cls, url):
        if not url:
            return None
        url = str(url).strip()
        if not re.match(cls.website_pattern, url, re.I):
            return None
        m = re.search(cls.website_dirname_pattern, url)
        if not m:
            return None
        slug = m.group(1).rstrip('/')
        return slug or None

    def stream_links(self):
        """All resolved stream links as {label: url} (signed, time-limited)."""
        out = {}
        for src in getattr(self, '_sources', []) or []:
            h = src.get('height')
            out[f'{h}p' if h else 'mp4'] = src['url']
        if getattr(self, '_direct_url', None) and not out:
            out['mp4'] = self._direct_url
        return out

    def get_url_infos(self):
        self._direct_url = None
        self._direct_referer = None
        self._m3u8url = None

        session = _make_session(self._HOST)
        try:
            response = _request(session, self._url)
            if response.status_code != 200:
                raise Exception(
                    f'page read failed (HTTP {response.status_code})')
            parsed = parse_video_page(response.text, self._HOST)
            if not parsed:
                raise Exception(
                    'no available MP4 download sources on this video')

            selected = select_source(parsed['sources'], get_resolution_pref())
            if not selected:
                raise Exception(
                    'no available MP4 download sources on this video')

            self._targetName = _clean(parsed['title']) or 'Video'
            image_url = ''
            og_img = re.search(
                r'<meta[^>]+property="og:image"[^>]+content="([^"]+)"',
                response.text)
            if og_img:
                image_url = html.unescape(og_img.group(1))
            self._imageUrl = image_url or None
            self._duration = None
            self._sources = parsed['sources']
            self._direct_url = selected['url']
            self._direct_referer = self._url
            self._extra_headers = {'Referer': self._url}
        finally:
            try:
                session.close()
            except Exception:
                pass


class KvsBrowser:
    """Browse/search/tags/models/channels adapter for KVS-style sites."""

    ROOT = FPV_ROOT
    HOST = FPV_HOST
    SITE_LABEL = 'FreePornVideos'

    HOMEPAGE_SECTIONS = (
        ('Trending', f'{FPV_ROOT}/most-popular/week/'),
        ('Latest Updates', f'{FPV_ROOT}/latest-updates/'),
        ('Most Popular', f'{FPV_ROOT}/most-popular/month/'),
    )

    CATEGORIES = ()

    # The sites publish one mixed /models/ directory (no /actors/ page, no
    # gender metadata).  This index of established male performers is
    # intersected with that directory to build the Actors tab.
    MALE_ACTORS = frozenset("""
johnny-sins manuel-ferrara mick-blue james-deen danny-d danny-mountain
keiran-lee jordan-ash xander-corvus ricky-johnson jason-luv prince-yahshua
jax-slayher isiah-maxwell rob-piper dredd jovan-jordan nat-turnher
mike-adriano mark-wood steve-holmes ian-scott david-perry jean-val-jean
randy-spears tommy-gunn erik-everhard toni-ribas ramon-nomar markus-dupree
scott-nails charles-dera tyler-nixon ryan-driller seth-gamble lucas-frost
justin-hunt alex-mack will-pounder rion-king ryan-mclane logan-long
kyle-mason damon-dice brad-newman christian-clay dan-damage evan-stone
enzo-east vince-karter freddy-gong darrell-deeps dean-van-damme peter-green
nick-manning marco-banderas rocco-siffredi nacho-vidal eric-masterson
billy-glide ron-jeremy peter-north codey-steele quinton-james ricky-spanish
small-hands tommy-pistol owen-gray danny-wylde dane-cross chris-strokes
j-mac johnny-castle karlo-karrera jonathan-jordan donnie-rock jay-bangher
ricky-larkin barry-scott scott-lyons dillon-diaz axel-haze
""".split())

    # Curated male actors force-listed even when they don't surface on the
    # harvested listing pages; their canonical /models/<slug>/ page is used.
    PINNED_ACTORS = ('johnny-sins',)

    @staticmethod
    def _slugify(name):
        return re.sub(r'[^a-z0-9]+', '-', str(name).lower()).strip('-')

    @classmethod
    def _get_session(cls):
        session = getattr(_browser_local, 'session', None)
        if session is None:
            session = _make_session(cls.HOST)
            _browser_local.session = session
        return session

    @classmethod
    def _fetch(cls, url):
        response = None
        for attempt in (0, 1):
            response = _request(cls._get_session(), url)
            if response.status_code == 200:
                return response.text
            if attempt == 0 and response.status_code in (429, 502, 503):
                # WAF/rate-limit blips: back off briefly and retry once
                time.sleep(0.8)
                continue
            break
        raise Exception(f'request failed (HTTP {response.status_code}) '
                        f'for {url}')

    @staticmethod
    def page_url(base_url, page):
        """Listing URL at 1-based `page` (KVS appends /{page}/, slash required)."""
        base = str(base_url).rstrip('/')
        page = max(int(page), 1)
        return f'{base}/{page}/' if page > 1 else f'{base}/'

    @classmethod
    def search_url(cls, query):
        clean_q = re.sub(r'[^a-zA-Z0-9\s]+', ' ', str(query).strip().lower())
        slug = '-'.join(clean_q.split())
        return f'{cls.ROOT}/search/{slug}/' if slug else f'{cls.ROOT}/latest-updates/'

    @classmethod
    def fetch_page(cls, listing_url, verify_name=None):
        try:
            raw = cls._fetch(listing_url)
        except Exception:
            return []
        if verify_name and not cls.page_mentions(raw, verify_name):
            return []
        return parse_cards(raw, listing_url, cls.HOST, cls.SITE_LABEL)

    @classmethod
    def page_mentions(cls, html_text, name):
        """True if a listing page actually belongs to entity `name`.

        KVS serves generic/broad pages (latest-updates, model indexes, etc.)
        when a requested listing slug doesn't resolve to a real entity.  We
        compare the page's own heading/title against the expected entity so
        the Watchlist never shows a page of videos unrelated to a starred
        item.
        """
        if not name:
            return True
        identity = ''
        h1 = re.search(r'<h1[^>]*>(.*?)</h1>', html_text, re.S | re.I)
        if h1:
            identity += re.sub(r'<[^>]+>', ' ', h1.group(1))
        t = _OG_TITLE_RE.search(html_text)
        if t:
            identity += ' ' + t.group(1)

        def _norm(s):
            return re.sub(r'[^a-z0-9]+', '', (s or '').lower())

        i = _norm(identity)
        n = _norm(name)
        return bool(n) and (n in i or i in n)

    # ---------- single-video metadata ----------
    @classmethod
    def _first_meta(cls, text, pattern):
        """content= of the first <meta> whose attrs match `pattern`."""
        for mt in re.finditer(r'<meta\b[^>]*>', text, re.I):
            tag = mt.group(0)
            if re.search(pattern, tag, re.I):
                mc = re.search(r'content="([^"]*)"', tag, re.I)
                if mc:
                    return html.unescape(mc.group(1))
        return ''

    @classmethod
    def fetch_video_info(cls, url):
        """Video page -> {'models', 'actors', 'tags', 'studio'} for the player page."""
        text = cls._fetch(url)

        models, actors, seen_m = [], [], set()

        # Scope video details section to avoid pulling models/tags from unrelated carousels/footers
        details_m = re.search(
            r'<div[^>]+class="[^"]*(?:block-details|video-info)[^"]*"[^>]*>(.*?)(?:<div class="list-videos"|<div class="main"|id="list_videos"|<footer|$)',
            text, re.S | re.I)
        scope_text = details_m.group(1) if details_m else text

        # 1. Models & Cast chips
        for m in re.finditer(r'<a\b([^>]*)>(.*?)</a>', scope_text, re.S | re.I):
            attrs, inner = m.groups()
            href_m = re.search(r'href=["\']([^"\']+)["\']', attrs, re.I)
            if not href_m:
                continue
            href = href_m.group(1)
            if '/models/' in href or 'btn_model' in attrs or 'thumb_model' in attrs:
                m_slug = re.search(r'/models/([a-z0-9-]+)/?$', href.split('?')[0], re.I)
                if not m_slug or m_slug.group(1) in ('models', 'all', 'top', 'latest-updates', 'most-popular'):
                    continue
                label = _clean(re.sub(r'<[^>]+>', ' ', inner))
                if not label:
                    continue
                u = html.unescape(href)
                if not u.startswith('http'):
                    u = urljoin(f'https://{cls.HOST}/', u)
                slug = cls._slugify(label) or m_slug.group(1)
                if not slug or slug in seen_m:
                    continue
                seen_m.add(slug)
                entry = {'name': label, 'url': u}
                if slug in cls.MALE_ACTORS:
                    actors.append(entry)
                else:
                    models.append(entry)

        # 2. Fallback to description / LD-JSON if no models or actors found in markup
        if not models and not actors:
            desc = cls._first_meta(text, r'name="description"') \
                or cls._first_meta(text, r'property="og:description"')
            ms = re.search(r'\b(?:Starring|Featuring|Watch)\b[:\s]+([^."]+?)(?:\s+in|\s*\.|$)',
                           desc, re.I)
            if ms:
                for name in re.split(r'\s*(?:,|\band\b)\s*', ms.group(1)):
                    name = _clean(name)
                    slug = cls._slugify(name)
                    if not name or not slug or slug in seen_m:
                        continue
                    seen_m.add(slug)
                    entry = {'name': name, 'url': f'{cls.ROOT}/models/{slug}/'}
                    if slug in cls.MALE_ACTORS:
                        actors.append(entry)
                    else:
                        models.append(entry)

        # 3. Tags: category / tag chips
        tags, seen_t = [], set()
        for m in re.finditer(r'<a\b([^>]*)>(.*?)</a>', scope_text, re.S | re.I):
            attrs, inner = m.groups()
            href_m = re.search(r'href=["\']([^"\']+)["\']', attrs, re.I)
            if not href_m:
                continue
            href = href_m.group(1)
            if '/categories/' in href or '/tags/' in href or 'btn_tag' in attrs:
                cat_slug = re.search(r'/(?:categories|tags)/([a-z0-9-]+)/?$', href.split('?')[0], re.I)
                if not cat_slug or cat_slug.group(1) in ('tags', 'categories', 'all'):
                    continue
                label = _clean(re.sub(r'<[^>]+>', ' ', inner))
                if not label:
                    continue
                u = html.unescape(href)
                if not u.startswith('http'):
                    u = urljoin(f'https://{cls.HOST}/', u)
                key = u.rstrip('/')
                if key in seen_t:
                    continue
                seen_t.add(key)
                tags.append({'name': label, 'url': u})

        # 4. Studio: sponsor / channel link or LD-JSON
        studio = None
        for m in re.finditer(r'<a\b([^>]*)>(.*?)</a>', scope_text, re.S | re.I):
            attrs, inner = m.groups()
            href_m = re.search(r'href=["\']([^"\']+)["\']', attrs, re.I)
            if not href_m:
                continue
            href = href_m.group(1)
            if '/sites/' in href or 'btn_sponsor' in attrs:
                s_slug = re.search(r'/sites/([a-z0-9-]+)/?$', href.split('?')[0], re.I)
                if not s_slug or s_slug.group(1) in ('sites', 'all'):
                    continue
                s_name = _clean(re.sub(r'<[^>]+>', ' ', inner))
                s_url = html.unescape(href)
                if not s_url.startswith('http'):
                    s_url = urljoin(f'https://{cls.HOST}/', s_url)
                if s_name:
                    studio = {'name': s_name, 'url': s_url}
                    break

        if studio is None:
            m_ld = re.search(r'"@type":\s*"VideoObject"[^{}]{0,600}?'
                             r'"name":\s*"([^"]*)"', text, re.S)
            prefix = m_ld.group(1).split(' - ')[0].strip() if m_ld else ''
            if prefix and prefix.lower() not in ('video', 'movie', 'porn'):
                studio = {'name': prefix,
                          'url': f'{cls.ROOT}/sites/{cls._slugify(prefix)}/'}

        # 5. Description
        desc = cls._first_meta(text, r'name="description"') \
            or cls._first_meta(text, r'property="og:description"')
        desc = _clean(desc)
        desc = re.sub(r'\s*\|\s*Free Porn Videos.*$', '', desc, flags=re.I).strip()

        return {
            'models': models[:8],
            'actors': actors[:8],
            'tags': tags[:24],
            'studio': studio,
            'description': desc,
        }

    @classmethod
    def fetch_model_thumb(cls, model_url):
        """Fetches the avatar image URL for a given model page URL."""
        if not model_url:
            return ''
        try:
            mtext = cls._fetch(model_url)
            # 1. Look for explicit model avatar image path
            m = re.search(r'https?://[^\s"\'<>]+/contents/models/\d+/[^\s"\'<>]+\.jpg', mtext)
            if m:
                return m.group(0)
            # 2. Look for img tag with model class or alt
            m2 = re.search(r'<img[^>]+(?:class="[^"]*model[^"]*"|alt="[^"]*")[^>]+(?:src|data-original|data-src)="([^"]+)"', mtext, re.I)
            if m2:
                u = html.unescape(m2.group(1))
                if not u.startswith('http'):
                    u = urljoin(f'https://{cls.HOST}/', u)
                return u
            # 3. Fallback: first video thumbnail on model page
            m3 = re.search(r'<img[^>]+class="[^"]*thumb[^"]*"[^>]+(?:src|data-original|data-src)="([^"]+)"', mtext, re.I)
            if m3:
                u = html.unescape(m3.group(1))
                if not u.startswith('http'):
                    u = urljoin(f'https://{cls.HOST}/', u)
                return u
        except Exception:
            pass
        return ''


    # ---------- directory pages ----------
    @classmethod
    def fetch_tags(cls):
        """Tag index -> [{'name','url','count'}] (alphabetical by site)."""
        text = cls._fetch(f'{cls.ROOT}/tags/')
        rows, seen = [], set()
        pat = re.compile(
            r'<a[^>]+href="(https?://[^"]*/tags/[^"]+|/tags/[^"]+)"[^>]*>'
            r'(.*?)</a>', re.S | re.I)
        for href, inner in pat.findall(text):
            label = re.sub(r'<[^>]+>', '', inner)
            label = _clean(label)
            url = html.unescape(href)
            if not url.startswith('http'):
                url = urljoin(f'https://{cls.HOST}/', url)
            key = url.rstrip('/')
            if not label or key in seen:
                continue
            seen.add(key)
            rows.append({'name': label, 'url': url, 'count': 0})
        return rows

    @classmethod
    def fetch_models(cls, max_pages=5):
        """Model directory -> [{'name','url','thumb','count'}] by video count."""
        rows, seen = [], set()
        for page in range(1, max_pages + 1):
            try:
                text = cls._fetch(cls.page_url(f'{cls.ROOT}/models/', page))
            except Exception:
                break
            found = 0
            for m in re.finditer(
                    r'<a class="item"[^>]+href="([^"]+/models/[^"]+)"'
                    r'[^>]*title="([^"]*)"(.*?)(?=<a class="item"|$)',
                    text, re.S):
                href, title, block = m.groups()
                url = html.unescape(href)
                if not url.startswith('http'):
                    url = urljoin(f'https://{cls.HOST}/', url)
                key = url.rstrip('/')
                if key in seen:
                    continue
                seen.add(key)
                thumb = ''
                mt = re.search(r'data-(?:original|src)="([^"]+)"', block)
                if mt:
                    thumb = html.unescape(mt.group(1))
                count = 0
                mc = re.search(r'class="videos">\s*([\d,]+)', block)
                if mc:
                    count = int(mc.group(1).replace(',', ''))
                name = _clean(title)
                if name:
                    rows.append({'name': name, 'url': url,
                                 'thumb': thumb, 'count': count})
                found += 1
            if found < 20:      # last (partial) page
                break
        return rows

    @classmethod
    def fetch_channels(cls, max_pages=3):
        """Harvest studio (/sites/) links from /sites/ index & listing seeds."""
        channels, seen = [], set()

        # 1. Direct /sites/ index pages
        for page in range(1, max_pages + 1):
            try:
                page_url = cls.page_url(f'{cls.ROOT}/sites/', page)
                text = cls._fetch(page_url)
                for m in re.finditer(
                        r'<h2>(.*?)</h2>\s*<a[^>]+class="more"[^>]*href="([^"]+)"[^>]*>.*?(\d+)?\s*Videos',
                        text, re.S | re.I):
                    name = _clean(html.unescape(m.group(1)))
                    url = html.unescape(m.group(2))
                    if not url.startswith('http'):
                        url = urljoin(f'https://{cls.HOST}/', url)
                    key = url.rstrip('/')
                    if not name or key in seen:
                        continue
                    seen.add(key)
                    count = int(m.group(3)) if m.group(3) else 0
                    channels.append({'name': name, 'url': url, 'count': count})
            except Exception:
                break

        # 2. Homepage seeds fallback
        seeds = [url for _n, url in cls.HOMEPAGE_SECTIONS]
        for seed in seeds:
            try:
                text = cls._fetch(seed)
                for m in re.finditer(
                        r'<a[^>]+href=["\'](https?://[^"\']*/sites/[a-z0-9-]+/?|/sites/[a-z0-9-]+/?)["\'][^>]*>(.*?)</a>',
                        text, re.S | re.I):
                    href, inner = m.groups()
                    name = _clean(re.sub(r'<[^>]+>', ' ', inner))
                    if not name or name.lower() in ('porn sites', 'view all', 'sites', 'all', 'more'):
                        continue
                    url = html.unescape(href)
                    if not url.startswith('http'):
                        url = urljoin(f'https://{cls.HOST}/', url)
                    key = url.rstrip('/')
                    if key in seen:
                        continue
                    seen.add(key)
                    channels.append({'name': name, 'url': url, 'count': 0})
            except Exception:
                continue

        return sorted(channels, key=lambda c: (-c.get('count', 0), c['name'].lower()))

    fetch_studios = fetch_channels

    # cast chip: <a class="models__item thumb_model" href="…/models/slug/">
    #               <svg …></svg> <span>Name</span> </a>
    _CHIP_RE = re.compile(
        r'<a class="models__item[^"]*thumb_model[^"]*"\s+'
        r'href="([^"]+/models/([a-z0-9-]+)/?)"(.*?)</a>', re.S)
    _CHIP_NAME_RE = re.compile(r'<span[^>]*>([^<]+)</span>')
    _MODEL_ITEM_RE = re.compile(
        r'<a class="item"[^>]+href="([^"]+/models/[^"]+)"'
        r'[^>]*title="([^"]*)"(.*?)(?=<a class="item"|$)', re.S)

    @classmethod
    def fetch_actors(cls, max_pages=6):
        """Male actors for the sidebar Actors tab.

        The sites publish a single mixed /models/ directory (no /actors/
        route, no gender metadata, and alphabetical sweeps are blocked by
        their WAF).  Male performers are therefore collected from the cast
        chips shown on busy listing pages plus the shallow model directory,
        then intersected with the curated MALE_ACTORS index.
        """
        found = {}

        def add(url, name, count=0, thumb=''):
            slug = cls._slugify(name)
            if not slug or slug not in cls.MALE_ACTORS:
                return
            prev = found.get(slug)
            if prev is None or (count and not prev.get('count')):
                found[slug] = {'name': name.strip(), 'url': url,
                               'thumb': thumb or '', 'count': count}

        # a) cast chips from high-traffic listing seeds
        seeds = [u for _n, u in cls.HOMEPAGE_SECTIONS]
        if seeds:
            seeds.append(KvsBrowser.page_url(seeds[-1], 2))
        for seed in seeds:
            try:
                text = cls._fetch(seed)
            except Exception:
                continue
            for url, slug, block in cls._CHIP_RE.findall(text):
                nm = cls._CHIP_NAME_RE.search(block)
                if nm:
                    add(urljoin(cls.ROOT + '/', url.lstrip('/')),
                        html.unescape(nm.group(1)))

        # b) enrich with the shallow /models/ directory (counts + thumbs)
        rows = cls.fetch_models(max_pages)
        for r in rows:
            add(r['url'], r['name'], r.get('count') or 0,
                r.get('thumb') or '')

        # c) pinned actors: guarantee presence via canonical model page
        for slug in cls.PINNED_ACTORS:
            if slug not in found:
                add(f'{cls.ROOT}/models/{slug}/', slug.replace('-', ' ')
                    .title())

        return sorted(found.values(),
                      key=lambda r: (-r.get('count') or 0,
                                     r.get('name', '').casefold()))


class SiteFreePornVideos(KvsDirectSite):
    """Download adapter for freepornvideos.xxx video pages (direct MP4)."""
    _ROOT = FPV_ROOT
    _HOST = FPV_HOST
    website_pattern = (
        r'https?://(?:www\.)?freepornvideos\.xxx/videos/(?:\d+/)?[^/?#]+')
    website_dirname_pattern = r'/videos/((?:\d+/)?[^/?#]+)'
    direct_site_name = 'FreePornVideos'
    direct_default_referer = FPV_HOME


class FreePornVideosBrowser(KvsBrowser):
    ROOT = FPV_ROOT
    HOST = FPV_HOST
    SITE_LABEL = 'FreePornVideos'

    CATEGORIES = ()
