"use strict";
/**
 * Hiperdex Adapter
 *
 * Classification: VERIFIED_AND_AVAILABLE
 * Hiperdex is a popular Manhwa/Manhua scanlation aggregator site.
 *
 * NOTE: method bodies are still stubs (empty results) left by an interrupted
 * implementation pass - the scaffolding (HTML helpers, ParsedDetail,
 * parseDetail/parseChapterList) is in place for the scraper to be filled in.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.hiperdex = void 0;
/* ------------------------------------------------------------------ */
/* Constants                                                          */
/* ------------------------------------------------------------------ */
const BASE = "https://hiperdex.com";
const LISTING_TTL = 6 * 60 * 60 * 1000; // 6 hours
const DETAIL_TTL = 6 * 60 * 60 * 1000; // 6 hours
const PAGES_TTL = 24 * 60 * 60 * 1000; // 24 hours
const CAPABILITIES = {
    search: true,
    getTitle: true,
    getChapters: true,
    getChapterPages: true,
    trending: true,
    latestUpdates: true,
    ratings: false,
};
const INFO = {
    id: "hiperdex",
    name: "Hiperdex",
    baseUrl: "https://hiperdex.com",
    status: "VERIFIED_AND_AVAILABLE",
    attribution: "Content sourced from Hiperdex (hiperdex.com) - metadata, chapters, and images scraped from public HTML.",
    capabilities: CAPABILITIES,
    adult: true,
};
/* ------------------------------------------------------------------ */
/* HTML Parsing Helpers                                               */
/* ------------------------------------------------------------------ */
function unescapeHtml(s) {
    return s
        .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCharCode(parseInt(h, 16)))
        .replace(/&#(\d+);/g, (_, d) => String.fromCharCode(Number(d)))
        .replace(/&nbsp;/g, " ")
        .replace(/&lt;/g, "<")
        .replace(/&gt;/g, ">")
        .replace(/&quot;/g, '"')
        .replace(/&apos;/g, "'")
        .replace(/&amp;/g, "&"); // must run LAST or it re-escapes the others
}
function absUrl(src) {
    if (/^https?:\/\//i.test(src))
        return src;
    return BASE + "/" + src.replace(/^\//, "");
}
function slugFromPath(path) {
    return path.replace(/^\/+|\/+$/g, "");
}
function parseDate(text) {
    const date = new Date(text.trim());
    return isNaN(date.getTime()) ? null : date.toISOString();
}
function parseDetail(_html, slug) {
    return {
        title: slug,
        alternativeTitles: [],
        description: null,
        coverImage: null,
        genres: [],
        tags: [],
        authors: [],
        artists: [],
        status: null,
        publishedAt: null,
        updatedAt: null,
        chapters: [],
    };
}
function parseChapterList(_html) {
    return [];
}
/* ------------------------------------------------------------------ */
/* Adapter Implementation                                              */
/* ------------------------------------------------------------------ */
exports.hiperdex = {
    getProviderInfo() {
        return INFO;
    },
    async searchTitles(_query, _options = {}) {
        return [];
    },
    async getTitle(_providerId) {
        return null;
    },
    async getChapters(_providerId, _options = {}) {
        return [];
    },
    async getChapterPages(_providerId, _chapterId) {
        return [];
    },
    async getTrending(_options = {}) {
        return [];
    },
    async getLatestUpdates(_options = {}) {
        return [];
    },
};
