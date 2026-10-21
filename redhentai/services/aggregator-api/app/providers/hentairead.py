"""HentaiRead.io provider implementation (HTML scraping)."""
import re
import json
import asyncio
from typing import List, Optional, Dict
from urllib.parse import quote
from app.providers.base import BaseProvider, ProviderError
from app.models import (
    NormalizedTitle, NormalizedChapter, NormalizedPage, NormalizedUpdate,
    SearchOptions, ChapterOptions, TrendingOptions, UpdateOptions,
    ProviderInfo, ProviderCapabilities, ProviderStatus, Category, PublicationStatus,
)
from app.core.http import get_http_client
from app.core.cache import cache
from app.core.matching import classify_hentairead


class HentaiReadProvider(BaseProvider):
    def __init__(self):
        self._base = "https://hentairead.io"
        self._listing_ttl = 21600  # 6 hours
        self._detail_ttl = 21600
        self._pages_ttl = 86400
        self._max_chapter_pages = 20
        self._chapter_concurrency = 4

    def get_info(self) -> ProviderInfo:
        return ProviderInfo(
            id="hentairead",
            name="HentaiRead",
            base_url=self._base,
            status="VERIFIED_AND_AVAILABLE",
            attribution="Content sourced from hentairead.io (metadata + chapters read in-app via display proxy).",
            capabilities=ProviderCapabilities(
                search=False, get_title=True, get_chapters=True,
                get_chapter_pages=True, trending=True, latest_updates=False, ratings=True
            ),
            adult=True,
        )

    def _unescape(self, s: str) -> str:
        return (s.replace("&", "&")
                .replace("&#x", "&#x").replace("&#", "&#")
                .replace("&nbsp;", " ").replace("<", "<")
                .replace(">", ">").replace("\"", '"')
                .replace("&apos;", "'"))

    def _parse_count(self, raw: Optional[str]) -> Optional[int]:
        if not raw:
            return None
        m = re.match(r"^([\d.]+)\s*([KMB])?$", raw.strip().upper())
        if not m:
            return None
        n = float(m.group(1))
        mult = {"K": 1_000, "M": 1_000_000, "B": 1_000_000_000}.get(m.group(2), 1)
        return int(n * mult)

    def _abs_url(self, src: str) -> str:
        return src if src.startswith("http") else f"{self._base}/{src.lstrip('/')}"

    def _proxy_image(self, url: str) -> str:
        return f"/api/hentairead-image?url={quote(url)}"

    def _slug_from_path(self, path: str) -> str:
        return path.strip("/")

    def _category_from_genres(self, slugs: List[str]) -> Category:
        if "manhwa" in slugs:
            return "manhwa"
        if "manhua" in slugs:
            return "manhua"
        return "manga"

    def _first_match(self, html: str, pattern: str) -> Optional[str]:
        m = re.search(pattern, html, re.IGNORECASE | re.DOTALL)
        return m.group(1).strip() if m else None

    def _build_title(self, card: Dict, category: Category) -> NormalizedTitle:
        return NormalizedTitle(
            id=f"hentairead:{card['slug']}",
            provider="hentairead",
            provider_id=card["slug"],
            slug=f"hentairead-{card['slug']}",
            title=card["title"],
            alternative_titles=[],
            description=None,
            category=category,
            is_adult=True,
            cover_image=self._proxy_image(card["cover"]),
            rating=None,
            popularity=card["views"],
            genres=[],
            tags=[],
            artists=[],
            authors=[],
            language="English",
            status=None,
            updated_at=None,
            published_at=None,
            provider_url=f"{self._base}/{card['path']}",
            readable=True,
            colored=True,
            adult=classify_hentairead(category),
        )

    def _parse_cards(self, html: str) -> List[Dict]:
        cards = []
        seen = set()

        view_re = re.compile(r'fa-eye">\s*</i>\s*([\d.,]+[KMB]?)\s*<i class="far fa-comment"><\/i>[\s\S]{0,300}?<a href="(\/[^"]*?-\d+\/)"', re.IGNORECASE)
        views = {}
        for m in view_re.finditer(html):
            count = self._parse_count(m.group(1))
            if count:
                views[self._slug_from_path(m.group(2))] = count

        card_re = re.compile(r'<a href="(\/[^"]*?-\d+\/)"><img src="([^"]+)"[^>]*alt="([^"]*)"', re.IGNORECASE)
        for m in card_re.finditer(html):
            path = m.group(1)
            slug = self._slug_from_path(path)
            if slug in seen or slug.count("-") < 2:
                continue
            seen.add(slug)
            cards.append({
                "path": path,
                "slug": slug,
                "cover": self._abs_url(m.group(2)),
                "title": self._unescape(m.group(3)).strip(),
                "views": views.get(slug),
            })
        return cards

    def _build_detail(self, html: str, slug: str) -> Optional[NormalizedTitle]:
        title = self._first_match(html, r'<h1[^>]*class="title-detail"[^>]*>([^<]+)</h1>')
        if not title:
            return None

        alt = self._first_match(html, r'<h2[^>]*class="other-name"[^>]*>([\s\S]*?)</h2>')
        alt_titles = [self._unescape(s).strip() for s in alt.split("/")] if alt else []

        genre_block = self._first_match(html, r'<i class="fa fa-tags">[\s\S]{0,200}?<p class="col-8">([\s\S]*?)</p>')
        genres, genre_slugs = [], []
        if genre_block:
            for m in re.finditer(r'<a href="/genres/([^/"\']+)/"[^>]*>([^<]+)</a>', genre_block, re.IGNORECASE):
                genre_slugs.append(m.group(1))
                genres.append(self._unescape(m.group(2)).strip())

        category = self._category_from_genres(genre_slugs)

        rating = self._first_match(html, r'<span itemprop="ratingValue">([\d.]+)</span>')
        best = self._first_match(html, r'<span itemprop="bestRating">([\d.]+)</span>')
        rating_val = None
        if rating:
            val, b = float(rating), float(best or 5)
            rating_val = round((val / b) * 100) if b > 0 else None

        views = self._parse_count(self._first_match(html, r'<i class="fa fa-eye">[\s\S]{0,200}?<p class="col-8">([\d.,]+[KMB]?)</p>'))

        updated = self._first_match(html, r'<time[^>]*>\s*Updated:\s*([^<]+?)\s*</time>')
        updated_iso = None
        if updated:
            try:
                from dateutil import parser
                updated_iso = parser.parse(updated).isoformat()
            except:
                pass

        status_raw = (self._first_match(html, r'<i class="fa fa-rss">[\s\S]{0,200}?<p class="col-8">([^<]*)</p>') or "").lower()
        status = ("Completed" if "completed" in status_raw else
                  "In Process" if "ongoing" in status_raw or "publishing" in status_raw else
                  "Paused" if "hiatus" in status_raw or "cancel" in status_raw else None)

        author_raw = self._first_match(html, r'<i class="fa fa-user">[\s\S]{0,200}?<p class="col-8">([^<]*)</p>')
        author = self._unescape(author_raw) if author_raw and not re.search(r"updating|^$", author_raw, re.IGNORECASE) else None

        cover = self._first_match(html, r'<meta property="og:image" content="([^"]+)"')
        desc = self._first_match(html, r'<meta property="og:description" content="([^"]*)"')

        return NormalizedTitle(
            id=f"hentairead:{slug}",
            provider="hentairead",
            provider_id=slug,
            slug=f"hentairead-{slug}",
            title=self._unescape(title),
            alternative_titles=alt_titles,
            description=self._unescape(desc) if desc else None,
            category=category,
            is_adult=True,
            cover_image=self._abs_url(cover) if cover else None,
            rating=rating_val,
            popularity=views,
            genres=genres,
            tags=genres,
            artists=[author] if author else [],
            authors=[author] if author else [],
            language="English",
            status=status,
            updated_at=updated_iso,
            published_at=None,
            provider_url=f"{self._base}/{slug}/",
            readable="class=\"version-chap\"" in html,
            colored=True,
            adult=classify_hentairead(category),
        )

    def _abs_url(self, src: str) -> str:
        return src if src.startswith("http") else f"{self._base}/{src.lstrip('/')}"

    async def _fetch_html(self, path: str, ttl: int) -> str:
        url = path if path.startswith("http") else f"{self._base}{path}"
        key = f"hentairead:html:{path}"
        cached = await cache.get("hentairead", key)
        if cached:
            return cached
        client = await get_http_client()
        resp = await client.request("hentairead", "GET", url, headers={"Referer": f"{self._base}/"})
        html = resp.text
        await cache.set("hentairead", key, html, ttl)
        return html

    def _parse_chapter_items(self, html: str) -> List[Dict]:
        items = []
        for m in re.finditer(r'<li class="wp-manga-chapter">\s*<a href="([^"]*\/chapter-[^"]+)"[^>]*>([^<]*)</a>\s*(?:<span class="chapter-release-date"><i>([^<]*)</i></span>)?', html, re.IGNORECASE):
            path = m.group(1).replace(f"https://{self._base}/", "").strip("/")
            if "/chapter-" not in path:
                continue
            items.append({"path": path, "label": m.group(2).strip(), "date": m.group(3).strip() if m.group(3) else None})
        return items

    def _chapter_number_from(self, item: Dict) -> Optional[str]:
        m = re.search(r"chapter\s*([\d.]+)", item["label"], re.IGNORECASE)
        if m:
            return m.group(1)
        m = re.search(r"/chapter-([\d.]+?)(?:-\d+)?$", item["path"])
        return m.group(1) if m else None

    def _iso_date(self, raw: Optional[str]) -> Optional[str]:
        if not raw:
            return None
        try:
            from dateutil import parser
            return parser.parse(raw).isoformat()
        except:
            return None

    async def get_trending(self, options: TrendingOptions) -> List[NormalizedTitle]:
        limit = min(options.limit or 20, 40)
        want = set(options.categories) if options.categories else None

        hot, manhwa, manhua = await asyncio.gather(
            self._fetch_html("/hot/", self._listing_ttl),
            self._fetch_html("/genres/manhwa/", self._listing_ttl),
            self._fetch_html("/genres/manhua/", self._listing_ttl),
        )

        manhwa_slugs = {c["slug"] for c in self._parse_cards(manhwa)}
        manhua_slugs = {c["slug"] for c in self._parse_cards(manhua)}

        by_slug = {}
        for card in self._parse_cards(hot):
            cat = "manhwa" if card["slug"] in manhwa_slugs else "manhua" if card["slug"] in manhua_slugs else "manga"
            by_slug[card["slug"]] = self._build_title(card, cat)

        for card in self._parse_cards(manhwa):
            if card["slug"] not in by_slug:
                by_slug[card["slug"]] = self._build_title(card, "manhwa")
        for card in self._parse_cards(manhua):
            if card["slug"] not in by_slug:
                by_slug[card["slug"]] = self._build_title(card, "manhua")

        titles = list(by_slug.values())
        if options.categories:
            want = set(options.categories)
            titles = [t for t in titles if t.category and t.category in want]
        return titles[:limit]

    async def get_title(self, provider_id: str) -> Optional[NormalizedTitle]:
        slug = provider_id.replace("hentairead-", "")
        try:
            html = await self._fetch_html(f"/{slug}/", self._detail_ttl)
            return self._build_detail(html, slug)
        except ProviderError:
            return None

    async def get_chapters(self, provider_id: str, options: ChapterOptions) -> List[NormalizedChapter]:
        slug = provider_id.replace("hentairead-", "")
        html = await self._fetch_html(f"/{slug}/", self._detail_ttl)

        list_match = re.search(r'<ul class="version-chap"[\s\S]*?</ul>', html)
        items = self._parse_chapter_items(list_match.group(0) if list_match else "")

        manga_id = self._first_match(html, r'id="title-detail-manga"[^>]*data-manga="(\d+)"')
        if manga_id:
            page_hints = re.findall(r'load_list_chapter\((\d+)\)', html)
            total_pages = max([int(h) for h in page_hints] + [1])
            for start in range(2, min(total_pages, self._max_chapter_pages) + 1, self._chapter_concurrency):
                batch = list(range(start, min(start + self._chapter_concurrency - 1, total_pages) + 1))
                results = await asyncio.gather(*[
                    self._fetch_html(f"/?act=ajax&code=load_list_chapter&manga_id={manga_id}&page_num={p}&chap_id=0&keyword=", self._detail_ttl)
                    for p in batch
                ], return_exceptions=True)
                for r in results:
                    if isinstance(r, str):
                        list_html = r
                        try:
                            list_html = json.loads(r).get("list_chap", "")
                        except:
                            pass
                        items.extend(self._parse_chapter_items(list_html))

        seen = set()
        chapters = []
        for it in items:
            if it["path"] in seen:
                continue
            seen.add(it["path"])
            ch_num = self._chapter_number_from(it)
            chapters.append(NormalizedChapter(
                id=f"hentairead:{it['path']}",
                title_id=f"hentairead:{slug}",
                provider="hentairead",
                provider_chapter_id=it["path"].replace("/", "__"),
                chapter_number=ch_num,
                chapter_title=it["label"] or None,
                language="en",
                published_at=self._iso_date(it["date"]),
                page_count=None,
                image_url="",
                readable=True,
            ))

        if options.order == "asc":
            chapters.reverse()
        return chapters

    async def get_chapter_pages(self, provider_id: str, chapter_id: str) -> List[NormalizedPage]:
        path = chapter_id.replace("__", "/")
        html = await self._fetch_html(f"/{path}/", self._pages_ttl)

        pages, tagged = [], {}
        for m in re.finditer(r'<img[^>]*data-index="(\d+)"[^>]*>', html):
            src_match = re.search(r'src="([^"]+)"', m.group(0))
            if src_match:
                src = self._abs_url(src_match.group(1))
                if "mgread.io" in src:
                    idx = int(m.group(1))
                    if idx not in tagged:
                        tagged[idx] = src

        for idx, src in sorted(tagged.items()):
            pages.append(NormalizedPage(index=idx, image_url=self._proxy_image(src)))

        if not pages:
            seen = set()
            for m in re.finditer(r'<img[^>]+src="([^"]+)"', html):
                src = self._abs_url(m.group(1))
                if "mgread.io" in src and src not in seen:
                    seen.add(src)
                    pages.append(NormalizedPage(index=len(pages), image_url=self._proxy_image(src)))

        if not pages:
            raise ProviderError("hentairead", "no pages found in chapter", "parse", False)
        return pages

    async def get_latest_updates(self, options: UpdateOptions) -> List[NormalizedUpdate]:
        raise ProviderError("hentairead", "latestUpdates not supported", "unsupported", False)

    async def search_titles(self, query: str, options: SearchOptions) -> List[NormalizedTitle]:
        raise ProviderError("hentairead", "search not supported", "unsupported", False)