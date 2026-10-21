"""Enma source adapter for nhentai, built on nhentai's official public API v2.

Why this module exists
----------------------
Enma's bundled NHentai adapter targets the legacy endpoints (``/api/gallery/*``,
``/api/galleries/*``). Those now answer::

    403 Use new API https://nhentai.net/api/v2/docs

nhentai publishes a documented REST API (OpenAPI spec at
``https://nhentai.net/api/v2/openapi.json``) and explicitly asks clients to use
it with a descriptive User-Agent. This module keeps Enma's ``IMangaRepository``
contract — so Enma's use cases, entities, error types and caching keep working —
while speaking API v2 instead of the retired one.

Access policy used by READHENTAI
--------------------------------
* public, documented endpoints only: no cookies, no challenge solving, no TLS
  fingerprinting, no HTML scraping;
* the published rate limits are enforced client-side with a sliding window per
  endpoint family (see RATE_LIMITS) — when a bucket is exhausted the adapter
  raises Enma's ``ExceedRateLimit`` instead of hammering the API;
* an optional API key (``NHENTAI_API_KEY``, created at
  https://nhentai.net/user/settings#apikeys) or user token (``NHENTAI_USER_TOKEN``)
  is sent as ``Authorization: Key …`` / ``Authorization: User …`` and selects the
  higher limits the same document publishes;
* image URLs are built from the official CDN configuration endpoint
  (``/api/v2/cdn``) — pages from the image servers, covers/thumbs from the thumb
  servers (verified: image servers drop cover requests, thumb servers serve them).
"""

from __future__ import annotations

import os
import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional, Union
from urllib.parse import urljoin

import requests
from expiringdict import ExpiringDict

from enma import IMangaRepository
from enma.application.core.handlers.error import (
    ExceedRateLimit,
    Forbidden,
    InvalidConfig,
    InvalidRequest,
    NotFound,
    Unknown,
)
from enma.domain.entities.author_page import AuthorPage
from enma.domain.entities.manga import (
    MIME,
    Author,
    Chapter,
    Genre,
    Image,
    Manga,
    SymbolicLink,
    Tag,
    Title,
)
from enma.domain.entities.pagination import Pagination, Thumb
from enma.domain.entities.search_result import SearchResult
from enma.domain.utils import mime as mime_util

API_BASE = os.getenv("NHENTAI_API_BASE", "https://nhentai.net/api/v2")
WEB_BASE = "https://nhentai.net"

DEFAULT_USER_AGENT = "readhentai-aggregator/1.0 (local development; see project repository)"

# Published anon limits (requests / minute / IP) from /api/v2/openapi.json.
ANON_LIMITS = {"search": 10, "list": 15, "popular": 8, "detail": 20, "random": 20, "cdn": 60}
# Published limits when authenticating with an API key or user token.
AUTH_LIMITS = {"search": 20, "list": 30, "popular": 8, "detail": 45, "random": 30, "cdn": 60}

VALID_SORTS = {"date", "popular", "popular-today", "popular-week", "popular-month"}

# v2 tag types -> Enma's Tag.type literals (parody is surfaced as "related",
# exactly like Enma's own NHentai adapter did).
TAG_TYPE_MAP = {"character": "character", "parody": "related", "category": "category"}


class _SlidingWindow:
    """Fixed-window-free request counter: keeps timestamps, drops expired ones."""

    def __init__(self, limit: int, window_seconds: int = 60) -> None:
        self.limit = max(1, int(limit))
        self.window = float(window_seconds)
        self._stamps: deque[float] = deque()
        self._lock = threading.Lock()

    def try_acquire(self) -> bool:
        now = time.monotonic()
        with self._lock:
            while self._stamps and now - self._stamps[0] >= self.window:
                self._stamps.popleft()
            if len(self._stamps) >= self.limit:
                return False
            self._stamps.append(now)
            return True

    def seconds_until_next_slot(self) -> float:
        with self._lock:
            if not self._stamps or len(self._stamps) < self.limit:
                return 0.0
            oldest = self._stamps[0]
            return max(0.0, self.window - (time.monotonic() - oldest))


def _mime_for(path: str) -> MIME:
    ext = path.rsplit(".", 1)[-1].upper() if "." in path else "JPG"
    return mime_util.get_mime_safelly(ext) or MIME.J


