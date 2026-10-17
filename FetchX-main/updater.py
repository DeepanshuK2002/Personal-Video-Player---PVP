# -*- coding: utf-8 -*-
"""
FetchX Auto-Updater Module
Checks GitHub Releases for new versions, streams downloads with real-time speed & progress,
and performs in-place application updates without opening an external browser.
"""

import json
import os
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import zipfile
from typing import Callable, Dict, Optional, Tuple

APP_VERSION = '2.5.0'
PRIMARY_REPO = 'DeepanshuK2002/FetchX'
FALLBACK_REPOS = ['FetchJAV/FetchX', 'FetchJAV/FetchJAV_Public']


def parse_version(v_str: str) -> Tuple[int, ...]:
    """Parse version string like 'v2.6.1', '2.6.0-beta' into a comparable integer tuple."""
    if not v_str:
        return (0, 0, 0)
    cleaned = str(v_str).strip().lstrip('vV')
    parts = re.findall(r'\d+', cleaned)
    if not parts:
        return (0, 0, 0)
    return tuple(int(p) for p in parts)


def is_newer_version(latest_ver: str, current_ver: str = APP_VERSION) -> bool:
    """Return True if latest_ver is strictly greater than current_ver."""
    return parse_version(latest_ver) > parse_version(current_ver)


