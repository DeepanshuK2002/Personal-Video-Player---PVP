"""Cache layer with Redis backend and in-memory fallback."""
import ujson as json
import time
from typing import Optional, Any
from app.config import settings


class Cache:
    """Multi-level cache: Redis (primary) + in-memory (fallback)."""
    
    def __init__(self):
        self._redis = None
        self._memory: Dict[str, tuple[Any, float]] = {}
        self._max_memory = settings.cache_max_size
    
    async def init(self):
        if settings.redis_url:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(settings.redis_url, decode_responses=True)
                await self._redis.ping()
            except Exception:
                self._redis = None
    
    async def close(self):
        if self._redis:
            await self._redis.close()
    
    def _make_key(self, prefix: str, key: str) -> str:
        return f"agg:{prefix}:{key}"
    
    async def get(self, prefix: str, key: str) -> Optional[Any]:
        full_key = self._make_key(prefix, key)
        
        # Try Redis first
        if self._redis:
            try:
                data = await self._redis.get(full_key)
                if data:
                    return json.loads(data)
            except Exception:
                pass
        
        # Fallback to memory
        entry = self._memory.get(full_key)
        if entry and time.time() < entry[1]:
            return entry[0]
        elif entry:
            del self._memory[full_key]
        return None
    
    async def set(self, prefix: str, key: str, value: Any, ttl: int) -> None:
        full_key = self._make_key(prefix, key)
        expires = time.time() + ttl
        
        # Try Redis first
        if self._redis:
            try:
                await self._redis.setex(full_key, ttl, json.dumps(value, default=str))
                return
            except Exception:
                pass
        
        # Fallback to memory (with size limit)
        if len(self._memory) >= self._max_memory:
            # Remove oldest entry
            oldest = min(self._memory.items(), key=lambda x: x[1][1])
            del self._memory[oldest[0]]
        
        self._memory[full_key] = (value, expires)
    
    async def delete(self, prefix: str, key: str) -> None:
        full_key = self._make_key(prefix, key)
        if self._redis:
            try:
                await self._redis.delete(full_key)
            except Exception:
                pass
        self._memory.pop(full_key, None)
    
    async def clear_prefix(self, prefix: str) -> int:
        count = 0
        full_prefix = self._make_key(prefix, "")
        if self._redis:
            try:
                keys = []
                async for key in self._redis.scan_iter(match=f"{full_prefix}*"):
                    keys.append(key)
                if keys:
                    count += await self._redis.delete(*keys)
            except Exception:
                pass
        
        to_delete = [k for k in self._memory if k.startswith(full_prefix)]
        for k in to_delete:
            del self._memory[k]
            count += 1
        return count


# Global cache instance
cache = Cache()