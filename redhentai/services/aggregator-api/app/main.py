"""RedHentai Aggregator API - Main FastAPI Application."""
import asyncio
import json
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from app.config import settings, get_settings
from app.core.http import http_client, HTTPClient
from app.core.cache import cache, Cache
from app.core.matching import (
    group_into_canonical, reconcile_chapters, is_eligible,
    series_match_confidence, are_same_series, combine_adult_signals,
    normalize_for_match,
)
from app.providers.registry import registry
from app.providers.mangadex import MangaDexProvider
from app.providers.anilist import AniListProvider
from app.providers.hentairead import HentaiReadProvider
from app.models import (
    SearchResponse, SeriesResponse, CanonicalSeriesResponse,
    TitleDetailResponse, ChapterPagesResponse, TrendingResponse,
    LatestResponse, ProvidersResponse, HealthResponse, StatsResponse,
    SearchOptions, TrendingOptions, UpdateOptions, ChapterOptions,
    NormalizedTitle, NormalizedChapter, CanonicalChapter,
    ChapterSourceVersion, AdultContentMetadata,
)

# Global instances
settings = get_settings()
http: Optional[HTTPClient] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global http
    # Startup
    http = HTTPClient()
    await http.__aenter__()
    await cache.init()
    
    # Register providers based on config
    if settings.mangadex_enabled:
        registry.register(MangaDexProvider())
    if settings.anilist_enabled:
        registry.register(AniListProvider())
    if settings.hentairead_enabled:
        registry.register(HentaiReadProvider())
    # Add more providers here as they're implemented
    
    print(f"[OK] RedHentai Aggregator API started on {settings.host}:{settings.port}")
    print(f"   Providers: {[p.get_info().id for p in registry.get_enabled()]}")
    
    yield
    
    # Shutdown
    await http.__aexit__(None, None, None)
    await cache.close()
    print("[STOP] RedHentai Aggregator API stopped")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Hentai Manga/Manhwa Aggregator API - Aggregates content from multiple providers with canonical series grouping and chapter reconciliation.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency
async def get_client() -> HTTPClient:
    if not http:
        raise HTTPException(503, "HTTP client not initialized")
    return http


# Health & Stats
@app.get("/health", response_model=HealthResponse)
async def health():
    provider_health = {}
    for p in registry.get_enabled():
        info = p.get_info()
        provider_health[info.id] = {
            "healthy": registry.is_healthy(info.id),
            "status": info.status,
            "capabilities": info.capabilities.model_dump(),
        }
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        timestamp=datetime.utcnow(),
        providers=provider_health,
    )


@app.get("/stats", response_model=StatsResponse)
async def stats():
    return StatsResponse(
        total_series=0,  # Would need persistent storage
        total_chapters=0,
        providers_active=len(registry.get_enabled()),
        cache_size=0,
        cache_hit_rate=0.0,
    )


# Provider Registry
@app.get("/providers", response_model=ProvidersResponse)
async def list_providers():
    return ProvidersResponse(providers=registry.get_all_info())


