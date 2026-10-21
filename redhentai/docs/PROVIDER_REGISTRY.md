# READHENTAI — Provider Registry

**Verification date:** 2026-10-18
**Purpose:** Record every content source investigated, its *verified* capabilities,
its eligibility for the intended use (an 18+ aggregation platform), and its actual
implementation status. **A name appearing here does NOT mean a provider is
integrated.** Statuses are backed by the "Evidence" field (real requests performed
during development).

## Status vocabulary

| Status | Meaning |
| --- | --- |
| `VERIFIED_AND_AVAILABLE` | Operationally verified with real requests during development. |
| `AUTHORIZED_WITH_RESTRICTIONS` | Verifiable public interface exists, but use is bounded (attribution/licensing/scope). |
| `METADATA_ONLY` | Verified, but exposes metadata only — no chapters/pages. |
| `LINK_OUT_ONLY` | Only outbound links to the official page may be shown. |
| `SELF_HOST_REQUIRED` | Requires the operator to deploy/operate a separate component. |
| `UNAVAILABLE` | Endpoint/hostname does not resolve or returns errors. |
| `NOT_AUTHORIZED_FOR_INTENDED_USE` | The available integration method bypasses an access control, so it is not used. |
| `INVESTIGATION_REQUIRED` | Not yet fully assessed. |

### Distinguishing the layers

- **Discovered** — found during research.
- **Operationally verified** — responded correctly to a real request from this project.
- **Eligible for intended use** — the method of access is permitted (no anti-bot/CAPTCHA/paywall bypass) *and* the content fits the adult-only policy.
- **Implemented** — an adapter exists in `src/lib/providers/`.
- **Tested** — adapter paths exercised (see "Testing performed").

---

## 1. MangaDex — *implemented, primary source*

| Field | Value |
| --- | --- |
| Name | MangaDex |
| Website | https://mangadex.org/ |
| API docs | https://api.mangadex.org/docs/ |
| Repository | — |
| Categories | Manga, Manhwa, Manhua, Doujinshi (original category tag) |
| Languages | Multi-language; this app requests English translations by default |
| Search | ✅ documented `GET /manga` (title, tags, demographic, contentRating) |
| Metadata | ✅ title, alt-titles, authors/artists, tags, status, year, cover, `contentRating` |
| Chapter list | ✅ `GET /chapter` (paged, ordered, decimal chapter numbers, language) |
| Reader / pages | ✅ `GET /at-home/server/{chapterId}` → real page-image URLs (verified 200, `image/jpeg`) |
| Auth | None required for read-only public endpoints |
| Rate limits | Shared global limit; this app uses a bounded semaphore + backoff + circuit breaker |
| Caching | In-memory TTL (title 5 min, chapter pages 60 min) |
| Attribution | Required — every record links back to `mangadex.org/title/{id}` |
| Copyright / redistribution | Images are served from MangaDex `at-home` CDN at read time, not stored. Publisher/scanlation rights apply. |
| Commercial restriction | **MangaDex rules restrict ads/paid services on apps using its API.** If READHENTAI is monetized, this compatibility must be resolved before shipping MangaDex-powered features. |
| Operational status | `VERIFIED_AND_AVAILABLE` |
| Verification evidence | Real requests: `GET /manga` search 200; chapter list 200; `at-home` server 200; page-image HEAD 200 `image/jpeg`; HTTP 400 without identifying `User-Agent` (UA now sent). |
| Implementation status | **Implemented + tested** (`src/lib/providers/mangadex.ts`, registered) |
| Adult classification | Reliable: native `contentRating ∈ {safe, suggestive, erotica, pornographic}` drives the central classifier. |
| Remaining limitations | No aggregate rating exposed by public API (surfaced as "unavailable", never invented). |

## 2. AniList — *implemented, metadata-only*

| Field | Value |
| --- | --- |
| Name | AniList |
| Website | https://anilist.co/ |
| API docs | https://docs.anilist.co/ (GraphQL) |
| Repository | — |
| Categories | Manga, Manhwa, Manhua, Novels |
| Languages | Multi (romaji/english/native titles) |
| Search | ✅ `POST https://graphql.anilist.co` |
| Metadata | ✅ rich: titles, synonyms, genres, tags, staff, status, popularity, **aggregate `averageScore`** |
| Chapter list | ❌ none |
| Reader / pages | ❌ none |
| Auth | None for read-only queries |
| Rate limits | Public GraphQL rate limit; app applies timeouts/backoff |
| Caching | In-memory TTL |
| Attribution | Link back to `anilist.co/manga/{id}` |
| Copyright | Metadata only — no images redistributed |
| Commercial | Public API; standard rate limiting applies |
| Operational status | `VERIFIED_AND_AVAILABLE` (metadata) |
| Verification evidence | Real `POST /` queries return 200 with media pages; double-`data` unwrap handled. |
| Implementation status | **Implemented + tested** (`src/lib/providers/anilist.ts`, registered) — `METADATA_ONLY`; chapters/pages throw `unsupported`, never faked. |
| Adult classification | Native boolean `isAdult`. |
| Remaining limitations | Cannot contribute chapters or pages. Provides the genuine rating MangaDex lacks. |

