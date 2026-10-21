# Personal Video Player (PVP)

<div align="center">
  <img src="assets/logo.svg" alt="PVP Logo" width="128" height="128">
  <h3>The World's Most Lightweight Video Player — Built in Rust</h3>
  <p><b>Only ~3.6 MB.</b> No bloat. No Electron. Just pure Rust performance.</p>
</div>

---

## Why PVP?

| | PVP | Typical Players |
|---|---|---|
| **Size** | **~3.6 MB** | 80–200+ MB |
| **Engine** | Rust + WebView2 | Electron / Chromium |
| **Startup** | Instant | Slow |
| **RAM Usage** | Minimal | Heavy |

PVP is a single `.exe` built entirely in Rust using [Tao](https://github.com/tauri-apps/tao) (windowing) and [Wry](https://github.com/tauri-apps/wry) (WebView2 bindings). There are no external dependencies to install — just download and play.

> **Make it yours.** This player was built exactly the way I needed it: lightweight, minimal, and focused on the features I actually use every day — not the dozens of options I'd never touch in a typical player. That's the point. Fork it, strip out what you don't need, add what you do, and shape it into *your* ideal player. The code is simple, the structure is clean, and everything is embedded in one place. If you've ever wanted a video player that does exactly what *you* want — nothing more, nothing less — start here.

---

## Features

- **Ultralightweight (~3.6 MB)** - World's most lightweight video player, built in Rust
- **Modern UI** - Clean, minimal interface with auto-hiding controls
- **Custom Titlebar** - Native-feel window controls with PVP+ branding
- **Folder Playlists** - Open a folder and play all videos in sequence with sort (time/name/duration, asc/desc)
- **Drag & Drop** - Drop videos, folders, or subtitle files
- **Subtitle Support** - SRT/VTT with style editor (font, size, color, background, shadow, box shadow, outline)
- **Live Captions** - Real-time speech-to-text subtitles powered by Windows Live Captions — 11 language models with IN USE/Download states, position (bottom/top/center/60%) and max-lines controls, dedicated style editor, never auto-starts. See [docs/live-captions.md](docs/live-captions.md)
- **Style Editors** - Separate presets for live captions and local subtitles: font, size, colors, background, text shadow, box shadow (0 to disable) and outline stroke
- **CC Menu** - Subtitle/live-caption quick menu with ON/OFF state and a palette icon straight into each style editor
- **Timeline Hover Preview** - Thumbnail + timestamp preview while scrubbing; renders above captions
- **Playback Speed Control** - 0.5x to 2x speed options
- **Volume Boost** - Up to 200% volume
- **Fullscreen Support** - Native fullscreen toggle
- **Progress Bar** - Click to seek, shows current/total time
- **File Association** - Open videos directly from command line or file explorer
- **stdin Support** - Pipe video data directly: `cat video.mp4 | pvp`

## Screenshots

<p align="center">
  <img src="docs/screenshots/live-captions.png" alt="Live captions flowing over a video" width="76%">
</p>

| Settings & About | Live Caption language models |
|---|---|
| <img src="docs/screenshots/settings.png" alt="Settings with version and About row" width="100%"> | <img src="docs/screenshots/live-captions-settings.png" alt="Language dropdown with IN USE and Download states" width="100%"> |
| **CC menu** | **Live Caption style editor** |
| <img src="docs/screenshots/cc-menu.png" alt="CC menu with Live subtitle ON and palette icons" width="100%"> | <img src="docs/screenshots/style-popup.png" alt="Style editor with shadow, box shadow and outline rows" width="100%"> |
| **Timeline hover preview** | |
| <img src="docs/screenshots/hover-preview.png" alt="Hover preview above the caption box" width="100%"> | |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play/Pause |
| `F` | Toggle Fullscreen |
| `←/→` | Seek -10s / +10s |
| `↑/↓` | Volume Up/Down |
| `M` | Mute/Unmute |
| `[ / ]` | Decrease/Increase Speed |
| `C` | Toggle Live Captions |
| `Click Video` | Play/Pause |
| `Right-click (double)` | Toggle Fullscreen |
| `Scroll Wheel` | Volume Control |

## Installation

### Download (Recommended)
Download the latest release from the [Releases](https://github.com/DeepanshuK2002/21-10-2026-Personal-Private-/releases) page.

### Build from Source
```bash
# Prerequisites: Rust 1.70+, WebView2 Runtime
git clone https://github.com/DeepanshuK2002/21-10-2026-Personal-Private-.git
cd 21-10-2026-Personal-Private-/pvp-plus
cargo build --release
```

The executable will be at `target/release/personal-video-player.exe`

## Usage

```bash
# Open a video file
personal-video-player.exe "path\to\video.mp4"

# Drag and drop a video file onto the window
# Or use the folder button in the controls
# Or drag a whole folder for a playlist
```

## Supported Formats

- MP4, M4V
- WebM
- OGG, OGV
- MKV
- AVI
- MOV
- And more (depends on system codecs)

## Architecture

PVP uses a local HTTP server to serve video files to the WebView2 engine, enabling reliable playback of local files with full seeking support (HTTP Range requests). The UI is built with vanilla HTML/CSS/JS embedded in the Rust binary.

## Tech Stack

- **Rust** - Systems programming language
- **Tao** - Window management
- **Wry** - WebView2 bindings
- **Resvg/Tiny-Skia** - SVG rendering for icons
- **HTML5 Video API** - Media playback

## License

MIT License - feel free to use, modify, and distribute.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

<div align="center">
  <sub>Built with ❤️ using Rust — ~3.6 MB of pure performance</sub>
</div>
