use std::sync::{Arc, Mutex};
use std::collections::VecDeque;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LiveCaptionConfig {
    pub language: String,
    pub enabled: bool,
    pub font_size: f32,
    pub font_color: String,
    pub background_color: String,
    pub background_opacity: f32,
    pub position: CaptionPosition,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum CaptionPosition {
    Bottom,
    Top,
    Center,
}

impl Default for LiveCaptionConfig {
    fn default() -> Self {
        Self {
            language: "en-US".to_string(),
            enabled: false,
            font_size: 18.0,
            font_color: "#FFFFFF".to_string(),
            background_color: "#000000".to_string(),
            background_opacity: 0.7,
            position: CaptionPosition::Bottom,
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CaptionSegment {
    pub text: String,
    pub is_final: bool,
    pub timestamp: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CaptionSettings {
    pub font_family: String,
    pub font_size: f32,
    pub font_color: String,
    pub background_color: String,
    pub background_opacity: f32,
    pub position: CaptionPosition,
    pub max_lines: usize,
    pub line_height: f32,
}

impl Default for CaptionSettings {
    fn default() -> Self {
        Self {
            font_family: "system-ui, sans-serif".to_string(),
            font_size: 20.0,
            font_color: "#FFFFFF".to_string(),
            background_color: "#000000".to_string(),
            background_opacity: 0.75,
            position: CaptionPosition::Bottom,
            max_lines: 3,
            line_height: 1.4,
        }
    }
}

pub struct LiveCaptionsManager {
    config: Arc<Mutex<LiveCaptionConfig>>,
    settings: Arc<Mutex<CaptionSettings>>,
    caption_history: Arc<Mutex<VecDeque<CaptionSegment>>>,
    is_active: Arc<Mutex<bool>>,
}

impl LiveCaptionsManager {
    pub fn new() -> Self {
        Self {
            config: Arc::new(Mutex::new(LiveCaptionConfig::default())),
            settings: Arc::new(Mutex::new(CaptionSettings::default())),
            caption_history: Arc::new(Mutex::new(VecDeque::with_capacity(100))),
            is_active: Arc::new(Mutex::new(false)),
        }
    }

    pub fn is_active(&self) -> bool {
        *self.is_active.lock().unwrap()
    }

    pub fn set_active(&self, active: bool) {
        *self.is_active.lock().unwrap() = active;
    }

    pub fn add_caption(&self, segment: CaptionSegment) {
        let mut history = self.caption_history.lock().unwrap();
        history.push_back(segment);
        if history.len() > 100 {
            history.pop_front();
        }
    }

    pub fn get_current_caption(&self) -> Option<CaptionSegment> {
        let history = self.caption_history.lock().unwrap();
        history.back().cloned()
    }

    pub fn clear_history(&self) {
        self.caption_history.lock().unwrap().clear();
    }

    pub fn update_config(&self, config: LiveCaptionConfig) {
        *self.config.lock().unwrap() = config;
    }

    pub fn update_settings(&self, settings: CaptionSettings) {
        *self.settings.lock().unwrap() = settings;
    }

    pub fn get_config(&self) -> LiveCaptionConfig {
        self.config.lock().unwrap().clone()
    }

    pub fn get_settings(&self) -> CaptionSettings {
        self.settings.lock().unwrap().clone()
    }
}

impl Default for LiveCaptionsManager {
    fn default() -> Self {
        Self::new()
    }
}