def _get_ssl_context():
    """Build or reuse a secure SSL context for GitHub API requests."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def fetch_release_info(repo: str = PRIMARY_REPO) -> Optional[Dict]:
    """
    Fetch the latest release information from GitHub API for the specified repo.
    Returns parsed release dictionary or None if not found/failed.
    """
    url = f'https://api.github.com/repos/{repo}/releases/latest'
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': f'FetchX/{APP_VERSION}',
            'Accept': 'application/vnd.github.v3+json',
        }
    )
    ctx = _get_ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=12, context=ctx) as response:
            if response.status == 200:
                raw = response.read().decode('utf-8')
                return json.loads(raw)
    except urllib.error.HTTPError as err:
        if err.code == 404:
            # Try fetching the list of releases in case latest tag is not marked 'latest'
            list_url = f'https://api.github.com/repos/{repo}/releases'
            list_req = urllib.request.Request(
                list_url,
                headers={
                    'User-Agent': f'FetchX/{APP_VERSION}',
                    'Accept': 'application/vnd.github.v3+json',
                }
            )
            try:
                with urllib.request.urlopen(list_req, timeout=12, context=ctx) as l_resp:
                    if l_resp.status == 200:
                        releases = json.loads(l_resp.read().decode('utf-8'))
                        if releases and isinstance(releases, list):
                            return releases[0]
            except Exception:
                pass
    except Exception as exc:
        print(f'[Updater] Error fetching release from {repo}:', exc)
    return None


def check_for_updates(current_version: str = APP_VERSION,
                       preferred_repo: Optional[str] = None) -> Dict:
    """
    Check GitHub releases across configured and fallback repositories.
    Returns structured update metadata.
    """
    repos_to_try = []
    if preferred_repo and preferred_repo.strip():
        repos_to_try.append(preferred_repo.strip())
    if PRIMARY_REPO not in repos_to_try:
        repos_to_try.append(PRIMARY_REPO)
    for fb in FALLBACK_REPOS:
        if fb not in repos_to_try:
            repos_to_try.append(fb)

    release_data = None
    matched_repo = None
    for repo in repos_to_try:
        info = fetch_release_info(repo)
        if info and info.get('tag_name'):
            release_data = info
            matched_repo = repo
            break

    if not release_data:
        return {
            'success': False,
            'error': 'No release found on GitHub repository.',
            'update_available': False,
            'current_version': current_version,
            'latest_version': current_version,
        }

    tag_name = release_data.get('tag_name', '').strip()
    clean_ver = tag_name.lstrip('vV')
    release_name = release_data.get('name') or tag_name
    release_notes = release_data.get('body') or 'No release notes provided.'
    published_at = release_data.get('published_at', '')
    html_url = release_data.get('html_url', f'https://github.com/{matched_repo}/releases')
    zipball_url = release_data.get('zipball_url')

    # Analyze assets: Look for Windows .exe or .zip
    assets = release_data.get('assets', [])
    chosen_asset = None
    for a in assets:
        name = a.get('name', '').lower()
        if name.endswith('.exe') or 'fetchx' in name or 'fetchjav' in name:
            chosen_asset = a
            break
    if not chosen_asset and assets:
        for a in assets:
            name = a.get('name', '').lower()
            if name.endswith('.zip') or name.endswith('.tar.gz'):
                chosen_asset = a
                break
    if not chosen_asset and assets:
        chosen_asset = assets[0]

    asset_name = chosen_asset.get('name') if chosen_asset else f'FetchX-{clean_ver}.zip'
    asset_url = chosen_asset.get('browser_download_url') if chosen_asset else zipball_url
    asset_size = chosen_asset.get('size', 0) if chosen_asset else 0

    has_update = is_newer_version(clean_ver, current_version)

    return {
        'success': True,
        'update_available': has_update,
        'current_version': current_version,
        'latest_version': clean_ver,
        'tag_name': tag_name,
        'release_name': release_name,
        'release_notes': release_notes,
        'published_at': published_at,
        'html_url': html_url,
        'repo': matched_repo,
        'asset_name': asset_name,
        'asset_url': asset_url,
        'asset_size': asset_size,
    }


def download_update(asset_url: str,
                    target_path: str,
                    progress_callback: Optional[Callable[[int, int, float, float], None]] = None,
                    cancel_event: Optional[threading.Event] = None) -> bool:
    """
    Stream download the release asset with real-time speed and progress reporting.
    progress_callback receives (downloaded_bytes, total_bytes, speed_bytes_per_sec, percent).
    """
    req = urllib.request.Request(
        asset_url,
        headers={
            'User-Agent': f'FetchX/{APP_VERSION}',
            'Accept': 'application/octet-stream',
        }
    )
    ctx = _get_ssl_context()
    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            total_bytes = int(resp.headers.get('Content-Length') or 0)
            downloaded = 0
            start_time = time.time()
            last_calc_time = start_time
            last_calc_bytes = 0
            speed = 0.0

            os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
            with open(target_path, 'wb') as out_f:
                chunk_size = 65536  # 64 KB
                while True:
                    if cancel_event and cancel_event.is_set():
                        out_f.close()
                        if os.path.exists(target_path):
                            try:
                                os.remove(target_path)
                            except Exception:
                                pass
                        return False

                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break

                    out_f.write(chunk)
                    downloaded += len(chunk)

                    now = time.time()
                    elapsed = now - last_calc_time
                    if elapsed >= 0.25:
                        speed = (downloaded - last_calc_bytes) / elapsed
                        last_calc_time = now
                        last_calc_bytes = downloaded

                    pct = (downloaded / total_bytes * 100.0) if total_bytes > 0 else 0.0
                    if progress_callback:
                        progress_callback(downloaded, total_bytes, speed, pct)

            if progress_callback and total_bytes > 0:
                progress_callback(total_bytes, total_bytes, speed, 100.0)
            return True
    except Exception as exc:
        print('[Updater] Download error:', exc)
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
            except Exception:
                pass
        raise exc


def apply_update_and_restart(downloaded_path: str,
                             on_shutdown: Optional[Callable[[], None]] = None) -> bool:
    """
    Applies the downloaded update package and automatically restarts FetchX.
    Supports both frozen (.exe) builds and Python source distributions.
    """
    if not os.path.exists(downloaded_path):
        raise FileNotFoundError(f'Downloaded update file does not exist: {downloaded_path}')

    is_frozen = getattr(sys, 'frozen', False)
    current_exe = os.path.abspath(sys.executable)
    current_pid = os.getpid()

    if is_frozen:
        # Running as PyInstaller packaged FetchX.exe
        target_replacement = None

        if downloaded_path.lower().endswith('.zip'):
            # Extract .zip to a temp folder and locate the .exe
            extract_dir = os.path.join(tempfile.gettempdir(), f'fetchx_update_ext_{int(time.time())}')
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(downloaded_path, 'r') as zf:
                zf.extractall(extract_dir)

            for root, _dirs, files in os.walk(extract_dir):
                for f in files:
                    if f.lower() == 'fetchx.exe' or f.lower().endswith('.exe'):
                        target_replacement = os.path.join(root, f)
                        break
                if target_replacement:
                    break

            if not target_replacement:
                target_replacement = downloaded_path
        else:
            target_replacement = downloaded_path

        # Generate a standalone Windows batch updater script
        bat_script_path = os.path.join(tempfile.gettempdir(), f'fetchx_updater_{int(time.time())}.bat')
        bat_content = f"""@echo off
