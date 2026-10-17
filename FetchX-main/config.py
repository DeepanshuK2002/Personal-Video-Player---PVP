import json
import os
import re
import threading
import time
from urllib.parse import urlsplit


headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
}

MIRRORS = {
    'missav':  ['missav.ai', 'missav.ws', 'missav123.com', 'missav.live'],
    'jable':   ['jable.tv', 'fs1.app'],
    'supjav':  ['supjav.com', 'supjav.net', 'supjav.org'],
    'hanime1': ['hanime1.me'],
    'hanimetv': ['hanime.tv'],
    'tnaflix':  ['www.tnaflix.com'],
}


_BEEG_HOST_RE = re.compile(r'(?:^|\.)beeg\.')


def site_name_from_url(url: str) -> str:
    host = (urlsplit(url or '').netloc or '').lower()
    if 'jable' in host or 'fs1.app' in host:
        return 'JableTV'
    if 'missav' in host:
        return 'MissAV'
    if 'supjav' in host:
        return 'SupJav'
    if 'hanime1' in host:
        return 'Hanime1'
    if 'hanime.tv' in host or 'hanime' in host:
        return 'HanimeTV'
    if 'tnaflix' in host:
        return 'TnaFlix'
    if 'freepornvideos' in host:
        return 'FreePornVideos'
    if '1porn.tv' in host:
        return 'OnePorn'
    if _BEEG_HOST_RE.search(host):
        return 'Beeg'
    return host or 'Video'

_cf_lock = threading.Lock()
_prefs_lock = threading.Lock()
_proxy_lock = threading.Lock()
_PROXY_UNSET = object()
_proxy_url_cache = _PROXY_UNSET
_proxy_mode_cache = _PROXY_UNSET
_system_proxy_cache = _PROXY_UNSET
CF_OVERRIDES = {}
VALID_RESOLUTION_PREFS = {'highest', 'lowest', '1080', '720', '480', '360'}
VALID_SUBTITLE_PREFS = {'none', 'ja', 'en', 'zh', 'all'}
VALID_RECOGNITION_QUALITIES = {'auto', 'quality', 'balanced', 'fast'}
DEFAULT_DOWNLOAD_CONCURRENCY = 2
MIN_DOWNLOAD_CONCURRENCY = 1
MAX_DOWNLOAD_CONCURRENCY = 32
DEFAULT_MAX_WORKERS_PER_VIDEO = (
    min(os.cpu_count() * 2, 16) if os.cpu_count() else 8)
MIN_WORKERS_PER_VIDEO = 1
MAX_WORKERS_PER_VIDEO = 16
VALID_PROXY_SCHEMES = {
    'http', 'https', 'socks4', 'socks4a', 'socks5', 'socks5h',
}
VALID_PROXY_MODES = {'manual', 'system', 'direct'}


def _cf_store_path():
    base = os.environ.get('APPDATA') or os.path.expanduser('~')
    return os.path.join(base, 'FetchJAV', 'cf_overrides.json')


def _ui_prefs_path():
    return os.path.join(os.path.dirname(_cf_store_path()), 'ui_prefs.json')


def queue_csv_path():
    return os.path.join(os.path.dirname(_ui_prefs_path()), 'download_queue.csv')


def _load_prefs():
    path = _ui_prefs_path()
    bak = path + '.bak'
    for p in (path, bak):
        try:
            with open(p, 'r', encoding='utf-8') as f:
                raw = json.load(f)
        except Exception:
            continue
        if isinstance(raw, dict):
            if p != path:
                try:
                    _save_prefs(raw)
                except Exception:
                    pass
            return dict(raw)
        if isinstance(raw, str):
            result = {'theme': raw}
            if p != path:
                try:
                    _save_prefs(result)
                except Exception:
                    pass
            return result
    return {}


def _save_prefs(prefs):
    path = _ui_prefs_path()
    folder = os.path.dirname(path)
    os.makedirs(folder, exist_ok=True)
    tmp = path + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(prefs, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)
    try:
        bak = path + '.bak'
        with open(bak, 'w', encoding='utf-8') as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
    except Exception:
        pass


def get_theme():
    mode = _load_prefs().get('theme')
    if isinstance(mode, str):
        mode = mode.strip().lower()
        if mode in {'system', 'light', 'dark'}:
            return mode
    return 'dark'


def set_theme(mode):
    mode = (mode or '').strip().lower()
    if mode not in {'system', 'light', 'dark'}:
        mode = 'dark'
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['theme'] = mode
            _save_prefs(prefs)
    except Exception:
        pass


def get_ui_lang():
    code = _load_prefs().get('lang')
    if isinstance(code, str):
        code = code.strip()
        if code in {'en', 'zh', 'zh-Hans', 'ja'}:
            return code
    return None


def set_ui_lang(code):
    code = (code or '').strip()
    if code not in {'en', 'zh', 'zh-Hans', 'ja'}:
        code = 'en'
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['lang'] = code
            _save_prefs(prefs)
    except Exception:
        pass


def get_resolution_pref():
    pref = _load_prefs().get('resolution')
    if isinstance(pref, str):
        pref = pref.strip().lower()
        if pref in VALID_RESOLUTION_PREFS:
            return pref
    return 'highest'


