//! Core data models for SpotiHi.

use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// A track in the music library.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Track {
    pub id: String,
    pub title: String,
    pub artist: String,
    pub album: Option<String>,
    pub duration_ms: u64,
    pub thumbnail_url: Option<String>,
    pub source: TrackSource,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum TrackSource {
    YouTube,
    Spotify,
    Local,
    WebDav,
    Smb,
}

/// A playlist containing tracks.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Playlist {
    pub id: Uuid,
    pub name: String,
    pub description: Option<String>,
    pub tracks: Vec<Track>,
    pub created_at: chrono::DateTime<chrono::Utc>,
    pub updated_at: chrono::DateTime<chrono::Utc>,
}

/// A user account.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct User {
    pub id: Uuid,
    pub name: String,
    pub email: Option<String>,
    pub avatar_url: Option<String>,
}

/// Playback state.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PlaybackState {
    pub track: Option<Track>,
    pub position_ms: u64,
    pub is_playing: bool,
    pub volume: f32,
    pub repeat_mode: RepeatMode,
    pub shuffle: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum RepeatMode {
    Off,
    One,
    All,
}

impl Default for PlaybackState {
    fn default() -> Self {
        Self {
            track: None,
            position_ms: 0,
            is_playing: false,
            volume: 1.0,
            repeat_mode: RepeatMode::Off,
            shuffle: false,
        }
    }
}