"use strict";
// HentaiRead.moe adapter.
//
// Classification: VERIFIED_AND_AVAILABLE (trending + latest + title metadata + chapters + readable pages).
// Source: https://hentairead.moe — a gallery-based hentai library. Each gallery is a
// single readable chapter (all of its pages). Images are served from readimg.site.
Object.defineProperty(exports, "__esModule", { value: true });
exports.hentaireadmoe = void 0;
const http_1 = require("./http");
const adult_1 = require("./adult");
const types_1 = require("./types");
const BASE = "https://hentairead.moe";
const LISTING_TTL = 15 * 60 * 1000;
const DETAIL_TTL = 60 * 60 * 1000;
const PAGES_TTL = 24 * 60 * 60 * 1000;
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
    id: "hentaireadmoe",
    name: "HentaiRead.moe",
    baseUrl: BASE,
    status: "VERIFIED_AND_AVAILABLE",
    attribution: "Content sourced from HentaiRead (hentairead.moe).",
    capabilities: CAPABILITIES,
    adult: true,
};
function unescapeHtml(s) {
    return s
        .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCharCode(parseInt(h, 16)))
        .replace(/&#(\d+);/g, (_, d) => String.fromCharCode(Number(d)))
        .replace(/&nbsp;/g, " ")
        .replace(/&lt;/g, "<")
        .replace(/&gt;/g, ">")
        .replace(/&quot;/g, '"')
        .replace(/&apos;/g, "'")
        .replace(/&amp;/g, "&");
}
function stripTags(s) {
    return s.replace(/<[^>]+>/g, "").trim();
}
function absUrl(src) {
    if (/^https?:\/\//i.test(src))
        return src;
    return `${BASE}/${src.replace(/^\/+/, "")}`;
}
function parseCards(html) {
    const cards = [];
    const seen = new Set();
    const re = /<a[^>]+href="https:\/\/hentairead\.moe\/hentai\/([^"]+)"[^>]*>[\s\S]*?<img[^>]*alt="([^"]*)"[^>]*src="([^"]*)"/gi;
    let m;
    while ((m = re.exec(html))) {
        const slug = m[1];
        if (seen.has(slug))
            continue;
        seen.add(slug);
        cards.push({
            slug,
            title: unescapeHtml(m[2].trim() || slug),
            cover: absUrl(m[3]),
        });
    }
    return cards;
}
function galleryIdFromHtml(html) {
    const m = html.match(/readimg\.site\/galleries\/(\d+)\//i);
    return m ? m[1] : null;
}
function parsePageCount(html) {
    const m = html.match(/Pages:\s*<\/[^>]*>\s*(\d+)/i) || html.match(/Pages:\s*(\d+)/i);
    return m ? parseInt(m[1], 10) : 0;
}
function parseTitle(html, slug) {
    const h1 = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/i);
    if (h1)
        return unescapeHtml(stripTags(h1[1]));
    const t = html.match(/<title>([^<]+)<\/title>/i);
    return t ? unescapeHtml(t[1].split("|")[0].trim()) : slug;
}
function parseTags(html) {
    const tags = [];
    const re = /\/tag\/[^"]+">([^<]+)</gi;
    let m;
    while ((m = re.exec(html)))
        tags.push(unescapeHtml(m[1].trim()));
    return Array.from(new Set(tags));
}
function parseArtist(html) {
    const m = html.match(/Artist:[\s\S]*?<a[^>]*>([^<]+)<\/a>/i);
    return m ? unescapeHtml(m[1].trim()) : null;
}
function buildTitle(slug, html) {
    const galleryId = galleryIdFromHtml(html);
    const pageCount = parsePageCount(html);
    const title = parseTitle(html, slug);
    const tags = parseTags(html);
    const artist = parseArtist(html);
    const cover = galleryId ? `https://readimg.site/galleries/${galleryId}/cover.webp` : null;
    return {
        id: `hentaireadmoe:${slug}`,
        provider: INFO.id,
        providerId: slug,
        slug: `hentaireadmoe-${slug}`,
        title,
        alternativeTitles: [],
        description: null,
        category: "manga",
        isAdult: true,
        coverImage: cover,
        rating: null,
        popularity: null,
        genres: tags,
        tags,
        artists: artist ? [artist] : [],
        authors: artist ? [artist] : [],
        language: "English",
        status: null,
        updatedAt: null,
        publishedAt: null,
        providerUrl: `${BASE}/hentai/${slug}`,
        readable: pageCount > 0,
        adult: (0, adult_1.classifyHentai18)("manga"),
    };
}
async function fetchHtml(path, ttl) {
    const url = path.startsWith("http") ? path : `${BASE}${path}`;
    const key = `hentaireadmoe:html:${path}`;
    return (0, http_1.cached)(key, ttl, async () => {
        try {
            return await (0, http_1.rawText)(url, { timeoutMs: 15000 });
        }
        catch (err) {
            throw new types_1.ProviderError(INFO.id, err.message, "network", true);
        }
    });
}
exports.hentaireadmoe = {
    getProviderInfo() {
        return INFO;
    },
    async searchTitles(query, options = {}) {
        const limit = Math.min(options.limit ?? 24, 50);
        const offset = Math.max(0, options.offset ?? 0);
        try {
            const html = await fetchHtml("/hentai-list", LISTING_TTL);
            const cards = parseCards(html);
            const q = (query ?? "").trim().toLowerCase();
            const filtered = q ? cards.filter((c) => c.title.toLowerCase().includes(q)) : cards;
            // This provider searches by filtering ONE listing page, so there is only
            // a single page of results. Slice by `offset` so aggregateSearch's paging
            // stays honest: later pages return [] here rather than re-serving the
            // same cards (which duplicated every merged page).
            return filtered.slice(offset, offset + limit).map((c) => ({
                id: `hentaireadmoe:${c.slug}`,
                provider: INFO.id,
                providerId: c.slug,
                slug: `hentaireadmoe-${c.slug}`,
                title: c.title,
                alternativeTitles: [],
                description: null,
                category: "manga",
                isAdult: true,
                coverImage: c.cover,
                rating: null,
                popularity: null,
                genres: [],
                tags: [],
                artists: [],
                authors: [],
                language: "English",
                status: null,
                updatedAt: null,
                publishedAt: null,
                providerUrl: `${BASE}/hentai/${c.slug}`,
                readable: true,
                adult: (0, adult_1.classifyHentai18)("manga"),
            }));
        }
        catch (err) {
            throw new types_1.ProviderError(INFO.id, err.message, "network", true);
        }
    },
    async getTitle(providerId) {
        const slug = providerId.replace(/^hentaireadmoe-/, "");
        try {
            const html = await fetchHtml(`/hentai/${slug}`, DETAIL_TTL);
            return buildTitle(slug, html);
        }
        catch {
            return null;
        }
    },
    async getChapters(providerId, options = {}) {
        const slug = providerId.replace(/^hentaireadmoe-/, "");
        try {
            const html = await fetchHtml(`/hentai/${slug}`, DETAIL_TTL);
            const pageCount = parsePageCount(html);
            const chapter = {
                id: `hentaireadmoe:${slug}`,
                titleId: `hentaireadmoe:${slug}`,
                provider: INFO.id,
                providerChapterId: slug,
                chapterNumber: "1",
                chapterTitle: "Chapter 1",
                language: "en",
                publishedAt: null,
                pageCount: pageCount || null,
                imageUrl: "",
                readable: pageCount > 0,
            };
            return [chapter];
        }
        catch (err) {
            throw new types_1.ProviderError(INFO.id, err.message, "network", true);
        }
    },
    async getChapterPages(providerId, chapterId) {
        const slug = chapterId.replace(/^hentaireadmoe-/, "");
        try {
            const html = await fetchHtml(`/hentai/${slug}`, PAGES_TTL);
            const galleryId = galleryIdFromHtml(html);
            const pageCount = parsePageCount(html);
            if (!galleryId || pageCount <= 0) {
                throw new types_1.ProviderError(INFO.id, "no pages found", "parse", false);
            }
            const pages = [];
            for (let i = 1; i <= pageCount; i++) {
                pages.push({ index: i - 1, imageUrl: `https://readimg.site/galleries/${galleryId}/${i}.webp` });
            }
            return pages;
        }
        catch (err) {
            if (err instanceof types_1.ProviderError)
                throw err;
            throw new types_1.ProviderError(INFO.id, err.message, "network", true);
        }
    },
    async getTrending(options = {}) {
        const limit = Math.min(options.limit ?? 24, 50);
        try {
            const html = await fetchHtml("/hentai-list", LISTING_TTL);
            const cards = parseCards(html);
            return cards.slice(0, limit).map((c) => ({
                id: `hentaireadmoe:${c.slug}`,
                provider: INFO.id,
                providerId: c.slug,
                slug: `hentaireadmoe-${c.slug}`,
                title: c.title,
                alternativeTitles: [],
                description: null,
                category: "manga",
                isAdult: true,
                coverImage: c.cover,
                rating: null,
                popularity: null,
                genres: [],
                tags: [],
                artists: [],
                authors: [],
                language: "English",
                status: null,
                updatedAt: null,
                publishedAt: null,
                providerUrl: `${BASE}/hentai/${c.slug}`,
                readable: true,
                adult: (0, adult_1.classifyHentai18)("manga"),
            }));
        }
        catch (err) {
            throw new types_1.ProviderError(INFO.id, err.message, "network", true);
        }
    },
    async getLatestUpdates(options = {}) {
        const limit = Math.min(options.limit ?? 24, 50);
        try {
            const html = await fetchHtml("/hentai-list?sortby=new", LISTING_TTL);
            const cards = parseCards(html);
            const updates = [];
            for (const card of cards.slice(0, limit)) {
                const title = {
                    id: `hentaireadmoe:${card.slug}`,
                    provider: INFO.id,
                    providerId: card.slug,
                    slug: `hentaireadmoe-${card.slug}`,
                    title: card.title,
                    alternativeTitles: [],
                    description: null,
                    category: "manga",
                    isAdult: true,
                    coverImage: card.cover,
                    rating: null,
                    popularity: null,
                    genres: [],
                    tags: [],
                    artists: [],
                    authors: [],
                    language: "English",
                    status: null,
                    updatedAt: null,
                    publishedAt: null,
                    providerUrl: `${BASE}/hentai/${card.slug}`,
                    readable: true,
                    adult: (0, adult_1.classifyHentai18)("manga"),
                };
                const chapter = {
                    id: `hentaireadmoe:${card.slug}`,
                    titleId: title.id,
                    provider: INFO.id,
                    providerChapterId: card.slug,
                    chapterNumber: "1",
                    chapterTitle: "Chapter 1",
                    language: "en",
                    publishedAt: null,
                    pageCount: null,
                    imageUrl: "",
                    readable: true,
                };
                updates.push({ title, chapter });
            }
            return updates;
        }
        catch (err) {
            throw new types_1.ProviderError(INFO.id, err.message, "network", true);
        }
    },
};