def set_resolution_pref(pref):
    pref = str(pref or '').strip().lower()
    if pref not in VALID_RESOLUTION_PREFS:
        pref = 'highest'
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['resolution'] = pref
            _save_prefs(prefs)
    except Exception:
        pass


MAX_DOWNLOAD_HISTORY = 10000


def get_download_history():
    try:
        with _prefs_lock:
            history = _load_prefs().get('download_history', [])
            if isinstance(history, list):
                return [dict(x) for x in history if isinstance(x, dict)]
    except Exception:
        pass
    return []


def add_download_history(entry: dict):
    url = (entry.get('url') or '').strip()
    if not url:
        return False
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            history = prefs.get('download_history', [])
            if not isinstance(history, list):
                history = []
            history = [x for x in history
                       if isinstance(x, dict) and x.get('url') != url]
            history.insert(0, {
                'url': url,
                'title': entry.get('title') or url,
                'path': entry.get('path') or '',
                'size': int(entry.get('size') or 0),
                'site': str(entry.get('site') or ''),
                'finished_at': str(entry.get('finished_at') or ''),
            })
            prefs['download_history'] = history[:MAX_DOWNLOAD_HISTORY]
            _save_prefs(prefs)
            return True
    except Exception:
        return False


def remove_download_history(url: str):
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            history = prefs.get('download_history', [])
            if not isinstance(history, list):
                return
            prefs['download_history'] = [
                x for x in history
                if isinstance(x, dict) and x.get('url') != url]
            _save_prefs(prefs)
    except Exception:
        pass


def clear_download_history():
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['download_history'] = []
            _save_prefs(prefs)
    except Exception:
        pass


def get_subtitle_pref():
    pref = _load_prefs().get('subtitle_mode')
    if isinstance(pref, str):
        pref = pref.strip().lower()
        if pref in VALID_SUBTITLE_PREFS:
            return pref
    return 'none'


def set_subtitle_pref(pref):
    pref = str(pref or '').strip().lower()
    if pref not in VALID_SUBTITLE_PREFS:
        pref = 'none'
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['subtitle_mode'] = pref
            _save_prefs(prefs)
    except Exception:
        pass


DEFAULT_INACTIVE_SITES = {'Hanime1', 'TnaFlix'}


def get_inactive_sites():
    prefs = _load_prefs()
    if 'inactive_sites' in prefs:
        val = prefs.get('inactive_sites')
        if isinstance(val, (list, tuple, set)):
            return {str(x).strip() for x in val if str(x).strip()}
    return set(DEFAULT_INACTIVE_SITES)


def set_inactive_sites(inactive_sites):
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['inactive_sites'] = sorted(list({str(x).strip() for x in (inactive_sites or set()) if str(x).strip()}))
            _save_prefs(prefs)
    except Exception:
        pass


def _normalize_recognition_quality(value):
    quality = str(value or '').strip().lower().replace('_', '-')
    aliases = {
        '': 'auto',
        'default': 'auto',
        'automatic': 'auto',
        'recommended': 'auto',
        'cpu': 'auto',
        'precise': 'quality',
        'precision': 'quality',
        'accurate': 'quality',
        'accuracy': 'quality',
        'high': 'quality',
        'best': 'quality',
        'large': 'quality',
        'large-v3-turbo': 'quality',
        'medium': 'balanced',
        'normal': 'balanced',
        'small': 'balanced',
        'speed': 'fast',
        'quick': 'fast',
        'base': 'fast',
        'legacy': 'fast',
    }
    quality = aliases.get(quality, quality)
    if quality in VALID_RECOGNITION_QUALITIES:
        return quality
    return 'auto'


def get_recognition_quality():
    """Return the shared local speech-recognition quality preference."""
    return _normalize_recognition_quality(
        _load_prefs().get('recognition_quality'))


def set_recognition_quality(value):
    """Persist a normalized speech-recognition quality for both GUIs."""
    quality = _normalize_recognition_quality(value)
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['recognition_quality'] = quality
            _save_prefs(prefs)
    except Exception:
        pass
    return quality


def _normalize_download_concurrency(value):
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        parsed = DEFAULT_DOWNLOAD_CONCURRENCY
    return max(MIN_DOWNLOAD_CONCURRENCY,
               min(parsed, MAX_DOWNLOAD_CONCURRENCY))


def get_download_concurrency():
    """Return the persisted number of simultaneous video downloads."""
    return _normalize_download_concurrency(
        _load_prefs().get('download_concurrency'))


def set_download_concurrency(value):
    """Persist a clamped simultaneous-video-download limit."""
    normalized = _normalize_download_concurrency(value)
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['download_concurrency'] = normalized
            _save_prefs(prefs)
    except Exception:
        pass
    return normalized


def normalize_max_workers_per_video(value):
    """Return a safe per-video segment worker count (1–16)."""
    try:
        parsed = int(str(value).strip())
    except (TypeError, ValueError):
        parsed = DEFAULT_MAX_WORKERS_PER_VIDEO
    return max(MIN_WORKERS_PER_VIDEO, min(parsed, MAX_WORKERS_PER_VIDEO))


