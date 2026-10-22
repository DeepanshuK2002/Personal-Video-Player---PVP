pub mod livecaptions;

use std::sync::{Arc, OnceLock};

pub use livecaptions::{current_language, speech_models_installed, start_speech_op, LiveCaptionsProvider};

pub type Emit = Arc<dyn Fn(CaptionEvent) + Send + Sync>;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum CapState {
    Unsupported,
    Setup,
    Ready,
    Error,
}

impl CapState {
    pub fn as_str(&self) -> &'static str {
        match self {
            CapState::Unsupported => "unsupported",
            CapState::Setup => "setup",
            CapState::Ready => "ready",
            CapState::Error => "error",
        }
    }
}

#[derive(Clone, Debug)]
pub struct Capability {
    pub supported: bool,
    pub reason: String,
}

#[derive(Clone, Debug)]
pub enum CaptionEvent {
    State(CapState, String),
    Update { text: String, is_final: bool },
}

pub trait CaptionProvider: Send {
    fn start(&mut self);
    fn stop(&mut self);
    fn set_language(&mut self, lang: &str);
    fn is_running(&self) -> bool;
}

static CAPABILITY: OnceLock<Capability> = OnceLock::new();

pub fn probe() -> &'static Capability {
    CAPABILITY.get_or_init(|| {
        let c = livecaptions::probe_capability();
        crate::lc_dbg(&format!(
            "probe: supported={} reason={}",
            c.supported, c.reason
        ));
        c
    })
}

pub fn looks_final(text: &str) -> bool {
    let t = text.trim_end();
    if t.is_empty() {
        return false;
    }
    matches!(
        t.chars().last(),
        Some('.' | '!' | '?' | '\u{964}' | '\u{3002}' | '\u{ff01}' | '\u{ff1f}' | '\u{2026}' | '"' | '\'' | '\u{2019}' | '\u{bb}')
    )
}

pub fn json_str(s: &str) -> String {
    let mut out = String::with_capacity(s.len() + 2);
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}

pub fn event_to_js(ev: &CaptionEvent) -> String {
    match ev {
        CaptionEvent::State(s, m) => format!(
            "pvpCaptionState({{\"s\":\"{}\",\"m\":{}}})",
            s.as_str(),
            json_str(m)
        ),
        CaptionEvent::Update { text, is_final } => format!(
            "pvpCaptionUpdate({{\"t\":{},\"f\":{}}})",
            json_str(text),
            if *is_final { "true" } else { "false" }
        ),
    }
}
