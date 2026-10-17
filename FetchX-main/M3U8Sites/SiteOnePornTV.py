#!/usr/bin/env python
# coding: utf-8
"""1porn.tv - same KVS engine/template as freepornvideos.xxx.

Video pages carry signed get_file MP4s (2160m/720m/480m), og:title has a
"| Free Porn" suffix (stripped by the shared parser). Listings, tags index,
models directory and studio ("channel") links all match the shared markup,
so everything is inherited from SiteFreePornVideos with a new domain.
"""

from M3U8Sites.SiteFreePornVideos import (
    KvsDirectSite,
    KvsBrowser,
)

ONEPORN_ROOT = 'https://www.1porn.tv'
ONEPORN_HOME = ONEPORN_ROOT + '/'
ONEPORN_HOST = 'www.1porn.tv'


class SiteOnePornTV(KvsDirectSite):
    """Download adapter for 1porn.tv video pages (direct MP4)."""
    _ROOT = ONEPORN_ROOT
    _HOST = ONEPORN_HOST
    website_pattern = (
        r'https?://(?:www\.)?1porn\.tv/videos/(?:\d+/)?[^/?#]+')
    website_dirname_pattern = r'/videos/((?:\d+/)?[^/?#]+)'
    direct_site_name = 'OnePorn'
    direct_default_referer = ONEPORN_HOME


class OnePornTVBrowser(KvsBrowser):
    ROOT = ONEPORN_ROOT
    HOST = ONEPORN_HOST
    SITE_LABEL = 'OnePorn'

    HOMEPAGE_SECTIONS = (
        ('Trending', f'{ONEPORN_ROOT}/most-popular/week/'),
        ('Latest Updates', f'{ONEPORN_ROOT}/latest-updates/'),
        ('Most Popular', f'{ONEPORN_ROOT}/most-popular/month/'),
    )

    CATEGORIES = ()
