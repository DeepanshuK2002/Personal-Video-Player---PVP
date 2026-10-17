#!/usr/bin/env python
# coding: utf-8
"""Minimal locales stub for headless FetchX (site_i18n compatibility)."""

LANGUAGES = {'en': 'English', 'zh': '繁體中文', 'zh-Hans': '简体中文', 'ja': '日本語'}

FONTS = {
    'en': 'Microsoft YaHei UI',
    'zh': 'Microsoft JhengHei UI',
    'zh-Hans': 'Microsoft YaHei UI',
    'ja': 'Yu Gothic UI',
}

_current = 'en'


def get_lang():
    return _current


def set_lang(lang):
    global _current
    if lang in LANGUAGES:
        _current = lang


def ui_font(*_a, **_k):
    return FONTS.get(_current, 'Microsoft YaHei UI')