def get_max_workers_per_video():
    """Return the persisted number of segment workers used by each video."""
    return normalize_max_workers_per_video(
        _load_prefs().get('max_workers_per_video'))


def set_max_workers_per_video(value):
    """Persist a clamped per-video segment worker limit for every client."""
    normalized = normalize_max_workers_per_video(value)
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['max_workers_per_video'] = normalized
            _save_prefs(prefs)
    except Exception:
        pass
    return normalized


def normalize_proxy_url(raw):
    """Validate one app-scoped proxy URL; bare host:port means HTTP."""
    value = str(raw or '').strip()
    if not value:
        return ''
    if re.search(r'[\x00-\x20\x7f]', value):
        raise ValueError('Proxy URL cannot contain whitespace or control characters')
    if '://' not in value:
        value = 'http://' + value
    try:
        parsed = urlsplit(value)
        scheme = parsed.scheme.lower()
        hostname = parsed.hostname
        parsed.port  # force validation of malformed/out-of-range ports
    except (TypeError, ValueError):
        raise ValueError('Invalid proxy URL') from None
    if scheme not in VALID_PROXY_SCHEMES or not hostname:
        raise ValueError('Unsupported or incomplete proxy URL')
    if parsed.path not in ('', '/') or parsed.query or parsed.fragment:
        raise ValueError('Proxy URL must not contain a path, query, or fragment')
    return value


def get_proxy_url():
    global _proxy_url_cache
    if _proxy_url_cache is _PROXY_UNSET:
        with _proxy_lock:
            if _proxy_url_cache is _PROXY_UNSET:
                try:
                    value = normalize_proxy_url(_load_prefs().get('proxy_url'))
                except ValueError:
                    value = ''
                _proxy_url_cache = value
    return _proxy_url_cache


def set_proxy_url(raw):
    global _proxy_mode_cache, _proxy_url_cache
    value = normalize_proxy_url(raw)
    with _prefs_lock:
        prefs = _load_prefs()
        if value:
            prefs['proxy_url'] = value
            prefs['proxy_mode'] = 'manual'
        else:
            prefs.pop('proxy_url', None)
            prefs['proxy_mode'] = 'direct'
        _save_prefs(prefs)
    with _proxy_lock:
        _proxy_url_cache = value
        _proxy_mode_cache = 'manual' if value else 'direct'
    return value


def get_proxy_mode():
    """Return manual/system/direct, migrating legacy preferences in memory."""
    global _proxy_mode_cache
    if _proxy_mode_cache is _PROXY_UNSET:
        with _proxy_lock:
            if _proxy_mode_cache is _PROXY_UNSET:
                prefs = _load_prefs()
                mode = str(prefs.get('proxy_mode') or '').strip().lower()
                if mode not in VALID_PROXY_MODES:
                    try:
                        legacy_url = normalize_proxy_url(
                            prefs.get('proxy_url'))
                    except ValueError:
                        legacy_url = ''
                    mode = 'manual' if legacy_url else 'direct'
                _proxy_mode_cache = mode
    return _proxy_mode_cache


def set_proxy_mode(mode):
    """Persist the routing mode without copying detected system settings."""
    global _proxy_mode_cache, _system_proxy_cache
    value = str(mode or '').strip().lower()
    if value not in VALID_PROXY_MODES:
        raise ValueError('Proxy mode must be manual, system, or direct')
    with _prefs_lock:
        prefs = _load_prefs()
        prefs['proxy_mode'] = value
        _save_prefs(prefs)
    with _proxy_lock:
        _proxy_mode_cache = value
        if value == 'system':
            _system_proxy_cache = _PROXY_UNSET
    return value


def parse_windows_proxy_server(raw):
    """Translate a Windows ProxyServer value into requests-style routes."""
    value = str(raw or '').strip()
    if not value:
        return {}

    if '=' not in value and ';' not in value:
        try:
            proxy = normalize_proxy_url(value)
        except ValueError:
            return {}
        return {'http': proxy, 'https': proxy}

    routes = {}
    socks_proxy = ''
    for item in value.split(';'):
        if '=' not in item:
            continue
        protocol, address = item.split('=', 1)
        protocol = protocol.strip().lower()
        address = address.strip()
        if protocol not in {'http', 'https', 'socks'} or not address:
            continue
        if protocol == 'socks' and '://' not in address:
            address = 'socks4://' + address
        try:
            proxy = normalize_proxy_url(address)
        except ValueError:
            continue
        if protocol == 'socks':
            socks_proxy = proxy
        else:
            routes[protocol] = proxy

    if socks_proxy:
        routes.setdefault('http', socks_proxy)
        routes.setdefault('https', socks_proxy)
    return routes


def _read_windows_proxy_settings():
    """Read the current user's manual WinINet proxy without changing it."""
    settings = {'enabled': False, 'server': '', 'pac_url': ''}
    if os.name != 'nt':
        return settings
    try:
        import winreg
        path = (
            r'Software\Microsoft\Windows\CurrentVersion'
            r'\Internet Settings'
        )
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, path) as key:
            try:
                enabled = winreg.QueryValueEx(key, 'ProxyEnable')[0]
                settings['enabled'] = (
                    isinstance(enabled, int) and enabled != 0)
            except OSError:
                pass
            try:
                server = winreg.QueryValueEx(key, 'ProxyServer')[0]
                if isinstance(server, str):
                    settings['server'] = server
            except OSError:
                pass
            try:
                pac_url = winreg.QueryValueEx(key, 'AutoConfigURL')[0]
                if isinstance(pac_url, str):
                    settings['pac_url'] = pac_url.strip()
            except OSError:
                pass
    except (ImportError, OSError, TypeError, ValueError):
        pass
    return settings