setlocal enabledelayedexpansion
set "PID={current_pid}"
set "SRC={target_replacement}"
set "DEST={current_exe}"

:: 1. Wait for parent process to completely terminate
:wait_loop
tasklist /fi "PID eq %PID%" 2>nul | find "%PID%" >nul
if not errorlevel 1 (
    timeout /t 1 /nobreak >nul
    goto wait_loop
)

:: 2. Small delay to release file locks
timeout /t 1 /nobreak >nul

:: 3. Overwrite target executable
copy /y "%SRC%" "%DEST%" >nul
if errorlevel 1 (
    move /y "%DEST%" "%DEST%.old" >nul
    copy /y "%SRC%" "%DEST%" >nul
)

:: 4. Launch updated executable
start "" "%DEST%"

:: 5. Clean up updater script
(goto) 2>nul & del "%~f0"
"""
        with open(bat_script_path, 'w', encoding='utf-8') as f:
            f.write(bat_content)

        # Launch detached updater script
        DETACHED_FLAGS = 0x00000008 | 0x08000000  # DETACHED_PROCESS | CREATE_NO_WINDOW
        subprocess.Popen(
            ['cmd.exe', '/c', bat_script_path],
            creationflags=DETACHED_FLAGS,
            close_fds=True
        )

        if on_shutdown:
            try:
                on_shutdown()
            except Exception:
                pass

        sys.exit(0)
        return True

    else:
        # Running as Python script in development or source mode
        if downloaded_path.lower().endswith('.zip'):
            # Extract updated python code into workspace
            target_dir = os.path.abspath(os.path.dirname(__file__))
            extract_dir = os.path.join(tempfile.gettempdir(), f'fetchx_src_ext_{int(time.time())}')
            os.makedirs(extract_dir, exist_ok=True)
            with zipfile.ZipFile(downloaded_path, 'r') as zf:
                zf.extractall(extract_dir)

            # Move files into workspace
            src_root = extract_dir
            # Handle github zipball top-level directory (e.g. repo-tag/)
            entries = os.listdir(extract_dir)
            if len(entries) == 1 and os.path.isdir(os.path.join(extract_dir, entries[0])):
                src_root = os.path.join(extract_dir, entries[0])

            for item in os.listdir(src_root):
                s = os.path.join(src_root, item)
                d = os.path.join(target_dir, item)
                if item in ('.git', '.venv', '__pycache__', 'downloads'):
                    continue
                if os.path.isdir(s):
                    if os.path.exists(d):
                        shutil.rmtree(d, ignore_errors=True)
                    shutil.copytree(s, d)
                else:
                    shutil.copy2(s, d)

            # Cleanup extract dir
            shutil.rmtree(extract_dir, ignore_errors=True)

        if on_shutdown:
            try:
                on_shutdown()
            except Exception:
                pass

        # Restart python process
        os.execl(sys.executable, sys.executable, *sys.argv)
        return True
