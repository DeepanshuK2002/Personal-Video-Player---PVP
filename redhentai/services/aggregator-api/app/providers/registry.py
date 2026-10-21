"""Provider Registry - manages all providers and handles failover."""
from typing import Dict, List, Optional, Set
from app.providers.base import BaseProvider, ProviderError
from app.models import (
    ProviderInfo, NormalizedTitle, NormalizedChapter, NormalizedPage,
    NormalizedUpdate, SearchOptions, ChapterOptions, TrendingOptions, UpdateOptions,
)


class ProviderRegistry:
    """Registry of all providers with failover support."""
    
    def __init__(self):
        self._providers: Dict[str, BaseProvider] = {}
        self._enabled: Set[str] = set()
        self._circuit_failures: Dict[str, int] = {}
        self._circuit_open: Dict[str, bool] = {}
    
    def register(self, provider: BaseProvider) -> None:
        """Register a provider."""
        info = provider.get_info()
        self._providers[info.id] = provider
        if info.status != "DISABLED":
            self._enabled.add(info.id)
    
    def get(self, provider_id: str) -> Optional[BaseProvider]:
        return self._providers.get(provider_id)
    
    def get_enabled(self) -> List[BaseProvider]:
        return [self._providers[p] for p in self._enabled if p in self._providers]
    
    def get_by_capability(self, capability: str) -> List[BaseProvider]:
        """Get enabled providers that support a capability."""
        return [
            p for p in self.get_enabled()
            if getattr(p.get_info().capabilities, capability, False)
        ]
    
    def record_failure(self, provider_id: str) -> None:
        self._circuit_failures[provider_id] = self._circuit_failures.get(provider_id, 0) + 1
        if self._circuit_failures[provider_id] >= 5:
            self._circuit_open[provider_id] = True
    
    def record_success(self, provider_id: str) -> None:
        self._circuit_failures[provider_id] = 0
        self._circuit_open[provider_id] = False
    
    def is_healthy(self, provider_id: str) -> bool:
        return not self._circuit_open.get(provider_id, False)
    
    def get_all_info(self) -> List[Dict]:
        result = []
        for p in self._providers.values():
            info = p.get_info()
            result.append({
                "id": info.id,
                "name": info.name,
                "base_url": info.base_url,
                "status": info.status,
                "capabilities": info.capabilities.model_dump(),
                "adult": info.adult,
                "enabled": info.id in self._enabled,
                "healthy": self.is_healthy(info.id),
                "failures": self._circuit_failures.get(info.id, 0),
            })
        return result


# Global registry instance
registry = ProviderRegistry()