//! Presence tracking for "listening now" stats.

use dashmap::DashMap;
use std::sync::Arc;
use std::time::{Duration, Instant};

pub struct PresenceTracker {
    entries: DashMap<String, Instant>,
    timeout: Duration,
}

impl PresenceTracker {
    pub fn new() -> Self {
        Self {
            entries: DashMap::new(),
            timeout: Duration::from_secs(120),
        }
    }

    pub fn with_timeout(timeout: Duration) -> Self {
        Self {
            entries: DashMap::new(),
            timeout,
        }
    }

    pub async fn ping(&self, _req: serde_json::Value) {
        let id = uuid::Uuid::new_v4().to_string();
        self.entries.insert(id, Instant::now());
    }

    pub async fn count(&self) -> usize {
        let now = Instant::now();
        self.entries
            .iter()
            .filter(|entry| now.duration_since(*entry.value()) < self.timeout)
            .count()
    }

    pub async fn sweep(&self) {
        let now = Instant::now();
        self.entries
            .retain(|_, v| now.duration_since(*v) < self.timeout);
    }
}