def _redact_proxy_url(value):
    """Return a display-safe endpoint with any user information removed."""
    if not value:
        return ''
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname or ''
        if ':' in hostname and not hostname.startswith('['):
            hostname = f'[{hostname}]'
        port = f':{parsed.port}' if parsed.port is not None else ''
        return f'{parsed.scheme}://{hostname}{port}'
    except (TypeError, ValueError):
        return ''


def _detect_windows_proxy_state():
    settings = _read_windows_proxy_settings()
    routes = {}
    if settings.get('enabled'):
        routes = parse_windows_proxy_server(settings.get('server'))
    if routes:
        selected = routes.get('https') or routes.get('http') or ''
        return routes, _redact_proxy_url(selected), 'detected'
    if settings.get('pac_url'):
        # A PAC URL points to executable configuration, not a proxy endpoint.
        return {}, '', 'pac'
    if settings.get('enabled'):
        return {}, '', 'invalid'
    return {}, '', 'disabled'


def detect_windows_proxy_url():
    """Detect once and return a credential-free endpoint plus status."""
    _routes, display_url, status = _detect_windows_proxy_state()
    return display_url, status


def refresh_system_proxy():
    """Refresh the in-memory system proxy used by System mode."""
    global _system_proxy_cache
    routes, display_url, status = _detect_windows_proxy_state()
    with _proxy_lock:
        _system_proxy_cache = (dict(routes), status)
    return display_url, status


def refresh_windows_proxy():
    """Compatibility alias for callers that name the Windows source."""
    return refresh_system_proxy()


def _get_cached_system_proxy():
    global _system_proxy_cache
    if _system_proxy_cache is _PROXY_UNSET:
        routes, _display_url, status = _detect_windows_proxy_state()
        with _proxy_lock:
            if _system_proxy_cache is _PROXY_UNSET:
                _system_proxy_cache = (dict(routes), status)
    with _proxy_lock:
        routes, status = _system_proxy_cache
        return dict(routes), status


def proxy_request_kwargs():
    """Return explicit routes for requests and curl_cffi.

    Empty routes are intentional: both clients otherwise inherit proxy
    environment variables, which would make the Direct mode misleading.
    """
    direct_routes = {'http': '', 'https': '', 'all': ''}
    mode = get_proxy_mode()
    if mode == 'direct':
        return {'proxies': direct_routes}
    if mode == 'system':
        routes, _status = _get_cached_system_proxy()
        direct_routes.update(routes)
        return {'proxies': direct_routes}
    value = get_proxy_url()
    if not value:
        return {'proxies': direct_routes}
    direct_routes.update({'http': value, 'https': value})
    return {'proxies': direct_routes}


def _parse_cf_clearance(raw):
    if raw is None:
        return ''
    s = re.sub(r'[\x00-\x1f\x7f]+', '', str(raw).strip())
    if not s:
        return ''
    if 'cf_clearance=' in s:
        m = re.search(r'cf_clearance=([^;,\s]+)', s)
        return m.group(1) if m else ''
    return s.strip('\'"')


def _norm_host(host):
    h = (host or '').strip().lower().rstrip('.')
    if ':' in h:
        h = h.split(':', 1)[0].rstrip('.')
    return h


def get_cf_override(host):
    with _cf_lock:
        entry = CF_OVERRIDES.get(_norm_host(host))
        return dict(entry) if entry else None


def cf_override_hosts():
    with _cf_lock:
        return sorted(CF_OVERRIDES.keys())


def set_cf_override(host, cookie, ua):
    global CF_OVERRIDES
    h = _norm_host(host)
    if not h:
        return
    entry = {}
    ck = _parse_cf_clearance(cookie)
    if ck:
        entry['cookie'] = ck
    ua = (ua or '').strip()
    if ua:
        entry['ua'] = ua
    with _cf_lock:
        next_overrides = dict(CF_OVERRIDES)
        if entry:
            next_overrides[h] = entry
        else:
            next_overrides.pop(h, None)
        CF_OVERRIDES = next_overrides
    save_cf_overrides()


def clear_cf_override(host):
    set_cf_override(host, '', '')


def load_cf_overrides():
    global CF_OVERRIDES
    path = _cf_store_path()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            raw = json.load(f)
    except FileNotFoundError:
        with _cf_lock:
            CF_OVERRIDES = {}
        return
    except Exception:
        try:
            os.replace(path, path + '.bak')
        except Exception:
            pass
        with _cf_lock:
            CF_OVERRIDES = {}
        return

    parsed = {}
    if isinstance(raw, dict):
        for host, entry in raw.items():
            h = _norm_host(host)
            if not h or not isinstance(entry, dict):
                continue
            clean = {}
            cookie = entry.get('cookie')
            ua = entry.get('ua')
            if isinstance(cookie, str):
                cookie = _parse_cf_clearance(cookie)
                if cookie:
                    clean['cookie'] = cookie
            if isinstance(ua, str) and ua.strip():
                clean['ua'] = ua.strip()
            if clean:
                parsed[h] = clean
    with _cf_lock:
        CF_OVERRIDES = parsed


