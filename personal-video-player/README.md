# Personal Video Player (PVP)

<div align="center">
  <img src="assets/logo.svg" alt="PVP Logo" width="128" height="128">
  <h3>A lightweight, modern video player built with Rust</h3>
</div>

---

## Features

- **Lightweight & Fast** - Built with Rust using Tao and Wry (WebView2)
- **Modern UI** - Clean, minimal interface with auto-hiding controls
- **Drag & Drop** - Simply drop video files to play
- **Keyboard Shortcuts** - Full keyboard control support
- **Playback Speed Control** - 0.5x to 2x speed options
- **Volume Boost** - Up to 200% volume
- **Fullscreen Support** - Native fullscreen toggle
- **Progress Bar** - Click to seek, shows current/total time
- **File Association** - Open videos directly from command line or file explorer
- **stdin Support** - Pipe video data directly: `cat video.mp4 | pvp`

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Space` | Play/Pause |
| `F` | Toggle Fullscreen |
| `←/→` | Seek -10s / +10s |
| `↑/↓` | Volume Up/Down |
| `M` | Mute/Unmute |
| `[ / ]` | Decrease/Increase Speed |
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
  <sub>Built with ❤️ using Rust</sub>
</div>