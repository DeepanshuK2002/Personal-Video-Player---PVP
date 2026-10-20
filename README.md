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
- **Subtitle Support** - SRT/VTT with style editor (font, size, color, background)
- **Playback Speed Control** - 0.5x to 2x speed options
- **Volume Boost** - Up to 200% volume
- **Fullscreen Support** - Native fullscreen toggle
- **Progress Bar** - Click to seek, shows current/total time
- **File Association** - Open videos directly from command line or file explorer
- **stdin Support** - Pipe video data directly: `cat video.mp4 | pvp`
- **Live Captions** - *(Coming Soon)*

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
Download the latest release from the [Releases](https://github.com/DeepanshuK2002/Personal-Video-Player---PVP/releases) page.

### Build from Source
```bash
# Prerequisites: Rust 1.70+, WebView2 Runtime
git clone https://github.com/DeepanshuK2002/Personal-Video-Player---PVP.git
cd Personal-Video-Player---PVP
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
