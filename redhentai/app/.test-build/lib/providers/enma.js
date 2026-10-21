"use strict";
// Enma adapter — content served by the LOCAL Enma sidecar (Python).
//
// Classification: SELF_HOST_REQUIRED. Every call goes to a local FastAPI
// process (`services/enma-api/server.py`) that wraps the Enma library; start it
// with `npm run enma` (from app/). When it isn't running, requests fail with
// connection errors, the circuit breaker opens, and this provider drops out of
// aggregated results — the rest of the app is unaffected.
//
// Source: nhentai via its OFFICIAL public API v2 (https://nhentai.net/api/v2),
// proxied through Enma's IMangaRepository contract (nhentai_v2.NHentaiV2).
// No cookies, no challenge solving, no TLS fingerprinting, no HTML scraping —
// the published rate limits are enforced client-side by the sidecar, and an
// optional API key (NHENTAI_API_KEY) raises them. nhentai's own notice points
// scrapers at this API. See services/enma-api/server.py for the full contract.
//
// Verified capabilities: search, title metadata, chapter list, page images
// (served directly from nhentai's CDN without any display proxy), and the
// official "popular" list. NOT provided: latest-updates feed (nhentai's listing
// carries no dates, so a "latest" row would need fabricated timestamps) and
// ratings (nhentai exposes favorites counts, not ratings).
Object.defineProperty(exports, "__esModule", { value: true });
exports.enma = void 0;
exports.chapterRef = chapterRef;
exports.parseChapterRef = parseChapterRef;
exports.sortForOrder = sortForOrder;
exports.languageCode = languageCode;
exports.languageLabel = languageLabel;
exports.originFromCategories = originFromCategories;
const http_1 = require("./http");
const adult_1 = require("./adult");
const types_1 = require("./types");
const SIDECAR = (process.env.ENMA_BASE_URL ?? "http://127.0.0.1:8765").replace(/\/+$/, "");
const LISTING_TTL = 15 * 60 * 1000; // 15 min
const DETAIL_TTL = 60 * 60 * 1000; // 1 hr
const PAGES_TTL = 24 * 60 * 60 * 1000; // 24 hr
const TIMEOUT_MS = 15000;
const PER_PAGE = 25; // nhentai API v2 `per_page`
const CAPABILITIES = {
    search: true,
    getTitle: true,
    getChapters: true,
    getChapterPages: true,
    trending: true,
    latestUpdates: false, // listing items carry no dates — never faked
    ratings: false, // favorites counts only, no rating signal
};
const INFO = {
    id: "enma", // must contain no "-" (slug parsing uses the first hyphen)
    name: "Enma (nhentai)",
    baseUrl: "https://nhentai.net/api/v2",
    status: "SELF_HOST_REQUIRED",
    attribution: "Content from nhentai.net via its official public API v2, served by the local Enma sidecar (`npm run enma`).",
    capabilities: CAPABILITIES,
    adult: true,
};
/* ------------------------------------------------------------------ */
/* Small exported helpers (unit-tested without network)                */
/* ------------------------------------------------------------------ */
/** Chapter ids must encode the title id: `getPagesForChapter` passes the
 *  chapter id as BOTH arguments (see registry.ts), so one string carries both. */
function chapterRef(titleId, index) {
    return `${titleId}__${index}`;
}
function parseChapterRef(ref) {
    // Accept both forms: the raw ref (`688749__0`, as `providerChapterId`) and
    // the namespaced `NormalizedChapter.id` (`enma:688749__0`). The sidecar needs
    // the bare numeric title id — sending `enma:688749` upstream yields HTTP 400.
    const bare = ref.startsWith(`${INFO.id}:`) ? ref.slice(INFO.id.length + 1) : ref;
    const cut = bare.lastIndexOf("__");
    if (cut <= 0)
        return null;
    const titleId = bare.slice(0, cut);
    const rest = bare.slice(cut + 2);
    if (!titleId || !rest)
        return null;
    const index = Number(rest);
    if (!Number.isInteger(index) || index < 0)
        return null;
    return { titleId, index };
}
/** Map the app's generic `order` onto the API v2 sort enum.
 *  v2 exposes no relevance ranking and no ratings, so those fall back to the
 *  sidecar default (newest first) instead of pretending to rank. */
