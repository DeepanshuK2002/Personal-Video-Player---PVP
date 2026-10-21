//! In-memory party store.

use dashmap::DashMap;
use spotihi_core::{Party, PartyMember, PartyTrack, Track};
use std::sync::Arc;
use uuid::Uuid;

pub struct PartyStore {
    parties: DashMap<String, Party>,
}

impl PartyStore {
    pub fn new() -> Self {
        Self {
            parties: DashMap::new(),
        }
    }

    pub async fn create_party(&self, host_name: String) -> Party {
        let code = generate_party_code();
        let host_id = Uuid::new_v4();
        let party = Party {
            code: code.clone(),
            host_id,
            members: vec![PartyMember {
                id: host_id,
                name: host_name,
                avatar_url: None,
                is_host: true,
            }],
            queue: Vec::new(),
            current_track_index: None,
            is_playing: false,
            position_ms: 0,
            created_at: chrono::Utc::now(),
        };
        self.parties.insert(code, party.clone());
        party
    }

    pub async fn get_party(&self, code: &str) -> Option<Party> {
        self.parties.get(code).map(|p| p.clone())
    }

    pub async fn add_track(&self, code: &str, track: Track, member_id: Uuid) -> bool {
        if let Some(mut party) = self.parties.get_mut(code) {
            party.queue.push(PartyTrack {
                track,
                added_by: member_id,
                added_at: chrono::Utc::now(),
            });
            true
        } else {
            false
        }
    }

    pub async fn remove_track(&self, code: &str, index: usize) -> bool {
        if let Some(mut party) = self.parties.get_mut(code) {
            if index < party.queue.len() {
                party.queue.remove(index);
                true
            } else {
                false
            }
        } else {
            false
        }
    }
}

fn generate_party_code() -> String {
    use rand::Rng;
    const CHARSET: &[u8] = b"ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    let mut rng = rand::thread_rng();
    (0..6)
        .map(|_| {
            let idx = rng.gen_range(0..CHARSET.len());
            CHARSET[idx] as char
        })
        .collect()
}