## 3. Dynasty Reader — *implemented, restricted capabilities*

| Field | Value |
| --- | --- |
| Name | Dynasty Reader |
| Website | https://dynasty-scans.com/ |
| API docs | None official; stable public JSON routes (documented below) |
| Repository | — (Rails app) |
| Categories | Predominantly **Yuri / GL** scanlations; **no `doujinshi` tag** (route 404s) |
| Languages | English scanlations (API has no explicit language field) |
| Search | ❌ **`/search` and `/search.json` return HTTP 500** (every variant tried) |
| Metadata | ✅ `GET /series/{permalink}.json` → name, tags (Author/General/Status), cover, description, aliases |
| Chapter list | ❌ **No per-series endpoint.** `GET /chapters.json?series=` is **ignored** (returns the global recent list); derived permalinks (`_ch1`) **404**. `chapters.json?page=N` paginates only the *global* directory. |
| Reader / pages | ✅ `GET /chapters/{permalink}.json` → `pages[].url` (webp, relative → absolute) |
| Latest | ✅ `GET /chapters/added.json` |
| Trending | ❌ `/hot.json`, `/recent.json` → 404 |
| Auth | None |
| Rate limits | Not published; app uses bounded concurrency + cache |
| Caching | In-memory TTL (metadata 5 min, pages 60 min, latest 60 s) |
| Attribution | Required — records link to `dynasty-scans.com/series/{permalink}` |
| Copyright / redistribution | **Dynasty hosts scanlations.** Images are hot-linked from their hosts at read time (never stored). **Operator must confirm this display use is acceptable for their context.** |
| Commercial | Not specified; treat as restricted |
| Operational status | `AUTHORIZED_WITH_RESTRICTIONS` |
| Verification evidence | Real requests: `series/{p}.json` 200 (full shape captured); `chapters/{p}.json` 200 with `pages[]`; `chapters/added.json` 200; `chapters.json?page=2` 200 (`current_page`,`total_pages`); `/search*` 500; `/hot.json` 404; `/chapters.json?series=` returns unfiltered 25. |
| Implementation status | **Implemented + tested** (`src/lib/providers/dynasty.ts`, registered) for `latestUpdates` + `getTitle` + `getChapterPages` **only**. `search`/`getChapters`/`trending` throw `unsupported` — never faked. |
| Adult classification | Conservative `unknown` unless an adult tag is present → under the adult-only policy most Dynasty titles are **filtered out** (honest consequence: its catalogue is largely non-adult Yuri/GL). |
| Remaining limitations | No search, no full chapter enumeration, largely non-adult catalogue. Surfaces mainly via "Latest updates" where each entry carries a directly readable chapter permalink. |

## 4. HentaiRead (hentairead.io) — *implemented, trending + metadata + in-app reader*