function sortForOrder(order) {
    if (order === "popular")
        return "popular";
    if (order === "latest")
        return "date";
    return undefined;
}
const CODE_BY_LANGUAGE = {
    japanese: "ja",
    english: "en",
    chinese: "zh",
    korean: "ko",
    russian: "ru",
    spanish: "es",
    portuguese: "pt",
    turkish: "tr",
    malay: "ms",
};
/** Language tag -> code used by chapter/eligibility logic ("japanese" -> "ja"). */
function languageCode(raw) {
    if (!raw)
        return null;
    return CODE_BY_LANGUAGE[raw.toLowerCase()] ?? null;
}
/** Language tag -> display label for the UI ("japanese" -> "Japanese"). */
function languageLabel(raw) {
    if (!raw)
        return null;
    const value = raw.trim();
    if (!value)
        return null;
    return value.charAt(0).toUpperCase() + value.slice(1);
}
/** Origin axis from nhentai's `category` tags; default doujinshi. */
function originFromCategories(categories) {
    const lower = categories.map((c) => c.toLowerCase());
    if (lower.includes("doujinshi"))
        return "doujinshi";
    if (lower.includes("manhwa"))
        return "manhwa";
    if (lower.includes("manhua"))
        return "manhua";
    if (lower.includes("manga"))
        return "manga";
    return "doujinshi";
}
function mapStatus(status) {
    if (status === "completed")
        return "Completed";
    if (status === "ongoing")
        return "In Process";
    return null;
}
/* ------------------------------------------------------------------ */
/* Builders                                                            */
/* ------------------------------------------------------------------ */
function titleFromThumb(thumb, source) {
    return {
        id: `enma:${thumb.id}`,
        provider: INFO.id,
        providerId: thumb.id,
        slug: `enma-${thumb.id}`,
        title: thumb.title || `Gallery #${thumb.id}`,
        alternativeTitles: [],
        description: null,
        category: "manga",
        isAdult: true,
        coverImage: thumb.cover?.url ?? null,
        rating: null,
        // Real upstream signal (nhentai favorites) — never fabricated.
        popularity: thumb.numFavorites ?? null,
        genres: [],
        tags: [],
        artists: [],
        authors: [],
        language: null,
        status: null,
        updatedAt: null,
        publishedAt: null,
        providerUrl: thumb.url,
        readable: true,
        adult: (0, adult_1.classifyEnma)(source, "doujinshi"),
    };
}
function titleFromDetail(detail) {
    const english = detail.title.english.trim();
    const japanese = detail.title.japanese.trim();
    const pretty = detail.title.pretty.trim();
    const display = english || pretty || japanese || `Gallery #${detail.id}`;
    const alternatives = [pretty, english, japanese].filter((t, i, all) => Boolean(t) && t !== display && all.indexOf(t) === i);
    const categories = detail.tags.filter((t) => t.type === "category").map((t) => t.name);
    const allTagNames = detail.tags.map((t) => t.name);
    const origin = originFromCategories(categories);
    const lowerNames = allTagNames.map((n) => n.toLowerCase());
    const colored = lowerNames.includes("full color")
        ? true
        : lowerNames.includes("black and white")
            ? false
            : undefined;
    return {
        id: `enma:${detail.id}`,
        provider: INFO.id,
        providerId: detail.id,
        slug: `enma-${detail.id}`,
        title: display,
        alternativeTitles: alternatives,
        description: null, // nhentai exposes no description field
        category: "manga",
        isAdult: true,
        coverImage: detail.cover?.url ?? detail.thumbnail?.url ?? null,
        rating: null,
        popularity: detail.numFavorites ?? null,
        genres: detail.genres,
        tags: allTagNames,
        artists: detail.authors,
        authors: detail.authors,
        language: languageLabel(detail.language),
        status: mapStatus(detail.status),
        updatedAt: null,
        publishedAt: detail.uploadDate, // real upload timestamp from the API
        providerUrl: detail.url,
        readable: detail.chapters.length > 0,
        colored,
        adult: (0, adult_1.classifyEnma)(detail.source, origin),
        chapterCount: detail.chapters.length,
    };
}
/* ------------------------------------------------------------------ */
/* Fetch helper                                                        */
/* ------------------------------------------------------------------ */
function getJson(path, cacheKey, ttlMs) {
    return (0, http_1.cached)(cacheKey, ttlMs, () => (0, http_1.providerFetch)(`${SIDECAR}${path}`, { providerId: INFO.id, timeoutMs: TIMEOUT_MS }));
}
async function fetchTitle(id) {
    return getJson(`/v1/title/${encodeURIComponent(id)}`, `enma:title:${id}`, DETAIL_TTL);
}
/* ------------------------------------------------------------------ */
/* Adapter                                                             */
/* ------------------------------------------------------------------ */
exports.enma = {
    getProviderInfo() {
        return INFO;
    },
    async searchTitles(query, options = {}) {
        const limit = Math.min(options.limit ?? 24, 50);
        const q = (query ?? "").trim();
        const sort = sortForOrder(options.order);
        const page = Math.floor((options.offset ?? 0) / PER_PAGE) + 1;
        // v2 requires a non-empty query; an empty search is a browse of the newest
        // galleries (same precedent as the other adult providers' empty search).
        const path = q
            ? `/v1/search?query=${encodeURIComponent(q)}&page=${page}${sort ? `&sort=${sort}` : ""}`
            : `/v1/list?page=${page}`;
        const data = await getJson(path, `enma:search:${q}:${sort ?? "default"}:${page}`, LISTING_TTL);
        // The caller's `limit` need not equal `PER_PAGE`, so an offset can land
        // mid-page (e.g. limit=24, offset=24 -> still page 1, not 2). Slicing from
        // the in-page position keeps paging honest; taking `slice(0, limit)` made
        // page N re-serve page N-1's items, repeating titles across pages.
        const start = Math.max(0, (options.offset ?? 0) % PER_PAGE);
        return data.results.slice(start, start + limit).map((t) => titleFromThumb(t, data.source));
    },
    async getTitle(providerId) {
        const id = providerId.replace(/^enma-/, "");
        try {
            const detail = await fetchTitle(id);
            return titleFromDetail(detail);
        }
        catch (err) {
            // A definitive "no such title / bad id" is a normal miss (-> null); every
            // other failure (sidecar down, timeouts, upstream 5xx/429) must propagate
            // so the circuit breaker records it.
            if (err instanceof types_1.ProviderError &&
                err.kind === "http" &&
                /HTTP (400|404)/.test(err.message)) {
                return null;
            }
            throw err;
        }
    },
    async getChapters(providerId, options = {}) {
        const id = providerId.replace(/^enma-/, "");
        const detail = await fetchTitle(id);
        const chapters = detail.chapters.map((ch) => {
            const ref = chapterRef(detail.id, ch.index);
            return {
                id: `enma:${ref}`,
                titleId: `enma:${detail.id}`,
                provider: INFO.id,
                providerChapterId: ref,
                // Never null: the aggregator dedupes chapters by number, so a missing
                // number would collapse multi-chapter works. The sidecar already
                // reports the source's own numbering (nhentai single work -> "1").
                chapterNumber: ch.number ?? String(ch.index + 1),
                chapterTitle: null,
                language: languageCode(detail.language),
                // Single-chapter works (all nhentai galleries) publish exactly when the
                // work uploads; multi-chapter sources give no per-chapter date here.
                publishedAt: detail.chapters.length === 1 ? detail.uploadDate : null,
                pageCount: ch.pagesCount ?? null,
                imageUrl: "",
                readable: true,
            };
        });
        return options.order === "desc" ? chapters.slice().reverse() : chapters;
    },
    async getChapterPages(_providerId, chapterId) {
        const ref = parseChapterRef(chapterId);
        if (!ref) {
            throw new types_1.ProviderError(INFO.id, `unparsable chapter id: ${chapterId}`, "parse", false);
        }
        const data = await getJson(`/v1/title/${encodeURIComponent(ref.titleId)}/chapters/${ref.index}/pages`, `enma:pages:${ref.titleId}:${ref.index}`, PAGES_TTL);
        if (!data.pages.length) {
            throw new types_1.ProviderError(INFO.id, "sidecar returned no pages for chapter", "parse", false);
        }
        return data.pages.map((p) => ({
            index: p.index,
            imageUrl: p.url,
            width: p.width ?? undefined,
            height: p.height ?? undefined,
        }));
    },
    async getTrending(options = {}) {
        const limit = Math.min(options.limit ?? 24, 50);
        // Official popularity endpoint. nhentai serves a single daily list (the API
        // ignores page/period parameters — verified), so `options.window` cannot be
        // honored without inventing a ranking; it is intentionally not used.
        const data = await getJson("/v1/popular", "enma:popular", LISTING_TTL);
        return data.results.slice(0, limit).map((t) => titleFromThumb(t, data.source));
    },
};
