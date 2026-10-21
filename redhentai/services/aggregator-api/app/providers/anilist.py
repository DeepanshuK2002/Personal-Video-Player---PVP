"""AniList provider implementation (GraphQL)."""
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
from app.core.matching import classify_anilist, infer_origin


class AniListProvider(BaseProvider):
    def __init__(self):
        self._endpoint = "https://graphql.anilist.co"
        self._site_url = "https://anilist.co"
        self._cache_ttl = 600  # 10 min
    
    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            id="anilist",
            name="AniList",
            base_url=self._endpoint,
            status="METADATA_ONLY",
            attribution="Metadata & ratings from AniList (anilist.co).",
            capabilities=ProviderCapabilities(
                search=True, get_title=True, get_chapters=False,
                get_chapter_pages=False, trending=True, latest_updates=False, ratings=True
            ),
            adult=False,
        )
    
    MEDIA_FIELDS = """
        id idMal type format status countryOfOrigin isAdult
        description(asHtml: false)
        startDate { year } updatedAt popularity meanScore averageScore chapters
        genres tags { name }
        coverImage { large extraLarge }
        title { romaji english native }
        synonyms
        staff(perPage: 1, sort: RELEVANCE) { edges { node { name { full } } role } }
    """
    
    def _map_category(self, media: Dict) -> Category:
        tag_names = [t.get("name", "").lower() for t in (media.get("tags") or [])]
        origin = (media.get("countryOfOrigin") or "").upper()
        if "manhwa" in tag_names or origin == "KR":
            return "manhwa"
        if "manhua" in tag_names or origin in ("CN", "TW"):
            return "manhua"
        return "manga"
    
    def _map_status(self, status: Optional[str]) -> Optional[PublicationStatus]:
        return {
            "FINISHED": "Completed", "RELEASING": "In Process",
            "CANCELLED": "Paused", "HIATUS": "Paused"
        }.get(status)
    
    def _normalize(self, media: Dict) -> NormalizedTitle:
        title_obj = media.get("title", {})
        title = title_obj.get("english") or title_obj.get("romaji") or title_obj.get("native") or "Untitled"
        alt = [title_obj.get("romaji"), title_obj.get("native"), *(media.get("synonyms") or [])]
        alt = [a for a in alt if a and a != title]
        
        staff = media.get("staffNodes", {}).get("edges", [])
        artists = [e.get("node", {}).get("name", {}).get("full") for e in staff if e.get("node", {}).get("name", {}).get("full")]
        tags = [t.get("name") for t in (media.get("tags") or []) if t.get("name")]
        
        adult = classify_anilist(media.get("isAdult"), infer_origin({"demographic": media.get("format"), "tags": tags}))
        
        return NormalizedTitle(
            id=f"anilist:{media['id']}",
            provider="anilist",
            provider_id=str(media["id"]),
            slug=f"anilist-{media['id']}",
            title=title,
            alternative_titles=alt,
            description=re.sub(r'<[^>]+>', '', media.get("description") or ""),
            category=self._map_category(media),
            is_adult=adult.is_adult,
            cover_image=media.get("coverImage", {}).get("large") or media.get("coverImage", {}).get("extraLarge"),
            rating=media.get("averageScore") or media.get("meanScore"),
            popularity=media.get("popularity"),
            genres=media.get("genres") or [],
            tags=tags,
            artists=artists,
            authors=artists,
            language=None,
            status=self._map_status(media.get("status")),
            chapter_count=media.get("chapters"),
            updated_at=str(media["updatedAt"] * 1000) if media.get("updatedAt") else None,
            published_at=str(media.get("startDate", {}).get("year")) if media.get("startDate", {}).get("year") else None,
            provider_url=f"https://anilist.co/manga/{media['id']}",
            readable=False,
            adult=adult,
        )
    
    async def _post(self, query: str, variables: Dict) -> Dict:
        key = f"gql:{query[:40]}:{str(variables)[:100]}"
        cached = await cache.get("anilist", key)
        if cached:
            return cached
        
        client = await get_http_client()
        data = await client.request("anilist", "POST", self._endpoint, json={"query": query, "variables": variables})
        if data.status_code != 200:
            raise ProviderError("anilist", f"HTTP {data.status_code}", "http", data.status_code >= 500)
        
        result = data.json()
        if result.get("errors"):
            raise ProviderError("anilist", result["errors"][0]["message"], "parse", False)
        return result["data"]
    
    async def search_titles(self, query: str, options: SearchOptions) -> List[NormalizedTitle]:
        limit = min(options.limit or 20, 50)
        page = max((options.offset or 0) // limit, 0) + 1
        
        sort_map = {"popular": "POPULARITY_DESC", "rating": "SCORE_DESC", "latest": "UPDATED_AT_DESC", "relevance": "SEARCH_MATCH"}
        sort = sort_map.get(options.order, "SEARCH_MATCH")
        
        category = options.categories[0] if options.categories and len(options.categories) == 1 else None
        country = "KR" if category == "manhwa" else "CN" if category == "manhua" else None
        
        variables = {
            "page": page, "perPage": limit, "sort": [sort], "type": "MANGA",
            "isAdult": options.is_adult if options.is_adult is not False else False,
        }
        if query:
            variables["search"] = query
        if country:
            variables["countryOfOrigin"] = country
        if options.genres:
            variables["genre_in"] = options.genres
        
        gql = f"query ($page: Int, $perPage: Int, $sort: [MediaSort], $search: String, $type: MediaType, $isAdult: Boolean, $genre_in: [String], $countryOfOrigin: CountryCode) {{ Page(page: $page, perPage: $perPage) {{ media(sort: $sort, search: $search, type: $type, isAdult: $isAdult, genre_in: $genre_in, countryOfOrigin: $countryOfOrigin) {{ {self.MEDIA_FIELDS} }} }} }}"
        
        data = await self._post(gql, variables)
        return [self._normalize(m) for m in data.get("Page", {}).get("media", [])]
    
    async def get_title(self, provider_id: str) -> Optional[NormalizedTitle]:
        key = f"title:{provider_id}"
        cached = await cache.get("anilist", key)
        if cached:
            return cached
        
        gql = f"query ($id: Int) {{ Media(id: $id, type: MANGA) {{ {self.MEDIA_FIELDS} }} }}"
        data = await self._post(gql, {"id": int(provider_id)})
        media = data.get("Media")
        if not media:
            return None
        result = self._normalize(media)
        await cache.set("anilist", key, result, 600)
        return result
    
    async def get_chapters(self, provider_id: str, options: ChapterOptions) -> List[NormalizedChapter]:
        raise ProviderError("anilist", "getChapters not supported", "unsupported", False)
    
    async def get_chapter_pages(self, provider_id: str, chapter_id: str) -> List[NormalizedPage]:
        raise ProviderError("anilist", "getChapterPages not supported", "unsupported", False)
    
    async def get_trending(self, options: TrendingOptions) -> List[NormalizedTitle]:
        limit = min(options.limit or 20, 50)
        gql = f"query ($page: Int, $perPage: Int, $isAdult: Boolean) {{ Page(page: $page, perPage: $perPage) {{ media(sort: [TRENDING_DESC, POPULARITY_DESC], type: MANGA, isAdult: $isAdult) {{ {self.MEDIA_FIELDS} }} }} }}"
        data = await self._post(gql, {"page": 1, "perPage": limit, "isAdult": options.is_adult if options.is_adult is not False else True})
        return [self._normalize(m) for m in data.get("Page", {}).get("media", [])]
    
    async def get_latest_updates(self, options: UpdateOptions) -> List[NormalizedUpdate]:
        raise ProviderError("anilist", "latestUpdates not supported", "unsupported", False)