def save_cf_overrides():
    try:
        path = _cf_store_path()
        folder = os.path.dirname(path)
        os.makedirs(folder, exist_ok=True)
        with _cf_lock:
            snapshot = dict(CF_OVERRIDES)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        pass


try:
    load_cf_overrides()
except Exception:
    pass


def get_saved_videos():
    try:
        with _prefs_lock:
            saved = _load_prefs().get('saved_videos', [])
            if isinstance(saved, list):
                return list(saved)
    except Exception:
        pass
    return []


def is_video_saved(url):
    url = (url or '').strip()
    if not url:
        return False
    saved = get_saved_videos()
    return any(isinstance(item, dict) and item.get('url') == url for item in saved)


def format_saved_date(date_str: str = '', timestamp: Optional[int] = None) -> str:
    """Returns human-friendly date string: 'Today', 'Yesterday', or 'Saturday, 29 August 2026'."""
    today_str = time.strftime('%Y-%m-%d')
    yesterday_str = time.strftime('%Y-%m-%d', time.localtime(time.time() - 86400))
    if date_str == today_str:
        return 'Today'
    if date_str == yesterday_str:
        return 'Yesterday'
    try:
        if date_str:
            t = time.strptime(date_str, '%Y-%m-%d')
            return time.strftime('%A, %d %B %Y', t)
        elif timestamp:
            t = time.localtime(timestamp)
            return time.strftime('%A, %d %B %Y', t)
    except Exception:
        pass
    return date_str or 'Earlier'


def add_saved_video(video_info: dict):
    url = (video_info.get('url') or video_info.get('page_url') or '').strip()
    if not url:
        return False
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            saved = prefs.get('saved_videos', [])
            if not isinstance(saved, list):
                saved = []

            existing_idx = -1
            for i, item in enumerate(saved):
                if isinstance(item, dict) and item.get('url') == url:
                    existing_idx = i
                    break

            now_ts = int(time.time())
            now_date = time.strftime('%Y-%m-%d')
            entry = {
                'url': url,
                'title': video_info.get('title') or url,
                'thumbnail': video_info.get('thumbnail') or video_info.get('img') or '',
                'duration': video_info.get('duration') or '',
                'site_name': video_info.get('site_name') or '',
                'saved_at': video_info.get('saved_at') or now_ts,
                'saved_date': video_info.get('saved_date') or now_date,
            }
            if existing_idx >= 0:
                old = saved[existing_idx]
                if isinstance(old, dict):
                    entry['saved_at'] = old.get('saved_at') or entry['saved_at']
                    entry['saved_date'] = old.get('saved_date') or entry['saved_date']
                saved[existing_idx] = entry
            else:
                saved.insert(0, entry)
            prefs['saved_videos'] = saved
            _save_prefs(prefs)
            return True
    except Exception:
        return False


def remove_saved_video(url: str):
    url = (url or '').strip()
    if not url:
        return False
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            saved = prefs.get('saved_videos', [])
            if not isinstance(saved, list):
                return False
            new_saved = [item for item in saved if isinstance(item, dict) and item.get('url') != url]
            prefs['saved_videos'] = new_saved
            _save_prefs(prefs)
            return True
    except Exception:
        return False


def toggle_saved_video(video_info: dict) -> bool:
    url = (video_info.get('url') or video_info.get('page_url') or '').strip()
    if not url:
        return False
    if is_video_saved(url):
        remove_saved_video(url)
        return False
    else:
        add_saved_video(video_info)
        return True


def clear_saved_videos():
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['saved_videos'] = []
            _save_prefs(prefs)
    except Exception:
        pass


# Aliases for Watch Later nomenclature
get_watch_later_videos = get_saved_videos
is_watch_later_video = is_video_saved
add_watch_later_video = add_saved_video
remove_watch_later_video = remove_saved_video
toggle_watch_later_video = toggle_saved_video
clear_watch_later_videos = clear_saved_videos


def export_saved_videos(filepath: str) -> int:
    """Export saved videos list to a JSON file. Returns number of items exported."""
    filepath = str(filepath or '').strip()
    if not filepath:
        return 0
    try:
        saved = get_saved_videos()
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(saved, f, ensure_ascii=False, indent=2, sort_keys=True)
        return len(saved)
    except Exception:
        return 0


def import_saved_videos(filepath: str) -> int:
    """Import saved videos from a JSON file, merging with existing list.
    Returns the number of NEW items added (duplicates by URL are skipped)."""
    filepath = str(filepath or '').strip()
    if not filepath:
        return 0
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, list):
            return 0
    except Exception:
        return 0
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            saved = prefs.get('saved_videos', [])
            if not isinstance(saved, list):
                saved = []
            existing_urls = {item.get('url') for item in saved if isinstance(item, dict)}
            added = 0
            for item in data:
                if not isinstance(item, dict):
                    continue
                url = (item.get('url') or '').strip()
                if not url or url in existing_urls:
                    continue
                entry = {
                    'url': url,
                    'title': item.get('title') or url,
                    'thumbnail': item.get('thumbnail') or item.get('img') or '',
                    'duration': item.get('duration') or '',
                    'site_name': item.get('site_name') or '',
                }
                saved.append(entry)
                existing_urls.add(url)
                added += 1
            if added:
                prefs['saved_videos'] = saved
                _save_prefs(prefs)
            return added
    except Exception:
        return 0


