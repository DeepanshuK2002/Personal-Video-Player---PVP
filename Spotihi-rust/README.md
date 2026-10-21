# SpotiHi - Rust Rebuild

This is the Rust rebuild of the SpotiHi (formerly BitChord) music player.

## Structure

- `core/` - Shared core library (models, party, protocol)
- `backend/` - Axum-based backend server (Listen Together, presence)
- `web/` - Leptos-based web frontend (WASM)
- `desktop/` - Tauri-based desktop app (in progress)

## Building

### Prerequisites
- Rust 1.70+ (install via rustup)
- For web: `rustup target add wasm32-unknown-unknown`

### Backend
```bash
cargo build -p spotihi-backend
cargo run -p spotihi-backend
```

### Web (WASM)
```bash
cargo build --target wasm32-unknown-unknown -p spotihi-web
```

### Core Library
```bash
cargo build -p spotihi-core
cargo test -p spotihi-core
```

## Mobile (Android/TV/Wear OS)

Mobile platforms will use Rust via the Android NDK with JNI bindings.
The core library provides the shared business logic that can be called from
Kotlin via JNI. This approach is documented but not yet implemented.

## License

GPL-3.0
