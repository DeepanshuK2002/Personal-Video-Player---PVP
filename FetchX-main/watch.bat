@echo off
setlocal enabledelayedexpansion

set FILE=FetchX_Desktop.py
set PID_FILE=%TEMP%\fetchx_pid.txt

echo.
echo   FetchX auto-runner
echo   Watching: %~dp0%FILE%
echo   Ctrl+C to stop
echo.

:LAUNCH
echo   ^> Launching %FILE%...
if exist "%PID_FILE%" (
    set /p OLD_PID=<"%PID_FILE%"
    taskkill /PID !OLD_PID! /F >nul 2>&1
    del "%PID_FILE%" >nul 2>&1
    timeout /t 1 /nobreak >nul
)
start /b "" python "%FILE%"
for /f "tokens=2" %%P in ('tasklist /fi "imagename eq python.exe" /fo list ^| find "PID:"') do (
    echo %%P>"%PID_FILE%"
    goto WATCH
)

:WATCH
for %%F in ("%FILE%") do set LAST=%%~tF
:LOOP
timeout /t 1 /nobreak >nul
for %%F in ("%FILE%") do set CURR=%%~tF
if not "!CURR!"=="!LAST!" (
    echo.
    echo   * %FILE% changed, restarting...
    set LAST=!CURR!
    goto LAUNCH
)
goto LOOP