# ==============================================================================
# Dynamic Remote Announcements / Notifications / Ads System
# ==============================================================================

DEFAULT_ANNOUNCEMENTS_URL = 'https://raw.githubusercontent.com/DeepanshuK2002/FetchX/main/announcements.json'


def get_remote_announcements_url() -> str:
    try:
        with _prefs_lock:
            return str(_load_prefs().get('remote_announcements_url') or DEFAULT_ANNOUNCEMENTS_URL).strip()
    except Exception:
        return DEFAULT_ANNOUNCEMENTS_URL


def set_remote_announcements_url(url: str):
    url = str(url or '').strip()
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['remote_announcements_url'] = url or DEFAULT_ANNOUNCEMENTS_URL
            _save_prefs(prefs)
    except Exception:
        pass


def get_announcements_enabled() -> bool:
    try:
        with _prefs_lock:
            return bool(_load_prefs().get('remote_announcements_enabled', True))
    except Exception:
        return True


def set_announcements_enabled(enabled: bool):
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['remote_announcements_enabled'] = bool(enabled)
            _save_prefs(prefs)
    except Exception:
        pass


def get_dismissed_announcements() -> list:
    try:
        with _prefs_lock:
            d = _load_prefs().get('dismissed_announcements', [])
            if isinstance(d, list):
                return list(d)
    except Exception:
        pass
    return []


def is_announcement_dismissed(notice_id: str) -> bool:
    if not notice_id:
        return False
    return str(notice_id) in set(get_dismissed_announcements())


def dismiss_announcement(notice_id: str):
    notice_id = str(notice_id or '').strip()
    if not notice_id:
        return
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            d = prefs.get('dismissed_announcements', [])
            if not isinstance(d, list):
                d = []
            if notice_id not in d:
                d.append(notice_id)
                prefs['dismissed_announcements'] = d
                _save_prefs(prefs)
    except Exception:
        pass


def reset_dismissed_announcements():
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['dismissed_announcements'] = []
            _save_prefs(prefs)
    except Exception:
        pass


def get_cached_announcements() -> dict:
    try:
        with _prefs_lock:
            c = _load_prefs().get('cached_announcements', {})
            if isinstance(c, dict):
                return dict(c)
    except Exception:
        pass
    return {}


def save_cached_announcements(data: dict):
    if not isinstance(data, dict):
        return
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['cached_announcements'] = {
                'payload': data,
                'cached_at': int(time.time()),
            }
            _save_prefs(prefs)
    except Exception:
        pass


def get_view_history():
    try:
        with _prefs_lock:
            h = _load_prefs().get('view_history', [])
            if isinstance(h, list):
                return list(h)
    except Exception:
        pass
    return []


def add_view_history(video):
    if not isinstance(video, dict):
        return
    url = (video.get('url') or video.get('page_url') or '').strip()
    if not url:
        return
    title = video.get('title') or url
    thumb = video.get('thumbnail') or video.get('img') or ''
    dur = video.get('duration') or ''
    site = video.get('site_name') or site_name_from_url(url)
    import time
    entry = {
        'url': url,
        'title': title,
        'thumbnail': thumb,
        'duration': dur,
        'site_name': site,
        'timestamp': int(time.time()),
    }
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            hist = prefs.get('view_history', [])
            if not isinstance(hist, list):
                hist = []
            hist = [item for item in hist if isinstance(item, dict) and item.get('url') != url]
            hist.insert(0, entry)
            prefs['view_history'] = hist[:10000]
            _save_prefs(prefs)
    except Exception:
        pass


def clear_view_history():
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['view_history'] = []
            _save_prefs(prefs)
    except Exception:
        pass


def remove_view_history(url):
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            hist = prefs.get('view_history', [])
            if isinstance(hist, list):
                prefs['view_history'] = [item for item in hist if isinstance(item, dict) and item.get('url') != url]
                _save_prefs(prefs)
    except Exception:
        pass


def _norm_wl_type(t: Optional[str]) -> str:
    if not t:
        return ''
    t = str(t).lower().strip()
    if t in ('models', 'model', 'actress', 'actresses'):
        return 'models'
    if t in ('channels', 'channel', 'studio', 'studios', 'sites', 'site'):
        return 'channels'
    if t in ('tags', 'tag', 'category', 'categories'):
        return 'tags'
    if t in ('actors', 'actor'):
        return 'actors'
    return t


def get_watchlist():
    try:
        with _prefs_lock:
            items = _load_prefs().get('watchlist', [])
            return list(items) if isinstance(items, list) else []
    except Exception:
        return []


def set_watchlist(items):
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['watchlist'] = list(items) if isinstance(items, list) else []
            _save_prefs(prefs)
    except Exception:
        pass


