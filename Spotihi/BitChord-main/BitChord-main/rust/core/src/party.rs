//! Party / Listen Together models.

use serde::{Deserialize, Serialize};
use uuid::Uuid;

/// A party (listening session).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Party {
    pub code: String,
    pub host_id: Uuid,
    pub members: Vec<PartyMember>,
    pub queue: Vec<PartyTrack>,
    pub current_track_index: Option<usize>,
    pub is_playing: bool,
    pub position_ms: u64,
    pub created_at: chrono::DateTime<chrono::Utc>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PartyMember {
    pub id: Uuid,
    pub name: String,
    pub avatar_url: Option<String>,
    pub is_host: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PartyTrack {
    pub track: super::models::Track,
    pub added_by: Uuid,
    pub added_at: chrono::DateTime<chrono::Utc>,
}

/// Messages exchanged over WebSocket.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum PartyMessage {
    Join { member: PartyMember },
    Leave { member_id: Uuid },
    Play { position_ms: u64 },
    Pause { position_ms: u64 },
    Seek { position_ms: u64 },
    AddTrack { track: super::models::Track },
    RemoveTrack { index: usize },
    ReorderQueue { from: usize, to: usize },
    Chat { member_id: Uuid, text: String },
    Sync { state: PartySyncState },
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct PartySyncState {
    pub current_track_index: Option<usize>,
    pub is_playing: bool,
    pub position_ms: u64,
    pub queue: Vec<PartyTrack>,
    pub members: Vec<PartyMember>,
}