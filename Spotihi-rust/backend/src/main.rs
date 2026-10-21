//! SpotiHi backend server - Rust implementation.
//!
//! Provides REST API and WebSocket endpoints for Listen Together,
//! presence tracking, and party management.

use axum::{
    extract::{Path, State},
    http::StatusCode,
    response::Json,
    routing::{get, post},
    Router,
};
use serde::{Deserialize, Serialize};
use std::sync::Arc;
use tokio::net::TcpListener;
use tower_http::cors::CorsLayer;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

mod party_store;
mod presence;

use party_store::PartyStore;
use presence::PresenceTracker;

#[derive(Clone)]
struct AppState {
    party_store: Arc<PartyStore>,
    presence: Arc<PresenceTracker>,
}

#[derive(Serialize)]
struct HealthResponse {
    status: String,
    version: String,
}

#[derive(Deserialize)]
struct CreatePartyRequest {
    host_name: String,
    host_id: Option<String>,
}

#[derive(Serialize)]
struct CreatePartyResponse {
    code: String,
    party: spotihi_core::Party,
}

#[derive(Serialize)]
struct ErrorResponse {
    error: String,
}

async fn healthz() -> Json<HealthResponse> {
    Json(HealthResponse {
        status: "ok".to_string(),
        version: env!("CARGO_PKG_VERSION").to_string(),
    })
}

async fn handle_root() -> &'static str {
    "SpotiHi Listen Together Server"
}

async fn create_party(
    State(state): State<AppState>,
    Json(req): Json<CreatePartyRequest>,
) -> Result<Json<CreatePartyResponse>, (StatusCode, Json<ErrorResponse>)> {
    let party = state.party_store.create_party(req.host_name).await;
    Ok(Json(CreatePartyResponse {
        code: party.code.clone(),
        party,
    }))
}

async fn get_party(
    State(state): State<AppState>,
    Path(code): Path<String>,
) -> Result<Json<spotihi_core::Party>, (StatusCode, Json<ErrorResponse>)> {
    match state.party_store.get_party(&code).await {
        Some(party) => Ok(Json(party)),
        None => Err((
            StatusCode::NOT_FOUND,
            Json(ErrorResponse {
                error: "Party not found".to_string(),
            }),
        )),
    }
}

async fn handle_presence(
    State(state): State<AppState>,
    Json(req): Json<serde_json::Value>,
) -> StatusCode {
    state.presence.ping(req).await;
    StatusCode::OK
}

async fn handle_live_stats(
    State(state): State<AppState>,
) -> Json<serde_json::Value> {
    let count = state.presence.count().await;
    Json(serde_json::json!({
        "count": count,
        "timestamp": chrono::Utc::now().to_rfc3339(),
    }))
}

#[tokio::main]
async fn main() {
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new(
            std::env::var("RUST_LOG").unwrap_or_else(|_| "info".into()),
        ))
        .with(tracing_subscriber::fmt::layer())
        .init();

    let party_store = Arc::new(PartyStore::new());
    let presence = Arc::new(PresenceTracker::new());

    let state = AppState {
        party_store,
        presence,
    };

    let app = Router::new()
        .route("/", get(handle_root))
        .route("/healthz", get(healthz))
        .route("/api/parties", post(create_party))
        .route("/api/parties/:code", get(get_party))
        .route("/api/presence", post(handle_presence))
        .route("/api/stats/live", get(handle_live_stats))
        .layer(CorsLayer::permissive())
        .with_state(state);

    let addr = "0.0.0.0:8080";
    tracing::info!("SpotiHi backend starting on {}", addr);

    let listener = TcpListener::bind(addr).await.unwrap();
    axum::serve(listener, app).await.unwrap();
}