def add_watchlist_item(item):
    if not isinstance(item, dict):
        return False
    name = (item.get('name') or '').strip()
    if not name:
        return False
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            wl = prefs.get('watchlist', [])
            if not isinstance(wl, list):
                wl = []
            name_clean = name.lower()
            item_type = _norm_wl_type(item.get('type', 'models'))
            norm_item = dict(item)
            norm_item['name'] = name
            norm_item['type'] = item_type

            for existing in wl:
                if isinstance(existing, dict) and str(existing.get('name', '')).strip().lower() == name_clean:
                    if _norm_wl_type(existing.get('type')) == item_type:
                        if item.get('urls'):
                            merged = list(existing.get('urls') or [])
                            for u in item['urls']:
                                if u not in merged:
                                    merged.append(u)
                            existing['urls'] = merged
                            prefs['watchlist'] = wl
                            _save_prefs(prefs)
                        return False
            wl.append(norm_item)
            prefs['watchlist'] = wl
            _save_prefs(prefs)
            return True
    except Exception:
        return False


def remove_watchlist_item(name, item_type=None):
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            wl = prefs.get('watchlist', [])
            if not isinstance(wl, list):
                return False
            name_clean = str(name).strip().lower()
            req_type = _norm_wl_type(item_type) if item_type else ''
            filtered = []
            removed = False
            for item in wl:
                if isinstance(item, dict):
                    match_name = str(item.get('name', '')).strip().lower() == name_clean
                    match_type = True if not req_type else _norm_wl_type(item.get('type')) == req_type
                    if match_name and match_type:
                        removed = True
                        continue
                filtered.append(item)
            if removed:
                prefs['watchlist'] = filtered
                _save_prefs(prefs)
            return removed
    except Exception:
        return False


def is_in_watchlist(name: str, item_type: Optional[str] = None) -> bool:
    if not name:
        return False
    try:
        with _prefs_lock:
            wl = _load_prefs().get('watchlist', [])
            if not isinstance(wl, list):
                return False
            name_clean = str(name).strip().lower()
            req_type = _norm_wl_type(item_type) if item_type else ''
            for it in wl:
                if isinstance(it, dict) and str(it.get('name', '')).strip().lower() == name_clean:
                    if not req_type:
                        return True
                    if _norm_wl_type(it.get('type')) == req_type:
                        return True
            return False
    except Exception:
        return False


def toggle_watchlist_item(name: str, item_type: str = 'models', site: str = 'All', urls: Optional[list] = None) -> bool:
    """Toggles item in watchlist. Returns True if now in watchlist, False if removed."""
    if not name:
        return False
    if is_in_watchlist(name, item_type):
        remove_watchlist_item(name, item_type)
        return False
    else:
        add_watchlist_item({
            'name': name.strip(),
            'type': _norm_wl_type(item_type),
            'site': site,
            'urls': list(urls or []),
            'starred_at': time.time(),
            'auto_download': get_watchlist_auto_download()
        })
        return True


def get_watchlist_auto_download() -> bool:
    try:
        with _prefs_lock:
            return bool(_load_prefs().get('watchlist_auto_download', False))
    except Exception:
        return False


def set_watchlist_auto_download(enabled: bool):
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['watchlist_auto_download'] = bool(enabled)
            _save_prefs(prefs)
    except Exception:
        pass


VALID_VIDEO_OCR_LANGS = {'zh', 'en', 'ja', 'auto'}
VALID_VIDEO_OCR_BACKENDS = {'auto', 'rapidocr', 'win_native', 'easyocr', 'pytesseract'}
VALID_VIDEO_OCR_MODES = {'on_hardcoded_detected', 'always', 'manual_only'}


def get_video_ocr_enabled() -> bool:
    try:
        with _prefs_lock:
            return bool(_load_prefs().get('video_ocr_enabled', True))
    except Exception:
        return True


def set_video_ocr_enabled(enabled: bool):
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['video_ocr_enabled'] = bool(enabled)
            _save_prefs(prefs)
    except Exception:
        pass


def get_video_ocr_lang() -> str:
    try:
        with _prefs_lock:
            lang = str(_load_prefs().get('video_ocr_lang', 'zh')).strip().lower()
            return lang if lang in VALID_VIDEO_OCR_LANGS else 'zh'
    except Exception:
        return 'zh'


def set_video_ocr_lang(lang: str):
    lang = str(lang or 'zh').strip().lower()
    if lang not in VALID_VIDEO_OCR_LANGS:
        lang = 'zh'
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['video_ocr_lang'] = lang
            _save_prefs(prefs)
    except Exception:
        pass


def get_video_ocr_backend() -> str:
    try:
        with _prefs_lock:
            backend = str(_load_prefs().get('video_ocr_backend', 'auto')).strip().lower()
            return backend if backend in VALID_VIDEO_OCR_BACKENDS else 'auto'
    except Exception:
        return 'auto'


def set_video_ocr_backend(backend: str):
    backend = str(backend or 'auto').strip().lower()
    if backend not in VALID_VIDEO_OCR_BACKENDS:
        backend = 'auto'
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['video_ocr_backend'] = backend
            _save_prefs(prefs)
    except Exception:
        pass