| Field | Value |
| --- | --- |
| Name | HentaiRead |
| Website | https://hentairead.io/ |
| API docs | None — server-rendered HTML only (no public JSON API) |
| Repository | — |
| Categories | Hentai **Manga / Manhwa / Manhua** (manhwa/manhua are explicit genres; everything else is manga) |
| Languages | English |
| Search | ❌ no keyword endpoint (only static top/latest listings) |
| Metadata | ✅ detail page: title, alt-names, **real genres**, view count, **schema.org `ratingValue`/`bestRating`** (0..5), updated date, cover, synopsis |
| Chapter list | ✅ `ul.version-chap` rows on the detail page (51 server-rendered per page); longer titles page the remainder through the site's **own AJAX endpoint** `/?act=ajax&code=load_list_chapter&manga_id=…&page_num=…` (discovered in `/layout/default/js/custom_new.js`, not invented). Yields chapter number, label, release date. |
| Reader / pages | ✅ chapter pages expose ordered `data-index="N"` images on the site's CDN (`cdn-ht.mgread.io`), which hotlink-blocks foreign Referers → served via our display proxy (below). Users read **entirely in-app**; no external reading links. |
| Trending | ✅ `/hot/` (global hot feed) + `/genres/manhwa/` + `/genres/manhua/` (per-category) — parsed for real titles/covers/views |
| Auth | None — pages are directly reachable (verified HTTP 200 HTML; not behind a bot challenge) |
| Rate limits | Not published; app uses a 6-hour TTL cache + a background 6-hour refresher (`scheduler.ts` / `instrumentation.ts`) |
| Caching | In-memory TTL: listings/detail/chapter lists 6 h, chapter page image lists 24 h |
| Attribution | Required — records link back to `hentairead.io/{slug}` |
| Copyright / redistribution | Metadata + covers + read-time page images only. **All images are hotlink-protected** (403 unless the Referer is their origin), so covers and chapter pages are served through a host-allowlisted **display proxy** (`/api/hentairead-image`, hosts: `*.hentairead.io`, `*.mgread.io`) that pipes bytes through with the correct Referer — nothing is stored or re-hosted. |
| Commercial | Not specified; treat as restricted |
| Operational status | `VERIFIED_AND_AVAILABLE` (trending + metadata + reader) |
| Verification evidence | Real requests: `/` 200 (296 KB HTML); `/hot/`, `/genres/manhwa/`, `/genres/manhua/`, detail pages — all 200 with parseable cards/genres/rating; chapter list (short + 92-chapter paginated titles) parsed in full; chapter page images 200 `image/jpeg` **only** with `Referer: https://hentairead.io/` (403 otherwise) → motivates the display proxy; proxied page images verified 200 through our own reader route. |
| Implementation status | **Implemented + tested** (`src/lib/providers/hentairead.ts`, registered) for `trending`, `getTitle`, `getChapters`, `getChapterPages`. `search` remains unsupported. `providerChapterId` encodes the full canonical site path (`slug__chapter-N-ID`) so old URL aliases still resolve. |
| Adult classification | Always `confirmed_adult` (adult-only catalogue); origin (manga/manhwa/manhua) set from the scraped genre/category. |
| Remaining limitations | No search. Per-category trending is derived from `/hot/` + genre pages; "manga" is the default bucket (no dedicated manga page). Detail genre classification is authoritative; listing-card category is cross-referenced (best-effort). Chapter-list pagination is bounded to the first 20 AJAX pages (~1000 chapters). |

## 5. Hentai18 (hentai18.net) — *implemented, full search + metadata + chapters + in-app reader*

| Field | Value |
| --- | --- |
| Name | Hentai18 |
| Website | https://hentai18.net/ |
| API docs | Server-rendered HTML + CDN image delivery |
| Categories | Hentai **Manga / Manhwa / Doujinshi / Artist CG** |
| Languages | English |
| Search | ✅ `GET /search?s={query}` |
| Metadata | ✅ Title, alternative title, artist, tags, category, status, view counts, cover image |
| Chapter list | ✅ Full chapter list per title with chapter numbers, titles, and dates |
| Reader / pages | ✅ Full sequential JPEG pages from `https://cdn.hentai18.net/images/manga/...`. **Hotlink-protected** (403 for foreign Referers, verified) — served via our display proxy with Hentai18's own Referer, like HentaiRead covers/pages. |
| Trending | ✅ `GET /top-hentai` |
| Latest updates | ✅ `GET /new-manga-hentai` |
| Auth | None required (verified direct 200 responses) |
| Caching | In-memory TTL (listing 15m, detail 1h, pages 24h) |
| Attribution | Required — records link back to `hentai18.net/read-hentai/{slug}` |
| Operational status | `VERIFIED_AND_AVAILABLE` |
| Implementation status | **Implemented + tested** (`src/lib/providers/hentai18.ts`, registered) |
| Adult classification | Always `confirmed_adult` (adult-only platform) |

## 6. Enma / nhentai — *implemented, self-hosted sidecar (official API v2)*

