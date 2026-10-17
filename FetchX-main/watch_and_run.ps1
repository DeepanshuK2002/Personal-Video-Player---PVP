# watch_and_run.ps1
# Watches FetchX_Desktop.py (and index.html) and re-launches on every save.
# Run from the project root:  .\watch_and_run.ps1

param(
    [string]$Script  = "FetchX_Desktop.py",
    [string]$WatchDir = $PSScriptRoot
)

$proc    = $null
$debounce = 1200   # ms — ignore rapid consecutive saves (e.g. editor autosave)
$lastFire = [DateTime]::MinValue

$patterns = @("*.py", "*.html")   # files to watch

function Start-App {
    if ($proc -and -not $proc.HasExited) {
        Write-Host "  ⏹  Stopping previous instance (PID $($proc.Id))…" -ForegroundColor DarkYellow
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        Start-Sleep -Milliseconds 400
    }
    Write-Host "  ▶  Launching $Script …" -ForegroundColor Green
    $script:proc = Start-Process python -ArgumentList $Script `
        -WorkingDirectory $WatchDir -PassThru
}

# ── Watcher setup ────────────────────────────────────────────────────────────
$watcher = New-Object System.IO.FileSystemWatcher
$watcher.Path                = $WatchDir
$watcher.IncludeSubdirectories = $true
$watcher.NotifyFilter        = [System.IO.NotifyFilters]::LastWrite
$watcher.EnableRaisingEvents = $false   # we'll poll manually so the handler runs on the main thread

Write-Host ""
Write-Host "  FetchX auto-runner" -ForegroundColor Cyan
Write-Host "  Watching: $WatchDir" -ForegroundColor DarkGray
Write-Host "  Ctrl+C to stop" -ForegroundColor DarkGray
Write-Host ""

# Initial launch
Start-App

# ── Poll loop ────────────────────────────────────────────────────────────────
$watcher.EnableRaisingEvents = $true
try {
    while ($true) {
        # WaitForChanged blocks for up to 500 ms then returns (TimedOut or a real event)
        $change = $watcher.WaitForChanged([System.IO.WatcherChangeTypes]::Changed, 500)

        if (-not $change.TimedOut) {
            $name = $change.Name
            $ext  = [System.IO.Path]::GetExtension($name).ToLower()

            # Only react to .py and .html files
            if ($ext -in @('.py', '.html')) {
                $now = [DateTime]::Now
                if (($now - $lastFire).TotalMilliseconds -gt $debounce) {
                    $lastFire = $now
                    Write-Host ""
                    Write-Host "  ✦ Changed: $name" -ForegroundColor Yellow
                    Start-App
                }
            }
        }

        # If the app crashed, report it but don't auto-relaunch (avoid tight loop)
        if ($proc -and $proc.HasExited -and $proc.ExitCode -ne 0) {
            Write-Host "  ✖ App exited with code $($proc.ExitCode). Save a file to restart." -ForegroundColor Red
            $proc = $null
        }
    }
} finally {
    $watcher.EnableRaisingEvents = $false
    $watcher.Dispose()
    if ($proc -and -not $proc.HasExited) {
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
    }
    Write-Host "Watcher stopped." -ForegroundColor DarkGray
}
