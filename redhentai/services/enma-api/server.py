"""Local Enma HTTP sidecar for READHENTAI.

Why this exists
---------------
The web app (Next.js / TypeScript) must not depend on a Python package at
runtime, while Enma — the manga/doujinshi source library we integrate — is
Python-only. This process bridges the two:

    app (TS adapter `enma`) -> HTTP -> this sidecar -> Enma -> nhentai API v2

Every endpoint is a thin, validated wrapper around one Enma use case and
serializes Enma's domain entities into stable JSON for the TypeScript adapter.
It is a LOCAL sidecar: it binds to 127.0.0.1 by default, serves no auth, and
is started on demand via `npm run enma` (see app/package.json). When it is not
running, the TS adapter fails fast with connection errors, the circuit breaker
opens, and the provider simply drops out of aggregated results — the rest of
the app is unaffected.

Configuration (env vars, or `services/enma-api/.env` next to this file)
----------------------------------------------------------------------
  ENMA_SOURCE            nhentai (default) | mangadex | manganato
  ENMA_HOST              default 127.0.0.1 (keep local)
  ENMA_PORT              default 8765
  ENMA_MAX_CONCURRENT    max simultaneous upstream calls (default 4)
  ENMA_LOG               "1" -> Enma's own logger at INFO
  NHENTAI_API_KEY        optional, from https://nhentai.net/user/settings#apikeys
  NHENTAI_USER_TOKEN     optional alternative to the API key
  NHENTAI_USER_AGENT     descriptive User-Agent (required by upstream etiquette)

Compliance notes
----------------
* Only nhentai's official, documented API v2 is used (no HTML scraping, no
  cookies, no challenge solving, no TLS fingerprinting). Enma's bundled
  `NHentai` adapter is replaced by `nhentai_v2.NHentaiV2`, which speaks API v2
  and enforces the published rate limits client-side.
* Enma's other sources (mangadex, manganato) are exposed as-is via ENMA_SOURCE;
  only the nhentai path is verified in this project.
"""

from __future__ import annotations

import os
import sys
import threading
from datetime import datetime
from functools import wraps
from pathlib import Path as FsPath

from dotenv import load_dotenv

load_dotenv(FsPath(__file__).with_name(".env"))

from enma import (  # noqa: E402  (env must load before enma import side effects)
    Enma,
    LogMode,
    Sources,
    __version__ as ENMA_VERSION,
    logger,
)
from enma.application.core.handlers.error import (  # noqa: E402
    ExceedRateLimit,
    Forbidden,
    InvalidConfig,
    InvalidRequest,
    NotFound,
    SourceNotAvailable,
    SourceWasNotDefined,
    Unknown,
)
from enma.domain.entities.manga import Chapter, Manga  # noqa: E402
from fastapi import FastAPI, Path as RoutePath, Query  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402

from nhentai_v2 import NHentaiV2  # noqa: E402

SOURCE = (os.getenv("ENMA_SOURCE", "nhentai") or "nhentai").strip() or "nhentai"
ENMA_HOST = os.getenv("ENMA_HOST", "127.0.0.1")
ENMA_PORT = int(os.getenv("ENMA_PORT", "8765"))
MAX_CONCURRENT = max(1, int(os.getenv("ENMA_MAX_CONCURRENT", "4")))

if os.getenv("ENMA_LOG") == "1":
    logger.mode = LogMode.NORMAL

# ---------------------------------------------------------------------------
# Enma wiring
# ---------------------------------------------------------------------------
# `Enma()` registers its own NHentai adapter, which still targets the retired
# `/api/galleries/*` endpoints (403 "Use new API"). Re-registering under the
# same key replaces it with the API-v2 implementation; the other Enma sources
# stay untouched.

enma = Enma()
if SOURCE == "nhentai":
    enma.source_manager.add_source(Sources.NHENTAI, NHentaiV2())
enma.source_manager.set_source(SOURCE)
REPO = enma.source_manager.source

# Only our v2 adapter understands the sidecar's `sort` values; other Enma
# sources would raise on an unknown keyword/enum, so `sort` is dropped for them.
SUPPORTS_SORT = isinstance(REPO, NHentaiV2)

