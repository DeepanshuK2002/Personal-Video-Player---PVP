//! WebSocket protocol definitions.

use serde::{Deserialize, Serialize};

pub const SOCKET_PROTOCOL: &str = "spotihi.v1";
pub const SOCKET_TOKEN_PREFIX: &str = "spotihi.token.";

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "snake_case")]
pub enum WsMessage {
    Hello { version: String },
    Ping,
    Pong,
    Error { message: String },
    Party(PartyEvent),
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(tag = "event", rename_all = "snake_case")]
pub enum PartyEvent {
    StateUpdate { state: crate::party::PartySyncState },
    MemberJoined { member: crate::party::PartyMember },
    MemberLeft { member_id: uuid::Uuid },
    TrackAdded { track: crate::models::Track, index: usize },
    TrackRemoved { index: usize },
    PlaybackChanged { is_playing: bool, position_ms: u64 },
}