"""API Models for Aggregator API."""
from datetime import datetime
from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


# Enums
Category = Literal["manga", "manhwa", "manhua"]
PublicationStatus = Literal["Completed", "In Process", "Paused"]
AdultClassification = Literal["confirmed_adult", "mature_non_explicit", "general_audience", "unknown"]
ContentOrigin = Literal["manga", "manhwa", "manhua", "doujinshi", "other"]
ChapterType = Literal["main", "special", "oneshot", "prologue", "epilogue", "extra", "side_story", "unknown"]
PageAccessCapability = Literal["available", "link_out_only", "metadata_only", "unavailable"]
ProviderStatus = Literal["VERIFIED_AND_AVAILABLE", "AUTHORIZED_WITH_RESTRICTIONS", "METADATA_ONLY", "LINK_OUT_ONLY", "SELF_HOST_REQUIRED", "UNAVAILABLE", "NOT_AUTHORIZED_FOR_INTENDED_USE", "DISABLED"]


class AdultContentMetadata(BaseModel):
    classification: AdultClassification
    is_adult: bool
    is_explicit: bool
    origin: ContentOrigin
    source_provider: str
    source_classification: Optional[str] = None
    reason: Optional[str] = None


class ProviderCapabilities(BaseModel):
    search: bool
    get_title: bool
    get_chapters: bool
    get_chapter_pages: bool
    trending: bool
    latest_updates: bool
    ratings: bool


class ProviderInfo(BaseModel):
    id: str
    name: str
    base_url: str
    status: ProviderStatus
    attribution: Optional[str] = None
    capabilities: ProviderCapabilities
    adult: bool


class SearchOptions(BaseModel):
    query: Optional[str] = None
    limit: int = 24
    offset: int = 0
    categories: Optional[List[Category]] = None
    genres: Optional[List[str]] = None
    status: Optional[PublicationStatus] = None
    is_adult: Optional[bool] = None
    language: Optional[str] = None
    order: Literal["latest", "popular", "rating", "relevance"] = "relevance"


class ChapterOptions(BaseModel):
    language: Optional[str] = None
    limit: Optional[int] = None
    offset: int = 0
    order: Literal["asc", "desc"] = "asc"


class TrendingOptions(BaseModel):
    window: Literal["daily", "weekly", "monthly", "all"] = "all"
    limit: int = 24
    categories: Optional[List[Category]] = None
    is_adult: Optional[bool] = None


class UpdateOptions(BaseModel):
    limit: int = 24
    categories: Optional[List[Category]] = None
    is_adult: Optional[bool] = None
    language: Optional[str] = None


# Response Models
class NormalizedTitle(BaseModel):
    id: str
    provider: str
    provider_id: str
    slug: str
    title: str
    alternative_titles: List[str] = []
    description: Optional[str] = None
    category: Optional[Category] = None
    is_adult: bool
    cover_image: Optional[str] = None
    rating: Optional[float] = None
    popularity: Optional[float] = None
    genres: List[str] = []
    tags: List[str] = []
    artists: List[str] = []
    authors: List[str] = []
    language: Optional[str] = None
    status: Optional[PublicationStatus] = None
    chapter_count: Optional[int] = None
    updated_at: Optional[str] = None
    published_at: Optional[str] = None
    provider_url: Optional[str] = None
    readable: bool
    adult: AdultContentMetadata
    original_language: Optional[str] = None
    colored: Optional[bool] = None


class NormalizedChapter(BaseModel):
    id: str
    title_id: str
    provider: str
    provider_chapter_id: str
    chapter_number: Optional[str] = None
    chapter_title: Optional[str] = None
    language: Optional[str] = None
    published_at: Optional[str] = None
    page_count: Optional[int] = None
    image_url: str = ""
    width: Optional[int] = None
    height: Optional[int] = None
    expires_at: Optional[str] = None
    readable: bool = False
    volume_number: Optional[str] = None


class NormalizedPage(BaseModel):
    index: int
    image_url: str
    width: Optional[int] = None
    height: Optional[int] = None
    expires_at: Optional[str] = None


class NormalizedUpdate(BaseModel):
    title: NormalizedTitle
    chapter: NormalizedChapter


class ProviderSeriesMapping(BaseModel):
    provider_id: str
    provider_series_id: str
    source_url: Optional[str] = None
    capabilities: Dict[str, bool] = {}


class CanonicalChapter(BaseModel):
    id: str
    series_id: str
    chapter_number: Optional[float] = None
    label: str
    volume_number: Optional[str] = None
    title: Optional[str] = None
    language: str
    chapter_type: ChapterType
    source_versions: List["ChapterSourceVersion"] = []
    sort_key: float


class ChapterSourceVersion(BaseModel):
    provider_id: str
    provider_series_id: str
    provider_chapter_id: str
    chapter_number: Optional[str] = None
    volume_number: Optional[str] = None
    title: Optional[str] = None
    language: str
    release_group: Optional[str] = None
    source_url: Optional[str] = None
    page_access_capability: PageAccessCapability
    page_count: Optional[int] = None
    published_at: Optional[str] = None


# Response wrappers
class SearchResponse(BaseModel):
    titles: List[NormalizedTitle]
    partial: bool = False
    errors: List[str] = []
    total: int


class SeriesResponse(BaseModel):
    series: List["CanonicalSeriesResponse"]
    partial: bool = False
    errors: List[str] = []
    total: int


class CanonicalSeriesResponse(BaseModel):
    id: str
    slug: str
    title: str
    alternative_titles: List[str] = []
    category: Category
    origin: ContentOrigin
    is_adult: bool
    adult: AdultContentMetadata
    description: Optional[str] = None
    cover_url: Optional[str] = None
    genres: List[str] = []
    tags: List[str] = []
    authors: List[str] = []
    artists: List[str] = []
    status: Optional[PublicationStatus] = None
    original_language: Optional[str] = None
    available_languages: List[str] = []
    release_year: Optional[int] = None
    rating: Optional[float] = None
    popularity: Optional[float] = None
    provider_mappings: List[ProviderSeriesMapping] = []
    created_at: str
    updated_at: Optional[str] = None
    chapters: List[CanonicalChapter] = []
    readable: bool = False
    canonical_id: Optional[str] = None
    readable_chapters: Optional[int] = None
    provider_mappings: List[ProviderSeriesMapping] = []


class TitleDetailResponse(BaseModel):
    item: NormalizedTitle
    chapters: List[NormalizedChapter]
    chapter_count: int
    partial: bool


class ChapterPagesResponse(BaseModel):
    pages: List[NormalizedPage]


class TrendingResponse(BaseModel):
    items: List[Dict[str, Any]]
    partial: bool = False
    errors: List[str] = []
    total: int
    has_more: bool = False


class LatestResponse(BaseModel):
    items: List[Dict[str, Any]]
    partial: bool = False
    errors: List[str] = []
    total: int
    has_more: bool = False


class ProvidersResponse(BaseModel):
    providers: List[ProviderInfo]


class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    providers: Dict[str, Dict[str, Any]] = {}


class StatsResponse(BaseModel):
    total_series: int
    total_chapters: int
    providers_active: int
    cache_size: int
    cache_hit_rate: float


CanonicalSeriesResponse.model_rebuild()