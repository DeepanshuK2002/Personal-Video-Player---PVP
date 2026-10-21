"""Provider interfaces and base classes."""
from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Literal
from app.models import (
    NormalizedTitle, NormalizedChapter, NormalizedPage, NormalizedUpdate,
    SearchOptions, ChapterOptions, TrendingOptions, UpdateOptions,
    ProviderInfo, ProviderCapabilities, ProviderStatus, AdultContentMetadata,
)


class ProviderError(Exception):
    """Error from a provider with categorization for fallback logic."""
    def __init__(
        self,
        provider_id: str,
        message: str,
        kind: Literal["timeout", "rate_limited", "network", "http", "parse", "unsupported"] = "network",
        retryable: bool = True,
    ):
        self.provider_id = provider_id
        self.kind = kind
        self.retryable = retryable
        super().__init__(f"[{provider_id}] {message}")


class BaseProvider(ABC):
    """Abstract base class for all content providers."""
    
    @abstractmethod
    def get_info(self) -> ProviderInfo:
        """Return provider metadata and capabilities."""
        pass
    
    @abstractmethod
    async def search_titles(self, query: str, options: SearchOptions) -> List["NormalizedTitle"]:
        """Search for titles by query."""
        pass
    
    @abstractmethod
    async def get_title(self, provider_id: str) -> Optional["NormalizedTitle"]:
        """Get title detail by provider's internal ID."""
        pass
    
    @abstractmethod
    async def get_chapters(self, provider_id: str, options: ChapterOptions) -> List["NormalizedChapter"]:
        """Get chapter list for a title."""
        pass
    
    @abstractmethod
    async def get_chapter_pages(self, provider_id: str, chapter_id: str) -> List["NormalizedPage"]:
        """Get page images for a chapter."""
        pass
    
    async def get_trending(self, options: TrendingOptions) -> List["NormalizedTitle"]:
        """Get trending/popular titles. Optional - raises NotImplementedError if not supported."""
        raise ProviderError(self.get_info().id, "trending not supported", "unsupported", False)
    
    async def get_latest_updates(self, options: UpdateOptions) -> List["NormalizedUpdate"]:
        """Get latest chapter updates. Optional - raises NotImplementedError if not supported."""
        raise ProviderError(self.get_info().id, "latest_updates not supported", "unsupported", False)


# Type alias for use in base class
NormalizedTitle = __import__("app.models", fromlist=["NormalizedTitle"]).NormalizedTitle
NormalizedChapter = __import__("app.models", fromlist=["NormalizedChapter"]).NormalizedChapter
NormalizedPage = __import__("app.models", fromlist=["NormalizedPage"]).NormalizedPage
NormalizedUpdate = __import__("app.models", fromlist=["NormalizedUpdate"]).NormalizedUpdate
SearchOptions = __import__("app.models", fromlist=["SearchOptions"]).SearchOptions
ChapterOptions = __import__("app.models", fromlist=["ChapterOptions"]).ChapterOptions
TrendingOptions = __import__("app.models", fromlist=["TrendingOptions"]).TrendingOptions
UpdateOptions = __import__("app.models", fromlist=["UpdateOptions"]).UpdateOptions