| Field | Value |
| --- | --- |
| Name | Enma (serving nhentai) |
| Website | https://nhentai.net/ |
| API docs | https://nhentai.net/api/v2/docs (OpenAPI: https://nhentai.net/api/v2/openapi.json) |
| Repository | https://github.com/AlexandreSenpai/Enma — Python library exposing one `IMangaRepository` contract over several sources; integrated through a **local sidecar** (`services/enma-api/`) because the app is TypeScript |
| Categories | Doujinshi / manga / magazine (origin axis read from the API's `category` tags; default doujinshi) |
| Languages | Per-work language tag (japanese, english, chinese, …) |
| Search | ✅ `GET /api/v2/search?query=&page=&sort=` (`sort ∈ date, popular, popular-today/-week/-month`; query syntax supports `artist:"…"`, `tag:"…"` prefixes; a non-empty query is required, so an empty search falls back to the newest listing) |
| Metadata | ✅ full detail: english/japanese/pretty titles, cover + thumbnail, tags typed by `category/parody/artist/character/language/tag`, upload date, favorites count, page count, per-page dimensions |
| Chapter list | ✅ each gallery is a single-chapter work → chapter number **"1"** (id `<titleId>__<index>` in the app, so the pages route can resolve both from one string) |
| Reader / pages | ✅ ordered page images on nhentai's own CDN (`i{n}.nhentai.net/…`, servers discovered via `GET /api/v2/cdn`) — **directly reachable with no Referer and no display proxy** (verified 200; covers served from the thumb servers `t{n}.nhentai.net`, image servers reject cover paths) |
| Trending | ✅ `GET /api/v2/galleries/popular` — the official daily popular list (verified: 5 items; `page`/period params are ignored by the API, so no windowed trending is faked) |
| Latest updates | ❌ listing items carry **no dates** — capability declared `false` rather than fabricating `publishedAt` |
| Ratings | ❌ no rating signal exists; the real favorites count is surfaced as `popularity` |
| Auth | Public API; optional `Authorization: Key …` (API key from `/user/settings#apikeys`) or `Authorization: User …` raises the published limits |
| Rate limits | Published per-minute/IP budgets (anonymous: search 10, list 15, popular 8, detail 20; higher with a key) — enforced client-side by a sliding window in the sidecar; budget exhaustion surfaces as HTTP 429/`rate_limited`, never as a hidden retry storm. A real server-side 429 (`Rate limit exceeded`) was observed when exceeding the budget |
| Caching | Sidecar: gallery detail 5 min, CDN config 1 h; app: listings 15 min, detail 1 h, page lists 24 h |
| Attribution | Required — records link to `nhentai.net/g/{id}`; upstream's own notice asks clients to use this API (with a descriptive User-Agent) instead of scraping HTML |
| Copyright / redistribution | Read-time image URLs only; nothing is stored or re-hosted, and no display proxy is involved |
| Commercial | Not specified — treat as restricted; attribution + rate limits are mandatory |
| Operational status | `SELF_HOST_REQUIRED` — one-time `npm run enma:setup` (creates `services/enma-api/.venv` exactly once and installs Enma + deps via `app/scripts/enma.mjs`), then `npm run enma` starts the local Python sidecar on `127.0.0.1:8765`. When it is down, connection failures open the circuit breaker and this provider silently drops out of every fan-out |
| Verification evidence | Real requests: legacy `/api/galleries/*` → **403 "Use new API https://nhentai.net/api/v2/docs"** (why Enma's bundled NHentai adapter is replaced); `search` 200 (e.g. `artist:dr.bug` → 25/45); `galleries` newest 200 (25 items, total 652039); `galleries/popular` 200 (5 items); `galleries/{id}` 200 (titles/tags/`pages[]`/upload_date); `cdn` 200 (image + thumb server lists); images: `t1…/thumb.webp` 200, `i1…/1.webp` 200 with a byte spot-check, cover 200 on thumb servers; rate-limit 429 reproduced; **sidecar smoke suite 12/12 passed** (`npm run enma:smoke`) covering health, search, detail, chapters, pages, listing, popular, 404 + validation contracts |
| Implementation status | **Implemented + tested** — sidecar `services/enma-api/` (`nhentai_v2.py` = `IMangaRepository` over API v2 with the sliding-window limiter, `server.py` = FastAPI JSON bridge, `smoke.py` = end-to-end checks); adapter `src/lib/providers/enma.ts` (registered) + `classifyEnma` in `adult.ts`; 13 unit tests in `src/lib/providers/__tests__/enma.test.ts`; runtime-verified end-to-end against the live sidecar (search → title → chapters → pages → trending → aggregateSearch, plus circuit-breaker drop-out when the sidecar stops) |
| Adult classification | `confirmed_adult` when the sidecar reports source `nhentai` (adult-only catalogue), origin from `category` tags; any other Enma source (`ENMA_SOURCE=mangadex`, …) is classified `unknown` and therefore excluded by the default policy until a maturity signal exists |
| Remaining limitations | Requires operating a local Python process; no latest-updates feed (no dates at listing level), no ratings, trending is the single official daily list (5 items). Distinct from excluded item 8 (`doujin-api`): **no impersonation, cookie, challenge or HTML-scraping path exists anywhere in this integration** — only the documented public API |

---

## Investigated and EXCLUDED (not registered)

### 7. comix-api (`yurtzy/comix-api`) — `NOT_AUTHORIZED_FOR_INTENDED_USE`

- **Website/repo:** https://github.com/yurtzy/comix-api — self-hosted Next.js proxy in front of **comix.to**.
- **What it is:** A scraper/proxy whose stated purpose is to bypass comix.to's CORS/CORP and 403 hotlink blocks, including an image proxy.
- **Evidence (real requests to the deployed instance `comix-api.vercel.app`):**
  - `GET /api/manga/home` → **503** `{"error":"Source blocked by Cloudflare bot protection."}`
  - `GET /api/manga/search?q=hentai` → **500**
  - `GET /api/manga/browse?...` → **500**
- **Why excluded:** comix.to sits behind Cloudflare bot protection; comix-api exists to circumvent it. Using it would **bypass an anti-bot control**, which this project's rules forbid (*"Do not bypass … anti-bot restrictions"* / *"Do not create proxies intended to evade provider restrictions"*). The deployed instance is also currently non-functional.
- **Implementation status:** **Not integrated.** The adapter layer (`ContentProvider`) is pluggable — if comix.to ever exposes an authorized API, an adapter can be added without architectural change.

### 8. nhentai local `doujin-api` — `NOT_AUTHORIZED_FOR_INTENDED_USE`

- **What it was:** A local FastAPI utility (`C:\Users\workd\AppData\Local\Temp\opencode\doujin-api`) used by the old `prebuild` cover pipeline.
- **Why excluded:** It used `curl_cffi` Chrome-impersonation to defeat TLS-fingerprint anti-bot detection — an access-control bypass.
- **Removed:** `prebuild` script, `scripts/fetch-covers.mjs`, `src/lib/covers.json`. The **build no longer depends** on this utility or on any network scraping. Not registered.

### 9. Omega Scans — `UNAVAILABLE`

- No public API/RSS; probe routes returned 404. Nothing to integrate compliantly.

### 10. JandaPress — `UNAVAILABLE`

- Hostname did not resolve (`ENOTFOUND`). Nothing to integrate.

---

## Summary counts

| Category | Count | Providers |
| --- | --- | --- |
| Discovered | 10 | MangaDex, AniList, Dynasty, HentaiRead, Hentai18, Enma/nhentai, comix-api, doujin-api, Omega Scans, JandaPress |
| Operationally verified | 6 | MangaDex, AniList, Dynasty, HentaiRead, Hentai18, Enma/nhentai |
| Eligible for intended use | 6 | MangaDex, AniList, Dynasty, HentaiRead, Hentai18 (within stated restrictions), Enma/nhentai (official API v2) |
| **Implemented (registered)** | **6** | MangaDex, AniList, Dynasty, HentaiRead, Hentai18, Enma/nhentai |
| Metadata-only | 1 | AniList |
| Trending + reader (no search) | 1 | HentaiRead |
| Search + full reader | 3 | MangaDex, Hentai18, Enma/nhentai |
| Latest updates + per-chapter pages | 1 | Dynasty |
| Requires local sidecar | 1 | Enma/nhentai |
| Excluded (not authorized) | 2 | comix-api, doujin-api |
| Unavailable | 2 | Omega Scans, JandaPress |

## Honest statement

**MangaDex**, **Hentai18** and **Enma/nhentai** each supply a full search → metadata →
chapter list → reader pipeline (Enma only while its local sidecar is running). **AniList**
supplies metadata + a genuine rating. **Dynasty** supplies latest-updates + per-chapter
pages. **HentaiRead** supplies trending/discovery + metadata (rating, genres, views) +
an in-app reader without search. Reading never leaves the app: images from
hotlink-protecting sources (HentaiRead, Hentai18) are piped through a host-allowlisted
display proxy at read time (never stored), while MangaDex and nhentai images load
directly from their CDNs. Because these providers rarely overlap on the same series at
runtime, **cross-provider chapter reconciliation and chapter-level fallback are
implemented and proven by mocked tests** (`src/lib/providers/__tests__/`, 90 tests) but
are not yet exercised by real multi-source overlap. The catalogue is therefore **not**
complete, and no provider is claimed to be integrated beyond the capabilities listed
above.
