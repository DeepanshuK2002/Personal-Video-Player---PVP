//! SpotiHi core library - shared types, models, and business logic.
//!
//! This crate contains the core domain types used across all SpotiHi platforms.

pub mod models;
pub mod party;
pub mod protocol;

pub use models::*;
pub use party::*;
pub use protocol::*;