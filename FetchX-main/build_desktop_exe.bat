@echo off
REM Build FetchX_Desktop into an optimized single windowed exe with official icon.
REM Requires: pip install pyinstaller python-vlc
cd /d "%~dp0"
python -m PyInstaller FetchX.spec --noconfirm --clean
if errorlevel 1 (
  echo BUILD FAILED
  exit /b 1
)
echo.
echo Done: dist\FetchX.exe