# Search Endpoint - Returns Canonical Series
@app.get("/api/v1/search", response_model=SeriesResponse)
async def search(
    q: str = Query("", description="Search query"),
    limit: int = Query(24, ge=1, le=50),
    offset: int = Query(0, ge=0),
    categories: Optional[List[str]] = Query(None, alias="category"),
    genres: Optional[List[str]] = Query(None),
    order: str = Query("relevance", pattern="^(latest|popular|rating|relevance)$"),
    is_adult: Optional[bool] = Query(None),
):
    options = SearchOptions(
        query=q, limit=limit, offset=offset,
        categories=categories, genres=genres, order=order, is_adult=is_adult,
    )
    
    # Fan-out to all search-capable providers
    providers = registry.get_by_capability("search")
    if not providers:
        raise HTTPException(503, "No search providers available")
    
    tasks = [p.search_titles(q, options) for p in providers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_titles: List[NormalizedTitle] = []
    errors = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            errors.append(f"{providers[i].get_info().id}: {result}")
        else:
            all_titles.extend(result)
    
    # Filter by adult eligibility
    filtered = [t for t in all_titles if is_eligible(t.adult.classification)]
    
    # Deduplicate by exact normalized title
    seen = set()
    deduped = []
    for t in filtered:
        key = normalize_for_match(t.title)
        if key and key not in seen:
            seen.add(key)
            deduped.append(t)
    
    # Group into canonical series
    series = group_into_canonical(deduped)
    
    # Fetch chapters for each series
    series_with_chapters = []
    for s in series:
        chapter_inputs = []
        for mapping in s["provider_mappings"]:
            provider = registry.get(mapping["provider_id"])
            if not provider or not provider.get_info().capabilities.get_chapters:
                continue
            try:
                chapters = await provider.get_chapters(mapping["provider_series_id"], ChapterOptions(language="en", order="asc"))
                for ch in chapters:
                    chapter_inputs.append({
                        "provider_id": provider.get_info().id,
                        "provider_series_id": mapping["provider_series_id"],
                        "provider_chapter_id": ch.provider_chapter_id,
                        "label": ch.chapter_title or ch.chapter_number or f"Chapter {ch.chapter_number or '?'}",
                        "title": ch.chapter_title,
                        "volume_number": ch.volume_number,
                        "language": ch.language or "en",
                        "release_group": None,
                        "source_url": mapping["source_url"],
                        "page_access_capability": "available" if provider.get_info().capabilities.get_chapter_pages else "metadata_only",
                        "page_count": ch.page_count,
                        "published_at": ch.published_at,
                    })
            except Exception:
                continue
        
        reconciled = reconcile_chapters(s["id"], chapter_inputs)
        s["chapters"] = reconciled
        s["readable"] = any(c.source_versions and any(v.page_access_capability == "available" for v in c.source_versions) for c in reconciled)
        series_with_chapters.append(s)
    
    # Sort
    if order == "relevance":
        pass
    else:
        series_with_chapters.sort(key=lambda s: s["chapters"][-1].source_versions[0].published_at if s["chapters"] and s["chapters"][-1].source_versions else "", reverse=True)
    
    return SeriesResponse(
        series=[CanonicalSeriesResponse(**s) for s in series_with_chapters[offset:offset+limit]],
        partial=len(errors) > 0,
        errors=errors,
        total=len(series_with_chapters),
    )


# Title Detail with Chapters
@app.get("/api/v1/series/{slug}", response_model=TitleDetailResponse)
async def get_series(slug: str):
    # Resolve provider from slug
    provider_id = slug.split("-")[0] if "-" in slug else slug
    provider = registry.get(provider_id)
    if not provider:
        raise HTTPException(404, "Provider not found")
    
    raw_id = slug[len(provider_id) + 1:] if slug.startswith(f"{provider_id}-") else slug
    title = await provider.get_title(raw_id)
    if not title:
        raise HTTPException(404, "Title not found")
    
    # Get chapters from all chapter-capable providers
    providers = registry.get_by_capability("get_chapters")
    preferred = [title.provider] if title.provider in [p.get_info().id for p in providers] else []
    
    # Use the existing getChaptersForTitle logic from registry
    # For now, get from title's own provider + fallback
    chapters = await provider.get_chapters(raw_id, ChapterOptions(language="en"))
    partial = False
    
    # Try fallback if no chapters
    if not chapters:
        for p in providers:
            if p.get_info().id == provider.get_info().id:
                continue
            try:
                fallback_chapters = await p.get_chapters(raw_id, ChapterOptions(language="en"))
                if fallback_chapters:
                    chapters = fallback_chapters
                    partial = True
                    break
            except:
                continue
    
    return TitleDetailResponse(
        item=title,
        chapters=chapters,
        chapter_count=len(chapters),
        partial=partial,
    )


# Chapter Pages
@app.get("/api/v1/series/{slug}/chapters/{chapter_id}/pages", response_model=ChapterPagesResponse)
async def get_chapter_pages(slug: str, chapter_id: str):
    # Extract provider from chapter_id (format: provider:chapter_id or just chapter_id)
    if ":" in chapter_id:
        provider_id, real_chapter_id = chapter_id.split(":", 1)
    else:
        provider_id = slug.split("-")[0] if "-" in slug else slug
        real_chapter_id = chapter_id
    
    provider = registry.get(provider_id)
    if not provider or not provider.get_info().capabilities.get_chapter_pages:
        raise HTTPException(400, "Provider does not support chapter pages")
    
    pages = await provider.get_chapter_pages(provider_id, real_chapter_id)
    return ChapterPagesResponse(pages=pages)


# Trending
@app.get("/api/v1/trending", response_model=TrendingResponse)
async def trending(
    limit: int = Query(24, ge=1, le=50),
    offset: int = Query(0, ge=0),
    page: int = Query(1, ge=1),
    categories: Optional[List[str]] = Query(None, alias="category"),
    is_adult: Optional[bool] = Query(None),
    period: str = Query("all", pattern="^(daily|weekly|monthly|all)$"),
):
    resolved_offset = offset if offset > 0 else (page - 1) * limit
    providers = registry.get_by_capability("trending")
    
    tasks = [p.get_trending(TrendingOptions(limit=limit + resolved_offset, categories=categories, is_adult=is_adult)) for p in providers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_titles = []
    errors = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            errors.append(f"{providers[i].get_info().id}: {r}")
        else:
            all_titles.extend(r)
    
    # Filter & dedupe
    filtered = [t for t in all_titles if is_eligible(t.adult.classification)]
    seen = set()
    deduped = []
    for t in filtered:
        key = normalize_for_match(t.title)
        if key and key not in seen:
            seen.add(key)
            deduped.append(t)
    
    # Interleave
    stride = max(len(providers), 3)
    emitted = [False] * len(deduped)
    ordered = []
    for i in range(0, len(deduped), stride):
        ordered.append(deduped[i])
        emitted[i] = True
    for i in range(len(deduped)):
        if not emitted[i]:
            ordered.append(deduped[i])
    
    final = ordered[resolved_offset:resolved_offset + limit]
    return TrendingResponse(
        items=[t.model_dump() for t in final],
        partial=len(errors) > 0,
        errors=errors,
        total=len(ordered),
        has_more=resolved_offset + len(final) < len(ordered),
    )


# Latest Updates
@app.get("/api/v1/latest", response_model=LatestResponse)
async def latest(
    limit: int = Query(24, ge=1, le=50),
    offset: int = Query(0, ge=0),
    page: int = Query(1, ge=1),
    is_adult: Optional[bool] = Query(None),
    language: str = Query("en"),
):
    resolved_offset = offset if offset > 0 else (page - 1) * limit
    providers = registry.get_by_capability("latest_updates")
    
    tasks = [p.get_latest_updates(UpdateOptions(limit=limit + resolved_offset, is_adult=is_adult, language=language)) for p in providers]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    all_updates = []
    errors = []
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            errors.append(f"{providers[i].get_info().id}: {r}")
        else:
            all_updates.extend(r)
    
    # Filter eligible
    filtered = [u for u in all_updates if is_eligible(u.title.adult.classification)]
    filtered.sort(key=lambda u: u.chapter.published_at or "", reverse=True)
    
    final = filtered[resolved_offset:resolved_offset + limit]
    return LatestResponse(
        items=[{
            "title": u.title.model_dump(),
            "chapter": u.chapter.model_dump(),
        } for u in final],
        partial=len(errors) > 0,
        errors=errors,
        total=len(filtered),
        has_more=resolved_offset + len(final) < len(filtered),
    )


# Image Proxy
@app.get("/api/v1/image-proxy")
async def image_proxy(url: str = Query(...)):
    """Proxy images from hotlink-protected sources."""
    import httpx
    from urllib.parse import urlparse
    
    allowed_hosts = [
        "hentairead.io", "cdn-ht.mgread.io", "mgread.io",
        "hentai18.net", "cdn.hentai18.net", "media.hentai18.net",
        "nhentai.net", "t.nhentai.net", "i.nhentai.net",
    ]
    
    host = urlparse(url).netloc
    if not any(h in host for h in allowed_hosts):
        raise HTTPException(403, "Host not allowed")
    
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url, headers={"Referer": f"https://{host}/"}, timeout=30.0)
            resp.raise_for_status()
            return StreamingResponse(
                iter([resp.content]),
                media_type=resp.headers.get("content-type", "image/jpeg"),
                headers={"Cache-Control": "public, max-age=86400"},
            )
        except httpx.HTTPError as e:
            raise HTTPException(502, f"Failed to fetch image: {e}")


# Root
@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "Hentai Manga/Manhwa Aggregator API",
        "docs": "/docs",
        "health": "/health",
        "providers": [p.get_info().id for p in registry.get_enabled()],
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.host, port=settings.port)