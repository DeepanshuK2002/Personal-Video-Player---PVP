# READHENTAI — Provider Registry

**Verification date:** 2026-10-17
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

---

## Investigated and EXCLUDED (not registered)

### 4. comix-api (`yurtzy/comix-api`) — `NOT_AUTHORIZED_FOR_INTENDED_USE`

- **Website/repo:** https://github.com/yurtzy/comix-api — self-hosted Next.js proxy in front of **comix.to**.
- **What it is:** A scraper/proxy whose stated purpose is to bypass comix.to's CORS/CORP and 403 hotlink blocks, including an image proxy.
- **Evidence (real requests to the deployed instance `comix-api.vercel.app`):**
  - `GET /api/manga/home` → **503** `{"error":"Source blocked by Cloudflare bot protection."}`
  - `GET /api/manga/search?q=hentai` → **500**
  - `GET /api/manga/browse?...` → **500**
- **Why excluded:** comix.to sits behind Cloudflare bot protection; comix-api exists to circumvent it. Using it would **bypass an anti-bot control**, which this project's rules forbid (*"Do not bypass … anti-bot restrictions"* / *"Do not create proxies intended to evade provider restrictions"*). The deployed instance is also currently non-functional.
- **Implementation status:** **Not integrated.** The adapter layer (`ContentProvider`) is pluggable — if comix.to ever exposes an authorized API, an adapter can be added without architectural change.

### 5. nhentai local `doujin-api` — `NOT_AUTHORIZED_FOR_INTENDED_USE`

- **What it was:** A local FastAPI utility (`C:\Users\workd\AppData\Local\Temp\opencode\doujin-api`) used by the old `prebuild` cover pipeline.
- **Why excluded:** It used `curl_cffi` Chrome-impersonation to defeat TLS-fingerprint anti-bot detection — an access-control bypass.
- **Removed:** `prebuild` script, `scripts/fetch-covers.mjs`, `src/lib/covers.json`. The **build no longer depends** on this utility or on any network scraping. Not registered.

### 6. Omega Scans — `UNAVAILABLE`

- No public API/RSS; probe routes returned 404. Nothing to integrate compliantly.

### 7. JandaPress — `UNAVAILABLE`

- Hostname did not resolve (`ENOTFOUND`). Nothing to integrate.

---

## Summary counts

| Category | Count | Providers |
| --- | --- | --- |
| Discovered | 7 | MangaDex, AniList, Dynasty, comix-api, doujin-api, Omega Scans, JandaPress |
| Operationally verified | 3 | MangaDex, AniList, Dynasty |
| Eligible for intended use | 3 | MangaDex, AniList, Dynasty (within stated restrictions) |
| **Implemented (registered)** | **3** | MangaDex, AniList, Dynasty |
| Metadata-only | 1 | AniList |
| Reader-capable | 2 | MangaDex, Dynasty (per-chapter only) |
| Excluded (not authorized) | 2 | comix-api, doujin-api |
| Unavailable | 2 | Omega Scans, JandaPress |

## Honest statement

Only **MangaDex** currently supplies a full search → metadata → chapter list → reader
pipeline. **AniList** supplies metadata + a genuine rating. **Dynasty** supplies
latest-updates + per-chapter pages. Because these three do not overlap on the same
series at runtime, **cross-provider chapter reconciliation and chapter-level fallback
are implemented and proven by mocked tests** (`src/lib/providers/__tests__/`, 67 tests)
but are not yet exercised by real multi-source overlap. The catalogue is therefore
**not** complete, and no provider is claimed to be integrated beyond the capabilities
listed above.