def _map_sort(sort: Any) -> str:
    """Map Enma's legacy sort values onto the v2 enum. Unknown -> newest."""
    value = getattr(sort, "value", sort)
    if value in (None, "", "recent", "date"):
        return "date"
    if isinstance(value, str) and value in VALID_SORTS:
        return value
    return "date"


class NHentaiV2(IMangaRepository):
    """Enma repository backed by nhentai's official API v2."""

    def __init__(self, config: Optional[dict[str, Any]] = None) -> None:
        self.__session = requests.Session()
        self.__config: dict[str, Any] = {}
        self.__cdn_lock = threading.Lock()
        self.__cdn_cache: tuple[float, tuple[str, str]] | None = None
        self.__details = ExpiringDict(
            max_len=50,
            max_age_seconds=int(os.getenv("ENMA_CACHING_GET_TTL_IN_SECONDS", 300)),
            items=None,
        )
        self.__windows: dict[str, _SlidingWindow] = {}
        self._reset_windows()
        if config is not None:
            self.set_config(config=config)

    # ------------------------------------------------------------------ #
    # Config / plumbing                                                   #
    # ------------------------------------------------------------------ #

    def set_config(self, config: Any) -> None:
        if config is None:
            self.__config = {}
            self._reset_windows()
            return
        if not isinstance(config, dict):
            raise InvalidConfig(message="NHentaiV2 config must be a dict of string keys.")
        self.__config = {k: v for k, v in config.items() if v}
        self._reset_windows()

    def _reset_windows(self) -> None:
        limits = AUTH_LIMITS if self._api_key() or self._user_token() else ANON_LIMITS
        self.__windows = {name: _SlidingWindow(limit) for name, limit in limits.items()}

    def _api_key(self) -> Optional[str]:
        return self.__config.get("api_key") or os.getenv("NHENTAI_API_KEY") or None

    def _user_token(self) -> Optional[str]:
        return self.__config.get("user_token") or os.getenv("NHENTAI_USER_TOKEN") or None

    def _headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": self.__config.get("user_agent")
            or os.getenv("NHENTAI_USER_AGENT")
            or DEFAULT_USER_AGENT,
            "Accept": "application/json",
        }
        if self._api_key():
            headers["Authorization"] = f"Key {self._api_key()}"
        elif self._user_token():
            headers["Authorization"] = f"User {self._user_token()}"
        return headers

    def _rate_limit(self, bucket: str) -> None:
        window = self.__windows.get(bucket) or _SlidingWindow(ANON_LIMITS.get(bucket, 10))
        if not window.try_acquire():
            raise ExceedRateLimit(
                message=f"nhentai API v2 {bucket!r} budget exhausted "
                        f"({window.limit}/min); retry in "
                        f"{window.seconds_until_next_slot():.0f}s."
            )

    def _get(self, path: str, bucket: str, params: Optional[dict[str, Any]] = None) -> Any:
        url = path if path.startswith("http") else urljoin(f"{API_BASE}/", path.lstrip("/"))
        self._rate_limit(bucket)
        try:
            response = self.__session.get(url, params=params, headers=self._headers(), timeout=20)
        except requests.RequestException as exc:
            raise Unknown(message=f"request to {url} failed: {exc}") from exc

        if response.status_code == 404:
            raise NotFound(message=f"nhentai API v2 has no resource at {url}")
        if response.status_code in (401, 403):
            raise Forbidden(
                message=f"nhentai API v2 rejected the request ({response.status_code}): "
                        f"{response.text[:160]}"
            )
        if response.status_code == 429:
            raise ExceedRateLimit(message="nhentai API v2 returned HTTP 429.")
        if response.status_code == 400:
            raise InvalidRequest(message=f"nhentai API v2 rejected the query: {response.text[:200]}")
        if response.status_code >= 300:
            raise Unknown(message=f"nhentai API v2 returned HTTP {response.status_code}.")

        try:
            return response.json()
        except ValueError as exc:
            raise Unknown(message=f"nhentai API v2 returned non-JSON from {url}") from exc

    def _cdn(self) -> tuple[str, str]:
        """Absolute (image_base, thumb_base) from /cdn, cached for one hour."""
        now = time.monotonic()
        cached = self.__cdn_cache
        if cached and now - cached[0] < 3600:
            return cached[1]
        with self.__cdn_lock:
            cached = self.__cdn_cache
            if cached and time.monotonic() - cached[0] < 3600:
                return cached[1]
            try:
                data = self._get("cdn", bucket="cdn")
                images = data.get("image_servers") or []
                thumbs = data.get("thumb_servers") or []
                if images and thumbs:
                    self.__cdn_cache = (
                        time.monotonic(),
                        (f"{images[0].rstrip('/')}/", f"{thumbs[0].rstrip('/')}/"),
                    )
                    return self.__cdn_cache[1]
            except Exception:
                pass  # fall back below; retried on the next call
            fallback = ("https://i1.nhentai.net/", "https://t1.nhentai.net/")
            self.__cdn_cache = (time.monotonic(), fallback)
            return fallback

    # ------------------------------------------------------------------ #
    # Entity builders                                                     #
    # ------------------------------------------------------------------ #

    def _thumb(self, item: dict[str, Any]) -> Thumb:
        gallery_id = item.get("id")
        _, thumb_base = self._cdn()
        path = item.get("thumbnail") or ""
        title = item.get("english_title") or item.get("japanese_title") or f"Gallery #{gallery_id}"
        thumb = Thumb(
            id=str(gallery_id),
            url=urljoin(f"{WEB_BASE}/", f"g/{gallery_id}"),
            title=title,
            cover=Image(
                uri=urljoin(thumb_base, path) if path else "",
                mime=_mime_for(path) if path else MIME.J,
                width=int(item.get("thumbnail_width") or 0),
                height=int(item.get("thumbnail_height") or 0),
            ),
        )
        # Enma's Thumb has no field for these; they are carried through for the
        # app's real popularity/page-count display (never invented).
        thumb.num_favorites = item.get("num_favorites")  # type: ignore[attr-defined]
        thumb.num_pages = item.get("num_pages")  # type: ignore[attr-defined]
        return thumb

    def _build_chapter(self, detail: dict[str, Any]) -> Chapter:
        image_base, _ = self._cdn()
        pages: list[Image] = []
        for page in detail.get("pages") or []:
            path = page.get("path")
            if not path:
                continue
            pages.append(
                Image(
                    uri=urljoin(image_base, path),
                    name=f"{page.get('number') or len(pages) + 1}.{path.rsplit('.', 1)[-1]}",
                    width=int(page.get("width") or 0),
                    height=int(page.get("height") or 0),
                    mime=_mime_for(path),
                )
            )
        # nhentai galleries are single-chapter works: chapter id 1 == the work.
        return Chapter(id=1, pages=pages)

    def _build_manga(self, detail: dict[str, Any], with_symbolic_links: bool) -> Manga:
        _, thumb_base = self._cdn()
        gallery_id = detail.get("id")
        title = detail.get("title") or {}
        tags = detail.get("tags") or []

        cover = detail.get("cover") or {}
        thumb = detail.get("thumbnail") or {}
        upload = detail.get("upload_date")
        created = datetime.fromtimestamp(upload, tz=timezone.utc) if upload else None

        language = next((t.get("name") for t in tags if t.get("type") == "language"), None)
        authors = [
            Author(id=t.get("id", 0), name=t.get("name", ""))
            for t in tags
            if t.get("type") == "artist" and t.get("name")
        ]
        genres = [
            Genre(id=t.get("id", 0), name=t.get("name", ""))
            for t in tags
            if t.get("type") == "tag" and t.get("name")
        ]
        entities: list[Tag] = []
        for tag in tags:
            mapped = TAG_TYPE_MAP.get(tag.get("type") or "")
            if mapped and tag.get("name"):
                entities.append(
                    Tag(type=mapped, name=tag.get("name", ""), id=tag.get("id", 0))  # type: ignore[arg-type]
                )

        if with_symbolic_links:
            chapter = Chapter(
                id=1,
                link=SymbolicLink(link=urljoin(f"{API_BASE}/", f"galleries/{gallery_id}")),
            )
        else:
            chapter = self._build_chapter(detail)

        manga = Manga(
            title=Title(
                english=title.get("english") or "",
                japanese=title.get("japanese") or "",
                other=title.get("pretty") or "",
            ),
            status="completed",
            url=urljoin(f"{WEB_BASE}/", f"g/{gallery_id}"),
            chapters=[chapter],
            language=language,
            genres=genres,
            tags=entities,
            authors=authors,
            cover=Image(
                uri=urljoin(thumb_base, cover.get("path", "")) if cover.get("path") else "",
                mime=_mime_for(cover.get("path", "")) if cover.get("path") else MIME.J,
                width=int(cover.get("width") or 0),
                height=int(cover.get("height") or 0),
            ),
            thumbnail=Image(
                uri=urljoin(thumb_base, thumb.get("path", "")) if thumb.get("path") else "",
                mime=_mime_for(thumb.get("path", "")) if thumb.get("path") else MIME.J,
                width=int(thumb.get("width") or 0),
                height=int(thumb.get("height") or 0),
            ),
            id=gallery_id,
            created_at=created,
            updated_at=created,
        )
        # Not representable on Enma's Manga entity; carried for serialization.
        manga.num_favorites = detail.get("num_favorites")  # type: ignore[attr-defined]
        manga.num_pages = detail.get("num_pages")  # type: ignore[attr-defined]
        manga.scanlator = detail.get("scanlator")  # type: ignore[attr-defined]
        return manga

    def _detail(self, identifier: str) -> dict[str, Any]:
        key = str(identifier)
        cached = self.__details.get(key)
        if cached is not None:
            return cached
        data = self._get(f"galleries/{key}", bucket="detail")
        self.__details[key] = data
        return data

    # ------------------------------------------------------------------ #
    # IMangaRepository                                                    #
    # ------------------------------------------------------------------ #

    def search(self, query: str, page: int = 1, **kwargs: Any) -> SearchResult:
        sort = _map_sort(kwargs.get("sort"))
        data = self._get(
            "search",
            bucket="search",
            params={"query": query, "page": page, "sort": sort},
        )
        items = data.get("result") or []
        result = SearchResult(
            query=query,
            page=int(data.get("page") or page or 1),
            total_pages=int(data.get("num_pages") or 1),
            total_results=int(data.get("total") or len(items)),
            results=[],
        )
        for item in items:
            result.add_result(self._thumb(item))
        return result

    def paginate(self, page: int = 1) -> Pagination:
        data = self._get("galleries", bucket="list", params={"page": page})
        items = data.get("result") or []
        pagination = Pagination(
            page=int(page),
            total_pages=int(data.get("num_pages") or 1),
            total_results=int(data.get("total") or len(items)),
            results=[],
        )
        for item in items:
            pagination.add_result(self._thumb(item))
        return pagination

    def popular(self, page: int = 1) -> Pagination:
        """Today's popular galleries (official endpoint). Not part of
        IMangaRepository — the sidecar feature-detects it."""
        data = self._get("galleries/popular", bucket="popular", params={"page": page})
        items = data if isinstance(data, list) else (
            data.get("result") or data.get("items") or []
        )
        pagination = Pagination(
            page=int(page),
            total_pages=1,
            total_results=len(items),
            results=[],
        )
        for item in items:
            pagination.add_result(self._thumb(item))
        return pagination

    def get(
        self,
        identifier: str,
        with_symbolic_links: bool = False,
        **kwargs: Any,
    ) -> Union[Manga, None]:
        detail = self._detail(identifier)
        if not detail or detail.get("id") is None:
            return None
        return self._build_manga(detail, with_symbolic_links=with_symbolic_links)

    def fetch_chapter_by_symbolic_link(self, link: SymbolicLink) -> Chapter:
        detail = self._get(link.link, bucket="detail")
        if not detail or detail.get("id") is None:
            return Chapter(id=1, pages=[])
        return self._build_chapter(detail)

    def random(self, retry: int = 0) -> Manga:
        data = self._get("galleries/random", bucket="random")
        if isinstance(data, dict) and data.get("pages"):
            return self._build_manga(data, with_symbolic_links=False)
        gallery_id = data.get("id") if isinstance(data, dict) else data
        if gallery_id is None:
            raise Unknown(message="nhentai API v2 random endpoint returned no gallery id.")
        manga = self.get(identifier=str(gallery_id), with_symbolic_links=False)
        if manga is None and retry < 3:
            return self.random(retry=retry + 1)
        if manga is None:
            raise NotFound(message="nhentai API v2 random endpoint returned an empty gallery.")
        return manga

    def author_page(self, author: str, page: int = 1) -> AuthorPage:
        result = self.search(query=f"artist:{author}", page=page)
        return AuthorPage(
            author=author,
            page=result.page,
            total_pages=result.total_pages,
            total_results=result.total_results,
            results=result.results,
        )
