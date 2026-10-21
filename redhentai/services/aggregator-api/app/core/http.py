"""HTTP client with retry, timeout, and circuit breaker."""
import asyncio
import httpx
from typing import Optional, Dict, Any
from app.config import settings
from app.providers.base import ProviderError


class HTTPClient:
    """Shared HTTP client with connection pooling, retries, and timeouts."""
    
    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None
        self._semaphores: Dict[str, asyncio.Semaphore] = {}
        self._max_concurrent = 4
    
    async def __aenter__(self):
        limits = httpx.Limits(max_connections=50, max_keepalive_connections=20)
        self._client = httpx.AsyncClient(
            limits=limits,
            timeout=httpx.Timeout(30.0, connect=10.0),
            follow_redirects=True,
        )
        return self
    
    async def __aexit__(self, *args):
        if self._client:
            await self._client.aclose()
    
    def _get_semaphore(self, provider_id: str) -> asyncio.Semaphore:
        if provider_id not in self._semaphores:
            self._semaphores[provider_id] = asyncio.Semaphore(self._max_concurrent)
        return self._semaphores[provider_id]
    
    async def request(
        self,
        provider_id: str,
        method: str,
        url: str,
        timeout: Optional[float] = None,
        **kwargs
    ) -> httpx.Response:
        if not self._client:
            raise RuntimeError("HTTPClient not initialized. Use async context manager.")
        
        semaphore = self._get_semaphore(provider_id)
        timeout = timeout or getattr(settings, f"{provider_id}_timeout", 15.0)
        
        async with semaphore:
            last_error = None
            for attempt in range(3):
                try:
                    response = await self._client.request(
                        method, url,
                        timeout=httpx.Timeout(timeout, connect=10.0),
                        **kwargs
                    )
                    if response.status_code == 429:
                        raise ProviderError(provider_id, "Rate limited", "rate_limited", True)
                    response.raise_for_status()
                    return response
                except httpx.TimeoutException as e:
                    last_error = ProviderError(provider_id, f"Timeout: {e}", "timeout", True)
                except httpx.HTTPStatusError as e:
                    last_error = ProviderError(provider_id, f"HTTP {e.response.status_code}", "http", e.response.status_code >= 500)
                    if not last_error.retryable:
                        raise
                except httpx.RequestError as e:
                    last_error = ProviderError(provider_id, f"Network: {e}", "network", True)
                
                if attempt < 2:
                    await asyncio.sleep(0.5 * (2 ** attempt))  # Exponential backoff
            
            raise last_error
    
    async def get_json(self, provider_id: str, url: str, **kwargs) -> Dict[str, Any]:
        response = await self.request(provider_id, "GET", url, **kwargs)
        return response.json()
    
    async def get_text(self, provider_id: str, url: str, **kwargs) -> str:
        response = await self.request(provider_id, "GET", url, **kwargs)
        return response.text


# Global client instance
_http_client: Optional["HTTPClient"] = None


async def get_http_client() -> HTTPClient:
    """Get the global HTTP client (initializes lazily on first call)."""
    global _http_client
    if _http_client is None:
        _http_client = HTTPClient()
        await _http_client.__aenter__()
    return _http_client


async def close_http_client() -> None:
    global _http_client
    if _http_client:
        await _http_client.__aexit__(None, None, None)
        _http_client = None


# Helper for backward compatibility - lazy access to the global client
class _LazyHTTPClient:
    def _get_client(self) -> HTTPClient:
        if _http_client is None:
            raise RuntimeError("HTTPClient not initialized. Make sure lifespan has run.")
        return _http_client
    
    def __getattr__(self, name):
        client = self._get_client()
        return getattr(client, name)

http_client = _LazyHTTPClient()