"""Configuration for Aggregator API."""
from functools import lru_cache
from typing import List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class ProviderConfig(BaseSettings):
    """Configuration for a single provider."""
    enabled: bool = True
    priority: int = 5  # 1 = highest
    timeout_seconds: float = 15.0
    max_retries: int = 2
    rate_limit_per_minute: int = 60
    
    model_config = SettingsConfigDict(env_prefix="PROVIDER_")


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # App
    app_name: str = "RedHentai Aggregator API"
    app_version: str = "1.0.0"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8766
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    
    # Redis Cache
    redis_url: Optional[str] = None
    cache_ttl_seconds: int = 300  # 5 minutes default
    cache_max_size: int = 10000
    
    # Rate Limiting
    global_rate_limit: int = 300  # requests per minute per IP
    burst_allowance: int = 50
    
    # Circuit Breaker
    circuit_failure_threshold: int = 5
    circuit_cooldown_seconds: int = 30
    
    # Provider Configs
    mangadex_enabled: bool = True
    mangadex_base_url: str = "https://api.mangadex.org"
    mangadex_timeout: float = 15.0
    
    anilist_enabled: bool = True
    anilist_base_url: str = "https://graphql.anilist.co"
    anilist_timeout: float = 20.0
    
    hentairead_enabled: bool = True
    hentairead_base_url: str = "https://hentairead.io"
    hentairead_timeout: float = 20.0
    
    hentai18_enabled: bool = True
    hentai18_base_url: str = "https://hentai18.net"
    hentai18_timeout: float = 20.0
    
    enma_enabled: bool = True
    enma_base_url: str = "http://127.0.0.1:8765"  # Local Enma sidecar
    enma_timeout: float = 30.0
    
    hentaireadmoe_enabled: bool = True
    hentaireadmoe_base_url: str = "https://hentairead.moe"
    hentaireadmoe_timeout: float = 20.0
    
    omegascans_enabled: bool = False
    hiperdex_enabled: bool = False
    
    # Adult Content Policy
    allow_confirmed_adult: bool = True
    allow_mature: bool = True
    allow_unknown: bool = False
    
    # Matching
    match_threshold: float = 0.55
    
    # Cache TTLs by operation (seconds)
    cache_ttl_search: int = 300
    cache_ttl_detail: int = 3600
    cache_ttl_chapters: int = 1800
    cache_ttl_pages: int = 86400
    cache_ttl_trending: int = 600
    cache_ttl_latest: int = 300
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


# Convenience access
settings = get_settings()