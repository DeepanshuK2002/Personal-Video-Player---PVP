# Live Captions

Real-time speech-to-text subtitles inside PVP+, powered by the **Windows Live Captions** app (`LiveCaptions.exe`, built into Windows 11). Live Captions hears the video's audio and its recognized text is shown live in the player's own subtitle overlay.

## Requirements

- Windows 11 22H2 (build 22621) or later
- The Live Captions app (present by default; `C:\Windows\System32\LiveCaptions.exe`)
- Volume above 5% — Live Captions needs to hear the audio
- First run for a language may download a small language file (a few minutes; the UI shows progress)

## Using it

- **Toggle**: Settings → Live Captions → *Live subtitles* button, the `Live subtitle` row in the CC menu, or press `C`
- **Language**: Settings → Live Captions → *Language* — pick the language the speaker in the video uses. Live Captions restarts itself automatically with the new language
- **Position**: Bottom / Top / Center
- **Max Lines**: caps the caption box to that many lines (long text is clamped with an ellipsis)
- **Style**: the palette icon in the Live Captions section opens a style editor **for the live captions only** (font, size, colors, background, shadow) — local subtitles keep their own palette in the Subtitles section
- **Info**: the `(i)` icon next to the palette explains how everything works
- Captions never start on their own — turn them on with the toggle, the CC menu row, or `C`

## How it works

```
Windows Live Captions  --UIA tree-->  Rust poll thread  --IPC-->  page JS  -->  overlay
```

1. On enable, the provider launches Live Captions (if not already running) and finds its window (class `LiveCaptionsDesktopWindow`).
2. A background thread polls the UI Automation tree (`Pane#CaptionsScrollViewer` → `Text#CaptionsTextBlock`) every 120 ms and forwards text changes to the page.
3. The page renders the text in the `.live-captions-overlay` element (z-index above local subtitles), applying the live-caption style, position and max-lines settings.
4. Empty gaps in recognition keep the last caption on screen; text only clears when subtitles are turned off or the file changes.

Behavioral details:

- The Live Captions window is **parked off-screen** the moment it is found (and re-parked every tick — Live Captions re-docks its bar by itself), so it never appears on screen or floats over other applications. Captions keep working regardless of which window is focused or on top.
- The window is hidden from the taskbar immediately; minimizing is deferred until captions are ready (minimizing too early can freeze Live Captions' startup).
- If the "getting ready" warmup screen hangs for more than 90 s, Live Captions is restarted once automatically.
- Only the instance the player spawned is terminated on exit/disable (by PID); a Live Captions window the user opened themselves is restored to its original position instead.

## Troubleshooting

- **Captions don't start**: open Live Captions once from the Start menu, then toggle captions again.
- **No text for a language**: the language file may still be downloading — the status shows progress (can take a few minutes).
- **Toast about volume**: raise the volume above 5% — that is Live Captions' minimum.
- **Diagnostics**: every lifecycle event (spawn, warmup, ready, terminate, panics) is appended to `C:\Users\Public\pvp_lc.txt`.

## Keyboard

| Key | Action |
|-----|--------|
| `C` | Toggle Live Captions |