def get_video_ocr_auto_mode() -> str:
    try:
        with _prefs_lock:
            mode = str(_load_prefs().get('video_ocr_auto_mode', 'manual_only')).strip().lower()
            return mode if mode in VALID_VIDEO_OCR_MODES else 'manual_only'
    except Exception:
        return 'manual_only'


def set_video_ocr_auto_mode(mode: str):
    mode = str(mode or 'manual_only').strip().lower()
    if mode not in VALID_VIDEO_OCR_MODES:
        mode = 'manual_only'
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['video_ocr_auto_mode'] = mode
            _save_prefs(prefs)
    except Exception:
        pass


def get_auto_resume_downloads() -> bool:
    try:
        with _prefs_lock:
            val = _load_prefs().get('auto_resume_downloads')
            if val is None:
                return True
            return bool(val)
    except Exception:
        return True


def set_auto_resume_downloads(enabled: bool):
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['auto_resume_downloads'] = bool(enabled)
            _save_prefs(prefs)
    except Exception:
        pass


def get_persisted_queue():
    try:
        with _prefs_lock:
            items = _load_prefs().get('incomplete_queue', [])
            return list(items) if isinstance(items, list) else []
    except Exception:
        return []


def set_persisted_queue(items):
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['incomplete_queue'] = list(items) if isinstance(items, list) else []
            _save_prefs(prefs)
    except Exception:
        pass


AVAILABLE_SOURCES = (
    ('FreePornVideos', 'FreePornVideos (freepornvideos.xxx)', 'Full HD Videos, Studio Channels & Tags'),
    ('OnePorn', 'OnePorn (1porn.tv)', 'Global Videos, Models & Categories'),
    ('Beeg', 'Beeg (beeg.com)', 'Fast Streaming & Trending Video Feeds'),
)

DEFAULT_ENABLED_SOURCES = ['FreePornVideos', 'OnePorn', 'Beeg']


def get_enabled_sources() -> list:
    """Return list of active source identifiers."""
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            sources = prefs.get('enabled_sources')
            if isinstance(sources, list) and sources:
                valid = [s for s in sources if any(s == k for k, _l, _d in AVAILABLE_SOURCES)]
                disabled = prefs.get('disabled_sources') or []
                for k, _l, _d in AVAILABLE_SOURCES:
                    if k not in valid and k not in disabled:
                        valid.append(k)
                if valid:
                    return valid
    except Exception:
        pass
    return list(DEFAULT_ENABLED_SOURCES)


def is_source_enabled(source_key: str) -> bool:
    """Check if a particular source key is active."""
    return source_key in get_enabled_sources()


def set_source_enabled(source_key: str, enabled: bool) -> None:
    """Enable or disable a specific video source."""
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            current = list(prefs.get('enabled_sources') or DEFAULT_ENABLED_SOURCES)
            disabled = list(prefs.get('disabled_sources') or [])
            if enabled:
                if source_key not in current:
                    current.append(source_key)
                if source_key in disabled:
                    disabled.remove(source_key)
            else:
                if source_key in current:
                    current.remove(source_key)
                if source_key not in disabled:
                    disabled.append(source_key)
            if not current:
                current = [source_key]
            prefs['enabled_sources'] = current
            prefs['disabled_sources'] = disabled
            _save_prefs(prefs)
    except Exception:
        pass


def set_enabled_sources(sources: list) -> None:
    """Save the full list of enabled sources."""
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            valid = [s for s in sources if any(s == k for k, _l, _d in AVAILABLE_SOURCES)]
            if not valid:
                valid = list(DEFAULT_ENABLED_SOURCES)
            prefs['enabled_sources'] = valid
            _save_prefs(prefs)
    except Exception:
        pass


def _sidebar_cache_path() -> str:
    base = os.path.dirname(_ui_prefs_path())
    os.makedirs(base, exist_ok=True)
    return os.path.join(base, 'sidebar_categories.json')


def get_sidebar_cache() -> dict:
    """Load cached sidebar categories (tags, models, channels, actors) from disk."""
    try:
        p = _sidebar_cache_path()
        if os.path.isfile(p):
            with open(p, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
    except Exception:
        pass
    return {}


def save_sidebar_cache(data: dict) -> None:
    """Persist cached sidebar categories to disk for instant startup availability."""
    try:
        if isinstance(data, dict) and data:
            p = _sidebar_cache_path()
            with open(p, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def get_auto_check_updates() -> bool:
    """True if FetchX should automatically check GitHub Releases for updates on startup."""
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            return bool(prefs.get('auto_check_updates', True))
    except Exception:
        return True


def set_auto_check_updates(enabled: bool) -> None:
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['auto_check_updates'] = bool(enabled)
            _save_prefs(prefs)
    except Exception:
        pass


def get_last_update_check() -> float:
    """Timestamp of last update check."""
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            return float(prefs.get('last_update_check_time', 0))
    except Exception:
        return 0.0


def set_last_update_check(ts: float = 0.0) -> None:
    if not ts:
        ts = time.time()
    try:
        with _prefs_lock:
            prefs = _load_prefs()
            prefs['last_update_check_time'] = float(ts)
            _save_prefs(prefs)
    except Exception:
        pass






