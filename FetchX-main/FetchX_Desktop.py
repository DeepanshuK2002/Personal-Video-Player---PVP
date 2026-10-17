#!/usr/bin/env python
# coding: utf-8
"""FetchX Desktop - Downloader & Media Browser for freepornvideos.xxx and beeg.com.

Visual Language:
- Apple Human Interface & Liquid Glass Aesthetics
- Crisp High-DPI resolution (Anti-aliased rendering)
- Heroicons (from https://heroicons.com/) vector icon engine
- Centered Wide Search Bar in Topbar
- Windows-native Caption Controls (Top-Right: Minimize, Maximize, Close)
- Left Sidebar Navigation Hub with Inline Badge Counts for Downloads
- 3 Videos Max per Row Adaptive Grid (No clipping/overflow)
- Large, Comfortable, Legible Font and Icon Sizes
- Grouped Settings Form & VLC In-App Video Theater Player
"""

import ctypes
import io
import math
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import traceback
import webbrowser
import concurrent.futures as futures

# ==============================================================================
# Windows High-DPI Awareness & GDI Initialization (Must run before Tkinter)
# ==============================================================================
try:
    if sys.platform == 'win32':
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor V2 DPI awareness
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass
        try:
            ctypes.windll.ole32.CoInitializeEx(None, 0x2)
        except Exception:
            pass
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('DeepanshuK2002.FetchX.Desktop.2.5')
        except Exception:
            pass
except Exception:
    pass

import tkinter as tk
from tkinter import ttk, font as tkfont, filedialog, messagebox
from PIL import Image, ImageDraw, ImageFont, ImageTk
import requests
from requests.adapters import HTTPAdapter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import config
import vlc
import analytics
import updater
from updater import APP_VERSION
from M3U8Sites.M3U8Crawler import set_resolution_pref
from M3U8Sites.SiteBeeg import SiteBeeg, BeegBrowser
from M3U8Sites.SiteFreePornVideos import SiteFreePornVideos, FreePornVideosBrowser
from M3U8Sites.SiteOnePornTV import SiteOnePornTV, OnePornTVBrowser
FEED_SITES = (
    ('FPV', FreePornVideosBrowser.HOMEPAGE_SECTIONS[1][1]),
    ('OnePorn', OnePornTVBrowser.HOMEPAGE_SECTIONS[1][1]),
    ('Beeg', 'teen'),
)

APP_TITLE = 'FetchX'
DEFAULT_SAVE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'downloads')
QUALITY_CHOICES = ('highest', '1080', '720', '480', 'lowest')

# ==============================================================================
# Liquid Glass & Apple Human Interface Theme Palettes (Dark & Light)
# ==============================================================================

DARK_PALETTE = {
    'WINDOW_BG':         '#121216',   # Frosted deep acrylic background
    'SIDEBAR_BG':        '#17171e',   # Acrylic left rail
    'SIDEBAR_DIVIDER':   '#262632',   # Glass hairline divider
    'SIDEBAR_HOVER':     '#22222d',   # Glass item hover
    'SIDEBAR_ACTIVE':    '#0a84ff',   # Apple System Blue active pill
    'CONTENT_BG':        '#0f0f13',   # Main canvas content background
    'CARD_BG':           '#1b1b24',   # Frosted glass card background
    'CARD_HOVER':        '#242430',   # Card hover surface
    'CARD_BORDER':       '#2a2a38',   # 1px glass border
    'CARD_BORDER_HOVER': '#404058',   # 1px glass hover highlight
    'ELEVATED':          '#20202c',   # Elevated glass surface
    'INK':               '#f5f5f7',   # High contrast crisp white
    'BODY':              '#a1a1aa',   # Light neutral gray
    'MUTE':              '#71717a',   # Muted caption gray
    'FAINT':             '#52525b',   # Faint placeholder gray
    'HAIRLINE':          '#262634',   # Subtle hairline separator
    'HAIRLINE_SOFT':     '#1f1f2a',   # Soft glass chip background
    'LINK':              '#0a84ff',   # Apple System Blue
    'LINK_HOVER':        '#409cff',   # Blue hover
    'LINK_DEEP':         '#0062cc',   # Blue pressed
    'LINK_SOFT':         '#1a365d',   # Blue subtle tint
    'ERROR':             '#ff453a',   # Apple System Red
    'ERROR_DEEP':        '#dc2626',   # Deep red
    'WARNING':           '#ff9f0a',   # Apple System Amber
    'WARNING_DEEP':      '#d97706',   # Deep amber
    'SUCCESS':           '#30d158',   # Apple System Green
    'ON_PRIMARY':        '#ffffff',   # White on primary
    'HOVER_SOFT':        '#22222e',   # Soft hover
    'HOVER_TINT':        '#2a2a38',   # Moderate hover
    'HOVER_DEEP':        '#323244',   # Deep hover
    'BORDER_HOVER':      '#444458',   # Border hover
    'SCROLLBAR':         '#323242',   # Scrollbar thumb
    'SCROLLBAR_ACTIVE':  '#4e4e62',   # Scrollbar active thumb
    'SEARCH_BG':         '#1f1f2b',   # Search capsule background
    'SEARCH_BORDER':     '#303042',   # Search capsule border
    'SEARCH_FOCUS':      '#0a84ff',   # Search capsule focus ring
    'CANVAS_BG':         '#0f0f13',

    # Custom component accents
    'INPUT_BG':          '#161622',
    'INPUT_BORDER':      '#2d2d3e',
    'INPUT_HOVER_BORDER':'#444458',
    'INPUT_BOX_BG':      '#1c1c2b',
    'PILL_SEC_BG':       '#161622',
    'PILL_SEC_BORDER':   '#3d3d52',
    'PILL_SEC_FG':       '#e4e4e7',
    'PILL_SEC_HOVER_BG': '#222232',
    'PILL_SEC_HOVER_BD': '#5a5a78',
    'PILL_SEC_HOVER_FG': '#60a5fa',
    'PILL_PRI_BG':       '#0f2844',
    'PILL_PRI_BORDER':   '#2563eb',
    'PILL_PRI_FG':       '#93c5fd',
    'PILL_PRI_HOVER_BG': '#16426e',
    'PILL_PRI_HOVER_BD': '#3b82f6',
    'PILL_PRI_HOVER_FG': '#ffffff',
    'PILL_SUC_BG':       '#0b2e22',
    'PILL_SUC_BORDER':   '#10b981',
    'PILL_SUC_FG':       '#6ee7b7',
    'PILL_SUC_HOVER_BG': '#134433',
    'PILL_SUC_HOVER_BD': '#34d399',
    'PILL_SUC_HOVER_FG': '#ffffff',
    'SWITCH_OFF_BG':     '#18181f',
    'SWITCH_OFF_BORDER': '#38384a',
    'SWITCH_ON_BG':      '#0070f3',
    'SWITCH_ON_BORDER':  '#3b82f6',
    'SEG_CONTAINER_BG':  '#121218',
    'SEG_CONTAINER_BD':  '#2d2d3a',
    'SEG_ACTIVE_BG':     '#0f2b48',
    'SEG_ACTIVE_BD':     '#2563eb',
    'SEG_ACTIVE_FG':     '#93c5fd',
    'SEG_INACTIVE_BG':   '#121218',
    'SEG_INACTIVE_FG':   '#71717a',
    'SEG_HOVER_BG':      '#1c1c28',
    'SEG_HOVER_BD':      '#3a3a4e',
    'SEG_HOVER_FG':      '#e4e4e7',
    'POPUP_BG':          '#181826',
    'POPUP_BORDER':      '#36364c',
    'POPUP_HOVER_BG':    '#222234',
    'POPUP_HOVER_BD':    '#32324a',
    'POPUP_ACTIVE_BG':   '#0f2b48',
    'POPUP_ACTIVE_BD':   '#2563eb',
    'POPUP_ACTIVE_FG':   '#93c5fd',
    'MEDIA_OVERLAY_BG':  '#0e0e14',
    'MEDIA_OVERLAY_BD':  '#323242',
    'MEDIA_OVERLAY_FG':  '#f4f4f5',
    'MEDIA_CHIP_BG':     '#13131c',
    'MEDIA_CHIP_BD':     '#3d3d52',
    'MEDIA_CHIP_FG':     '#e4e4e7',
    'THUMB_BLANK_BG':    '#0d0d12',
    'CAPTION_HOVER_BG':  '#2a2a34',
    'PROGRESS_TROUGH':   '#262634',
    'PROGRESS_BAR':      '#0a84ff',

    # Sidebar Liquid Glass Tokens (Dark)
    'SIDEBAR_ITEM_IDLE_BG':   '#17171e',
    'SIDEBAR_ITEM_IDLE_BD':   '#17171e',
    'SIDEBAR_ITEM_IDLE_FG':   '#d4d4d8',
    'SIDEBAR_ITEM_IDLE_ICO':  '#9494a8',
    'SIDEBAR_ITEM_HOVER_BG':  '#22222d',
    'SIDEBAR_ITEM_HOVER_BD':  '#353548',
    'SIDEBAR_ITEM_HOVER_FG':  '#ffffff',
    'SIDEBAR_ITEM_HOVER_ICO': '#60a5fa',
    'SIDEBAR_ITEM_ACTIVE_BG': '#0e2540',
    'SIDEBAR_ITEM_ACTIVE_BD': '#2563eb',
    'SIDEBAR_ITEM_ACTIVE_FG': '#ffffff',
    'SIDEBAR_ITEM_ACTIVE_ICO':'#60a5fa',
    'SIDEBAR_ITEM_ACTIVE_IND':'#38bdf8',
    'SIDEBAR_BADGE_IDLE_BG':  '#1c1c28',
    'SIDEBAR_BADGE_IDLE_BD':  '#2d2d3e',
    'SIDEBAR_BADGE_IDLE_FG':  '#a1a1aa',
    'SIDEBAR_BADGE_ACTIVE_BG':'#1d4ed8',
    'SIDEBAR_BADGE_ACTIVE_BD':'#60a5fa',
    'SIDEBAR_BADGE_ACTIVE_FG':'#ffffff',
    'SIDEBAR_HDR_FG':         '#828296',
    'SIDEBAR_INPUT_BG':       '#151520',
    'SIDEBAR_INPUT_BD':       '#2d2d3e',
    'SIDEBAR_BACK_BG':        '#161622',
    'SIDEBAR_BACK_BD':        '#38384e',
    'SIDEBAR_BACK_FG':        '#d4d4d8',
    'SIDEBAR_BACK_HOVER_BG':  '#1e2a3a',
    'SIDEBAR_BACK_HOVER_BD':  '#2563eb',
    'SIDEBAR_BACK_HOVER_FG':  '#93c5fd',
    'SIDEBAR_LB_BG':          '#13131a',
    'SIDEBAR_LB_SEL_BG':      '#0e2540',
    'SIDEBAR_LB_SEL_FG':      '#ffffff',
}

LIGHT_PALETTE = {
    'WINDOW_BG':         '#f5f5f7',   # Frosted clean light acrylic background
    'SIDEBAR_BG':        '#f0f0f4',   # Crisp light gray left rail
    'SIDEBAR_DIVIDER':   '#e0e0e6',   # Subtle hairline divider
    'SIDEBAR_HOVER':     '#e5e5ed',   # Soft item hover
    'SIDEBAR_ACTIVE':    '#0070f3',   # Apple System Blue active pill
    'CONTENT_BG':        '#fafafa',   # Main canvas clean background
    'CARD_BG':           '#ffffff',   # Pure white elevated card
    'CARD_HOVER':        '#f7f7f9',   # Card hover surface
    'CARD_BORDER':       '#e6e6ee',   # 1px crisp border
    'CARD_BORDER_HOVER': '#cbd5e1',   # 1px border hover highlight
    'ELEVATED':          '#ffffff',   # Elevated glass surface
    'INK':               '#111827',   # High contrast crisp dark text
    'BODY':              '#4b5563',   # Readable neutral gray text
    'MUTE':              '#6b7280',   # Muted caption gray
    'FAINT':             '#9ca3af',   # Faint placeholder gray
    'HAIRLINE':          '#e5e7eb',   # Clean hairline separator
    'HAIRLINE_SOFT':     '#f3f4f6',   # Soft chip background
    'LINK':              '#0070f3',   # Apple System Blue
    'LINK_HOVER':        '#2563eb',   # Blue hover
    'LINK_DEEP':         '#1d4ed8',   # Blue pressed
    'LINK_SOFT':         '#dbeafe',   # Blue subtle tint
    'ERROR':             '#e11d48',   # Apple System Red
    'ERROR_DEEP':        '#be123c',   # Deep red
    'WARNING':           '#d97706',   # Amber
    'WARNING_DEEP':      '#b45309',   # Deep amber
    'SUCCESS':           '#16a34a',   # Apple System Green
    'ON_PRIMARY':        '#ffffff',   # White on primary
    'HOVER_SOFT':        '#f3f4f6',   # Soft hover
    'HOVER_TINT':        '#e5e7eb',   # Moderate hover
    'HOVER_DEEP':        '#d1d5db',   # Deep hover
    'BORDER_HOVER':      '#94a3b8',   # Border hover
    'SCROLLBAR':         '#cbd5e1',   # Scrollbar thumb
    'SCROLLBAR_ACTIVE':  '#94a3b8',   # Scrollbar active thumb
    'SEARCH_BG':         '#ffffff',   # Search capsule background
    'SEARCH_BORDER':     '#d1d5db',   # Search capsule border
    'SEARCH_FOCUS':      '#0070f3',   # Search capsule focus ring
    'CANVAS_BG':         '#fafafa',

    # Custom component accents
    'INPUT_BG':          '#ffffff',
    'INPUT_BORDER':      '#dcdce4',
    'INPUT_HOVER_BORDER':'#94a3b8',
    'INPUT_BOX_BG':      '#f4f4f7',
    'PILL_SEC_BG':       '#f3f4f6',
    'PILL_SEC_BORDER':   '#d1d5db',
    'PILL_SEC_FG':       '#374151',
    'PILL_SEC_HOVER_BG': '#e5e7eb',
    'PILL_SEC_HOVER_BD': '#9ca3af',
    'PILL_SEC_HOVER_FG': '#111827',
    'PILL_PRI_BG':       '#eff6ff',
    'PILL_PRI_BORDER':   '#bfdbfe',
    'PILL_PRI_FG':       '#1d4ed8',
    'PILL_PRI_HOVER_BG': '#2563eb',
    'PILL_PRI_HOVER_BD': '#1d4ed8',
    'PILL_PRI_HOVER_FG': '#ffffff',
    'PILL_SUC_BG':       '#f0fdf4',
    'PILL_SUC_BORDER':   '#bbf7d0',
    'PILL_SUC_FG':       '#15803d',
    'PILL_SUC_HOVER_BG': '#16a34a',
    'PILL_SUC_HOVER_BD': '#15803d',
    'PILL_SUC_HOVER_FG': '#ffffff',
    'SWITCH_OFF_BG':     '#e4e4e7',
    'SWITCH_OFF_BORDER': '#d4d4d8',
    'SWITCH_ON_BG':      '#0070f3',
    'SWITCH_ON_BORDER':  '#3b82f6',
    'SEG_CONTAINER_BG':  '#e8e8ee',
    'SEG_CONTAINER_BD':  '#d5d5de',
    'SEG_ACTIVE_BG':     '#ffffff',
    'SEG_ACTIVE_BD':     '#d1d5db',
    'SEG_ACTIVE_FG':     '#0070f3',
    'SEG_INACTIVE_BG':   '#e8e8ee',
    'SEG_INACTIVE_FG':   '#6b7280',
    'SEG_HOVER_BG':      '#f0f0f5',
    'SEG_HOVER_BD':      '#cbd5e1',
    'SEG_HOVER_FG':      '#111827',
    'POPUP_BG':          '#ffffff',
    'POPUP_BORDER':      '#dcdce4',
    'POPUP_HOVER_BG':    '#f4f4f7',
    'POPUP_HOVER_BD':    '#e2e8f0',
    'POPUP_ACTIVE_BG':   '#eff6ff',
    'POPUP_ACTIVE_BD':   '#bfdbfe',
    'POPUP_ACTIVE_FG':   '#1d4ed8',
    'MEDIA_OVERLAY_BG':  '#18181b',
    'MEDIA_OVERLAY_BD':  '#3f3f46',
    'MEDIA_OVERLAY_FG':  '#f4f4f5',
    'MEDIA_CHIP_BG':     '#27272a',
    'MEDIA_CHIP_BD':     '#3f3f46',
    'MEDIA_CHIP_FG':     '#f4f4f5',
    'THUMB_BLANK_BG':    '#e5e5ea',
    'CAPTION_HOVER_BG':  '#e2e8f0',
    'PROGRESS_TROUGH':   '#e5e7eb',
    'PROGRESS_BAR':      '#0070f3',

    # Sidebar Liquid Glass Tokens (Light)
    'SIDEBAR_ITEM_IDLE_BG':   '#f0f0f4',
    'SIDEBAR_ITEM_IDLE_BD':   '#f0f0f4',
    'SIDEBAR_ITEM_IDLE_FG':   '#374151',
    'SIDEBAR_ITEM_IDLE_ICO':  '#6b7280',
    'SIDEBAR_ITEM_HOVER_BG':  '#e5e7eb',
    'SIDEBAR_ITEM_HOVER_BD':  '#cbd5e1',
    'SIDEBAR_ITEM_HOVER_FG':  '#111827',
    'SIDEBAR_ITEM_HOVER_ICO': '#2563eb',
    'SIDEBAR_ITEM_ACTIVE_BG': '#eff6ff',
    'SIDEBAR_ITEM_ACTIVE_BD': '#3b82f6',
    'SIDEBAR_ITEM_ACTIVE_FG': '#1d4ed8',
    'SIDEBAR_ITEM_ACTIVE_ICO':'#2563eb',
    'SIDEBAR_ITEM_ACTIVE_IND':'#2563eb',
    'SIDEBAR_BADGE_IDLE_BG':  '#e5e7eb',
    'SIDEBAR_BADGE_IDLE_BD':  '#d1d5db',
    'SIDEBAR_BADGE_IDLE_FG':  '#4b5563',
    'SIDEBAR_BADGE_ACTIVE_BG':'#dbeafe',
    'SIDEBAR_BADGE_ACTIVE_BD':'#93c5fd',
    'SIDEBAR_BADGE_ACTIVE_FG':'#1d4ed8',
    'SIDEBAR_HDR_FG':         '#6b7280',
    'SIDEBAR_INPUT_BG':       '#ffffff',
    'SIDEBAR_INPUT_BD':       '#d1d5db',
    'SIDEBAR_BACK_BG':        '#ffffff',
    'SIDEBAR_BACK_BD':        '#d1d5db',
    'SIDEBAR_BACK_FG':        '#374151',
    'SIDEBAR_BACK_HOVER_BG':  '#eff6ff',
    'SIDEBAR_BACK_HOVER_BD':  '#2563eb',
    'SIDEBAR_BACK_HOVER_FG':  '#1d4ed8',
    'SIDEBAR_LB_BG':          '#f0f0f4',
    'SIDEBAR_LB_SEL_BG':      '#eff6ff',
    'SIDEBAR_LB_SEL_FG':      '#1d4ed8',
}

CURRENT_PALETTE = dict(DARK_PALETTE)

WINDOW_BG         = CURRENT_PALETTE['WINDOW_BG']
SIDEBAR_BG        = CURRENT_PALETTE['SIDEBAR_BG']
SIDEBAR_DIVIDER   = CURRENT_PALETTE['SIDEBAR_DIVIDER']
SIDEBAR_HOVER     = CURRENT_PALETTE['SIDEBAR_HOVER']
SIDEBAR_ACTIVE    = CURRENT_PALETTE['SIDEBAR_ACTIVE']
CONTENT_BG        = CURRENT_PALETTE['CONTENT_BG']
CARD_BG           = CURRENT_PALETTE['CARD_BG']
CARD_HOVER        = CURRENT_PALETTE['CARD_HOVER']
CARD_BORDER       = CURRENT_PALETTE['CARD_BORDER']
CARD_BORDER_HOVER = CURRENT_PALETTE['CARD_BORDER_HOVER']
ELEVATED          = CURRENT_PALETTE['ELEVATED']
INK               = CURRENT_PALETTE['INK']
BODY              = CURRENT_PALETTE['BODY']
MUTE              = CURRENT_PALETTE['MUTE']
FAINT             = CURRENT_PALETTE['FAINT']
HAIRLINE          = CURRENT_PALETTE['HAIRLINE']
HAIRLINE_SOFT     = CURRENT_PALETTE['HAIRLINE_SOFT']
LINK              = CURRENT_PALETTE['LINK']
LINK_HOVER        = CURRENT_PALETTE['LINK_HOVER']
LINK_DEEP         = CURRENT_PALETTE['LINK_DEEP']
LINK_SOFT         = CURRENT_PALETTE['LINK_SOFT']
ERROR             = CURRENT_PALETTE['ERROR']
ERROR_DEEP        = CURRENT_PALETTE['ERROR_DEEP']
WARNING           = CURRENT_PALETTE['WARNING']
WARNING_DEEP      = CURRENT_PALETTE['WARNING_DEEP']
SUCCESS           = CURRENT_PALETTE['SUCCESS']
ON_PRIMARY        = CURRENT_PALETTE['ON_PRIMARY']
HOVER_SOFT        = CURRENT_PALETTE['HOVER_SOFT']
HOVER_TINT        = CURRENT_PALETTE['HOVER_TINT']
HOVER_DEEP        = CURRENT_PALETTE['HOVER_DEEP']
BORDER_HOVER      = CURRENT_PALETTE['BORDER_HOVER']
SCROLLBAR         = CURRENT_PALETTE['SCROLLBAR']
SCROLLBAR_ACTIVE  = CURRENT_PALETTE['SCROLLBAR_ACTIVE']
SEARCH_BG         = CURRENT_PALETTE['SEARCH_BG']
SEARCH_BORDER     = CURRENT_PALETTE['SEARCH_BORDER']
SEARCH_FOCUS      = CURRENT_PALETTE['SEARCH_FOCUS']
CANVAS_BG         = CURRENT_PALETTE['CANVAS_BG']
PROGRESS_TROUGH   = CURRENT_PALETTE.get('PROGRESS_TROUGH', '#262634')
PROGRESS_BAR      = CURRENT_PALETTE.get('PROGRESS_BAR', '#0a84ff')

INPUT_BG          = CURRENT_PALETTE['INPUT_BG']
INPUT_BORDER      = CURRENT_PALETTE['INPUT_BORDER']
INPUT_HOVER_BORDER= CURRENT_PALETTE['INPUT_HOVER_BORDER']
INPUT_BOX_BG      = CURRENT_PALETTE['INPUT_BOX_BG']
PILL_SEC_BG       = CURRENT_PALETTE['PILL_SEC_BG']
PILL_SEC_BORDER   = CURRENT_PALETTE['PILL_SEC_BORDER']
PILL_SEC_FG       = CURRENT_PALETTE['PILL_SEC_FG']
PILL_SEC_HOVER_BG = CURRENT_PALETTE['PILL_SEC_HOVER_BG']
PILL_SEC_HOVER_BD = CURRENT_PALETTE['PILL_SEC_HOVER_BD']
PILL_SEC_HOVER_FG = CURRENT_PALETTE['PILL_SEC_HOVER_FG']
PILL_PRI_BG       = CURRENT_PALETTE['PILL_PRI_BG']
PILL_PRI_BORDER   = CURRENT_PALETTE['PILL_PRI_BORDER']
PILL_PRI_FG       = CURRENT_PALETTE['PILL_PRI_FG']
PILL_PRI_HOVER_BG = CURRENT_PALETTE['PILL_PRI_HOVER_BG']
PILL_PRI_HOVER_BD = CURRENT_PALETTE['PILL_PRI_HOVER_BD']
PILL_PRI_HOVER_FG = CURRENT_PALETTE['PILL_PRI_HOVER_FG']
PILL_SUC_BG       = CURRENT_PALETTE['PILL_SUC_BG']
PILL_SUC_BORDER   = CURRENT_PALETTE['PILL_SUC_BORDER']
PILL_SUC_FG       = CURRENT_PALETTE['PILL_SUC_FG']
PILL_SUC_HOVER_BG = CURRENT_PALETTE['PILL_SUC_HOVER_BG']
PILL_SUC_HOVER_BD = CURRENT_PALETTE['PILL_SUC_HOVER_BD']
PILL_SUC_HOVER_FG = CURRENT_PALETTE['PILL_SUC_HOVER_FG']
SWITCH_OFF_BG     = CURRENT_PALETTE['SWITCH_OFF_BG']
SWITCH_OFF_BORDER = CURRENT_PALETTE['SWITCH_OFF_BORDER']
SWITCH_ON_BG      = CURRENT_PALETTE['SWITCH_ON_BG']
SWITCH_ON_BORDER  = CURRENT_PALETTE['SWITCH_ON_BORDER']
SEG_CONTAINER_BG  = CURRENT_PALETTE['SEG_CONTAINER_BG']
SEG_CONTAINER_BD  = CURRENT_PALETTE['SEG_CONTAINER_BD']
SEG_ACTIVE_BG     = CURRENT_PALETTE['SEG_ACTIVE_BG']
SEG_ACTIVE_BD     = CURRENT_PALETTE['SEG_ACTIVE_BD']
SEG_ACTIVE_FG     = CURRENT_PALETTE['SEG_ACTIVE_FG']
SEG_INACTIVE_BG   = CURRENT_PALETTE['SEG_INACTIVE_BG']
SEG_INACTIVE_FG   = CURRENT_PALETTE['SEG_INACTIVE_FG']
SEG_HOVER_BG      = CURRENT_PALETTE['SEG_HOVER_BG']
SEG_HOVER_BD      = CURRENT_PALETTE['SEG_HOVER_BD']
SEG_HOVER_FG      = CURRENT_PALETTE['SEG_HOVER_FG']
POPUP_BG          = CURRENT_PALETTE['POPUP_BG']
POPUP_BORDER      = CURRENT_PALETTE['POPUP_BORDER']
POPUP_HOVER_BG    = CURRENT_PALETTE['POPUP_HOVER_BG']
POPUP_HOVER_BD    = CURRENT_PALETTE['POPUP_HOVER_BD']
POPUP_ACTIVE_BG   = CURRENT_PALETTE['POPUP_ACTIVE_BG']
POPUP_ACTIVE_BD   = CURRENT_PALETTE['POPUP_ACTIVE_BD']
POPUP_ACTIVE_FG   = CURRENT_PALETTE['POPUP_ACTIVE_FG']
MEDIA_OVERLAY_BG  = CURRENT_PALETTE['MEDIA_OVERLAY_BG']
MEDIA_OVERLAY_BD  = CURRENT_PALETTE['MEDIA_OVERLAY_BD']
MEDIA_OVERLAY_FG  = CURRENT_PALETTE['MEDIA_OVERLAY_FG']
MEDIA_CHIP_BG     = CURRENT_PALETTE['MEDIA_CHIP_BG']
MEDIA_CHIP_BD     = CURRENT_PALETTE['MEDIA_CHIP_BD']
MEDIA_CHIP_FG     = CURRENT_PALETTE['MEDIA_CHIP_FG']
THUMB_BLANK_BG    = CURRENT_PALETTE['THUMB_BLANK_BG']
CAPTION_HOVER_BG  = CURRENT_PALETTE['CAPTION_HOVER_BG']

SIDEBAR_ITEM_IDLE_BG   = CURRENT_PALETTE['SIDEBAR_ITEM_IDLE_BG']
SIDEBAR_ITEM_IDLE_BD   = CURRENT_PALETTE['SIDEBAR_ITEM_IDLE_BD']
SIDEBAR_ITEM_IDLE_FG   = CURRENT_PALETTE['SIDEBAR_ITEM_IDLE_FG']
SIDEBAR_ITEM_IDLE_ICO  = CURRENT_PALETTE['SIDEBAR_ITEM_IDLE_ICO']
SIDEBAR_ITEM_HOVER_BG  = CURRENT_PALETTE['SIDEBAR_ITEM_HOVER_BG']
SIDEBAR_ITEM_HOVER_BD  = CURRENT_PALETTE['SIDEBAR_ITEM_HOVER_BD']
SIDEBAR_ITEM_HOVER_FG  = CURRENT_PALETTE['SIDEBAR_ITEM_HOVER_FG']
SIDEBAR_ITEM_HOVER_ICO = CURRENT_PALETTE['SIDEBAR_ITEM_HOVER_ICO']
SIDEBAR_ITEM_ACTIVE_BG = CURRENT_PALETTE['SIDEBAR_ITEM_ACTIVE_BG']
SIDEBAR_ITEM_ACTIVE_BD = CURRENT_PALETTE['SIDEBAR_ITEM_ACTIVE_BD']
SIDEBAR_ITEM_ACTIVE_FG = CURRENT_PALETTE['SIDEBAR_ITEM_ACTIVE_FG']
SIDEBAR_ITEM_ACTIVE_ICO= CURRENT_PALETTE['SIDEBAR_ITEM_ACTIVE_ICO']
SIDEBAR_ITEM_ACTIVE_IND= CURRENT_PALETTE['SIDEBAR_ITEM_ACTIVE_IND']
SIDEBAR_BADGE_IDLE_BG  = CURRENT_PALETTE['SIDEBAR_BADGE_IDLE_BG']
SIDEBAR_BADGE_IDLE_BD  = CURRENT_PALETTE['SIDEBAR_BADGE_IDLE_BD']
SIDEBAR_BADGE_IDLE_FG  = CURRENT_PALETTE['SIDEBAR_BADGE_IDLE_FG']
SIDEBAR_BADGE_ACTIVE_BG= CURRENT_PALETTE['SIDEBAR_BADGE_ACTIVE_BG']
SIDEBAR_BADGE_ACTIVE_BD= CURRENT_PALETTE['SIDEBAR_BADGE_ACTIVE_BD']
SIDEBAR_BADGE_ACTIVE_FG= CURRENT_PALETTE['SIDEBAR_BADGE_ACTIVE_FG']
SIDEBAR_HDR_FG         = CURRENT_PALETTE['SIDEBAR_HDR_FG']
SIDEBAR_INPUT_BG       = CURRENT_PALETTE['SIDEBAR_INPUT_BG']
SIDEBAR_INPUT_BD       = CURRENT_PALETTE['SIDEBAR_INPUT_BD']
SIDEBAR_BACK_BG        = CURRENT_PALETTE['SIDEBAR_BACK_BG']
SIDEBAR_BACK_BD        = CURRENT_PALETTE['SIDEBAR_BACK_BD']
SIDEBAR_BACK_FG        = CURRENT_PALETTE['SIDEBAR_BACK_FG']
SIDEBAR_BACK_HOVER_BG  = CURRENT_PALETTE['SIDEBAR_BACK_HOVER_BG']
SIDEBAR_BACK_HOVER_BD  = CURRENT_PALETTE['SIDEBAR_BACK_HOVER_BD']
SIDEBAR_BACK_HOVER_FG  = CURRENT_PALETTE['SIDEBAR_BACK_HOVER_FG']
SIDEBAR_LB_BG          = CURRENT_PALETTE['SIDEBAR_LB_BG']
SIDEBAR_LB_SEL_BG      = CURRENT_PALETTE['SIDEBAR_LB_SEL_BG']
SIDEBAR_LB_SEL_FG      = CURRENT_PALETTE['SIDEBAR_LB_SEL_FG']


def is_system_dark_mode():
    """Detects whether Windows OS is currently using Dark Mode."""
    if sys.platform == 'win32':
        try:
            import winreg
            key_path = r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                val, _ = winreg.QueryValueEx(key, 'AppsUseLightTheme')
                return val == 0
        except Exception:
            pass
    return True


def get_effective_theme(theme_pref=None):
    """Resolves 'system' | 'dark' | 'light' into concrete 'dark' or 'light'."""
    if theme_pref is None:
        try:
            theme_pref = config.get_theme()
        except Exception:
            theme_pref = 'dark'
    theme_pref = str(theme_pref or 'dark').lower().strip()
    if theme_pref == 'system':
        return 'dark' if is_system_dark_mode() else 'light'
    elif theme_pref == 'light':
        return 'light'
    return 'dark'


def apply_global_palette(mode='dark'):
    """Updates the global color constants to match the specified theme ('dark' | 'light')."""
    palette = LIGHT_PALETTE if str(mode).lower() == 'light' else DARK_PALETTE
    CURRENT_PALETTE.clear()
    CURRENT_PALETTE.update(palette)
    global WINDOW_BG, SIDEBAR_BG, SIDEBAR_DIVIDER, SIDEBAR_HOVER, SIDEBAR_ACTIVE
    global CONTENT_BG, CARD_BG, CARD_HOVER, CARD_BORDER, CARD_BORDER_HOVER
    global ELEVATED, INK, BODY, MUTE, FAINT, HAIRLINE, HAIRLINE_SOFT
    global LINK, LINK_HOVER, LINK_DEEP, LINK_SOFT, ERROR, ERROR_DEEP
    global WARNING, WARNING_DEEP, SUCCESS, ON_PRIMARY, HOVER_SOFT, HOVER_TINT
    global HOVER_DEEP, BORDER_HOVER, SCROLLBAR, SCROLLBAR_ACTIVE, SEARCH_BG
    global SEARCH_BORDER, SEARCH_FOCUS, CANVAS_BG
    global PROGRESS_TROUGH, PROGRESS_BAR
    global INPUT_BG, INPUT_BORDER, INPUT_HOVER_BORDER, INPUT_BOX_BG
    global PILL_SEC_BG, PILL_SEC_BORDER, PILL_SEC_FG, PILL_SEC_HOVER_BG, PILL_SEC_HOVER_BD, PILL_SEC_HOVER_FG
    global PILL_PRI_BG, PILL_PRI_BORDER, PILL_PRI_FG, PILL_PRI_HOVER_BG, PILL_PRI_HOVER_BD, PILL_PRI_HOVER_FG
    global PILL_SUC_BG, PILL_SUC_BORDER, PILL_SUC_FG, PILL_SUC_HOVER_BG, PILL_SUC_HOVER_BD, PILL_SUC_HOVER_FG
    global SWITCH_OFF_BG, SWITCH_OFF_BORDER, SWITCH_ON_BG, SWITCH_ON_BORDER
    global SEG_CONTAINER_BG, SEG_CONTAINER_BD, SEG_ACTIVE_BG, SEG_ACTIVE_BD, SEG_ACTIVE_FG
    global SEG_INACTIVE_BG, SEG_INACTIVE_FG, SEG_HOVER_BG, SEG_HOVER_BD, SEG_HOVER_FG
    global POPUP_BG, POPUP_BORDER, POPUP_HOVER_BG, POPUP_HOVER_BD, POPUP_ACTIVE_BG, POPUP_ACTIVE_BD, POPUP_ACTIVE_FG
    global MEDIA_OVERLAY_BG, MEDIA_OVERLAY_BD, MEDIA_OVERLAY_FG
    global MEDIA_CHIP_BG, MEDIA_CHIP_BD, MEDIA_CHIP_FG
    global THUMB_BLANK_BG, CAPTION_HOVER_BG

    global SIDEBAR_ITEM_IDLE_BG, SIDEBAR_ITEM_IDLE_BD, SIDEBAR_ITEM_IDLE_FG, SIDEBAR_ITEM_IDLE_ICO
    global SIDEBAR_ITEM_HOVER_BG, SIDEBAR_ITEM_HOVER_BD, SIDEBAR_ITEM_HOVER_FG, SIDEBAR_ITEM_HOVER_ICO
    global SIDEBAR_ITEM_ACTIVE_BG, SIDEBAR_ITEM_ACTIVE_BD, SIDEBAR_ITEM_ACTIVE_FG, SIDEBAR_ITEM_ACTIVE_ICO, SIDEBAR_ITEM_ACTIVE_IND
    global SIDEBAR_BADGE_IDLE_BG, SIDEBAR_BADGE_IDLE_BD, SIDEBAR_BADGE_IDLE_FG
    global SIDEBAR_BADGE_ACTIVE_BG, SIDEBAR_BADGE_ACTIVE_BD, SIDEBAR_BADGE_ACTIVE_FG
    global SIDEBAR_HDR_FG, SIDEBAR_INPUT_BG, SIDEBAR_INPUT_BD, SIDEBAR_BACK_BG, SIDEBAR_BACK_BD, SIDEBAR_BACK_FG
    global SIDEBAR_BACK_HOVER_BG, SIDEBAR_BACK_HOVER_BD, SIDEBAR_BACK_HOVER_FG, SIDEBAR_LB_BG, SIDEBAR_LB_SEL_BG, SIDEBAR_LB_SEL_FG

    WINDOW_BG         = palette['WINDOW_BG']
    SIDEBAR_BG        = palette['SIDEBAR_BG']
    SIDEBAR_DIVIDER   = palette['SIDEBAR_DIVIDER']
    SIDEBAR_HOVER     = palette['SIDEBAR_HOVER']
    SIDEBAR_ACTIVE    = palette['SIDEBAR_ACTIVE']
    CONTENT_BG        = palette['CONTENT_BG']
    CARD_BG           = palette['CARD_BG']
    CARD_HOVER        = palette['CARD_HOVER']
    CARD_BORDER       = palette['CARD_BORDER']
    CARD_BORDER_HOVER = palette['CARD_BORDER_HOVER']
    ELEVATED          = palette['ELEVATED']
    INK               = palette['INK']
    BODY              = palette['BODY']
    MUTE              = palette['MUTE']
    FAINT             = palette['FAINT']
    HAIRLINE          = palette['HAIRLINE']
    HAIRLINE_SOFT     = palette['HAIRLINE_SOFT']
    LINK              = palette['LINK']
    LINK_HOVER        = palette['LINK_HOVER']
    LINK_DEEP         = palette['LINK_DEEP']
    LINK_SOFT         = palette['LINK_SOFT']
    ERROR             = palette['ERROR']
    ERROR_DEEP        = palette['ERROR_DEEP']
    WARNING           = palette['WARNING']
    WARNING_DEEP      = palette['WARNING_DEEP']
    SUCCESS           = palette['SUCCESS']
    ON_PRIMARY        = palette['ON_PRIMARY']
    HOVER_SOFT        = palette['HOVER_SOFT']
    HOVER_TINT        = palette['HOVER_TINT']
    HOVER_DEEP        = palette['HOVER_DEEP']
    BORDER_HOVER      = palette['BORDER_HOVER']
    SCROLLBAR         = palette['SCROLLBAR']
    SCROLLBAR_ACTIVE  = palette['SCROLLBAR_ACTIVE']
    SEARCH_BG         = palette['SEARCH_BG']
    SEARCH_BORDER     = palette['SEARCH_BORDER']
    SEARCH_FOCUS      = palette['SEARCH_FOCUS']
    CANVAS_BG         = palette['CANVAS_BG']

    INPUT_BG          = palette['INPUT_BG']
    INPUT_BORDER      = palette['INPUT_BORDER']
    INPUT_HOVER_BORDER= palette['INPUT_HOVER_BORDER']
    INPUT_BOX_BG      = palette['INPUT_BOX_BG']
    PILL_SEC_BG       = palette['PILL_SEC_BG']
    PILL_SEC_BORDER   = palette['PILL_SEC_BORDER']
    PILL_SEC_FG       = palette['PILL_SEC_FG']
    PILL_SEC_HOVER_BG = palette['PILL_SEC_HOVER_BG']
    PILL_SEC_HOVER_BD = palette['PILL_SEC_HOVER_BD']
    PILL_SEC_HOVER_FG = palette['PILL_SEC_HOVER_FG']
    PILL_PRI_BG       = palette['PILL_PRI_BG']
    PILL_PRI_BORDER   = palette['PILL_PRI_BORDER']
    PILL_PRI_FG       = palette['PILL_PRI_FG']
    PILL_PRI_HOVER_BG = palette['PILL_PRI_HOVER_BG']
    PILL_PRI_HOVER_BD = palette['PILL_PRI_HOVER_BD']
    PILL_PRI_HOVER_FG = palette['PILL_PRI_HOVER_FG']
    PILL_SUC_BG       = palette['PILL_SUC_BG']
    PILL_SUC_BORDER   = palette['PILL_SUC_BORDER']
    PILL_SUC_FG       = palette['PILL_SUC_FG']
    PILL_SUC_HOVER_BG = palette['PILL_SUC_HOVER_BG']
    PILL_SUC_HOVER_BD = palette['PILL_SUC_HOVER_BD']
    PILL_SUC_HOVER_FG = palette['PILL_SUC_HOVER_FG']
    SWITCH_OFF_BG     = palette['SWITCH_OFF_BG']
    SWITCH_OFF_BORDER = palette['SWITCH_OFF_BORDER']
    SWITCH_ON_BG      = palette['SWITCH_ON_BG']
    SWITCH_ON_BORDER  = palette['SWITCH_ON_BORDER']
    SEG_CONTAINER_BG  = palette['SEG_CONTAINER_BG']
    SEG_CONTAINER_BD  = palette['SEG_CONTAINER_BD']
    SEG_ACTIVE_BG     = palette['SEG_ACTIVE_BG']
    SEG_ACTIVE_BD     = palette['SEG_ACTIVE_BD']
    SEG_ACTIVE_FG     = palette['SEG_ACTIVE_FG']
    SEG_INACTIVE_BG   = palette['SEG_INACTIVE_BG']
    SEG_INACTIVE_FG   = palette['SEG_INACTIVE_FG']
    SEG_HOVER_BG      = palette['SEG_HOVER_BG']
    SEG_HOVER_BD      = palette['SEG_HOVER_BD']
    SEG_HOVER_FG      = palette['SEG_HOVER_FG']
    POPUP_BG          = palette['POPUP_BG']
    POPUP_BORDER      = palette['POPUP_BORDER']
    POPUP_HOVER_BG    = palette['POPUP_HOVER_BG']
    POPUP_HOVER_BD    = palette['POPUP_HOVER_BD']
    POPUP_ACTIVE_BG   = palette['POPUP_ACTIVE_BG']
    POPUP_ACTIVE_BD   = palette['POPUP_ACTIVE_BD']
    POPUP_ACTIVE_FG   = palette['POPUP_ACTIVE_FG']
    MEDIA_OVERLAY_BG  = palette['MEDIA_OVERLAY_BG']
    MEDIA_OVERLAY_BD  = palette['MEDIA_OVERLAY_BD']
    MEDIA_OVERLAY_FG  = palette['MEDIA_OVERLAY_FG']
    MEDIA_CHIP_BG     = palette['MEDIA_CHIP_BG']
    MEDIA_CHIP_BD     = palette['MEDIA_CHIP_BD']
    MEDIA_CHIP_FG     = palette['MEDIA_CHIP_FG']
    THUMB_BLANK_BG    = palette['THUMB_BLANK_BG']
    CAPTION_HOVER_BG  = palette['CAPTION_HOVER_BG']

    SIDEBAR_ITEM_IDLE_BG   = palette['SIDEBAR_ITEM_IDLE_BG']
    SIDEBAR_ITEM_IDLE_BD   = palette['SIDEBAR_ITEM_IDLE_BD']
    SIDEBAR_ITEM_IDLE_FG   = palette['SIDEBAR_ITEM_IDLE_FG']
    SIDEBAR_ITEM_IDLE_ICO  = palette['SIDEBAR_ITEM_IDLE_ICO']
    SIDEBAR_ITEM_HOVER_BG  = palette['SIDEBAR_ITEM_HOVER_BG']
    SIDEBAR_ITEM_HOVER_BD  = palette['SIDEBAR_ITEM_HOVER_BD']
    SIDEBAR_ITEM_HOVER_FG  = palette['SIDEBAR_ITEM_HOVER_FG']
    SIDEBAR_ITEM_HOVER_ICO = palette['SIDEBAR_ITEM_HOVER_ICO']
    SIDEBAR_ITEM_ACTIVE_BG = palette['SIDEBAR_ITEM_ACTIVE_BG']
    SIDEBAR_ITEM_ACTIVE_BD = palette['SIDEBAR_ITEM_ACTIVE_BD']
    SIDEBAR_ITEM_ACTIVE_FG = palette['SIDEBAR_ITEM_ACTIVE_FG']
    SIDEBAR_ITEM_ACTIVE_ICO= palette['SIDEBAR_ITEM_ACTIVE_ICO']
    SIDEBAR_ITEM_ACTIVE_IND= palette['SIDEBAR_ITEM_ACTIVE_IND']
    SIDEBAR_BADGE_IDLE_BG  = palette['SIDEBAR_BADGE_IDLE_BG']
    SIDEBAR_BADGE_IDLE_BD  = palette['SIDEBAR_BADGE_IDLE_BD']
    SIDEBAR_BADGE_IDLE_FG  = palette['SIDEBAR_BADGE_IDLE_FG']
    SIDEBAR_BADGE_ACTIVE_BG= palette['SIDEBAR_BADGE_ACTIVE_BG']
    SIDEBAR_BADGE_ACTIVE_BD= palette['SIDEBAR_BADGE_ACTIVE_BD']
    SIDEBAR_BADGE_ACTIVE_FG= palette['SIDEBAR_BADGE_ACTIVE_FG']
    SIDEBAR_HDR_FG         = palette['SIDEBAR_HDR_FG']
    SIDEBAR_INPUT_BG       = palette['SIDEBAR_INPUT_BG']
    SIDEBAR_INPUT_BD       = palette['SIDEBAR_INPUT_BD']
    SIDEBAR_BACK_BG        = palette['SIDEBAR_BACK_BG']
    SIDEBAR_BACK_BD        = palette['SIDEBAR_BACK_BD']
    SIDEBAR_BACK_FG        = palette['SIDEBAR_BACK_FG']
    SIDEBAR_BACK_HOVER_BG  = palette['SIDEBAR_BACK_HOVER_BG']
    SIDEBAR_BACK_HOVER_BD  = palette['SIDEBAR_BACK_HOVER_BD']
    SIDEBAR_BACK_HOVER_FG  = palette['SIDEBAR_BACK_HOVER_FG']
    SIDEBAR_LB_BG          = palette['SIDEBAR_LB_BG']
    SIDEBAR_LB_SEL_BG      = palette['SIDEBAR_LB_SEL_BG']
    SIDEBAR_LB_SEL_FG      = palette['SIDEBAR_LB_SEL_FG']

    PROGRESS_TROUGH        = palette.get('PROGRESS_TROUGH', '#262634' if str(mode).lower() == 'dark' else '#e5e7eb')
    PROGRESS_BAR           = palette.get('PROGRESS_BAR', LINK)

    if 'JobRow' in globals() and hasattr(globals()['JobRow'], 'STATE_FG'):
        globals()['JobRow'].STATE_FG = {
            'done': SUCCESS,
            'ready': LINK,
            'blocked': WARNING_DEEP,
            'error': ERROR,
            'cancelled': WARNING,
            'queued': FAINT,
            'resolving': BODY,
            'downloading': LINK,
        }


def _thumb_path(url):
    return re.sub(r'^https?://[^/]+', '', str(url or '').split('?', 1)[0])


def _dur_seconds(text):
    parts = str(text or '').strip().split(':')
    if not parts or not parts[0]:
        return None
    try:
        vals = [int(p) for p in parts]
    except ValueError:
        return None
    secs = 0
    for v in vals:
        secs = secs * 60 + v
    return secs


def _dup_key(item):
    path = _thumb_path(item.get('thumbnail'))
    secs = _dur_seconds(item.get('duration'))
    if not path or secs is None or secs <= 0:
        return None
    return (path, secs)


_FAST_SITE_RANK = {'FreePornVideos': 0, 'OnePorn': 0, 'TnaFlix': 0, 'Beeg': 1}


def _site_rank(item):
    name = str(item.get('site_name') or '')
    return (_FAST_SITE_RANK.get(name, 2), name)


def _interleave(items):
    buckets = {}
    for it in items:
        buckets.setdefault(it.get('site_name') or '?', []).append(it)
    queues = [buckets[k] for k in sorted(buckets)]
    out = []
    while queues:
        nxt = []
        for q in queues:
            if q:
                out.append(q.pop(0))
                nxt.append(q)
        queues = nxt
    return out


def fmt_bytes(n):
    for unit in ('B', 'KB', 'MB', 'GB'):
        if n < 1024 or unit == 'GB':
            return f'{n:.0f} {unit}' if unit == 'B' else f'{n:.1f} {unit}'
        n /= 1024


def pick_site_class(url):
    url = (url or '').strip()
    if not url:
        return None
    if SiteBeeg.validate_url(url):
        return SiteBeeg
    if SiteFreePornVideos.validate_url(url):
        return SiteFreePornVideos
    if SiteOnePornTV.validate_url(url):
        return SiteOnePornTV
    try:
        from M3U8Sites import VaildateUrl
        site = VaildateUrl(url)
        if site is not None:
            return site
    except Exception:
        pass
    return None


if sys.platform == 'win32':
    try:
        if sys.stdout is not None and hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(errors='replace')
        if sys.stderr is not None and hasattr(sys.stderr, 'reconfigure'):
            sys.stderr.reconfigure(errors='replace')
    except Exception:
        pass


def _register_all_fonts():
    """Registers bundled SF Pro font files so tkinter can resolve the families."""
    if sys.platform != 'win32':
        return
    base = getattr(sys, '_MEIPASS', None) or os.path.dirname(os.path.abspath(__file__))
    font_dir = os.path.join(base, 'assets', 'fonts', 'SF Pro')
    if not os.path.isdir(font_dir):
        font_dir = os.path.join(base, 'assets', 'fonts')
        if not os.path.isdir(font_dir):
            return
    used = ('SF-Pro-Display-Regular.otf', 'SF-Pro-Display-Bold.otf',
            'SF-Pro-Text-Regular.otf', 'SF-Pro-Text-Bold.otf')
    for name in used:
        p = os.path.join(font_dir, name)
        if os.path.isfile(p):
            try:
                ctypes.windll.gdi32.AddFontResourceExW(os.path.abspath(p), 0x10, 0)
            except Exception:
                pass


_register_all_fonts()


# ==============================================================================
# Heroicons Vector Engine (Razor Sharp 4x Supersampling with Lanczos Filter)
# ==============================================================================

_ICON_CACHE = {}


def get_heroicon(kind, size=22, color=INK, stroke_width=1.75):
    """
    Renders an authentic 24x24 Heroicon (from https://heroicons.com/) at 4x supersampling
    and scales down with Lanczos resampling for razor-sharp rendering on High-DPI screens.
    """
    key = (kind, size, color, stroke_width)
    cached = _ICON_CACHE.get(key)
    if cached is not None:
        try:
            cached.tk.call('image', 'type', cached._PhotoImage__photo.name)
            return cached
        except Exception:
            _ICON_CACHE.pop(key, None)

    scale = 4
    canvas_size = size * scale
    img = Image.new('RGBA', (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    s = canvas_size / 24.0
    sw = max(1.0, stroke_width * s)

    def pt(x, y):
        return (x * s, y * s)

    def draw_lines(points, width=sw, close=False):
        pts = [pt(x, y) for x, y in points]
        if close and pts[0] != pts[-1]:
            pts.append(pts[0])
        for i in range(len(pts) - 1):
            draw.line([pts[i], pts[i+1]], fill=color, width=int(round(width)), joint='curve')
            r = width / 2.0
            draw.ellipse([pts[i][0]-r, pts[i][1]-r, pts[i][0]+r, pts[i][1]+r], fill=color)
        r = width / 2.0
        draw.ellipse([pts[-1][0]-r, pts[-1][1]-r, pts[-1][0]+r, pts[-1][1]+r], fill=color)

    def draw_circle(cx, cy, r, fill=None, outline=None, width=sw):
        x0, y0 = pt(cx - r, cy - r)
        x1, y1 = pt(cx + r, cy + r)
        draw.ellipse([x0, y0, x1, y1], fill=fill, outline=outline, width=int(round(width)) if outline else 0)

    def draw_polygon(points, fill=color):
        pts = [pt(x, y) for x, y in points]
        draw.polygon(pts, fill=fill)

    # Heroicons 24x24 geometry
    if kind in ('browse', 'grid', 'squares_2x2'):
        r = 1.2
        for bx, by in [(3.5, 3.5), (13.5, 3.5), (3.5, 13.5), (13.5, 13.5)]:
            draw_lines([(bx+r, by), (bx+7-r, by), (bx+7, by+r), (bx+7, by+7-r),
                        (bx+7-r, by+7), (bx+r, by+7), (bx, by+7-r), (bx, by+r), (bx+r, by)], close=True)
    elif kind in ('download', 'downloads', 'arrow_down_tray'):
        draw_lines([(12, 3.5), (12, 15.5)])
        draw_lines([(7.5, 11), (12, 15.5), (16.5, 11)])
        draw_lines([(3.5, 16), (3.5, 19.5), (5.5, 20.5), (18.5, 20.5), (20.5, 19.5), (20.5, 16)])
    elif kind in ('history', 'clock'):
        draw_circle(12, 12, 8.5, outline=color, width=sw)
        draw_lines([(12, 7.5), (12, 12), (15.5, 14)])
    elif kind in ('settings', 'gear', 'cog_6_tooth'):
        draw_circle(12, 12, 3.2, outline=color, width=sw)
        draw_circle(12, 12, 7.8, outline=color, width=sw)
        for ang in range(0, 360, 60):
            rad = math.radians(ang)
            x1, y1 = 12 + 7.8 * math.cos(rad), 12 + 7.8 * math.sin(rad)
            x2, y2 = 12 + 9.8 * math.cos(rad), 12 + 9.8 * math.sin(rad)
            draw_lines([(x1, y1), (x2, y2)], width=sw * 1.3)
    elif kind in ('share', 'share_2', 'arrow_up_tray'):
        draw_circle(18, 5, 2.8, outline=color, width=sw)
        draw_circle(6, 12, 2.8, outline=color, width=sw)
        draw_circle(18, 19, 2.8, outline=color, width=sw)
        draw_lines([(8.5, 10.5), (15.5, 6.5)])
        draw_lines([(8.5, 13.5), (15.5, 17.5)])
    elif kind in ('star', 'watchlist', 'star_outline'):
        pts = [
            (12, 2.8), (14.8, 8.5), (21, 9.4), (16.5, 13.8), (17.6, 20),
            (12, 17.1), (6.4, 20), (7.5, 13.8), (3, 9.4), (9.2, 8.5)
        ]
        draw_lines(pts, close=True, width=sw)
    elif kind in ('star_fill', 'star_solid', 'starred'):
        pts = [
            (12, 2.8), (14.8, 8.5), (21, 9.4), (16.5, 13.8), (17.6, 20),
            (12, 17.1), (6.4, 20), (7.5, 13.8), (3, 9.4), (9.2, 8.5)
        ]
        draw_polygon(pts, fill=color)
    elif kind in ('bookmark', 'bookmark_outline', 'watch_later', 'save', 'saved'):
        # Exact Heroicon v2 24x24 Bookmark outline with rounded shoulder profile
        pts = [
            (6.4, 3.8), (17.6, 3.8), (19.2, 5.4),
            (19.2, 21.0), (12.0, 16.8), (4.8, 21.0),
            (4.8, 5.4), (6.4, 3.8)
        ]
        draw_lines(pts, close=True, width=sw)
    elif kind in ('bookmark_fill', 'bookmark_solid', 'saved_fill', 'watch_later_fill'):
        # Exact Heroicon v2 24x24 Bookmark solid fill
        pts = [
            (6.4, 3.8), (17.6, 3.8), (19.2, 5.4),
            (19.2, 21.0), (12.0, 16.8), (4.8, 21.0),
            (4.8, 5.4)
        ]
        draw_polygon(pts, fill=color)
    elif kind in ('sparkles', 'new'):
        pts1 = [(12, 3), (13.5, 8.5), (19, 10), (13.5, 11.5), (12, 17), (10.5, 11.5), (5, 10), (10.5, 8.5)]
        draw_polygon(pts1, fill=color)
        pts2 = [(18, 15), (18.8, 17.5), (21.5, 18), (18.8, 18.5), (18, 21), (17.2, 18.5), (14.5, 18), (17.2, 17.5)]
        draw_polygon(pts2, fill=color)
    elif kind in ('bell', 'notification'):
        draw_lines([(12, 3), (12, 4.5)], width=sw)
        draw_lines([(6, 17), (18, 17)], width=sw)
        draw_lines([(7.5, 17), (7.5, 11), (9, 6), (15, 6), (16.5, 11), (16.5, 17)], width=sw)
        draw.arc([pt(10, 17), pt(14, 21)], start=0, end=180, fill=color, width=int(round(sw)))
    elif kind in ('megaphone', 'announcement', 'broadcast'):
        draw_polygon([(4, 11), (7, 11), (14, 6), (14, 18), (7, 13), (4, 13)], fill=color)
        draw_lines([(14, 9), (18, 7), (18, 17), (14, 15)], width=sw)
        draw_lines([(7, 13), (7, 19), (10, 19), (10, 13)], width=sw)
    elif kind in ('shield', 'shield_check', 'security'):
        draw_lines([(12, 3), (19.5, 6), (19.5, 12), (12, 21), (4.5, 12), (4.5, 6), (12, 3)], close=True, width=sw)
    elif kind in ('info', 'information_circle'):
        draw_circle(12, 12, 9, outline=color, width=sw)
        draw_circle(12, 8, 1.2, fill=color)
        draw_lines([(12, 11), (12, 16.5)], width=sw)
    elif kind in ('fire', 'views'):
        draw_lines([(12, 2.5), (14.5, 6), (17, 9.5), (18, 13.5), (16.5, 18), (13.5, 20.5), (9.5, 20.5), (6.5, 17.5), (6, 13), (8, 9.5), (10, 11), (12, 7.5), (12, 2.5)], close=True)
    elif kind in ('trending', 'arrow_trending_up'):
        draw_lines([(3, 17), (9, 11), (13.5, 15), (20.5, 7.5)])
        draw_lines([(15.5, 7.5), (20.5, 7.5), (20.5, 12.5)])
    elif kind in ('shuffle', 'arrows_right_left', 'random'):
        draw_lines([(4, 6.5), (9, 6.5), (15, 17.5), (20, 17.5)])
        draw_lines([(16.5, 14.5), (20, 17.5), (16.5, 20.5)])
        draw_lines([(4, 17.5), (9, 17.5), (11, 13.8)])
        draw_lines([(13, 10.2), (15, 6.5), (20, 6.5)])
        draw_lines([(16.5, 3.5), (20, 6.5), (16.5, 9.5)])
    elif kind in ('tag', 'tags'):
        draw_lines([(4, 4), (10, 4), (20, 14), (14, 20), (4, 10), (4, 4)], close=True)
        draw_circle(7.5, 7.5, 1.2, fill=color)
    elif kind in ('user', 'actress', 'models'):
        draw_circle(12, 7.5, 4, outline=color, width=sw)
        draw_lines([(4.5, 19.5), (7, 15.5), (12, 14.5), (17, 15.5), (19.5, 19.5)])
    elif kind in ('tv', 'channels', 'channel'):
        draw_lines([(3.5, 5), (20.5, 5), (20.5, 17), (3.5, 17), (3.5, 5)], close=True)
        draw_lines([(8, 20.5), (16, 20.5)])
        draw_lines([(12, 17), (12, 20.5)])
    elif kind in ('users', 'people', 'actors', 'actor'):
        draw_circle(9, 7.5, 3.2, outline=color, width=sw)
        draw_lines([(3, 19.5), (5, 15.5), (9, 14.5), (13, 15.5), (15, 19.5)])
        draw_circle(16.5, 8.5, 2.6, outline=color, width=sw)
        draw_lines([(14.5, 15), (17.5, 15.5), (20.5, 19.5)])
    elif kind in ('search', 'magnifying_glass'):
        draw_circle(10.5, 10.5, 6, outline=color, width=sw)
        draw_lines([(15, 15), (20.5, 20.5)], width=sw * 1.3)
    elif kind in ('play', 'play_fill'):
        draw_polygon([(7, 5), (19, 12), (7, 19)], fill=color)
    elif kind in ('pause', 'pause_fill'):
        draw_polygon([(6, 5), (10, 5), (10, 19), (6, 19)], fill=color)
        draw_polygon([(14, 5), (18, 5), (18, 19), (14, 19)], fill=color)
    elif kind in ('plus', 'add'):
        draw_lines([(12, 4.5), (12, 19.5)])
        draw_lines([(4.5, 12), (19.5, 12)])
    elif kind in ('refresh', 'reload', 'arrow_path', 'rotate'):
        # Authentic Heroicons 24x24 arrow-path (dual clockwise refresh arcs)
        draw_lines([(16.0, 9.35), (21.0, 9.35), (21.0, 4.35)], width=sw)
        draw_lines([(3.0, 19.65), (3.0, 14.65), (8.0, 14.65)], width=sw)
        draw.arc([pt(3.75, 3.75), pt(20.25, 20.25)], start=215, end=335, fill=color, width=int(round(sw)))
        draw_lines([(17.8, 6.15), (21.0, 9.35)], width=sw)
        draw.arc([pt(3.75, 3.75), pt(20.25, 20.25)], start=35, end=155, fill=color, width=int(round(sw)))
        draw_lines([(6.2, 17.85), (3.0, 14.65)], width=sw)
    elif kind in ('close', 'x_mark', 'remove', 'x'):
        draw_lines([(5.5, 5.5), (18.5, 18.5)])
        draw_lines([(18.5, 5.5), (5.5, 18.5)])
    elif kind in ('folder',):
        draw_lines([(3, 6.5), (9, 6.5), (11, 8.5), (20.5, 8.5), (20.5, 18.5), (3, 18.5), (3, 6.5)], close=True)
    elif kind in ('folder_arrow_down', 'folder_download', 'folder_down'):
        draw_lines([(3, 6.5), (9, 6.5), (11, 8.5), (20.5, 8.5), (20.5, 18.5), (3, 18.5), (3, 6.5)], close=True)
        draw_lines([(12, 8.5), (12, 15.5)])
        draw_lines([(9, 12.5), (12, 15.5), (15, 12.5)])
    elif kind in ('folder_open',):
        draw_lines([(3.75, 9.75), (3.75, 6), (6, 4), (9.5, 4), (11.5, 6.5), (18, 6.5), (20.25, 9), (20.25, 9.75)])
        draw_lines([(3.75, 9.75), (20.25, 9.75), (19.05, 19.5), (4.95, 19.5), (3.75, 9.75)], close=True)
    elif kind in ('arrow_top_right_on_square', 'external_link', 'open_in_new'):
        draw_lines([(13.5, 4.5), (19.5, 4.5), (19.5, 10.5)])
        draw_lines([(19.5, 4.5), (10.5, 13.5)])
        draw_lines([(16.5, 13.5), (16.5, 18), (6, 18), (6, 7.5), (10.5, 7.5)])
    elif kind in ('trash',):
        draw_lines([(4.5, 6), (19.5, 6)])
        draw_lines([(9, 6), (9, 3.5), (15, 3.5), (15, 6)])
        draw_lines([(6, 6), (7, 19.5), (17, 19.5), (18, 6)])
        draw_lines([(10, 9.5), (10, 16)])
        draw_lines([(14, 9.5), (14, 16)])
    elif kind in ('link',):
        draw_lines([(13, 11), (15, 9), (17, 9), (19, 11), (19, 13), (17, 15), (15, 15)])
        draw_lines([(11, 13), (9, 15), (7, 15), (5, 13), (5, 11), (7, 9), (9, 9)])
        draw_lines([(8.5, 15.5), (15.5, 8.5)])
    elif kind in ('backward', 'skip_back'):
        draw_polygon([(12, 12), (20, 5), (20, 19)], fill=color)
        draw_polygon([(4, 12), (12, 5), (12, 19)], fill=color)
    elif kind in ('forward', 'skip_fwd'):
        draw_polygon([(12, 12), (4, 5), (4, 19)], fill=color)
        draw_polygon([(20, 12), (12, 5), (12, 19)], fill=color)
    elif kind in ('speaker_wave', 'volume'):
        draw_polygon([(3, 9), (7, 9), (12, 4), (12, 20), (7, 15), (3, 15)], fill=color)
        draw_lines([(15, 8), (17.5, 12), (15, 16)], width=sw * 1.1)
        draw_lines([(18, 5.5), (21.5, 12), (18, 18.5)], width=sw * 1.1)
    elif kind in ('speaker_x_mark', 'mute'):
        draw_polygon([(3, 9), (7, 9), (12, 4), (12, 20), (7, 15), (3, 15)], fill=color)
        draw_lines([(16, 9), (21, 15)])
        draw_lines([(21, 9), (16, 15)])
    elif kind in ('fullscreen', 'arrows_pointing_out'):
        draw_lines([(4, 9), (4, 4), (9, 4)])
        draw_lines([(15, 4), (20, 4), (20, 9)])
        draw_lines([(20, 15), (20, 20), (15, 20)])
        draw_lines([(9, 20), (4, 20), (4, 15)])
    elif kind in ('fullscreen_exit', 'arrows_pointing_in', 'exit_fullscreen'):
        draw_lines([(4, 9), (9, 9), (9, 4)])
        draw_lines([(20, 9), (15, 9), (15, 4)])
        draw_lines([(20, 15), (15, 15), (15, 20)])
        draw_lines([(4, 15), (9, 15), (9, 20)])
    elif kind in ('arrow_left', 'back', 'arrow_small_left'):
        draw_lines([(20.5, 12), (3.5, 12)])
        draw_lines([(10.5, 19), (3.5, 12), (10.5, 5)])
    elif kind in ('chevron_down', 'chevron-down'):
        draw_lines([(6, 9.5), (12, 15.5), (18, 9.5)], width=sw * 1.1)
    elif kind in ('chevron_up', 'chevron-up'):
        draw_lines([(6, 15.5), (12, 9.5), (18, 15.5)], width=sw * 1.1)
    elif kind in ('chevrons_up_down', 'chevron_up_down', 'chevrons-up-down'):
        draw_lines([(8, 9), (12, 5.5), (16, 9)], width=sw * 1.0)
        draw_lines([(8, 15), (12, 18.5), (16, 15)], width=sw * 1.0)
    elif kind in ('check', 'checkmark'):
        draw_lines([(4.5, 12.5), (9.5, 17.5), (19.5, 7)], width=sw * 1.2)
    elif kind in ('github', 'github_logo', 'git'):
        pts = [
            (12, 2), (9.5, 2.3), (7.2, 3.3), (5.2, 5.0), (3.8, 7.2), (3.0, 9.7), (3.0, 12.0),
            (3.5, 14.5), (4.8, 16.7), (6.8, 18.4), (8.8, 19.5), (8.8, 17.8),
            (7.8, 17.5), (6.8, 16.8), (6.2, 15.5), (5.8, 14.5), (5.0, 14.0),
            (4.5, 14.0), (4.8, 14.6), (5.4, 15.2), (6.0, 16.8), (7.0, 17.8),
            (8.8, 17.5), (8.9, 15.8), (9.5, 15.2), (7.3, 14.9), (5.5, 14.0),
            (4.8, 12.0), (5.2, 9.8), (5.8, 8.8), (5.6, 7.5), (5.8, 6.2),
            (7.0, 6.2), (8.2, 7.0), (9.5, 6.6), (12.0, 6.6), (14.5, 6.6),
            (15.8, 7.0), (17.0, 6.2), (18.2, 6.2), (18.4, 7.5), (18.2, 8.8),
            (18.8, 9.8), (19.2, 12.0), (18.5, 14.0), (16.7, 14.9), (14.5, 15.2),
            (15.1, 15.8), (15.2, 17.5), (17.0, 17.8), (18.0, 16.8), (18.6, 15.2),
            (19.2, 14.6), (19.5, 14.0), (19.0, 14.0), (18.2, 14.5), (17.8, 15.5),
            (17.2, 16.8), (16.2, 17.5), (15.2, 17.8), (15.2, 19.5), (17.2, 18.4),
            (19.2, 16.7), (20.5, 14.5), (21.0, 12.0), (21.0, 9.7), (20.2, 7.2),
            (18.8, 5.0), (16.8, 3.3), (14.5, 2.3), (12, 2)
        ]
        draw_polygon(pts, fill=color)
    elif kind in ('telegram', 'paper_airplane', 'send'):
        # Paper airplane / Telegram icon
        draw_polygon([(21.5, 3.2), (2.8, 11.2), (8.8, 14.5), (18.2, 7.8)], fill=color)
        draw_polygon([(21.5, 3.2), (18.2, 7.8), (12.2, 17.8), (17.5, 20.8)], fill=color)
        draw_polygon([(8.8, 14.5), (12.2, 17.8), (10.2, 21.0)], fill=color)
    elif kind in ('telegram_badge', 'telegram_circle', 'telegram_logo'):
        # Official Telegram circular emblem with white paper plane
        draw_circle(12, 12, 10.5, fill=color)
        white = '#ffffff'
        draw_polygon([(17.5, 6.5), (5.5, 11.5), (9.8, 13.8), (15.5, 9.4)], fill=white)
        draw_polygon([(17.5, 6.5), (15.5, 9.4), (12.0, 15.8), (15.2, 17.8)], fill=white)
        draw_polygon([(9.8, 13.8), (12.0, 15.8), (10.8, 18.0)], fill=white)
    else:
        draw_circle(12, 12, 4, fill=color)

    resampled = img.resize((size, size), Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(resampled)
    _ICON_CACHE[key] = photo
    return photo


_SITE_LABEL = {
    SiteFreePornVideos: 'FreePornVideos',
    SiteOnePornTV: 'OnePorn',
    SiteBeeg: 'Beeg',
}


def make_rounded_box_img(w, h, r, bg_color, border_color=None, border_width=1):
    scale = 4
    sw, sh, sr, sbw = w * scale, h * scale, r * scale, border_width * scale
    img = Image.new('RGBA', (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if border_color and sbw > 0:
        draw.rounded_rectangle([0, 0, sw - 1, sh - 1], radius=sr, fill=bg_color,
                               outline=border_color, width=int(round(sbw)))
    else:
        draw.rounded_rectangle([0, 0, sw - 1, sh - 1], radius=sr, fill=bg_color)
    resampled = img.resize((w, h), Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(resampled)


_MASK_CACHE = {}

def apply_rounded_corners(im, radius=14, bg_color=None):
    if im is None:
        return None
    if bg_color is None:
        card_bg = CURRENT_PALETTE.get('CARD_BG', '#1b1b24').lower()
        if card_bg in ('#ffffff', '#fafafa'):
            bg_color = (255, 255, 255, 255)
        else:
            bg_color = (27, 27, 36, 255)
    w, h = im.size
    if w <= 0 or h <= 0:
        return im
    mask_key = (w, h, radius)
    smooth_mask = _MASK_CACHE.get(mask_key)
    if smooth_mask is None:
        scale = 2
        sw, sh = w * scale, h * scale
        sr = radius * scale
        big_mask = Image.new('L', (sw, sh), 0)
        big_draw = ImageDraw.Draw(big_mask)
        big_draw.rounded_rectangle([0, 0, sw - 1, sh - 1], radius=sr, fill=255)
        smooth_mask = big_mask.resize((w, h), Image.Resampling.BILINEAR)
        if len(_MASK_CACHE) > 100:
            _MASK_CACHE.clear()
        _MASK_CACHE[mask_key] = smooth_mask

    bg = Image.new('RGBA', (w, h), bg_color)
    if im.mode != 'RGBA':
        im = im.convert('RGBA')
    bg.paste(im, (0, 0), smooth_mask)
    return bg


def get_pil_font(size_pt, bold=False):
    font_names = [
        "segoeuib.ttf" if bold else "segoeui.ttf",
        "arialbd.ttf" if bold else "arial.ttf",
        "Helvetica-Bold.ttf" if bold else "Helvetica.ttf"
    ]
    for fn in font_names:
        try:
            return ImageFont.truetype(fn, int(size_pt))
        except Exception:
            pass
    return ImageFont.load_default()


def draw_vector_star(draw, cx, cy, r_out, r_in, fill, outline=None, width=1):
    pts = []
    for i in range(10):
        a = i * math.pi / 5 - math.pi / 2
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    draw.polygon(pts, fill=fill, outline=outline, width=width)


def create_poster_card_pil(raw_img, name, role='Actress', is_starred=False,
                           width=210, height=290, radius=16,
                           is_hover=False, mode='dark'):
    """
    Renders a large rectangular poster card PIL Image:
    - Clean, sharp full-cover photo with smooth rounded corners (no inner border).
    - Bottom dark gradient overlay with bold white performer name and role subtitle.
    - Bottom-right vector Watchlist star (★ / ☆).
    - Glowing border ring on hover.
    """
    scale = 4
    sw, sh, sr = width * scale, height * scale, radius * scale

    if raw_img:
        try:
            iw, ih = raw_img.size
            target_ratio = width / height
            img_ratio = iw / ih
            if img_ratio > target_ratio:
                new_w = int(ih * target_ratio)
                left = (iw - new_w) // 2
                cropped = raw_img.crop((left, 0, left + new_w, ih))
            else:
                new_h = int(iw / target_ratio)
                top = (ih - new_h) // 2
                cropped = raw_img.crop((0, top, iw, top + new_h))
            base = cropped.resize((sw, sh), Image.Resampling.LANCZOS).convert('RGBA')
        except Exception:
            raw_img = None

    if not raw_img:
        base = Image.new('RGBA', (sw, sh), '#181822')
        draw_b = ImageDraw.Draw(base)
        top_c = (37, 99, 235, 255) if role.lower() == 'actress' else (124, 58, 237, 255)
        bot_c = (15, 23, 42, 255)
        for y in range(sh):
            t = y / sh
            r = int(top_c[0] * (1 - t) + bot_c[0] * t)
            g = int(top_c[1] * (1 - t) + bot_c[1] * t)
            b = int(top_c[2] * (1 - t) + bot_c[2] * t)
            draw_b.line([(0, y), (sw, y)], fill=(r, g, b, 255))

        initial = (name.strip()[0] if name and name.strip() else '?').upper()
        init_font = get_pil_font(64 * scale, bold=True)
        bbox = draw_b.textbbox((0, 0), initial, font=init_font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw_b.text(((sw - tw) // 2, int(sh * 0.35) - th // 2), initial, fill=(255, 255, 255, 140), font=init_font)

    # Bottom Dark Gradient Overlay
    gradient = Image.new('RGBA', (sw, sh), (0, 0, 0, 0))
    draw_g = ImageDraw.Draw(gradient)
    grad_start = int(sh * 0.45)
    for y in range(grad_start, sh):
        progress = (y - grad_start) / (sh - grad_start)
        alpha = int(245 * (progress ** 1.15))
        draw_g.line([(0, y), (sw, y)], fill=(0, 0, 0, min(255, alpha)))
    base = Image.alpha_composite(base, gradient)

    # Typography & Star on Bottom
    overlay = Image.new('RGBA', (sw, sh), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    pad_x = 16 * scale
    pad_b = 16 * scale

    bold_font = get_pil_font(14 * scale, bold=True)
    sub_font = get_pil_font(10.5 * scale, bold=False)

    # Bottom Left: Role subtitle
    role_str = role.capitalize()
    draw.text((pad_x, sh - pad_b - 18 * scale), role_str, fill=(210, 215, 225, 230), font=sub_font)

    # Bottom Right: Star Button placed where 3 dots were
    star_cx = sw - pad_x - 12 * scale
    star_cy = sh - pad_b - 10 * scale
    star_fill = (245, 158, 11, 255) if is_starred else (255, 255, 255, 100)
    star_out = (255, 255, 255, 255) if is_starred else (255, 255, 255, 190)
    draw_vector_star(draw, star_cx, star_cy, 10 * scale, 4.8 * scale, fill=star_fill, outline=star_out, width=int(1.3 * scale))

    # Bottom Left: Performer Name (bold white)
    name_y = sh - pad_b - 42 * scale
    n_bbox = draw.textbbox((0, 0), name, font=bold_font)
    max_w = sw - pad_x * 2 - 32 * scale
    if n_bbox[2] - n_bbox[0] > max_w:
        words = name.split()
        if len(words) > 1:
            l1 = words[0]
            l2 = " ".join(words[1:])
            draw.text((pad_x, name_y - 17 * scale), l1, fill=(255, 255, 255, 255), font=bold_font)
            draw.text((pad_x, name_y), l2, fill=(255, 255, 255, 255), font=bold_font)
        else:
            draw.text((pad_x, name_y), name, fill=(255, 255, 255, 255), font=bold_font)
    else:
        draw.text((pad_x, name_y), name, fill=(255, 255, 255, 255), font=bold_font)

    base = Image.alpha_composite(base, overlay)

    # Rounded corner mask for entire card
    mask = Image.new('L', (sw, sh), 0)
    draw_m = ImageDraw.Draw(mask)
    draw_m.rounded_rectangle([0, 0, sw - 1, sh - 1], radius=sr, fill=255)

    final_img = Image.new('RGBA', (sw, sh), (0, 0, 0, 0))
    final_img.paste(base, (0, 0), mask=mask)

    # Outer Card Border Ring
    border_col = (10, 132, 255, 255) if is_hover else ((255, 255, 255, 55) if mode == 'dark' else (0, 0, 0, 40))
    draw_f = ImageDraw.Draw(final_img)
    bw = (2.5 if is_hover else 1) * scale
    draw_f.rounded_rectangle([0, 0, sw - 1, sh - 1], radius=sr, outline=border_col, width=int(round(bw)))

    resampled = final_img.resize((width, height), Image.Resampling.LANCZOS)
    return resampled


def create_poster_card_img(raw_img, name, role='Actress', is_starred=False,
                           width=210, height=290, radius=16,
                           is_hover=False, mode='dark'):
    im = create_poster_card_pil(raw_img, name, role=role, is_starred=is_starred,
                                width=width, height=height, radius=radius,
                                is_hover=is_hover, mode=mode)
    return ImageTk.PhotoImage(im)


def make_circle_crop_img(img, size=44, border_color=None, border_width=1, bg_color=None):
    """
    Crops a PIL Image into a smooth antialiased circular avatar with an optional subtle border ring.
    """
    if img is None:
        return None
    try:
        w, h = img.size
        m = min(w, h)
        left = (w - m) // 2
        top = (h - m) // 2
        cropped = img.crop((left, top, left + m, top + m))

        scale = 4
        s = size * scale
        resized = cropped.resize((s, s), Image.Resampling.LANCZOS).convert('RGBA')

        mask = Image.new('L', (s, s), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, s - 1, s - 1), fill=255)

        base_bg = bg_color if bg_color else (0, 0, 0, 0)
        out = Image.new('RGBA', (s, s), base_bg)
        out.paste(resized, (0, 0), mask=mask)

        if border_color and border_width > 0:
            bw = border_width * scale
            draw_out = ImageDraw.Draw(out)
            draw_out.ellipse((bw // 2, bw // 2, s - 1 - bw // 2, s - 1 - bw // 2),
                             outline=border_color, width=int(round(bw)))

        resampled = out.resize((size, size), Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(resampled)
    except Exception:
        return None


def make_initial_circle_avatar(name, size=44, bg_color='#2563eb', fg_color='#ffffff'):
    """
    Generates a crisp, colorful circular placeholder avatar displaying the performer's initial letter.
    """
    initial = (name.strip()[0] if name and name.strip() else '?').upper()
    scale = 4
    s = size * scale
    img = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse((0, 0, s - 1, s - 1), fill=bg_color)

    font = None
    for fn in ('seguiui.ttf', 'arial.ttf', 'segoeui.ttf'):
        try:
            font = ImageFont.truetype(fn, int(s * 0.45))
            break
        except Exception:
            pass
    if font is None:
        try:
            font = ImageFont.load_default()
        except Exception:
            pass

    if font:
        try:
            bbox = draw.textbbox((0, 0), initial, font=font)
            tw = bbox[2] - bbox[0]
            th = bbox[3] - bbox[1]
            tx = (s - tw) // 2 - bbox[0]
            ty = (s - th) // 2 - bbox[1]
            draw.text((tx, ty), initial, fill=fg_color, font=font)
        except Exception:
            draw.text((s // 3, s // 4), initial, fill=fg_color)

    resampled = img.resize((size, size), Image.Resampling.LANCZOS)
    return ImageTk.PhotoImage(resampled)


_WORDMARK_CACHE = {}

def get_fetchx_wordmark(font_size=16, hover=False, suffix='', scale=4, mode=None):
    """
    Renders the official FetchX brand wordmark with crisp anti-aliasing
    and a vibrant blue gradient on the 'X'.
    - 'Fetch' in crisp white text (dark mode) or dark text (light mode)
    - 'X' in vibrant royal blue to cyan gradient
    """
    if mode is None:
        mode = get_effective_theme()
    key = (font_size, hover, suffix, mode)
    cached = _WORDMARK_CACHE.get(key)
    if cached is not None:
        try:
            cached.tk.call('image', 'type', cached._PhotoImage__photo.name)
            return cached
        except Exception:
            _WORDMARK_CACHE.pop(key, None)

    scaled_font_size = int(font_size * scale)
    font_names = [
        "segoeuib.ttf", "SegUIVar.ttf", "arialbd.ttf", "SFProText-Bold.ttf",
        "SFProDisplay-Bold.ttf", "Inter-Bold.ttf", "DejaVuSans-Bold.ttf", "arial.ttf"
    ]
    font = None
    for name in font_names:
        try:
            font = ImageFont.truetype(name, scaled_font_size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    dummy_img = Image.new("RGBA", (1, 1), (0, 0, 0, 0))
    dummy_draw = ImageDraw.Draw(dummy_img)

    text_fetch = "Fetch"
    text_x = "X"
    text_suffix = str(suffix) if suffix else ""

    bbox_fetch = dummy_draw.textbbox((0, 0), text_fetch, font=font)
    fetch_w = bbox_fetch[2] - bbox_fetch[0]
    fetch_h = bbox_fetch[3] - bbox_fetch[1]

    bbox_x = dummy_draw.textbbox((0, 0), text_x, font=font)
    x_w = bbox_x[2] - bbox_x[0]
    x_h = bbox_x[3] - bbox_x[1]

    suf_w, suf_h, bbox_suf = 0, 0, None
    if text_suffix:
        bbox_suf = dummy_draw.textbbox((0, 0), text_suffix, font=font)
        suf_w = bbox_suf[2] - bbox_suf[0]
        suf_h = bbox_suf[3] - bbox_suf[1]

    pad_x = int(2 * scale)
    pad_y = int(2 * scale)
    spacing_x = int(1 * scale)

    total_w = fetch_w + spacing_x + x_w + (suf_w + int(6 * scale) if text_suffix else 0) + pad_x * 2 + int(4 * scale)
    max_text_h = max(fetch_h, x_h, suf_h)
    total_h = max_text_h + pad_y * 2 + int(6 * scale)

    img = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    base_y = pad_y + (max_text_h - fetch_h) // 2 - bbox_fetch[1]

    if mode == 'light':
        fetch_color = (17, 24, 39, 255) if not hover else (37, 99, 235, 255)
    else:
        fetch_color = (255, 255, 255, 255) if not hover else (224, 242, 254, 255)
    draw.text((pad_x, base_y), text_fetch, font=font, fill=fetch_color)

    x_offset = pad_x + fetch_w + spacing_x
    mask_x = Image.new("L", (total_w, total_h), 0)
    draw_mask = ImageDraw.Draw(mask_x)
    base_y_x = pad_y + (max_text_h - x_h) // 2 - bbox_x[1]
    draw_mask.text((x_offset, base_y_x), text_x, font=font, fill=255)

    if hover:
        c_start = (59, 130, 246)  # #3b82f6 - Radiant Blue
        c_end = (96, 165, 250)    # #60a5fa - Luminous Cyan/Sky Blue
    else:
        c_start = (37, 99, 235)   # #2563eb - Electric Royal Blue
        c_end = (56, 189, 248)    # #38bdf8 - Vivid Cyan / Sky Blue

    grad = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
    for y in range(total_h):
        for x in range(x_offset, min(total_w, x_offset + x_w + int(8 * scale))):
            t_y = (y - pad_y) / max(1, x_h)
            t_x = (x - x_offset) / max(1, x_w)
            t = (t_x * 0.45 + (1.0 - t_y) * 0.55)
            t = min(max(t, 0.0), 1.0)

            r = int(c_start[0] + (c_end[0] - c_start[0]) * t)
            g = int(c_start[1] + (c_end[1] - c_start[1]) * t)
            b = int(c_start[2] + (c_end[2] - c_start[2]) * t)
            grad.putpixel((x, y), (r, g, b, 255))

    img.paste(grad, (0, 0), mask=mask_x)

    if text_suffix and bbox_suf:
        suf_x = x_offset + x_w + int(6 * scale)
        base_y_suf = pad_y + (max_text_h - suf_h) // 2 - bbox_suf[1]
        suf_color = (107, 114, 128, 255) if mode == 'light' else (161, 161, 170, 255)
        draw.text((suf_x, base_y_suf), text_suffix, font=font, fill=suf_color)

    final_w = max(1, total_w // scale)
    final_h = max(1, total_h // scale)
    resampled = img.resize((final_w, final_h), Image.Resampling.LANCZOS)
    photo = ImageTk.PhotoImage(resampled)
    _WORDMARK_CACHE[key] = photo
    return photo


# ==============================================================================
# Windows-Native Window Controls (Top-Right Caption Bar)
# ==============================================================================

class WindowsCaptionControls(tk.Frame):
    """Windows 11 native-style window controls (Refresh, Minimize, Maximize/Restore, Close)."""
    def __init__(self, master, on_close, on_min, on_max, on_refresh=None, bg=None, **kw):
        bg = bg or WINDOW_BG
        super().__init__(master, bg=bg, bd=0, highlightthickness=0, **kw)
        self.on_close = on_close
        self.on_min = on_min
        self.on_max = on_max
        self.on_refresh = on_refresh

        # Refresh button (inline with control buttons)
        self.btn_refresh = tk.Label(self, text='\u27f3', width=5, pady=8, bg=bg, fg=BODY,
                                    font=('Segoe UI', 11), cursor='arrow')
        self.btn_refresh.pack(side='left')
        self.btn_refresh.bind('<Button-1>', lambda _e: self.on_refresh() if self.on_refresh else None)

        # Minimize button
        self.btn_min = tk.Label(self, text='\u2500', width=5, pady=8, bg=bg, fg=BODY,
                                font=('Segoe UI', 11), cursor='arrow')
        self.btn_min.pack(side='left')
        self.btn_min.bind('<Button-1>', lambda _e: self.on_min())

        # Maximize / Restore button
        self.btn_max = tk.Label(self, text='\u25a1', width=5, pady=8, bg=bg, fg=BODY,
                                font=('Segoe UI', 11), cursor='arrow')
        self.btn_max.pack(side='left')
        self.btn_max.bind('<Button-1>', lambda _e: self.on_max())

        # Close button (Windows Red hover)
        self.btn_close = tk.Label(self, text='\u2715', width=5, pady=8, bg=bg, fg=BODY,
                                  font=('Segoe UI', 11), cursor='arrow')
        self.btn_close.pack(side='left')
        self.btn_close.bind('<Button-1>', lambda _e: self.on_close())

        self._bind_hovers()

    def _bind_hovers(self):
        hover_bg = CURRENT_PALETTE.get('CAPTION_HOVER_BG', '#2a2a34')
        bg = self.cget('bg')
        if hasattr(self, 'btn_refresh'):
            self.btn_refresh.bind('<Enter>', lambda _e: self.btn_refresh.configure(bg=hover_bg, fg=INK))
            self.btn_refresh.bind('<Leave>', lambda _e: self.btn_refresh.configure(bg=bg, fg=BODY))
        self.btn_min.bind('<Enter>', lambda _e: self.btn_min.configure(bg=hover_bg, fg=INK))
        self.btn_min.bind('<Leave>', lambda _e: self.btn_min.configure(bg=bg, fg=BODY))
        self.btn_max.bind('<Enter>', lambda _e: self.btn_max.configure(bg=hover_bg, fg=INK))
        self.btn_max.bind('<Leave>', lambda _e: self.btn_max.configure(bg=bg, fg=BODY))
        self.btn_close.bind('<Enter>', lambda _e: self.btn_close.configure(bg='#e81123', fg='#ffffff'))
        self.btn_close.bind('<Leave>', lambda _e: self.btn_close.configure(bg=bg, fg=BODY))

    def retheme(self, bg=None):
        bg = bg or WINDOW_BG
        self.configure(bg=bg)
        if hasattr(self, 'btn_refresh'):
            self.btn_refresh.configure(bg=bg, fg=BODY)
        self.btn_min.configure(bg=bg, fg=BODY)
        self.btn_max.configure(bg=bg, fg=BODY)
        self.btn_close.configure(bg=bg, fg=BODY)
        self._bind_hovers()

    def set_maximized(self, is_max):
        self.btn_max.configure(text='\u2750' if is_max else '\u25a1')


# ==============================================================================
# Liquid Glass Rounded Search Bar Capsule
# ==============================================================================

class GlassSearchBar(tk.Canvas):
    """Liquid Glass Search Capsule with Anti-Aliased Curved Borders."""
    def __init__(self, master, app, on_search, placeholder='Search 1,000,000+ videos or paste direct link\u2026',
                 width=600, height=36, radius=18, bg=None, **kw):
        bg = bg or WINDOW_BG
        super().__init__(master, width=width, height=height, bg=bg, bd=0, highlightthickness=0, **kw)
        self.app = app
        self.on_search = on_search
        self.placeholder = placeholder
        self._focused = False
        self._bg_color = bg

        # Search icon
        ico_img = get_heroicon('search', size=20, color=FAINT)
        self.lbl_icon = tk.Label(self, image=ico_img, bg=SEARCH_BG)
        self.lbl_icon.image = ico_img

        # Text entry inside the capsule
        self.entry = tk.Entry(self, bg=SEARCH_BG, fg=FAINT, relief='flat',
                              insertbackground=INK, bd=0, font=app.font_sans(11))
        self.entry.insert(0, placeholder)

        # Clear button
        clear_img = get_heroicon('close', size=16, color=FAINT)
        self.btn_clear = tk.Label(self, image=clear_img, bg=SEARCH_BG, cursor='hand2')
        self.btn_clear.image = clear_img

        # Window items on canvas
        self._win_icon = self.create_window(20, 18, window=self.lbl_icon, anchor='center')
        self._win_entry = self.create_window(40, 18, window=self.entry, anchor='w')
        self._win_clear = self.create_window(576, 18, window=self.btn_clear, anchor='center')
        self.itemconfigure(self._win_clear, state='hidden')

        self.bind('<Configure>', self._on_configure)
        self.bind('<Button-1>', lambda _e: self.entry.focus_set())
        self.lbl_icon.bind('<Button-1>', lambda _e: self.entry.focus_set())
        self.entry.bind('<FocusIn>', self._on_focus_in)
        self.entry.bind('<FocusOut>', self._on_focus_out)
        self.entry.bind('<KeyRelease>', self._on_key)
        self.entry.bind('<Return>', self._on_return)
        self.btn_clear.bind('<Button-1>', self._clear)

    def retheme(self, bg=None):
        bg = bg or WINDOW_BG
        self._bg_color = bg
        self.configure(bg=bg)
        ico_img = get_heroicon('search', size=20, color=FAINT)
        self.lbl_icon.configure(bg=SEARCH_BG, image=ico_img)
        self.lbl_icon.image = ico_img
        clear_img = get_heroicon('close', size=16, color=FAINT)
        self.btn_clear.configure(bg=SEARCH_BG, image=clear_img)
        self.btn_clear.image = clear_img
        cur = self.entry.get()
        self.entry.configure(bg=SEARCH_BG, insertbackground=INK,
                             fg=INK if cur and cur != self.placeholder else FAINT)
        self._render()

    def _on_configure(self, _e=None):
        self._render()

    def _render(self):
        self.delete('pill_bg')
        w = max(self.winfo_width(), 120)
        h = max(self.winfo_height(), 36)
        r = h // 2

        border = SEARCH_FOCUS if self._focused else SEARCH_BORDER
        bg = SEARCH_BG

        # Left semi-circle arc
        self.create_arc(1, 1, h - 1, h - 1, start=90, extent=180,
                        fill=bg, outline=border, width=1, tags='pill_bg')
        # Right semi-circle arc
        self.create_arc(w - h + 1, 1, w - 1, h - 1, start=270, extent=180,
                        fill=bg, outline=border, width=1, tags='pill_bg')
        # Center filled rectangle
        self.create_rectangle(r, 1, w - r, h - 1, fill=bg, outline=bg, tags='pill_bg')
        # Top and bottom border lines
        self.create_line(r, 1, w - r, 1, fill=border, width=1, tags='pill_bg')
        self.create_line(r, h - 1, w - r, h - 1, fill=border, width=1, tags='pill_bg')

        # Reposition elements
        self.coords(self._win_icon, 20, h // 2)
        self.coords(self._win_entry, 38, h // 2)
        entry_w = max(40, w - 75)
        self.itemconfigure(self._win_entry, width=entry_w)
        self.coords(self._win_clear, w - 20, h // 2)

    def get(self):
        val = self.entry.get().strip()
        return '' if val == self.placeholder else val

    def set(self, text):
        self.entry.delete(0, 'end')
        if text:
            self.entry.insert(0, text)
            self.entry.configure(fg=INK)
            self.itemconfigure(self._win_clear, state='normal')
        else:
            self.entry.insert(0, self.placeholder)
            self.entry.configure(fg=FAINT)
            self.itemconfigure(self._win_clear, state='hidden')

    def _on_focus_in(self, _e=None):
        self._focused = True
        self._render()
        if self.entry.get() == self.placeholder:
            self.entry.delete(0, 'end')
        self.entry.configure(fg=INK)

    def _on_focus_out(self, _e=None):
        self._focused = False
        self._render()
        if not self.entry.get().strip():
            self.entry.delete(0, 'end')
            self.entry.insert(0, self.placeholder)
            self.entry.configure(fg=FAINT)
            self.itemconfigure(self._win_clear, state='hidden')

    def _on_key(self, _e=None):
        val = self.entry.get().strip()
        if val and val != self.placeholder:
            self.itemconfigure(self._win_clear, state='normal')
        else:
            self.itemconfigure(self._win_clear, state='hidden')

    def _on_return(self, _e=None):
        if self.on_search:
            self.on_search(self.get())

    def _clear(self, _e=None):
        self.set('')
        if self.on_search:
            self.on_search('')


class MacToggleSwitch(tk.Canvas):
    """Vercel / Geist UI Design System Toggle Switch with sleek capsule track and drop-shadow knob."""
    def __init__(self, master, variable=None, command=None,
                 on_color=None, off_color=None,
                 on_border=None, off_border=None, **kw):
        on_color = on_color or CURRENT_PALETTE.get('SWITCH_ON_BG', '#0070f3')
        off_color = off_color or CURRENT_PALETTE.get('SWITCH_OFF_BG', '#18181f')
        on_border = on_border or CURRENT_PALETTE.get('SWITCH_ON_BORDER', '#3b82f6')
        off_border = off_border or CURRENT_PALETTE.get('SWITCH_OFF_BORDER', '#38384a')
        super().__init__(master, width=42, height=24, bg=master['bg'],
                         bd=0, highlightthickness=0, cursor='hand2', **kw)
        self.variable = variable or tk.BooleanVar(value=False)
        self.command = command
        self.on_color = on_color
        self.off_color = off_color
        self.on_border = on_border
        self.off_border = off_border
        self._hover = False

        self.bind('<Button-1>', self._on_click)
        self.bind('<Enter>', lambda _e: self._on_hover(True))
        self.bind('<Leave>', lambda _e: self._on_hover(False))
        self._render()
        self.variable.trace_add('write', lambda *_: self._render())

    def retheme(self):
        self.on_color = CURRENT_PALETTE.get('SWITCH_ON_BG', '#0070f3')
        self.off_color = CURRENT_PALETTE.get('SWITCH_OFF_BG', '#18181f')
        self.on_border = CURRENT_PALETTE.get('SWITCH_ON_BORDER', '#3b82f6')
        self.off_border = CURRENT_PALETTE.get('SWITCH_OFF_BORDER', '#38384a')
        try:
            self.configure(bg=self.master['bg'])
        except Exception:
            pass
        self._render()

    def _on_hover(self, hover):
        self._hover = hover
        self._render()

    def _on_click(self, _e=None):
        self.variable.set(not self.variable.get())
        if self.command:
            try:
                self.command()
            except Exception:
                pass

    def _render(self):
        self.delete('all')
        w, h = 42, 24
        r = 12
        val = self.variable.get()
        track_color = self.on_color if val else self.off_color

        if val:
            border_color = '#60a5fa' if self._hover else self.on_border
        else:
            border_color = '#525266' if (self._hover and CURRENT_PALETTE['INK'] == '#f5f5f7') else (
                '#9ca3af' if self._hover else self.off_border)

        # Capsule Track Border (Geist 1px rim)
        self.create_oval(0, 0, h - 1, h - 1, fill=border_color, outline='')
        self.create_oval(w - h, 0, w - 1, h - 1, fill=border_color, outline='')
        self.create_rectangle(r, 0, w - r, h - 1, fill=border_color, outline='')

        # Capsule Track Body (Inset by 1px)
        self.create_oval(1, 1, h - 2, h - 2, fill=track_color, outline='')
        self.create_oval(w - h + 1, 1, w - 2, h - 2, fill=track_color, outline='')
        self.create_rectangle(r, 1, w - r, h - 2, fill=track_color, outline='')

        # Circular Knob with subtle drop shadow
        knob_r = 8.5
        kx = (w - r) if val else r
        ky = r

        # Drop shadow
        shadow_col = '#09090d' if CURRENT_PALETTE['INK'] == '#f5f5f7' else '#cbd5e1'
        self.create_oval(kx - knob_r, ky - knob_r + 1, kx + knob_r, ky + knob_r + 1,
                         fill=shadow_col, outline='')
        # Main white knob
        self.create_oval(kx - knob_r, ky - knob_r, kx + knob_r, ky + knob_r,
                         fill='#ffffff', outline='#d4d4d8' if not val else '#bfdbfe')


# Geist / Vercel component alias
Switch = MacToggleSwitch
SwitchControl = MacToggleSwitch


class GeistSegmentedSwitch(tk.Frame):
    """Vercel / Geist UI Segmented Switch Control.
    Encloses segmented options within a continuous capsule with elevated active pill.
    """
    def __init__(self, master, app, segments, on_change=None, default=None, **kw):
        c_bg = CURRENT_PALETTE.get('SEG_CONTAINER_BG', '#121218')
        c_bd = CURRENT_PALETTE.get('SEG_CONTAINER_BD', '#2d2d3a')
        super().__init__(master, bg=c_bg, highlightthickness=1,
                         highlightbackground=c_bd, cursor='hand2', **kw)
        self.app = app
        self.segments = segments
        self.on_change = on_change
        self.active_val = default or (segments[0][0] if segments else '')
        self._frames = {}
        self._labels = {}
        self._hover_key = None

        for val, label in segments:
            f = tk.Frame(self, bg=c_bg, cursor='hand2')
            f.pack(side='left', padx=2, pady=2)
            lbl = tk.Label(f, text=label, font=app.font_sans(9, bold=True),
                           cursor='hand2', padx=12, pady=3)
            lbl.pack()
            self._frames[val] = f
            self._labels[val] = lbl

            for w in (f, lbl):
                w.bind('<Button-1>', lambda _e, v=val: self.set_value(v))
                w.bind('<Enter>', lambda _e, v=val: self._on_hover(v, True))
                w.bind('<Leave>', lambda _e, v=val: self._on_hover(v, False))

        self._render()

    def retheme(self):
        c_bg = CURRENT_PALETTE.get('SEG_CONTAINER_BG', '#121218')
        c_bd = CURRENT_PALETTE.get('SEG_CONTAINER_BD', '#2d2d3a')
        self.configure(bg=c_bg, highlightbackground=c_bd)
        self._render()

    def set_value(self, val):
        if self.active_val != val:
            self.active_val = val
            self._render()
            if self.on_change:
                try:
                    self.on_change(val)
                except Exception as exc:
                    print('switch on_change error:', exc)

    def _on_hover(self, val, enter):
        self._hover_key = val if enter else None
        self._render()

    def _render(self):
        act_bg = CURRENT_PALETTE.get('SEG_ACTIVE_BG', '#0f2b48')
        act_bd = CURRENT_PALETTE.get('SEG_ACTIVE_BD', '#2563eb')
        act_fg = CURRENT_PALETTE.get('SEG_ACTIVE_FG', '#93c5fd')
        hov_bg = CURRENT_PALETTE.get('SEG_HOVER_BG', '#1c1c28')
        hov_bd = CURRENT_PALETTE.get('SEG_HOVER_BD', '#3a3a4e')
        hov_fg = CURRENT_PALETTE.get('SEG_HOVER_FG', '#e4e4e7')
        ina_bg = CURRENT_PALETTE.get('SEG_INACTIVE_BG', '#121218')
        ina_fg = CURRENT_PALETTE.get('SEG_INACTIVE_FG', '#71717a')

        for val in self._frames.keys():
            f = self._frames[val]
            lbl = self._labels[val]
            is_active = (val == self.active_val)
            is_hover = (val == self._hover_key and not is_active)

            if is_active:
                f.configure(bg=act_bg, highlightthickness=1, highlightbackground=act_bd)
                lbl.configure(bg=act_bg, fg=act_fg)
            elif is_hover:
                f.configure(bg=hov_bg, highlightthickness=1, highlightbackground=hov_bd)
                lbl.configure(bg=hov_bg, fg=hov_fg)
            else:
                f.configure(bg=ina_bg, highlightthickness=1, highlightbackground=ina_bg)
                lbl.configure(bg=ina_bg, fg=ina_fg)


# ==============================================================================
# Geist UI / Vercel Input Component System (@vercel/geistcn/components Input)
# ==============================================================================

class GeistInput(tk.Frame):
    """Vercel / Geist UI Design System Input Component.

    Implements @vercel/geistcn/components Input specifications:
    - Prefix: Icon (<IconArrowCircleUp />, <IconFolder />, etc.) or text prefix ("https://", "vercel/")
    - PrefixStyling: Container badge/chip styling with hairline separator (True) or seamless inline (False)
    - Center Entry: Flat text input with placeholder support and dynamic textvariable binding
    - Suffix: Icon, text (".com"), or interactive action buttons
    - SuffixStyling: Container styling (True/False)
    - SuffixContainer: Wrapped in container box or integrated
    - Interactive Focus: Vercel Blue active highlight rim on focus
    - Subtle Hover: Hairline border highlight on mouse hover
    """
    def __init__(self, master, app, textvariable=None, placeholder='',
                 prefix=None, prefix_styling=True,
                 suffix=None, suffix_styling=True, suffix_container=True,
                 actions=None, bg=None, border=None,
                 hover_border=None, focus_border=None,
                 fg=None, font=None, state='normal', width=None,
                 on_change=None, on_return=None, **kw):
        bg = bg or CURRENT_PALETTE.get('INPUT_BG', '#161622')
        border = border or CURRENT_PALETTE.get('INPUT_BORDER', '#2d2d3e')
        hover_border = hover_border or CURRENT_PALETTE.get('INPUT_HOVER_BORDER', '#444458')
        focus_border = focus_border or CURRENT_PALETTE.get('LINK', '#0a84ff')
        fg = fg or INK
        super().__init__(master, bg=bg, highlightthickness=1,
                         highlightbackground=border, **kw)
        self.app = app
        self.textvariable = textvariable or tk.StringVar()
        self.placeholder = placeholder
        self.prefix = prefix
        self.prefix_styling = prefix_styling
        self.suffix = suffix
        self.suffix_styling = suffix_styling
        self.suffix_container = suffix_container
        self.actions = actions or []
        self._bg_color = bg
        self._border_color = border
        self._hover_border = hover_border
        self._focus_border = focus_border
        self._fg_color = fg
        self._focused = False
        self._hovered = False
        self.on_change = on_change
        self.on_return = on_return
        self.font = font or app.font_sans(10)
        self.entry_state = state
        self._entry_width = width

        self._action_widgets = []
        self._action_items = []
        self._build_ui()
        self._bind_events()

    def _build_ui(self):
        box_bg = CURRENT_PALETTE.get('INPUT_BOX_BG', '#1c1c2b')
        # 1. Prefix
        if self.prefix is not None:
            if self.prefix_styling:
                p_box = tk.Frame(self, bg=box_bg)
                p_box.pack(side='left', fill='y', padx=0, pady=0)
                self._p_box = p_box
                self._render_prefix_content(p_box, bg=box_bg)
                div = tk.Frame(self, bg=self._border_color, width=1)
                div.pack(side='left', fill='y')
                self._p_div = div
            else:
                p_box = tk.Frame(self, bg=self._bg_color)
                p_box.pack(side='left', fill='y', padx=(8, 2), pady=0)
                self._p_box = p_box
                self._render_prefix_content(p_box, bg=self._bg_color)

        # 2. Text Entry (Center)
        self.entry = tk.Entry(
            self,
            textvariable=self.textvariable,
            bg=self._bg_color,
            fg=INK,
            relief='flat',
            bd=0,
            insertbackground=INK,
            font=self.font,
            state=self.entry_state,
            highlightthickness=0
        )
        if self._entry_width:
            self.entry.configure(width=self._entry_width)
        self.entry.pack(side='left', fill='x', expand=True, padx=(8, 6), pady=6)

        # 3. Actions / Suffix
        if self.actions:
            if self.suffix_container:
                s_box = tk.Frame(self, bg=self._bg_color)
                s_box.pack(side='right', fill='y', padx=(0, 4), pady=3)
                self._s_box = s_box
                if self.suffix_styling:
                    div = tk.Frame(self, bg=self._border_color, width=1)
                    div.pack(side='right', fill='y')
                    self._s_div = div
            else:
                s_box = tk.Frame(self, bg=self._bg_color)
                s_box.pack(side='right', fill='y', padx=(0, 4), pady=3)
                self._s_box = s_box

            for act in self.actions:
                self._render_action_button(s_box, act)

        elif self.suffix is not None:
            if self.suffix_styling:
                if self.suffix_container:
                    div = tk.Frame(self, bg=self._border_color, width=1)
                    div.pack(side='right', fill='y')
                    self._s_div = div
                s_box = tk.Frame(self, bg=box_bg if self.suffix_container else self._bg_color)
                s_box.pack(side='right', fill='y', padx=0, pady=0)
                self._s_box = s_box
                self._render_suffix_content(s_box, bg=box_bg if self.suffix_container else self._bg_color)
            else:
                s_box = tk.Frame(self, bg=self._bg_color)
                s_box.pack(side='right', fill='y', padx=(2, 8), pady=0)
                self._s_box = s_box
                self._render_suffix_content(s_box, bg=self._bg_color)

    def _render_prefix_content(self, container, bg):
        if isinstance(self.prefix, str):
            if self.prefix in ('folder', 'folder_arrow_down', 'folder_download', 'folder_open', 'search', 'arrow_down_tray', 'link', 'tag', 'settings', 'clock', 'sparkles', 'tv'):
                img = get_heroicon(self.prefix, size=16, color=BODY)
                lbl = tk.Label(container, image=img, bg=bg, padx=8, pady=4)
                lbl.image = img
                lbl.pack(side='left')
                lbl.bind('<Button-1>', lambda _e: self.entry.focus_set())
                self._p_lbl = lbl
            else:
                lbl = tk.Label(container, text=self.prefix, bg=bg, fg=MUTE,
                               font=self.app.font_sans(9, bold=True), padx=8, pady=4)
                lbl.pack(side='left')
                lbl.bind('<Button-1>', lambda _e: self.entry.focus_set())
                self._p_lbl = lbl
        elif hasattr(self.prefix, '__getitem__') or isinstance(self.prefix, (tk.PhotoImage, object)):
            lbl = tk.Label(container, image=self.prefix, bg=bg, padx=8, pady=4)
            lbl.image = self.prefix
            lbl.pack(side='left')
            lbl.bind('<Button-1>', lambda _e: self.entry.focus_set())
            self._p_lbl = lbl

    def _render_suffix_content(self, container, bg):
        if isinstance(self.suffix, str):
            if self.suffix in ('folder', 'folder_arrow_down', 'folder_download', 'folder_open', 'arrow_down_tray', 'close', 'link', 'search'):
                img = get_heroicon(self.suffix, size=16, color=BODY)
                lbl = tk.Label(container, image=img, bg=bg, padx=8, pady=4)
                lbl.image = img
                lbl.pack(side='left')
                lbl.bind('<Button-1>', lambda _e: self.entry.focus_set())
                self._s_lbl = lbl
            else:
                lbl = tk.Label(container, text=self.suffix, bg=bg, fg=MUTE,
                               font=self.app.font_sans(9, bold=True), padx=8, pady=4)
                lbl.pack(side='left')
                lbl.bind('<Button-1>', lambda _e: self.entry.focus_set())
                self._s_lbl = lbl

    def _render_action_button(self, container, act):
        label = act.get('label')
        icon = act.get('icon')
        cmd = act.get('command')
        tooltip = act.get('tooltip', '')

        btn_bg = CURRENT_PALETTE.get('PILL_SEC_BG', '#20202e')
        btn_bd = CURRENT_PALETTE.get('PILL_SEC_BORDER', '#36364a')
        btn_fg = CURRENT_PALETTE.get('PILL_SEC_FG', '#d4d4d8')

        btn = tk.Frame(container, bg=btn_bg, highlightthickness=1,
                       highlightbackground=btn_bd, cursor='hand2')
        btn.pack(side='left', padx=2, pady=1)

        inner_items = []
        if icon:
            ico_img = get_heroicon(icon, size=14, color=BODY)
            ico_lbl = tk.Label(btn, image=ico_img, bg=btn_bg, cursor='hand2')
            ico_lbl.image = ico_img
            ico_lbl.pack(side='left', padx=(6 if label else 5, 2 if label else 5), pady=3)
            inner_items.append((ico_lbl, 'icon', icon))

        if label:
            txt_lbl = tk.Label(btn, text=label, bg=btn_bg, fg=btn_fg,
                               font=self.app.font_sans(9, bold=True), cursor='hand2')
            txt_lbl.pack(side='left', padx=(2 if icon else 8, 8), pady=3)
            inner_items.append((txt_lbl, 'text', label))

        def _on_btn_h(enter):
            bg = CURRENT_PALETTE.get('PILL_SEC_HOVER_BG', '#2a2a3e') if enter else CURRENT_PALETTE.get('PILL_SEC_BG', '#20202e')
            bd = CURRENT_PALETTE.get('PILL_SEC_HOVER_BD', '#4f4f6b') if enter else CURRENT_PALETTE.get('PILL_SEC_BORDER', '#36364a')
            fg = CURRENT_PALETTE.get('PILL_SEC_HOVER_FG', '#ffffff') if enter else CURRENT_PALETTE.get('PILL_SEC_FG', '#d4d4d8')
            btn.configure(bg=bg, highlightbackground=bd)
            for w, kind, val in inner_items:
                if kind == 'text':
                    w.configure(bg=bg, fg=fg)
                elif kind == 'icon' and val:
                    w.configure(bg=bg, image=get_heroicon(val, size=14, color=LINK if enter else BODY))

        btn.bind('<Enter>', lambda _e: _on_btn_h(True))
        btn.bind('<Leave>', lambda _e: _on_btn_h(False))
        if cmd:
            btn.bind('<Button-1>', lambda _e: cmd())

        for w, _, _ in inner_items:
            w.bind('<Enter>', lambda _e: _on_btn_h(True))
            w.bind('<Leave>', lambda _e: _on_btn_h(False))
            if cmd:
                w.bind('<Button-1>', lambda _e: cmd())

        self._action_widgets.append(btn)
        self._action_items.append((btn, inner_items, act))

    def _bind_events(self):
        self.entry.bind('<FocusIn>', self._on_focus_in)
        self.entry.bind('<FocusOut>', self._on_focus_out)
        self.bind('<Enter>', lambda _e: self._on_hover(True))
        self.bind('<Leave>', lambda _e: self._on_hover(False))
        self.bind('<Button-1>', lambda _e: self.entry.focus_set())
        if self.on_return:
            self.entry.bind('<Return>', lambda _e: self.on_return(self.textvariable.get()))

    def retheme(self):
        self._bg_color = CURRENT_PALETTE.get('INPUT_BG', '#161622')
        self._border_color = CURRENT_PALETTE.get('INPUT_BORDER', '#2d2d3e')
        self._hover_border = CURRENT_PALETTE.get('INPUT_HOVER_BORDER', '#444458')
        self._focus_border = CURRENT_PALETTE.get('LINK', '#0a84ff')
        self.configure(bg=self._bg_color,
                       highlightbackground=self._focus_border if self._focused else (
                           self._hover_border if self._hovered else self._border_color))
        self.entry.configure(bg=self._bg_color, fg=INK, insertbackground=INK)
        box_bg = CURRENT_PALETTE.get('INPUT_BOX_BG', '#1c1c2b')
        if hasattr(self, '_p_box'):
            self._p_box.configure(bg=box_bg if self.prefix_styling else self._bg_color)
        if hasattr(self, '_p_lbl'):
            self._p_lbl.configure(bg=box_bg if self.prefix_styling else self._bg_color)
            if isinstance(self.prefix, str) and self.prefix in ('folder', 'folder_arrow_down', 'folder_download', 'folder_open', 'search', 'arrow_down_tray', 'link', 'tag', 'settings', 'clock', 'sparkles', 'tv'):
                img = get_heroicon(self.prefix, size=16, color=BODY)
                self._p_lbl.configure(image=img)
                self._p_lbl.image = img
            elif isinstance(self.prefix, str):
                self._p_lbl.configure(fg=MUTE)
        if hasattr(self, '_p_div'):
            self._p_div.configure(bg=self._border_color)
        if hasattr(self, '_s_box'):
            self._s_box.configure(bg=box_bg if self.suffix_container and self.suffix_styling else self._bg_color)
        if hasattr(self, '_s_div'):
            self._s_div.configure(bg=self._border_color)
        for btn, inner_items, act in getattr(self, '_action_items', []):
            btn_bg = CURRENT_PALETTE.get('PILL_SEC_BG', '#20202e')
            btn_bd = CURRENT_PALETTE.get('PILL_SEC_BORDER', '#36364a')
            btn_fg = CURRENT_PALETTE.get('PILL_SEC_FG', '#d4d4d8')
            btn.configure(bg=btn_bg, highlightbackground=btn_bd)
            for w, kind, val in inner_items:
                if kind == 'text':
                    w.configure(bg=btn_bg, fg=btn_fg)
                elif kind == 'icon' and val:
                    ico_img = get_heroicon(val, size=14, color=BODY)
                    w.configure(bg=btn_bg, image=ico_img)
                    w.image = ico_img

    def _on_focus_in(self, _e=None):
        self._focused = True
        self.configure(highlightbackground=self._focus_border)

    def _on_focus_out(self, _e=None):
        self._focused = False
        self.configure(highlightbackground=self._hover_border if self._hovered else self._border_color)

    def _on_hover(self, hover):
        self._hovered = hover
        if not self._focused:
            self.configure(highlightbackground=self._hover_border if hover else self._border_color)

    def get(self):
        return self.textvariable.get()

    def set(self, val):
        self.textvariable.set(val)


class GeistFolderInput(GeistInput):
    """Vercel / Geist UI Folder Selector Input Component."""
    def __init__(self, master, app, textvariable=None, on_browse=None, on_open=None,
                 placeholder='Choose download folder…', **kw):
        actions = []
        if on_browse:
            actions.append({
                'label': 'Browse',
                'icon': 'folder_open',
                'command': on_browse,
                'tooltip': 'Browse folder in file picker',
            })
        if on_open:
            actions.append({
                'label': 'Open',
                'icon': 'arrow_top_right_on_square',
                'command': on_open,
                'tooltip': 'Open folder in File Explorer',
            })

        super().__init__(
            master,
            app=app,
            textvariable=textvariable,
            placeholder=placeholder,
            prefix=None,
            prefix_styling=False,
            suffix_styling=True,
            suffix_container=True,
            actions=actions,
            **kw
        )



class GeistSelect(tk.Frame):
    """Vercel / Geist UI Design System Select Dropdown Component."""
    def __init__(self, master, app, textvariable=None, values=None,
                 placeholder='Select…', size='default',
                 aria_label=None, on_change=None,
                 bg=None, border=None,
                 hover_border=None, focus_border=None,
                 fg=None, state='normal', width=None, min_width=None, **kw):
        bg = bg or CURRENT_PALETTE.get('INPUT_BG', '#161622')
        border = border or CURRENT_PALETTE.get('INPUT_BORDER', '#2d2d3e')
        hover_border = hover_border or CURRENT_PALETTE.get('INPUT_HOVER_BORDER', '#444458')
        focus_border = focus_border or CURRENT_PALETTE.get('LINK', '#0a84ff')
        fg = fg or INK
        super().__init__(master, bg=bg, highlightthickness=1,
                         highlightbackground=border,
                         cursor='hand2' if state != 'disabled' else 'arrow', **kw)
        self.app = app
        self.textvariable = textvariable or tk.StringVar()
        self.placeholder = placeholder
        self.size = (size or 'default').lower()
        self.aria_label = aria_label or placeholder
        self.on_change = on_change
        self.select_state = state
        self._bg_color = bg
        self._border_color = border
        self._hover_border = hover_border
        self._focus_border = focus_border
        self._fg_color = fg
        self._is_open = False
        self._is_hovered = False
        self._popup = None
        self._raw_values = []
        self._val_pairs = []  # [(val, label)]
        self._width = width
        self._min_width = min_width

        # Determine typography, icon size, and padding based on size variant
        if self.size == 'small':
            self.font = app.font_sans(10)
            self._icon_size = 14
            self._pad_x = (10, 8)
            self._pad_y = 4
        elif self.size == 'large':
            self.font = app.font_sans(13)
            self._icon_size = 18
            self._pad_x = (14, 12)
            self._pad_y = 9
        else:  # 'default' / 'medium'
            self.font = app.font_sans(11)
            self._icon_size = 16
            self._pad_x = (12, 10)
            self._pad_y = 6

        self._build_ui()
        self.set_values(values or [])
        self._bind_events()

    def _build_ui(self):
        # Value Label
        self.label_var = tk.StringVar()
        self.lbl_text = tk.Label(
            self,
            textvariable=self.label_var,
            bg=self._bg_color,
            fg=self._fg_color,
            font=self.font,
            anchor='w',
            cursor='hand2' if self.select_state != 'disabled' else 'arrow'
        )
        if self._width:
            self.lbl_text.configure(width=self._width)
        self.lbl_text.pack(side='left', fill='x', expand=True,
                           padx=(self._pad_x[0], 4), pady=self._pad_y)

        # Chevron Icon
        self._ico_chevron = get_heroicon('chevron_down', size=self._icon_size, color=BODY)
        self.lbl_chevron = tk.Label(
            self,
            image=self._ico_chevron,
            bg=self._bg_color,
            cursor='hand2' if self.select_state != 'disabled' else 'arrow'
        )
        self.lbl_chevron.image = self._ico_chevron
        self.lbl_chevron.pack(side='right', padx=(0, self._pad_x[1]), pady=self._pad_y)

        self._sync_display()

    def retheme(self):
        self._bg_color = CURRENT_PALETTE.get('INPUT_BG', '#161622')
        self._border_color = CURRENT_PALETTE.get('INPUT_BORDER', '#2d2d3e')
        self._hover_border = CURRENT_PALETTE.get('INPUT_HOVER_BORDER', '#444458')
        self._focus_border = CURRENT_PALETTE.get('LINK', '#0a84ff')
        self._fg_color = INK
        self.configure(bg=self._bg_color,
                       highlightbackground=self._focus_border if self._is_open else (
                           self._hover_border if self._is_hovered else self._border_color))
        self.lbl_text.configure(bg=self._bg_color, fg=INK if self.textvariable.get() else FAINT)
        ico = get_heroicon('chevron_down', size=self._icon_size, color=BODY)
        self.lbl_chevron.configure(bg=self._bg_color, image=ico)
        self.lbl_chevron.image = ico

    def set_values(self, values):
        self._raw_values = values or []
        self._val_pairs = []
        for item in self._raw_values:
            if isinstance(item, (list, tuple)) and len(item) >= 2:
                self._val_pairs.append((str(item[0]), str(item[1])))
            else:
                self._val_pairs.append((str(item), str(item)))
        self._sync_display()

    def _sync_display(self):
        cur_val = self.textvariable.get()
        matched = False
        for v, l in self._val_pairs:
            if v == cur_val:
                self.label_var.set(l)
                self.lbl_text.configure(fg=self._fg_color)
                matched = True
                break
        if not matched:
            if cur_val:
                self.label_var.set(cur_val)
                self.lbl_text.configure(fg=self._fg_color)
            else:
                self.label_var.set(self.placeholder)
                self.lbl_text.configure(fg=FAINT)

    def _bind_events(self):
        for w in (self, self.lbl_text, self.lbl_chevron):
            w.bind('<Button-1>', self._on_click)
            w.bind('<Enter>', lambda _e: self._on_hover(True))
            w.bind('<Leave>', lambda _e: self._on_hover(False))

        self._trace_id = self.textvariable.trace_add('write', lambda *_: self._sync_display())

    def _on_hover(self, hover):
        if self.select_state == 'disabled':
            return
        self._is_hovered = hover
        if not self._is_open:
            self.configure(highlightbackground=self._hover_border if hover else self._border_color)
            chevron_color = INK if hover else BODY
            img = get_heroicon('chevron_down', size=self._icon_size, color=chevron_color)
            self.lbl_chevron.configure(image=img)
            self.lbl_chevron.image = img

    def _on_click(self, _e=None):
        if self.select_state == 'disabled':
            return
        if self._is_open:
            self.close_dropdown()
        else:
            self.open_dropdown()

    def open_dropdown(self):
        if self._is_open or self.select_state == 'disabled' or not self._val_pairs:
            return

        self._is_open = True
        self.configure(highlightbackground=self._focus_border)
        ico_up = get_heroicon('chevron_up', size=self._icon_size, color=LINK)
        self.lbl_chevron.configure(image=ico_up)
        self.lbl_chevron.image = ico_up

        top = self.winfo_toplevel()
        self._popup = tk.Toplevel(top)
        self._popup.overrideredirect(True)
        try:
            self._popup.wm_attributes('-topmost', True)
        except Exception:
            pass

        pop_bg = CURRENT_PALETTE.get('POPUP_BG', '#181826')
        pop_bd = CURRENT_PALETTE.get('POPUP_BORDER', '#36364c')
        act_bg = CURRENT_PALETTE.get('POPUP_ACTIVE_BG', '#0f2b48')
        act_bd = CURRENT_PALETTE.get('POPUP_ACTIVE_BD', '#2563eb')
        act_fg = CURRENT_PALETTE.get('POPUP_ACTIVE_FG', '#93c5fd')
        hov_bg = CURRENT_PALETTE.get('POPUP_HOVER_BG', '#222234')
        hov_bd = CURRENT_PALETTE.get('POPUP_HOVER_BD', '#32324a')

        p_frame = tk.Frame(self._popup, bg=pop_bg, highlightthickness=1,
                           highlightbackground=pop_bd)
        p_frame.pack(fill='both', expand=True)

        inner = tk.Frame(p_frame, bg=pop_bg)
        inner.pack(fill='both', expand=True, padx=3, pady=4)

        cur_val = self.textvariable.get()

        for val, lbl in self._val_pairs:
            is_active = (val == cur_val)
            row = tk.Frame(inner, bg=act_bg if is_active else pop_bg,
                           highlightthickness=1,
                           highlightbackground=act_bd if is_active else pop_bg,
                           cursor='hand2')
            row.pack(fill='x', pady=1)

            opt_lbl = tk.Label(
                row,
                text=lbl,
                bg=act_bg if is_active else pop_bg,
                fg=act_fg if is_active else INK,
                font=self.font,
                anchor='w',
                cursor='hand2'
            )
            opt_lbl.pack(side='left', fill='x', expand=True,
                         padx=(8, 6), pady=(self._pad_y - 1))

            if is_active:
                chk_img = get_heroicon('check', size=max(12, self._icon_size - 2), color=act_fg)
                chk_lbl = tk.Label(row, image=chk_img, bg=act_bg, cursor='hand2')
                chk_lbl.image = chk_img
                chk_lbl.pack(side='right', padx=(0, 6), pady=(self._pad_y - 1))
            else:
                chk_lbl = None

            def _make_hover_handlers(r, ol, cl, active):
                def _enter(_e):
                    if not active:
                        r.configure(bg=hov_bg, highlightbackground=hov_bd)
                        ol.configure(bg=hov_bg, fg=INK)
                def _leave(_e):
                    if not active:
                        r.configure(bg=pop_bg, highlightbackground=pop_bg)
                        ol.configure(bg=pop_bg, fg=INK)
                return _enter, _leave

            _ent, _lev = _make_hover_handlers(row, opt_lbl, chk_lbl, is_active)
            for w in filter(None, (row, opt_lbl, chk_lbl)):
                w.bind('<Enter>', _ent)
                w.bind('<Leave>', _lev)
                w.bind('<Button-1>', lambda _e, v=val: self._select_val(v))

        # Geometry positioning
        self.update_idletasks()
        self._popup.update_idletasks()

        rx = self.winfo_rootx()
        ry = self.winfo_rooty()
        rw = self.winfo_width()
        rh = self.winfo_height()

        req_w = max(rw, p_frame.winfo_reqwidth(), (self._min_width or 0))
        req_h = p_frame.winfo_reqheight()

        sh = self.winfo_screenheight()
        if ry + rh + req_h + 8 > sh:
            py = max(0, ry - req_h - 3)
        else:
            py = ry + rh + 3

        self._popup.geometry(f"{req_w}x{req_h}+{rx}+{py}")

        # Bind dismiss events
        self._dismiss_id = top.bind('<Button-1>', self._on_root_click, add='+')
        self._popup.bind('<Escape>', lambda _e: self.close_dropdown())
        self._popup.bind('<FocusOut>', lambda _e: self.close_dropdown())
        self._win_conf_id = top.bind('<Configure>', lambda _e: self.close_dropdown(), add='+')

    def _select_val(self, val):
        self.set(val)
        if self.on_change:
            try:
                self.on_change(val)
            except Exception as exc:
                print('GeistSelect on_change error:', exc)
        self.close_dropdown()

    def _on_root_click(self, event):
        if not self._is_open or not self._popup:
            return
        wx = self.winfo_rootx()
        wy = self.winfo_rooty()
        ww = self.winfo_width()
        wh = self.winfo_height()
        if wx <= event.x_root <= wx + ww and wy <= event.y_root <= wy + wh:
            return

        px = self._popup.winfo_rootx()
        py = self._popup.winfo_rooty()
        pw = self._popup.winfo_width()
        ph = self._popup.winfo_height()
        if not (px <= event.x_root <= px + pw and py <= event.y_root <= py + ph):
            self.close_dropdown()

    def close_dropdown(self):
        if not self._is_open:
            return
        self._is_open = False
        if self._popup:
            try:
                self._popup.destroy()
            except Exception:
                pass
            self._popup = None

        top = self.winfo_toplevel()
        try:
            if hasattr(self, '_dismiss_id') and self._dismiss_id:
                top.unbind('<Button-1>', self._dismiss_id)
        except Exception:
            pass
        try:
            if hasattr(self, '_win_conf_id') and self._win_conf_id:
                top.unbind('<Configure>', self._win_conf_id)
        except Exception:
            pass

        self.configure(highlightbackground=self._hover_border if self._is_hovered else self._border_color)
        chevron_color = INK if self._is_hovered else BODY
        ico_down = get_heroicon('chevron_down', size=self._icon_size, color=chevron_color)
        self.lbl_chevron.configure(image=ico_down)
        self.lbl_chevron.image = ico_down

    def get(self):
        return self.textvariable.get()

    def set(self, val):
        self.textvariable.set(val)
        self._sync_display()


# Geist component aliases matching @vercel/geistcn/components
Input = GeistInput
FolderInput = GeistFolderInput
Select = GeistSelect
Dropdown = GeistSelect


# ==============================================================================
# Liquid Glass In-App Update Modal
# ==============================================================================

class UpdateDialog(tk.Toplevel):
    """
    Modern Liquid Glass In-App Update Dialog.
    Allows user to review release details, download the new version directly in-app,
    and automatically restart to apply updates without navigating to GitHub.
    """
    def __init__(self, master, app, release_info, on_close=None):
        super().__init__(master)
        self.app = app
        self.info = release_info
        self.on_close = on_close
        self._cancel_event = threading.Event()
        self._download_thread = None
        self._is_downloading = False
        self._download_temp_path = None

        self.title("FetchX Update Available")
        self.configure(bg=CARD_BG)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        w, h = 540, 500
        self.geometry(f"{w}x{h}")
        self._center_window(w, h)
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _center_window(self, w, h):
        self.update_idletasks()
        try:
            pw = self.master.winfo_width()
            ph = self.master.winfo_height()
            px = self.master.winfo_rootx()
            py = self.master.winfo_rooty()
            x = px + max(0, (pw - w) // 2)
            y = py + max(0, (ph - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            pass

    def font_sans(self, size, bold=False):
        if hasattr(self.app, 'font_sans'):
            return self.app.font_sans(size, bold)
        return ('Segoe UI', size, 'bold' if bold else 'normal')

    def font_mono(self, size, bold=False):
        if hasattr(self.app, 'font_mono'):
            return self.app.font_mono(size, bold)
        return ('Consolas', size, 'bold' if bold else 'normal')

    def eyebrow(self, parent, text):
        if hasattr(self.app, 'eyebrow'):
            return self.app.eyebrow(parent, text)
        return tk.Label(parent, text=str(text).upper(), bg=CARD_BG, fg=MUTE,
                        font=self.font_sans(10, bold=True))

    def _build_ui(self):
        container = tk.Frame(self, bg=CARD_BG, padx=22, pady=18)
        container.pack(fill='both', expand=True)

        # Header Row
        head_row = tk.Frame(container, bg=CARD_BG)
        head_row.pack(fill='x', pady=(0, 12))

        ico_img = get_heroicon('sparkles', size=32, color=LINK)
        lbl_ico = tk.Label(head_row, image=ico_img, bg=CARD_BG)
        lbl_ico.image = ico_img
        lbl_ico.pack(side='left', padx=(0, 14))

        titles_box = tk.Frame(head_row, bg=CARD_BG)
        titles_box.pack(side='left', fill='x', expand=True)

        latest_ver = self.info.get('latest_version', 'latest')
        curr_ver = self.info.get('current_version', APP_VERSION)
        rel_name = self.info.get('release_name') or f'FetchX v{latest_ver}'

        tk.Label(titles_box, text=f'Update Available: v{latest_ver}',
                 bg=CARD_BG, fg=INK, font=self.font_sans(14, bold=True)).pack(anchor='w')
        tk.Label(titles_box, text=f'A new version is ready to install directly (Current: v{curr_ver})',
                 bg=CARD_BG, fg=MUTE, font=self.font_sans(9)).pack(anchor='w', pady=(2, 0))

        # Hairline
        tk.Frame(container, bg=HAIRLINE, height=1).pack(fill='x', pady=(0, 12))

        # Release notes header
        self.eyebrow(container, f"What's New in {rel_name}").pack(anchor='w', pady=(0, 6))

        # Release notes scrollable text
        notes_frame = tk.Frame(container, bg=ELEVATED, highlightthickness=1,
                               highlightbackground=HAIRLINE)
        notes_frame.pack(fill='both', expand=True, pady=(0, 10))

        notes_sb = ttk.Scrollbar(notes_frame, orient='vertical')
        notes_sb.pack(side='right', fill='y')

        txt_notes = tk.Text(notes_frame, bg=ELEVATED, fg=BODY, bd=0, highlightthickness=0,
                            font=self.font_sans(10), wrap='word',
                            yscrollcommand=notes_sb.set, padx=12, pady=10, height=8)
        txt_notes.pack(side='left', fill='both', expand=True)
        notes_sb.config(command=txt_notes.yview)

        raw_notes = self.info.get('release_notes') or 'No release notes provided.'
        txt_notes.insert('1.0', raw_notes.strip())
        txt_notes.configure(state='disabled')

        # Meta Row: Asset size & Published date
        meta_row = tk.Frame(container, bg=CARD_BG)
        meta_row.pack(fill='x', pady=(0, 14))

        size_bytes = self.info.get('asset_size', 0)
        size_str = f"{size_bytes / (1024 * 1024):.1f} MB" if size_bytes > 0 else "Source / Binary Package"
        pub_date = (self.info.get('published_at') or '')[:10]
        meta_text = f"Package Size: {size_str}" + (f"  •  Released: {pub_date}" if pub_date else "")

        tk.Label(meta_row, text=meta_text, bg=CARD_BG, fg=MUTE,
                 font=self.font_mono(9)).pack(side='left')

        # Progress Section (Canvas Bar + Status Text)
        self.prog_box = tk.Frame(container, bg=CARD_BG)
        self.prog_box.pack(fill='x', pady=(0, 12))

        self.lbl_prog_status = tk.Label(self.prog_box, text='Ready to update directly', bg=CARD_BG,
                                        fg=BODY, font=self.font_sans(9, bold=True))
        self.lbl_prog_status.pack(anchor='w')

        self.lbl_prog_speed = tk.Label(self.prog_box, text='', bg=CARD_BG,
                                       fg=MUTE, font=self.font_mono(9))
        self.lbl_prog_speed.pack(anchor='e', pady=(0, 4))

        self.prog_canvas = tk.Canvas(self.prog_box, bg=PROGRESS_TROUGH, height=6, bd=0, highlightthickness=0)
        self.prog_canvas.pack(fill='x')
        self._prog_rect = self.prog_canvas.create_rectangle(0, 0, 0, 6, fill=PROGRESS_BAR, width=0)

        # Bottom Action Buttons
        bot_bar = tk.Frame(container, bg=CARD_BG)
        bot_bar.pack(fill='x', pady=(4, 0))

        # Remind later button
        self.btn_later = tk.Frame(bot_bar, bg=PILL_SEC_BG, highlightthickness=1,
                                  highlightbackground=PILL_SEC_BORDER, cursor='hand2', padx=14, pady=7)
        self.btn_later.pack(side='left')
        self.lbl_later = tk.Label(self.btn_later, text='Remind Later', bg=PILL_SEC_BG,
                                  fg=PILL_SEC_FG, font=self.font_sans(10, bold=True), cursor='hand2')
        self.lbl_later.pack()

        # Update Now Button
        self.btn_update = tk.Frame(bot_bar, bg=PILL_PRI_BG, highlightthickness=1,
                                   highlightbackground=PILL_PRI_BORDER, cursor='hand2', padx=18, pady=7)
        self.btn_update.pack(side='right')
        self.lbl_update = tk.Label(self.btn_update, text='Update Now', bg=PILL_PRI_BG,
                                   fg=PILL_PRI_FG, font=self.font_sans(10, bold=True), cursor='hand2')
        self.lbl_update.pack()

        # Bindings
        def _on_later_hover(enter):
            bg = PILL_SEC_HOVER_BG if enter else PILL_SEC_BG
            bd = PILL_SEC_HOVER_BD if enter else PILL_SEC_BORDER
            fg = PILL_SEC_HOVER_FG if enter else PILL_SEC_FG
            self.btn_later.configure(bg=bg, highlightbackground=bd)
            self.lbl_later.configure(bg=bg, fg=fg)

        def _on_update_hover(enter):
            if self._is_downloading:
                return
            bg = PILL_PRI_HOVER_BG if enter else PILL_PRI_BG
            bd = PILL_PRI_HOVER_BD if enter else PILL_PRI_BORDER
            fg = PILL_PRI_HOVER_FG if enter else PILL_PRI_FG
            self.btn_update.configure(bg=bg, highlightbackground=bd)
            self.lbl_update.configure(bg=bg, fg=fg)

        for w in (self.btn_later, self.lbl_later):
            w.bind('<Enter>', lambda _e: _on_later_hover(True))
            w.bind('<Leave>', lambda _e: _on_later_hover(False))
            w.bind('<Button-1>', lambda _e: self._on_cancel())

        for w in (self.btn_update, self.lbl_update):
            w.bind('<Enter>', lambda _e: _on_update_hover(True))
            w.bind('<Leave>', lambda _e: _on_update_hover(False))
            w.bind('<Button-1>', lambda _e: self._start_update_download())

    def _update_progress_bar(self, frac):
        try:
            w = self.prog_canvas.winfo_width()
            bar_w = int(w * max(0.0, min(1.0, frac)))
            self.prog_canvas.coords(self._prog_rect, 0, 0, bar_w, 6)
        except Exception:
            pass

    def _start_update_download(self):
        if self._is_downloading:
            return
        self._is_downloading = True
        self.lbl_update.configure(text='Downloading…')
        self.btn_update.configure(cursor='watch')
        self.lbl_update.configure(cursor='watch')

        asset_url = self.info.get('asset_url')
        if not asset_url:
            self.lbl_prog_status.configure(text='Error: No download asset URL found in release.', fg='#ee0000')
            self._is_downloading = False
            self.lbl_update.configure(text='Retry')
            return

        ext = '.exe' if asset_url.lower().endswith('.exe') else '.zip'
        temp_dir = tempfile.gettempdir()
        target_path = os.path.join(temp_dir, f'fetchx_update_{int(time.time())}{ext}')
        self._download_temp_path = target_path

        def worker():
            def on_prog(downloaded, total, speed, pct):
                def _ui():
                    frac = (pct / 100.0) if pct > 0 else 0.0
                    self._update_progress_bar(frac)
                    d_mb = downloaded / (1024 * 1024)
                    t_mb = total / (1024 * 1024) if total > 0 else 0
                    s_mb = speed / (1024 * 1024)
                    self.lbl_prog_status.configure(text=f'Downloading update… {pct:.1f}%', fg=LINK)
                    self.lbl_prog_speed.configure(text=f'{d_mb:.1f} MB / {t_mb:.1f} MB  ({s_mb:.1f} MB/s)')
                self.after(0, _ui)

            try:
                ok = updater.download_update(
                    asset_url,
                    target_path,
                    progress_callback=on_prog,
                    cancel_event=self._cancel_event
                )
                if ok:
                    def _on_success():
                        self.lbl_prog_status.configure(text='Download complete! Restarting to apply update…', fg='#22c55e')
                        self.lbl_update.configure(text='Applying…')
                        self.after(800, self._apply_and_restart)
                    self.after(0, _on_success)
            except Exception as exc:
                def _on_err():
                    self._is_downloading = False
                    self.lbl_prog_status.configure(text=f'Download failed: {exc}', fg='#ee0000')
                    self.lbl_update.configure(text='Retry')
                    self.btn_update.configure(cursor='hand2')
                    self.lbl_update.configure(cursor='hand2')
                self.after(0, _on_err)

        self._download_thread = threading.Thread(target=worker, daemon=True)
        self._download_thread.start()

    def _apply_and_restart(self):
        try:
            updater.apply_update_and_restart(self._download_temp_path, on_shutdown=self.app.destroy)
        except Exception as exc:
            self.lbl_prog_status.configure(text=f'Failed to apply update: {exc}', fg='#ee0000')
            self._is_downloading = False
            self.lbl_update.configure(text='Retry')

    def _on_cancel(self):
        if self._is_downloading:
            self._cancel_event.set()
        if self.on_close:
            try:
                self.on_close()
            except Exception:
                pass
        self.destroy()


# ==============================================================================
# JobRow - Downloads Queue Card (macOS List Row Style)
# ==============================================================================

class JobRow:
    """One queued video rendered as a clean liquid glass row card."""

    STATE_FG = {
        'done': SUCCESS,
        'ready': LINK,
        'blocked': WARNING_DEEP,
        'error': ERROR,
        'cancelled': WARNING,
        'queued': FAINT,
        'resolving': BODY,
        'downloading': LINK,
    }

    def __init__(self, app, url, index):
        self.app = app
        self.url = url
        self.index = index
        self.site_cls = pick_site_class(url)
        self.crawler = None
        self.state = 'queued'
        self.cancelled = False
        self.links = {}
        self.auto_watch = False
        self.auto_download = False

        site_name = _SITE_LABEL.get(self.site_cls, '?')

        self.frame = tk.Frame(app.queue_inner, bg=CARD_BG,
                              highlightthickness=1, highlightbackground=CARD_BORDER)
        self.frame.pack(fill='x', padx=4, pady=6)
        inner = tk.Frame(self.frame, bg=CARD_BG)
        inner.pack(fill='both', expand=True, padx=16, pady=14)

        # Top row: Site chip + Title + Status badge
        top = tk.Frame(inner, bg=CARD_BG)
        top.pack(fill='x')

        chip = tk.Label(top, text=f' {site_name} ', bg=HAIRLINE_SOFT, fg=BODY,
                        font=app.font_mono(10))
        chip.pack(side='left')

        self.lbl_title = tk.Label(top, text=url, bg=CARD_BG, fg=INK,
                                  anchor='w', font=app.font_sans(11, bold=True))
        self.lbl_title.pack(side='left', fill='x', expand=True, padx=(10, 8))

        self.lbl_status = tk.Label(top, text='queued', bg=CARD_BG, fg=FAINT,
                                   anchor='e', font=app.font_mono(10))
        self.lbl_status.pack(side='left')

        # Mid row: Progress bar + Percentage
        mid = tk.Frame(inner, bg=CARD_BG)
        mid.pack(fill='x', pady=(10, 0))
        self.bar = ttk.Progressbar(mid, mode='determinate', maximum=100,
                                   value=0, style='Blue.Horizontal.TProgressbar')
        self.bar.pack(side='left', fill='x', expand=True)
        self.pct_lbl = tk.Label(mid, text='', bg=CARD_BG, fg=BODY,
                                width=6, anchor='e', font=app.font_mono(10))
        self.pct_lbl.pack(side='left', padx=(8, 0))

        # Bottom row: Stream info + Liquid Glass Action buttons
        bot = tk.Frame(inner, bg=CARD_BG)
        bot.pack(fill='x', pady=(10, 0))
        self.lbl_stream = tk.Label(bot, text='', bg=CARD_BG, fg=MUTE,
                                   anchor='w', font=app.font_mono(10))
        self.lbl_stream.pack(side='left', fill='x', expand=True)

        self._ready = False

        # Copy link pill
        self.btn_copy = tk.Frame(bot, bg=ELEVATED, highlightthickness=1,
                                 highlightbackground=HAIRLINE, cursor='arrow')
        self.btn_copy.pack(side='left')
        self.lbl_copy = tk.Label(self.btn_copy, text='Copy link', bg=ELEVATED,
                                 fg=FAINT, font=app.font_sans(8, bold=True),
                                 cursor='arrow', padx=8, pady=2)
        self.lbl_copy.pack()

        def _on_copy_hover(enter):
            if not self._ready:
                return
            bg = PILL_SEC_HOVER_BG if enter else PILL_SEC_BG
            bd = PILL_SEC_HOVER_BD if enter else PILL_SEC_BORDER
            fg = PILL_SEC_HOVER_FG if enter else PILL_SEC_FG
            self.btn_copy.configure(bg=bg, highlightbackground=bd)
            self.lbl_copy.configure(bg=bg, fg=fg)

        for w in (self.btn_copy, self.lbl_copy):
            w.bind('<Button-1>', lambda _e: self._trigger_copy())
            w.bind('<Enter>', lambda _e: _on_copy_hover(True))
            w.bind('<Leave>', lambda _e: _on_copy_hover(False))

        # Watch pill
        self.btn_play = tk.Frame(bot, bg=ELEVATED, highlightthickness=1,
                                 highlightbackground=HAIRLINE, cursor='arrow')
        self.btn_play.pack(side='left', padx=(6, 0))
        self.lbl_play = tk.Label(self.btn_play, text='▶ Watch', bg=ELEVATED,
                                 fg=FAINT, font=app.font_sans(8, bold=True),
                                 cursor='arrow', padx=8, pady=2)
        self.lbl_play.pack()

        def _on_play_hover(enter):
            if not self._ready:
                return
            bg=PILL_PRI_HOVER_BG if enter else PILL_PRI_BG
            bd = PILL_PRI_HOVER_BD if enter else PILL_PRI_BORDER
            fg = PILL_PRI_HOVER_FG if enter else PILL_PRI_FG
            self.btn_play.configure(bg=bg, highlightbackground=bd)
            self.lbl_play.configure(bg=bg, fg=fg)

        for w in (self.btn_play, self.lbl_play):
            w.bind('<Button-1>', lambda _e: self._trigger_play())
            w.bind('<Enter>', lambda _e: _on_play_hover(True))
            w.bind('<Leave>', lambda _e: _on_play_hover(False))

        # Download pill
        self.btn_dl = tk.Frame(bot, bg=ELEVATED, highlightthickness=1,
                               highlightbackground=HAIRLINE, cursor='arrow')
        self.btn_dl.pack(side='left', padx=(6, 0))
        self.lbl_dl = tk.Label(self.btn_dl, text='Download', bg=ELEVATED,
                               fg=FAINT, font=app.font_sans(8, bold=True),
                               cursor='arrow', padx=8, pady=2)
        self.lbl_dl.pack()

        def _on_dl_hover(enter):
            if not self._ready:
                return
            if getattr(self, 'state', '') == 'downloading':
                bg = PILL_PRI_HOVER_BG if enter else PILL_PRI_BG
                bd = PILL_PRI_HOVER_BD if enter else PILL_PRI_BORDER
                fg = PILL_PRI_HOVER_FG if enter else PILL_PRI_FG
            else:
                bg=PILL_SUC_HOVER_BG if enter else PILL_SUC_BG
                bd = PILL_SUC_HOVER_BD if enter else PILL_SUC_BORDER
                fg = PILL_SUC_HOVER_FG if enter else PILL_SUC_FG
            self.btn_dl.configure(bg=bg, highlightbackground=bd)
            self.lbl_dl.configure(bg=bg, fg=fg)

        for w in (self.btn_dl, self.lbl_dl):
            w.bind('<Button-1>', lambda _e: self._trigger_download())
            w.bind('<Enter>', lambda _e: _on_dl_hover(True))
            w.bind('<Leave>', lambda _e: _on_dl_hover(False))

        # Heroicon remove button
        del_img = get_heroicon('close', size=18, color=BODY)
        self.btn_del = tk.Label(bot, image=del_img, bg=CARD_BG, cursor='hand2', padx=5, pady=2)
        self.btn_del.image = del_img
        self.btn_del.pack(side='left', padx=(6, 0))
        self.btn_del.bind('<Button-1>', lambda _e: self.remove())
        self.btn_del.bind('<Enter>', lambda _e: self.btn_del.configure(
            image=get_heroicon('close', size=18, color=ERROR)))
        self.btn_del.bind('<Leave>', lambda _e: self.btn_del.configure(
            image=get_heroicon('close', size=18, color=BODY)))

        self._wrap_to_width(self.lbl_title)
        self._wrap_to_width(self.lbl_stream)

    @staticmethod
    def _wrap_to_width(label):
        label.bind('<Configure>',
                   lambda e: label.configure(wraplength=max(80, e.width - 4)))

    def current_link(self):
        if not self.crawler:
            return ''
        links = self.crawler.stream_links() or {}
        for key in ('HLS master', 'mp4'):
            if key in links:
                return links[key]
        return next(iter(links.values()), '')

    def copy_link(self):
        link = self.current_link()
        if link:
            self.app.clipboard_clear()
            self.app.clipboard_append(link)
            self.app.say('Stream link copied \u2014 paste it into any player.')

    def play_stream(self):
        self.app.open_player_for_row(self)

    def download_now(self):
        if self.state == 'ready' and self.crawler is not None and self.crawler.is_url_vaildate():
            self.app.start_rows([self])
        else:
            self.cancelled = False
            self.auto_download = True
            self.lbl_status.configure(text='resuming…', fg=LINK)
            self.app.resolver_pool.submit(self.app._resolve_row, self)

    def _trigger_copy(self):
        if self.state == 'done' and getattr(self, 'target_path', ''):
            self.app._reveal_history_file(self.target_path)
        elif self._ready:
            self.copy_link()

    def _trigger_play(self):
        if self.state == 'done' and getattr(self, 'target_path', '') and os.path.exists(self.target_path):
            self.app._play_history_file(self.target_path)
        elif self._ready:
            self.play_stream()

    def _trigger_download(self):
        if self.state == 'done' and getattr(self, 'target_path', '') and os.path.exists(self.target_path):
            self.app._play_history_file(self.target_path)
        elif self._ready and self.state != 'downloading':
            self.download_now()

    def set_ready(self):
        self._ready = True
        self.btn_copy.configure(bg=PILL_SEC_BG, highlightbackground=PILL_SEC_BORDER, cursor='hand2')
        self.lbl_copy.configure(bg=PILL_SEC_BG, fg=PILL_SEC_FG, text='Copy link', cursor='hand2')

        self.btn_play.configure(bg=PILL_PRI_BG, highlightbackground=PILL_PRI_BORDER, cursor='hand2')
        self.lbl_play.configure(bg=PILL_PRI_BG, fg=PILL_PRI_FG, text='▶ Watch', cursor='hand2')

        self.btn_dl.configure(bg=PILL_SUC_BG, highlightbackground=PILL_SUC_BORDER, cursor='hand2')
        self.lbl_dl.configure(bg=PILL_SUC_BG, fg=PILL_SUC_FG, text='Download', cursor='hand2')

        links = (self.crawler.stream_links() if (self.crawler and hasattr(self.crawler, 'stream_links')) else {}) or {}
        self.links = links
        if links:
            self.lbl_stream.configure(
                text='streams:  ' + '   '.join(links.keys()))

    def set_downloading(self):
        self._ready = True
        self.btn_dl.configure(bg=PILL_PRI_BG, highlightbackground=PILL_PRI_BORDER, cursor='hand2')
        self.lbl_dl.configure(bg=PILL_PRI_BG, fg=PILL_PRI_FG, text='Downloading…', cursor='hand2')

    def set_resumable(self):
        self._ready = True
        self.btn_copy.configure(bg=PILL_SEC_BG, highlightbackground=PILL_SEC_BORDER, cursor='hand2')
        self.lbl_copy.configure(bg=PILL_SEC_BG, fg=PILL_SEC_FG, text='Copy link', cursor='hand2')

        self.btn_play.configure(bg=PILL_PRI_BG, highlightbackground=PILL_PRI_BORDER, cursor='hand2')
        self.lbl_play.configure(bg=PILL_PRI_BG, fg=PILL_PRI_FG, text='▶ Watch', cursor='hand2')

        self.btn_dl.configure(bg=PILL_SUC_BG, highlightbackground=PILL_SUC_BORDER, cursor='hand2')
        self.lbl_dl.configure(bg=PILL_SUC_BG, fg=PILL_SUC_FG, text='▶ Resume', cursor='hand2')

    def set_done(self, path=''):
        self._ready = True
        self.state = 'done'
        self.target_path = path or getattr(self, 'target_path', '')
        self.bar.configure(value=100)
        self.pct_lbl.configure(text='100%', fg=SUCCESS)
        self.lbl_status.configure(text='completed', fg=SUCCESS)

        filename = os.path.basename(self.target_path) if self.target_path else ''
        if filename:
            self.lbl_stream.configure(text=f'saved:  {filename}')
        else:
            self.lbl_stream.configure(text='saved to disk')

        self.btn_copy.configure(bg=PILL_SEC_BG, highlightbackground=PILL_SEC_BORDER, cursor='hand2')
        self.lbl_copy.configure(bg=PILL_SEC_BG, fg=PILL_SEC_FG, text='📁 Open Folder', cursor='hand2')

        self.btn_play.configure(bg=PILL_PRI_BG, highlightbackground=PILL_PRI_BORDER, cursor='hand2')
        self.lbl_play.configure(bg=PILL_PRI_BG, fg=PILL_PRI_FG, text='▶ Play File', cursor='hand2')

        self.btn_dl.configure(bg=PILL_SUC_BG, highlightbackground=PILL_SUC_BORDER, cursor='hand2')
        self.lbl_dl.configure(bg=PILL_SUC_BG, fg=PILL_SUC_FG, text='✓ Finished', cursor='hand2')

    def remove(self):
        self.cancelled = True
        if self.crawler is not None:
            self.crawler._cancel_job = True
        self.app.remove_row(self)


# ==============================================================================
# VideoCard - Responsive Liquid Glass Video Grid Card
# ==============================================================================

class VideoCard(tk.Frame):
    """Browse-grid card: 16:9 thumbnail preview, frosted duration capsule, Heroicon actions."""

    IMG_W = 300
    IMG_H = 168

    def __init__(self, app, parent, item):
        super().__init__(parent, bg=CARD_BG, highlightthickness=1,
                         highlightbackground=CARD_BORDER, cursor='hand2')
        self.app = app
        self.item = item
        self.photo = None
        self._src = None
        self.card_w = self.IMG_W
        self._rendered_w = 0

        self.bind('<Enter>', lambda _e: self._on_hover(True))
        self.bind('<Leave>', lambda _e: self._on_hover(False))

        # Thumbnail container with subtle inset border and background
        img_wrap = tk.Frame(self, bg=THUMB_BLANK_BG, height=self.IMG_H,
                            highlightthickness=1, highlightbackground=CARD_BORDER)
        self.img_wrap = img_wrap
        img_wrap.pack(fill='x', padx=6, pady=(6, 0))
        img_wrap.pack_propagate(False)
        img_wrap.bind('<Configure>', self._on_wrap_configure)

        self.img_lbl = tk.Label(img_wrap, bg=THUMB_BLANK_BG, fg=MUTE, text='…',
                                font=app.font_sans(10), bd=0, padx=0, pady=0)
        self.img_lbl.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        # Duration badge (bottom-right liquid glass capsule)
        duration = str(item.get('duration') or '').strip()
        self.badge = None
        if duration:
            self.badge = tk.Label(img_wrap, text=f' {duration} ', bg=MEDIA_OVERLAY_BG,
                                   fg=MEDIA_OVERLAY_FG, font=app.font_mono(8, bold=True),
                                   highlightthickness=1, highlightbackground=MEDIA_OVERLAY_BD,
                                  padx=5, pady=2)
            self.badge.place(relx=1.0, rely=1.0, x=-7, y=-7, anchor='se')

        # Site source chip (top-right liquid frosted glass chip)
        site = str(item.get('site_name') or '').upper()
        self.chip = None
        if site:
            self.chip = tk.Label(img_wrap, text=f' {site} ', bg=MEDIA_CHIP_BG,
                                  fg=MEDIA_CHIP_FG, font=app.font_mono(8, bold=True),
                                  highlightthickness=1, highlightbackground=MEDIA_CHIP_BD,
                                 padx=6, pady=2)
            self.chip.place(relx=1.0, rely=0.0, x=-7, y=7, anchor='ne')

        # Quality badge (top-left liquid sapphire glass badge)
        tags = []
        is_4k = bool(item.get('is_4k'))
        is_hd = bool(item.get('is_hd'))
        if is_4k:
            tags.append('4K')
        elif is_hd:
            tags.append('HD')
        self.q_badge = None
        if tags:
            q_bg = PILL_PRI_BG if is_4k else LINK_SOFT
            q_fg = LINK if is_4k else LINK
            q_border = PILL_PRI_BORDER if is_4k else LINK
            self.q_badge = tk.Label(img_wrap, text=f' {" ".join(tags)} ', bg=q_bg,
                                    fg=q_fg, font=app.font_mono(8, bold=True),
                                    highlightthickness=1, highlightbackground=q_border,
                                    padx=6, pady=2)
            self.q_badge.place(relx=0.0, rely=0.0, x=7, y=7, anchor='nw')

        # Card body
        inner = tk.Frame(self, bg=CARD_BG)
        inner.pack(fill='both', expand=True, padx=10, pady=(8, 10))
        self.inner = inner

        title = str(item.get('title') or '').strip() or '(untitled)'
        self.title_lbl = tk.Label(inner, text=title,
                                  height=2, wraplength=self.IMG_W - 24,
                                  justify='left', anchor='nw',
                                  bg=CARD_BG, fg=INK,
                                  font=app.font_sans(10, bold=True))
        self.title_lbl.pack(side='top', fill='x')

        # Card action footer (pinned to bottom of card)
        foot = tk.Frame(inner, bg=CARD_BG)
        foot.pack(side='bottom', fill='x', pady=(8, 0))
        self.foot = foot

        dl_img = get_heroicon('download', size=26, color=BODY)
        self.btn_dl_icon = tk.Label(foot, image=dl_img, bg=CARD_BG, cursor='hand2', padx=4, pady=2)
        self.btn_dl_icon.image = dl_img
        self.btn_dl_icon.pack(side='left')

        # Save / Watch Later Bookmark Icon Button
        url = str(item.get('url') or '')
        is_saved = config.is_video_saved(url)
        save_col = LINK if is_saved else BODY
        save_img = get_heroicon('bookmark_solid' if is_saved else 'bookmark', size=24, color=save_col)
        self.btn_save_icon = tk.Label(foot, image=save_img, bg=CARD_BG, cursor='hand2', padx=4, pady=2)
        self.btn_save_icon.image = save_img
        self.btn_save_icon.pack(side='left', padx=(4, 0))

        def _on_save_icon_hover(enter):
            u = str(self.item.get('url') or '')
            saved = config.is_video_saved(u)
            if saved:
                col = LINK_HOVER if enter else LINK
                img = get_heroicon('bookmark_solid', size=24, color=col)
            else:
                col = LINK if enter else BODY
                img = get_heroicon('bookmark', size=24, color=col)
            self.btn_save_icon.configure(image=img)
            self.btn_save_icon.image = img

        def _on_save_icon_click(_e=None):
            u = str(self.item.get('url') or '')
            t = str(self.item.get('title') or u)
            was_saved = config.is_video_saved(u)
            if was_saved:
                config.remove_saved_video(u)
                img = get_heroicon('bookmark', size=24, color=BODY)
                self.btn_save_icon.configure(image=img)
                self.btn_save_icon.image = img
                self.app.show_toast(f'Removed "{t[:36]}" from Watch Later', icon='bookmark', color=MUTE)
            else:
                config.add_saved_video(dict(self.item))
                img = get_heroicon('bookmark_solid', size=24, color=LINK)
                self.btn_save_icon.configure(image=img)
                self.btn_save_icon.image = img
                self.app.show_toast(f'Saved "{t[:36]}" to Watch Later', icon='bookmark', color=LINK)
            self.app._on_watch_later_updated(u)

        self.btn_save_icon.bind('<Button-1>', _on_save_icon_click)
        self.btn_save_icon.bind('<Enter>', lambda _e: _on_save_icon_hover(True))
        self.btn_save_icon.bind('<Leave>', lambda _e: _on_save_icon_hover(False))

        def _on_dl_icon_hover(enter):
            if getattr(self, '_dl_state', '') == 'downloading':
                return
            if getattr(self, '_dl_state', '') == 'done':
                img = get_heroicon('check', size=26, color='#4ade80')
            elif enter:
                img = get_heroicon('download', size=26, color=LINK)
            else:
                c = '#a1a1aa' if getattr(self, '_dl_state', '') == 'queued' else BODY
                img = get_heroicon('download', size=26, color=c)
            self.btn_dl_icon.configure(image=img)
            self.btn_dl_icon.image = img

        self.btn_dl_icon.bind('<Button-1>', lambda _e: app.download_item(self.item, self))
        self.btn_dl_icon.bind('<Enter>', lambda _e: _on_dl_icon_hover(True))
        self.btn_dl_icon.bind('<Leave>', lambda _e: _on_dl_icon_hover(False))

        # Liquid Glass Watch Button (Neon Sapphire Pill)
        self.btn_watch = tk.Frame(foot, bg=PILL_PRI_BG, highlightthickness=1,
                                  highlightbackground=PILL_PRI_BORDER, cursor='hand2')
        self.btn_watch.pack(side='right')
        self.lbl_watch = tk.Label(self.btn_watch, text='▶ Watch', bg=PILL_PRI_BG,
                                  fg=PILL_PRI_FG, font=app.font_sans(9, bold=True),
                                  cursor='hand2', padx=10, pady=3)
        self.lbl_watch.pack()

        def _on_watch_hover(enter):
            if getattr(self, '_busy', False):
                return
            bg=PILL_PRI_HOVER_BG if enter else PILL_PRI_BG
            bd = PILL_PRI_HOVER_BD if enter else PILL_PRI_BORDER
            fg = PILL_PRI_HOVER_FG if enter else PILL_PRI_FG
            self.btn_watch.configure(bg=bg, highlightbackground=bd)
            self.lbl_watch.configure(bg=bg, fg=fg)

        for w in (self.btn_watch, self.lbl_watch):
            w.bind('<Button-1>', lambda _e: self._trigger_watch())
            w.bind('<Enter>', lambda _e: _on_watch_hover(True))
            w.bind('<Leave>', lambda _e: _on_watch_hover(False))

        # Liquid Glass Queue Button (Frosted Quartz Pill)
        self.btn_queue = tk.Frame(foot, bg=PILL_SEC_BG, highlightthickness=1,
                                  highlightbackground=PILL_SEC_BORDER, cursor='hand2')
        self.btn_queue.pack(side='right', padx=(0, 6))
        self.lbl_queue = tk.Label(self.btn_queue, text='+ Queue', bg=PILL_SEC_BG,
                                  fg=PILL_SEC_FG, font=app.font_sans(9, bold=True),
                                  cursor='hand2', padx=9, pady=3)
        self.lbl_queue.pack()

        def _on_queue_hover(enter):
            bg = PILL_SEC_HOVER_BG if enter else PILL_SEC_BG
            bd = PILL_SEC_HOVER_BD if enter else PILL_SEC_BORDER
            fg = PILL_SEC_HOVER_FG if enter else PILL_SEC_FG
            self.btn_queue.configure(bg=bg, highlightbackground=bd)
            self.lbl_queue.configure(bg=bg, fg=fg)

        for w in (self.btn_queue, self.lbl_queue):
            w.bind('<Button-1>', lambda _e: app.queue_item(self.item))
            w.bind('<Enter>', lambda _e: _on_queue_hover(True))
            w.bind('<Leave>', lambda _e: _on_queue_hover(False))

        # Sync initial state if url is already downloading or queued
        row = app._row_for_url(item.get('url', ''))
        if row is not None:
            if row.state == 'downloading':
                self.set_download_state('downloading')
            elif row.state in ('queued', 'resolving', 'ready'):
                self.set_download_state('queued')
            elif row.state == 'done':
                self.set_download_state('done')

        for w in (self, img_wrap, self.img_lbl, inner, self.title_lbl):
            w.bind('<Double-1>', lambda _e: app.watch_item(self.item, self))
            w.bind('<Enter>', lambda _e: self._on_hover(True), add='+')
            w.bind('<Leave>', lambda _e: self._on_hover(False), add='+')

    def _trigger_watch(self):
        if not getattr(self, '_busy', False):
            self.app.watch_item(self.item, self)

    def _on_wrap_configure(self, event=None):
        if event is not None and hasattr(event, 'width'):
            w = event.width
        else:
            w = self.img_wrap.winfo_width()
        if w > 50 and abs(w - self._rendered_w) >= 4:
            self.after_idle(self._render_image)

    def _on_hover(self, enter):
        border = CARD_BORDER_HOVER if enter else CARD_BORDER
        bg = CARD_HOVER if enter else CARD_BG
        self.configure(highlightbackground=border, bg=bg)
        try:
            self.inner.configure(bg=bg)
            self.title_lbl.configure(bg=bg)
            self.foot.configure(bg=bg)
            self.btn_dl_icon.configure(bg=bg)
            self.btn_save_icon.configure(bg=bg)
        except Exception:
            pass

    def set_save_state(self, is_saved):
        if not bool(self.winfo_exists()) or not bool(getattr(self, 'btn_save_icon', None)):
            return
        col = LINK if is_saved else BODY
        img = get_heroicon('bookmark_solid' if is_saved else 'bookmark', size=24, color=col)
        self.btn_save_icon.configure(image=img)
        self.btn_save_icon.image = img

    def set_download_state(self, state):
        self._dl_state = state
        if not bool(self.winfo_exists()) or not bool(getattr(self, 'btn_dl_icon', None)):
            return
        if state == 'downloading':
            img = get_heroicon('download', size=26, color='#38bdf8')
            self.btn_dl_icon.configure(image=img)
            self.btn_dl_icon.image = img
        elif state == 'queued':
            img = get_heroicon('download', size=26, color='#a1a1aa')
            self.btn_dl_icon.configure(image=img)
            self.btn_dl_icon.image = img
        elif state == 'done':
            img = get_heroicon('check', size=26, color='#4ade80')
            self.btn_dl_icon.configure(image=img)
            self.btn_dl_icon.image = img
        else:
            img = get_heroicon('download', size=26, color=BODY)
            self.btn_dl_icon.configure(image=img)
            self.btn_dl_icon.image = img

    def set_busy(self, text='Resolving…'):
        self._busy = True
        if bool(self.winfo_exists()):
            self.btn_watch.configure(bg=ELEVATED, highlightbackground=HAIRLINE)
            self.lbl_watch.configure(bg=ELEVATED, fg=MUTE, text=text)
            if 'download' in str(text).lower():
                self.set_download_state('downloading')

    def set_idle(self):
        self._busy = False
        if bool(self.winfo_exists()):
            self.btn_watch.configure(bg=PILL_PRI_BG, highlightbackground=PILL_PRI_BORDER)
            self.lbl_watch.configure(bg=PILL_PRI_BG, fg=PILL_PRI_FG, text='▶ Watch')
            if getattr(self, '_dl_state', '') == 'downloading':
                self.set_download_state('downloading')

    def apply_image(self, pil_image):
        if not bool(self.winfo_exists()) or pil_image is None:
            return
        self._src = pil_image
        self._render_image()

    def set_width(self, w):
        w = max(200, int(w))
        self.card_w = w
        try:
            self.title_lbl.configure(wraplength=max(80, w - 24))
        except Exception:
            pass
        # NOTE: Image (re)rendering is driven by the img_wrap '<Configure>' event
        # (_on_wrap_configure) so it only happens when the width truly changes.
        # Forcing _render_image() here during bulk relayout causes one LANCZOS
        # resize per card per relayout, which stalls the UI when many cards exist.
        # If a thumbnail is already loaded and we're below the configured wrap
        # width, the wrap configure handler will catch the real geometry change.

    def _render_image(self):
        if not bool(self.winfo_exists()) or self._src is None:
            return
        wrap_w = self.img_wrap.winfo_width()
        tw = wrap_w if wrap_w > 50 else max(50, self.card_w - 12)
        th = max(30, round(tw * 9 / 16))
        if abs(tw - getattr(self, '_rendered_w', 0)) < 4 and getattr(self, 'photo', None) is not None:
            return
        self._rendered_w = tw

        try:
            self.img_wrap.configure(height=th)
        except Exception:
            pass

        sw, sh = self._src.size
        if sw <= 0 or sh <= 0:
            return

        scale = max(tw / sw, th / sh)
        nw = max(tw, round(sw * scale))
        nh = max(th, round(sh * scale))
        im = self._src.resize((nw, nh), Image.Resampling.BICUBIC)
        left = max(0, (nw - tw) // 2)
        top = max(0, (nh - th) // 2)
        crop = im.crop((left, top, left + tw, top + th))
        rounded_crop = apply_rounded_corners(crop, radius=14, bg_color=(13, 13, 18, 255)) or crop
        self.photo = ImageTk.PhotoImage(rounded_crop)
        try:
            self.img_lbl.configure(image=self.photo, text='')
            self.img_lbl.place(x=0, y=0, relwidth=1.0, relheight=1.0)
            # Keep overlay badges in front of resized thumbnail
            for child in self.img_wrap.winfo_children():
                if child != self.img_lbl:
                    child.lift()
        except Exception:
            pass


# ==============================================================================
# SponsoredCard - Dynamic In-Grid Ad / Notice / Promo Card
# ==============================================================================

class SponsoredCard(tk.Frame):
    """Dynamic promotional / announcement card embedded seamlessly into the video grid."""
    IMG_W = 300
    IMG_H = 168

    def __init__(self, app, parent, item):
        super().__init__(parent, bg=CARD_BG, highlightthickness=1,
                         highlightbackground=CARD_BORDER, cursor='hand2')
        self.app = app
        self.item = item
        self.photo = None
        self._src = None
        self.card_w = self.IMG_W
        self._rendered_w = 0
        self.accent = item.get('accent_color') or LINK

        self.bind('<Enter>', lambda _e: self._on_hover(True))
        self.bind('<Leave>', lambda _e: self._on_hover(False))

        img_wrap = tk.Frame(self, bg=THUMB_BLANK_BG, height=self.IMG_H,
                            highlightthickness=1, highlightbackground=CARD_BORDER)
        self.img_wrap = img_wrap
        img_wrap.pack(fill='x', padx=6, pady=(6, 0))
        img_wrap.pack_propagate(False)
        img_wrap.bind('<Configure>', self._on_wrap_configure)

        self.img_lbl = tk.Label(img_wrap, bg=THUMB_BLANK_BG, fg=MUTE, text='',
                                font=app.font_sans(10), bd=0, padx=0, pady=0)
        self.img_lbl.place(x=0, y=0, relwidth=1.0, relheight=1.0)

        # Eyebrow / Badge (top-left)
        badge_txt = str(item.get('badge') or 'SPONSORED').upper()
        self.badge_lbl = tk.Label(img_wrap, text=f' {badge_txt} ', bg=ELEVATED,
                                  fg=self.accent, font=app.font_mono(8, bold=True),
                                  highlightthickness=1, highlightbackground=self.accent,
                                  padx=6, pady=2)
        self.badge_lbl.place(relx=0.0, rely=0.0, x=7, y=7, anchor='nw')

        # Close / Remove button (top-right of thumbnail)
        self.btn_close = tk.Label(img_wrap, text=' ✕ ', bg=MEDIA_OVERLAY_BG, fg=MEDIA_OVERLAY_FG,
                                  font=app.font_sans(8, bold=True),
                                  highlightthickness=1, highlightbackground=MEDIA_OVERLAY_BD,
                                  cursor='hand2', padx=5, pady=2)
        self.btn_close.place(relx=1.0, rely=0.0, x=-7, y=7, anchor='ne')

        def _on_close_h(enter):
            self.btn_close.configure(fg=ERROR if enter else MEDIA_OVERLAY_FG,
                                     highlightbackground=ERROR if enter else MEDIA_OVERLAY_BD)

        def _on_close_click(event=None):
            self.app._dismiss_card_ad(self, self.item)
            return 'break'

        self.btn_close.bind('<Enter>', lambda _e: _on_close_h(True))
        self.btn_close.bind('<Leave>', lambda _e: _on_close_h(False))
        self.btn_close.bind('<Button-1>', _on_close_click)

        # Card body
        inner = tk.Frame(self, bg=CARD_BG)
        inner.pack(fill='both', expand=True, padx=10, pady=(8, 10))
        self.inner = inner

        title = str(item.get('title') or '').strip() or 'Sponsored'
        self.title_lbl = tk.Label(inner, text=title,
                                  height=2, wraplength=self.IMG_W - 24,
                                  justify='left', anchor='nw',
                                  bg=CARD_BG, fg=INK,
                                  font=app.font_sans(10, bold=True))
        self.title_lbl.pack(side='top', fill='x')

        desc = str(item.get('description') or item.get('message') or '').strip()
        if desc:
            self.desc_lbl = tk.Label(inner, text=desc[:110],
                                     wraplength=self.IMG_W - 24,
                                     justify='left', anchor='nw',
                                     bg=CARD_BG, fg=BODY,
                                     font=app.font_sans(9))
            self.desc_lbl.pack(side='top', fill='x', pady=(2, 0))

        foot = tk.Frame(inner, bg=CARD_BG)
        foot.pack(side='bottom', fill='x', pady=(8, 0))
        self.foot = foot

        link_text = str(item.get('link_text') or 'Learn More ↗')
        self.btn_act = tk.Frame(foot, bg=PILL_PRI_BG, highlightthickness=1,
                                highlightbackground=PILL_PRI_BORDER, cursor='hand2')
        self.btn_act.pack(side='right')
        self.lbl_act = tk.Label(self.btn_act, text=link_text, bg=PILL_PRI_BG,
                                fg=PILL_PRI_FG, font=app.font_sans(9, bold=True),
                                cursor='hand2', padx=10, pady=3)
        self.lbl_act.pack()

        link_url = item.get('link_url') or ''
        for w in (self, img_wrap, self.img_lbl, inner, self.title_lbl, self.btn_act, self.lbl_act):
            if hasattr(self, 'desc_lbl'):
                self.desc_lbl.bind('<Button-1>', lambda _e, u=link_url: self.app._open_external_url(u))
            w.bind('<Button-1>', lambda _e, u=link_url: self.app._open_external_url(u))
            w.bind('<Enter>', lambda _e: self._on_hover(True), add='+')
            w.bind('<Leave>', lambda _e: self._on_hover(False), add='+')

        # Load image if provided
        img_url = item.get('image_url') or item.get('thumbnail') or ''
        if img_url:
            self.app.thumb_pool.submit(self.app._load_thumb, self, img_url)

    def set_width(self, w):
        w = max(200, int(w))
        self.card_w = w
        try:
            self.title_lbl.configure(wraplength=max(80, w - 24))
            if hasattr(self, 'desc_lbl'):
                self.desc_lbl.configure(wraplength=max(80, w - 24))
        except Exception:
            pass

    def _on_wrap_configure(self, event=None):
        if event is not None and hasattr(event, 'width'):
            w = event.width
        else:
            w = self.img_wrap.winfo_width()
        if w > 50 and abs(w - self._rendered_w) >= 4:
            self.after_idle(self._render_image)

    def _on_hover(self, enter):
        border = CARD_BORDER_HOVER if enter else CARD_BORDER
        bg = CARD_HOVER if enter else CARD_BG
        self.configure(highlightbackground=border, bg=bg)
        try:
            self.inner.configure(bg=bg)
            self.title_lbl.configure(bg=bg)
            if hasattr(self, 'desc_lbl'):
                self.desc_lbl.configure(bg=bg)
            self.foot.configure(bg=bg)
        except Exception:
            pass

    def apply_image(self, pil_image):
        self._src = pil_image
        self._render_image()

    def _render(self):
        self._render_image()

    def _render_image(self):
        if not bool(self.winfo_exists()):
            return
        wrap_w = self.img_wrap.winfo_width()
        tw = wrap_w if wrap_w > 50 else max(50, self.card_w - 12)
        th = max(30, round(tw * 9 / 16))
        self._rendered_w = tw

        try:
            self.img_wrap.configure(height=th)
        except Exception:
            pass

        im = self._src
        if im is None:
            return
        iw, ih = im.size
        scale = max(tw / iw, th / ih)
        nw = max(1, round(iw * scale))
        nh = max(1, round(ih * scale))
        if (nw, nh) != (iw, ih):
            im = im.resize((nw, nh), Image.Resampling.LANCZOS)
        left = max(0, (nw - tw) // 2)
        top = max(0, (nh - th) // 2)
        crop = im.crop((left, top, left + tw, top + th))
        rounded_crop = apply_rounded_corners(crop, radius=14, bg_color=(13, 13, 18, 255)) or crop
        self.photo = ImageTk.PhotoImage(rounded_crop)
        try:
            self.img_lbl.configure(image=self.photo, text='')
            self.img_lbl.place(x=0, y=0, relwidth=1.0, relheight=1.0)
            for child in self.img_wrap.winfo_children():
                if child != self.img_lbl:
                    child.lift()
        except Exception:
            pass


# ==============================================================================
# RecCard - Recommendations Rail Video Card
# ==============================================================================

class RecCard(tk.Frame):
    """Vertical card for the player's recommendations rail."""
    TH = 300

    def __init__(self, app, master, item):
        super().__init__(master, bg=CARD_BG, cursor='hand2',
                         highlightthickness=1, highlightbackground=CARD_BORDER)
        self.app = app
        self.item = item
        self.photo = None
        self._src = None
        self._rendered_w = 0

        self.bind('<Enter>', lambda _e: self._on_hover(True))
        self.bind('<Leave>', lambda _e: self._on_hover(False))

        self.thumb = tk.Canvas(self, height=self.TH, bg=THUMB_BLANK_BG, bd=0, highlightthickness=0)
        self.thumb.pack(fill='x', padx=4, pady=(4, 0))
        self.thumb.bind('<Configure>', self._on_thumb_resize)

        # Actions bar container (bottom-left overlay on thumbnail)
        self.actions_bar = tk.Frame(self.thumb, bg=THUMB_BLANK_BG, bd=0, highlightthickness=0)

        # Overlay Icon-Only Download Button (Larger & Comfortable Hit Target)
        self.dl_btn = tk.Frame(self.actions_bar, bg=PILL_PRI_BG, highlightthickness=1,
                               highlightbackground=PILL_PRI_BORDER, cursor='hand2')
        self._ico_dl = get_heroicon('download', size=20, color=PILL_PRI_FG)
        self.lbl_dl = tk.Label(self.dl_btn, image=self._ico_dl,
                               bg=PILL_PRI_BG, cursor='hand2',
                               padx=7, pady=5)
        self.lbl_dl.image = self._ico_dl
        self.lbl_dl.pack()
        self.dl_btn.pack(side='left', padx=(0, 6))

        def _on_dl_hover(enter):
            if getattr(self, '_dl_done', False):
                return
            bg = PILL_PRI_HOVER_BG if enter else PILL_PRI_BG
            bd = PILL_PRI_HOVER_BD if enter else PILL_PRI_BORDER
            c = PILL_PRI_HOVER_FG if enter else PILL_PRI_FG
            self.dl_btn.configure(bg=bg, highlightbackground=bd)
            img = get_heroicon('download', size=20, color=c)
            self.lbl_dl.configure(bg=bg, image=img)
            self.lbl_dl.image = img

        for w in (self.dl_btn, self.lbl_dl):
            w.bind('<Button-1>', self._on_download_click)
            w.bind('<Enter>', lambda _e: _on_dl_hover(True))
            w.bind('<Leave>', lambda _e: _on_dl_hover(False))

        # Overlay Icon-Only Queue (+) Button (In line with Download, with clean margin)
        self.queue_btn = tk.Frame(self.actions_bar, bg=PILL_SEC_BG, highlightthickness=1,
                                  highlightbackground=PILL_SEC_BORDER, cursor='hand2')
        self._ico_plus = get_heroicon('plus', size=20, color=PILL_SEC_FG)
        self.lbl_queue = tk.Label(self.queue_btn, image=self._ico_plus,
                                  bg=PILL_SEC_BG, cursor='hand2',
                                  padx=7, pady=5)
        self.lbl_queue.image = self._ico_plus
        self.lbl_queue.pack()
        self.queue_btn.pack(side='left', padx=(0, 6))

        def _on_queue_hover(enter):
            if getattr(self, '_queue_done', False):
                return
            bg = PILL_SEC_HOVER_BG if enter else PILL_SEC_BG
            bd = PILL_SEC_HOVER_BD if enter else PILL_SEC_BORDER
            c = PILL_SEC_HOVER_FG if enter else PILL_SEC_FG
            self.queue_btn.configure(bg=bg, highlightbackground=bd)
            img = get_heroicon('plus', size=20, color=c)
            self.lbl_queue.configure(bg=bg, image=img)
            self.lbl_queue.image = img

        for w in (self.queue_btn, self.lbl_queue):
            w.bind('<Button-1>', self._on_queue_click)
            w.bind('<Enter>', lambda _e: _on_queue_hover(True))
            w.bind('<Leave>', lambda _e: _on_queue_hover(False))

        # Overlay Icon-Only Save / Watch Later Bookmark Button
        self.save_btn = tk.Frame(self.actions_bar, bg=PILL_SEC_BG, highlightthickness=1,
                                 highlightbackground=PILL_SEC_BORDER, cursor='hand2')
        is_rec_saved = config.is_video_saved(str(item.get('url') or ''))
        rec_save_col = LINK if is_rec_saved else PILL_SEC_FG
        self._ico_save = get_heroicon('bookmark_solid' if is_rec_saved else 'bookmark', size=20, color=rec_save_col)
        self.lbl_save = tk.Label(self.save_btn, image=self._ico_save,
                                 bg=PILL_SEC_BG, cursor='hand2',
                                 padx=7, pady=5)
        self.lbl_save.image = self._ico_save
        self.lbl_save.pack()
        self.save_btn.pack(side='left')

        def _on_rec_save_hover(enter):
            u = str(self.item.get('url') or '')
            saved = config.is_video_saved(u)
            bg = PILL_SEC_HOVER_BG if enter else PILL_SEC_BG
            bd = PILL_SEC_HOVER_BD if enter else PILL_SEC_BORDER
            if saved:
                c = LINK_HOVER if enter else LINK
                img = get_heroicon('bookmark_solid', size=20, color=c)
            else:
                c = LINK if enter else (PILL_SEC_HOVER_FG if enter else PILL_SEC_FG)
                img = get_heroicon('bookmark', size=20, color=c)
            self.save_btn.configure(bg=bg, highlightbackground=bd)
            self.lbl_save.configure(bg=bg, image=img)
            self.lbl_save.image = img

        def _on_rec_save_click(_e=None):
            u = str(self.item.get('url') or '')
            t = str(self.item.get('title') or u)
            was_saved = config.is_video_saved(u)
            if was_saved:
                config.remove_saved_video(u)
                img = get_heroicon('bookmark', size=20, color=PILL_SEC_FG)
                self.lbl_save.configure(image=img)
                self.lbl_save.image = img
                self.app.show_toast(f'Removed "{t[:36]}" from Watch Later', icon='bookmark', color=MUTE)
            else:
                config.add_saved_video(dict(self.item))
                img = get_heroicon('bookmark_solid', size=20, color=LINK)
                self.lbl_save.configure(image=img)
                self.lbl_save.image = img
                self.app.show_toast(f'Saved "{t[:36]}" to Watch Later', icon='bookmark', color=LINK)
            self.app._on_watch_later_updated(u)

        for w in (self.save_btn, self.lbl_save):
            w.bind('<Button-1>', _on_rec_save_click)
            w.bind('<Enter>', lambda _e: _on_rec_save_hover(True))
            w.bind('<Leave>', lambda _e: _on_rec_save_hover(False))

        # Overlay Duration Badge
        self.dur_badge = tk.Label(
            self.thumb, text='', bg=MEDIA_OVERLAY_BG, fg=MEDIA_OVERLAY_FG,
            font=self.app.font_mono(8, bold=True),
            highlightthickness=1, highlightbackground=MEDIA_OVERLAY_BD,
            padx=5, pady=2)

        self.title_lbl = tk.Label(self, text=str(item.get('title') or 'Video')[:90],
                                  bg=CARD_BG, fg=INK, wraplength=self.app.RECS_W - 32,
                                  justify='left', anchor='w',
                                  font=app.font_sans(10, bold=True))
        self.title_lbl.pack(fill='x', padx=8, pady=(6, 8))
        for w in (self, self.thumb, self.title_lbl):
            w.bind('<Button-1>', self._open)
            w.bind('<Enter>', lambda _e: self._on_hover(True), add='+')
            w.bind('<Leave>', lambda _e: self._on_hover(False), add='+')

    def _on_download_click(self, event=None):
        if getattr(self, '_animating_dl', False):
            return
        self._animating_dl = True
        self.app.download_item(dict(self.item))

        # Stage 1: Active cyan pulse
        try:
            pulse_ico = get_heroicon('download', size=20, color=ON_PRIMARY)
            self.lbl_dl.configure(image=pulse_ico, bg=PILL_PRI_BG)
            self.lbl_dl.image = pulse_ico
            self.dl_btn.configure(bg=PILL_PRI_BG, highlightbackground=PILL_PRI_BORDER)
        except Exception:
            pass

        # Stage 2 (120ms): Intermediate streaming glow
        def _step2():
            if not bool(self.winfo_exists()):
                return
            try:
                glow_ico = get_heroicon('download', size=20, color=SUCCESS)
                self.lbl_dl.configure(image=glow_ico, bg=PILL_SUC_BG)
                self.lbl_dl.image = glow_ico
                self.dl_btn.configure(bg=PILL_SUC_BG, highlightbackground=PILL_SUC_BORDER)
            except Exception:
                pass

        # Stage 3 (240ms): Smooth morph to emerald checkmark
        def _step3():
            if not bool(self.winfo_exists()):
                return
            self._dl_done = True
            self._animating_dl = False
            try:
                chk_img = get_heroicon('check', size=20, color=SUCCESS)
                self.lbl_dl.configure(image=chk_img, bg=PILL_SUC_BG)
                self.lbl_dl.image = chk_img
                self.dl_btn.configure(bg=PILL_SUC_BG, highlightbackground=PILL_SUC_BORDER)
            except Exception:
                pass

        self.after(120, _step2)
        self.after(240, _step3)

    def _on_queue_click(self, event=None):
        if getattr(self, '_animating_queue', False):
            return
        self._animating_queue = True
        self.app.queue_item(dict(self.item))

        # Stage 1: Active blue pulse
        try:
            pulse_ico = get_heroicon('plus', size=20, color=ON_PRIMARY)
            self.lbl_queue.configure(image=pulse_ico, bg=PILL_PRI_BG)
            self.lbl_queue.image = pulse_ico
            self.queue_btn.configure(bg=PILL_PRI_BG, highlightbackground=PILL_PRI_BORDER)
        except Exception:
            pass

        # Stage 2 (120ms): Intermediate glow
        def _step2():
            if not bool(self.winfo_exists()):
                return
            try:
                glow_ico = get_heroicon('plus', size=20, color=SUCCESS)
                self.lbl_queue.configure(image=glow_ico, bg=PILL_SUC_BG)
                self.lbl_queue.image = glow_ico
                self.queue_btn.configure(bg=PILL_SUC_BG, highlightbackground=PILL_SUC_BORDER)
            except Exception:
                pass

        # Stage 3 (240ms): Smooth morph to emerald checkmark
        def _step3():
            if not bool(self.winfo_exists()):
                return
            self._queue_done = True
            self._animating_queue = False
            try:
                chk_img = get_heroicon('check', size=20, color=SUCCESS)
                self.lbl_queue.configure(image=chk_img, bg=PILL_SUC_BG)
                self.lbl_queue.image = chk_img
                self.queue_btn.configure(bg=PILL_SUC_BG, highlightbackground=PILL_SUC_BORDER)
            except Exception:
                pass

        self.after(120, _step2)
        self.after(240, _step3)

    def _on_hover(self, enter):
        border = CARD_BORDER_HOVER if enter else CARD_BORDER
        bg = CARD_HOVER if enter else CARD_BG
        self.configure(highlightbackground=border, bg=bg)
        try:
            self.title_lbl.configure(bg=bg)
        except Exception:
            pass

    def _open(self, _e=None):
        self.app.watch_item(dict(self.item))

    def _on_thumb_resize(self, _e=None):
        if abs(self.thumb.winfo_width() - self._rendered_w) > 4:
            self.thumb.after_idle(self._render)

    def apply_image(self, im):
        if im is None:
            return
        self._src = im
        self._render()

    def _render(self):
        src = self._src
        w = max(60, self.thumb.winfo_width())
        self._rendered_w = w
        h = round(w * 9 / 16)
        try:
            self.thumb.configure(height=h)
            self.title_lbl.configure(wraplength=max(60, w - 20))
            self.thumb.delete('all')
            if src is not None:
                scale = max(w / src.width, h / src.height)
                nw = max(1, round(src.width * scale))
                nh = max(1, round(src.height * scale))
                resized = src.resize((nw, nh), Image.Resampling.LANCZOS)
                left = (nw - w) // 2
                top = (nh - h) // 2
                crop = resized.crop((left, top, left + w, top + h))
                rounded_crop = apply_rounded_corners(crop, radius=14) or crop
                self.photo = ImageTk.PhotoImage(rounded_crop)
                self.thumb.create_image(0, 0, anchor='nw', image=self.photo)

            # Place Overlay Actions Bar on bottom-left of thumbnail
            self.thumb.create_window(7, h - 6, window=self.actions_bar,
                                     anchor='sw', tags='actions_bar')

            # Place Duration Badge on bottom-right of thumbnail
            dur = str(self.item.get('duration') or '')
            if dur:
                self.dur_badge.configure(text=f' {dur} ')
                self.thumb.create_window(w - 7, h - 6, window=self.dur_badge,
                                         anchor='se', tags='dur_badge')
        except Exception:
            pass


# ==============================================================================
# BrowseSidebar - Primary Navigation Hub with Inline Badge Counts
# ==============================================================================

class BrowseSidebar(tk.Frame):
    """Permanent Left Navigation Rail for all application sections."""

    TABS = (('tags', 'Tags', 'tag'),
            ('models', 'Actresses', 'user'),
            ('channels', 'Studios', 'tv'),
            ('actors', 'Actors', 'users'))

    def __init__(self, master, app, on_pick):
        super().__init__(master, bg=SIDEBAR_BG, bd=0, highlightthickness=0)
        self.app = app
        self.on_pick = on_pick
        disk_cache = config.get_sidebar_cache()
        self._cache = {'ALL': dict(disk_cache)} if disk_cache else {}
        for kind, _l, _i in self.TABS:
            if disk_cache and disk_cache.get(kind):
                setattr(self, f'_full_{kind}', disk_cache[kind])
        self._loading = set()
        self._current_kind = self.TABS[0][0]
        self._active_key = 'new'
        self._selected_detail = {}
        self._active_detail_kind = None
        self._dt_rows = []
        self._all_items = {}
        self._section_hdrs = []
        self._dividers = []

        # ═══════ MAIN VIEW ═══════
        self._main_view = tk.Frame(self, bg=SIDEBAR_BG)
        self._main_view.pack(fill='both', expand=True)

        # --- Section 1: DISCOVER ---
        self._section_header(self._main_view, 'DISCOVER', top_pad=14)
        self._quick_btns = {}
        for key, label, icon_name in [('new', 'Newly Released', 'sparkles'),
                                      ('views', 'Most Viewed', 'fire'),
                                      ('trending', 'Trending', 'trending'),
                                      ('watchlist', 'Watchlist', 'star'),
                                      ('watch_later', 'Watch Later', 'bookmark'),
                                      ('shuffle', 'Shuffle', 'shuffle')]:
            row = self._make_sidebar_item(self._main_view, key, label, icon_name,
                                          command=lambda k=key: self._on_quick(k))
            self._quick_btns[key] = row
            self._all_items[key] = row

        # Divider
        d1 = tk.Frame(self._main_view, bg=SIDEBAR_DIVIDER, height=1)
        d1.pack(fill='x', padx=8, pady=(12, 10))
        self._dividers.append(d1)

        # --- Section 2: CATEGORIES ---
        self._section_header(self._main_view, 'CATEGORIES')
        self._cat_frames = {}
        for kind, label, icon_name in self.TABS:
            row = self._make_sidebar_item(self._main_view, kind, label, icon_name,
                                          command=lambda k=kind: self._show_detail(k))
            self._cat_frames[kind] = row
            self._all_items[kind] = row

        # Divider
        d2 = tk.Frame(self._main_view, bg=SIDEBAR_DIVIDER, height=1)
        d2.pack(fill='x', padx=8, pady=(12, 10))
        self._dividers.append(d2)

        # --- Section 3: LIBRARY ---
        self._section_header(self._main_view, 'LIBRARY')
        self._lib_btns = {}
        for tab_id, label, icon_name in [('queue', 'Downloads', 'download'),
                                         ('history', 'History', 'history'),
                                         ('settings', 'Settings', 'settings')]:
            row = self._make_sidebar_item(self._main_view, tab_id, label, icon_name,
                                          command=lambda t=tab_id: self._on_library_click(t))
            self._lib_btns[tab_id] = row
            self._all_items[tab_id] = row

        # ═══════ DETAIL VIEW (Drill-Down for Categories) ═══════
        self._detail_view = tk.Frame(self, bg=SIDEBAR_BG)

        dt_head = tk.Frame(self._detail_view, bg=SIDEBAR_BG)
        dt_head.pack(fill='x', padx=10, pady=(12, 8))
        self._detail_head = dt_head

        self.btn_detail_back = tk.Frame(dt_head, bg=SIDEBAR_BACK_BG, highlightthickness=1,
                                        highlightbackground=SIDEBAR_BACK_BD, cursor='hand2')
        self.btn_detail_back.pack(side='left')
        self._detail_back = tk.Label(
            self.btn_detail_back, text='← Back', bg=SIDEBAR_BACK_BG, fg=SIDEBAR_BACK_FG,
            font=app.font_sans(9, bold=True), cursor='hand2', padx=8, pady=2)
        self._detail_back.pack()

        def _on_back_hover(enter):
            fg = LINK_HOVER if enter else SIDEBAR_BACK_FG
            self._detail_back.configure(fg=fg)

        for w in (self.btn_detail_back, self._detail_back):
            w.bind('<Button-1>', lambda _e: self._show_main())
            w.bind('<Enter>', lambda _e: _on_back_hover(True))
            w.bind('<Leave>', lambda _e: _on_back_hover(False))

        self._detail_title = tk.Label(
            dt_head, text='', bg=SIDEBAR_BG, fg=INK,
            font=app.font_sans(11, bold=True))
        self._detail_title.pack(side='left', padx=(10, 0))

        dt_fframe = tk.Frame(self._detail_view, bg=SIDEBAR_INPUT_BG, highlightthickness=1,
                             highlightbackground=SIDEBAR_INPUT_BD)
        dt_fframe.pack(fill='x', padx=8, pady=(0, 8))
        self._filter_wrap = dt_fframe
        self._filter_ent = tk.Entry(
            dt_fframe, bg=SIDEBAR_INPUT_BG, fg=INK, relief='flat',
            insertbackground=INK, bd=0, font=app.font_sans(10))
        self._filter_ent.pack(fill='x', padx=6, pady=4)
        self._filter_ent.insert(0, 'Filter\u2026')
        self._filter_ent.bind('<FocusIn>', lambda _e: self._filter_focus_in())
        self._filter_ent.bind('<FocusOut>', lambda _e: self._filter_focus_out())
        self._filter_ent.bind('<KeyRelease>',
                              lambda _e: self._apply_filter(
                                  self._current_kind,
                                  self._filter_ent.get()))

        dt_holder = tk.Frame(self._detail_view, bg=SIDEBAR_BG)
        dt_holder.pack(fill='both', expand=True, padx=4, pady=(0, 4))
        self._dt_holder = dt_holder

        self._dt_canvas = tk.Canvas(dt_holder, bg=SIDEBAR_BG, bd=0, highlightthickness=0)
        dt_sb = ttk.Scrollbar(dt_holder, orient='vertical',
                              command=self._dt_canvas.yview,
                              style='Sidebar.Vertical.TScrollbar')
        self._dt_canvas.configure(yscrollcommand=dt_sb.set)
        dt_sb.pack(side='right', fill='y')
        self._dt_canvas.pack(side='left', fill='both', expand=True)

        self._dt_inner = tk.Frame(self._dt_canvas, bg=SIDEBAR_BG)
        self._dt_win = self._dt_canvas.create_window((0, 0), window=self._dt_inner, anchor='nw')

        def _on_dt_canvas_configure(event):
            self._dt_canvas.itemconfig(self._dt_win, width=event.width)
        self._dt_canvas.bind('<Configure>', _on_dt_canvas_configure)

        def _on_dt_inner_configure(_event=None):
            self._dt_canvas.configure(scrollregion=self._dt_canvas.bbox('all'))
        self._dt_inner.bind('<Configure>', _on_dt_inner_configure)

        def _on_dt_wheel(event):
            delta = -1 if event.delta < 0 else 1
            self._dt_canvas.yview_scroll(-1 * delta, 'units')
            return 'break'
        self._dt_canvas.bind('<MouseWheel>', _on_dt_wheel)
        self._dt_inner.bind('<MouseWheel>', _on_dt_wheel)

    def _section_header(self, parent, text, top_pad=12):
        hdr = tk.Frame(parent, bg=SIDEBAR_BG)
        hdr.pack(fill='x', padx=14, pady=(top_pad, 4))

        lbl = tk.Label(hdr, text=text, bg=SIDEBAR_BG, fg=SIDEBAR_HDR_FG,
                       font=self.app.font_sans(8, bold=True), anchor='w')
        lbl.pack(side='left')
        self._section_hdrs.append((hdr, lbl))

    def _make_sidebar_item(self, parent, key, label, icon_name, command):
        # Outer Liquid Glass capsule container
        row = tk.Frame(parent, bg=SIDEBAR_ITEM_IDLE_BG, highlightthickness=1,
                       highlightbackground=SIDEBAR_ITEM_IDLE_BD, cursor='hand2')
        row.pack(fill='x', padx=8, pady=2)

        inner = tk.Frame(row, bg=SIDEBAR_ITEM_IDLE_BG, cursor='hand2')
        inner.pack(fill='x', padx=4, pady=4)

        # Glowing Accent Indicator (3px wide)
        indicator = tk.Frame(inner, bg=SIDEBAR_ITEM_IDLE_BG, width=3, height=18)
        indicator.pack(side='left', padx=(0, 6))
        indicator.pack_propagate(False)

        ico_img = get_heroicon(icon_name, size=20, color=SIDEBAR_ITEM_IDLE_ICO)
        lbl_ico = tk.Label(inner, image=ico_img, bg=SIDEBAR_ITEM_IDLE_BG, cursor='hand2')
        lbl_ico.image = ico_img
        lbl_ico.pack(side='left', padx=(0, 8))

        lbl = tk.Label(inner, text=label, bg=SIDEBAR_ITEM_IDLE_BG, fg=SIDEBAR_ITEM_IDLE_FG,
                       font=self.app.font_sans(10), anchor='w', cursor='hand2')
        lbl.pack(side='left', fill='x', expand=True)

        # Liquid Glass Counter Badge
        badge_wrap = tk.Frame(inner, bg=SIDEBAR_BADGE_IDLE_BG, highlightthickness=1,
                              highlightbackground=SIDEBAR_BADGE_IDLE_BD, cursor='hand2')
        badge = tk.Label(badge_wrap, text='', bg=SIDEBAR_BADGE_IDLE_BG, fg=SIDEBAR_BADGE_IDLE_FG,
                         font=self.app.font_mono(9, bold=True), cursor='hand2', padx=6, pady=0)
        badge.pack()

        for w in (row, inner, indicator, lbl_ico, lbl, badge_wrap, badge):
            w.bind('<Button-1>', lambda _e: command())
            w.bind('<Enter>', lambda _e: self._hover_item(row, inner, indicator, lbl_ico, lbl, badge_wrap, badge, icon_name, True))
            w.bind('<Leave>', lambda _e: self._hover_item(row, inner, indicator, lbl_ico, lbl, badge_wrap, badge, icon_name, False))

        row._inner = inner
        row._indicator = indicator
        row._ico = lbl_ico
        row._lbl = lbl
        row._badge_wrap = badge_wrap
        row._badge = badge
        row._icon_name = icon_name
        row._key = key
        return row

    def set_badge(self, tab_id, text):
        row = self._lib_btns.get(tab_id)
        if not row:
            return
        badge_wrap = row._badge_wrap
        badge = row._badge
        if text:
            badge.configure(text=str(text).strip())
            if not badge_wrap.winfo_ismapped():
                badge_wrap.pack(side='right', padx=(4, 2))
        else:
            if badge_wrap.winfo_ismapped():
                badge_wrap.pack_forget()

    def set_active(self, active_key):
        self._active_key = active_key
        if active_key not in ('tags', 'models', 'channels', 'actors'):
            self._active_detail_kind = None
            self._selected_detail.clear()
        for key, row in self._all_items.items():
            is_active = (key == active_key)
            row._active = is_active
            if is_active:
                # Liquid Sapphire Active Glass Pill
                bg = SIDEBAR_ITEM_ACTIVE_BG
                bd = SIDEBAR_ITEM_ACTIVE_BD
                fg = SIDEBAR_ITEM_ACTIVE_FG
                ind_bg = SIDEBAR_ITEM_ACTIVE_IND
                ico_color = SIDEBAR_ITEM_ACTIVE_ICO
                b_bg = SIDEBAR_BADGE_ACTIVE_BG
                b_bd = SIDEBAR_BADGE_ACTIVE_BD
                b_fg = SIDEBAR_BADGE_ACTIVE_FG
                font = self.app.font_sans(10, bold=True)
            else:
                # Idle Frosted Background
                bg = SIDEBAR_ITEM_IDLE_BG
                bd = SIDEBAR_ITEM_IDLE_BD
                fg = SIDEBAR_ITEM_IDLE_FG
                ind_bg = SIDEBAR_ITEM_IDLE_BG
                ico_color = SIDEBAR_ITEM_IDLE_ICO
                b_bg = SIDEBAR_BADGE_IDLE_BG
                b_bd = SIDEBAR_BADGE_IDLE_BD
                b_fg = SIDEBAR_BADGE_IDLE_FG
                font = self.app.font_sans(10, bold=False)

            ico_img = get_heroicon(row._icon_name, size=20, color=ico_color)

            row.configure(bg=bg, highlightbackground=bd)
            row._inner.configure(bg=bg)
            row._indicator.configure(bg=ind_bg)
            row._ico.configure(bg=bg, image=ico_img)
            row._ico.image = ico_img
            row._lbl.configure(bg=bg, fg=fg, font=font)
            row._badge_wrap.configure(bg=b_bg, highlightbackground=b_bd)
            row._badge.configure(bg=b_bg, fg=b_fg)
        self._update_dt_rows_visuals()

    def set_selected_detail(self, kind, name):
        """Programmatically select and highlight a detail item (tag, actress, studio, actor)."""
        if kind and name:
            self._selected_detail[kind] = name
            self._active_detail_kind = kind
            self.set_active(kind)
            if getattr(self, '_current_kind', None) == kind:
                self._update_dt_rows_visuals()

    def _update_dt_rows_visuals(self):
        """Refreshes active selection and idle visual styling on all visible detail list rows."""
        cur_selected = (self._selected_detail.get(self._current_kind) or '').strip().lower()
        is_cat_active = (self._active_key == self._current_kind)
        for r_frame, indicator, lbl_name, lbl_star, item_name in getattr(self, '_dt_rows', []):
            is_act = is_cat_active and bool(cur_selected) and (item_name.strip().lower() == cur_selected)
            r_frame._active = is_act
            if is_act:
                bg = SIDEBAR_ITEM_ACTIVE_BG
                bd = SIDEBAR_ITEM_ACTIVE_BD
                fg = SIDEBAR_ITEM_ACTIVE_FG
                ind_bg = SIDEBAR_ITEM_ACTIVE_IND
                font = self.app.font_sans(10, bold=True)
            else:
                bg = SIDEBAR_ITEM_IDLE_BG
                bd = SIDEBAR_ITEM_IDLE_BD
                fg = INK
                ind_bg = SIDEBAR_ITEM_IDLE_BG
                font = self.app.font_sans(10, bold=False)
            try:
                r_frame.configure(bg=bg, highlightbackground=bd)
                indicator.configure(bg=ind_bg)
                lbl_name.configure(bg=bg, fg=fg, font=font)
                lbl_star.configure(bg=bg)
            except Exception:
                pass

    def _hover_item(self, row, inner, indicator, ico, lbl, badge_wrap, badge, icon_name, enter):
        if getattr(row, '_active', False):
            return
        if enter:
            bg = SIDEBAR_ITEM_IDLE_BG
            bd = SIDEBAR_ITEM_IDLE_BD
            fg = LINK_HOVER
            ind_bg = SIDEBAR_ITEM_IDLE_BG
            ico_color = LINK_HOVER
            b_bg = SIDEBAR_BADGE_IDLE_BG
            b_bd = SIDEBAR_BADGE_IDLE_BD
            b_fg = LINK_HOVER
        else:
            bg = SIDEBAR_ITEM_IDLE_BG
            bd = SIDEBAR_ITEM_IDLE_BD
            fg = SIDEBAR_ITEM_IDLE_FG
            ind_bg = SIDEBAR_ITEM_IDLE_BG
            ico_color = SIDEBAR_ITEM_IDLE_ICO
            b_bg = SIDEBAR_BADGE_IDLE_BG
            b_bd = SIDEBAR_BADGE_IDLE_BD
            b_fg = SIDEBAR_BADGE_IDLE_FG

        ico_img = get_heroicon(icon_name, size=20, color=ico_color)

        row.configure(bg=bg, highlightbackground=bd)
        inner.configure(bg=bg)
        indicator.configure(bg=ind_bg)
        ico.configure(bg=bg, image=ico_img)
        ico.image = ico_img
        lbl.configure(bg=bg, fg=fg)
        badge_wrap.configure(bg=b_bg, highlightbackground=b_bd)
        badge.configure(bg=b_bg, fg=b_fg)

    def retheme(self):
        self.configure(bg=SIDEBAR_BG)
        self._main_view.configure(bg=SIDEBAR_BG)
        self._detail_view.configure(bg=SIDEBAR_BG)
        if hasattr(self, '_detail_head'):
            self._detail_head.configure(bg=SIDEBAR_BG)
        if hasattr(self, '_detail_title'):
            self._detail_title.configure(bg=SIDEBAR_BG, fg=INK)
        if hasattr(self, 'btn_detail_back'):
            self.btn_detail_back.configure(bg=SIDEBAR_BACK_BG, highlightbackground=SIDEBAR_BACK_BD)
        if hasattr(self, '_detail_back'):
            self._detail_back.configure(bg=SIDEBAR_BACK_BG, fg=SIDEBAR_BACK_FG)
        if hasattr(self, '_filter_wrap'):
            self._filter_wrap.configure(bg=SIDEBAR_INPUT_BG, highlightbackground=SIDEBAR_INPUT_BD)
        if hasattr(self, '_filter_ent'):
            self._filter_ent.configure(bg=SIDEBAR_INPUT_BG, fg=INK, insertbackground=INK)
        if hasattr(self, '_dt_holder'):
            self._dt_holder.configure(bg=SIDEBAR_BG)
        if hasattr(self, '_dt_canvas'):
            self._dt_canvas.configure(bg=SIDEBAR_BG)
        if hasattr(self, '_dt_inner'):
            self._dt_inner.configure(bg=SIDEBAR_BG)
        for hdr, lbl in getattr(self, '_section_hdrs', []):
            try:
                hdr.configure(bg=SIDEBAR_BG)
                lbl.configure(bg=SIDEBAR_BG, fg=SIDEBAR_HDR_FG)
            except Exception:
                pass
        for div in getattr(self, '_dividers', []):
            try:
                div.configure(bg=SIDEBAR_DIVIDER)
            except Exception:
                pass
        self.set_active(self._active_key)

    _QUICK_LABELS = {
        'new': 'Newly Released',
        'views': 'Most Viewed',
        'trending': 'Trending',
        'watchlist': 'Watchlist',
        'watch_later': 'Watch Later',
        'shuffle': 'Shuffle',
    }

    def get_quick_urls(self, key):
        enabled = set(config.get_enabled_sources())
        urls = []
        if key == 'new':
            if 'FreePornVideos' in enabled:
                urls.append('https://www.freepornvideos.xxx/latest-updates/')
            if 'OnePorn' in enabled:
                urls.append('https://www.1porn.tv/latest-updates/')
        elif key == 'views':
            if 'FreePornVideos' in enabled:
                urls.append('https://www.freepornvideos.xxx/most-popular/month/')
            if 'OnePorn' in enabled:
                urls.append('https://www.1porn.tv/most-popular/month/')
        elif key == 'trending':
            if 'FreePornVideos' in enabled:
                urls.append('https://www.freepornvideos.xxx/most-popular/week/')
            if 'OnePorn' in enabled:
                urls.append('https://www.1porn.tv/most-popular/week/')
        if not urls:
            if 'FreePornVideos' in enabled:
                urls.append('https://www.freepornvideos.xxx/latest-updates/')
            else:
                urls.append('https://www.freepornvideos.xxx/latest-updates/')
        return urls

    def _on_quick(self, key):
        self.set_active(key)
        if key == 'shuffle':
            self.app.switch_tab('browse')
            self.app.browse_shuffle()
        elif key == 'watchlist':
            self.app.switch_tab('browse')
            self.app.browse_watchlist()
        elif key == 'watch_later':
            self.app.switch_tab('watch_later')
        else:
            self.app.switch_tab('browse')
            urls = self.get_quick_urls(key)
            name = self._QUICK_LABELS.get(key, key)
            self.app.browse_load({'name': name, 'urls': list(urls)}, reset=True)
            self.app.say(f'Browsing: {name}')

    def _on_library_click(self, tab_id):
        self.set_active(tab_id)
        self.app.switch_tab(tab_id)

    def _show_main(self):
        self._detail_view.pack_forget()
        self._main_view.pack(fill='both', expand=True)

    def _show_detail(self, kind):
        self._current_kind = kind
        self.set_active(kind)
        labels = {k: l for k, l, _i in self.TABS}
        self._detail_title.configure(text=labels.get(kind, kind))
        self._main_view.pack_forget()
        self._detail_view.pack(fill='both', expand=True)

        self._filter_ent.delete(0, 'end')
        self._filter_ent.insert(0, 'Filter\u2026')
        self._filter_ent.configure(fg=MUTE)

        cached_all = self._cache.get('ALL') or {}
        rows = cached_all.get(kind) or getattr(self, f'_full_{kind}', None)
        if rows:
            self._populate_detail_list(kind)
        else:
            for w in self._dt_inner.winfo_children():
                w.destroy()
            lbl_ld = tk.Label(self._dt_inner, text='  loading\u2026', bg=SIDEBAR_BG, fg=MUTE,
                              font=self.app.font_sans(10), anchor='w')
            lbl_ld.pack(fill='x', padx=10, pady=8)
            self._load_subcategories(kind)

    def _populate_detail_list(self, kind):
        for w in self._dt_inner.winfo_children():
            w.destroy()
        self._dt_rows = []
        self._dt_canvas.yview_moveto(0)

        cached = self._cache.get('ALL') or self._cache.get(kind) or []
        rows = cached.get(kind, []) if isinstance(cached, dict) else cached
        if not rows:
            rows = getattr(self, f'_full_{kind}', [])
        pairs = self._pairs_for(kind, rows)
        filt = '' if self._filter_ent.get() in ('', 'Filter\u2026') else self._filter_ent.get()
        filtered = self._display_rows(pairs, filt)
        if not filtered:
            lbl_none = tk.Label(self._dt_inner, text='  (none)', bg=SIDEBAR_BG, fg=MUTE,
                                font=self.app.font_sans(10), anchor='w')
            lbl_none.pack(fill='x', padx=10, pady=8)
            return

        def _on_dt_wheel(event):
            delta = -1 if event.delta < 0 else 1
            self._dt_canvas.yview_scroll(-1 * delta, 'units')
            return 'break'

        cur_selected = (self._selected_detail.get(kind) or '').strip().lower()
        is_cat_active = (self._active_key == kind)

        for item_obj, label in filtered:
            name = item_obj.get('name') if isinstance(item_obj, dict) else str(item_obj)
            is_starred = config.is_in_watchlist(name, kind)
            is_selected = is_cat_active and bool(cur_selected) and (name.strip().lower() == cur_selected)

            bg = SIDEBAR_ITEM_ACTIVE_BG if is_selected else SIDEBAR_ITEM_IDLE_BG
            bd = SIDEBAR_ITEM_ACTIVE_BD if is_selected else SIDEBAR_ITEM_IDLE_BD
            fg = SIDEBAR_ITEM_ACTIVE_FG if is_selected else INK
            ind_bg = SIDEBAR_ITEM_ACTIVE_IND if is_selected else SIDEBAR_ITEM_IDLE_BG
            font = self.app.font_sans(10, bold=True) if is_selected else self.app.font_sans(10)

            row = tk.Frame(self._dt_inner, bg=bg, highlightthickness=1,
                           highlightbackground=bd, cursor='hand2')
            row.pack(fill='x', padx=3, pady=1)
            row._active = is_selected

            # Glowing Accent Indicator on Left
            indicator = tk.Frame(row, bg=ind_bg, width=3, height=18)
            indicator.pack(side='left', padx=(2, 4))
            indicator.pack_propagate(False)

            # Left: Label / Name
            lbl_name = tk.Label(row, text=label, bg=bg, fg=fg,
                                font=font, anchor='w', cursor='hand2', padx=4, pady=3)
            lbl_name.pack(side='left', fill='x', expand=True)

            # Right margin: Star toggle button
            star_color = '#f59e0b' if is_starred else MUTE
            star_char = '★' if is_starred else '☆'
            lbl_star = tk.Label(row, text=star_char, bg=bg, fg=star_color,
                                font=self.app.font_sans(11, bold=True), cursor='hand2', padx=8, pady=3)
            lbl_star.pack(side='right')

            def make_bindings(r_frame, r_ind, r_lbl, r_star, r_item, r_name, r_kind):
                def _toggle_star(_e=None):
                    curr = config.is_in_watchlist(r_name, r_kind)
                    if curr:
                        config.remove_watchlist_item(r_name, r_kind)
                        r_star.configure(text='☆', fg=MUTE)
                        self.app.show_toast(f'Removed "{r_name}" from Watchlist', icon='star', color=MUTE)
                    else:
                        urls = []
                        if isinstance(r_item, dict):
                            if r_item.get('urls'):
                                urls = list(r_item['urls'])
                            elif r_item.get('url'):
                                urls = [r_item['url']]
                        config.add_watchlist_item({
                            'name': r_name,
                            'type': r_kind,
                            'urls': urls,
                            'starred_at': time.time()
                        })
                        r_star.configure(text='★', fg='#f59e0b')
                        self.app.show_toast(f'★ Added "{r_name}" to Watchlist', icon='star', color='#f59e0b')
                    return 'break'

                def _select_item(_e=None):
                    self._selected_detail[r_kind] = r_name
                    self._active_detail_kind = r_kind
                    self.set_active(r_kind)
                    self._update_dt_rows_visuals()
                    self.app.switch_tab('browse')
                    if isinstance(r_item, dict):
                        urls = r_item.get('urls') or ([r_item['url']] if r_item.get('url') else [])
                        self.on_pick((r_kind, {'name': r_name, 'urls': urls}))
                    elif isinstance(r_item, str):
                        self.on_pick((r_kind, r_item))

                def _enter(_e=None):
                    if getattr(r_frame, '_active', False):
                        return
                    r_frame.configure(bg=SIDEBAR_ITEM_HOVER_BG, highlightbackground=SIDEBAR_ITEM_HOVER_BD)
                    r_ind.configure(bg=SIDEBAR_ITEM_HOVER_BG)
                    r_lbl.configure(bg=SIDEBAR_ITEM_HOVER_BG, fg=LINK_HOVER)
                    r_star.configure(bg=SIDEBAR_ITEM_HOVER_BG)

                def _leave(_e=None):
                    if getattr(r_frame, '_active', False):
                        return
                    r_frame.configure(bg=SIDEBAR_ITEM_IDLE_BG, highlightbackground=SIDEBAR_ITEM_IDLE_BD)
                    r_ind.configure(bg=SIDEBAR_ITEM_IDLE_BG)
                    r_lbl.configure(bg=SIDEBAR_ITEM_IDLE_BG, fg=INK)
                    r_star.configure(bg=SIDEBAR_ITEM_IDLE_BG)

                r_star.bind('<Button-1>', _toggle_star)
                r_lbl.bind('<Button-1>', _select_item)
                r_frame.bind('<Button-1>', _select_item)

                for w in (r_frame, r_ind, r_lbl, r_star):
                    w.bind('<Enter>', _enter)
                    w.bind('<Leave>', _leave)
                    w.bind('<MouseWheel>', _on_dt_wheel)

            make_bindings(row, indicator, lbl_name, lbl_star, item_obj, name, kind)
            self._dt_rows.append((row, indicator, lbl_name, lbl_star, name))

    def _load_subcategories(self, kind):
        cached_all = self._cache.get('ALL') or {}
        if cached_all.get(kind):
            self._populate_detail_list(kind)
            return
        self._loading.add(kind)

        def worker():
            self._load_kind(kind)
            self._loading.discard(kind)
            self.app.after(0, lambda: self._populate_detail_list(kind))

        threading.Thread(target=worker, daemon=True).start()

    def _filter_focus_in(self):
        if self._filter_ent.get() == 'Filter\u2026':
            self._filter_ent.delete(0, 'end')
        self._filter_ent.configure(fg=INK)

    def _filter_focus_out(self):
        if not self._filter_ent.get():
            self._filter_ent.insert(0, 'Filter\u2026')
            self._filter_ent.configure(fg=MUTE)

    def _display_rows(self, rows, filt):
        if not filt:
            return rows
        f = filt.casefold()
        return [r for r in rows if f in r[1].casefold()]

    def _apply_filter(self, kind, text):
        self._populate_detail_list(kind)

    def _label(self, kind, r):
        if kind in ('models', 'actors', 'channels') and isinstance(r, dict) and r.get('count'):
            return f"{r['name']}  ({r['count']})"
        return r.get('name', '') if isinstance(r, dict) else str(r)

    def refresh(self):
        cached_all = self._cache.get('ALL') or {}
        if not all(cached_all.get(k) for k in ('tags', 'models', 'channels', 'actors')):
            threading.Thread(target=self._load_all, daemon=True).start()

    @staticmethod
    def _norm_tag(name):
        return ' '.join(str(name or '').split()).casefold()

    def _fetch_browser_kind(self, browser, kind):
        fn = getattr(browser, f'fetch_{kind}', None)
        if fn is None and kind == 'channels':
            fn = getattr(browser, 'fetch_studios', None)
        try:
            return fn() if fn else []
        except Exception as exc:
            print(f'fetch_{kind} on {browser} failed:', exc)
            return []

    def _process_kind_rows(self, kind, raw_rows):
        if kind == 'tags':
            groups = {}
            for r in sorted(raw_rows, key=lambda r: r.get('name', '').casefold()):
                key = self._norm_tag(r.get('name'))
                if not key or not r.get('url'):
                    continue
                g = groups.setdefault(key, {'name': str(r['name']).strip(), 'urls': []})
                if r['url'] not in g['urls']:
                    g['urls'].append(r['url'])
            return [groups[k] for k in sorted(groups)]
        elif kind == 'channels':
            cseen = set()
            channels = []
            for r in sorted(raw_rows, key=lambda r: (-r.get('count', 0), r.get('name', '').casefold())):
                u = r.get('url', '')
                k = u.rstrip('/')
                if k and k not in cseen:
                    cseen.add(k)
                    channels.append(r)
            return channels
        elif kind == 'actors':
            aseen = set()
            actors = []
            for r in sorted(raw_rows, key=lambda r: (-r.get('count', 0), r.get('name', '').casefold())):
                name = str(r.get('name', '')).strip()
                key = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
                if key and key not in aseen and r.get('url'):
                    aseen.add(key)
                    actors.append(r)
            return actors
        elif kind == 'models':
            mseen = set()
            models = []
            for r in sorted(raw_rows, key=lambda r: (-r.get('count', 0), r.get('name', '').casefold())):
                name = str(r.get('name', '')).strip()
                key = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
                if key and key not in mseen and r.get('url'):
                    mseen.add(key)
                    models.append(r)
            return models
        return raw_rows

    def _load_kind(self, kind):
        enabled = set(config.get_enabled_sources())
        active_browsers = []
        if 'FreePornVideos' in enabled:
            active_browsers.append(FreePornVideosBrowser)
        if 'OnePorn' in enabled:
            active_browsers.append(OnePornTVBrowser)
        if not active_browsers:
            active_browsers = [FreePornVideosBrowser, OnePornTVBrowser]

        rows = []
        threads = []
        lock = threading.Lock()

        def sub_work(b):
            res = self._fetch_browser_kind(b, kind)
            with lock:
                rows.extend(res)

        for b in active_browsers:
            t = threading.Thread(target=sub_work, args=(b,), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join(timeout=25)

        processed = self._process_kind_rows(kind, rows)
        cur = self._cache.get('ALL') or {}
        cur[kind] = processed
        self._cache['ALL'] = cur
        setattr(self, f'_full_{kind}', processed)
        config.save_sidebar_cache(cur)
        self.app.events.put(('sidebar_data', 'ALL', {kind: processed}))
        return processed

    def _load_all(self):
        kinds = ('tags', 'models', 'channels', 'actors')
        threads = []
        for kind in kinds:
            t = threading.Thread(target=self._load_kind, args=(kind,), daemon=True)
            t.start()
            threads.append(t)
        for t in threads:
            t.join(timeout=35)

    def _pairs_for(self, kind, rows):
        out = []
        for r in rows or []:
            if isinstance(r, dict):
                name = str(r.get('name') or '').strip()
                if not name:
                    continue
                if 'urls' in r and r['urls']:
                    out.append((r, name))
                elif 'url' in r and r['url']:
                    out.append((r, name))
            elif isinstance(r, str) and r.strip():
                out.append((r.strip(), r.strip()))
        return out

    def apply_data(self, site, result):
        if site == 'ALL':
            # Accumulate into the ALL cache instead of replacing it, so a
            # mid-load partial result (a single kind) never blanks out the
            # kinds that already arrived. The final merged result fills the rest.
            cur = self._cache.get('ALL') or {}
            cur.update(result)
            self._cache['ALL'] = cur
        else:
            self._cache.setdefault(site, {}).update(result)
        for kind, _label, _ico in self.TABS:
            if kind in result:
                rows = result.get(kind) or []
                setattr(self, f'_full_{kind}', rows)
                if kind == self._current_kind:
                    self.app.after(0, lambda k=kind: self._populate_detail_list(k))

    def reload_all(self):
        """Clear cache and reload sidebar data strictly for currently enabled sources."""
        self._cache.clear()
        self._loading.clear()
        for kind, _label, _ico in self.TABS:
            setattr(self, f'_full_{kind}', [])
        if hasattr(self, '_dt_inner') and bool(self._dt_inner.winfo_exists()):
            for w in self._dt_inner.winfo_children():
                w.destroy()
            lbl = tk.Label(self._dt_inner, text='  updating\u2026', bg=SIDEBAR_BG, fg=MUTE,
                           font=self.app.font_sans(10), anchor='w')
            lbl.pack(fill='x', padx=10, pady=8)
        threading.Thread(target=self._load_all, daemon=True).start()

    @staticmethod
    def _entry_matches(payload):
        if isinstance(payload, dict):
            name = payload.get('name')
            return lambda r: isinstance(r, dict) and r.get('name') == name
        url = payload
        return lambda r: (r.get('url') if isinstance(r, dict) else r) == url

    def remove_entry(self, kind, payload):
        hit = self._entry_matches(payload)
        rows = getattr(self, f'_full_{kind}', None)
        if rows:
            setattr(self, f'_full_{kind}', [r for r in rows if not hit(r)])
        cached = self._cache.get('ALL', {}).get(kind)
        if cached:
            self._cache['ALL'][kind] = [r for r in cached if not hit(r)]
        self.app.after(0, lambda k=kind: self._populate_detail_list(k))


# ==============================================================================
# SeekBar (Liquid Glass Video Transport)
# ==============================================================================

class SeekBar(tk.Canvas):
    """Liquid glass seek bar with smooth scrubber handle."""

    HEIGHT = 18

    def __init__(self, master, on_commit, **kw):
        super().__init__(master, height=self.HEIGHT, bd=0,
                         highlightthickness=0, bg=master['bg'], **kw)
        self._frac = 0.0
        self._dragging = False
        self._on_commit = on_commit
        self._hover = False

        self.bind('<Button-1>', self._on_press)
        self.bind('<B1-Motion>', self._on_drag)
        self.bind('<ButtonRelease-1>', self._on_release)
        self.bind('<Motion>', self._on_motion)
        self.bind('<Leave>', self._on_leave)

    def set_frac(self, frac):
        if not self._dragging:
            self._frac = min(max(frac, 0.0), 1.0)
            self._paint()

    def is_dragging(self):
        return self._dragging

    def _frac_at(self, x):
        w = max(self.winfo_width(), 1)
        return min(max(x / w, 0.0), 1.0)

    def _on_press(self, ev):
        self._dragging = True
        self._frac = self._frac_at(ev.x)
        self._paint()

    def _on_drag(self, ev):
        self._frac = self._frac_at(ev.x)
        self._paint()

    def _on_release(self, ev):
        self._dragging = False
        self._frac = self._frac_at(ev.x)
        self._paint()
        try:
            self._on_commit(self._frac)
        except Exception:
            pass

    def _on_motion(self, _e=None):
        self._hover = True
        self._paint()

    def _on_leave(self, _e=None):
        self._hover = False
        self._paint()

    def _paint(self, *_):
        self.delete('all')
        w = max(self.winfo_width(), 1)
        mid = self.HEIGHT // 2
        track_h = 5
        self.create_rectangle(2, mid - track_h // 2, w - 2, mid + track_h // 2,
                              fill='#2b2b3a', width=0)
        fx = 2 + int((w - 4) * self._frac)
        if fx > 2:
            self.create_rectangle(2, mid - track_h // 2, fx, mid + track_h // 2,
                                  fill='#0a84ff', width=0)
        if self._dragging or self._hover:
            self.create_oval(fx - 7, mid - 7, fx + 7, mid + 7,
                             fill='#ffffff', outline='#202028', width=1)


# ==============================================================================
# FetchXApp - Main High-DPI Desktop Application
# ==============================================================================

class FetchXApp(tk.Tk):
    def __init__(self):
        super().__init__()
        apply_global_palette(get_effective_theme())
        self.title(APP_TITLE)
        base = getattr(sys, '_MEIPASS', None) or os.path.dirname(os.path.abspath(__file__))
        ico = os.path.join(base, 'assets', 'fetchx.ico')
        if os.path.isfile(ico):
            try:
                self.iconbitmap(ico)
            except Exception:
                pass
            try:
                self._ico_img = Image.open(ico)
                self._ico_photo = ImageTk.PhotoImage(self._ico_img)
                self.iconphoto(True, self._ico_photo)
            except Exception:
                pass
        self._thumb_session = requests.Session()
        _adapter = HTTPAdapter(pool_connections=16, pool_maxsize=32, max_retries=1)
        self._thumb_session.mount('http://', _adapter)
        self._thumb_session.mount('https://', _adapter)
        self.geometry('1200x800')
        self.minsize(920, 620)
        self.configure(background=WINDOW_BG, bd=0, highlightthickness=0)

        self.save_dir = tk.StringVar(value=DEFAULT_SAVE_DIR)
        self.quality = tk.StringVar(value=QUALITY_CHOICES[0])
        self.page = 1
        self.current_base = None
        self._feed_mode = True
        self._feed_pages = {}
        self._browse_seq = 0
        self._sidebar_pending = None
        self._no_more = False
        self._browse_loading = False
        self._seen_urls = set()
        self._dup_cards = {}
        self._multi_urls = []
        self._multi_label = ''
        self._multi_pages = {}
        self._watchlist_verify = {}
        self.events = queue.Queue()
        self.rows = []
        self.row_lock = threading.Lock()
        self.running = False
        self.resolver_pool = futures.ThreadPoolExecutor(
            max_workers=4, thread_name_prefix='resolve')
        self.dl_pool = None
        self.thumb_pool = futures.ThreadPoolExecutor(
            max_workers=4, thread_name_prefix='thumb')
        self._thumb_cache = {}
        self._performer_avatar_cache = {}
        self._cards = []
        self._card_cols = 3
        self._grid_w = 0
        self._relayout_after = None
        self._selected_row = None
        self.browse_thread = None
        self._session_dismissed_cards = set()

        self._resolve_fonts()
        self._build_style()
        self._build_ui()
        analytics.track('session_start')
        self.bind_all('<Key>', self._on_global_key)
        self.after(120, self._poll_events)
        self.after(60, self._apply_borderless_chrome)
        self.after(250, self._load_persisted_queue)
        self.protocol('WM_DELETE_WINDOW', self._on_close)

    def _apply_borderless_chrome(self):
        if sys.platform != 'win32':
            return
        try:
            user32 = ctypes.windll.user32
            hwnd = user32.GetParent(self.winfo_id())
            if not hwnd:
                self.after(120, self._apply_borderless_chrome)
                return

            try:
                dwmapi = ctypes.windll.dwmapi
                DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                DWMWA_BORDER_COLOR = 34
                DWMWA_CAPTION_COLOR = 35
                is_dark = get_effective_theme() == 'dark'
                val = ctypes.c_int(1 if is_dark else 0)
                dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(val), ctypes.sizeof(val))
                color_hex = 0x00161212 if is_dark else 0x00f5f5f7
                color_val = ctypes.c_int(color_hex)
                dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_BORDER_COLOR, ctypes.byref(color_val), ctypes.sizeof(color_val))
                dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_CAPTION_COLOR, ctypes.byref(color_val), ctypes.sizeof(color_val))
            except Exception:
                pass

            get_long = getattr(user32, 'GetWindowLongPtrW', user32.GetWindowLongW)
            set_long = getattr(user32, 'SetWindowLongPtrW', user32.SetWindowLongW)
            GWL_STYLE = -16
            WS_CAPTION = 0x00C00000
            style = get_long(hwnd, GWL_STYLE)
            set_long(hwnd, GWL_STYLE, style & ~WS_CAPTION)
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            SWP_FRAMECHANGED = 0x0020
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                SWP_FRAMECHANGED | SWP_NOMOVE |
                                SWP_NOSIZE | SWP_NOZORDER)
            self._is_maximized = False
        except Exception as exc:
            print('borderless chrome skipped:', exc)

    # ---------- Windows Caption Controls (Top-Right) ----------
    def _win_minimize(self):
        try:
            self.iconify()
        except Exception:
            pass

    def _ensure_maximized(self):
        """Open the app maximized (fit to screen) on every launch."""
        try:
            self.update_idletasks()
            if self.state() != 'zoomed':
                self.state('zoomed')
                self._is_maximized = True
                if hasattr(self, 'win_controls'):
                    self.win_controls.set_maximized(True)
        except Exception:
            pass

    def _win_toggle_maximize(self):
        try:
            if self.state() == 'zoomed':
                self.state('normal')
                self._is_maximized = False
            else:
                self.state('zoomed')
                self._is_maximized = True
            if hasattr(self, 'win_controls'):
                self.win_controls.set_maximized(self._is_maximized)
        except Exception:
            pass

    def _win_close(self):
        self._on_close()

    def _win_refresh(self):
        """Refresh active view, clear/reload cache, and update feeds."""
        try:
            cur_tab = getattr(self, '_current_tab', 'browse')
            if cur_tab == 'browse':
                if hasattr(self, 'current_base') and self.current_base is not None:
                    self.browse_load(self.current_base, reset=True)
                elif hasattr(self, 'sidebar'):
                    act_key = getattr(self.sidebar, '_active_key', 'new')
                    self.sidebar._on_quick(act_key)
                else:
                    self.browse_load(reset=True)
            elif cur_tab == 'history':
                self._render_history()
            elif cur_tab == 'queue':
                if hasattr(self, 'save_dir'):
                    self.save_dir.set(config.get_save_dir())
            elif cur_tab == 'settings':
                pass

            if hasattr(self, 'sidebar'):
                self.sidebar.refresh()

            self.say('Refreshed')
        except Exception as exc:
            print('Refresh error:', exc)

    # ---------- Software Update Engine ----------
    def _check_for_updates_ui(self, user_triggered=False):
        """Checks GitHub releases for updates in background and updates UI/prompts user."""
        if getattr(self, '_checking_updates', False):
            return
        self._checking_updates = True

        if hasattr(self, 'lbl_update_status') and bool(self.lbl_update_status.winfo_exists()):
            self.lbl_update_status.configure(text='Status: Checking GitHub Releases…', fg=LINK)
        if hasattr(self, 'lbl_check_txt') and bool(self.lbl_check_txt.winfo_exists()):
            self.lbl_check_txt.configure(text='Checking…')

        def worker():
            try:
                info = updater.check_for_updates(current_version=APP_VERSION)
                config.set_last_update_check(time.time())
                self.after(0, lambda: self._on_update_check_done(info, user_triggered))
            except Exception as exc:
                self.after(0, lambda: self._on_update_check_error(str(exc), user_triggered))
            finally:
                self._checking_updates = False

        threading.Thread(target=worker, daemon=True).start()

    def _on_update_check_done(self, info, user_triggered):
        if hasattr(self, 'lbl_check_txt') and bool(self.lbl_check_txt.winfo_exists()):
            self.lbl_check_txt.configure(text='Check for Updates')

        if info and info.get('update_available'):
            latest = info.get('latest_version')
            if hasattr(self, 'lbl_update_status') and bool(self.lbl_update_status.winfo_exists()):
                self.lbl_update_status.configure(
                    text=f'Status: Update available (v{latest})! Click Update to install.', fg='#22c55e'
                )
            # Show interactive UpdateDialog
            UpdateDialog(self, self, info)
            self.show_toast(f'🎉 FetchX v{latest} is available!', icon='sparkles', color='#0070f3')
        else:
            if hasattr(self, 'lbl_update_status') and bool(self.lbl_update_status.winfo_exists()):
                self.lbl_update_status.configure(
                    text=f'Status: You are running the latest version of FetchX (v{APP_VERSION})', fg=MUTE
                )
            if user_triggered:
                self.show_toast(f'FetchX v{APP_VERSION} is up to date!', icon='check', color='#22c55e')

    def _on_update_check_error(self, err_msg, user_triggered):
        if hasattr(self, 'lbl_check_txt') and bool(self.lbl_check_txt.winfo_exists()):
            self.lbl_check_txt.configure(text='Check for Updates')
        if hasattr(self, 'lbl_update_status') and bool(self.lbl_update_status.winfo_exists()):
            self.lbl_update_status.configure(
                text=f'Status: Up to date (v{APP_VERSION})', fg=MUTE
            )
        if user_triggered:
            self.show_toast(f'FetchX v{APP_VERSION} is up to date!', icon='check', color=LINK)

    def _topbar_drag_start(self, event):
        if getattr(self, '_is_maximized', False):
            return
        self._drag_off = (event.x_root - self.winfo_x(),
                          event.y_root - self.winfo_y())

    def _topbar_drag_move(self, event):
        off = getattr(self, '_drag_off', None)
        if off is None or getattr(self, '_is_maximized', False):
            return
        x = event.x_root - off[0]
        y = event.y_root - off[1]
        self.geometry(f'+{max(x, -8)}+{max(y, 0)}')

    # ---------- design tokens & fonts ----------
    def _resolve_fonts(self):
        available = set(tkfont.families())
        def pick(candidates):
            for c in candidates:
                if c in available:
                    return c
            return candidates[-1]
        self._sans = pick(['Microsoft YaHei UI', 'Microsoft YaHei', 'Microsoft JhengHei UI',
                           'Microsoft JhengHei', 'Segoe UI Variable Display', 'Segoe UI',
                           'PingFang SC', 'Inter', 'SF Pro Display', 'Arial'])
        self._mono = pick(['Consolas', 'Cascadia Mono', 'Cascadia Code', 'Geist Mono',
                           'SF Pro Text', 'Courier New'])

    def font_sans(self, size, bold=False):
        return (self._sans, size, 'bold' if bold else 'normal')

    def font_mono(self, size, bold=False):
        return (self._mono, size, 'bold' if bold else 'normal')

    # ---------- styling ----------
    def _build_style(self):
        style = ttk.Style(self)
        try:
            style.theme_use('clam')
        except Exception:
            pass
        F = self._sans
        M = self._mono

        style.configure('.', background=CONTENT_BG, foreground=INK,
                        fieldbackground=CARD_BG, borderwidth=0,
                        focusthickness=0, font=(F, 11))

        style.configure('TFrame', background=CONTENT_BG, borderwidth=0, relief='flat')
        style.configure('Card.TFrame', background=CARD_BG, borderwidth=0, relief='flat')

        style.configure('TLabel', background=CONTENT_BG, foreground=INK, font=(F, 11))
        style.configure('Body.TLabel', background=CONTENT_BG, foreground=BODY)
        style.configure('Mute.TLabel', background=CONTENT_BG, foreground=MUTE, font=(F, 10))
        style.configure('CardInk.TLabel', background=CARD_BG, foreground=INK)
        style.configure('CardBody.TLabel', background=CARD_BG, foreground=BODY)
        style.configure('CardMute.TLabel', background=CARD_BG, foreground=MUTE, font=(F, 10))
        style.configure('Eyebrow.TLabel', background=CARD_BG, foreground=MUTE, font=(M, 10))
        style.configure('Chip.TLabel', background=HAIRLINE_SOFT, foreground=BODY, font=(M, 10))

        # Store generated images to keep references active
        self._style_imgs = {}

        # 1. Standard / Secondary Button (Dark Acrylic with rounded border, radius 7px)
        r = 7
        btn_normal = make_rounded_box_img(32, 32, r, '#252532', '#363648', 1)
        btn_hover = make_rounded_box_img(32, 32, r, '#303042', '#4e4e66', 1)
        btn_pressed = make_rounded_box_img(32, 32, r, '#1c1c26', '#262634', 1)
        btn_disabled = make_rounded_box_img(32, 32, r, '#191922', '#242430', 1)
        self._style_imgs['btn'] = (btn_normal, btn_hover, btn_pressed, btn_disabled)

        style.element_create("RoundedBtn.border", "image", btn_normal,
                             ("pressed", btn_pressed),
                             ("active", btn_hover),
                             ("disabled", btn_disabled),
                             border=8, sticky="nsew")

        style.layout("TButton", [
            ("RoundedBtn.border", {"sticky": "nsew", "children": [
                ("Button.padding", {"sticky": "nsew", "children": [
                    ("Button.label", {"sticky": "nswe"})
                ]})
            ]})
        ])
        style.configure("TButton", foreground=INK, font=(F, 11), padding=(18, 7))

        # 2. Primary Button (Apple System Blue, radius 7px)
        pri_normal = make_rounded_box_img(32, 32, r, LINK, LINK, 0)
        pri_hover = make_rounded_box_img(32, 32, r, LINK_HOVER, LINK_HOVER, 0)
        pri_pressed = make_rounded_box_img(32, 32, r, LINK_DEEP, LINK_DEEP, 0)
        pri_disabled = make_rounded_box_img(32, 32, r, '#363646', '#363646', 0)
        self._style_imgs['pri'] = (pri_normal, pri_hover, pri_pressed, pri_disabled)

        style.element_create("PrimaryBtn.border", "image", pri_normal,
                             ("pressed", pri_pressed),
                             ("active", pri_hover),
                             ("disabled", pri_disabled),
                             border=8, sticky="nsew")

        style.layout("Primary.TButton", [
            ("PrimaryBtn.border", {"sticky": "nsew", "children": [
                ("Button.padding", {"sticky": "nsew", "children": [
                    ("Button.label", {"sticky": "nswe"})
                ]})
            ]})
        ])
        style.configure("Primary.TButton", foreground='#ffffff', font=(F, 11), padding=(18, 7))

        style.layout("PrimarySm.TButton", [
            ("PrimaryBtn.border", {"sticky": "nsew", "children": [
                ("Button.padding", {"sticky": "nsew", "children": [
                    ("Button.label", {"sticky": "nswe"})
                ]})
            ]})
        ])
        style.configure("PrimarySm.TButton", foreground='#ffffff', font=(F, 10), padding=(14, 6))

        style.layout("Sm.TButton", [
            ("RoundedBtn.border", {"sticky": "nsew", "children": [
                ("Button.padding", {"sticky": "nsew", "children": [
                    ("Button.label", {"sticky": "nswe"})
                ]})
            ]})
        ])
        style.configure("Sm.TButton", foreground=INK, font=(F, 10), padding=(14, 6))

        # 3. Outline Button (Dark border, radius 7px)
        out_normal = make_rounded_box_img(32, 32, r, '#1b1b24', '#343446', 1)
        out_hover = make_rounded_box_img(32, 32, r, '#282836', '#505068', 1)
        out_pressed = make_rounded_box_img(32, 32, r, '#1c1c26', '#262634', 1)
        out_disabled = make_rounded_box_img(32, 32, r, '#15151c', '#20202a', 1)
        self._style_imgs['out'] = (out_normal, out_hover, out_pressed, out_disabled)

        style.element_create("OutlineBtn.border", "image", out_normal,
                             ("pressed", out_pressed),
                             ("active", out_hover),
                             ("disabled", out_disabled),
                             border=8, sticky="nsew")

        style.layout("OutlineSm.TButton", [
            ("OutlineBtn.border", {"sticky": "nsew", "children": [
                ("Button.padding", {"sticky": "nsew", "children": [
                    ("Button.label", {"sticky": "nswe"})
                ]})
            ]})
        ])
        style.configure("OutlineSm.TButton", foreground=INK, font=(F, 10), padding=(14, 6))

        # 4. Ghost Button
        style.layout("GhostSm.TButton", [
            ("Button.padding", {"sticky": "nsew", "children": [
                ("Button.label", {"sticky": "nswe"})
            ]})
        ])
        style.configure("GhostSm.TButton", font=(F, 10), padding=(14, 6),
                        background=CONTENT_BG, foreground=BODY, borderwidth=0)
        style.map("GhostSm.TButton", background=[("active", HOVER_SOFT)], foreground=[("active", INK)])

        # 5. Entry Fields (Rounded 9-slice, radius 7px)
        ent_normal = make_rounded_box_img(32, 32, r, SEARCH_BG, SEARCH_BORDER, 1)
        ent_focus = make_rounded_box_img(32, 32, r, SEARCH_BG, SEARCH_FOCUS, 1)
        ent_disabled = make_rounded_box_img(32, 32, r, '#15151c', '#22222e', 1)
        self._style_imgs['ent'] = (ent_normal, ent_focus, ent_disabled)

        style.element_create("RoundedEntry.field", "image", ent_normal,
                             ("focus", ent_focus),
                             ("disabled", ent_disabled),
                             border=8, sticky="nsew")

        style.layout("TEntry", [
            ("RoundedEntry.field", {"sticky": "nsew", "children": [
                ("Entry.padding", {"sticky": "nsew", "children": [
                    ("Entry.textarea", {"sticky": "nswe"})
                ]})
            ]})
        ])
        style.configure("TEntry", foreground=INK, insertcolor=INK,
                        padding=(12, 7), font=(F, 11),
                        selectbackground=LINK_SOFT, selectforeground=INK)

        style.layout("Flat.TEntry", [
            ("RoundedEntry.field", {"sticky": "nsew", "children": [
                ("Entry.padding", {"sticky": "nsew", "children": [
                    ("Entry.textarea", {"sticky": "nswe"})
                ]})
            ]})
        ])
        style.configure("Flat.TEntry", foreground=INK, insertcolor=INK,
                        padding=(12, 7), font=(F, 11),
                        selectbackground=LINK_SOFT, selectforeground=INK)

        # Combobox
        style.configure('TCombobox', fieldbackground=SEARCH_BG, foreground=INK,
                        arrowcolor=BODY, bordercolor=HAIRLINE,
                        lightcolor=HAIRLINE, darkcolor=HAIRLINE, padding=7,
                        font=(F, 11))
        style.map('TCombobox',
                  bordercolor=[('focus', LINK)],
                  fieldbackground=[('readonly', SEARCH_BG)],
                  foreground=[('readonly', INK)])
        self.option_add('*TCombobox*Listbox.background', CARD_BG)
        self.option_add('*TCombobox*Listbox.foreground', INK)
        self.option_add('*TCombobox*Listbox.selectBackground', LINK)
        self.option_add('*TCombobox*Listbox.selectForeground', '#ffffff')
        self.option_add('*TCombobox*Listbox.font', (F, 11))
        self.option_add('*TCombobox*Listbox.borderWidth', 1)

        # Progressbar
        style.configure('Blue.Horizontal.TProgressbar',
                        background=PROGRESS_BAR, troughcolor=PROGRESS_TROUGH,
                        bordercolor=CARD_BG, lightcolor=PROGRESS_BAR,
                        darkcolor=PROGRESS_BAR, thickness=8)

        # Scrollbars
        style.configure('Vertical.TScrollbar', background=SCROLLBAR,
                        troughcolor=CONTENT_BG, bordercolor=CONTENT_BG,
                        arrowcolor=MUTE, lightcolor=CONTENT_BG, darkcolor=CONTENT_BG)
        style.map('Vertical.TScrollbar', background=[('active', SCROLLBAR_ACTIVE)])
        style.configure('Sidebar.Vertical.TScrollbar',
                        background=SCROLLBAR, troughcolor=SIDEBAR_BG,
                        bordercolor=SIDEBAR_BG, arrowcolor=MUTE,
                        lightcolor=SIDEBAR_BG, darkcolor=SIDEBAR_BG,
                        arrowsize=10)
        style.map('Sidebar.Vertical.TScrollbar',
                  background=[('active', SCROLLBAR_ACTIVE)])

    def card(self, parent):
        outer = tk.Frame(parent, bg=CARD_BG, highlightthickness=1,
                         highlightbackground=CARD_BORDER)
        inner = tk.Frame(outer, bg=CARD_BG)
        inner.pack(fill='both', expand=True, padx=20, pady=18)
        return outer, inner

    def eyebrow(self, parent, text):
        return tk.Label(parent, text=str(text).upper(), bg=CARD_BG, fg=MUTE,
                        font=self.font_sans(10, bold=True))

    def _hero_button(self, parent, kind, command, size=22, bg=CARD_BG, fg=BODY, hover_fg=LINK):
        img = get_heroicon(kind, size=size, color=fg)
        lbl = tk.Label(parent, image=img, bg=bg, cursor='hand2', padx=5, pady=3)
        lbl.image = img
        lbl.bind('<Button-1>', lambda _e: command())
        lbl.bind('<Enter>', lambda _e: lbl.configure(image=get_heroicon(kind, size=size, color=hover_fg)))
        lbl.bind('<Leave>', lambda _e: lbl.configure(image=get_heroicon(kind, size=size, color=fg)))
        return lbl

    # ---------- Centered Topbar with Wide Search Bar & Windows Controls ----------
    def _build_topbar(self):
        self._is_maximized = False
        self._drag_off = None

        bar = tk.Frame(self, bg=WINDOW_BG, pady=6, bd=0, highlightthickness=0)
        bar.pack(fill='x', padx=0, pady=0)
        self.topbar = bar

        # Left section: Wordmark Logo
        left = tk.Frame(bar, bg=WINDOW_BG)
        left.pack(side='left', padx=(18, 0))

        img_norm = get_fetchx_wordmark(font_size=30, hover=False)
        img_hov = get_fetchx_wordmark(font_size=30, hover=True)
        wordmark = tk.Label(left, image=img_norm, bg=WINDOW_BG, cursor='hand2', bd=0, highlightthickness=0)
        wordmark.image = img_norm
        wordmark.pack(side='left', padx=(2, 16))

        def _on_wordmark_hover(enter):
            img = img_hov if enter else img_norm
            wordmark.configure(image=img)
            wordmark.image = img

        wordmark.bind('<Enter>', lambda _e: _on_wordmark_hover(True))
        wordmark.bind('<Leave>', lambda _e: _on_wordmark_hover(False))
        wordmark.bind('<Button-1>', lambda _e: self._on_home_click())

        # Right section: Windows Control Buttons
        right = tk.Frame(bar, bg=WINDOW_BG)
        right.pack(side='right', padx=0)

        self.win_controls = WindowsCaptionControls(
            right, on_close=self._win_close, on_min=self._win_minimize,
            on_max=self._win_toggle_maximize, on_refresh=self._win_refresh, bg=WINDOW_BG)
        self.win_controls.pack(side='right', padx=(10, 0))

        # Center section: Wide Search Bar placed in the middle
        center = tk.Frame(bar, bg=WINDOW_BG)
        center.pack(side='left', fill='both', expand=True, padx=(10, 10))

        self.top_search = GlassSearchBar(center, self, on_search=self._on_top_search,
                                         placeholder='Search videos\u2026', bg=WINDOW_BG)
        self.top_search.pack(expand=True, pady=2)

        # Draggable header bindings (for empty bar areas)
        for w in (bar, left, center):
            w.bind('<ButtonPress-1>', self._topbar_drag_start)
            w.bind('<B1-Motion>', self._topbar_drag_move)
            w.bind('<Double-Button-1>', lambda _e: self._win_toggle_maximize())

    def _on_home_click(self):
        # Close active video player if playing/open
        if hasattr(self, 'player_host') and (self.player_host.winfo_ismapped() or getattr(self, '_stage_live', False)):
            self.close_preview()
        # Reset search bar text
        if hasattr(self, 'top_search') and hasattr(self.top_search, 'entry'):
            try:
                self.top_search.entry.delete(0, 'end')
                self.top_search._on_focus_out()
            except Exception:
                pass
        # Reset sidebar view to main and trigger Newly Released feed
        if hasattr(self, 'sidebar'):
            try:
                self.sidebar._show_main()
                self.sidebar._on_quick('new')
            except Exception:
                pass

    def _build_search_urls(self, raw_query):
        """
        Builds robust, fault-tolerant search and recommendation URLs:
        1. Primary sanitized query slug URLs across active sources.
        2. Fuzzy taxonomy-corrected URLs (models, actresses, tags, channels, studios).
        3. Word-level keyword fallback URLs for multi-word queries.
        4. Trending / popular fallback URLs to ensure related videos always appear.
        """
        import difflib
        enabled = set(config.get_enabled_sources())
        clean_q = re.sub(r'[^a-zA-Z0-9\s]+', ' ', str(raw_query).strip().lower())
        words = [w for w in clean_q.split() if w]
        if not words:
            words = ['latest']
        primary_slug = '-'.join(words)
        q_str = ' '.join(words)

        sb_cache = config.get_sidebar_cache() or {}
        all_models = [m.get('name', '') for m in sb_cache.get('models', []) if m.get('name')]
        all_tags = [t.get('name', '') for t in sb_cache.get('tags', []) if t.get('name')]
        all_actors = [a.get('name', '') for a in sb_cache.get('actors', []) if a.get('name')]
        all_channels = [c.get('name', '') for c in sb_cache.get('channels', []) if c.get('name')]

        taxonomy = {}
        for m in all_models:
            taxonomy[m.lower()] = ('models', m)
        for a in all_actors:
            taxonomy[a.lower()] = ('actors', a)
        for t in all_tags:
            taxonomy[t.lower()] = ('tags', t)
        for c in all_channels:
            taxonomy[c.lower()] = ('sites', c)

        primary_urls = []
        if 'FreePornVideos' in enabled:
            primary_urls.append(f'https://www.freepornvideos.xxx/search/{primary_slug}/')
        if 'OnePorn' in enabled:
            primary_urls.append(f'https://www.1porn.tv/search/{primary_slug}/')
        if not primary_urls:
            primary_urls.append(f'https://www.freepornvideos.xxx/search/{primary_slug}/')

        fallback_urls = []
        best_suggestion = None

        # 1. Fuzzy match whole query against known performers, tags, studios
        close_keys = difflib.get_close_matches(q_str, list(taxonomy.keys()), n=4, cutoff=0.55)
        if close_keys:
            best_suggestion = taxonomy[close_keys[0]][1]
        for ck in close_keys:
            sec, orig_name = taxonomy[ck]
            c_slug = '-'.join(re.sub(r'[^a-zA-Z0-9\s]+', ' ', orig_name.lower()).split())
            if 'FreePornVideos' in enabled or not enabled:
                fallback_urls.append(f'https://www.freepornvideos.xxx/{sec}/{c_slug}/')
                fallback_urls.append(f'https://www.freepornvideos.xxx/search/{c_slug}/')
            if 'OnePorn' in enabled or not enabled:
                fallback_urls.append(f'https://www.1porn.tv/{sec}/{c_slug}/')
                fallback_urls.append(f'https://www.1porn.tv/search/{c_slug}/')

        # 2. Sub-words fuzzy match & single word searches
        if len(words) > 1:
            for w in words:
                if len(w) >= 3:
                    w_close = difflib.get_close_matches(w, list(taxonomy.keys()), n=2, cutoff=0.65)
                    for wk in w_close:
                        sec, orig_name = taxonomy[wk]
                        c_slug = '-'.join(re.sub(r'[^a-zA-Z0-9\s]+', ' ', orig_name.lower()).split())
                        if not best_suggestion:
                            best_suggestion = orig_name
                        if 'FreePornVideos' in enabled or not enabled:
                            fallback_urls.append(f'https://www.freepornvideos.xxx/search/{c_slug}/')
                        if 'OnePorn' in enabled or not enabled:
                            fallback_urls.append(f'https://www.1porn.tv/search/{c_slug}/')
                    if 'FreePornVideos' in enabled or not enabled:
                        fallback_urls.append(f'https://www.freepornvideos.xxx/search/{w}/')
                    if 'OnePorn' in enabled or not enabled:
                        fallback_urls.append(f'https://www.1porn.tv/search/{w}/')

        # 3. Trending / Popular fallback if query is completely unknown
        trending_urls = []
        if 'FreePornVideos' in enabled or not enabled:
            trending_urls.append('https://www.freepornvideos.xxx/most-popular/')
            trending_urls.append('https://www.freepornvideos.xxx/latest-updates/')
        if 'OnePorn' in enabled or not enabled:
            trending_urls.append('https://www.1porn.tv/most-popular/')
            trending_urls.append('https://www.1porn.tv/latest-updates/')

        seen = set()
        dedup_fallback = []
        for u in fallback_urls + trending_urls:
            if u not in seen and u not in primary_urls:
                seen.add(u)
                dedup_fallback.append(u)

        return primary_urls, dedup_fallback, best_suggestion

    def _on_top_search(self, q):
        q = str(q).strip()
        if not q:
            return
        self.switch_tab('browse')
        primary_urls, fallback_urls, best_suggestion = self._build_search_urls(q)
        self.browse_load({
            'name': f'search: {q}',
            'query': q,
            'urls': primary_urls,
            'fallback_urls': fallback_urls,
            'suggestion': best_suggestion
        }, reset=True)
        if best_suggestion and best_suggestion.lower() != q.lower():
            self.say(f'Searching for: {q} (related: {best_suggestion})')
        else:
            self.say(f'Searching active sources for: {q}')
        try:
            analytics.track('search', query=str(q)[:120])
        except Exception:
            pass

    # ---------- Navigation & Main Layout ----------
    def _build_ui(self):
        self._build_topbar()

        # Hairline divider under topbar
        self.topbar_divider = tk.Frame(self, bg=SIDEBAR_DIVIDER, height=1)
        self.topbar_divider.pack(fill='x')

        # Main App Layout: Permanent Left Sidebar + Right Content Pane
        main_holder = tk.Frame(self, bg=CONTENT_BG, bd=0, highlightthickness=0)
        main_holder.pack(fill='both', expand=True)
        self.main_holder = main_holder

        # Left Sidebar Navigation Spine
        self.sidebar_wrap = tk.Frame(main_holder, bg=SIDEBAR_BG, width=289, bd=0, highlightthickness=0)
        self.sidebar_wrap.pack(side='left', fill='y')
        self.sidebar_wrap.pack_propagate(False)

        # 1px hairline divider on the right edge of sidebar
        tk.Frame(self.sidebar_wrap, bg=SIDEBAR_DIVIDER, width=1
                 ).place(relx=1.0, rely=0.0, relheight=1.0, anchor='ne')

        self.sidebar = BrowseSidebar(self.sidebar_wrap, self, on_pick=self._on_sidebar_pick)
        self.sidebar.pack(fill='both', expand=True)

        # Right Content View Container
        self.content_holder = tk.Frame(main_holder, bg=CONTENT_BG, bd=0, highlightthickness=0)
        self.content_holder.pack(side='left', fill='both', expand=True)
        self.content_holder.grid_rowconfigure(0, weight=1)
        self.content_holder.grid_columnconfigure(0, weight=1)

        # Views
        self.view_browse = tk.Frame(self.content_holder, bg=CONTENT_BG, bd=0, highlightthickness=0)
        self.view_watch_later = tk.Frame(self.content_holder, bg=CONTENT_BG, bd=0, highlightthickness=0)
        self.view_queue = tk.Frame(self.content_holder, bg=CONTENT_BG, bd=0, highlightthickness=0)
        self.view_history = tk.Frame(self.content_holder, bg=CONTENT_BG, bd=0, highlightthickness=0)
        self.view_settings = tk.Frame(self.content_holder, bg=CONTENT_BG, bd=0, highlightthickness=0)

        for v in (self.view_browse, self.view_watch_later, self.view_queue, self.view_history, self.view_settings):
            v.grid(row=0, column=0, sticky='nsew')

        # ===== 1. Browse View =====
        self._build_browse_view()

        # ===== 2. Watch Later View =====
        self._build_watch_later_view()

        # ===== 3. Downloads Queue View =====
        self._build_downloads_view()

        # ===== 4. History View =====
        self._build_history_view()
        self._render_history()

        # ===== 5. Settings View =====
        self._build_settings_view()

        # Key shortcuts
        self.bind_all('<Key>', self._on_global_key)

        # Default start on Browse -> Newly Released
        self.switch_tab('browse')
        self.sidebar._on_quick('new')
        self.sidebar.refresh()

        # Always open maximized (fit to screen)
        self._ensure_maximized()
        self.after_idle(self._ensure_maximized)

        # Check for updates automatically in background on startup
        if config.get_auto_check_updates():
            self.after(3500, lambda: self._check_for_updates_ui(user_triggered=False))

        # Immediately display announcements on launch (0ms delay)
        self._load_initial_announcements()

        # Check for remote updates in background
        if config.get_announcements_enabled():
            self.after(600, lambda: self._fetch_remote_announcements(user_triggered=False))

    def switch_tab(self, tab_key):
        """Switches the right pane to the specified tab and updates sidebar state."""
        view_map = {
            'browse': self.view_browse,
            'watch_later': self.view_watch_later,
            'queue': self.view_queue,
            'history': self.view_history,
            'settings': self.view_settings,
        }
        target = view_map.get(tab_key)
        if target:
            target.tkraise()
            self._current_tab = tab_key
            if not getattr(self, 'player_host', None) or not self.player_host.winfo_ismapped() or tab_key != 'browse':
                if not self.sidebar_wrap.winfo_ismapped():
                    self.sidebar_wrap.pack(side='left', fill='y', before=self.content_holder)
            if tab_key in ('queue', 'history', 'settings', 'watch_later'):
                self.sidebar.set_active(tab_key)
            if tab_key == 'watch_later':
                self._render_watch_later()

    # ---------- Browse View & Player ----------
    def _build_browse_view(self):
        self.view_browse.grid_rowconfigure(0, weight=1)
        self.view_browse.grid_columnconfigure(0, weight=1)

        # Video Grid Outer
        grid_outer = tk.Frame(self.view_browse, bg=CONTENT_BG, bd=0, highlightthickness=0)
        grid_outer.grid(row=0, column=0, sticky='nsew')
        self.grid_outer = grid_outer

        self.back_bar = tk.Frame(grid_outer, bg=CONTENT_BG)

        # Liquid Glass "Back to video" Pill Button (Compact Sapphire Glass)
        self.btn_back_video = tk.Frame(self.back_bar, bg=PILL_PRI_BG, highlightthickness=1,
                                       highlightbackground=PILL_PRI_BORDER, cursor='hand2')
        self.btn_back_video.pack(side='left')

        back_ico = get_heroicon('arrow_left', size=13, color=LINK)
        self.lbl_back_video = tk.Label(self.btn_back_video, text=' Back to video', image=back_ico,
                                       compound='left', bg=PILL_PRI_BG, fg=PILL_PRI_FG,
                                       font=self.font_sans(9, bold=True), cursor='hand2',
                                       padx=8, pady=3)
        self.lbl_back_video.image = back_ico
        self.lbl_back_video.pack()

        def _on_back_hover(enter):
            bg = PILL_PRI_HOVER_BG if enter else PILL_PRI_BG
            bd = PILL_PRI_HOVER_BD if enter else PILL_PRI_BORDER
            fg = PILL_PRI_HOVER_FG if enter else PILL_PRI_FG
            ico_col = PILL_PRI_HOVER_FG if enter else LINK
            self.btn_back_video.configure(bg=bg, highlightbackground=bd)
            h_ico = get_heroicon('arrow_left', size=13, color=ico_col)
            self.lbl_back_video.configure(bg=bg, fg=fg, image=h_ico)
            self.lbl_back_video.image = h_ico

        for w in (self.btn_back_video, self.lbl_back_video):
            w.bind('<Button-1>', lambda _e: self._exit_preview_nav())
            w.bind('<Enter>', lambda _e: _on_back_hover(True))
            w.bind('<Leave>', lambda _e: _on_back_hover(False))

        tk.Label(self.back_bar, text='●  player paused', bg=CONTENT_BG,
                 fg=MUTE, font=self.font_sans(9)).pack(side='left', padx=(10, 0))

        # ===== Watchlist Liquid Glass Top Bar =====
        self.watchlist_bar = tk.Frame(grid_outer, bg=CONTENT_BG)
        self._watchlist_active_cat = 'all'
        self._watchlist_active_item = None

        # ===== Dynamic Remote Announcement Banner Container =====
        self.announcement_bar = tk.Frame(grid_outer, bg=CONTENT_BG)

        # Video Grid Canvas Container
        cards_body = tk.Frame(grid_outer, bg=CONTENT_BG, bd=0, highlightthickness=0)
        cards_body.pack(side='top', fill='both', expand=True)
        self.cards_body = cards_body

        self.cards_canvas = tk.Canvas(cards_body, bg=CONTENT_BG, bd=0, highlightthickness=0)
        gvsb = ttk.Scrollbar(cards_body, orient='vertical', command=self.cards_canvas.yview)
        self.cards_canvas.configure(yscrollcommand=gvsb.set)
        gvsb.pack(side='right', fill='y')
        self.cards_canvas.pack(side='left', fill='both', expand=True)

        self.cards_inner = tk.Frame(self.cards_canvas, bg=CONTENT_BG, bd=0, highlightthickness=0)
        self.cards_canvas.create_window((0, 0), window=self.cards_inner, anchor='nw', tags='cards')
        self.cards_inner.bind(
            '<Configure>',
            lambda _e: self.cards_canvas.configure(scrollregion=self.cards_canvas.bbox('all')))
        self.cards_canvas.bind('<Configure>', self._on_cards_configure)
        self._mousewheel_bind(self.cards_canvas, self._on_cards_wheel)

        self.lbl_cards_empty = tk.Label(
            self.cards_inner,
            text='Select a category or search for videos above.',
            bg=CONTENT_BG, fg=FAINT, pady=60, font=self.font_sans(12))
        self.lbl_cards_empty.grid(row=0, column=0,
                                  columnspan=max(1, getattr(self, '_card_cols', 3)),
                                  sticky='nsew')

        # ===== Inline VLC Video Player Preview =====
        self.player_host = tk.Frame(self.view_browse, bg=CONTENT_BG, bd=0, highlightthickness=0)
        self.player_host.bind('<Configure>', self._on_player_host_configure)

        # Single Unified Scrollable container for video player + recommendations (like YouTube)
        self.player_canvas = tk.Canvas(self.player_host, bg=CONTENT_BG, bd=0, highlightthickness=0)
        self.player_vsb = ttk.Scrollbar(self.player_host, orient='vertical', command=self.player_canvas.yview)
        self.player_canvas.configure(yscrollcommand=self.player_vsb.set)
        self.player_vsb.pack(side='right', fill='y')
        self.player_canvas.pack(side='left', fill='both', expand=True)

        pbody = tk.Frame(self.player_canvas, bg=CONTENT_BG, bd=0, highlightthickness=0)
        self.pbody = pbody
        self._pbody_win = self.player_canvas.create_window((0, 0), window=pbody, anchor='nw', tags='pbody_win')
        pbody.bind('<Configure>', lambda _e: self._update_player_vsb())
        self.player_canvas.bind('<Configure>', self._on_player_canvas_configure)
        self._mousewheel_bind(self.player_canvas, self._on_player_wheel)
        self._bind_wheel_recursive(pbody, self._on_player_wheel)

        # --- Left Column: Main Player & Info ---
        self.player_main_col = tk.Frame(pbody, bg=CONTENT_BG, bd=0, highlightthickness=0)
        self.player_main_col.pack(side='left', fill='x', expand=True, anchor='n')

        ph_head = tk.Frame(self.player_main_col, bg=CONTENT_BG)
        ph_head.pack(fill='x', padx=(20, 16), pady=(12, 0))
        self.ph_head = ph_head

        tk.Label(ph_head, text=' PREVIEW ', bg=ELEVATED, fg=INK,
                 font=self.font_mono(8, bold=True), padx=4, pady=1).pack(side='left')
        self.preview_title = tk.Label(ph_head, text='', bg=CONTENT_BG, fg=INK,
                                      anchor='w', font=self.font_sans(10, bold=True))
        self.preview_title.pack(side='left', fill='x', expand=True, padx=(10, 8))
        self.preview_status = tk.Label(ph_head, text='', bg=CONTENT_BG,
                                       fg=MUTE, font=self.font_mono(9))
        self.preview_status.pack(side='left', padx=(0, 10))

        # Liquid Glass Action Buttons
        # Close Button (Frosted Smoked Glass Pill)
        self.btn_close_head = tk.Frame(ph_head, bg=PILL_SEC_BG, highlightthickness=1,
                                       highlightbackground=PILL_SEC_BORDER, cursor='hand2')
        self.btn_close_head.pack(side='right', padx=(6, 0))
        self.lbl_close_head = tk.Label(self.btn_close_head, text='✕ Close', bg=PILL_SEC_BG,
                                       fg=PILL_SEC_FG, font=self.font_sans(9, bold=True),
                                       cursor='hand2', padx=8, pady=3)
        self.lbl_close_head.pack()

        def _on_close_hover(enter):
            bg = PILL_SEC_HOVER_BG if enter else PILL_SEC_BG
            bd = ERROR if enter else PILL_SEC_BORDER
            fg = ERROR if enter else PILL_SEC_FG
            self.btn_close_head.configure(bg=bg, highlightbackground=bd)
            self.lbl_close_head.configure(bg=bg, fg=fg)

        for w in (self.btn_close_head, self.lbl_close_head):
            w.bind('<Button-1>', lambda _e: self.close_preview())
            w.bind('<Enter>', lambda _e: _on_close_hover(True))
            w.bind('<Leave>', lambda _e: _on_close_hover(False))

        self.preview_stage = tk.Frame(self.player_main_col, bg='#000000', highlightthickness=1,
                                      highlightbackground=CARD_BORDER, cursor='hand2')
        self.preview_stage.pack(fill='x', pady=(10, 4), padx=(20, 16))
        self.preview_stage.bind('<Configure>', self._on_stage_configure)

        self.preview_placeholder = tk.Label(
            self.preview_stage, text='▶  Pick a video and press Watch',
            bg='#000000', fg=MUTE, pady=60, font=self.font_sans(12), cursor='hand2')
        self.preview_video = tk.Frame(self.preview_stage, bg='#000000', cursor='hand2')
        self.preview_placeholder.pack(expand=True)

        for w in (self.preview_stage, self.preview_video, self.preview_placeholder):
            w.bind('<Double-Button-1>', lambda _e: self._toggle_fullscreen())

        # Transport Controls (Inline Single Row)
        self.preview_transport = tk.Frame(self.player_main_col, bg=CONTENT_BG)

        # Left controls: Play/Pause, Skip Back/Fwd, Mute & Volume, Current Time
        play_img = get_heroicon('play', size=24, color=INK)
        self.btn_pp = tk.Label(self.preview_transport, image=play_img, bg=CONTENT_BG, cursor='hand2')
        self.btn_pp.image = play_img
        self.btn_pp.pack(side='left', padx=(2, 6))
        self.btn_pp.bind('<Button-1>', lambda _e: self.preview_toggle_play())

        b_img = get_heroicon('backward', size=24, color=BODY)
        self.btn_back = tk.Label(self.preview_transport, image=b_img, bg=CONTENT_BG, cursor='hand2')
        self.btn_back.image = b_img
        self.btn_back.pack(side='left', padx=(0, 6))
        self.btn_back.bind('<Button-1>', lambda _e: self.preview_skip(-10))

        f_img = get_heroicon('forward', size=24, color=BODY)
        self.btn_fwd = tk.Label(self.preview_transport, image=f_img, bg=CONTENT_BG, cursor='hand2')
        self.btn_fwd.image = f_img
        self.btn_fwd.pack(side='left', padx=(0, 10))
        self.btn_fwd.bind('<Button-1>', lambda _e: self.preview_skip(10))

        mute_img = get_heroicon('speaker_wave', size=24, color=BODY)
        self.btn_mute = tk.Label(self.preview_transport, image=mute_img, bg=CONTENT_BG, cursor='hand2')
        self.btn_mute.image = mute_img
        self.btn_mute.pack(side='left', padx=(0, 4))
        self.btn_mute.bind('<Button-1>', lambda _e: self.preview_toggle_mute())

        self.vol_scale = ttk.Scale(self.preview_transport, from_=0, to=100, orient='horizontal',
                                   length=80, command=self._on_volume_move)
        self.vol_scale.set(70)
        self.vol_scale.pack(side='left', padx=(0, 4))

        self.lbl_vol = tk.Label(self.preview_transport, text='70%', bg=CONTENT_BG, fg=MUTE,
                                font=self.font_mono(10), width=4, anchor='w')
        self.lbl_vol.pack(side='left', padx=(0, 8))

        self.lbl_cur = tk.Label(self.preview_transport, text='0:00', bg=CONTENT_BG, fg=MUTE,
                                font=self.font_mono(10), width=5, anchor='e')
        self.lbl_cur.pack(side='left', padx=(0, 4))

        # Right controls: Fullscreen, Duration (packed in reverse order)
        fs_img = get_heroicon('fullscreen', size=24, color=BODY)
        self.btn_fs = tk.Label(self.preview_transport, image=fs_img, bg=CONTENT_BG, cursor='hand2')
        self.btn_fs.image = fs_img
        self.btn_fs.pack(side='right', padx=(6, 2))
        self.btn_fs.bind('<Button-1>', lambda _e: self._toggle_fullscreen())

        self.lbl_dur = tk.Label(self.preview_transport, text='0:00', bg=CONTENT_BG, fg=MUTE,
                                font=self.font_mono(10), width=5, anchor='w')
        self.lbl_dur.pack(side='right', padx=(4, 0))

        # Center seek bar: expands to fill remaining space
        self.seek_bar = SeekBar(self.preview_transport, self._on_seek_commit)
        self.seek_bar.pack(side='left', fill='x', expand=True, padx=(4, 4))

        self._vlc_inst = None
        self.player = None
        self._vol = 70
        self._muted = False
        self._pending_watch_item = None
        self._watch_recorded = True
        self._fs_active = False
        self._fs_win = None
        self._preview_closing = False
        self._preview_item = None
        self._preview_url = ''
        self._preview_seq = 0
        self._player_layout_mode = None

        self.preview_info = tk.Frame(self.player_main_col, bg=CONTENT_BG)
        self.preview_info.pack(fill='x', pady=(10, 0), padx=(20, 16))

        # --- Recommendations Section (in same unified scroll container) ---
        recs = tk.Frame(pbody, bg=CARD_BG, highlightthickness=1,
                        highlightbackground=CARD_BORDER)
        self.recs_panel = recs
        self.recs_panel.configure(width=self.RECS_W)

        rhead = tk.Frame(recs, bg=CARD_BG)
        rhead.pack(fill='x', padx=14, pady=(14, 10))
        self.lbl_recs_hdr = tk.Label(rhead, text='Recommended', bg=CARD_BG, fg=INK,
                                     font=self.font_sans(12, bold=True))
        self.lbl_recs_hdr.pack(side='left')

        # Shuffle Liquid Glass Pill Button
        self.btn_shuffle = tk.Frame(rhead, bg=PILL_SEC_BG, highlightthickness=1,
                                    highlightbackground=PILL_SEC_BORDER, cursor='hand2')
        self.btn_shuffle.pack(side='right', padx=(8, 0))
        self.lbl_shuffle = tk.Label(self.btn_shuffle, text='Shuffle', bg=PILL_SEC_BG,
                                    fg=PILL_SEC_FG, font=self.font_sans(9, bold=True),
                                    cursor='hand2', padx=8, pady=2)
        self.lbl_shuffle.pack()

        def _on_shuffle_hover(enter):
            bg = PILL_SEC_HOVER_BG if enter else PILL_SEC_BG
            bd = '#2563eb' if enter else '#3d3d52'
            fg = PILL_SEC_HOVER_FG if enter else PILL_SEC_FG
            self.btn_shuffle.configure(bg=bg, highlightbackground=bd)
            self.lbl_shuffle.configure(bg=bg, fg=fg)

        for w in (self.btn_shuffle, self.lbl_shuffle):
            w.bind('<Button-1>', lambda _e: self.shuffle_recommendations())
            w.bind('<Enter>', lambda _e: _on_shuffle_hover(True))
            w.bind('<Leave>', lambda _e: _on_shuffle_hover(False))

        self.lbl_recs_status = tk.Label(rhead, text='', bg=CARD_BG,
                                        fg=MUTE, font=self.font_mono(10))
        self.lbl_recs_status.pack(side='right')

        self.recs_inner = tk.Frame(recs, bg=CARD_BG)
        self.recs_inner.pack(fill='both', expand=True, padx=6, pady=(0, 10))

        self.lbl_recs_empty = tk.Label(self.recs_inner, text='Loading related videos\u2026',
                                       bg=CARD_BG, fg=MUTE, wraplength=self.RECS_W - 56,
                                       justify='left', anchor='w', font=self.font_sans(10), pady=16)
        self.lbl_recs_empty.pack(fill='x', padx=14)
        self._bind_wheel_recursive(recs, self._on_player_wheel)


    # ---------- Downloads View ----------
    def _build_downloads_view(self):
        loc_card, loc_inner = self.card(self.view_queue)
        loc_card.pack(fill='x', pady=(16, 12), padx=24)

        loc_row = tk.Frame(loc_inner, bg=CARD_BG)
        loc_row.pack(fill='x')

        ttk.Label(loc_row, text='Download Folder', style='CardBody.TLabel'
                  ).pack(side='left', padx=(0, 14))

        self.folder_input_dl = GeistFolderInput(
            loc_row,
            app=self,
            textvariable=self.save_dir,
            on_browse=self._pick_folder,
            on_open=self._open_save_folder,
            placeholder='Choose download folder…',
        )
        self.folder_input_dl.pack(side='left', fill='x', expand=True)

        qual = tk.Frame(loc_row, bg=CARD_BG)
        qual.pack(side='left', padx=(18, 0))
        ttk.Label(qual, text='Quality', style='CardBody.TLabel').pack(side='left', padx=(0, 8))
        self.quality_select = GeistSelect(
            qual,
            app=self,
            textvariable=self.quality,
            values=list(QUALITY_CHOICES),
            size='small',
            on_change=lambda val: set_resolution_pref(val)
        )
        self.quality_select.pack(side='left')

        # Queue List Card
        q_card, q_inner = self.card(self.view_queue)
        q_card.pack(fill='both', expand=True, pady=(0, 16), padx=24)

        q_head = tk.Frame(q_inner, bg=CARD_BG)
        q_head.pack(fill='x')
        self.eyebrow(q_head, 'Active Downloads & Queue').pack(side='left')

        outer = tk.Frame(q_inner, bg=CARD_BG)
        outer.pack(fill='both', expand=True, pady=(14, 0))
        outer.grid_rowconfigure(0, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        self.queue_canvas = tk.Canvas(outer, bg=CARD_BG, bd=0, highlightthickness=0)
        self.vsb = ttk.Scrollbar(outer, orient='vertical', command=self.queue_canvas.yview)
        self.queue_canvas.configure(yscrollcommand=self.vsb.set)
        self.queue_canvas.grid(row=0, column=0, sticky='nsew')

        self.queue_inner = tk.Frame(self.queue_canvas, bg=CARD_BG)
        self.queue_canvas.create_window((0, 0), window=self.queue_inner, anchor='nw', tags='inner')
        self.queue_inner.bind('<Configure>', self._on_inner_configure)
        self.queue_canvas.bind(
            '<Configure>',
            lambda e: (self.queue_canvas.itemconfigure('inner', width=e.width),
                       self.after_idle(self._update_vsb)))
        self._mousewheel_bind(self.queue_canvas)
        self.after_idle(self._update_vsb)

        # Batch actions (Compact Liquid Glass Pills)
        qbar = tk.Frame(q_inner, bg=CARD_BG)
        qbar.pack(fill='x', pady=(14, 0))

        # Start all (Liquid Sapphire Pill)
        self.btn_start = tk.Frame(qbar, bg=PILL_PRI_BG, highlightthickness=1,
                                  highlightbackground=PILL_PRI_BORDER, cursor='hand2')
        self.btn_start.pack(side='left')
        self.lbl_start = tk.Label(self.btn_start, text='Start all', bg=PILL_PRI_BG,
                                  fg=PILL_PRI_FG, font=self.font_sans(9, bold=True),
                                  cursor='hand2', padx=10, pady=3)
        self.lbl_start.pack()

        def _on_start_hover(enter):
            bg=PILL_PRI_HOVER_BG if enter else PILL_PRI_BG
            bd = PILL_PRI_HOVER_BD if enter else PILL_PRI_BORDER
            fg = PILL_PRI_HOVER_FG if enter else PILL_PRI_FG
            self.btn_start.configure(bg=bg, highlightbackground=bd)
            self.lbl_start.configure(bg=bg, fg=fg)

        for w in (self.btn_start, self.lbl_start):
            w.bind('<Button-1>', lambda _e: self.start_all())
            w.bind('<Enter>', lambda _e: _on_start_hover(True))
            w.bind('<Leave>', lambda _e: _on_start_hover(False))

        # Cancel all (Liquid Smoked Quartz Pill with Crimson Hover)
        self.btn_cancel_all = tk.Frame(qbar, bg=PILL_SEC_BG, highlightthickness=1,
                                       highlightbackground=PILL_SEC_BORDER, cursor='hand2')
        self.btn_cancel_all.pack(side='left', padx=(8, 0))
        self.lbl_cancel_all = tk.Label(self.btn_cancel_all, text='Cancel all', bg=PILL_SEC_BG,
                                       fg=PILL_SEC_FG, font=self.font_sans(9, bold=True),
                                       cursor='hand2', padx=10, pady=3)
        self.lbl_cancel_all.pack()

        def _on_cancel_hover(enter):
            bg = PILL_SEC_HOVER_BG if enter else PILL_SEC_BG
            bd = '#ef4444' if enter else PILL_SEC_BORDER
            fg = '#ef4444' if enter else PILL_SEC_FG
            self.btn_cancel_all.configure(bg=bg, highlightbackground=bd)
            self.lbl_cancel_all.configure(bg=bg, fg=fg)

        for w in (self.btn_cancel_all, self.lbl_cancel_all):
            w.bind('<Button-1>', lambda _e: self.cancel_all())
            w.bind('<Enter>', lambda _e: _on_cancel_hover(True))
            w.bind('<Leave>', lambda _e: _on_cancel_hover(False))

        # Clear finished (Liquid Smoked Quartz Pill)
        self.btn_clear_fin = tk.Frame(qbar, bg=PILL_SEC_BG, highlightthickness=1,
                                      highlightbackground=PILL_SEC_BORDER, cursor='hand2')
        self.btn_clear_fin.pack(side='left', padx=(8, 0))
        self.lbl_clear_fin = tk.Label(self.btn_clear_fin, text='Clear finished', bg=PILL_SEC_BG,
                                      fg=PILL_SEC_FG, font=self.font_sans(9, bold=True),
                                      cursor='hand2', padx=10, pady=3)
        self.lbl_clear_fin.pack()

        def _on_clear_hover(enter):
            bg = PILL_SEC_HOVER_BG if enter else PILL_SEC_BG
            bd = PILL_SEC_HOVER_BD if enter else PILL_SEC_BORDER
            fg = PILL_SEC_HOVER_FG if enter else PILL_SEC_FG
            self.btn_clear_fin.configure(bg=bg, highlightbackground=bd)
            self.lbl_clear_fin.configure(bg=bg, fg=fg)

        for w in (self.btn_clear_fin, self.lbl_clear_fin):
            w.bind('<Button-1>', lambda _e: self.clear_finished())
            w.bind('<Enter>', lambda _e: _on_clear_hover(True))
            w.bind('<Leave>', lambda _e: _on_clear_hover(False))

        self.lbl_overall = ttk.Label(qbar, text='', style='CardMute.TLabel')
        self.lbl_overall.pack(side='right')

        empty = tk.Label(self.queue_inner,
                         text='Nothing queued yet \u2014 browse videos and click "+ Queue" or "Download".',
                         bg=CARD_BG, fg=FAINT, pady=42, font=self.font_sans(11))
        empty.pack(fill='x')
        self.empty_hint = empty

    # ---------- Settings View ----------
    def _build_settings_view(self):
        page = self.view_settings

        sc = tk.Canvas(page, bg=CONTENT_BG, bd=0, highlightthickness=0)
        ssb = ttk.Scrollbar(page, orient='vertical', command=sc.yview)
        sc.configure(yscrollcommand=ssb.set)
        ssb.pack(side='right', fill='y')
        sc.pack(side='left', fill='both', expand=True)

        inner = tk.Frame(sc, bg=CONTENT_BG)
        sc.create_window((0, 0), window=inner, anchor='nw', tags='settings_inner')
        inner.bind('<Configure>', lambda _e: sc.configure(scrollregion=sc.bbox('all')))
        sc.bind('<Configure>', lambda e: sc.itemconfigure('settings_inner', width=e.width))
        self._mousewheel_bind(sc)

        # Permanent Telegram Community Banner
        tg_url = 'https://t.me/FetchJAV'
        tg_accent = '#229ED9'

        banner_fr = tk.Frame(inner, bg=HAIRLINE_SOFT, highlightthickness=1,
                             highlightbackground=tg_accent, cursor='hand2')
        banner_fr.pack(fill='x', padx=28, pady=(18, 14))

        banner_in = tk.Frame(banner_fr, bg=HAIRLINE_SOFT, padx=14, pady=12)
        banner_in.pack(fill='x')

        # Telegram Icon Badge on Left
        tg_badge_img = get_heroicon('telegram_badge', size=42, color=tg_accent)
        lbl_tg_icon = tk.Label(banner_in, image=tg_badge_img, bg=HAIRLINE_SOFT, cursor='hand2', bd=0)
        lbl_tg_icon.image = tg_badge_img
        lbl_tg_icon.pack(side='left', padx=(0, 14))

        # Center: Eyebrow + Title + Message
        tg_center = tk.Frame(banner_in, bg=HAIRLINE_SOFT)
        tg_center.pack(side='left', fill='both', expand=True)

        tg_row_top = tk.Frame(tg_center, bg=HAIRLINE_SOFT)
        tg_row_top.pack(fill='x', anchor='w')

        lbl_tg_badge = tk.Label(tg_row_top, text=' TELEGRAM GROUP ', bg=ELEVATED, fg=tg_accent,
                                font=self.font_mono(8, bold=True),
                                highlightthickness=1, highlightbackground=tg_accent,
                                padx=6, pady=2)
        lbl_tg_badge.pack(side='left', padx=(0, 8))

        lbl_tg_title = tk.Label(tg_row_top, text='Join the FetchJAV Telegram Community', bg=HAIRLINE_SOFT, fg=INK,
                                font=self.font_sans(11, bold=True), anchor='w')
        lbl_tg_title.pack(side='left', fill='x')

        lbl_tg_msg = tk.Label(tg_center,
                              text='Join https://t.me/FetchJAV for instant announcements, latest releases, community discussions, and direct support.',
                              bg=HAIRLINE_SOFT, fg=BODY, font=self.font_sans(9), justify='left', anchor='w', wraplength=480)
        lbl_tg_msg.pack(fill='x', anchor='w', pady=(4, 0))
        tg_center.bind('<Configure>', lambda e, l=lbl_tg_msg: l.configure(wraplength=max(200, e.width - 20)))

        # Right: Action Button
        tg_right = tk.Frame(banner_in, bg=HAIRLINE_SOFT)
        tg_right.pack(side='right', padx=(10, 0))

        btn_tg_join = tk.Frame(tg_right, bg=tg_accent, highlightthickness=1,
                               highlightbackground=tg_accent, cursor='hand2', padx=14, pady=7)
        btn_tg_join.pack(side='left')

        tg_btn_ico = get_heroicon('telegram', size=16, color='#ffffff')
        lbl_tg_btn_ico = tk.Label(btn_tg_join, image=tg_btn_ico, bg=tg_accent, bd=0, cursor='hand2')
        lbl_tg_btn_ico.image = tg_btn_ico
        lbl_tg_btn_ico.pack(side='left', padx=(0, 6))

        lbl_tg_btn_txt = tk.Label(btn_tg_join, text='Join Group', bg=tg_accent, fg='#ffffff',
                                  font=self.font_sans(10, bold=True), cursor='hand2')
        lbl_tg_btn_txt.pack(side='left')

        def _on_tg_btn_hover(enter):
            h_bg = '#1d8ec4' if enter else tg_accent
            btn_tg_join.configure(bg=h_bg, highlightbackground=h_bg)
            lbl_tg_btn_ico.configure(bg=h_bg)
            lbl_tg_btn_txt.configure(bg=h_bg)

        def _open_telegram(_e=None):
            self._open_external_url(tg_url)
            self.show_toast('Opening Telegram Group (https://t.me/FetchJAV)…', icon='telegram', color=tg_accent)

        for w in (btn_tg_join, lbl_tg_btn_ico, lbl_tg_btn_txt):
            w.bind('<Button-1>', _open_telegram)
            w.bind('<Enter>', lambda _e: _on_tg_btn_hover(True))
            w.bind('<Leave>', lambda _e: _on_tg_btn_hover(False))

        for w in (banner_fr, banner_in, lbl_tg_icon, tg_center, tg_row_top, lbl_tg_badge, lbl_tg_title, lbl_tg_msg):
            w.bind('<Button-1>', _open_telegram)

        # Section 1: Downloads & Storage
        c1, in1 = self.card(inner)
        c1.pack(fill='x', padx=28, pady=(0, 14))
        self.eyebrow(in1, 'Downloads & Storage').pack(anchor='w', pady=(0, 12))

        r1 = tk.Frame(in1, bg=CARD_BG)
        r1.pack(fill='x', pady=8)
        tk.Label(r1, text='Download Location', bg=CARD_BG, fg=INK,
                 font=self.font_sans(11)).pack(side='left')
        self.folder_input_settings = GeistFolderInput(
            r1,
            app=self,
            textvariable=self.save_dir,
            on_browse=self._pick_folder,
            on_open=self._open_save_folder,
            placeholder='Choose download folder…',
        )
        self.folder_input_settings.pack(side='right', fill='x', expand=True, padx=(24, 0))

        tk.Frame(in1, bg=HAIRLINE, height=1).pack(fill='x', pady=10)

        r2 = tk.Frame(in1, bg=CARD_BG)
        r2.pack(fill='x', pady=8)
        tk.Label(r2, text='Preferred Video Resolution', bg=CARD_BG, fg=INK,
                 font=self.font_sans(11)).pack(side='left')
        self.cb_res = GeistSelect(
            r2,
            app=self,
            textvariable=self.quality,
            values=list(QUALITY_CHOICES),
            size='default',
            width=12,
            on_change=lambda val: set_resolution_pref(val)
        )
        self.cb_res.pack(side='right')

        tk.Frame(in1, bg=HAIRLINE, height=1).pack(fill='x', pady=10)

        r3 = tk.Frame(in1, bg=CARD_BG)
        r3.pack(fill='x', pady=8)
        tk.Label(r3, text='Max Concurrent Downloads', bg=CARD_BG, fg=INK,
                 font=self.font_sans(11)).pack(side='left')
        self.var_concurrency = tk.StringVar(value=str(config.get_download_concurrency()))
        self.sp_con = GeistSelect(
            r3,
            app=self,
            textvariable=self.var_concurrency,
            values=['1', '2', '3', '4', '6', '8'],
            size='default',
            width=8,
            on_change=lambda val: config.set_download_concurrency(int(val))
        )
        self.sp_con.pack(side='right')

        tk.Frame(in1, bg=HAIRLINE, height=1).pack(fill='x', pady=10)

        r_resume = tk.Frame(in1, bg=CARD_BG)
        r_resume.pack(fill='x', pady=8)
        lbl_box = tk.Frame(r_resume, bg=CARD_BG)
        lbl_box.pack(side='left', fill='x', expand=True)
        tk.Label(lbl_box, text='Auto-Resume Incomplete Downloads', bg=CARD_BG, fg=INK,
                 font=self.font_sans(11)).pack(anchor='w')
        tk.Label(lbl_box, text='Automatically resume unfinished downloads on startup',
                 bg=CARD_BG, fg=MUTE, font=self.font_sans(9)).pack(anchor='w', pady=(2, 0))

        self.var_auto_resume = tk.BooleanVar(value=config.get_auto_resume_downloads())
        MacToggleSwitch(r_resume, variable=self.var_auto_resume,
                        command=lambda: config.set_auto_resume_downloads(self.var_auto_resume.get())
                       ).pack(side='right')

        # Section 2: Content Sources & Providers
        c_src, in_src = self.card(inner)
        c_src.pack(fill='x', padx=28, pady=(0, 14))
        self.eyebrow(in_src, 'Content Sources & Providers').pack(anchor='w', pady=(0, 4))
        tk.Label(in_src,
                 text='Enable or disable specific video providers. Only active sources will show results in browse feeds and search.',
                 bg=CARD_BG, fg=MUTE, font=self.font_sans(9)).pack(anchor='w', pady=(0, 12))

        self._source_vars = {}
        for idx, (s_key, s_label, s_desc) in enumerate(config.AVAILABLE_SOURCES):
            if idx > 0:
                tk.Frame(in_src, bg=HAIRLINE, height=1).pack(fill='x', pady=8)

            row_s = tk.Frame(in_src, bg=CARD_BG)
            row_s.pack(fill='x', pady=6)

            txt_box = tk.Frame(row_s, bg=CARD_BG)
            txt_box.pack(side='left', fill='x', expand=True)

            tk.Label(txt_box, text=s_label, bg=CARD_BG, fg=INK,
                     font=self.font_sans(11, bold=True)).pack(anchor='w')
            tk.Label(txt_box, text=s_desc, bg=CARD_BG, fg=BODY,
                     font=self.font_sans(9)).pack(anchor='w', pady=(2, 0))

            s_var = tk.BooleanVar(value=config.is_source_enabled(s_key))
            self._source_vars[s_key] = s_var

            def _make_cmd(k, v):
                def _cmd():
                    config.set_source_enabled(k, v.get())
                    self._on_sources_changed()
                return _cmd

            MacToggleSwitch(row_s, variable=s_var, command=_make_cmd(s_key, s_var)).pack(side='right')

        # Section 3: Media Playback & Player
        c2, in2 = self.card(inner)
        c2.pack(fill='x', padx=28, pady=(0, 14))
        self.eyebrow(in2, 'Media Playback & Player').pack(anchor='w', pady=(0, 12))

        r4 = tk.Frame(in2, bg=CARD_BG)
        r4.pack(fill='x', pady=8)
        tk.Label(r4, text='Auto-Play when opening Watch preview', bg=CARD_BG, fg=INK,
                 font=self.font_sans(11)).pack(side='left')
        self.var_autoplay = tk.BooleanVar(value=True)
        MacToggleSwitch(r4, variable=self.var_autoplay).pack(side='right')

        tk.Frame(in2, bg=HAIRLINE, height=1).pack(fill='x', pady=10)

        r5 = tk.Frame(in2, bg=CARD_BG)
        r5.pack(fill='x', pady=8)
        tk.Label(r5, text='Hardware Video Decoding (GPU acceleration)', bg=CARD_BG, fg=INK,
                 font=self.font_sans(11)).pack(side='left')
        self.var_hw_accel = tk.BooleanVar(value=True)
        MacToggleSwitch(r5, variable=self.var_hw_accel).pack(side='right')

        # Section 4: Appearance
        c_appearance, in_appearance = self.card(inner)
        c_appearance.pack(fill='x', padx=28, pady=(0, 14))
        self.eyebrow(in_appearance, 'Appearance').pack(anchor='w', pady=(0, 4))
        tk.Label(in_appearance,
                 text='Switch between dark and light themes, or follow your system setting.',
                 bg=CARD_BG, fg=MUTE, font=self.font_sans(9)).pack(anchor='w', pady=(0, 12))

        r_theme = tk.Frame(in_appearance, bg=CARD_BG)
        r_theme.pack(fill='x', pady=8)
        tk.Label(r_theme, text='Theme', bg=CARD_BG, fg=INK,
                 font=self.font_sans(11)).pack(side='left')

        self._theme_var = tk.StringVar(value=config.get_theme())
        self._theme_seg = GeistSegmentedSwitch(
            r_theme, self,
            segments=[('system', 'System'), ('dark', 'Dark'), ('light', 'Light')],
            default=config.get_theme(),
            on_change=self._on_theme_changed,
        )
        self._theme_seg.pack(side='right')

        # Section 5: Software Updates
        c_up, in_up = self.card(inner)
        c_up.pack(fill='x', padx=28, pady=(0, 14))
        self.eyebrow(in_up, 'Software Updates').pack(anchor='w', pady=(0, 4))
        tk.Label(in_up,
                 text='Automatically check and install new FetchX updates directly from GitHub Releases.',
                 bg=CARD_BG, fg=MUTE, font=self.font_sans(9)).pack(anchor='w', pady=(0, 12))

        r_up = tk.Frame(in_up, bg=CARD_BG)
        r_up.pack(fill='x', pady=6)

        up_info = tk.Frame(r_up, bg=CARD_BG)
        up_info.pack(side='left', fill='x', expand=True)
        tk.Label(up_info, text=f'Current Version: FetchX v{APP_VERSION}', bg=CARD_BG, fg=INK,
                 font=self.font_sans(11, bold=True)).pack(anchor='w')
        self.lbl_update_status = tk.Label(up_info, text='Status: Ready to check for updates',
                                          bg=CARD_BG, fg=MUTE, font=self.font_sans(9))
        self.lbl_update_status.pack(anchor='w', pady=(2, 0))

        # Check for updates button
        btn_check_up = tk.Frame(r_up, bg=PILL_PRI_BG, highlightthickness=1,
                                highlightbackground=PILL_PRI_BORDER, cursor='hand2', padx=14, pady=7)
        btn_check_up.pack(side='right')

        up_ico_img = get_heroicon('refresh', size=16, color=PILL_PRI_FG)
        lbl_check_ico = tk.Label(btn_check_up, image=up_ico_img, bg=PILL_PRI_BG, bd=0, cursor='hand2')
        lbl_check_ico.image = up_ico_img
        lbl_check_ico.pack(side='left', padx=(0, 6))

        self.lbl_check_txt = tk.Label(btn_check_up, text='Check for Updates', bg=PILL_PRI_BG, fg=PILL_PRI_FG,
                                      font=self.font_sans(11, bold=True), cursor='hand2')
        self.lbl_check_txt.pack(side='left')

        def _on_check_enter(_e=None):
            if getattr(self, '_checking_updates', False):
                return
            btn_check_up.configure(bg=PILL_PRI_HOVER_BG, highlightbackground=PILL_PRI_HOVER_BD)
            lbl_check_ico.configure(bg=PILL_PRI_HOVER_BG, image=get_heroicon('refresh', size=16, color=PILL_PRI_HOVER_FG))
            self.lbl_check_txt.configure(bg=PILL_PRI_HOVER_BG, fg=PILL_PRI_HOVER_FG)

        def _on_check_leave(_e=None):
            btn_check_up.configure(bg=PILL_PRI_BG, highlightbackground=PILL_PRI_BORDER)
            lbl_check_ico.configure(bg=PILL_PRI_BG, image=get_heroicon('refresh', size=16, color=PILL_PRI_FG))
            self.lbl_check_txt.configure(bg=PILL_PRI_BG, fg=PILL_PRI_FG)

        def _on_check_click(_e=None):
            self._check_for_updates_ui(user_triggered=True)

        for w in (btn_check_up, lbl_check_ico, self.lbl_check_txt):
            w.bind('<Enter>', _on_check_enter)
            w.bind('<Leave>', _on_check_leave)
            w.bind('<Button-1>', _on_check_click)

        tk.Frame(in_up, bg=HAIRLINE, height=1).pack(fill='x', pady=10)

        r_auto_up = tk.Frame(in_up, bg=CARD_BG)
        r_auto_up.pack(fill='x', pady=8)
        lbl_auto_box = tk.Frame(r_auto_up, bg=CARD_BG)
        lbl_auto_box.pack(side='left', fill='x', expand=True)
        tk.Label(lbl_auto_box, text='Automatic Update Checks', bg=CARD_BG, fg=INK,
                 font=self.font_sans(11)).pack(anchor='w')
        tk.Label(lbl_auto_box, text='Silently check GitHub Releases when FetchX starts',
                 bg=CARD_BG, fg=MUTE, font=self.font_sans(9)).pack(anchor='w', pady=(2, 0))

        self.var_auto_update = tk.BooleanVar(value=config.get_auto_check_updates())
        MacToggleSwitch(r_auto_up, variable=self.var_auto_update,
                        command=lambda: config.set_auto_check_updates(self.var_auto_update.get())
                       ).pack(side='right')

        # Section 6: Dynamic Remote Announcements & Information
        c_ann, in_ann = self.card(inner)
        c_ann.pack(fill='x', padx=28, pady=(0, 14))
        self.eyebrow(in_ann, 'Remote Announcements & Broadcasts').pack(anchor='w', pady=(0, 4))
        tk.Label(in_ann,
                 text='Dynamically receive announcements, community updates, alerts, and notifications directly on the home page.',
                 bg=CARD_BG, fg=MUTE, font=self.font_sans(9)).pack(anchor='w', pady=(0, 12))

        r_ann_toggle = tk.Frame(in_ann, bg=CARD_BG)
        r_ann_toggle.pack(fill='x', pady=8)
        lbl_ann_box = tk.Frame(r_ann_toggle, bg=CARD_BG)
        lbl_ann_box.pack(side='left', fill='x', expand=True)
        tk.Label(lbl_ann_box, text='Enable Dynamic Announcements', bg=CARD_BG, fg=INK,
                 font=self.font_sans(11)).pack(anchor='w')
        tk.Label(lbl_ann_box, text='Show banners, notices, and sponsored updates on the Browse page',
                 bg=CARD_BG, fg=MUTE, font=self.font_sans(9)).pack(anchor='w', pady=(2, 0))

        self.var_ann_enabled = tk.BooleanVar(value=config.get_announcements_enabled())
        MacToggleSwitch(r_ann_toggle, variable=self.var_ann_enabled,
                        command=lambda: config.set_announcements_enabled(self.var_ann_enabled.get())
                       ).pack(side='right')

        tk.Frame(in_ann, bg=HAIRLINE, height=1).pack(fill='x', pady=10)

        r_ann_url = tk.Frame(in_ann, bg=CARD_BG)
        r_ann_url.pack(fill='x', pady=8)
        tk.Label(r_ann_url, text='Manifest Endpoint URL', bg=CARD_BG, fg=INK,
                 font=self.font_sans(11)).pack(anchor='w')

        url_input_fr = tk.Frame(in_ann, bg=CARD_BG)
        url_input_fr.pack(fill='x', pady=(4, 8))

        self.ent_ann_url = tk.Entry(url_input_fr, bg=HAIRLINE_SOFT, fg=INK,
                                    font=self.font_mono(10), bd=1, relief='solid',
                                    highlightthickness=1, highlightbackground=HAIRLINE)
        self.ent_ann_url.insert(0, config.get_remote_announcements_url())
        self.ent_ann_url.pack(side='left', fill='x', expand=True, ipady=4, padx=(0, 8))

        btn_save_url = tk.Frame(url_input_fr, bg=PILL_PRI_BG, highlightthickness=1,
                                highlightbackground=PILL_PRI_BORDER, cursor='hand2')
        btn_save_url.pack(side='left', padx=(0, 6))
        lbl_save_url = tk.Label(btn_save_url, text='Save URL', bg=PILL_PRI_BG, fg=PILL_PRI_FG,
                                font=self.font_sans(9, bold=True), cursor='hand2', padx=10, pady=3)
        lbl_save_url.pack()

        def _on_save_ann_url(_e=None):
            new_u = self.ent_ann_url.get().strip()
            config.set_remote_announcements_url(new_u)
            self.show_toast('Announcements URL saved', icon='check', color='#4ade80')
            self._fetch_remote_announcements(user_triggered=True)

        for w in (btn_save_url, lbl_save_url):
            w.bind('<Button-1>', _on_save_ann_url)

        btn_reset_dismiss = tk.Frame(url_input_fr, bg=PILL_SEC_BG, highlightthickness=1,
                                     highlightbackground=PILL_SEC_BORDER, cursor='hand2')
        btn_reset_dismiss.pack(side='left')
        lbl_reset_dismiss = tk.Label(btn_reset_dismiss, text='Reset Dismissed', bg=PILL_SEC_BG, fg=PILL_SEC_FG,
                                     font=self.font_sans(9, bold=True), cursor='hand2', padx=10, pady=3)
        lbl_reset_dismiss.pack()

        def _on_reset_dismiss(_e=None):
            config.reset_dismissed_announcements()
            self.show_toast('Reset dismissed notices', icon='refresh', color=LINK)
            self._fetch_remote_announcements(user_triggered=True)

        for w in (btn_reset_dismiss, lbl_reset_dismiss):
            w.bind('<Button-1>', _on_reset_dismiss)

        # Section 7: About FetchX & FetchJAV Project
        c3, in3 = self.card(inner)
        c3.pack(fill='x', padx=28, pady=(0, 24))
        self.eyebrow(in3, 'About FetchX & FetchJAV Ecosystem').pack(anchor='w', pady=(0, 12))

        # Brand header: FetchX Wordmark + "Part of FetchJAV Project" Badge
        top_brand_row = tk.Frame(in3, bg=CARD_BG)
        top_brand_row.pack(fill='x', anchor='w')

        about_logo = get_fetchx_wordmark(font_size=24, suffix='Desktop 2.5')
        lbl_about_title = tk.Label(top_brand_row, image=about_logo, bg=CARD_BG, bd=0, highlightthickness=0)
        lbl_about_title.image = about_logo
        lbl_about_title.pack(side='left', anchor='w')

        badge_jav = tk.Label(top_brand_row, text=' PART OF FETCHJAV PROJECT ', bg=ELEVATED, fg=LINK,
                             font=self.font_mono(8, bold=True),
                             highlightthickness=1, highlightbackground=LINK,
                             padx=7, pady=2)
        badge_jav.pack(side='left', padx=(12, 0))

        tk.Label(in3,
                 text='Native high-performance desktop media browser and HLS client developed as part of the FetchJAV Project.\n'
                      'Backed by the proven FetchJAV core engine for instant stream resolution, multi-threaded segment downloading,\n'
                      'AES-128 decryption, and integrated VLC theater playback.\n\n'
                      'Supported Sources: FreePornVideos, OnePorn, Beeg, and the extended FetchJAV crawler ecosystem.',
                 bg=CARD_BG, fg=BODY, font=self.font_sans(11), justify='left').pack(
                     anchor='w', pady=(10, 0))

        # FetchJAV Project Information Box / Callout
        jav_box = tk.Frame(in3, bg=HAIRLINE_SOFT, highlightthickness=1, highlightbackground=HAIRLINE)
        jav_box.pack(fill='x', pady=(16, 4))

        jav_inner = tk.Frame(jav_box, bg=HAIRLINE_SOFT, padx=14, pady=12)
        jav_inner.pack(fill='x')

        jav_head = tk.Frame(jav_inner, bg=HAIRLINE_SOFT)
        jav_head.pack(fill='x', anchor='w')

        ico_jav = get_heroicon('sparkles', size=16, color=LINK)
        lbl_jav_ico = tk.Label(jav_head, image=ico_jav, bg=HAIRLINE_SOFT, bd=0)
        lbl_jav_ico.image = ico_jav
        lbl_jav_ico.pack(side='left', padx=(0, 6))

        tk.Label(jav_head, text='About the FetchJAV Project', bg=HAIRLINE_SOFT, fg=INK,
                 font=self.font_sans(11, bold=True)).pack(side='left')

        lbl_jav_desc = tk.Label(jav_inner,
                                text='FetchJAV is an open-source media scraping, stream resolution, and HLS downloading platform engineered for '
                                     'high-performance video extraction, resilient CDN mirror failover, multi-connection segment assembly, and stream processing. '
                                     'It provides the core architecture powering FetchX desktop, web client, and extraction tools across multiple supported sites.',
                                bg=HAIRLINE_SOFT, fg=BODY, font=self.font_sans(9), justify='left', wraplength=620)
        lbl_jav_desc.pack(anchor='w', pady=(6, 0))
        jav_box.bind('<Configure>', lambda e, l=lbl_jav_desc: l.configure(wraplength=max(200, e.width - 32)))

        # Action 1: FetchJAV Project Repository Link
        tk.Frame(in3, bg=HAIRLINE, height=1).pack(fill='x', pady=(14, 12))

        jav_gh_row = tk.Frame(in3, bg=CARD_BG)
        jav_gh_row.pack(fill='x')

        jav_gh_info = tk.Frame(jav_gh_row, bg=CARD_BG)
        jav_gh_info.pack(side='left', fill='x', expand=True)
        tk.Label(jav_gh_info, text='FetchJAV Core Project', bg=CARD_BG, fg=INK,
                 font=self.font_sans(11, bold=True)).pack(anchor='w')
        tk.Label(jav_gh_info, text='Explore the upstream FetchJAV engine, public releases, and extractor repositories.',
                 bg=CARD_BG, fg=MUTE, font=self.font_sans(9)).pack(anchor='w', pady=(2, 0))

        btn_jav_gh = tk.Frame(jav_gh_row, bg=ELEVATED, highlightthickness=1,
                              highlightbackground=HAIRLINE, cursor='hand2', padx=14, pady=7)
        btn_jav_gh.pack(side='right')

        jav_ico_img = get_heroicon('github', size=18, color=INK)
        lbl_jav_gh_ico = tk.Label(btn_jav_gh, image=jav_ico_img, bg=ELEVATED, bd=0, cursor='hand2')
        lbl_jav_gh_ico.image = jav_ico_img
        lbl_jav_gh_ico.pack(side='left', padx=(0, 8))

        lbl_jav_gh_txt = tk.Label(btn_jav_gh, text='FetchJAV Hub', bg=ELEVATED, fg=INK,
                                  font=self.font_sans(11, bold=True), cursor='hand2')
        lbl_jav_gh_txt.pack(side='left')

        ext_jav_img = get_heroicon('arrow_top_right_on_square', size=14, color=MUTE)
        lbl_jav_gh_ext = tk.Label(btn_jav_gh, image=ext_jav_img, bg=ELEVATED, bd=0, cursor='hand2')
        lbl_jav_gh_ext.image = ext_jav_img
        lbl_jav_gh_ext.pack(side='left', padx=(6, 0))

        def _open_fetchjav_github(_e=None):
            url = 'https://github.com/FetchJAV/FetchJAV_Public'
            try:
                webbrowser.open_new_tab(url)
                self.show_toast('Opening FetchJAV Project Repository…', icon='sparkles', color='#38bdf8')
            except Exception:
                pass

        def _on_jav_gh_enter(_e=None):
            btn_jav_gh.configure(bg=CARD_HOVER, highlightbackground='#52526b')
            lbl_jav_gh_ico.configure(bg=CARD_HOVER)
            lbl_jav_gh_txt.configure(bg=CARD_HOVER, fg='#ffffff')
            lbl_jav_gh_ext.configure(bg=CARD_HOVER)

        def _on_jav_gh_leave(_e=None):
            btn_jav_gh.configure(bg=ELEVATED, highlightbackground=HAIRLINE)
            lbl_jav_gh_ico.configure(bg=ELEVATED)
            lbl_jav_gh_txt.configure(bg=ELEVATED, fg=INK)
            lbl_jav_gh_ext.configure(bg=ELEVATED)

        for w in (btn_jav_gh, lbl_jav_gh_ico, lbl_jav_gh_txt, lbl_jav_gh_ext):
            w.bind('<Button-1>', _open_fetchjav_github)
            w.bind('<Enter>', _on_jav_gh_enter)
            w.bind('<Leave>', _on_jav_gh_leave)

        # Action 2: FetchX Desktop GitHub Repository Link
        tk.Frame(in3, bg=HAIRLINE, height=1).pack(fill='x', pady=(12, 12))

        gh_row = tk.Frame(in3, bg=CARD_BG)
        gh_row.pack(fill='x')

        gh_info = tk.Frame(gh_row, bg=CARD_BG)
        gh_info.pack(side='left', fill='x', expand=True)
        tk.Label(gh_info, text='FetchX Desktop Repository', bg=CARD_BG, fg=INK,
                 font=self.font_sans(11, bold=True)).pack(anchor='w')
        tk.Label(gh_info, text='Star FetchX, report issues, and view desktop release notes on GitHub.',
                 bg=CARD_BG, fg=MUTE, font=self.font_sans(9)).pack(anchor='w', pady=(2, 0))

        btn_gh = tk.Frame(gh_row, bg=ELEVATED, highlightthickness=1,
                          highlightbackground=HAIRLINE, cursor='hand2', padx=14, pady=7)
        btn_gh.pack(side='right')

        gh_ico_img = get_heroicon('github', size=18, color=INK)
        lbl_gh_ico = tk.Label(btn_gh, image=gh_ico_img, bg=ELEVATED, bd=0, cursor='hand2')
        lbl_gh_ico.image = gh_ico_img
        lbl_gh_ico.pack(side='left', padx=(0, 8))

        lbl_gh_txt = tk.Label(btn_gh, text='FetchX GitHub', bg=ELEVATED, fg=INK,
                              font=self.font_sans(11, bold=True), cursor='hand2')
        lbl_gh_txt.pack(side='left')

        ext_ico_img = get_heroicon('arrow_top_right_on_square', size=14, color=MUTE)
        lbl_gh_ext = tk.Label(btn_gh, image=ext_ico_img, bg=ELEVATED, bd=0, cursor='hand2')
        lbl_gh_ext.image = ext_ico_img
        lbl_gh_ext.pack(side='left', padx=(6, 0))

        def _open_github(_e=None):
            url = 'https://github.com/DeepanshuK2002/FetchX'
            try:
                webbrowser.open_new_tab(url)
                self.show_toast('Opening FetchX GitHub Repository…', icon='sparkles', color='#a855f7')
            except Exception:
                pass

        def _on_gh_enter(_e=None):
            btn_gh.configure(bg=CARD_HOVER, highlightbackground='#52526b')
            lbl_gh_ico.configure(bg=CARD_HOVER)
            lbl_gh_txt.configure(bg=CARD_HOVER, fg='#ffffff')
            lbl_gh_ext.configure(bg=CARD_HOVER)

        def _on_gh_leave(_e=None):
            btn_gh.configure(bg=ELEVATED, highlightbackground=HAIRLINE)
            lbl_gh_ico.configure(bg=ELEVATED)
            lbl_gh_txt.configure(bg=ELEVATED, fg=INK)
            lbl_gh_ext.configure(bg=ELEVATED)

        for w in (btn_gh, lbl_gh_ico, lbl_gh_txt, lbl_gh_ext):
            w.bind('<Button-1>', _open_github)
            w.bind('<Enter>', _on_gh_enter)
            w.bind('<Leave>', _on_gh_leave)

        # Action 3: Share FetchX Action Link
        tk.Frame(in3, bg=HAIRLINE, height=1).pack(fill='x', pady=(12, 12))

        share_row = tk.Frame(in3, bg=CARD_BG)
        share_row.pack(fill='x')

        share_info = tk.Frame(share_row, bg=CARD_BG)
        share_info.pack(side='left', fill='x', expand=True)
        tk.Label(share_info, text='Share Application', bg=CARD_BG, fg=INK,
                 font=self.font_sans(11, bold=True)).pack(anchor='w')
        tk.Label(share_info, text='Share FetchX download link and details with friends and community.',
                 bg=CARD_BG, fg=MUTE, font=self.font_sans(9)).pack(anchor='w', pady=(2, 0))

        # Share Pill Button (Liquid Sapphire Glass Pill with Share Icon)
        btn_share = tk.Frame(share_row, bg=PILL_PRI_BG, highlightthickness=1,
                             highlightbackground=PILL_PRI_BORDER, cursor='hand2', padx=14, pady=7)
        btn_share.pack(side='right')

        share_ico_img = get_heroicon('share', size=18, color=PILL_PRI_FG)
        lbl_share_ico = tk.Label(btn_share, image=share_ico_img, bg=PILL_PRI_BG, bd=0, cursor='hand2')
        lbl_share_ico.image = share_ico_img
        lbl_share_ico.pack(side='left', padx=(0, 8))

        lbl_share_txt = tk.Label(btn_share, text='Share App', bg=PILL_PRI_BG, fg=PILL_PRI_FG,
                                 font=self.font_sans(11, bold=True), cursor='hand2')
        lbl_share_txt.pack(side='left')

        def _share_app(_e=None):
            share_url = 'https://github.com/DeepanshuK2002/FetchX'
            share_text = f'Check out FetchX (FetchJAV Project) — High-performance video downloader & VLC player: {share_url}'
            try:
                self.clipboard_clear()
                self.clipboard_append(share_text)
            except Exception:
                pass
            self.show_toast('Share link copied to clipboard!', icon='share', color=LINK)
            try:
                analytics.track('share_app')
            except Exception:
                pass

        def _on_share_enter(_e=None):
            btn_share.configure(bg=PILL_PRI_HOVER_BG, highlightbackground=PILL_PRI_HOVER_BD)
            lbl_share_ico.configure(bg=PILL_PRI_HOVER_BG, image=get_heroicon('share', size=18, color=PILL_PRI_HOVER_FG))
            lbl_share_txt.configure(bg=PILL_PRI_HOVER_BG, fg=PILL_PRI_HOVER_FG)

        def _on_share_leave(_e=None):
            btn_share.configure(bg=PILL_PRI_BG, highlightbackground=PILL_PRI_BORDER)
            lbl_share_ico.configure(bg=PILL_PRI_BG, image=get_heroicon('share', size=18, color=PILL_PRI_FG))
            lbl_share_txt.configure(bg=PILL_PRI_BG, fg=PILL_PRI_FG)

        for w in (btn_share, lbl_share_ico, lbl_share_txt):
            w.bind('<Button-1>', _share_app)
            w.bind('<Enter>', _on_share_enter)
            w.bind('<Leave>', _on_share_leave)

    def _on_theme_changed(self, new_theme):
        config.set_theme(new_theme)
        self.after(100, lambda: os.execl(sys.executable, sys.executable, *sys.argv))

    # ---------- History View ----------
    def _build_history_view(self):
        page = self.view_history
        page.grid_rowconfigure(0, weight=1)
        page.grid_columnconfigure(0, weight=1)

        h_card, h_inner = self.card(page)
        h_card.grid(row=0, column=0, sticky='nsew', padx=(24, 0), pady=(16, 16))

        head = tk.Frame(h_inner, bg=CARD_BG)
        head.pack(fill='x')

        # Geist Segmented Switch (Downloads vs Watched)
        self.hist_switch = GeistSegmentedSwitch(
            head, self,
            segments=[('downloads', 'Downloads'), ('watched', 'Watched')],
            default='downloads',
            on_change=self._on_hist_mode
        )
        self.hist_switch.pack(side='left', padx=(0, 10))

        # Open folder (Liquid Glass Pill)
        self.btn_hist_open_folder = tk.Frame(head, bg=PILL_SEC_BG, highlightthickness=1,
                                             highlightbackground=PILL_SEC_BORDER, cursor='hand2')
        self.btn_hist_open_folder.pack(side='right')
        self.lbl_hist_open = tk.Label(self.btn_hist_open_folder, text='Open folder', bg=PILL_SEC_BG,
                                      fg=PILL_SEC_FG, font=self.font_sans(9, bold=True),
                                      cursor='hand2', padx=10, pady=3)
        self.lbl_hist_open.pack()

        def _on_hist_open_hover(enter):
            bg = PILL_SEC_HOVER_BG if enter else PILL_SEC_BG
            bd = PILL_SEC_HOVER_BD if enter else PILL_SEC_BORDER
            fg = PILL_SEC_HOVER_FG if enter else PILL_SEC_FG
            self.btn_hist_open_folder.configure(bg=bg, highlightbackground=bd)
            self.lbl_hist_open.configure(bg=bg, fg=fg)

        for w in (self.btn_hist_open_folder, self.lbl_hist_open):
            w.bind('<Button-1>', lambda _e: self._open_save_folder())
            w.bind('<Enter>', lambda _e: _on_hist_open_hover(True))
            w.bind('<Leave>', lambda _e: _on_hist_open_hover(False))

        # Clear history (Liquid Smoked Quartz Pill with Crimson Hover)
        self.btn_hist_clear = tk.Frame(head, bg=PILL_SEC_BG, highlightthickness=1,
                                       highlightbackground=PILL_SEC_BORDER, cursor='hand2')
        self.btn_hist_clear.pack(side='right', padx=(0, 8))
        self.lbl_hist_clear = tk.Label(self.btn_hist_clear, text='Clear history', bg=PILL_SEC_BG,
                                       fg=PILL_SEC_FG, font=self.font_sans(9, bold=True),
                                       cursor='hand2', padx=10, pady=3)
        self.lbl_hist_clear.pack()

        def _on_hist_clear_hover(enter):
            bg = PILL_SEC_HOVER_BG if enter else PILL_SEC_BG
            bd = ERROR if enter else PILL_SEC_BORDER
            fg = ERROR if enter else PILL_SEC_FG
            self.btn_hist_clear.configure(bg=bg, highlightbackground=bd)
            self.lbl_hist_clear.configure(bg=bg, fg=fg)

        for w in (self.btn_hist_clear, self.lbl_hist_clear):
            w.bind('<Button-1>', lambda _e: self._clear_history())
            w.bind('<Enter>', lambda _e: _on_hist_clear_hover(True))
            w.bind('<Leave>', lambda _e: _on_hist_clear_hover(False))

        self._hist_mode = 'downloads'

        outer = tk.Frame(h_inner, bg=CARD_BG)
        outer.pack(fill='both', expand=True, pady=(14, 0))

        self.history_canvas = tk.Canvas(outer, bg=CARD_BG, bd=0, highlightthickness=0)
        self.history_vsb = ttk.Scrollbar(page, orient='vertical', command=self.history_canvas.yview)
        self.history_vsb.grid(row=0, column=1, sticky='ns', padx=(8, 3))
        self.history_canvas.configure(yscrollcommand=self.history_vsb.set)
        self.history_canvas.pack(side='left', fill='both', expand=True)

        self.history_inner = tk.Frame(self.history_canvas, bg=CARD_BG)
        self.history_canvas.create_window((0, 0), window=self.history_inner, anchor='nw', tags='hinner')
        self.history_inner.bind(
            '<Configure>',
            lambda _e: self.history_canvas.configure(scrollregion=self.history_canvas.bbox('all')))
        self.history_canvas.bind(
            '<Configure>',
            lambda e: self.history_canvas.itemconfigure('hinner', width=e.width))
        self._mousewheel_bind(self.history_canvas, self._on_history_wheel)

        self.lbl_history_empty = tk.Label(
            self.history_inner, text='No downloads yet \u2014 finished videos land here.',
            bg=CARD_BG, fg=FAINT, pady=42, font=self.font_sans(11))
        self.lbl_history_empty.pack(fill='x')

    def _on_history_wheel(self, event):
        self.history_canvas.yview_scroll(int(-event.delta / 120), 'units')

    def _on_hist_mode(self, mode):
        self._hist_mode = mode
        if hasattr(self, 'hist_switch') and self.hist_switch.active_val != mode:
            self.hist_switch.set_value(mode)
        self._render_history()

    def _render_history(self):
        for w in self.history_inner.winfo_children():
            if w is not self.lbl_history_empty:
                w.destroy()
        if self._hist_mode == 'watched':
            entries = config.get_view_history()
            empty = 'Nothing watched yet \u2014 videos you play land here.'
            row_fn = self._watch_row
            self.btn_hist_open_folder.pack_forget()
        else:
            entries = config.get_download_history()
            empty = 'No downloads yet \u2014 finished videos land here.'
            row_fn = self._history_row
            if not self.btn_hist_open_folder.winfo_ismapped():
                self.btn_hist_open_folder.pack(side='right', before=self.btn_hist_clear)
                self.btn_hist_clear.pack_configure(padx=(0, 8))
        self.lbl_history_empty.pack(fill='x')
        if not entries:
            self.lbl_history_empty.configure(text=empty)
            return
        self.lbl_history_empty.pack_forget()
        for entry in entries:
            row_fn(entry)

    def _fmt_history_meta(self, entry):
        parts = []
        site = str(entry.get('site') or '').strip()
        if site:
            parts.append(site.upper())
        size = int(entry.get('size') or 0)
        if size > 0:
            parts.append(fmt_bytes(size))
        when = str(entry.get('finished_at') or '').strip()
        if when:
            parts.append(when)
        return '  \u00b7  '.join(parts)

    def _history_row(self, entry):
        frame = tk.Frame(self.history_inner, bg=CARD_BG,
                         highlightthickness=1, highlightbackground=CARD_BORDER)
        frame.pack(fill='x', padx=4, pady=5)
        inner = tk.Frame(frame, bg=CARD_BG)
        inner.pack(fill='both', expand=True, padx=16, pady=12)

        top = tk.Frame(inner, bg=CARD_BG)
        top.pack(fill='x')
        title = str(entry.get('title') or entry.get('url') or '')
        tk.Label(top, text=title[:90], bg=CARD_BG, fg=INK, anchor='w',
                 font=self.font_sans(11, bold=True)).pack(
                     side='left', fill='x', expand=True)
        meta = self._fmt_history_meta(entry)
        if meta:
            tk.Label(top, text=meta, bg=CARD_BG, fg=MUTE,
                     font=self.font_mono(10)).pack(side='left', padx=(10, 0))

        bot = tk.Frame(inner, bg=CARD_BG)
        bot.pack(fill='x', pady=(8, 0))
        path = str(entry.get('path') or '')
        url = str(entry.get('url') or '')
        lbl_path = tk.Label(bot, text=path[:120], bg=CARD_BG, fg=MUTE,
                            anchor='w', font=self.font_mono(10))
        lbl_path.pack(side='left', fill='x', expand=True)
        lbl_path.bind(
            '<Configure>',
            lambda e: lbl_path.configure(wraplength=max(80, e.width - 4)))

        # Play button (Liquid Sapphire Pill)
        btn_play = tk.Frame(bot, bg=PILL_PRI_BG, highlightthickness=1,
                            highlightbackground=PILL_PRI_BORDER, cursor='hand2')
        btn_play.pack(side='left')
        lbl_play = tk.Label(btn_play, text='▶ Play', bg=PILL_PRI_BG,
                            fg=PILL_PRI_FG, font=self.font_sans(8, bold=True),
                            cursor='hand2', padx=9, pady=2)
        lbl_play.pack()

        def _on_play_h(enter):
            bg=PILL_PRI_HOVER_BG if enter else PILL_PRI_BG
            bd = PILL_PRI_HOVER_BD if enter else PILL_PRI_BORDER
            fg = PILL_PRI_HOVER_FG if enter else PILL_PRI_FG
            btn_play.configure(bg=bg, highlightbackground=bd)
            lbl_play.configure(bg=bg, fg=fg)

        for w in (btn_play, lbl_play):
            w.bind('<Button-1>', lambda _e, p=path: self._play_history_file(p))
            w.bind('<Enter>', lambda _e: _on_play_h(True))
            w.bind('<Leave>', lambda _e: _on_play_h(False))

        # Show in folder button (Liquid Smoked Quartz Pill)
        btn_folder = tk.Frame(bot, bg=PILL_SEC_BG, highlightthickness=1,
                              highlightbackground=PILL_SEC_BORDER, cursor='hand2')
        btn_folder.pack(side='left', padx=(6, 0))
        lbl_folder = tk.Label(btn_folder, text='Show in folder', bg=PILL_SEC_BG,
                              fg=PILL_SEC_FG, font=self.font_sans(8, bold=True),
                              cursor='hand2', padx=8, pady=2)
        lbl_folder.pack()

        def _on_folder_h(enter):
            bg = PILL_SEC_HOVER_BG if enter else PILL_SEC_BG
            bd = PILL_SEC_HOVER_BD if enter else PILL_SEC_BORDER
            fg = PILL_SEC_HOVER_FG if enter else PILL_SEC_FG
            btn_folder.configure(bg=bg, highlightbackground=bd)
            lbl_folder.configure(bg=bg, fg=fg)

        for w in (btn_folder, lbl_folder):
            w.bind('<Button-1>', lambda _e, p=path: self._reveal_history_file(p))
            w.bind('<Enter>', lambda _e: _on_folder_h(True))
            w.bind('<Leave>', lambda _e: _on_folder_h(False))

        # Large Dustbin / Trash Icon
        trash_img = get_heroicon('trash', size=24, color=BODY)
        btn_trash = tk.Label(bot, image=trash_img, bg=CARD_BG, cursor='hand2', padx=6, pady=2)
        btn_trash.image = trash_img
        btn_trash.pack(side='left', padx=(8, 0))
        btn_trash.bind('<Button-1>', lambda _e, u=url: self._remove_history_entry(u))
        btn_trash.bind('<Enter>', lambda _e: btn_trash.configure(image=get_heroicon('trash', size=24, color=ERROR)))
        btn_trash.bind('<Leave>', lambda _e: btn_trash.configure(image=get_heroicon('trash', size=24, color=BODY)))

    def _watch_row(self, entry):
        frame = tk.Frame(self.history_inner, bg=CARD_BG,
                         highlightthickness=1, highlightbackground=CARD_BORDER)
        frame.pack(fill='x', padx=4, pady=5)
        inner = tk.Frame(frame, bg=CARD_BG)
        inner.pack(fill='both', expand=True, padx=16, pady=12)

        top = tk.Frame(inner, bg=CARD_BG)
        top.pack(fill='x')
        title = str(entry.get('title') or entry.get('url') or '')
        tk.Label(top, text=title[:90], bg=CARD_BG, fg=INK, anchor='w',
                 font=self.font_sans(11, bold=True)).pack(
                     side='left', fill='x', expand=True)
        meta = self._fmt_watch_meta(entry)
        if meta:
            tk.Label(top, text=meta, bg=CARD_BG, fg=MUTE,
                     font=self.font_mono(10)).pack(side='left', padx=(10, 0))

        bot = tk.Frame(inner, bg=CARD_BG)
        bot.pack(fill='x', pady=(8, 0))
        url = str(entry.get('url') or '')
        lbl_url = tk.Label(bot, text=url[:120], bg=CARD_BG, fg=MUTE,
                            anchor='w', font=self.font_mono(10))
        lbl_url.pack(side='left', fill='x', expand=True)
        lbl_url.bind(
            '<Configure>',
            lambda e: lbl_url.configure(wraplength=max(80, e.width - 4)))
        item = {'url': url,
                'title': entry.get('title') or '',
                'thumbnail': entry.get('thumbnail') or '',
                'duration': entry.get('duration') or '',
                'site_name': entry.get('site_name') or ''}

        # Watch button (Liquid Sapphire Pill)
        btn_watch = tk.Frame(bot, bg=PILL_PRI_BG, highlightthickness=1,
                             highlightbackground=PILL_PRI_BORDER, cursor='hand2')
        btn_watch.pack(side='left')
        lbl_watch = tk.Label(btn_watch, text='▶ Watch', bg=PILL_PRI_BG,
                             fg=PILL_PRI_FG, font=self.font_sans(8, bold=True),
                             cursor='hand2', padx=9, pady=2)
        lbl_watch.pack()

        def _on_watch_h(enter):
            bg=PILL_PRI_HOVER_BG if enter else PILL_PRI_BG
            bd = PILL_PRI_HOVER_BD if enter else PILL_PRI_BORDER
            fg = PILL_PRI_HOVER_FG if enter else PILL_PRI_FG
            btn_watch.configure(bg=bg, highlightbackground=bd)
            lbl_watch.configure(bg=bg, fg=fg)

        for w in (btn_watch, lbl_watch):
            w.bind('<Button-1>', lambda _e, it=dict(item): self.watch_item(it))
            w.bind('<Enter>', lambda _e: _on_watch_h(True))
            w.bind('<Leave>', lambda _e: _on_watch_h(False))

        # Large Dustbin / Trash Icon
        trash_img = get_heroicon('trash', size=24, color=BODY)
        btn_trash = tk.Label(bot, image=trash_img, bg=CARD_BG, cursor='hand2', padx=6, pady=2)
        btn_trash.image = trash_img
        btn_trash.pack(side='left', padx=(8, 0))
        btn_trash.bind('<Button-1>', lambda _e, u=url: self._remove_history_entry(u))
        btn_trash.bind('<Enter>', lambda _e: btn_trash.configure(image=get_heroicon('trash', size=24, color=ERROR)))
        btn_trash.bind('<Leave>', lambda _e: btn_trash.configure(image=get_heroicon('trash', size=24, color=BODY)))

    def _fmt_watch_meta(self, entry):
        parts = []
        site = str(entry.get('site_name') or '').strip()
        if site:
            parts.append(site.upper())
        dur = str(entry.get('duration') or '').strip()
        if dur:
            parts.append(dur)
        try:
            ts = int(entry.get('timestamp') or 0)
            if ts > 0:
                parts.append(time.strftime('%Y-%m-%d %H:%M', time.localtime(ts)))
        except Exception:
            pass
        return '  \u00b7  '.join(parts)

    def _play_history_file(self, path):
        if path and os.path.isfile(path):
            try:
                os.startfile(path)
            except Exception as exc:
                messagebox.showerror(APP_TITLE, f'Could not open file: {exc}')
        else:
            messagebox.showwarning(APP_TITLE, 'File not found \u2014 it may have been moved or deleted.')

    def _reveal_history_file(self, path):
        if not path:
            return
        folder = os.path.dirname(os.path.abspath(path)) or os.path.abspath(self.save_dir.get() or '.')
        try:
            if os.path.isfile(path):
                subprocess.Popen(['explorer', '/select,', path])
            else:
                os.makedirs(folder, exist_ok=True)
                os.startfile(folder)
        except Exception:
            try:
                os.startfile(folder)
            except Exception as exc:
                messagebox.showerror(APP_TITLE, f'Could not open folder: {exc}')

    def _remove_history_entry(self, url):
        if self._hist_mode == 'watched':
            config.remove_view_history(url)
        else:
            config.remove_download_history(url)
        self._render_history()

    # ---------- Watch Later View ----------
    def _build_watch_later_view(self):
        page = self.view_watch_later
        page.grid_rowconfigure(0, weight=1)
        page.grid_columnconfigure(0, weight=1)

        wl_card, wl_inner = self.card(page)
        wl_card.grid(row=0, column=0, sticky='nsew', padx=(24, 0), pady=(16, 16))

        # Top bar with title, stats, and actions
        head = tk.Frame(wl_inner, bg=CARD_BG)
        head.pack(fill='x')

        # Left: Title + Count Badge
        t_box = tk.Frame(head, bg=CARD_BG)
        t_box.pack(side='left')

        wl_ico = get_heroicon('bookmark_solid', size=18, color=LINK)
        lbl_head_ico = tk.Label(t_box, image=wl_ico, bg=CARD_BG)
        lbl_head_ico.image = wl_ico
        lbl_head_ico.pack(side='left', padx=(0, 8))

        tk.Label(t_box, text='Watch Later', bg=CARD_BG, fg=INK,
                 font=self.font_sans(13, bold=True)).pack(side='left')

        self.lbl_wl_count = tk.Label(t_box, text='0 videos', bg=PILL_SEC_BG, fg=MUTE,
                                     font=self.font_mono(9, bold=True), padx=8, pady=2)
        self.lbl_wl_count.pack(side='left', padx=(10, 0))

        # Right actions: Clear All, Play First
        self.btn_wl_clear = tk.Frame(head, bg=PILL_SEC_BG, highlightthickness=1,
                                     highlightbackground=PILL_SEC_BORDER, cursor='hand2')
        self.btn_wl_clear.pack(side='right')
        self.lbl_wl_clear = tk.Label(self.btn_wl_clear, text='Clear all', bg=PILL_SEC_BG,
                                     fg=PILL_SEC_FG, font=self.font_sans(9, bold=True),
                                     cursor='hand2', padx=10, pady=3)
        self.lbl_wl_clear.pack()

        def _on_wl_clear_hover(enter):
            bg = PILL_SEC_HOVER_BG if enter else PILL_SEC_BG
            bd = ERROR if enter else PILL_SEC_BORDER
            fg = ERROR if enter else PILL_SEC_FG
            self.btn_wl_clear.configure(bg=bg, highlightbackground=bd)
            self.lbl_wl_clear.configure(bg=bg, fg=fg)

        for w in (self.btn_wl_clear, self.lbl_wl_clear):
            w.bind('<Button-1>', lambda _e: self._clear_watch_later())
            w.bind('<Enter>', lambda _e: _on_wl_clear_hover(True))
            w.bind('<Leave>', lambda _e: _on_wl_clear_hover(False))

        # Play first button
        self.btn_wl_play_all = tk.Frame(head, bg=PILL_PRI_BG, highlightthickness=1,
                                        highlightbackground=PILL_PRI_BORDER, cursor='hand2')
        self.btn_wl_play_all.pack(side='right', padx=(0, 8))
        self.lbl_wl_play_all = tk.Label(self.btn_wl_play_all, text='▶ Play first', bg=PILL_PRI_BG,
                                        fg=PILL_PRI_FG, font=self.font_sans(9, bold=True),
                                        cursor='hand2', padx=10, pady=3)
        self.lbl_wl_play_all.pack()

        def _on_wl_play_hover(enter):
            bg = PILL_PRI_HOVER_BG if enter else PILL_PRI_BG
            bd = PILL_PRI_HOVER_BD if enter else PILL_PRI_BORDER
            fg = PILL_PRI_HOVER_FG if enter else PILL_PRI_FG
            self.btn_wl_play_all.configure(bg=bg, highlightbackground=bd)
            self.lbl_wl_play_all.configure(bg=bg, fg=fg)

        for w in (self.btn_wl_play_all, self.lbl_wl_play_all):
            w.bind('<Button-1>', lambda _e: self._play_first_watch_later())
            w.bind('<Enter>', lambda _e: _on_wl_play_hover(True))
            w.bind('<Leave>', lambda _e: _on_wl_play_hover(False))

        # Horizontal Filter Bar Container (Permanent Liquid Glass Header)
        self.wl_filter_bar = tk.Frame(wl_inner, bg=CARD_BG)
        self.wl_filter_bar.pack(fill='x', pady=(8, 0))
        self._wl_active_cat = 'all'
        self._wl_active_filter = None

        # Scrollable area
        outer = tk.Frame(wl_inner, bg=CARD_BG)
        self.wl_outer = outer
        outer.pack(fill='both', expand=True, pady=(10, 0))

        self.wl_canvas = tk.Canvas(outer, bg=CARD_BG, bd=0, highlightthickness=0)
        self.wl_vsb = ttk.Scrollbar(page, orient='vertical', command=self.wl_canvas.yview)
        self.wl_vsb.grid(row=0, column=1, sticky='ns', padx=(8, 3))
        self.wl_canvas.configure(yscrollcommand=self.wl_vsb.set)
        self.wl_canvas.pack(side='left', fill='both', expand=True)

        self.wl_inner_container = tk.Frame(self.wl_canvas, bg=CARD_BG)
        self.wl_canvas.create_window((0, 0), window=self.wl_inner_container, anchor='nw', tags='wlinner')
        self.wl_inner_container.bind(
            '<Configure>',
            lambda _e: self.wl_canvas.configure(scrollregion=self.wl_canvas.bbox('all')))
        self.wl_canvas.bind(
            '<Configure>',
            self._on_wl_canvas_configure)
        self._mousewheel_bind(self.wl_canvas, self._on_wl_wheel)

        self.lbl_wl_empty = tk.Label(
            self.wl_inner_container,
            text='★  Your Watch Later list is empty\n\n'
                 'Click the bookmark icon on any video card to save it here for later viewing.',
            bg=CARD_BG, fg=FAINT, pady=60, font=self.font_sans(12))
        self.lbl_wl_empty.pack(fill='x')

        self._render_watch_later_filter_bar()

    def _render_watch_later_filter_bar(self):
        for w in self.wl_filter_bar.winfo_children():
            w.destroy()

        saved_videos = config.get_saved_videos() or []

        # Count by source site
        site_counts = {}
        # Group by date
        date_counts = {}
        for it in saved_videos:
            if not isinstance(it, dict):
                continue
            s_name = str(it.get('site_name') or '').strip()
            if not s_name:
                u = str(it.get('url') or '').lower()
                if 'freepornvideos' in u:
                    s_name = 'FreePornVideos'
                elif '1porn' in u:
                    s_name = 'OnePorn'
                elif 'beeg' in u:
                    s_name = 'Beeg'
                else:
                    s_name = 'Other'
            site_counts[s_name] = site_counts.get(s_name, 0) + 1

            saved_date = it.get('saved_date')
            if not saved_date and it.get('saved_at'):
                try:
                    saved_date = time.strftime('%Y-%m-%d', time.localtime(int(it['saved_at'])))
                except Exception:
                    saved_date = time.strftime('%Y-%m-%d')
            elif not saved_date:
                saved_date = time.strftime('%Y-%m-%d')
            date_counts[saved_date] = date_counts.get(saved_date, 0) + 1

        is_dark = (get_effective_theme() == 'dark')
        cap_bg = '#0f121d' if is_dark else '#ffffff'
        cap_bd = '#22283d' if is_dark else '#e2e8f0'
        div_col = '#282f45' if is_dark else '#e2e8f0'
        hover_bg = '#1c2336' if is_dark else '#f1f5f9'

        self.wl_filter_bar.configure(bg=CARD_BG)

        # Outer Liquid Glass Container Capsule
        glass_capsule = tk.Frame(self.wl_filter_bar, bg=cap_bg, highlightthickness=1,
                                 highlightbackground=cap_bd)
        glass_capsule.pack(fill='x', padx=6, pady=2)

        # Left Side: Category Pills
        left_fr = tk.Frame(glass_capsule, bg=cap_bg)
        left_fr.pack(side='left', padx=(6, 4), pady=3)

        cur_cat = getattr(self, '_wl_active_cat', 'all')
        cur_filter = getattr(self, '_wl_active_filter', None)

        if is_dark:
            categories_def = [
                ('all', f'All ({len(saved_videos)})', '#6366f1', '#1a1d2e', '#2c3350', '#e2e8f0'),
                ('sources', f'Sources ({len(site_counts)})', '#3b82f6', '#0f1c33', '#1d3866', '#60a5fa'),
                ('dates', f'Dates ({len(date_counts)})', '#f59e0b', '#241a08', '#4d370e', '#fbbf24'),
            ]
        else:
            categories_def = [
                ('all', f'All ({len(saved_videos)})', '#4f46e5', '#f1f5f9', '#cbd5e1', '#334155'),
                ('sources', f'Sources ({len(site_counts)})', '#2563eb', '#eff6ff', '#bfdbfe', '#2563eb'),
                ('dates', f'Dates ({len(date_counts)})', '#d97706', '#fffbeb', '#fde68a', '#d97706'),
            ]

        for cat_key, cat_label, pri_col, idle_bg, idle_bd, idle_fg in categories_def:
            is_active = (cur_cat == cat_key and cur_filter is None)
            c_bg = pri_col if is_active else idle_bg
            c_bd = pri_col if is_active else idle_bd
            c_fg = '#ffffff' if is_active else idle_fg

            pill = tk.Frame(left_fr, bg=c_bg, highlightthickness=1,
                            highlightbackground=c_bd, cursor='hand2')
            pill.pack(side='left', padx=3, pady=0)

            lbl = tk.Label(pill, text=cat_label, bg=c_bg, fg=c_fg,
                           font=self.font_sans(9, bold=True), cursor='hand2',
                           padx=8, pady=3)
            lbl.pack()

            def make_cat_handlers(p_frame, p_lbl, k_key, p_pri, p_ibg, p_ibd, p_ifg):
                def _on_click(_e=None):
                    self._wl_active_cat = k_key
                    self._wl_active_filter = None
                    self._render_watch_later()

                def _on_enter(_e=None):
                    if not (self._wl_active_cat == k_key and self._wl_active_filter is None):
                        p_frame.configure(highlightbackground=p_pri)
                        p_lbl.configure(fg='#ffffff' if is_dark else p_pri)

                def _on_leave(_e=None):
                    if not (self._wl_active_cat == k_key and self._wl_active_filter is None):
                        p_frame.configure(highlightbackground=p_ibd)
                        p_lbl.configure(fg=p_ifg)

                for w in (p_frame, p_lbl):
                    w.bind('<Button-1>', _on_click)
                    w.bind('<Enter>', _on_enter)
                    w.bind('<Leave>', _on_leave)

            make_cat_handlers(pill, lbl, cat_key, pri_col, idle_bg, idle_bd, idle_fg)

        # Vertical Divider
        div = tk.Frame(glass_capsule, bg=div_col, width=1)
        div.pack(side='left', fill='y', padx=8, pady=3)

        # Right Side: Horizontal Scrollable Chips Canvas
        right_canvas = tk.Canvas(glass_capsule, bg=cap_bg, bd=0, highlightthickness=0, height=37)
        right_canvas.pack(side='left', fill='x', expand=True, padx=(2, 6), pady=3)

        chips_fr = tk.Frame(right_canvas, bg=cap_bg)
        chips_win = right_canvas.create_window((0, 0), window=chips_fr, anchor='nw')

        def _on_chips_configure(_e=None):
            h = max(37, chips_fr.winfo_reqheight())
            right_canvas.configure(height=h, scrollregion=right_canvas.bbox('all'))
        chips_fr.bind('<Configure>', _on_chips_configure)

        def _on_chips_wheel(event):
            delta = -1 if event.delta < 0 else 1
            right_canvas.xview_scroll(-1 * delta, 'units')
            return 'break'

        def _on_chips_drag_start(event):
            right_canvas.scan_mark(event.x, event.y)

        def _on_chips_drag_move(event):
            right_canvas.scan_dragto(event.x, event.y, gain=1)

        right_canvas.bind('<MouseWheel>', _on_chips_wheel)
        chips_fr.bind('<MouseWheel>', _on_chips_wheel)
        right_canvas.bind('<ButtonPress-1>', _on_chips_drag_start)
        right_canvas.bind('<B1-Motion>', _on_chips_drag_move)
        chips_fr.bind('<ButtonPress-1>', _on_chips_drag_start)
        chips_fr.bind('<B1-Motion>', _on_chips_drag_move)

        chips_list = []
        if cur_cat == 'sources':
            for s_name, s_cnt in sorted(site_counts.items()):
                chips_list.append(('source', s_name, f'{s_name} ({s_cnt})', '#3b82f6' if is_dark else '#2563eb'))
        elif cur_cat == 'dates':
            for d_key, d_cnt in sorted(date_counts.items(), reverse=True):
                h_date = config.format_saved_date(d_key)
                chips_list.append(('date', d_key, f'{h_date} ({d_cnt})', '#f59e0b' if is_dark else '#d97706'))
        else:
            for s_name, s_cnt in sorted(site_counts.items()):
                chips_list.append(('source', s_name, f'{s_name} ({s_cnt})', '#3b82f6' if is_dark else '#2563eb'))
            for d_key, d_cnt in sorted(date_counts.items(), reverse=True)[:5]:
                h_date = config.format_saved_date(d_key)
                chips_list.append(('date', d_key, f'{h_date} ({d_cnt})', '#f59e0b' if is_dark else '#d97706'))

        if not chips_list:
            tk.Label(chips_fr, text='No saved videos to filter yet', bg=cap_bg, fg=MUTE,
                     font=self.font_sans(9)).pack(side='left', padx=6, pady=3)
        else:
            for f_type, f_val, f_label, f_accent in chips_list:
                is_active = (cur_filter == (f_type, f_val))
                g_bd = f_accent
                g_bg = f_accent if is_active else ('#161c2d' if is_dark else '#f8fafc')
                g_fg = '#ffffff' if is_active else (f_accent if not is_dark else '#93c5fd')

                chip = tk.Frame(chips_fr, bg=g_bg, highlightthickness=1,
                                highlightbackground=g_bd, cursor='hand2')
                chip.pack(side='left', padx=3, pady=0)

                lbl_c = tk.Label(chip, text=f_label, bg=g_bg, fg=g_fg,
                                 font=self.font_sans(9, bold=True), cursor='hand2', padx=8, pady=3)
                lbl_c.pack(side='left')

                def make_wl_chip_handlers(c_frame, c_lbl, ft, fv, acc_col):
                    def _on_c_click(_e=None):
                        if getattr(self, '_wl_active_filter', None) == (ft, fv):
                            self._wl_active_filter = None
                        else:
                            self._wl_active_filter = (ft, fv)
                        self._render_watch_later()

                    def _on_c_enter(_e=None):
                        c_frame.configure(bg=hover_bg)
                        c_lbl.configure(bg=hover_bg, fg='#ffffff' if is_dark else acc_col)

                    def _on_c_leave(_e=None):
                        if getattr(self, '_wl_active_filter', None) == (ft, fv):
                            c_frame.configure(bg=acc_col)
                            c_lbl.configure(bg=acc_col, fg='#ffffff')
                        else:
                            c_frame.configure(bg='#161c2d' if is_dark else '#f8fafc')
                            c_lbl.configure(bg='#161c2d' if is_dark else '#f8fafc', fg=acc_col)

                    for w in (c_frame, c_lbl):
                        w.bind('<Button-1>', _on_c_click)
                        w.bind('<Enter>', _on_c_enter)
                        w.bind('<Leave>', _on_c_leave)
                        w.bind('<MouseWheel>', _on_chips_wheel)

                make_wl_chip_handlers(chip, lbl_c, f_type, f_val, f_accent)

    def _on_wl_canvas_configure(self, event=None):
        if event is not None and hasattr(event, 'width'):
            w = event.width
        else:
            w = self.wl_canvas.winfo_width()
        if w > 50:
            self.wl_canvas.itemconfigure('wlinner', width=w)
            cols, _cw = self._calc_cols_and_width(w)
            if cols != getattr(self, '_wl_cols', 3):
                self._wl_cols = cols
                if getattr(self, '_wl_relayout_timer', None):
                    try:
                        self.after_cancel(self._wl_relayout_timer)
                    except Exception:
                        pass
                self._wl_relayout_timer = self.after(120, self._render_watch_later)

    def _on_wl_wheel(self, event):
        self.wl_canvas.yview_scroll(int(-event.delta / 120), 'units')

    def _clear_watch_later(self):
        if messagebox.askyesno('Clear Watch Later', 'Are you sure you want to remove all saved videos from Watch Later?'):
            config.clear_saved_videos()
            self._render_watch_later()
            self._sync_all_card_save_states()
            self.show_toast('Watch Later cleared', icon='trash', color=ERROR)

    def _play_first_watch_later(self):
        saved = config.get_saved_videos()
        if saved:
            self.watch_item(dict(saved[0]))

    def _on_watch_later_updated(self, url=None):
        if getattr(self, '_current_tab', '') == 'watch_later':
            self._render_watch_later()
        self._sync_all_card_save_states(url)

    def _sync_all_card_save_states(self, target_url=None):
        cards = getattr(self, '_cards', [])
        for c in cards:
            if not bool(c.winfo_exists()):
                continue
            u = str(c.item.get('url') or '')
            if target_url is None or u == target_url:
                is_saved = config.is_video_saved(u)
                c.set_save_state(is_saved)

    def _render_watch_later(self):
        for w in self.wl_inner_container.winfo_children():
            if w is not self.lbl_wl_empty:
                w.destroy()

        all_saved_videos = config.get_saved_videos() or []
        count = len(all_saved_videos)
        self.lbl_wl_count.configure(text=f'{count} {"video" if count == 1 else "videos"}')

        self._render_watch_later_filter_bar()

        if not all_saved_videos:
            self.lbl_wl_empty.pack(fill='x')
            self.btn_wl_play_all.pack_forget()
            self.btn_wl_clear.pack_forget()
            return

        self.lbl_wl_empty.pack_forget()
        if not self.btn_wl_clear.winfo_ismapped():
            self.btn_wl_clear.pack(side='right')
        if not self.btn_wl_play_all.winfo_ismapped():
            self.btn_wl_play_all.pack(side='right', padx=(0, 8))

        # Filter items if active filter or active category
        cur_filter = getattr(self, '_wl_active_filter', None)
        saved_videos = []
        for item in all_saved_videos:
            if not isinstance(item, dict):
                continue
            if cur_filter:
                f_type, f_val = cur_filter
                if f_type == 'source':
                    s_name = str(item.get('site_name') or '').strip()
                    if not s_name:
                        u = str(item.get('url') or '').lower()
                        if 'freepornvideos' in u:
                            s_name = 'FreePornVideos'
                        elif '1porn' in u:
                            s_name = 'OnePorn'
                        elif 'beeg' in u:
                            s_name = 'Beeg'
                        else:
                            s_name = 'Other'
                    if s_name != f_val:
                        continue
                elif f_type == 'date':
                    saved_date = item.get('saved_date')
                    if not saved_date and item.get('saved_at'):
                        try:
                            saved_date = time.strftime('%Y-%m-%d', time.localtime(int(item['saved_at'])))
                        except Exception:
                            saved_date = time.strftime('%Y-%m-%d')
                    elif not saved_date:
                        saved_date = time.strftime('%Y-%m-%d')
                    if saved_date != f_val:
                        continue
            saved_videos.append(item)

        if not saved_videos:
            lbl_empty_filter = tk.Label(
                self.wl_inner_container,
                text='No videos match the selected filter.',
                bg=CARD_BG, fg=FAINT, pady=40, font=self.font_sans(11))
            lbl_empty_filter.pack(fill='x')
            return

        # Group videos by date string (YYYY-MM-DD), newest dates first
        groups = {}
        for item in saved_videos:
            saved_date = item.get('saved_date')
            saved_at = item.get('saved_at')
            if not saved_date and saved_at:
                try:
                    saved_date = time.strftime('%Y-%m-%d', time.localtime(int(saved_at)))
                except Exception:
                    saved_date = time.strftime('%Y-%m-%d')
            elif not saved_date:
                saved_date = time.strftime('%Y-%m-%d')
            groups.setdefault(saved_date, []).append(item)

        sorted_dates = sorted(groups.keys(), reverse=True)

        w = max(200, self.wl_canvas.winfo_width())
        cols, card_w = self._calc_cols_and_width(w)
        self._wl_cols = cols

        for d_idx, date_key in enumerate(sorted_dates):
            vids = groups[date_key]
            # Date Section Container
            sec_frame = tk.Frame(self.wl_inner_container, bg=CARD_BG)
            sec_frame.pack(fill='x', padx=6, pady=(12, 16))

            # Date Header Bar
            date_head = tk.Frame(sec_frame, bg=CARD_BG)
            date_head.pack(fill='x', pady=(0, 10))

            human_date = config.format_saved_date(date_key)
            lbl_date_txt = tk.Label(date_head, text=human_date, bg=CARD_BG, fg=INK,
                                    font=self.font_sans(11, bold=True))
            lbl_date_txt.pack(side='left')

            count_str = f'{len(vids)} {"video" if len(vids) == 1 else "videos"}'
            lbl_date_cnt = tk.Label(date_head, text=f'·  {count_str}', bg=CARD_BG, fg=MUTE,
                                    font=self.font_mono(10))
            lbl_date_cnt.pack(side='left', padx=(8, 0))

            # Hairline divider stretching across
            tk.Frame(date_head, bg=HAIRLINE, height=1).pack(side='left', fill='x', expand=True, padx=(14, 0), pady=6)

            # Grid of video cards for this date
            grid_frame = tk.Frame(sec_frame, bg=CARD_BG)
            grid_frame.pack(fill='x')

            for c in range(cols):
                grid_frame.grid_columnconfigure(c, weight=1, uniform='wlcol')

            for i, vid in enumerate(vids):
                card = VideoCard(self, grid_frame, vid)
                r, c = divmod(i, cols)
                card.grid(row=r, column=c, padx=8, pady=8, sticky='nsew')
                card.set_width(card_w)
                self._bind_wheel_recursive(card, self._on_wl_wheel)

                url = vid.get('thumbnail') or ''
                if url:
                    cached = self._thumb_cache.get(url)
                    if cached is not None:
                        card.apply_image(cached)
                    else:
                        self.thumb_pool.submit(self._load_thumb, card, url)

    # ---------- Queue Management & Helpers ----------
    def _on_inner_configure(self, _event):
        self.queue_canvas.configure(scrollregion=self.queue_canvas.bbox('all'))
        self.after_idle(self._update_vsb)
        has_rows = bool(self.rows)
        if hasattr(self, 'empty_hint'):
            if has_rows and self.empty_hint.winfo_manager():
                self.empty_hint.pack_forget()
            elif not has_rows and not self.empty_hint.winfo_manager():
                self.empty_hint.pack(fill='x')

    def _update_vsb(self):
        canvas_h = self.queue_canvas.winfo_height()
        need = canvas_h > 1 and self.queue_inner.winfo_reqheight() > canvas_h
        if need and not self.vsb.winfo_manager():
            self.vsb.grid(row=0, column=1, sticky='ns')
        elif not need and self.vsb.winfo_manager():
            self.vsb.grid_remove()

    def _mousewheel_bind(self, widget, handler=None):
        handler = handler or self._on_queue_wheel
        widget.bind('<Enter>', lambda _e: widget.bind_all('<MouseWheel>', handler))
        widget.bind('<Leave>', lambda _e: widget.unbind_all('<MouseWheel>'))

    def _bind_wheel_recursive(self, widget, handler=None):
        """Bind mousewheel event directly to top widget."""
        handler = handler or self._on_cards_wheel
        try:
            widget.bind('<MouseWheel>', handler, add='+')
        except Exception:
            pass

    def _on_queue_wheel(self, event):
        self.queue_canvas.yview_scroll(int(-1 * (event.delta / 120) * 3), 'units')

    def _on_cards_wheel(self, event):
        self.cards_canvas.yview_scroll(int(-1 * (event.delta / 120) * 3), 'units')
        self.after_idle(self._maybe_load_more)

    def _open_save_folder(self):
        d = os.path.abspath(self.save_dir.get() or '.')
        os.makedirs(d, exist_ok=True)
        os.startfile(d)

    def _pick_folder(self):
        d = filedialog.askdirectory(initialdir=self.save_dir.get() or '.')
        if d:
            self.save_dir.set(d)

    def say(self, msg):
        self.events.put(('log', msg))

    def show_toast(self, message, icon='download', color='#38bdf8'):
        """Displays a floating Vercel glass pill toast notification with smooth animation."""
        if not hasattr(self, '_toast_frame'):
            self._toast_frame = None
            self._toast_timer = None

        if self._toast_timer:
            try:
                self.after_cancel(self._toast_timer)
            except Exception:
                pass
            self._toast_timer = None

        if self._toast_frame and bool(self._toast_frame.winfo_exists()):
            try:
                self._toast_frame.destroy()
            except Exception:
                pass

        toast = tk.Frame(self, bg=ELEVATED, highlightthickness=1,
                         highlightbackground=LINK, cursor='hand2')
        self._toast_frame = toast

        ico_img = get_heroicon(icon, size=16, color=color)
        ico_lbl = tk.Label(toast, image=ico_img, bg=ELEVATED)
        ico_lbl.image = ico_img
        ico_lbl.pack(side='left', padx=(12, 6), pady=7)

        msg_lbl = tk.Label(toast, text=message, bg=ELEVATED, fg=INK,
                           font=self.font_sans(10, bold=True))
        msg_lbl.pack(side='left', padx=(0, 14), pady=7)

        # Place floating centered near top
        toast.place(relx=0.5, y=56, anchor='n')

        def _settle():
            if bool(toast.winfo_exists()):
                toast.configure(highlightbackground=HAIRLINE)

        self.after(220, _settle)

        def _dismiss():
            if bool(toast.winfo_exists()):
                try:
                    toast.destroy()
                except Exception:
                    pass
            self._toast_frame = None
            self._toast_timer = None

        for w in (toast, msg_lbl, ico_lbl):
            w.bind('<Button-1>', lambda _e: _dismiss())

        self._toast_timer = self.after(2800, _dismiss)

    def add_urls(self, urls):
        added = skipped = invalid = 0
        seen = {r.url for r in self.rows}
        for url in urls:
            if not url:
                continue
            cls = pick_site_class(url)
            if cls is None:
                invalid += 1
                continue
            norm = url.rstrip('/')
            if norm in seen or url in seen:
                skipped += 1
                continue
            seen.add(norm)
            save_at = os.path.abspath(self.save_dir.get() or '.')
            with self.row_lock:
                row = JobRow(self, url, len(self.rows))
                row.save_dir = save_at
                self.rows.append(row)
            added += 1
            self.resolver_pool.submit(self._resolve_row, row)
        if invalid:
            messagebox.showwarning(
                APP_TITLE,
                f'{invalid} line(s) ignored \u2014 only freepornvideos.xxx, 1porn.tv '
                'and beeg.com video URLs are supported.')
        self._update_overall()

    def remove_row(self, row):
        with self.row_lock:
            if row in self.rows:
                self.rows.remove(row)
        row.frame.destroy()
        self._update_overall()

    def clear_finished(self):
        for row in [r for r in list(self.rows) if r.state in ('done', 'error', 'cancelled')]:
            self.remove_row(row)

    def cancel_all(self):
        for row in list(self.rows):
            row.cancelled = True
            c = row.crawler
            if c is not None:
                c._cancel_job = True

    def select_row(self, row):
        self._selected_row = row
        for r in self.rows:
            try:
                r.frame.configure(highlightbackground=(
                    LINK if r is row else CARD_BORDER))
            except Exception:
                pass

    def cancel_selected(self):
        row = getattr(self, '_selected_row', None)
        if row is None or row not in list(self.rows):
            self.say('Select a queued item first \u2014 click its card.')
            return
        row.cancelled = True
        c = row.crawler
        if c is not None:
            c._cancel_job = True
        self.say('Cancellation requested for the selected item.')

    def start_rows(self, rows):
        rows = [r for r in rows if r.state == 'ready' and not r.cancelled]
        if not rows:
            return
        save_dir = os.path.abspath(self.save_dir.get() or '.')
        os.makedirs(save_dir, exist_ok=True)
        set_resolution_pref(self.quality.get())
        if self.dl_pool is None:
            self.dl_pool = futures.ThreadPoolExecutor(max_workers=config.get_download_concurrency(),
                                                      thread_name_prefix='dl')

        def worker(row):
            try:
                self._download_row(row, save_dir)
            finally:
                self.events.put(('job_done', row))

        for row in rows:
            row.state = 'downloading'
            self.events.put(('state', row, 'downloading', 'starting\u2026'))
            self.dl_pool.submit(worker, row)

    def start_all(self):
        ready = [r for r in list(self.rows) if r.state == 'ready']
        if not ready:
            self.say('No resolved streams to download yet.')
            return
        self.start_rows(ready)

    # ---------- browse-card actions ----------
    def _row_for_url(self, url):
        norm = url.rstrip('/')
        for row in list(self.rows):
            if row.url.rstrip('/') == norm:
                return row
        return None

    def _unbusy_cards_for(self, url):
        norm = url.rstrip('/')
        for card in list(getattr(self, '_cards', [])):
            try:
                if not bool(card.winfo_exists()):
                    continue
                if str(card.item.get('url', '')).rstrip('/') == norm:
                    card.set_idle()
            except Exception:
                pass

    def queue_item(self, item):
        url = item['url']
        title = str(item.get('title') or 'Video').strip()
        short_title = (title[:34] + '…') if len(title) > 36 else title
        try:
            analytics.track('queue_add', site=str(item.get('site_name') or ''))
        except Exception:
            pass
        row = self._row_for_url(url)
        if row is None or row.state in ('error', 'cancelled', 'blocked'):
            with self.row_lock:
                if row is not None:
                    try:
                        row.frame.destroy()
                    except Exception:
                        pass
                    if row in self.rows:
                        self.rows.remove(row)
                save_at = os.path.abspath(self.save_dir.get() or '.')
                row = JobRow(self, url, len(self.rows))
                row.save_dir = save_at
                self.rows.append(row)
            self.resolver_pool.submit(self._resolve_row, row)
            self.say('Added to queue — resolving stream link…')
            self.show_toast(f'Added to queue: {short_title}', icon='plus', color=LINK)
        else:
            self.say('Already in the queue.')
            self.show_toast(f'Already in queue: {short_title}', icon='check', color='#a1a1aa')
        self._update_overall()

    def download_item(self, item, card=None):
        url = item['url']
        title = str(item.get('title') or 'Video').strip()
        short_title = (title[:34] + '…') if len(title) > 36 else title
        try:
            analytics.track('download_start', site=str(item.get('site_name') or ''))
        except Exception:
            pass
        row = self._row_for_url(url)
        if row is None:
            if card is not None:
                card.set_busy('Downloading…')
            with self.row_lock:
                save_at = os.path.abspath(self.save_dir.get() or '.')
                row = JobRow(self, url, len(self.rows))
                row.save_dir = save_at
                row.auto_download = True
                self.rows.append(row)
            self.resolver_pool.submit(self._resolve_row, row)
            self.say('Started download in background — resolving link…')
            self.show_toast(f'Downloading: {short_title}', icon='download', color='#38bdf8')
            self._update_overall()
            return
        if row.auto_watch:
            row.auto_watch = False
        if row.state == 'ready':
            row.auto_download = False
            if card is not None:
                card.set_busy('Downloading…')
            self.start_rows([row])
            self.say('Started download.')
            self.show_toast(f'Downloading: {short_title}', icon='download', color='#38bdf8')
            self._update_overall()
            return
        if row.state == 'downloading':
            self.say('Already downloading in the background.')
            self.show_toast(f'Already downloading: {short_title}', icon='download', color='#a1a1aa')
            return
        if row.state in ('error', 'cancelled', 'blocked'):
            with self.row_lock:
                try:
                    row.frame.destroy()
                except Exception:
                    pass
                if row in self.rows:
                    self.rows.remove(row)
            self.download_item(item, card)
            return
        if card is not None:
            card.set_busy('Downloading…')
        self.show_toast(f'Downloading: {short_title}', icon='download', color='#38bdf8')
        row.auto_download = True
        self.say('Queued for download.')
        self._update_overall()

    def watch_item(self, item, card=None):
        url = item.get('url')
        if not url:
            return
        try:
            analytics.track('watch', site=str(item.get('site_name') or ''))
        except Exception:
            pass

        # If already in the queue and resolved, open directly
        row = self._row_for_url(url)
        if row is not None and row.state == 'ready' and row.crawler is not None:
            self.open_player_for_row(row, item=item)
            return

        if card is not None:
            card.set_busy('Opening\u2026')

        title = item.get('title') or url

        def resolver_worker():
            cls = pick_site_class(url)
            crawler = None
            if cls is not None:
                try:
                    savepath = os.path.abspath(self.save_dir.get() or '.')
                    crawler = cls(url, savepath=savepath, silence=True)
                except Exception:
                    crawler = None
                if crawler is None:
                    try:
                        crawler = cls(url, savepath='', silence=True)
                        if not crawler.is_url_vaildate():
                            crawler = None
                    except Exception:
                        crawler = None

            link = None
            resolved_title = title
            if crawler and crawler.is_url_vaildate():
                try:
                    resolved_title = crawler.target_name() or title
                except Exception:
                    pass
                links = (crawler.stream_links() if hasattr(crawler, 'stream_links') else {}) or {}
                for key in ('HLS master', 'mp4'):
                    if key in links:
                        link = links[key]
                        break
                if not link and links:
                    link = next(iter(links.values()), None)
                if not link:
                    link = getattr(crawler, '_direct_url', None)

            self.events.put(('playback_ready', url, resolved_title, link, item))

        self.resolver_pool.submit(resolver_worker)

    def open_player_for_row(self, row, item=None):
        link = row.current_link()
        if item is None:
            site = _SITE_LABEL.get(getattr(row, 'site_cls', None), '')
            item = {'url': row.url, 'site_name': site}
        try:
            title = row.lbl_title.cget('text')
        except Exception:
            title = row.url
        if not link:
            messagebox.showinfo(
                APP_TITLE,
                'No stream link available for this video yet.\n'
                'Resolve it first (or wait until resolving finishes).')
            self.say('Watch failed \u2014 no stream link available.')
            return
        try:
            self.switch_tab('browse')
        except Exception:
            pass
        self.play_in_preview(title, link, item=item, url=row.url)

    # ===== in-app preview player =====
    def play_in_preview(self, title, link, item=None, url=None):
        if getattr(self, '_fs_active', False):
            self._exit_fullscreen()
        self._preview_seq = getattr(self, '_preview_seq', 0) + 1
        self._preview_item = item
        self._preview_url = url or (item or {}).get('url')
        self._preview_info_data = None
        self._recs_page_map = {}
        self._recs_seen_urls = {str(self._preview_url or '').rstrip('/')}
        self._recs_shuffle_idx = 0
        self._show_back_bar(False)
        self.sidebar_wrap.pack_forget()
        self.grid_outer.grid_remove()
        self.player_host.grid(row=0, column=0, sticky='nsew')
        self.preview_stage.configure(width=0)
        self.preview_title.configure(text=title[:90])
        self.preview_status.configure(text='opening\u2026', fg=MUTE)
        self._stop_preview_playback()
        self._preview_closing = False
        self._watch_recorded = False
        self._render_preview_info(None)
        self._clear_recs('Loading related videos\u2026')
        self._update_player_save_button()
        if hasattr(self, 'player_canvas'):
            self.player_canvas.yview_moveto(0)
        self._player_layout_mode = None
        self._on_player_host_configure()
        if self._preview_url:
            seq = self._preview_seq
            threading.Thread(target=self._load_preview_meta,
                             args=(seq, False), daemon=True).start()

        watch_item = dict(item or {})
        watch_item.setdefault('url', self._preview_url or link)
        watch_item.setdefault('site_name', '')
        watch_item.setdefault('title', title[:120])
        self._pending_watch_item = watch_item
        self._watch_recorded = False
        self._start_preview_engine(link)

    def shuffle_recommendations(self):
        if getattr(self, '_preview_closing', False) or not self._preview_url:
            return
        self._clear_recs('Shuffling related videos\u2026')
        seq = getattr(self, '_preview_seq', 0)
        threading.Thread(target=self._load_preview_meta,
                         args=(seq, True), daemon=True).start()

    def _load_preview_meta(self, seq, is_shuffle=False):
        import random
        item = dict(self._preview_item or {})
        item.setdefault('url', self._preview_url or '')
        site = str(item.get('site_name') or '')
        if site == 'Beeg':
            self.events.put(('preview_recs', seq, []))
            return
        if site == 'OnePorn':
            browser = OnePornTVBrowser
        else:
            browser = self._kvs_browser_for_url(item.get('url') or '')

        def stale():
            return (seq != getattr(self, '_preview_seq', -1)
                    or getattr(self, '_preview_closing', False))

        info = getattr(self, '_preview_info_data', None)
        if info is None:
            try:
                info = browser.fetch_video_info(item['url'])
            except Exception as exc:
                print('video info failed:', exc)
                info = None
            if stale():
                return
            self._preview_info_data = info
            self.events.put(('preview_info', seq, info))

        tags = list((info or {}).get('tags') or [])
        models = list((info or {}).get('models') or [])
        categories = tags + models

        if not hasattr(self, '_recs_page_map') or not isinstance(self._recs_page_map, dict):
            self._recs_page_map = {}
        if not hasattr(self, '_recs_seen_urls') or not isinstance(self._recs_seen_urls, set):
            self._recs_seen_urls = {item['url'].rstrip('/')}

        recs = []

        if categories:
            query_cats = list(categories)
            if is_shuffle:
                random.shuffle(query_cats)

            for cat in query_cats:
                if stale():
                    return
                cat_url = cat.get('url') or ''
                if not cat_url:
                    continue

                cur_page = self._recs_page_map.get(cat_url, 1)
                if is_shuffle:
                    cur_page = (cur_page % 6) + 1
                self._recs_page_map[cat_url] = cur_page

                try:
                    target_url = browser.page_url(cat_url, cur_page)
                    rows = browser.fetch_page(target_url)
                except Exception as exc:
                    print('related fetch failed:', exc)
                    continue

                for it in rows:
                    key = str(it.get('url') or '').rstrip('/')
                    if not key or key in self._recs_seen_urls:
                        continue
                    self._recs_seen_urls.add(key)
                    recs.append(it)
                if len(recs) >= 18:
                    break

        if len(recs) < 8:
            if len(self._recs_seen_urls) > 60:
                self._recs_seen_urls = {item['url'].rstrip('/')}
            try:
                gen_page = random.randint(1, 5) if is_shuffle else 1
                cat_tag = (tags[0]['url'] if tags else '')
                if cat_tag:
                    fallback_rows = browser.fetch_page(browser.page_url(cat_tag, gen_page))
                    for it in fallback_rows:
                        key = str(it.get('url') or '').rstrip('/')
                        if key and key not in self._recs_seen_urls:
                            self._recs_seen_urls.add(key)
                            recs.append(it)
            except Exception:
                pass

        if stale():
            return

        if is_shuffle and recs:
            random.shuffle(recs)

        self.events.put(('preview_recs', seq, recs[:18]))

    def _load_performer_avatar(self, name, model_url, thumb_url, card_widget, width=210, height=290, role='actress'):
        """Asynchronously loads raw photo, caches, and renders uniform poster cards."""
        name_key = str(name).strip().lower()
        if not hasattr(self, '_performer_raw_cache'):
            self._performer_raw_cache = {}
        if not hasattr(self, '_performer_poster_cache'):
            self._performer_poster_cache = {}

        is_starred = config.is_in_watchlist(name, 'models' if role.lower() == 'actress' else 'actors')
        cache_key = (name_key, is_starred, False)

        if cache_key in self._performer_poster_cache:
            photo = self._performer_poster_cache[cache_key]
            if photo and bool(card_widget.winfo_exists()):
                try:
                    card_widget.configure(image=photo)
                    card_widget.image = photo
                    card_widget._norm_photo = photo
                    card_widget._hover_photo = self._performer_poster_cache.get((name_key, is_starred, True), photo)
                except Exception:
                    pass
                return

        def worker():
            nonlocal thumb_url
            raw_img = self._performer_raw_cache.get(name_key)
            if raw_img is None:
                # 1. Look up in sidebar cache (check both models and actors)
                if not thumb_url:
                    try:
                        sb_cache = config.get_sidebar_cache()
                        for list_key in ('models', 'actors'):
                            for m in sb_cache.get(list_key, []):
                                if str(m.get('name', '')).strip().lower() == name_key and m.get('thumb'):
                                    thumb_url = m['thumb']
                                    break
                            if thumb_url:
                                break
                    except Exception:
                        pass

                # 2. If still missing, fetch on the fly from model page
                if not thumb_url and model_url:
                    try:
                        browser = self._kvs_browser_for_url(model_url)
                        if hasattr(browser, 'fetch_model_thumb'):
                            thumb_url = browser.fetch_model_thumb(model_url)
                    except Exception:
                        pass

                # 3. Download raw image
                if thumb_url:
                    try:
                        session = getattr(self, '_thumb_session', requests)
                        resp = session.get(thumb_url, timeout=6, headers={'User-Agent': 'Mozilla/5.0'})
                        if resp.status_code == 200:
                            raw_img = Image.open(io.BytesIO(resp.content)).convert('RGBA')
                            self._performer_raw_cache[name_key] = raw_img
                    except Exception:
                        pass

            # Safe cross-thread event dispatch to main UI loop
            self.events.put(('performer_avatar', card_widget, name_key, raw_img, name, role, width, height))

        threading.Thread(target=worker, daemon=True).start()

    def _apply_performer_avatar(self, card_widget, name_key, raw_img, name, role, width, height):
        try:
            curr_starred = config.is_in_watchlist(name, 'models' if role.lower() == 'actress' else 'actors')
            norm_photo = create_poster_card_img(raw_img, name, role=role, is_starred=curr_starred,
                                                width=width, height=height, is_hover=False)
            hover_photo = create_poster_card_img(raw_img, name, role=role, is_starred=curr_starred,
                                                 width=width, height=height, is_hover=True)

            self._performer_poster_cache[(name_key, curr_starred, False)] = norm_photo
            self._performer_poster_cache[(name_key, curr_starred, True)] = hover_photo

            if bool(card_widget.winfo_exists()):
                card_widget.configure(image=norm_photo)
                card_widget.image = norm_photo
                card_widget._norm_photo = norm_photo
                card_widget._hover_photo = hover_photo
                card_widget._is_starred = curr_starred
        except Exception as exc:
            print('Apply performer avatar failed:', exc)

    def _render_preview_info(self, info):
        for w in self.preview_info.winfo_children():
            w.destroy()

        # Build clean translucent Description & Details container below the video
        card_bg_color = HAIRLINE_SOFT  # Softer, lower-opacity surface
        desc_card = tk.Frame(self.preview_info, bg=card_bg_color, highlightthickness=1,
                             highlightbackground=CARD_BORDER)
        desc_card.pack(fill='x', pady=(0, 14))

        desc_in = tk.Frame(desc_card, bg=card_bg_color, padx=16, pady=12)
        desc_in.pack(fill='x')

        # Header bar containing "Description & Details" on left and action buttons (Download + Save) on right
        desc_head = tk.Frame(desc_in, bg=card_bg_color)
        desc_head.pack(fill='x', pady=(0, 8))

        self.eyebrow(desc_head, 'Description & Details').pack(side='left', anchor='center')

        # Action Buttons container (inline on right of Description & Details)
        actions_bar = tk.Frame(desc_head, bg=card_bg_color)
        actions_bar.pack(side='right', anchor='center')

        # 1. Download Button (Liquid Sapphire Glass Pill)
        self.btn_dl_info = tk.Frame(actions_bar, bg=PILL_PRI_BG, highlightthickness=1,
                                    highlightbackground=PILL_PRI_BORDER, cursor='hand2')
        self.btn_dl_info.pack(side='left', padx=(0, 8))

        dl_ico = get_heroicon('download', size=14, color=LINK)
        self.lbl_dl_info = tk.Label(self.btn_dl_info, text=' Download', image=dl_ico,
                                    compound='left', bg=PILL_PRI_BG, fg=PILL_PRI_FG,
                                    font=self.font_sans(9, bold=True), cursor='hand2',
                                    padx=10, pady=4)
        self.lbl_dl_info.image = dl_ico
        self.lbl_dl_info.pack()

        def _on_info_dl_hover(enter):
            bg = PILL_PRI_HOVER_BG if enter else PILL_PRI_BG
            bd = PILL_PRI_HOVER_BD if enter else PILL_PRI_BORDER
            fg = PILL_PRI_HOVER_FG if enter else PILL_PRI_FG
            self.btn_dl_info.configure(bg=bg, highlightbackground=bd)
            self.lbl_dl_info.configure(bg=bg, fg=fg)

        for w in (self.btn_dl_info, self.lbl_dl_info):
            w.bind('<Button-1>', lambda _e: self._download_from_player())
            w.bind('<Enter>', lambda _e: _on_info_dl_hover(True))
            w.bind('<Leave>', lambda _e: _on_info_dl_hover(False))

        # 2. Save / Watch Later Bookmark Button (Liquid Glass Pill)
        self.btn_save_info = tk.Frame(actions_bar, bg=PILL_SEC_BG, highlightthickness=1,
                                      highlightbackground=PILL_SEC_BORDER, cursor='hand2')
        self.btn_save_info.pack(side='left')

        url_str = str(self._preview_url or (self._preview_item or {}).get('url') or '')
        is_cur_saved = config.is_video_saved(url_str)
        save_col = LINK if is_cur_saved else PILL_SEC_FG
        save_ico = get_heroicon('bookmark_solid' if is_cur_saved else 'bookmark', size=14, color=save_col)
        save_text = ' Saved' if is_cur_saved else ' Save'
        self.lbl_save_info = tk.Label(self.btn_save_info, text=save_text, image=save_ico,
                                      compound='left', bg=PILL_SEC_BG, fg=save_col,
                                      font=self.font_sans(9, bold=True), cursor='hand2',
                                      padx=10, pady=4)
        self.lbl_save_info.image = save_ico
        self.lbl_save_info.pack()

        def _on_info_save_hover(enter):
            u = str(self._preview_url or (self._preview_item or {}).get('url') or '')
            saved = config.is_video_saved(u)
            bg = PILL_SEC_HOVER_BG if enter else PILL_SEC_BG
            bd = PILL_SEC_HOVER_BD if enter else PILL_SEC_BORDER
            fg = LINK_HOVER if (enter and saved) else (PILL_SEC_HOVER_FG if enter else (LINK if saved else PILL_SEC_FG))
            self.btn_save_info.configure(bg=bg, highlightbackground=bd)
            self.lbl_save_info.configure(bg=bg, fg=fg)

        for w in (self.btn_save_info, self.lbl_save_info):
            w.bind('<Button-1>', lambda _e: self._save_from_player())
            w.bind('<Enter>', lambda _e: _on_info_save_hover(True))
            w.bind('<Leave>', lambda _e: _on_info_save_hover(False))

        if info is None:
            if self._preview_url and str((self._preview_item or {}).get('site_name') or '') != 'Beeg':
                lbl_fetch = tk.Label(desc_in, text='Fetching video details\u2026',
                                     bg=card_bg_color, fg=FAINT, font=self.font_sans(10), anchor='w')
                lbl_fetch.pack(fill='x', pady=(4, 2))
                self._bind_wheel_recursive(lbl_fetch, self._on_player_wheel)
            self._update_player_vsb()
            return

        # Performers (models & actors)
        models = info.get('models') or []
        actors = info.get('actors') or []
        performers = []
        for m in models:
            performers.append((m, 'actress', 'models'))
        for a in actors:
            performers.append((a, 'actor', 'actors'))

        # Performer names string for description
        names = [p[0].get('name') for p in performers if p[0].get('name')]
        names_str = ", ".join(names)

        # Unified Description & Metadata Card
        desc = (info.get('description') or '').strip()
        studio = info.get('studio')
        tags = info.get('tags') or []

        full_desc = ""
        if desc:
            if names_str and not all(n.lower() in desc.lower() for n in names):
                full_desc = f"{desc}\n\nStarring: {names_str}"
            else:
                full_desc = desc
        elif names_str:
            full_desc = f"Starring: {names_str}"

        if full_desc:
            lbl_desc = tk.Label(desc_in, text=full_desc, bg=card_bg_color, fg=BODY,
                                font=self.font_sans(10), justify='left', anchor='w')
            lbl_desc.pack(fill='x', anchor='w', pady=(0, 8))
            desc_in.bind('<Configure>', lambda e, l=lbl_desc: l.configure(wraplength=max(240, e.width - 12)))

        def heading(parent, label_text):
            tk.Label(parent, text=label_text, bg=card_bg_color, fg=MUTE,
                     font=self.font_sans(9, bold=True), width=8, anchor='nw'
                     ).pack(side='left', anchor='n', pady=3)

        def chip_row(parent, label_text, entries, icon_name='tag', kind_key='tags'):
            fr = tk.Frame(parent, bg=card_bg_color)
            fr.pack(fill='x', pady=4)
            heading(fr, label_text)

            txt = tk.Text(fr, bg=card_bg_color, fg=BODY,
                          font=self.font_sans(13), bd=0,
                          highlightthickness=0, wrap='word', height=1,
                          spacing1=3, spacing2=4, spacing3=4, padx=0, pady=2,
                          cursor='arrow', takefocus=0)
            txt.pack(side='left', fill='x', expand=True)

            def autosize(_e=None):
                try:
                    n = txt.count('1.0', 'end', 'displaylines')
                    n = n[0] if isinstance(n, tuple) else (n or 1)
                    txt.configure(height=max(1, int(n)))
                except Exception:
                    pass
            txt.bind('<Configure>', autosize)
            self.after_idle(autosize)

            for entry in entries:
                e_name, e_url = entry.get('name') or '', entry.get('url') or ''
                if not e_name:
                    continue

                is_starred = config.is_in_watchlist(e_name, kind_key)
                item_fr = tk.Frame(txt, bg=card_bg_color, bd=0, highlightthickness=0, cursor='hand2')

                star_color = '#f59e0b' if is_starred else MUTE
                star_char = '★' if is_starred else '☆'
                lbl_star = tk.Label(item_fr, text=star_char, bg=card_bg_color, fg=star_color,
                                    font=self.font_sans(10, bold=True), cursor='hand2', padx=2, pady=0)
                lbl_star.pack(side='left')

                display_txt = f'#{e_name}' if label_text == 'TAGS' else e_name
                lbl_name = tk.Label(item_fr, text=display_txt, bg=card_bg_color, fg=BODY,
                                    font=self.font_sans(10), cursor='hand2', padx=2, pady=0)
                lbl_name.pack(side='left')

                def make_item_handlers(p_frame, p_star, p_name, u_name, u_url, u_kind):
                    def _toggle_star(_e=None):
                        curr_starred = config.is_in_watchlist(u_name, u_kind)
                        if curr_starred:
                            config.remove_watchlist_item(u_name, u_kind)
                            p_star.configure(text='☆', fg=MUTE)
                            self.show_toast(f'Removed "{u_name}" from Watchlist', icon='star', color=MUTE)
                        else:
                            config.add_watchlist_item({
                                'name': u_name,
                                'type': u_kind,
                                'urls': [u_url] if u_url else [],
                                'starred_at': time.time()
                            })
                            p_star.configure(text='★', fg='#f59e0b')
                            self.show_toast(f'★ Added "{u_name}" to Watchlist', icon='star', color='#f59e0b')
                        return 'break'

                    def _on_enter(_e=None):
                        p_name.configure(fg=LINK_HOVER)

                    def _on_leave(_e=None):
                        p_name.configure(fg=BODY)

                    def _on_name_click(_e=None):
                        if u_url:
                            self._preview_nav(u_url)

                    p_star.bind('<Button-1>', _toggle_star)
                    p_name.bind('<Button-1>', _on_name_click)
                    p_frame.bind('<Button-1>', _on_name_click)

                    for w in (p_star, p_name, p_frame):
                        w.bind('<Enter>', _on_enter)
                        w.bind('<Leave>', _on_leave)

                make_item_handlers(item_fr, lbl_star, lbl_name, e_name, e_url, kind_key)
                txt.window_create('end', window=item_fr)
                txt.insert('end', '   ')

            txt.configure(state='disabled')

        # Details inside Description Card: Studio and Tags
        meta_sub = tk.Frame(desc_in, bg=card_bg_color)
        meta_sub.pack(fill='x', pady=(4, 0))

        if studio and studio.get('name'):
            chip_row(meta_sub, 'STUDIO', [studio], 'tv', 'channels')

        if tags:
            chip_row(meta_sub, 'TAGS', tags, 'tag', 'tags')

        # 2. Below Description Card: List Actors & Actresses as Large, Responsive Flow Cards
        if performers:
            cast_box = tk.Frame(self.preview_info, bg=CONTENT_BG)
            cast_box.pack(fill='x', pady=(0, 14))

            cast_hdr = tk.Frame(cast_box, bg=CONTENT_BG)
            cast_hdr.pack(fill='x', pady=(0, 8))
            self.eyebrow(cast_hdr, f'Starring & Cast ({len(performers)})').pack(side='left')

            cards_wrap = tk.Frame(cast_box, bg=CONTENT_BG)
            cards_wrap.pack(fill='x')

            card_w = 210
            card_h = 290
            gap_x = 16
            gap_y = 16

            card_widgets = []

            for idx, (perf, role_label, kind_key) in enumerate(performers):
                p_name = perf.get('name') or ''
                p_url = perf.get('url') or ''
                p_thumb = perf.get('thumb') or ''
                if not p_name:
                    continue

                is_starred = config.is_in_watchlist(p_name, kind_key)

                init_norm = create_poster_card_img(None, p_name, role=role_label, is_starred=is_starred,
                                                   width=card_w, height=card_h, is_hover=False)
                init_hover = create_poster_card_img(None, p_name, role=role_label, is_starred=is_starred,
                                                    width=card_w, height=card_h, is_hover=True)

                p_card = tk.Label(cards_wrap, image=init_norm, bg=CONTENT_BG,
                                  cursor='hand2', bd=0, highlightthickness=0)
                p_card.image = init_norm
                p_card._norm_photo = init_norm
                p_card._hover_photo = init_hover
                p_card._is_starred = is_starred
                card_widgets.append(p_card)

                self._load_performer_avatar(p_name, p_url, p_thumb, p_card, width=card_w, height=card_h, role=role_label)

                def make_card_handlers(lbl_widget, u_name, u_url, u_kind, u_role, u_thumb):
                    def _on_click(event):
                        # Bottom-right area is the Star button (x: 155..210, y: 235..290)
                        if event.x >= 155 and event.y >= 235:
                            curr_starred = config.is_in_watchlist(u_name, u_kind)
                            if curr_starred:
                                config.remove_watchlist_item(u_name, u_kind)
                                self.show_toast(f'Removed "{u_name}" from Watchlist', icon='star', color=MUTE)
                            else:
                                config.add_watchlist_item({
                                    'name': u_name,
                                    'type': u_kind,
                                    'urls': [u_url] if u_url else [],
                                    'starred_at': time.time()
                                })
                                self.show_toast(f'★ Added "{u_name}" to Watchlist', icon='star', color='#f59e0b')
                            new_starred = config.is_in_watchlist(u_name, u_kind)
                            lbl_widget._is_starred = new_starred
                            raw = getattr(self, '_performer_raw_cache', {}).get(u_name.strip().lower())
                            n_p = create_poster_card_img(raw, u_name, role=u_role, is_starred=new_starred,
                                                         width=card_w, height=card_h, is_hover=True)
                            lbl_widget.configure(image=n_p)
                            lbl_widget.image = n_p
                            lbl_widget._hover_photo = n_p
                            lbl_widget._norm_photo = create_poster_card_img(raw, u_name, role=u_role, is_starred=new_starred,
                                                                            width=card_w, height=card_h, is_hover=False)
                            return 'break'
                        else:
                            if u_url:
                                self._preview_nav(u_url)

                    def _on_enter(_e=None):
                        hp = getattr(lbl_widget, '_hover_photo', None)
                        if hp:
                            lbl_widget.configure(image=hp)

                    def _on_leave(_e=None):
                        np = getattr(lbl_widget, '_norm_photo', None)
                        if np:
                            lbl_widget.configure(image=np)

                    lbl_widget.bind('<Button-1>', _on_click)
                    lbl_widget.bind('<Enter>', _on_enter)
                    lbl_widget.bind('<Leave>', _on_leave)

                make_card_handlers(p_card, p_name, p_url, kind_key, role_label, p_thumb)

            # Responsive Dynamic Flow: cleanly layout cards in grid columns and reflow on resize
            current_cols = [0]

            def _reflow_cast_cards(event=None):
                try:
                    if not cards_wrap.winfo_exists() or not self.preview_info.winfo_exists():
                        return
                except Exception:
                    return
                if event and event.widget not in (cards_wrap, self.preview_info):
                    return
                try:
                    avail_w = cards_wrap.winfo_width()
                    if avail_w <= 20:
                        avail_w = self.preview_info.winfo_width() - 24
                    if avail_w <= 20:
                        avail_w = 800  # Fallback initial width

                    cols = max(1, (avail_w + gap_x) // (card_w + gap_x))
                    if cols == current_cols[0] and bool(card_widgets and card_widgets[0].winfo_ismapped()):
                        return
                    current_cols[0] = cols

                    for c_idx, c_widget in enumerate(card_widgets):
                        row = c_idx // cols
                        col = c_idx % cols
                        c_widget.grid(row=row, column=col, padx=(0, gap_x), pady=(0, gap_y), sticky='nw')
                except tk.TclError:
                    return
                except Exception:
                    return
                try:
                    self.after_idle(self._update_player_vsb)
                except Exception:
                    pass

            cards_wrap.bind('<Configure>', _reflow_cast_cards)
            self.preview_info.bind('<Configure>', _reflow_cast_cards)
            self.after_idle(_reflow_cast_cards)

        self._bind_wheel_recursive(self.preview_info, self._on_player_wheel)
        self._update_player_vsb()

    def _preview_nav(self, url):
        if self.player is not None:
            try:
                if self.player.is_playing():
                    self.player.pause()
            except Exception:
                pass
        self.player_host.grid_remove()
        self.grid_outer.grid()
        if not self.sidebar_wrap.winfo_ismapped():
            self.sidebar_wrap.pack(side='left', fill='y', before=self.content_holder)
        self._show_back_bar(True)
        self.browse_load(base_url=url, reset=True)

    def _exit_preview_nav(self):
        self._show_back_bar(False)
        self.grid_outer.grid_remove()
        self.sidebar_wrap.pack_forget()
        self.player_host.grid(row=0, column=0, sticky='nsew')
        self._player_layout_mode = None
        self.after_idle(self._on_player_host_configure)
        if self.player is not None:
            try:
                if not self.player.is_playing():
                    self.player.play()
            except Exception:
                pass

    def _show_back_bar(self, show):
        if show:
            self.back_bar.pack(side='top', anchor='w', padx=(20, 12), pady=(10, 4),
                               before=self.cards_body)
        else:
            try:
                self.back_bar.pack_forget()
            except Exception:
                pass

    # ---------- recommendations rail & responsive layout ----------
    def _clear_recs(self, msg=None):
        for w in self.recs_inner.winfo_children():
            if w is not self.lbl_recs_empty:
                w.destroy()
        if msg:
            self.lbl_recs_empty.configure(text=msg)
            self.lbl_recs_empty.pack(fill='x', padx=14)
        self.lbl_recs_status.configure(text='')
        self._update_player_vsb()

    def _relayout_recs(self):
        """Relayout recommendation cards depending on current layout mode (side-by-side vs stacked)."""
        if not hasattr(self, 'recs_inner'):
            return
        cards = [w for w in self.recs_inner.winfo_children() if isinstance(w, (RecCard, SponsoredCard))]
        if not cards:
            return

        for card in cards:
            card.grid_forget()

        is_stacked = (getattr(self, '_player_layout_mode', 'side_by_side') == 'stacked')
        canvas_w = (self.player_canvas.winfo_width() if hasattr(self, 'player_canvas') and self.player_canvas.winfo_width() > 100
                    else (self.player_host.winfo_width() if hasattr(self, 'player_host') else 800))

        if is_stacked:
            # Responsive grid when recommendations are placed below the video player
            avail_w = max(200, canvas_w - 60)
            if avail_w >= 1150:
                cols = 4
            elif avail_w >= 820:
                cols = 3
            elif avail_w >= 420:
                cols = 2  # 2 videos per row on medium/decreased screen
            else:
                cols = 1

            for i in range(6):
                self.recs_inner.grid_columnconfigure(i, weight=1 if i < cols else 0, uniform='reccol' if i < cols else '')
            card_title_wrap = max(60, (avail_w // cols) - 28)
            for i, card in enumerate(cards):
                r, c = divmod(i, cols)
                card.grid(row=r, column=c, padx=6, pady=6, sticky='nsew')
                try:
                    card.title_lbl.configure(wraplength=card_title_wrap)
                    card.after_idle(card._render)
                except Exception:
                    pass
        else:
            # Single vertical column when recommendations are in the right sidebar rail
            for i in range(6):
                self.recs_inner.grid_columnconfigure(i, weight=1 if i == 0 else 0, uniform='reccol' if i == 0 else '')
            card_title_wrap = max(60, getattr(self, 'RECS_W', 400) - 32)
            for i, card in enumerate(cards):
                card.grid(row=i, column=0, padx=8, pady=6, sticky='nsew')
                try:
                    card.title_lbl.configure(wraplength=card_title_wrap)
                    card.after_idle(card._render)
                except Exception:
                    pass

    def _fill_recs(self, items):
        self.lbl_recs_empty.pack_forget()
        if not items:
            self.lbl_recs_empty.configure(text='No suggestions found.')
            self.lbl_recs_empty.pack(fill='x', padx=14)
            self.lbl_recs_status.configure(text='')
            self._update_player_vsb()
            return
        self.lbl_recs_status.configure(text=f'{len(items)} videos')
        pending = []

        for it in items:
            card = RecCard(self, self.recs_inner, it)
            self._bind_wheel_recursive(card, self._on_player_wheel)
            url = it.get('thumbnail') or ''
            if not url:
                continue
            cached = self._thumb_cache.get(url)
            if cached is not None:
                card.apply_image(cached)
            else:
                pending.append((card, url))

        self._relayout_recs()

        for card, url in pending:
            self.thumb_pool.submit(self._load_thumb, card, url)

        self._bind_wheel_recursive(self.recs_panel, self._on_player_wheel)
        self._update_player_vsb()

    def _on_player_wheel(self, event):
        if getattr(self, '_fs_active', False):
            return
        if getattr(self, 'player_canvas', None):
            self.player_canvas.yview_scroll(int(-1 * (event.delta / 120) * 3), 'units')

    def _on_recs_wheel(self, event):
        self._on_player_wheel(event)

    def _on_player_canvas_configure(self, event=None):
        if not getattr(self, 'player_canvas', None) or not getattr(self, 'pbody', None):
            return
        if getattr(self, '_fs_active', False):
            return
        w = self.player_canvas.winfo_width()
        if w > 10:
            self.player_canvas.itemconfigure('pbody_win', width=w)
        self._on_player_host_configure()

    def _update_player_vsb(self):
        try:
            if (not getattr(self, 'player_canvas', None)
                    or not getattr(self, 'player_vsb', None)
                    or not getattr(self, 'pbody', None)):
                return
            if not self.player_canvas.winfo_exists() or not self.pbody.winfo_exists():
                return
            self.player_canvas.configure(scrollregion=self.player_canvas.bbox('all'))
            inner_h = self.pbody.winfo_reqheight()
            view_h = self.player_canvas.winfo_height()
            if view_h <= 1:
                return
            if inner_h > view_h:
                if not self.player_vsb.winfo_ismapped():
                    self.player_vsb.pack(side='right', fill='y', before=self.player_canvas)
            elif self.player_vsb.winfo_ismapped():
                self.player_vsb.pack_forget()
        except tk.TclError:
            return
        except Exception:
            return

    def _update_recs_vsb(self):
        self._update_player_vsb()

    def _download_from_player(self):
        item = dict(self._preview_item or {})
        url = self._preview_url or item.get('url')
        if not url:
            return
        item.setdefault('url', url)
        try:
            item.setdefault('title', self.preview_title.cget('text'))
        except Exception:
            pass
        self.download_item(item)

    def _save_from_player(self):
        item = dict(self._preview_item or {})
        url = self._preview_url or item.get('url')
        if not url:
            return
        item.setdefault('url', url)
        try:
            item.setdefault('title', self.preview_title.cget('text'))
        except Exception:
            pass
        title = str(item.get('title') or url)
        was_saved = config.is_video_saved(url)
        if was_saved:
            config.remove_saved_video(url)
            self._update_player_save_button(False)
            self.show_toast(f'Removed "{title[:36]}" from Watch Later', icon='bookmark', color=MUTE)
        else:
            config.add_saved_video(item)
            self._update_player_save_button(True)
            self.show_toast(f'Saved "{title[:36]}" to Watch Later', icon='bookmark', color=LINK)
        self._on_watch_later_updated(url)

    def _update_player_save_button(self, is_saved=None):
        if not hasattr(self, 'lbl_save_info') or not bool(getattr(self, 'lbl_save_info', None).winfo_exists()):
            return
        if is_saved is None:
            url = str(self._preview_url or (self._preview_item or {}).get('url') or '')
            is_saved = config.is_video_saved(url)
        if is_saved:
            ico = get_heroicon('bookmark_solid', size=14, color=LINK)
            self.lbl_save_info.configure(text=' Saved', image=ico, fg=LINK)
            self.lbl_save_info.image = ico
        else:
            ico = get_heroicon('bookmark', size=14, color=PILL_SEC_FG)
            self.lbl_save_info.configure(text=' Save', image=ico, fg=PILL_SEC_FG)
            self.lbl_save_info.image = ico

    # ---------- VLC preview engine & responsive configuration ----------
    def _on_player_host_configure(self, event=None):
        if not getattr(self, 'player_host', None) or not self.player_host.winfo_ismapped():
            return
        if getattr(self, '_fs_active', False):
            return
        host_w = self.player_host.winfo_width()
        host_h = self.player_host.winfo_height()
        if host_w <= 100 or host_h <= 100:
            return

        canvas_w = self.player_canvas.winfo_width()
        if canvas_w <= 100:
            canvas_w = host_w
        if hasattr(self, 'player_vsb') and self.player_vsb.winfo_ismapped():
            canvas_w = max(200, canvas_w)

        # Track maximum observed window / screen width to compute video player 20% area reduction
        ref_max_w = max(getattr(self, '_max_observed_host_w', 0), host_w, self.winfo_screenwidth())
        self._max_observed_host_w = ref_max_w

        # Max potential video player width & area in side-by-side mode on this display
        max_recs_w = max(360, min(480, round(ref_max_w * 0.32)))
        max_side_player_w = max(400, ref_max_w - max_recs_w - 36)
        max_player_area = max_side_player_w * (max_side_player_w * 9 / 16)

        # Current available video player width & area in side-by-side mode
        cur_recs_w = max(360, min(480, round(canvas_w * 0.32)))
        cur_side_player_w = max(100, canvas_w - cur_recs_w - 36)
        cur_player_area = cur_side_player_w * (cur_side_player_w * 9 / 16)

        # 20% area loss condition: video player loses 20% or more of its area
        area_loss = (1.0 - (cur_player_area / max_player_area)) if max_player_area > 0 else 0.0
        is_stacked = (area_loss >= 0.20 or cur_side_player_w < 700 or host_w < 1120)
        cur_mode = getattr(self, '_player_layout_mode', None)

        if is_stacked:
            # Mode: STACKED (Reduced screen size - recommendations move below the player & description)
            if cur_mode != 'stacked':
                self._player_layout_mode = 'stacked'
                self.player_main_col.pack_forget()
                self.recs_panel.pack_forget()

                self.player_main_col.pack(side='top', fill='x', padx=0, pady=0)
                self.recs_panel.pack(side='top', fill='x', padx=(20, 16), pady=(16, 24))
                self.recs_panel.pack_propagate(True)

            self.recs_panel.configure(width=0)
            self.RECS_W = max(200, canvas_w - 40)

            # Stage sizing for stacked mode (exact 16:9 ratio):
            stage_w = max(200, canvas_w - 36)
            stage_h = round(stage_w * 9 / 16)
            self.preview_stage.configure(width=0, height=stage_h)

            self.player_canvas.itemconfigure('pbody_win', width=canvas_w)
            self._relayout_recs()
            self._update_player_vsb()

        else:
            # Mode: SIDE-BY-SIDE (Wide screen - video player on left, recommendations on right, scrolling together)
            recs_w = max(360, min(480, round(canvas_w * 0.32)))
            main_w = max(400, canvas_w - recs_w - 20)

            if cur_mode != 'side_by_side':
                self._player_layout_mode = 'side_by_side'
                self.player_main_col.pack_forget()
                self.recs_panel.pack_forget()

                # Place recommendations on the right and main player on the left inside the unified scroll body
                self.recs_panel.pack(side='right', anchor='n', padx=(0, 16), pady=(12, 16))
                self.recs_panel.pack_propagate(True)
                self.player_main_col.pack(side='left', fill='x', expand=True, anchor='n')

            self.recs_panel.configure(width=recs_w)
            self.RECS_W = recs_w

            # Stage sizing for side-by-side mode (exact 16:9 ratio):
            stage_w = max(200, main_w - 36)
            stage_h = round(stage_w * 9 / 16)
            self.preview_stage.configure(width=0, height=stage_h)

            self.player_canvas.itemconfigure('pbody_win', width=canvas_w)
            self._relayout_recs()
            self._update_player_vsb()

        self._on_stage_configure()
        self._bind_wheel_recursive(self.pbody, self._on_player_wheel)

    def _on_stage_configure(self, event=None):
        if not getattr(self, '_stage_live', False):
            return
        if getattr(self, '_fs_active', False):
            stage_w = self.winfo_width() or self.winfo_screenwidth()
            stage_h = self.winfo_height() or self.winfo_screenheight()
            self.preview_stage.configure(width=stage_w, height=stage_h)
            if hasattr(self, 'player_canvas'):
                try:
                    self.player_canvas.itemconfigure('pbody_win', width=stage_w, height=stage_h)
                except Exception:
                    pass
            if hasattr(self, 'player_main_col'):
                try:
                    self.player_main_col.configure(width=stage_w, height=stage_h)
                except Exception:
                    pass
            self.preview_video.place(x=0, y=0, relwidth=1.0, relheight=1.0)
            return

        w = (event.width if (event and getattr(event, 'width', 0) > 50) else None) or self.preview_stage.winfo_width()
        if w > 50:
            target_h = round(w * 9 / 16)
            try:
                if abs(self.preview_stage.winfo_height() - target_h) > 2:
                    self.preview_stage.configure(height=target_h)
            except Exception:
                pass
        self.preview_video.place(x=0, y=0, relwidth=1.0, relheight=1.0)

    def _show_stage(self, video):
        if video == getattr(self, '_stage_live', False):
            return
        if video:
            self.preview_placeholder.pack_forget()
            self._stage_live = True
            try:
                self.preview_transport.pack_forget()
                self.preview_transport.pack(fill='x', before=self.preview_info, padx=(20, 16), pady=(4, 0))
            except Exception:
                self.preview_transport.pack(fill='x', padx=(20, 16), pady=(4, 0))
            self._on_stage_configure()
            self.after_idle(self._on_stage_configure)
        else:
            self.preview_video.place_forget()
            self.preview_transport.pack_forget()
            self.preview_placeholder.pack(expand=True)
            self._stage_live = False

    def _media_headers(self):
        site = str((self._preview_item or {}).get('site_name') or '')
        page = str(self._preview_url or '')
        headers = {}
        ua = (getattr(config, 'headers', None) or {}).get('User-Agent') or 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
        headers['User-Agent'] = ua
        if site == 'Beeg':
            headers.setdefault('Referer', 'https://beeg.com/')
        elif site == 'OnePorn':
            headers.setdefault('Referer', page or f'https://{OnePornTVBrowser.HOST}/')
        else:
            headers.setdefault('Referer', page or f'https://{FreePornVideosBrowser.HOST}/')
        return headers

    def _start_preview_engine(self, link):
        self._stop_preview_engine()
        self._preview_closing = False
        self._show_stage(video=True)
        headers = self._media_headers()
        ua = headers.get('User-Agent', '')
        ref = headers.get('Referer', '')
        seq = self._preview_seq

        def starter():
            player = None
            try:
                args = ['--no-video-title', '--no-osd',
                        '--network-caching=1500',
                        '--http-reconnect']
                if ref:
                    args.append(f'--http-referrer={ref}')
                if ua:
                    args.append(f'--http-user-agent={ua}')
                inst = vlc.Instance(*args)
                player = inst.media_player_new()
                media = inst.media_new(link)
                if ua:
                    media.add_option(f':http-user-agent={ua}')
                if ref:
                    media.add_option(f':http-referrer={ref}')
                player.set_media(media)
                self.events.put(('preview_vlc_ready', seq, player))
            except Exception as exc:
                print('vlc start failed:', repr(exc))
                if player is not None:
                    try:
                        player.release()
                    except Exception:
                        pass
                self.events.put(('preview_vlc_failed', seq, str(exc)))

        threading.Thread(target=starter, daemon=True).start()

    def _attach_preview_vlc(self, seq, player):
        if (seq != getattr(self, '_preview_seq', -1) or self._preview_closing):
            try:
                player.stop()
                player.release()
            except Exception:
                pass
            return
        self.player = player
        self._on_stage_configure()
        try:
            player.set_hwnd(self.preview_video.winfo_id())
        except Exception as exc:
            print('vlc attach failed:', exc)
        player.audio_set_volume(self._vol)
        player.audio_set_mute(self._muted)
        player.play()
        self.preview_status.configure(text='buffering…', fg=MUTE)
        self._watch_preview()

    def _watch_preview(self):
        p = self.player
        if p is None or self._preview_closing:
            return
        state = str(p.get_state()).split('.')[-1].lower()
        dur = max(p.get_length(), 0)
        cur = max(p.get_time(), 0)
        if dur > 0:
            self.lbl_dur.configure(text=self._fmt_time(dur))
            if not self.seek_bar.is_dragging():
                self.seek_bar.set_frac(min(cur / dur, 1.0))
                self.lbl_cur.configure(text=self._fmt_time(cur))
        if 'playing' in state:
            self.preview_status.configure(text='▶ playing', fg=LINK)
            self.btn_pp.configure(image=get_heroicon('pause', size=24, color=INK))
            if not self._watch_recorded and self._pending_watch_item:
                item = dict(self._pending_watch_item)
                config.add_view_history(item)
                self._watch_recorded = True
                self._render_history()
        elif 'paused' in state:
            self.preview_status.configure(text='⏸ paused', fg=MUTE)
            self.btn_pp.configure(image=get_heroicon('play', size=24, color=INK))
        elif 'ended' in state:
            self.preview_status.configure(text='ended', fg=MUTE)
            self.btn_pp.configure(image=get_heroicon('play', size=24, color=INK))
        elif 'error' in state:
            self.preview_status.configure(text='stream error', fg=ERROR)
        elif 'opening' in state or 'buffering' in state:
            self.preview_status.configure(text='buffering…', fg=MUTE)
        self.after(500, self._watch_preview)

    @staticmethod
    def _fmt_time(ms):
        s = int(max(ms, 0) // 1000)
        return f'{s // 60}:{s % 60:02d}'

    def _stop_preview_engine(self):
        self._preview_closing = True
        self._pending_watch_item = None
        self._watch_recorded = True
        if getattr(self, '_fs_active', False):
            self._exit_fullscreen()
        p, self.player = self.player, None
        if p is not None:
            try:
                p.stop()
            except Exception:
                pass
            try:
                p.release()
            except Exception:
                pass

    def _stop_preview_playback(self):
        self._show_stage(video=False)
        self._stop_preview_engine()

    def preview_toggle_play(self):
        p = self.player
        if p is None:
            return
        try:
            if p.is_playing():
                p.pause()
            else:
                p.play()
        except Exception:
            pass

    def preview_skip(self, seconds):
        p = self.player
        if p is None:
            return
        try:
            dur = max(p.get_length(), 0)
            target = min(max(p.get_time() + seconds * 1000, 0), max(dur - 500, 0))
            p.set_time(target)
        except Exception:
            pass

    def _on_seek_commit(self, frac):
        p = self.player
        if p is None:
            return
        try:
            dur = p.get_length()
            if dur > 0:
                p.set_time(int(frac * dur))
                self.lbl_cur.configure(text=self._fmt_time(int(frac * dur)))
        except Exception:
            pass

    def _on_volume_move(self, value):
        if not hasattr(self, '_muted'):
            return
        try:
            vol = int(float(value))
        except Exception:
            return
        self._vol = vol
        if hasattr(self, 'lbl_vol') and self.lbl_vol.winfo_exists():
            self.lbl_vol.configure(text=f'{vol}%')
        if vol > 0 and self._muted:
            self._muted = False
            if hasattr(self, 'btn_mute') and self.btn_mute.winfo_exists():
                self.btn_mute.configure(image=get_heroicon('speaker_wave', size=24, color=BODY))
        p = self.player
        if p is not None:
            try:
                p.audio_set_mute(False)
                p.audio_set_volume(vol)
            except Exception:
                pass

    def preview_toggle_mute(self):
        self._muted = not self._muted
        if hasattr(self, 'btn_mute') and self.btn_mute.winfo_exists():
            ico = 'speaker_x_mark' if self._muted else 'speaker_wave'
            self.btn_mute.configure(image=get_heroicon(ico, size=24, color=BODY))
        p = self.player
        if p is not None:
            try:
                p.audio_set_mute(self._muted)
            except Exception:
                pass


    def _adjust_volume(self, delta):
        cur = getattr(self, '_vol', 70)
        new_vol = min(max(cur + delta, 0), 100)
        self.vol_scale.set(new_vol)
        self._on_volume_move(new_vol)

    def _seek_to_percent(self, frac):
        p = self.player
        if p is None:
            return
        try:
            dur = p.get_length()
            if dur > 0:
                p.set_time(int(frac * dur))
                self.lbl_cur.configure(text=self._fmt_time(int(frac * dur)))
                self.seek_bar.set_frac(frac)
        except Exception:
            pass

    def _change_rate(self, delta):
        p = self.player
        if p is None:
            return
        try:
            rates = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
            cur = round(float(p.get_rate() or 1.0), 2)
            idx = 3
            closest_diff = 999
            for i, r in enumerate(rates):
                if abs(r - cur) < closest_diff:
                    closest_diff = abs(r - cur)
                    idx = i
            new_idx = min(max(idx + delta, 0), len(rates) - 1)
            new_rate = rates[new_idx]
            p.set_rate(new_rate)
            self.preview_status.configure(text=f'{new_rate}x speed', fg=LINK)
        except Exception:
            pass

    def _on_global_key(self, event):
        focus = self.focus_get()
        if isinstance(focus, (tk.Entry, ttk.Entry, tk.Text, ttk.Combobox, tk.Spinbox, GeistInput, GeistSelect)):
            return

        sym = (event.keysym or '').lower()
        char = getattr(event, 'char', '')
        state = getattr(event, 'state', 0)
        is_shift = bool(state & 0x0001)
        is_ctrl = bool(state & 0x0004)

        if sym == 'f5' or (sym == 'r' and is_ctrl):
            self._win_refresh()
            return 'break'

        is_player_open = getattr(self, '_fs_active', False) or (
            hasattr(self, 'player_host') and self.player_host.winfo_ismapped()
        ) or (self.player is not None)
        if not is_player_open:
            return

        if sym in ('space', 'k'):
            self.preview_toggle_play()
            return 'break'
        elif sym in ('left', 'j'):
            step = -30 if is_shift else (-5 if sym == 'left' else -10)
            self.preview_skip(step)
            return 'break'
        elif sym in ('right', 'l'):
            step = 30 if is_shift else (5 if sym == 'right' else 10)
            self.preview_skip(step)
            return 'break'
        elif sym == 'bracketleft':
            self.preview_skip(-30)
            return 'break'
        elif sym == 'bracketright':
            self.preview_skip(30)
            return 'break'
        elif sym == 'up':
            self._adjust_volume(5)
            return 'break'
        elif sym == 'down':
            self._adjust_volume(-5)
            return 'break'
        elif sym == 'm':
            self.preview_toggle_mute()
            return 'break'
        elif sym == 'f':
            if getattr(self, '_fs_active', False):
                self._exit_fullscreen()
            else:
                self.preview_fullscreen()
            return 'break'
        elif sym == 'escape':
            if getattr(self, '_fs_active', False):
                self._exit_fullscreen()
            else:
                self.close_preview()
            return 'break'
        elif sym == 'home':
            self._seek_to_percent(0.0)
            return 'break'
        elif sym == 'end':
            self._seek_to_percent(0.99)
            return 'break'
        elif (sym == 'greater' or char == '>' or (sym == 'period' and is_shift)):
            self._change_rate(1)
            return 'break'
        elif (sym == 'less' or char == '<' or (sym == 'comma' and is_shift)):
            self._change_rate(-1)
            return 'break'
        elif sym in ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'):
            frac = int(sym) / 10.0
            self._seek_to_percent(frac)
            return 'break'

    def _toggle_fullscreen(self):
        if getattr(self, '_fs_active', False):
            self._exit_fullscreen()
        else:
            self.preview_fullscreen()

    def preview_fullscreen(self):
        p = self.player
        if p is None or getattr(self, '_fs_active', False):
            return
        self._fs_active = True
        self._was_maximized = (self.state() == 'zoomed')

        # 1. Hide chrome surrounding the video stage
        try:
            self.topbar.pack_forget()
        except Exception:
            pass
        try:
            if hasattr(self, 'topbar_divider'):
                self.topbar_divider.pack_forget()
        except Exception:
            pass
        try:
            self.sidebar_wrap.pack_forget()
        except Exception:
            pass
        try:
            self.recs_panel.pack_forget()
        except Exception:
            pass
        try:
            if hasattr(self, 'player_vsb'):
                self.player_vsb.pack_forget()
        except Exception:
            pass
        try:
            self.ph_head.pack_forget()
        except Exception:
            pass
        try:
            self.preview_info.pack_forget()
        except Exception:
            pass

        # 2. Configure container frames for full screen display
        try:
            self.player_canvas.yview_moveto(0)
            self.player_main_col.pack_forget()
            self.player_main_col.pack(fill='both', expand=True, padx=0, pady=0)
            self.preview_stage.pack_forget()
            self.preview_stage.pack(fill='both', expand=True, padx=0, pady=0)
            self.preview_stage.configure(highlightthickness=0)
        except Exception:
            pass

        # 3. Configure backgrounds to pure black for theater mode
        try:
            self.configure(bg='#000000')
            self.main_holder.configure(bg='#000000')
            self.content_holder.configure(bg='#000000')
            self.view_browse.configure(bg='#000000')
            self.player_host.configure(bg='#000000')
            self.player_canvas.configure(bg='#000000')
            self.pbody.configure(bg='#000000')
            self.player_main_col.configure(bg='#000000')
        except Exception:
            pass

        # 4. Enter true fullscreen
        try:
            self.attributes('-fullscreen', True)
        except Exception:
            pass

        # 5. Update transport controls to float at the bottom as Liquid Glass HUD
        try:
            self.preview_transport.pack_forget()
        except Exception:
            pass
        self.preview_transport.place(in_=self.preview_stage, relx=0.5, rely=0.96, anchor='s', relwidth=0.90, height=46)
        self.preview_transport.configure(bg='#101018', highlightthickness=1, highlightbackground='#323246')
        for child in self.preview_transport.winfo_children():
            try:
                child.configure(bg='#101018')
                for gc in child.winfo_children():
                    try:
                        gc.configure(bg='#101018')
                    except Exception:
                        pass
            except Exception:
                pass
        self.preview_transport.lift()

        # 6. Switch button icon to exit fullscreen
        fs_img = get_heroicon('fullscreen_exit', size=24, color='#ffffff')
        self.btn_fs.configure(image=fs_img)
        self.btn_fs.image = fs_img

        # 7. Bind mouse motion for HUD auto-hide (including global cursor polling for HWND video overlays)
        self._fs_hud_visible = True
        self._fs_last_mouse_pos = None
        self.bind('<Motion>', self._on_fs_mouse_motion)
        self.preview_stage.bind('<Motion>', self._on_fs_mouse_motion)
        self.preview_video.bind('<Motion>', self._on_fs_mouse_motion)
        self.preview_transport.bind('<Motion>', self._on_fs_mouse_motion)
        self._poll_fs_mouse()
        self._schedule_fs_hud_hide()

        self._on_stage_configure()
        self.after(50, self._on_stage_configure)
        self.after(150, self._on_stage_configure)

    def _poll_fs_mouse(self):
        if not getattr(self, '_fs_active', False):
            return
        try:
            cur_pos = self.winfo_pointerxy()
            if getattr(self, '_fs_last_mouse_pos', None) is None:
                self._fs_last_mouse_pos = cur_pos
            elif cur_pos != self._fs_last_mouse_pos:
                self._fs_last_mouse_pos = cur_pos
                self._on_fs_mouse_motion()
        except Exception:
            pass
        if getattr(self, '_fs_active', False):
            self._fs_mouse_timer = self.after(100, self._poll_fs_mouse)

    def _schedule_fs_hud_hide(self):
        if getattr(self, '_fs_hud_timer', None):
            try:
                self.after_cancel(self._fs_hud_timer)
            except Exception:
                pass
            self._fs_hud_timer = None
        if getattr(self, '_fs_active', False):
            self._fs_hud_timer = self.after(3500, self._hide_fs_hud)

    def _hide_fs_hud(self):
        if not getattr(self, '_fs_active', False):
            return
        self._fs_hud_visible = False
        try:
            self.preview_transport.place_forget()
            self.config(cursor='none')
            self.preview_stage.config(cursor='none')
            self.preview_video.config(cursor='none')
        except Exception:
            pass

    def _on_fs_mouse_motion(self, event=None):
        if not getattr(self, '_fs_active', False):
            return
        if not getattr(self, '_fs_hud_visible', False):
            self._fs_hud_visible = True
            try:
                self.config(cursor='')
                self.preview_stage.config(cursor='')
                self.preview_video.config(cursor='')
                self.preview_transport.place(in_=self.preview_stage, relx=0.5, rely=0.96, anchor='s', relwidth=0.90, height=46)
                self.preview_transport.lift()
            except Exception:
                pass
        self._schedule_fs_hud_hide()

    def _exit_fullscreen(self):
        if not getattr(self, '_fs_active', False):
            return
        self._fs_active = False

        # Cancel HUD & mouse poll timers & restore cursor
        if getattr(self, '_fs_mouse_timer', None):
            try:
                self.after_cancel(self._fs_mouse_timer)
            except Exception:
                pass
            self._fs_mouse_timer = None
        if getattr(self, '_fs_hud_timer', None):
            try:
                self.after_cancel(self._fs_hud_timer)
            except Exception:
                pass
            self._fs_hud_timer = None
        self.config(cursor='')
        self.preview_stage.config(cursor='')
        self.preview_video.config(cursor='')

        # Unbind fullscreen motion listeners
        try:
            self.unbind('<Motion>')
            self.preview_stage.unbind('<Motion>')
            self.preview_video.unbind('<Motion>')
            self.preview_transport.unbind('<Motion>')
        except Exception:
            pass

        # 1. Exit OS Fullscreen
        try:
            self.attributes('-fullscreen', False)
        except Exception:
            pass
        if getattr(self, '_was_maximized', False):
            try:
                self.state('zoomed')
            except Exception:
                pass
        self._apply_borderless_chrome()
        self.after(50, self._apply_borderless_chrome)
        self.after(150, self._apply_borderless_chrome)

        # 2. Restore theme backgrounds
        try:
            self.configure(bg=WINDOW_BG)
            self.main_holder.configure(bg=CONTENT_BG)
            self.content_holder.configure(bg=CONTENT_BG)
            self.view_browse.configure(bg=CONTENT_BG)
            self.player_host.configure(bg=CONTENT_BG)
            self.player_canvas.configure(bg=CONTENT_BG)
            self.pbody.configure(bg=CONTENT_BG)
            self.player_main_col.configure(bg=CONTENT_BG, width=0, height=0)
        except Exception:
            pass

        # 3. Restore topbar (sidebar remains hidden while player is open)
        try:
            self.topbar.pack(side='top', fill='x', before=self.main_holder)
        except Exception:
            pass
        try:
            if hasattr(self, 'topbar_divider'):
                self.topbar_divider.pack(side='top', fill='x', before=self.main_holder)
        except Exception:
            pass

        # 4. Restore pbody / player_main_col contents sequentially
        try:
            self.ph_head.pack_forget()
            self.preview_stage.pack_forget()
            self.preview_transport.place_forget()
            self.preview_transport.pack_forget()
            self.preview_info.pack_forget()

            self.ph_head.pack(in_=self.player_main_col, fill='x', padx=(20, 16), pady=(12, 0))
            self.preview_stage.pack(in_=self.player_main_col, fill='x', pady=(10, 4), padx=(20, 16))
            self.preview_stage.configure(width=0, highlightthickness=1, highlightbackground=CARD_BORDER)

            self.preview_transport.pack(in_=self.player_main_col, fill='x', padx=(20, 16), pady=(4, 0))
            self.preview_transport.configure(bg=CONTENT_BG, highlightthickness=0)
            for child in self.preview_transport.winfo_children():
                try:
                    child.configure(bg=CONTENT_BG)
                    for gc in child.winfo_children():
                        try:
                            gc.configure(bg=CONTENT_BG)
                        except Exception:
                            pass
                except Exception:
                    pass

            self.preview_info.pack(in_=self.player_main_col, fill='x', pady=(10, 0), padx=(20, 16))
        except Exception as exc:
            print('pbody restore error:', exc)

        # 5. Restore fullscreen button icon
        fs_img = get_heroicon('fullscreen', size=24, color=BODY)
        self.btn_fs.configure(image=fs_img)
        self.btn_fs.image = fs_img

        # 6. Reset canvas window height override and trigger layout calculations
        if hasattr(self, 'player_canvas'):
            try:
                self.player_canvas.itemconfigure('pbody_win', height=0)
            except Exception:
                pass
        self._player_layout_mode = None
        self._on_player_host_configure()
        self.after(50, self._on_player_host_configure)
        self.after(150, self._on_player_host_configure)

    def close_preview(self):
        if getattr(self, '_fs_active', False):
            self._exit_fullscreen()
        self._preview_seq = getattr(self, '_preview_seq', 0) + 1
        self._show_back_bar(False)
        if getattr(self, '_overlay_timer', None):
            try:
                self.after_cancel(self._overlay_timer)
            except Exception:
                pass
            self._overlay_timer = None
        self._stop_preview_playback()
        try:
            self.player_host.grid_remove()
        except Exception:
            pass
        self.preview_title.configure(text='')
        self.preview_status.configure(text='')
        self.grid_outer.grid()
        if not self.sidebar_wrap.winfo_ismapped():
            self.sidebar_wrap.pack(side='left', fill='y', before=self.content_holder)

    def _resolve_row(self, row):
        if row.cancelled:
            return
        self.events.put(('state', row, 'resolving', 'resolving\u2026'))
        cls = row.site_cls
        try:
            crawler = cls(row.url, savepath=getattr(row, 'save_dir', os.path.abspath('.')), silence=True)
        except Exception:
            crawler = None
        if crawler is None:
            try:
                crawler = cls(row.url, savepath=getattr(row, 'save_dir', ''), silence=True)
                if not crawler.is_url_vaildate():
                    crawler = None
            except Exception:
                crawler = None
        if row.cancelled:
            return
        if crawler is None or not crawler.is_url_vaildate():
            reason = getattr(crawler, '_last_error', None)
            self.events.put((
                'resolve_failed', row,
                'no stream found' + (f' ({reason})' if reason else '')))
            return
        row.crawler = crawler
        self.events.put(('ready', row))
        self._probe_stream(row)

    def _probe_stream(self, row):
        cr = row.crawler
        link = getattr(cr, '_direct_url', None)
        if not link:
            return
        try:
            import requests
            resp = requests.get(
                link, timeout=(10, 15), stream=True,
                headers={'Referer': getattr(cr, '_direct_referer', cr._url or ''),
                         'Range': 'bytes=0-31'})
            chunk = next(resp.iter_content(32), b'')
            resp.close()
            if chunk[:5] == b'error':
                row.stream_blocked = True
                self.events.put((
                    'probe', row,
                    'ready \u00b7 site refuses this link off-browser'))
        except Exception:
            pass

    def _download_row(self, row, save_dir):
        cr = row.crawler
        if cr is None:
            row.state = 'error'
            return
        if row.cancelled:
            row.state = 'cancelled'
            return

        def progress(done_bytes, total_bytes, speed):
            pct = (done_bytes * 100.0 / total_bytes) if total_bytes else 0
            if speed:
                eta = int((total_bytes - done_bytes) / speed) if total_bytes else 0
                txt = (f'{fmt_bytes(done_bytes)} / {fmt_bytes(total_bytes)} \u00b7 '
                       f'{fmt_bytes(speed)}/s \u00b7 eta {eta // 60}:{eta % 60:02d}')
            else:
                txt = f'{fmt_bytes(done_bytes)} / {fmt_bytes(total_bytes or 0)}'
            self.events.put(('progress', row, pct, txt))

        cr._progress_callback = progress
        try:
            ok = cr.start_download()
            if row.cancelled:
                self.events.put(('state', row, 'cancelled', 'cancelled'))
                return
            if not ok:
                self.events.put(('state', row, 'cancelled', 'cancelled'))
                return
            out_path = None
            try:
                out_path = cr._get_video_savename()
            except Exception:
                out_path = None
            if out_path and os.path.exists(out_path) and os.path.getsize(out_path) < 50_000:
                self.events.put((
                    'state', row, 'blocked',
                    'site refused the stream (error page saved instead)'))
                return
            self.events.put(('state', row, 'done', 'done'))
            title = ''
            try:
                title = str(cr.target_name() or '')
            except Exception:
                title = ''
            self.events.put(('download_done', row, out_path or '', title))
        except Exception as exc:
            self.events.put(('state', row, 'error', f'failed: {exc}'))

    # ---------- browse data loaders ----------
    def _beeg_browser(self):
        if getattr(self, '_beeg_browser_obj', None) is None:
            self._beeg_browser_obj = BeegBrowser()
        return self._beeg_browser_obj

    def _kvs_browser_for_url(self, url):
        u = (url or '').lower()
        if '1porn.tv' in u:
            if getattr(self, '_oneporn_browser_obj', None) is None:
                self._oneporn_browser_obj = OnePornTVBrowser()
            return self._oneporn_browser_obj
        if getattr(self, '_fpv_browser_obj', None) is None:
            self._fpv_browser_obj = FreePornVideosBrowser()
        return self._fpv_browser_obj

    def _is_item_enabled(self, item):
        if not item:
            return False
        enabled = set(config.get_enabled_sources())
        site = (item.get('site_name') or '').strip()
        url = (item.get('url') or '').lower()

        if 'freepornvideos' in url or site in ('FreePornVideos', 'FPV'):
            return 'FreePornVideos' in enabled
        if '1porn.tv' in url or site == 'OnePorn':
            return 'OnePorn' in enabled
        if 'beeg.com' in url or 'beeg:' in url or site == 'Beeg':
            return 'Beeg' in enabled
        return True

    def _is_url_enabled(self, url):
        if not url:
            return False
        enabled = set(config.get_enabled_sources())
        u = str(url).lower()
        if 'freepornvideos' in u:
            return 'FreePornVideos' in enabled
        if '1porn.tv' in u:
            return 'OnePorn' in enabled
        if 'beeg.com' in u or 'beeg:' in u:
            return 'Beeg' in enabled
        return True

    def _purge_disabled_cards(self):
        """Immediately destroy and remove any cards from disabled sources."""
        kept = []
        for card in list(self._cards):
            if not self._is_item_enabled(card.item):
                try:
                    card.destroy()
                except Exception:
                    pass
            else:
                kept.append(card)
        self._cards = kept
        self._relayout_cards()

    def _active_feed_sites(self):
        enabled = set(config.get_enabled_sources())
        active = [(k, u) for k, u in FEED_SITES if k in enabled]
        if not active:
            active = [FEED_SITES[0]]
        return active

    def _on_sources_changed(self):
        """Triggered whenever a source toggle is switched in Settings."""
        enabled = config.get_enabled_sources()
        self.say(f"Active sources updated: {', '.join(enabled)}")
        self._purge_disabled_cards()
        if hasattr(self, 'sidebar'):
            try:
                self.sidebar.reload_all()
            except Exception:
                pass
        if getattr(self, '_feed_mode', False):
            self.browse_home()
        elif hasattr(self, 'current_base') and self.current_base:
            self.browse_load(self.current_base, reset=True)

    def browse_home(self):
        self.browse_load(None, reset=True)

    @staticmethod
    def _clean_wl_url_name(raw):
        """If a stored name is really a listing URL, return a clean human name."""
        s = str(raw or '').strip()
        if '://' not in s and not s.lower().startswith('http'):
            return s
        m = re.search(r'/(?:models|sites|actors|tags|categories)/([a-z0-9-]+)/?$',
                      s.lower())
        if m:
            return re.sub(r'[-_]+', ' ', m.group(1)).strip().title()
        return s

    def _repair_watchlist_names(self):
        """Repair older entries that stored the listing URL as the item name."""
        try:
            wl = config.get_watchlist()
        except Exception:
            return
        if not isinstance(wl, list):
            return
        changed = False
        for it in wl:
            if not isinstance(it, dict):
                continue
            raw = str(it.get('name') or '').strip()
            clean = self._clean_wl_url_name(raw)
            if clean != raw:
                it['name'] = clean
                changed = True
        if changed:
            try:
                config.set_watchlist(wl)
            except Exception:
                pass

    def browse_watchlist(self):
        """Displays new releases from all starred actresses, actors, studios, and tags."""
        self.switch_tab('browse')
        if hasattr(self, 'sidebar'):
            self.sidebar.set_active('watchlist')

        watchlist = config.get_watchlist()
        if not watchlist:
            self._browse_seq += 1
            self.current_base = None
            self._feed_mode = False
            self._multi_urls = []
            self._multi_label = 'Watchlist'
            self._seen_urls = set()
            self._dup_cards = {}
            self._no_more = True
            self._clear_cards()
            self.lbl_cards_empty.configure(
                text='★  Your Watchlist is empty\n\n'
                     'Star your favourite actresses, studios, actors, or tags\n'
                     'from the sidebar lists or any video description to see their new releases here!',
                fg=MUTE
            )
    def _render_watchlist_header_bar(self, active_cat=None, active_item=None):
        for w in self.watchlist_bar.winfo_children():
            w.destroy()

        watchlist = config.get_watchlist()
        if not watchlist:
            return

        if active_cat is not None:
            self._watchlist_active_cat = active_cat
        if active_item is not None:
            self._watchlist_active_item = active_item

        cur_cat = getattr(self, '_watchlist_active_cat', 'all')
        cur_item = getattr(self, '_watchlist_active_item', None)

        # Separate items by category
        women_items = []
        men_items = []
        studio_items = []
        tag_items = []

        for it in watchlist:
            if not isinstance(it, dict):
                continue
            cat = config._norm_wl_type(it.get('type'))
            if cat in ('models', 'actress'):
                women_items.append(it)
            elif cat in ('actors', 'actor'):
                men_items.append(it)
            elif cat in ('channels', 'studio'):
                studio_items.append(it)
            else:
                tag_items.append(it)

        is_dark = (get_effective_theme() == 'dark')
        self.watchlist_bar.configure(bg=CONTENT_BG)

        cap_bg = '#0f121d' if is_dark else '#ffffff'
        cap_bd = '#22283d' if is_dark else '#e2e8f0'
        div_col = '#282f45' if is_dark else '#e2e8f0'
        hover_bg = '#1c2336' if is_dark else '#f1f5f9'

        # Outer Liquid Glass Container Capsule
        glass_capsule = tk.Frame(self.watchlist_bar, bg=cap_bg, highlightthickness=1,
                                 highlightbackground=cap_bd)
        glass_capsule.pack(fill='x', padx=14, pady=(8, 4))

        # ───────── 1. Left Side: Category Pills with Liquid Glass Colors ─────────
        left_fr = tk.Frame(glass_capsule, bg=cap_bg)
        left_fr.pack(side='left', padx=(6, 4), pady=3)

        if is_dark:
            categories_def = [
                ('all', f'All ({len(watchlist)})', '#6366f1', '#1a1d2e', '#2c3350', '#e2e8f0'),
                ('models', f'Women ({len(women_items)})', '#ec4899', '#24101d', '#4d1c3a', '#f472b6'),
                ('actors', f'Men ({len(men_items)})', '#3b82f6', '#0f1c33', '#1d3866', '#60a5fa'),
                ('channels', f'Studio ({len(studio_items)})', '#f59e0b', '#241a08', '#4d370e', '#fbbf24'),
                ('tags', f'Tags ({len(tag_items)})', '#b45309', '#22140a', '#472914', '#f59e0b'),
            ]
        else:
            categories_def = [
                ('all', f'All ({len(watchlist)})', '#4f46e5', '#f1f5f9', '#cbd5e1', '#334155'),
                ('models', f'Women ({len(women_items)})', '#db2777', '#fdf2f8', '#fbcfe8', '#db2777'),
                ('actors', f'Men ({len(men_items)})', '#2563eb', '#eff6ff', '#bfdbfe', '#2563eb'),
                ('channels', f'Studio ({len(studio_items)})', '#d97706', '#fffbeb', '#fde68a', '#d97706'),
                ('tags', f'Tags ({len(tag_items)})', '#92400e', '#fef3c7', '#fed7aa', '#92400e'),
            ]

        for cat_key, cat_label, pri_col, idle_bg, idle_bd, idle_fg in categories_def:
            is_active = (cur_cat == cat_key and cur_item is None)

            c_bg = pri_col if is_active else idle_bg
            c_bd = pri_col if is_active else idle_bd
            c_fg = '#ffffff' if is_active else idle_fg

            pill = tk.Frame(left_fr, bg=c_bg, highlightthickness=1,
                            highlightbackground=c_bd, cursor='hand2')
            pill.pack(side='left', padx=3, pady=0)

            lbl = tk.Label(pill, text=cat_label, bg=c_bg, fg=c_fg,
                           font=self.font_sans(9, bold=True), cursor='hand2',
                           padx=8, pady=3)
            lbl.pack()

            def make_cat_handlers(p_frame, p_lbl, k_key, p_pri, p_ibg, p_ibd, p_ifg):
                def _on_click(_e=None):
                    self._watchlist_active_cat = k_key
                    self._watchlist_active_item = None
                    self.browse_watchlist(cat_filter=k_key)

                def _on_enter(_e=None):
                    if not (self._watchlist_active_cat == k_key and self._watchlist_active_item is None):
                        p_frame.configure(highlightbackground=p_pri)
                        p_lbl.configure(fg='#ffffff' if is_dark else p_pri)

                def _on_leave(_e=None):
                    if not (self._watchlist_active_cat == k_key and self._watchlist_active_item is None):
                        p_frame.configure(highlightbackground=p_ibd)
                        p_lbl.configure(fg=p_ifg)

                for w in (p_frame, p_lbl):
                    w.bind('<Button-1>', _on_click)
                    w.bind('<Enter>', _on_enter)
                    w.bind('<Leave>', _on_leave)

            make_cat_handlers(pill, lbl, cat_key, pri_col, idle_bg, idle_bd, idle_fg)

        # ───────── 2. Vertical Line Divider ─────────
        div = tk.Frame(glass_capsule, bg=div_col, width=1)
        div.pack(side='left', fill='y', padx=8, pady=3)

        # ───────── 3. Right Side: Starred Entity Chips with Outline Glass Effect ─────────
        if cur_cat == 'models':
            visible_items = women_items
        elif cur_cat == 'actors':
            visible_items = men_items
        elif cur_cat == 'channels':
            visible_items = studio_items
        elif cur_cat == 'tags':
            visible_items = tag_items
        else:
            visible_items = watchlist

        right_canvas = tk.Canvas(glass_capsule, bg=cap_bg, bd=0, highlightthickness=0, height=37)
        right_canvas.pack(side='left', fill='x', expand=True, padx=(2, 6), pady=3)

        chips_fr = tk.Frame(right_canvas, bg=cap_bg)
        chips_win = right_canvas.create_window((0, 0), window=chips_fr, anchor='nw')

        def _on_chips_configure(_e=None):
            h = max(37, chips_fr.winfo_reqheight())
            right_canvas.configure(height=h, scrollregion=right_canvas.bbox('all'))
        chips_fr.bind('<Configure>', _on_chips_configure)

        def _on_chips_wheel(event):
            delta = -1 if event.delta < 0 else 1
            right_canvas.xview_scroll(-1 * delta, 'units')
            return 'break'
        right_canvas.bind('<MouseWheel>', _on_chips_wheel)
        chips_fr.bind('<MouseWheel>', _on_chips_wheel)

        if not visible_items:
            tk.Label(chips_fr, text='No starred items in this category', bg=cap_bg, fg=MUTE,
                     font=self.font_sans(9)).pack(side='left', padx=6, pady=3)
        else:
            for it in visible_items:
                name = (it.get('name') or '').strip()
                if not name:
                    continue
                cat = config._norm_wl_type(it.get('type'))

                # Outline glass styling based on entity type:
                # - Men/Actors: Blue outline glass
                # - Women/Models: Pink outline glass
                # - Studio: Yellow/Gold outline glass
                # - Tags: Brown/Ochre outline glass
                if is_dark:
                    if cat in ('actors', 'actor'):
                        g_bd = '#3b82f6'
                        g_bg = '#0e1d38'
                        g_fg = '#93c5fd'
                        g_star = '#60a5fa'
                    elif cat in ('models', 'model', 'actress'):
                        g_bd = '#ec4899'
                        g_bg = '#2b1021'
                        g_fg = '#f9a8d4'
                        g_star = '#f472b6'
                    elif cat in ('channels', 'studio', 'sites'):
                        g_bd = '#f59e0b'
                        g_bg = '#261b07'
                        g_fg = '#fde68a'
                        g_star = '#fbbf24'
                    else:  # tags
                        g_bd = '#b45309'
                        g_bg = '#22140a'
                        g_fg = '#fed7aa'
                        g_star = '#d97706'
                else:
                    if cat in ('actors', 'actor'):
                        g_bd = '#93c5fd'
                        g_bg = '#eff6ff'
                        g_fg = '#1d4ed8'
                        g_star = '#2563eb'
                    elif cat in ('models', 'model', 'actress'):
                        g_bd = '#f9a8d4'
                        g_bg = '#fdf2f8'
                        g_fg = '#be185d'
                        g_star = '#db2777'
                    elif cat in ('channels', 'studio', 'sites'):
                        g_bd = '#fde68a'
                        g_bg = '#fffbeb'
                        g_fg = '#b45309'
                        g_star = '#d97706'
                    else:  # tags
                        g_bd = '#fed7aa'
                        g_bg = '#fef3c7'
                        g_fg = '#78350f'
                        g_star = '#92400e'

                is_this_item_active = (cur_item == name)
                if is_this_item_active:
                    g_bg = g_bd
                    g_fg = '#ffffff'
                    g_star = '#ffffff'

                chip = tk.Frame(chips_fr, bg=g_bg, highlightthickness=1,
                                highlightbackground=g_bd, cursor='hand2')
                chip.pack(side='left', padx=3, pady=0)

                lbl_s = tk.Label(chip, text='★', bg=g_bg, fg=g_star,
                                 font=self.font_sans(9, bold=True), cursor='hand2', padx=5, pady=3)
                lbl_s.pack(side='left')

                display_name = f'#{name}' if cat in ('tags', 'tag') else name
                lbl_n = tk.Label(chip, text=display_name, bg=g_bg, fg=g_fg,
                                 font=self.font_sans(9, bold=True), cursor='hand2', padx=3, pady=3)
                lbl_n.pack(side='left', padx=(0, 4))

                def make_chip_handlers(c_frame, c_lbl_s, c_lbl_n, u_item, u_name, u_cat, bd_col, bg_col, fg_col, star_col):
                    def _on_chip_click(_e=None):
                        self._watchlist_active_item = u_name
                        self.browse_watchlist(single_item=u_item)

                    def _on_chip_star_click(_e=None):
                        config.remove_watchlist_item(u_name, u_cat)
                        self.show_toast(f'Removed "{u_name}" from Watchlist', icon='star', color=MUTE)
                        self.browse_watchlist(cat_filter=self._watchlist_active_cat)
                        return 'break'

                    def _on_chip_enter(_e=None):
                        c_frame.configure(bg=hover_bg)
                        c_lbl_s.configure(bg=hover_bg)
                        c_lbl_n.configure(bg=hover_bg, fg=INK if not is_dark else '#ffffff')

                    def _on_chip_leave(_e=None):
                        if self._watchlist_active_item == u_name:
                            c_frame.configure(bg=bd_col)
                            c_lbl_s.configure(bg=bd_col, fg='#ffffff')
                            c_lbl_n.configure(bg=bd_col, fg='#ffffff')
                        else:
                            c_frame.configure(bg=bg_col)
                            c_lbl_s.configure(bg=bg_col, fg=star_col)
                            c_lbl_n.configure(bg=bg_col, fg=fg_col)

                    c_lbl_s.bind('<Button-1>', _on_chip_star_click)
                    c_lbl_n.bind('<Button-1>', _on_chip_click)
                    c_frame.bind('<Button-1>', _on_chip_click)

                    for w in (c_frame, c_lbl_s, c_lbl_n):
                        w.bind('<Enter>', _on_chip_enter)
                        w.bind('<Leave>', _on_chip_leave)
                        w.bind('<MouseWheel>', _on_chips_wheel)

                make_chip_handlers(chip, lbl_s, lbl_n, it, name, cat, g_bd, g_bg, g_fg, g_star)

    def browse_watchlist(self, cat_filter=None, single_item=None):
        """Displays new releases from starred entities with horizontal liquid glass category bar."""
        self.switch_tab('browse')
        if hasattr(self, 'sidebar'):
            self.sidebar.set_active('watchlist')

        self._repair_watchlist_names()

        watchlist = config.get_watchlist()
        if not watchlist:
            if hasattr(self, 'watchlist_bar'):
                self.watchlist_bar.pack_forget()
            self._browse_seq += 1
            self.current_base = None
            self._feed_mode = False
            self._multi_urls = []
            self._multi_label = 'Watchlist'
            self._seen_urls = set()
            self._dup_cards = {}
            self._no_more = True
            self._clear_cards()
            self.lbl_cards_empty.configure(
                text='★  Your Watchlist is empty\n\n'
                     'Star your favourite actresses, studios, actors, or tags\n'
                     'from the sidebar lists or any video description to see their new releases here!',
                fg=MUTE
            )
            self.lbl_cards_empty.grid(row=0, column=0, columnspan=max(1, getattr(self, '_card_cols', 3)), sticky='nsew')
            self.say('Watchlist: No items starred')
            return

        active_cat = cat_filter or getattr(self, '_watchlist_active_cat', 'all')
        active_name = (single_item.get('name') if isinstance(single_item, dict) else single_item) if single_item else (None if cat_filter else getattr(self, '_watchlist_active_item', None))
        self._watchlist_active_cat = active_cat
        self._watchlist_active_item = active_name

        if hasattr(self, 'watchlist_bar'):
            self.watchlist_bar.pack(side='top', fill='x', before=self.cards_body)
            self._render_watchlist_header_bar(active_cat=active_cat, active_item=active_name)

        # Filter items to fetch
        if single_item:
            target_items = [single_item]
        elif active_cat and active_cat != 'all':
            target_items = [it for it in watchlist if isinstance(it, dict) and config._norm_wl_type(it.get('type')) == active_cat]
        else:
            target_items = [it for it in watchlist if isinstance(it, dict)]

        if not target_items:
            self._browse_seq += 1
            self.current_base = None
            self._feed_mode = False
            self._multi_urls = []
            self._multi_label = 'Watchlist'
            self._seen_urls = set()
            self._dup_cards = {}
            self._no_more = True
            self._clear_cards()
            self.lbl_cards_empty.configure(
                text='No starred items found in this category.\n\nStar more items to see their latest videos!',
                fg=MUTE
            )
            self.lbl_cards_empty.grid(row=0, column=0, columnspan=max(1, getattr(self, '_card_cols', 3)), sticky='nsew')
            self.say('Watchlist: No items in this category')
            return

        enabled = set(config.get_enabled_sources())
        all_pairs = []
        names_list = []

        for it in target_items:
            name = (it.get('name') or '').strip()
            if not name:
                continue
            names_list.append(name)

            stored_urls = it.get('urls') or ([it.get('url')] if it.get('url') else [])
            valid_stored = []
            for u in stored_urls:
                if 'freepornvideos' in u and 'FreePornVideos' in enabled:
                    valid_stored.append(u)
                elif '1porn' in u and 'OnePorn' in enabled:
                    valid_stored.append(u)
                elif not enabled:
                    valid_stored.append(u)

            if valid_stored:
                for u in valid_stored:
                    all_pairs.append((u, name))
            else:
                slug = re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')
                itype = (it.get('type') or 'models').lower()

                if itype in ('models', 'model', 'actress', 'actresses'):
                    if 'FreePornVideos' in enabled or not enabled:
                        all_pairs.append((f'https://www.freepornvideos.xxx/models/{slug}/', name))
                    if 'OnePorn' in enabled or not enabled:
                        all_pairs.append((f'https://www.1porn.tv/models/{slug}/', name))
                elif itype in ('channels', 'channel', 'studio', 'studios', 'sites'):
                    if 'FreePornVideos' in enabled or not enabled:
                        all_pairs.append((f'https://www.freepornvideos.xxx/sites/{slug}/', name))
                    if 'OnePorn' in enabled or not enabled:
                        all_pairs.append((f'https://www.1porn.tv/sites/{slug}/', name))
                elif itype in ('actors', 'actor'):
                    # The KVS sites have no /actors/ route; male performers are
                    # listed under /models/<slug>/ (same as actresses).
                    if 'FreePornVideos' in enabled or not enabled:
                        all_pairs.append((f'https://www.freepornvideos.xxx/models/{slug}/', name))
                    if 'OnePorn' in enabled or not enabled:
                        all_pairs.append((f'https://www.1porn.tv/models/{slug}/', name))
                else:  # tags
                    if 'FreePornVideos' in enabled or not enabled:
                        all_pairs.append((f'https://www.freepornvideos.xxx/tags/{slug}/', name))
                    if 'OnePorn' in enabled or not enabled:
                        all_pairs.append((f'https://www.1porn.tv/tags/{slug}/', name))

        seen = set()
        dedup_urls = []
        self._watchlist_verify = {}
        for u, name in all_pairs:
            if u not in seen:
                seen.add(u)
                dedup_urls.append(u)
                self._watchlist_verify[u] = name

        label_summary = f"Watchlist: {', '.join(names_list[:3])}" if names_list else 'Watchlist'
        if len(names_list) > 3:
            label_summary += f" (+{len(names_list) - 3} more)"

        self.browse_load({'name': label_summary, 'urls': dedup_urls,
                          'verify': dict(self._watchlist_verify)}, reset=True)
        self.say('Watchlist: Showing new releases from starred items')

    def browse_shuffle(self):
        import random
        candidates = []
        enabled = set(config.get_enabled_sources())
        if 'FreePornVideos' in enabled:
            candidates.extend([
                'https://www.freepornvideos.xxx/latest-updates/',
                'https://www.freepornvideos.xxx/most-popular/',
                'https://www.freepornvideos.xxx/most-popular/month/',
            ])
        if 'OnePorn' in enabled:
            candidates.extend([
                'https://www.1porn.tv/latest-updates/',
                'https://www.1porn.tv/most-popular/',
                'https://www.1porn.tv/most-popular/month/',
            ])
        if not candidates:
            candidates = ['https://www.freepornvideos.xxx/latest-updates/']
        chosen = random.sample(candidates, k=min(2, len(candidates)))
        self.browse_load({'name': 'Shuffle', 'urls': chosen}, reset=True)
        for u in chosen:
            self._multi_pages[u] = random.randint(1, 10)
        self.say('Browsing: Shuffle (active sources)')

    def browse_load(self, base_url=None, reset=False):
        if reset:
            self._browse_seq += 1
            self.current_base = base_url
            self._feed_mode = base_url is None
            self.page = 1
            self._feed_pages = {key: 1 for key, _u in self._active_feed_sites()}
            if isinstance(base_url, dict):
                self._multi_urls = list(base_url.get('urls') or [])
                self._fallback_urls = list(base_url.get('fallback_urls') or [])
                self._search_suggestion = base_url.get('suggestion')
                self._multi_label = f"tag: {base_url.get('name', '')}"
                self._watchlist_verify = dict(base_url.get('verify') or {})
            else:
                self._multi_urls = []
                self._fallback_urls = []
                self._search_suggestion = None
                self._multi_label = ''
                self._watchlist_verify = {}

            # Hide watchlist bar if navigating away from Watchlist
            is_watchlist = False
            if hasattr(self, 'sidebar') and getattr(self.sidebar, '_active_key', '') == 'watchlist':
                is_watchlist = True
            elif isinstance(base_url, dict) and str(base_url.get('name', '')).startswith('Watchlist'):
                is_watchlist = True
            if not is_watchlist and hasattr(self, 'watchlist_bar'):
                self.watchlist_bar.pack_forget()

            self._multi_pages = {u: 1 for u in self._multi_urls}
            self._seen_urls = set()
            self._dup_cards = {}
            self._no_more = False
            self._load_got_any = False
            self._clear_cards()
        self._start_browse_fetch(reset)

    def _start_browse_fetch(self, reset):
        if self._no_more or self._browse_loading:
            return
        if self.browse_thread and self.browse_thread.is_alive():
            return
        seq = self._browse_seq
        page = self.page
        base = self.current_base
        feed = self._feed_mode
        pages = dict(self._feed_pages)
        multi_urls = list(self._multi_urls)
        fallback_urls = list(getattr(self, '_fallback_urls', []))
        multi_pages = dict(self._multi_pages)
        multi_label = self._multi_label
        wv = dict(self._watchlist_verify or {})
        self._browse_loading = True

        def worker():
            errs = []
            label = ''

            def emit(it, er, fin):
                self.events.put(('browse', seq, reset, label, it, er, fin))

            try:
                if feed:
                    jobs = []
                    for key, site_base in self._active_feed_sites():
                        if key == 'Beeg':
                            jobs.append((key, site_base, self._beeg_browser()))
                        else:
                            jobs.append((key, site_base, self._kvs_browser_for_url(site_base)))

                    def fetch_feed(key, site_base, browser):
                        p = pages.get(key, 1)
                        try:
                            got = browser.fetch_page(browser.page_url(site_base, p))
                        except Exception as exc:
                            errs.append(f'{key}: {exc}')
                            return []
                        self._feed_pages[key] = p + 1
                        return got

                    with futures.ThreadPoolExecutor(
                            max_workers=min(8, max(len(jobs), 1))) as pool:
                        futs = [pool.submit(fetch_feed, k, b, br) for k, b, br in jobs]
                        for fut in futures.as_completed(futs):
                            emit(fut.result(), '', False)
                elif multi_urls:
                    label = multi_label
                    primary_results_count = 0

                    def fetch_multi(u):
                        p = multi_pages.get(u, 1)
                        try:
                            browser = self._kvs_browser_for_url(u)
                            got = browser.fetch_page(
                                browser.page_url(u, p),
                                verify_name=wv.get(u))
                        except Exception as exc:
                            errs.append(f'{u.rsplit("/", 2)[-2]}: {exc}')
                            return []
                        self._multi_pages[u] = p + 1
                        return got

                    with futures.ThreadPoolExecutor(
                            max_workers=min(8, max(len(multi_urls), 1))) as pool:
                        futs = [pool.submit(fetch_multi, u) for u in multi_urls]
                        for fut in futures.as_completed(futs):
                            res = fut.result()
                            if res:
                                primary_results_count += len(res)
                            emit(res, '', False)

                    # If primary search returned 0 items (e.g. spelling mistake, typo, niche query), seamlessly fetch fallback recommendations!
                    if primary_results_count == 0 and fallback_urls and reset:
                        sugg = getattr(self, '_search_suggestion', None)
                        if sugg:
                            try:
                                self.after(0, lambda s=sugg: self.show_toast(f'Showing related videos for "{s}"', icon='sparkles', color='#0a84ff'))
                            except Exception:
                                pass
                        fb_targets = fallback_urls[:8]
                        def fetch_fb(u):
                            try:
                                browser = self._kvs_browser_for_url(u)
                                return browser.fetch_page(browser.page_url(u, 1))
                            except Exception:
                                return []

                        with futures.ThreadPoolExecutor(
                                max_workers=min(8, max(len(fb_targets), 1))) as pool:
                            futs = [pool.submit(fetch_fb, u) for u in fb_targets]
                            for fut in futures.as_completed(futs):
                                emit(fut.result(), '', False)
                else:
                    browser = self._kvs_browser_for_url(base)
                    fetch_url = browser.page_url(base, page)
                    label = ''
                    items = browser.fetch_page(fetch_url)
                    self.page = page + 1
                    emit(items, '', True)
                    return
                emit([], '; '.join(errs), True)
            except Exception as exc:
                emit([], '; '.join(errs + [str(exc)]), True)

        self.browse_thread = threading.Thread(target=worker, daemon=True)
        self.browse_thread.start()

    def _maybe_load_more(self, _e=None):
        if self._no_more or self._browse_loading:
            return
        if self.browse_thread and self.browse_thread.is_alive():
            return
        canvas = self.cards_canvas
        if canvas.winfo_height() < 80 or not self._cards:
            return
        _top, bottom = canvas.yview()
        if bottom >= 0.995:
            self._start_browse_fetch(reset=False)

    def _on_sidebar_pick(self, picked):
        kind, target = picked
        self._sidebar_pending = (kind, target)
        if isinstance(target, dict) and 'urls' in target:
            name = target.get('name') or 'tag'
            self.browse_load(target, reset=True)
            self.say(f'Browsing tag: {name}')
            try:
                analytics.track('browse', category=str(kind), target=str(name)[:100])
            except Exception:
                pass
            return
        self.browse_load(target, reset=True)
        self.say(f'Browsing: {target[:60]}')
        try:
            analytics.track('browse', category=str(kind), target=str(target)[:100])
        except Exception:
            pass

    # ---------- event pump ----------
    def _poll_events(self):
        try:
            while True:
                ev = self.events.get_nowait()
                try:
                    self._handle_event(ev)
                except Exception:
                    traceback.print_exc()
        except queue.Empty:
            pass
        self.after(120, self._poll_events)

    def _handle_event(self, ev):
        kind = ev[0]
        if kind == 'log':
            self.lbl_overall.configure(text=str(ev[1])[:90])
        elif kind == 'state':
            _, row, state, text = ev
            row.state = state
            row.lbl_status.configure(text=text[:40])
            row.lbl_status.configure(fg=JobRow.STATE_FG.get(state, MUTE))
            if state == 'downloading':
                row.set_downloading()
                self._set_cards_download_state(row.url, 'downloading')
                if hasattr(self, '_preview_url') and self._preview_url and self._preview_url.rstrip('/') == (row.url or '').rstrip('/'):
                    try:
                        self.lbl_dl_head.configure(text=' Downloading…', fg=PILL_PRI_FG)
                        self.btn_dl_head.configure(bg=PILL_PRI_BG, highlightbackground=PILL_PRI_BORDER)
                    except Exception:
                        pass
            elif state in ('cancelled', 'error', 'blocked'):
                row.set_resumable()
                self._set_cards_download_state(row.url, 'idle')
            elif state == 'ready':
                row.set_ready()
                self._set_cards_download_state(row.url, 'queued')

            if state != 'downloading':
                row.pct_lbl.configure(
                    text='' if state in ('queued', 'resolving') else '\u2014')
            self._save_persisted_queue()
        elif kind == 'title':
            _, row, title = ev
            row.lbl_title.configure(text=title)
        elif kind == 'ready':
            _, row = ev
            row.state = 'ready'
            row.set_ready()
            title = row.crawler.target_name() if row.crawler else ''
            if title:
                row.lbl_title.configure(text=title)
            row.lbl_status.configure(text='ready', fg=LINK)
            row.pct_lbl.configure(text='')
            self._unbusy_cards_for(row.url)
            self._set_cards_download_state(row.url, 'queued')
            self._save_persisted_queue()
            if getattr(row, 'auto_watch', False):
                row.auto_watch = False
                self.open_player_for_row(row)
            elif getattr(row, 'auto_download', False):
                row.auto_download = False
                self.start_rows([row])
        elif kind == 'playback_ready':
            _, url, title, link, item = ev
            self._unbusy_cards_for(url)
            if link:
                self.switch_tab('browse')
                self.play_in_preview(title, link, item=item, url=url)
            else:
                self.say('Could not resolve stream link for playback.')
        elif kind == 'resolve_failed':
            _, row, text = ev
            row.state = 'error'
            row.lbl_status.configure(text=text[:40], fg=ERROR)
            row.pct_lbl.configure(text='\u2014')
            self._unbusy_cards_for(row.url)
            row.set_resumable()
            self._save_persisted_queue()
        elif kind == 'progress':
            _, row, pct, txt = ev
            row._last_pct = pct
            row._last_txt = txt
            row.bar.configure(value=min(pct, 100))
            row.pct_lbl.configure(text=f'{min(pct, 100):.0f}%')
            row.lbl_status.configure(text=txt[:44], fg=MUTE)
        elif kind == 'browse':
            _, seq, reset, label, items, err, final = ev
            if seq != self._browse_seq:
                return
            self._browse_loading = False
            items = [it for it in (items or []) if self._is_item_enabled(it)]
            fresh = []
            batch = {}
            for it in items:
                u = it.get('url')
                if not u or u in self._seen_urls:
                    continue
                self._seen_urls.add(u)
                key = _dup_key(it)
                if key is None:
                    fresh.append(it)
                    continue
                prev = batch.get(key)
                if prev is None:
                    shown_card = self._dup_cards.get(key)
                    if shown_card is not None:
                        try:
                            if (bool(shown_card.winfo_exists())
                                    and not shown_card.btn_watch.instate(['disabled'])
                                    and _site_rank(it) < _site_rank(shown_card.item)):
                                self._swap_card(shown_card, it, key)
                        except Exception:
                            pass
                        continue
                    batch[key] = it
                elif _site_rank(it) < _site_rank(prev):
                    batch[key] = it
            appended = fresh + list(batch.values())
            if appended:
                start = len(self._cards)
                self._append_cards(appended)
                url_key = {str(it.get('url')): key for key, it in batch.items()}
                for card in self._cards[start:]:
                    key = url_key.get(str(card.item.get('url')))
                    if key is not None:
                        self._dup_cards[key] = card
            if appended:
                self._load_got_any = True
            if final:
                if not self._load_got_any:
                    self._no_more = True
                    if reset:
                        self.lbl_cards_empty.configure(
                            text='No videos here \u2014 pick a tag, actress or channel on the left.')
                        self.lbl_cards_empty.grid(row=0, column=0,
                                                  columnspan=max(1, getattr(self, '_card_cols', 3)),
                                                  sticky='nsew')
                    pending = self._sidebar_pending
                    if reset and pending is not None:
                        self._sidebar_pending = None
                        kind, target = pending
                        self.sidebar.remove_entry(kind, target)
                        name = (target.get('name') if isinstance(target, dict)
                                else str(target)[:60])
                        self.say(f'Broken or empty link \u2014 removed: {name}')
                self._sidebar_pending = None
                self.after(300, self._maybe_load_more)
        elif kind == 'download_done':
            _, row, path, title = ev
            self._set_cards_download_state(row.url, 'done')
            row.state = 'done'
            row.target_path = path or ''
            row.set_done(path)
            try:
                analytics.track('download_complete')
            except Exception:
                pass
            if hasattr(self, '_preview_url') and self._preview_url and self._preview_url.rstrip('/') == (row.url or '').rstrip('/'):
                try:
                    self.lbl_dl_head.configure(text=' Downloaded', fg=PILL_SUC_FG)
                    self.btn_dl_head.configure(bg=PILL_SUC_BG, highlightbackground=PILL_SUC_BORDER)
                except Exception:
                    pass
            size = 0
            try:
                if path and os.path.isfile(path):
                    size = os.path.getsize(path)
            except Exception:
                size = 0
            config.add_download_history({
                'url': row.url,
                'title': title or row.url,
                'path': path or '',
                'size': size,
                'site': _SITE_LABEL.get(row.site_cls, ''),
                'finished_at': time.strftime('%Y-%m-%d %H:%M'),
            })
            self._save_persisted_queue()
            self._render_history()
            self._update_overall()
            self.say('Download finished — saved and added to History.')
        elif kind == 'thumb':
            _, card, im = ev
            card.apply_image(im)
        elif kind == 'performer_avatar':
            _, card_widget, name_key, raw_img, name, role, width, height = ev
            self._apply_performer_avatar(card_widget, name_key, raw_img, name, role, width, height)
        elif kind == 'probe':
            _, row, text = ev
            if row.state == 'ready':
                row.lbl_status.configure(text=text[:40], fg=WARNING_DEEP)
        elif kind == 'preview_info':
            _, seq, info = ev
            if seq == self._preview_seq:
                self._render_preview_info(info)
        elif kind == 'preview_recs':
            _, seq, items = ev
            if seq == self._preview_seq:
                self._fill_recs(items)
        elif kind == 'sidebar_data':
            _, site, result = ev
            try:
                self.sidebar.apply_data(site, result)
            except Exception:
                pass
        elif kind == 'job_done':
            self._update_overall()
        elif kind == 'preview_vlc_ready':
            _, seq, player = ev
            self._attach_preview_vlc(seq, player)
        elif kind == 'preview_vlc_failed':
            _, seq, err = ev
            if seq == getattr(self, '_preview_seq', -1):
                self.preview_status.configure(
                    text=f'VLC error: {err[:60]}', fg=ERROR)
        elif kind == 'announcements':
            _, data, user_triggered = ev
            self._apply_announcements(data, user_triggered=user_triggered)

    # ---------- Dynamic Remote Announcements, Ads & Notifications System ----------
    def _open_external_url(self, url):
        url = str(url or '').strip()
        if not url:
            return
        try:
            webbrowser.open_new_tab(url)
        except Exception:
            try:
                os.startfile(url)
            except Exception:
                pass

    @staticmethod
    def _resolve_image_path(path_str):
        if not path_str:
            return ''
        s = str(path_str).strip()
        if s.startswith('file://'):
            s = s[7:].lstrip('/')
        if os.path.isfile(s):
            return os.path.abspath(s)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        rel_p = os.path.join(base_dir, s)
        if os.path.isfile(rel_p):
            return rel_p
        fname = os.path.basename(s)
        asset_p = os.path.join(base_dir, 'assets', 'announcements', fname)
        if os.path.isfile(asset_p):
            return asset_p
        fname_lower = fname.lower()
        if 'banner' in fname_lower or 'food' in fname_lower:
            fallback_b = os.path.join(base_dir, 'assets', 'announcements', 'fetchjav_banner.png')
            if os.path.isfile(fallback_b):
                return fallback_b
        elif 'thumb' in fname_lower or 'project' in fname_lower or 'card' in fname_lower:
            fallback_t = os.path.join(base_dir, 'assets', 'announcements', 'fetchjav_thumb.png')
            if os.path.isfile(fallback_t):
                return fallback_t
        return s

    def _load_initial_announcements(self):
        """Immediately loads announcements from local file or cache on app launch without waiting."""
        if not config.get_announcements_enabled():
            return
        data = None
        local_manifest = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'announcements.json')
        if os.path.isfile(local_manifest):
            try:
                with open(local_manifest, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                data = None
        if not data:
            cached = config.get_cached_announcements().get('payload')
            if cached and isinstance(cached, dict):
                data = cached
        if data:
            self._apply_announcements(data, user_triggered=False)

    def _fetch_remote_announcements(self, user_triggered=False):
        """Fetches dynamic remote announcements/ads from the configured JSON endpoint in background."""
        if not config.get_announcements_enabled() and not user_triggered:
            return

        def worker():
            url = config.get_remote_announcements_url()
            if not url:
                if user_triggered:
                    self.events.put(('toast', 'No announcement URL configured.', 'close', ERROR))
                return
            applied = False
            try:
                fetch_url = url
                if user_triggered:
                    sep = '&' if '?' in url else '?'
                    fetch_url = f'{url}{sep}_t={int(time.time())}'

                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) FetchX/2.5',
                    'Cache-Control': 'no-cache',
                }
                session = getattr(self, '_thumb_session', requests)
                resp = session.get(fetch_url, headers=headers, timeout=6)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                    except Exception:
                        data = json.loads(resp.text)
                    config.save_cached_announcements(data)
                    self.events.put(('announcements', data, user_triggered))
                    applied = True
                elif user_triggered:
                    self.events.put(('toast', f'Failed to fetch notices (HTTP {resp.status_code})', 'close', ERROR))
            except Exception as exc:
                if user_triggered:
                    self.events.put(('toast', f'Could not fetch notices: {exc}', 'close', ERROR))

            if not applied and not user_triggered:
                # Fallback to local announcements.json or cache if remote fails or is offline
                cached = config.get_cached_announcements().get('payload')
                if not cached:
                    local_manifest = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'announcements.json')
                    if os.path.isfile(local_manifest):
                        try:
                            with open(local_manifest, 'r', encoding='utf-8') as f:
                                cached = json.load(f)
                        except Exception:
                            cached = None
                if cached:
                    self.events.put(('announcements', cached, False))

        threading.Thread(target=worker, daemon=True).start()

    def _is_card_ad_dismissed(self, notice_id):
        if not config.get_announcements_enabled():
            return True
        if not notice_id:
            return False
        return str(notice_id) in getattr(self, '_session_dismissed_cards', set())

    def _dismiss_card_ad(self, card_widget, item):
        notice_id = str(item.get('id') or '')
        if not hasattr(self, '_session_dismissed_cards'):
            self._session_dismissed_cards = set()
        if notice_id:
            self._session_dismissed_cards.add(notice_id)
        if card_widget in getattr(self, '_cards', []):
            self._cards.remove(card_widget)
        try:
            card_widget.destroy()
        except Exception:
            pass
        if getattr(self, '_current_tab', '') == 'watch_later':
            self._render_watch_later()
        else:
            self._relayout_cards()
            if hasattr(self, '_relayout_recs'):
                self._relayout_recs()
        self.show_toast('Promo card hidden for this session', icon='check', color=MUTE)

    def _apply_announcements(self, data, user_triggered=False):
        if not isinstance(data, dict):
            return
        items = data.get('announcements') or []
        if not isinstance(items, list):
            return

        banner_shown = False
        self._remote_card_ads = []

        for item in items:
            if not isinstance(item, dict) or not item.get('enabled', True):
                continue
            notice_id = str(item.get('id') or '').strip()

            ntype = str(item.get('type') or 'banner').lower()
            if ntype == 'banner':
                if notice_id and config.is_announcement_dismissed(notice_id):
                    continue
                if not banner_shown:
                    self._render_announcement_banner(item)
                    banner_shown = True
            elif ntype == 'card':
                if not self._is_card_ad_dismissed(notice_id):
                    self._remote_card_ads.append(item)
            elif ntype == 'modal':
                if notice_id and config.is_announcement_dismissed(notice_id):
                    continue
                self._render_modal_announcement(item)

        if not banner_shown and hasattr(self, 'announcement_bar'):
            self.announcement_bar.pack_forget()

        if self._remote_card_ads:
            self._maybe_inject_card_ads()

        if user_triggered:
            active_count = (1 if banner_shown else 0) + len(self._remote_card_ads)
            self.show_toast(f'Fetched announcements ({active_count} active)', icon='sparkles', color=LINK)

    def _should_inject_card_ads(self):
        if not config.get_announcements_enabled():
            return False
        if getattr(self, '_current_tab', 'browse') != 'browse':
            return False
        if getattr(self, '_is_shuffle_mode', False):
            return False
        c_base = getattr(self, 'current_base', None)
        if isinstance(c_base, dict):
            b_name = str(c_base.get('name') or '').lower()
            if 'shuffle' in b_name or 'watchlist' in b_name:
                return False
        if hasattr(self, 'sidebar'):
            a_key = getattr(self.sidebar, '_active_key', '')
            if a_key in ('shuffle', 'watchlist', 'watch_later'):
                return False
        m_lbl = str(getattr(self, '_multi_label', '')).lower()
        if 'shuffle' in m_lbl or 'watchlist' in m_lbl:
            return False
        return True

    def _maybe_inject_card_ads(self):
        if not self._should_inject_card_ads():
            return
        if not getattr(self, '_remote_card_ads', None) or not getattr(self, '_cards', []):
            return
        has_sponsored = any(isinstance(c, SponsoredCard) for c in self._cards)
        if not has_sponsored:
            cols, card_w = self._calc_cols_and_width(self.cards_canvas.winfo_width())
            for ad_item in list(self._remote_card_ads):
                if self._is_card_ad_dismissed(ad_item.get('id')):
                    continue
                ad_card = SponsoredCard(self, self.cards_inner, ad_item)
                self._cards.insert(0, ad_card)
                self._bind_wheel_recursive(ad_card, self._on_cards_wheel)
            self._relayout_cards()

    def _render_announcement_banner(self, item):
        if not hasattr(self, 'announcement_bar'):
            return
        for w in self.announcement_bar.winfo_children():
            w.destroy()

        notice_id = str(item.get('id') or '')
        accent = item.get('accent_color') or '#0070f3'
        badge_txt = str(item.get('badge') or 'NEW RELEASE').upper()
        icon_name = str(item.get('icon') or 'sparkles')
        title = str(item.get('title') or '').strip()
        message = str(item.get('message') or item.get('description') or '').strip()
        link_text = str(item.get('link_text') or 'Download ⬇')
        link_url = str(item.get('link_url') or '')
        dismissible = bool(item.get('dismissible', True))

        # Outer banner card with subtle glowing border
        banner_fr = tk.Frame(self.announcement_bar, bg=HAIRLINE_SOFT, highlightthickness=1,
                             highlightbackground=accent, cursor='hand2' if link_url else 'arrow')
        banner_fr.pack(fill='x', padx=14, pady=(8, 4))

        inner = tk.Frame(banner_fr, bg=HAIRLINE_SOFT, padx=12, pady=10)
        inner.pack(fill='x')

        img_src = self._resolve_image_path(item.get('image_url') or item.get('image_path') or '')
        banner_photo = None
        if img_src and os.path.isfile(img_src):
            try:
                raw_im = Image.open(img_src).convert('RGBA')
                bh = 90
                bw = max(1, round(raw_im.width * bh / raw_im.height))
                if bw > 340:
                    bw = 340
                    bh = max(1, round(raw_im.height * bw / raw_im.width))
                resized_im = raw_im.resize((bw, bh), Image.Resampling.LANCZOS)
                rounded_im = apply_rounded_corners(resized_im, radius=10, bg_color=(18, 18, 22, 255)) or resized_im
                banner_photo = ImageTk.PhotoImage(rounded_im)
            except Exception:
                banner_photo = None

        if banner_photo:
            img_box = tk.Frame(inner, bg=HAIRLINE_SOFT, highlightthickness=1, highlightbackground=accent)
            img_box.pack(side='left', padx=(0, 14))
            lbl_banner_img = tk.Label(img_box, image=banner_photo, bg=HAIRLINE_SOFT, cursor='hand2' if link_url else 'arrow', bd=0)
            lbl_banner_img.image = banner_photo
            lbl_banner_img.pack()
            if link_url:
                lbl_banner_img.bind('<Button-1>', lambda _e, u=link_url: self._open_external_url(u))

        # Center: Eyebrow + Title + Message
        center_fr = tk.Frame(inner, bg=HAIRLINE_SOFT)
        center_fr.pack(side='left', fill='both', expand=True)

        row_top = tk.Frame(center_fr, bg=HAIRLINE_SOFT)
        row_top.pack(fill='x', anchor='w')

        lbl_badge = tk.Label(row_top, text=f' {badge_txt} ', bg=ELEVATED, fg=accent,
                             font=self.font_mono(8, bold=True),
                             highlightthickness=1, highlightbackground=accent,
                             padx=6, pady=2)
        lbl_badge.pack(side='left', padx=(0, 8))

        if title:
            lbl_title = tk.Label(row_top, text=title, bg=HAIRLINE_SOFT, fg=INK,
                                 font=self.font_sans(11, bold=True), anchor='w')
            lbl_title.pack(side='left', fill='x')

        if message:
            lbl_msg = tk.Label(center_fr, text=message, bg=HAIRLINE_SOFT, fg=BODY,
                               font=self.font_sans(9), justify='left', anchor='w', wraplength=480)
            lbl_msg.pack(fill='x', anchor='w', pady=(4, 0))
            center_fr.bind('<Configure>', lambda e, l=lbl_msg: l.configure(wraplength=max(200, e.width - 20)))

        # Right: Action Button + Close Button
        right_fr = tk.Frame(inner, bg=HAIRLINE_SOFT)
        right_fr.pack(side='right', padx=(10, 0))

        if link_url:
            btn_act = tk.Frame(right_fr, bg=PILL_PRI_BG, highlightthickness=1,
                               highlightbackground=PILL_PRI_BORDER, cursor='hand2')
            btn_act.pack(side='left', padx=(0, 8))
            lbl_act = tk.Label(btn_act, text=link_text, bg=PILL_PRI_BG, fg=PILL_PRI_FG,
                               font=self.font_sans(9, bold=True), cursor='hand2',
                               padx=12, pady=5)
            lbl_act.pack()

            def _on_btn_h(enter):
                btn_act.configure(bg=PILL_PRI_HOVER_BG if enter else PILL_PRI_BG,
                                  highlightbackground=PILL_PRI_HOVER_BD if enter else PILL_PRI_BORDER)
                lbl_act.configure(bg=PILL_PRI_HOVER_BG if enter else PILL_PRI_BG,
                                  fg=PILL_PRI_HOVER_FG if enter else PILL_PRI_FG)

            for w in (btn_act, lbl_act):
                w.bind('<Button-1>', lambda _e, u=link_url: self._open_external_url(u))
                w.bind('<Enter>', lambda _e: _on_btn_h(True))
                w.bind('<Leave>', lambda _e: _on_btn_h(False))

        if dismissible:
            btn_close = tk.Label(right_fr, text='✕', bg=HAIRLINE_SOFT, fg=MUTE,
                                 font=self.font_sans(11, bold=True), cursor='hand2', padx=6, pady=2)
            btn_close.pack(side='left')

            def _on_close_h(enter):
                btn_close.configure(fg=ERROR if enter else MUTE)

            btn_close.bind('<Button-1>', lambda _e, nid=notice_id: self._dismiss_announcement_ui(nid))
            btn_close.bind('<Enter>', lambda _e: _on_close_h(True))
            btn_close.bind('<Leave>', lambda _e: _on_close_h(False))

        if link_url:
            for w in (banner_fr, inner, center_fr, row_top, lbl_badge):
                w.bind('<Button-1>', lambda _e, u=link_url: self._open_external_url(u))

        if hasattr(self, 'cards_body'):
            self.announcement_bar.pack(side='top', fill='x', before=self.cards_body)
        else:
            self.announcement_bar.pack(side='top', fill='x')

    def _dismiss_announcement_ui(self, notice_id):
        if notice_id:
            config.dismiss_announcement(notice_id)
        if hasattr(self, 'announcement_bar'):
            self.announcement_bar.pack_forget()

    def _render_modal_announcement(self, item):
        notice_id = str(item.get('id') or '')
        accent = item.get('accent_color') or LINK
        badge_txt = str(item.get('badge') or 'ANNOUNCEMENT').upper()
        icon_name = str(item.get('icon') or 'sparkles')
        title = str(item.get('title') or 'Notice').strip()
        message = str(item.get('message') or item.get('description') or '').strip()
        link_text = str(item.get('link_text') or 'Open Link ↗')
        link_url = str(item.get('link_url') or '')

        top = tk.Toplevel(self)
        top.title(title)
        top.geometry('460x280')
        top.configure(bg=CARD_BG)
        top.resizable(False, False)
        top.transient(self)
        top.grab_set()

        try:
            x = self.winfo_x() + (self.winfo_width() - 460) // 2
            y = self.winfo_y() + (self.winfo_height() - 280) // 2
            top.geometry(f'+{max(0, x)}+{max(0, y)}')
        except Exception:
            pass

        card_fr = tk.Frame(top, bg=CARD_BG, padx=24, pady=20)
        card_fr.pack(fill='both', expand=True)

        head_fr = tk.Frame(card_fr, bg=CARD_BG)
        head_fr.pack(fill='x', pady=(0, 12))

        ico_img = get_heroicon(icon_name, size=24, color=accent)
        lbl_ico = tk.Label(head_fr, image=ico_img, bg=CARD_BG)
        lbl_ico.image = ico_img
        lbl_ico.pack(side='left', padx=(0, 10))

        lbl_badge = tk.Label(head_fr, text=f' {badge_txt} ', bg=ELEVATED, fg=accent,
                             font=self.font_mono(9, bold=True),
                             highlightthickness=1, highlightbackground=accent,
                             padx=8, pady=3)
        lbl_badge.pack(side='left')

        tk.Label(card_fr, text=title, bg=CARD_BG, fg=INK,
                 font=self.font_sans(13, bold=True), anchor='w', wraplength=410, justify='left'
                 ).pack(fill='x', pady=(0, 8))

        tk.Label(card_fr, text=message, bg=CARD_BG, fg=BODY,
                 font=self.font_sans(10), anchor='w', wraplength=410, justify='left'
                 ).pack(fill='x', pady=(0, 16))

        bot_fr = tk.Frame(card_fr, bg=CARD_BG)
        bot_fr.pack(side='bottom', fill='x')

        var_dont_show = tk.BooleanVar(value=True)
        cb = ttk.Checkbutton(bot_fr, text="Don't show again", variable=var_dont_show)
        cb.pack(side='left')

        def _on_close_modal():
            if var_dont_show.get() and notice_id:
                config.dismiss_announcement(notice_id)
            top.destroy()

        btn_dismiss = tk.Frame(bot_fr, bg=PILL_SEC_BG, highlightthickness=1,
                               highlightbackground=PILL_SEC_BORDER, cursor='hand2')
        btn_dismiss.pack(side='right', padx=(8, 0))
        lbl_dismiss = tk.Label(btn_dismiss, text='Close', bg=PILL_SEC_BG, fg=PILL_SEC_FG,
                               font=self.font_sans(9, bold=True), cursor='hand2', padx=12, pady=4)
        lbl_dismiss.pack()
        for w in (btn_dismiss, lbl_dismiss):
            w.bind('<Button-1>', lambda _e: _on_close_modal())

        if link_url:
            btn_act = tk.Frame(bot_fr, bg=PILL_PRI_BG, highlightthickness=1,
                               highlightbackground=PILL_PRI_BORDER, cursor='hand2')
            btn_act.pack(side='right')
            lbl_act = tk.Label(btn_act, text=link_text, bg=PILL_PRI_BG, fg=PILL_PRI_FG,
                               font=self.font_sans(9, bold=True), cursor='hand2', padx=12, pady=4)
            lbl_act.pack()

            def _on_modal_act(_e=None):
                if var_dont_show.get() and notice_id:
                    config.dismiss_announcement(notice_id)
                self._open_external_url(link_url)
                top.destroy()

            for w in (btn_act, lbl_act):
                w.bind('<Button-1>', _on_modal_act)

    def _clear_cards(self):
        for w in self.cards_inner.winfo_children():
            if w is not self.lbl_cards_empty:
                w.destroy()
        self._cards = []
        self._card_ad_injected = False
        self.lbl_cards_empty.configure(text='Loading videos\u2026')
        self.lbl_cards_empty.grid(row=0, column=0,
                                  columnspan=self._card_cols, sticky='nsew')
        self.cards_canvas.yview_moveto(0)

    # ---------- Adaptive Card Grid (3 Videos Max per Row on Full Screen) ----------
    CARD_COLS_MAX = 3
    RECS_W = 520

    def _calc_cols_and_width(self, w):
        """Calculate optimal column count and per-card pixel width for viewport width `w`.
        - Full screen / maximized / large window: strictly 3 cards per row (large & clear).
        - Medium / compact window: automatically adapts down to 2 cards per row.
        - Narrow / split window: automatically adapts down to 1 card per row.
        """
        w = max(w, 200)
        if w >= 780:
            cols = 3
        elif w >= 480:
            cols = 2
        else:
            cols = 1
        cols = min(self.CARD_COLS_MAX, max(1, cols))
        pad_total = (cols + 1) * 16
        card_w = max(200, int((w - pad_total) / cols))
        return cols, card_w

    def _on_cards_configure(self, event=None):
        if event is not None and hasattr(event, 'width') and event.widget == self.cards_canvas:
            w = event.width
        else:
            w = self.cards_canvas.winfo_width()
        if w <= 50:
            return
        self.cards_canvas.itemconfigure('cards', width=w)
        cols, _cw = self._calc_cols_and_width(w)
        changed = (cols != self._card_cols or abs(w - getattr(self, '_grid_w', 0)) > 16)
        if changed:
            self._grid_w = w
            self._card_cols = cols
            if getattr(self, '_relayout_after', None):
                try:
                    self.after_cancel(self._relayout_after)
                except Exception:
                    pass
            self._relayout_after = self.after(140, self._relayout_cards)
        self._maybe_load_more()

    def _relayout_cards(self):
        self._relayout_after = None
        if not bool(self.cards_canvas.winfo_exists()) or not bool(self.cards_inner.winfo_exists()):
            return
        w = max(200, self.cards_canvas.winfo_width())
        self.cards_canvas.itemconfigure('cards', width=w)
        cols, card_w = self._calc_cols_and_width(w)
        cols_changed = (cols != self._card_cols)
        self._card_cols = cols

        if cols_changed:
            # Only reconfigure column weights when the column count actually
            # changes; re-setting them on every resize is pure overhead.
            for c in range(12):
                self.cards_inner.grid_columnconfigure(c, weight=0, uniform='')
            for c in range(cols):
                self.cards_inner.grid_columnconfigure(c, weight=1, uniform='card')

        for i, card in enumerate(list(self._cards)):
            if not bool(card.winfo_exists()):
                continue
            r, c = divmod(i, cols)
            if cols_changed:
                card.grid(row=r, column=c, padx=8, pady=8, sticky='nsew')
            card.set_width(card_w)
            if getattr(card, '_src', None) is None:
                url = card.item.get('thumbnail') or ''
                cached = self._thumb_cache.get(url)
                if cached is not None:
                    card.apply_image(cached)

        self.cards_canvas.configure(scrollregion=self.cards_canvas.bbox('all'))

    def _append_cards(self, items):
        items = [it for it in (items or []) if self._is_item_enabled(it)]
        if not items:
            return
        start = len(self._cards)
        self.lbl_cards_empty.grid_forget()
        w = max(200, self.cards_canvas.winfo_width())
        self.cards_canvas.itemconfigure('cards', width=w)
        cols, card_w = self._calc_cols_and_width(w)
        self._card_cols = cols

        # Inject dynamic remote promotional/notice card if available (Browse only)
        if self._should_inject_card_ads() and not getattr(self, '_card_ad_injected', False) and getattr(self, '_remote_card_ads', None):
            self._card_ad_injected = True
            for ad_item in list(self._remote_card_ads):
                if self._is_card_ad_dismissed(ad_item.get('id')):
                    continue
                ad_card = SponsoredCard(self, self.cards_inner, ad_item)
                ad_idx = len(self._cards)
                r, c = divmod(ad_idx, cols)
                ad_card.grid(row=r, column=c, padx=8, pady=8, sticky='nsew')
                ad_card.set_width(card_w)
                self._cards.append(ad_card)
                self._bind_wheel_recursive(ad_card, self._on_cards_wheel)

        start = len(self._cards)
        for i, it in enumerate(items):
            card = VideoCard(self, self.cards_inner, it)
            r, c = divmod(start + i, cols)
            card.grid(row=r, column=c, padx=8, pady=8, sticky='nsew')
            card.set_width(card_w)
            self._cards.append(card)
            self._bind_wheel_recursive(card, self._on_cards_wheel)

        for c in range(cols):
            self.cards_inner.grid_columnconfigure(c, weight=1, uniform='card')

        pending = []
        for card in self._cards[start:]:
            url = card.item.get('thumbnail') or ''
            if not url:
                continue
            cached = self._thumb_cache.get(url)
            if cached is not None:
                card.apply_image(cached)
            else:
                pending.append((card, url))
        for card, url in pending:
            self.thumb_pool.submit(self._load_thumb, card, url)

    def _swap_card(self, old_card, item, key):
        info = old_card.grid_info()
        idx = self._cards.index(old_card)
        try:
            old_card.destroy()
        except Exception:
            pass
        card = VideoCard(self, self.cards_inner, item)
        card.grid(row=info.get('row', 0), column=info.get('column', 0),
                  padx=9, pady=9, sticky='nsew')
        self._cards[idx] = card
        self._bind_wheel_recursive(card, self._on_cards_wheel)
        if self._dup_cards.get(key) is not None:
            self._dup_cards[key] = card
        url = item.get('thumbnail') or ''
        if url:
            cached = self._thumb_cache.get(url)
            if cached is not None:
                card.apply_image(cached)
            else:
                self.thumb_pool.submit(self._load_thumb, card, url)
        self.say('Swapped in a faster source for a duplicate video.')

    def _load_thumb(self, card, url):
        site = str(card.item.get('site_name') or '')
        referer = {'Beeg': 'https://beeg.com/',
                   'OnePorn': 'https://www.1porn.tv/'}.get(
            site, 'https://www.freepornvideos.xxx/')
        im = None
        local_path = self._resolve_image_path(url)
        if os.path.isfile(local_path):
            try:
                raw = Image.open(local_path).convert('RGB')
                if raw.width > 640:
                    raw = raw.resize(
                        (640, max(1, round(raw.height * 640 / raw.width))),
                        Image.Resampling.BICUBIC)
                im = raw
            except Exception:
                im = None
        else:
            try:
                session = getattr(self, '_thumb_session', None) or requests
                ua = config.headers.get('User-Agent', 'Mozilla/5.0')
                resp = session.get(
                    url, timeout=12,
                    headers={'User-Agent': ua,
                             'Referer': referer})
                if resp.status_code == 200:
                    raw = Image.open(io.BytesIO(resp.content)).convert('RGB')
                    if raw.width > 480:
                        raw = raw.resize(
                            (480, max(1, round(raw.height * 480 / raw.width))),
                            Image.Resampling.BICUBIC)
                    im = raw
            except Exception:
                im = None
        if im is None and not getattr(card, '_thumb_fallback_done', False):
            card._thumb_fallback_done = True
            im = self._load_thumb_fallback(card)
        if len(self._thumb_cache) > 250:
            for k in list(self._thumb_cache.keys())[:50]:
                self._thumb_cache.pop(k, None)
        self._thumb_cache[url] = im
        self.events.put(('thumb', card, im))

    def _load_thumb_fallback(self, card):
        """If the card's thumbnail URL fails, re-fetch the video page from the
        internet and pull its og:image so the card still shows a preview."""
        item = card.item or {}
        page = str(item.get('url') or '')
        if not page:
            return None
        site = str(item.get('site_name') or '')
        referer = {'Beeg': 'https://beeg.com/',
                   'OnePorn': 'https://www.1porn.tv/'}.get(
            site, 'https://www.freepornvideos.xxx/')
        try:
            import html as _html
            from urllib.parse import urljoin
            session = getattr(self, '_thumb_session', None) or requests
            ua = config.headers.get('User-Agent', 'Mozilla/5.0')
            headers = {'User-Agent': ua, 'Referer': referer}
            resp = session.get(page, timeout=12, headers=headers)
            if resp.status_code != 200:
                return None
            m = re.search(
                r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
                resp.text, re.I)
            if not m:
                m = re.search(
                    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
                    resp.text, re.I)
            og = _html.unescape(m.group(1)) if m else ''
            if not og:
                return None
            if not og.startswith('http'):
                og = urljoin(page, og)
                if not og.startswith('http'):
                    return None
            r2 = session.get(og, timeout=12, headers=headers)
            if r2.status_code != 200:
                return None
            raw = Image.open(io.BytesIO(r2.content)).convert('RGB')
            if raw.width > 480:
                raw = raw.resize(
                    (480, max(1, round(raw.height * 480 / raw.width))),
                    Image.Resampling.BICUBIC)
            return raw
        except Exception:
            return None

    def _update_overall(self):
        rows = list(self.rows)
        counts = {}
        active_count = 0
        for r in rows:
            counts[r.state] = counts.get(r.state, 0) + 1
            if r.state in ('downloading', 'resolving', 'queued', 'ready'):
                active_count += 1
        parts = [f'{v} {k}' for k, v in sorted(counts.items())]
        self.lbl_overall.configure(text='  \u00b7  '.join(parts))
        self.sidebar.set_badge('queue', str(active_count) if active_count > 0 else '')

    def _set_cards_download_state(self, url, state):
        norm = (url or '').rstrip('/')
        for card in list(getattr(self, '_cards', [])):
            try:
                if bool(card.winfo_exists()) and str(card.item.get('url', '')).rstrip('/') == norm:
                    card.set_download_state(state)
            except Exception:
                pass

    def _save_persisted_queue(self):
        items = []
        for r in list(self.rows):
            title = ''
            try:
                title = r.lbl_title.cget('text')
            except Exception:
                title = r.url
            items.append({
                'url': r.url,
                'title': title or r.url,
                'save_dir': getattr(r, 'save_dir', os.path.abspath(self.save_dir.get() or '.')),
                'state': r.state,
                'last_pct': getattr(r, '_last_pct', 100 if r.state == 'done' else 0),
                'last_txt': getattr(r, '_last_txt', 'completed' if r.state == 'done' else ''),
                'target_path': getattr(r, 'target_path', ''),
            })
        config.set_persisted_queue(items)

    def _load_persisted_queue(self):
        items = config.get_persisted_queue()
        if not items:
            return
        auto_resume = config.get_auto_resume_downloads()
        with self.row_lock:
            for it in items:
                url = it.get('url')
                if not url or self._row_for_url(url):
                    continue
                cls = pick_site_class(url)
                if cls is None:
                    continue
                row = JobRow(self, url, len(self.rows))
                row.save_dir = it.get('save_dir') or os.path.abspath(self.save_dir.get() or '.')
                title = it.get('title')
                if title and title != url:
                    row.lbl_title.configure(text=title)
                saved_state = it.get('state', 'queued')
                target_path = it.get('target_path', '')
                last_pct = it.get('last_pct', 0)
                last_txt = it.get('last_txt', '')
                row.target_path = target_path

                if saved_state == 'done':
                    row.state = 'done'
                    row._last_pct = 100
                    row._last_txt = 'completed'
                    row.set_done(target_path)
                else:
                    if last_pct:
                        row._last_pct = last_pct
                        row.bar.configure(value=min(last_pct, 100))
                        row.pct_lbl.configure(text=f'{min(last_pct, 100):.0f}%')
                    if last_txt:
                        row._last_txt = last_txt
                        row.lbl_status.configure(text=last_txt[:44], fg=MUTE)

                self.rows.append(row)

                if saved_state == 'done':
                    pass
                elif auto_resume and saved_state in ('downloading', 'ready'):
                    row.auto_download = True
                    self.resolver_pool.submit(self._resolve_row, row)
                elif saved_state == 'downloading':
                    row.state = 'ready'
                    row.lbl_status.configure(text='interrupted \u00b7 ready to resume', fg=WARNING)
                    row.set_resumable()
                elif saved_state == 'ready':
                    row.set_resumable()
                elif saved_state in ('error', 'cancelled', 'blocked'):
                    row.state = saved_state
                    row.lbl_status.configure(text=saved_state, fg=ERROR if saved_state == 'error' else WARNING)
                    row.set_resumable()
                else:
                    self.resolver_pool.submit(self._resolve_row, row)

        self._update_overall()

    def _on_close(self):
        self._save_persisted_queue()
        self.cancel_all()
        for pool in (self.resolver_pool, self.dl_pool):
            if pool is not None:
                pool.shutdown(wait=False, cancel_futures=True)
        if hasattr(self, '_thumb_session') and self._thumb_session:
            try:
                self._thumb_session.close()
            except Exception:
                pass
        self._stop_preview_playback()
        try:
            analytics.track('session_end')
        except Exception:
            pass
        self.destroy()


def main():
    app = FetchXApp()

    def guard(exc_type, exc, tb):
        traceback.print_exception(exc_type, exc, tb)
        try:
            analytics.track('app_error')
        except Exception:
            pass
        messagebox.showerror(APP_TITLE, ''.join(traceback.format_exception(
            exc_type, exc, tb))[-1500:])
    app.report_callback_exception = guard
    app.mainloop()


if __name__ == '__main__':
    main()
