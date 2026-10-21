"""MangaDex provider implementation."""
import re
from typing import List, Optional, Dict, Any
from app.providers.base import BaseProvider, ProviderError
from app.models import (
    NormalizedTitle, NormalizedChapter, NormalizedPage, NormalizedUpdate,
    SearchOptions, ChapterOptions, TrendingOptions, UpdateOptions,
    ProviderInfo, ProviderCapabilities, ProviderStatus, Category, PublicationStatus,
)
from app.core.http import get_http_client
from app.core.cache import cache
from app.core.matching import classify_mangadex, infer_origin


class MangaDexProvider(BaseProvider):
    def __init__(self):
        self._base_url = "https://api.mangadex.org"
        self._site_url = "https://mangadex.org"
        self._cache_ttl = 300  # 5 min
        self._pages_ttl = 3600  # 1 hour
    
    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            id="mangadex",
            name="MangaDex",
            base_url=self._base_url,
            status="VERIFIED_AND_AVAILABLE",
            attribution="Content sourced from MangaDex (mangadex.org).",
            capabilities=ProviderCapabilities(
                search=True, get_title=True, get_chapters=True,
                get_chapter_pages=True, trending=True, latest_updates=True, ratings=False
            ),
            adult=False,
        )
    
    def _build_params(self, options: SearchOptions, adult_only: bool = True) -> Dict[str, Any]:
        params = {
            "limit": str(min(options.limit or 20, 50)),
            "offset": str(options.offset or 0),
            "includes[]": "cover_art",
        }
        if options.query:
            params["title"] = options.query
        
        order_map = {
            "popular": "followedCount",
            "rating": "rating",
            "latest": "latestUploadedChapter",
            "relevance": "relevance",
        }
        params[f"order[{order_map.get(options.order, 'latestUploadedChapter')}]"] = "desc"
        
        if adult_only:
            for r in ["pornographic", "erotica", "suggestive"]:
                params.setdefault("contentRating[]", []).append(r)
        elif options.is_adult is False:
            params.setdefault("contentRating[]", []).extend(["safe", "suggestive"])
        
        if options.status:
            status_map = {"Completed": "completed", "In Process": "ongoing", "Paused": "hiatus"}
            params["status[]"] = status_map.get(options.status, "hiatus")
        
        if options.language:
            params["availableTranslatedLanguage[]"] = options.language
        
        return params
    
    def _pick_localized(self, obj: Optional[Dict]) -> Optional[str]:
        if not obj:
            return None
        return obj.get("en") or next((v for v in obj.values() if v), None)
    
    def _normalize(self, manga: Dict) -> NormalizedTitle:
        attrs = manga.get("attributes", {})
        rels = manga.get("relationships", [])
        
        title = self._pick_localized(attrs.get("title")) or "Untitled"
        alt = [self._pick_localized(t) for t in (attrs.get("altTitles") or []) if self._pick_localized(t) != title]
        
        tags = [self._pick_localized(t.get("attributes", {}).get("name")) for t in attrs.get("tags", [])]
        tags = [t for t in tags if t]
        
        demo = attrs.get("publicationDemographic")
        tag_names = tags
        category = "manhwa" if demo in ("shoujo", "josei") or "manhwa" in tag_names else \
                   "manhua" if "manhua" in tag_names else "manga"
        
        status_map = {"completed": "Completed", "ongoing": "In Process", "cancelled": "Paused", "hiatus": "Paused"}
        status = status_map.get(attrs.get("status"))
        
        cover_rel = next((r for r in rels if r["type"] == "cover_art"), None)
        cover_url = None
        if cover_rel and cover_rel.get("attributes", {}).get("fileName"):
            cover_url = f"https://uploads.mangadex.org/covers/{manga['id']}/{cover_rel['attributes']['fileName']}.256.jpg"
        
        adult = classify_mangadex(attrs.get("contentRating"), infer_origin({"demographic": demo, "tags": tag_names}))
        
        return NormalizedTitle(
            id=f"mangadex:{manga['id']}",
            provider="mangadex",
            provider_id=manga["id"],
            slug=f"mangadex-{manga['id']}",
            title=title,
            alternative_titles=alt,
            description=self._pick_localized(attrs.get("description")),
            category=category,
            is_adult=adult.is_adult,
            cover_image=cover_url,
            rating=None,
            popularity=None,
            genres=[],
            tags=tags,
            artists=[],
            authors=[],
            language=None,
            status=status,
            chapter_count=attrs.get("chapters"),
            updated_at=attrs.get("latestUploadedChapter"),
            published_at=str(attrs.get("year")) if attrs.get("year") else None,
            provider_url=f"{self._site_url}/title/{manga['id']}",
            readable=True,
            adult=adult,
        )
    
    async def search_titles(self, query: str, options: SearchOptions) -> List[NormalizedTitle]:
        params = self._build_params(options)
        key = f"search:{query}:{options.offset}:{options.limit}:{options.order}"
        cached = await cache.get("mangadex", key)
        if cached:
            return cached
        
        client = await get_http_client()
        data = await client.get_json("mangadex", f"{self._base_url}/manga", params=params)
        results = [self._normalize(m) for m in data.get("data", [])]
        await cache.set("mangadex", key, results, 300)
        return results
    
    async def get_title(self, provider_id: str) -> Optional[NormalizedTitle]:
        key = f"title:{provider_id}"
        cached = await cache.get("mangadex", key)
        if cached:
            return cached
        
        client = await get_http_client()
        data = await client.get_json("mangadex", f"{self._base_url}/manga/{provider_id}", params={"includes[]": "cover_art"})
        manga = data.get("data")
        if isinstance(manga, list):
            manga = manga[0] if manga else None
        if not manga:
            return None
        result = self._normalize(manga)
        await cache.set("mangadex", key, result, 3600)
        return result
    
    async def get_chapters(self, provider_id: str, options: ChapterOptions) -> List[NormalizedChapter]:
        params = {
            "limit": str(min(options.limit or 500, 500)),
            "order[chapter]": options.order or "asc",
        }
        if options.language:
            params["translatedLanguage[]"] = options.language
        for r in ["pornographic", "erotica", "suggestive"]:
            params.setdefault("contentRating[]", []).append(r)
        
        key = f"chapters:{provider_id}:{options.language}:{options.order}"
        cached = await cache.get("mangadex", key)
        if cached:
            return cached
        
        client = await get_http_client()
        data = await client.get_json("mangadex", f"{self._base_url}/manga/{provider_id}/feed", params=params)
        results = []
        for ch in data.get("data", []):
            attrs = ch.get("attributes", {})
            results.append(NormalizedChapter(
                id=f"mangadex:{ch['id']}",
                title_id=f"mangadex:{provider_id}",
                provider="mangadex",
                provider_chapter_id=ch["id"],
                chapter_number=attrs.get("chapter"),
                chapter_title=attrs.get("title"),
                language=attrs.get("translatedLanguage"),
                published_at=attrs.get("readableAt") or attrs.get("publishAt"),
                page_count=attrs.get("pages"),
                image_url="",
                readable=attrs.get("pages", 0) > 0,
            ))
        await cache.set("mangadex", key, results, 300)
        return results
    
    async def get_chapter_pages(self, provider_id: str, chapter_id: str) -> List[NormalizedPage]:
        key = f"pages:{chapter_id}"
        cached = await cache.get("mangadex", key)
        if cached:
            return cached
        
        client = await get_http_client()
        data = await client.get_json("mangadex", f"{self._base_url}/at-home/server/{chapter_id}")
        base = data.get("baseUrl")
        hash_ = data.get("chapter", {}).get("hash")
        files = data.get("chapter", {}).get("data", [])
        if not base or not hash_ or not files:
            raise ProviderError("mangadex", "no pages available", "http", False)
        
        pages = [NormalizedPage(index=i, image_url=f"{base}/data/{hash_}/{f}") for i, f in enumerate(files)]
        await cache.set("mangadex", key, pages, 3600)
        return pages
    
    async def get_trending(self, options: TrendingOptions) -> List[NormalizedTitle]:
        return await self.search_titles("", SearchOptions(
            limit=options.limit, categories=options.categories,
            is_adult=options.is_adult, order="popular"
        ))
    
    async def get_latest_updates(self, options: UpdateOptions) -> List[NormalizedUpdate]:
        params = {
            "limit": str(min(options.limit or 20, 50)),
            "order[readableAt]": "desc",
            "includes[]": "manga",
            "includes[]": "cover_art",
        }
        for r in ["pornographic", "erotica", "suggestive"]:
            params.setdefault("contentRating[]", []).append(r)
        if options.language:
            params["translatedLanguage[]"] = options.language
        
        key = f"latest:{options.limit}:{options.language}"
        cached = await cache.get("mangadex", key)
        if cached:
            return cached
        
        client = await get_http_client()
        data = await client.get_json("mangadex", f"{self._base_url}/chapter", params=params)
        chapters = data.get("data", [])
        
        manga_ids = []
        seen = set()
        for ch in chapters:
            manga_rel = next((r for r in ch.get("relationships", []) if r["type"] == "manga"), None)
            if manga_rel and manga_rel["id"] not in seen:
                seen.add(manga_rel["id"])
                manga_ids.append(manga_rel["id"])
            if len(manga_ids) >= options.limit:
                break
        
        if not manga_ids:
            return []
        
        manga_params = {"includes[]": "cover_art"}
        for mid in manga_ids:
            manga_params.setdefault("ids[]", []).append(mid)
        for r in ["pornographic", "erotica", "suggestive"]:
            manga_params.setdefault("contentRating[]", []).append(r)
        
        client = await get_http_client()
        manga_data = await client.get_json("mangadex", f"{self._base_url}/manga", params=manga_params)
        manga_map = {m["id"]: self._normalize(m) for m in manga_data.get("data", [])}
        
        updates = []
        seen_titles = set()
        for ch in chapters:
            manga_rel = next((r for r in ch.get("relationships", []) if r["type"] == "manga"), None)
            if not manga_rel or manga_rel["id"] in seen_titles:
                continue
            title = manga_map.get(manga_rel["id"])
            if not title:
                continue
            seen_titles.add(manga_rel["id"])
            attrs = ch.get("attributes", {})
            updates.append(NormalizedUpdate(
                title=title,
                chapter=NormalizedChapter(
                    id=f"mangadex:{ch['id']}",
                    title_id=title.id,
                    provider="mangadex",
                    provider_chapter_id=ch["id"],
                    chapter_number=attrs.get("chapter"),
                    chapter_title=attrs.get("title"),
                    language=attrs.get("translatedLanguage"),
                    published_at=attrs.get("readableAt") or attrs.get("publishAt"),
                    page_count=attrs.get("pages"),
                    image_url="",
                    readable=attrs.get("pages", 0) > 0,
                )
            ))
            if len(updates) >= options.limit:
                break
        
        await cache.set("mangadex", key, updates, 300)
        return updates