_UPSTREAM_SLOTS = threading.BoundedSemaphore(MAX_CONCURRENT)


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class SidecarError(Exception):
    """An error already carrying its HTTP status + stable machine code."""

    def __init__(self, status: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message


_ENMA_HTTP_STATUS: dict[type[Exception], int] = {
    ExceedRateLimit: 429,  # client-visible "slow down" signal
    Forbidden: 403,
    NotFound: 404,
    InvalidRequest: 400,
    InvalidConfig: 400,
    SourceNotAvailable: 501,
    SourceWasNotDefined: 501,
    Unknown: 502,  # unknown upstream failure -> retryable for the TS adapter
}


def map_enma_error(exc: Exception) -> SidecarError:
    if isinstance(exc, SidecarError):
        return exc
    if isinstance(exc, NotImplementedError):
        return SidecarError(
            501,
            "NOT_SUPPORTED",
            str(exc) or "this Enma source does not support the operation",
        )
    for exc_type, status in _ENMA_HTTP_STATUS.items():
        if isinstance(exc, exc_type):
            code = getattr(exc, "code", None) or type(exc).__name__.upper()
            return SidecarError(status, code, str(exc) or type(exc).__name__)
    return SidecarError(502, "UNKNOWN", f"{type(exc).__name__}: {exc}")


def sidecar_endpoint(fn):
    """Map Enma's exception hierarchy onto SidecarError (handled below)."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except SidecarError:
            raise
        except Exception as exc:  # noqa: BLE001 - deliberate boundary
            raise map_enma_error(exc) from exc

    return wrapper


app = FastAPI(
    title="readhentai Enma sidecar",
    version=ENMA_VERSION,
    docs_url="/docs",
    openapi_url="/openapi.json",
)


@app.exception_handler(SidecarError)
async def _sidecar_error_handler(_request, exc: SidecarError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status,
        content={"error": exc.code, "message": exc.message},
    )


# ---------------------------------------------------------------------------
# Serialization (stable JSON contract for app/src/lib/providers/enma.ts)
# ---------------------------------------------------------------------------


def _source_name() -> str:
    return enma.source_manager.source_name or SOURCE


def _image_json(image) -> dict | None:
    if image is None or not getattr(image, "uri", ""):
        return None
    return {"url": image.uri, "width": image.width or None, "height": image.height or None}


def _thumb_json(thumb) -> dict:
    return {
        "id": str(thumb.id),
        "url": thumb.url,
        "title": thumb.title,
        "cover": _image_json(thumb.cover),
        # Real upstream signals (may be None; never fabricated).
        "numPages": getattr(thumb, "num_pages", None),
        "numFavorites": getattr(thumb, "num_favorites", None),
    }


def _chapter_json(manga: Manga, chapter: Chapter, index: int) -> dict:
    # Symbolic-link chapters carry no pages (pages_count=0); the gallery-level
    # page count from the same API response is the honest fallback for the
    # single-chapter case.
    pages_count = chapter.pages_count or getattr(manga, "num_pages", None)
    return {
        "index": index,
        "id": str(chapter.id),
        # Chapter numbering: Enma uses the chapter id as the label (nhentai:
        # single chapter "1"; MangaDex: chapter number). None -> TS falls back
        # to the array index.
        "number": str(chapter.id) if chapter.id not in (0, None, "") else None,
        "pagesCount": pages_count,
        "link": chapter.link.link if chapter.link else None,
    }


def _title_json(manga: Manga) -> dict:
    title = manga.title
    return {
        "source": _source_name(),
        "id": str(manga.id),
        "url": manga.url,
        "title": {
            "english": title.english or "",
            "japanese": title.japanese or "",
            "pretty": title.other or "",
        },
        "language": manga.language,
        "status": manga.status,
        "cover": _image_json(manga.cover),
        "thumbnail": _image_json(manga.thumbnail),
        "genres": [g.name for g in manga.genres],
        # Enma's Tag.type is one of character/related/category ("related" is how
        # Enma surfaces nhentai's parody tags).
        "tags": [{"type": t.type, "name": t.name} for t in manga.tags],
        "authors": [a.name for a in manga.authors],
        "uploadDate": _iso(getattr(manga, "created_at", None)),
        "numPages": getattr(manga, "num_pages", None),
        "numFavorites": getattr(manga, "num_favorites", None),
        "scanlator": getattr(manga, "scanlator", None) or "",
        "chapters": [
            _chapter_json(manga, ch, index) for index, ch in enumerate(manga.chapters)
        ],
    }


def _iso(value) -> str | None:
    return value.isoformat() if isinstance(value, datetime) else None


def _listing_json(result) -> dict:
    return {
        "source": _source_name(),
        "page": result.page,
        "numPages": result.total_pages,
        "total": result.total_results,
        "results": [_thumb_json(t) for t in result.results],
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    """Liveness only — no upstream call, so it answers even offline."""
    return {
        "ok": True,
        "enma": ENMA_VERSION,
        "source": SOURCE,
        "sourceName": _source_name(),
        "supportsSort": SUPPORTS_SORT,
        "python": sys.version.split()[0],
        "authenticated": bool(os.getenv("NHENTAI_API_KEY") or os.getenv("NHENTAI_USER_TOKEN")),
    }


@app.get("/v1/search")
@sidecar_endpoint
def search(
    query: str = Query(..., min_length=1),
    page: int = Query(1, ge=1),
    sort: str | None = Query(None),
) -> dict:
    with _UPSTREAM_SLOTS:
        kwargs = {"sort": sort} if SUPPORTS_SORT and sort else {}
        result = enma.search(query=query, page=page, **kwargs)
    return _listing_json(result)


@app.get("/v1/list")
@sidecar_endpoint
def list_gallery(page: int = Query(1, ge=1)) -> dict:
    """Newest-first gallery listing (browse / empty-query fallback)."""
    with _UPSTREAM_SLOTS:
        result = enma.paginate(page=page)
    return _listing_json(result)


@app.get("/v1/popular")
@sidecar_endpoint
def popular() -> dict:
    """The source's official popularity list (nhentai: daily popular)."""
    repo = enma.source_manager.source
    if repo is None or not hasattr(repo, "popular"):
        raise NotImplementedError(
            f"Enma source '{_source_name()}' exposes no popularity endpoint"
        )
    with _UPSTREAM_SLOTS:
        result = repo.popular(page=1)
    return _listing_json(result)


@app.get("/v1/random")
@sidecar_endpoint
def random_title() -> dict:
    with _UPSTREAM_SLOTS:
        manga = enma.random()
    return _title_json(manga)


@app.get("/v1/title/{title_id}")
@sidecar_endpoint
def get_title(title_id: str = RoutePath(..., min_length=1, max_length=64)) -> dict:
    with _UPSTREAM_SLOTS:
        manga = enma.get(identifier=title_id, with_symbolic_links=True)
    if manga is None:
        raise NotFound(message=f"title {title_id!r} not found")
    return _title_json(manga)


@app.get("/v1/title/{title_id}/chapters/{index}/pages")
@sidecar_endpoint
def get_chapter_pages(
    title_id: str = RoutePath(..., min_length=1, max_length=64),
    index: int = RoutePath(..., ge=0),
) -> dict:
    with _UPSTREAM_SLOTS:
        manga = enma.get(identifier=title_id, with_symbolic_links=False)
        if manga is None:
            raise NotFound(message=f"title {title_id!r} not found")
        if index >= len(manga.chapters):
            raise NotFound(
                message=f"chapter index {index} does not exist for title {title_id!r}"
            )
        chapter = manga.chapters[index]

        if not chapter.pages:
            # Source that serves pages only through symbolic links: re-fetch the
            # title with links and resolve the chapter link.
            linked = enma.get(identifier=title_id, with_symbolic_links=True)
            if linked is not None and index < len(linked.chapters):
                candidate = linked.chapters[index]
                if candidate.link:
                    chapter = enma.fetch_chapter_by_symbolic_link(chapter=candidate)

    if not chapter.pages:
        raise NotFound(message=f"chapter {index} of title {title_id!r} has no pages")

    return {
        "source": _source_name(),
        "titleId": title_id,
        "index": index,
        "pages": [
            {"index": i, "url": page.uri, "width": page.width, "height": page.height}
            for i, page in enumerate(chapter.pages)
        ],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=ENMA_HOST,
        port=ENMA_PORT,
        log_level=os.getenv("ENMA_LOG_LEVEL", "warning"),
    )
