"use strict";
// Hentairead.io adapter.
//
// Classification: VERIFIED_AND_AVAILABLE (trending + title metadata + real rating
// + chapters + readable pages, served in-app).
// hentairead.io is an adult-only hentai catalogue (manga / manhwa / manhua) that
// exposes NO public JSON API — only server-rendered HTML. We fetch the public
// listing, detail and chapter pages with a normal browser-like GET (no access
// control, CAPTCHA, or paywall is bypassed), parse the REAL titles / covers /
// view counts / genres / ratings / chapter lists / page images, and always link
// back to the source.
//
// Role: trending / discovery + a full in-app reader. Users never leave the app:
// chapter page images live on the site's CDN (cdn-ht.mgread.io), which hotlink-
// blocks foreign Referers, so every image is served through our host-allowlisted
// display proxy (/api/hentairead-image) with the site's own Referer — bytes are
// piped through at read time, never stored or re-hosted.
Object.defineProperty(exports, "__esModule", { value: true });
exports.hentairead = void 0;
const http_1 = require("./http");
const adult_1 = require("./adult");
const types_1 = require("./types");
const BASE = "https://hentairead.io";
// Listing/detail caches live for 6 hours, matching the background refresh
// cadence (see scheduler.ts / instrumentation.ts) — the trending page shows a
// list that is at most 6 hours old. Chapter page image lists are stable, so
// they are cached for 24 hours.
const LISTING_TTL = 6 * 60 * 60 * 1000;
const DETAIL_TTL = 6 * 60 * 60 * 1000;
const PAGES_TTL = 24 * 60 * 60 * 1000;
// The detail page server-renders 51 chapter rows and pages the rest through the
// site's own AJAX endpoint (load_list_chapter — discovered in custom_new.js).
// Bound the fan-out: 20 pages ≈ 1000+ chapters, far beyond any real title.
const MAX_CHAPTER_LIST_PAGES = 20;
const CHAPTER_PAGE_FETCH_CONCURRENCY = 4;
const CAPABILITIES = {
    search: false,
    getTitle: true,
    getChapters: true,
    getChapterPages: true,
    trending: true,
    latestUpdates: false,
    ratings: true, // detail page exposes a real schema.org 0..5 rating
};
const INFO = {
    id: "hentairead",
    name: "HentaiRead",
    baseUrl: BASE,
    status: "VERIFIED_AND_AVAILABLE",
    attribution: "Content sourced from hentairead.io (metadata + chapters read in-app via display proxy).",
    capabilities: CAPABILITIES,
    adult: true,
};
/* ------------------------------------------------------------------ */
/* Small parsing helpers                                               */
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
        .replace(/&amp;/g, "&");
}
/** "2.9K" -> 2900 ; "19.9K" -> 19900 ; "222" -> 222. Null when unparseable. */
function parseCount(raw) {
    if (!raw)
        return null;
    const m = String(raw).trim().toUpperCase().match(/^([\d.]+)\s*([KMB])?$/);
    if (!m)
        return null;
    const n = parseFloat(m[1]);
    if (!Number.isFinite(n))
        return null;
    const mult = m[2] === "K" ? 1e3 : m[2] === "M" ? 1e6 : m[2] === "B" ? 1e9 : 1;
    return Math.round(n * mult);
}
function absUrl(src) {
    if (/^https?:\/\//i.test(src))
        return src;
    return `${BASE}/${src.replace(/^\//, "")}`;
}
/**
 * hentairead hotlink-protects its images (covers AND chapter pages: 403 unless
 * the Referer is their own origin), so a bare <img src="https://..."> from our
 * app never loads. Route image bytes through our host-allowlisted display
 * proxy, which fetches server-side with the correct Referer and streams them
 * back (display proxy, nothing stored).
 */
function proxyImage(absoluteUrl) {
    return `/api/hentairead-image?url=${encodeURIComponent(absoluteUrl)}`;
}
/** "/firstclass-seat-to-the-abyss-60286/" -> "firstclass-seat-to-the-abyss-60286" */
function slugFromPath(path) {
    return path.replace(/^\/+|\/+$/g, "");
}
function categoryFromGenreSlugs(slugs) {
    if (slugs.includes("manhwa"))
        return "manhwa";
    if (slugs.includes("manhua"))
        return "manhua";
    return "manga"; // hentairead's taxonomy: manhwa/manhua are explicit genres; else manga
}
function originFromCategory(c) {
    return c; // manga | manhwa | manhua are all valid ContentOrigin values
}
// The cover anchor + img carries path, cover and the title (alt).
const CARD_RE = /<a href="(\/[^"]*?-\d+\/)"><img src="([^"]+)"[^>]*alt="([^"]*)"/g;
// The view block sits immediately before the cover anchor: eye/comment/heart.
const VIEW_RE = /fa-eye">\s*<\/i>\s*([\d.,]+[KMB]?)\s*<i class="far fa-comment"><\/i>[\s\S]{0,300}?<a href="(\/[^"]*?-\d+\/)"/g;
function parseCards(html) {
    const viewsBySlug = new Map();
    let vm;
    VIEW_RE.lastIndex = 0;
    while ((vm = VIEW_RE.exec(html))) {
        const count = parseCount(vm[1]);
        if (count !== null)
            viewsBySlug.set(slugFromPath(vm[2]), count);
    }
    const cards = [];
    const seen = new Set();
    let m;
    CARD_RE.lastIndex = 0;
    while ((m = CARD_RE.exec(html))) {
        const path = m[1];
        const slug = slugFromPath(path);
        if (seen.has(slug))
            continue;
        seen.add(slug);
        cards.push({
            path,
            slug,
            cover: absUrl(m[2]),
            title: unescapeHtml(m[3]).trim(),
            views: viewsBySlug.get(slug) ?? null,
        });
    }
    return cards;
}
function buildListTitle(card, category) {
    return {
        id: `hentairead:${card.slug}`,
        provider: INFO.id,
        providerId: card.slug,
        slug: `hentairead-${card.slug}`,
        title: card.title,
        alternativeTitles: [],
        description: null,
        category,
        isAdult: true,
        coverImage: proxyImage(card.cover),
        rating: null, // listing cards carry no rating; the detail page does
        popularity: card.views,
        genres: [],
        tags: [],
        artists: [],
        authors: [],
        language: "English",
        status: null,
        updatedAt: null,
        publishedAt: null,
        providerUrl: `${BASE}/${card.path}`,
        readable: true, // chapters + pages are served in-app via getChapters/getChapterPages
        colored: true, // hentairead content is predominantly full color
        adult: (0, adult_1.classifyHentairead)(originFromCategory(category)),
    };
}
/* ------------------------------------------------------------------ */
/* Detail parsing                                                      */
/* ------------------------------------------------------------------ */
function firstMatch(html, re) {
    const m = html.match(re);
    return m ? m[1].trim() : null;
}
function buildDetailTitle(html, slug) {
    const title = firstMatch(html, /<h1[^>]*class="title-detail"[^>]*>([^<]+)<\/h1>/);
    if (!title)
        return null;
    const altRaw = firstMatch(html, /<h2[^>]*class="other-name[^"]*"[^>]*>([\s\S]*?)<\/h2>/);
    const alternativeTitles = altRaw
        ? altRaw
            .split(/\s*\/\s*/)
            .map((s) => unescapeHtml(s).trim())
            .filter(Boolean)
        : [];
    // Genres block: <i class="fa fa-tags"> ... <p class="col-8"><a ..>X</a> - <a ..>Y</a>
    const genreBlock = firstMatch(html, /<i class="fa fa-tags">[\s\S]{0,200}?<p class="col-8">([\s\S]*?)<\/p>/);
    const genreSlugs = [];
    const genres = [];
    if (genreBlock) {
        const gre = /<a href="\/genres\/([^\/"]+)\/"[^>]*>([^<]+)<\/a>/g;
        let g;
        while ((g = gre.exec(genreBlock))) {
            genreSlugs.push(g[1]);
            genres.push(unescapeHtml(g[2]).trim());
        }
    }
    const category = categoryFromGenreSlugs(genreSlugs);
    // Real schema.org rating. NormalizedTitle.rating is the 0..100 scale (AniList
    // convention); toManga() later divides by 20 to render 0..5. So store 0..100.
    const ratingRaw = firstMatch(html, /<span itemprop="ratingValue">([\d.]+)<\/span>/);
    const bestRaw = firstMatch(html, /<span itemprop="bestRating">([\d.]+)<\/span>/);
    let rating = null;
    if (ratingRaw) {
        const val = parseFloat(ratingRaw);
        const best = bestRaw ? parseFloat(bestRaw) : 5;
        if (Number.isFinite(val) && Number.isFinite(best) && best > 0) {
            rating = Math.round((val / best) * 100); // normalize to 0..100
        }
    }
    // View count + updated date + status + author.
    const views = parseCount(firstMatch(html, /<i class="fa fa-eye">[\s\S]{0,200}?<p class="col-8">([\d.,]+[KMB]?)<\/p>/));
    const updatedRaw = firstMatch(html, /<time[^>]*>\s*Updated:\s*([^<]+?)\s*<\/time>/);
    const updatedAt = updatedRaw ? new Date(updatedRaw).toISOString() : null;
    const statusRaw = (firstMatch(html, /<i class="fa fa-rss">[\s\S]{0,200}?<p class="col-8">([^<]*)<\/p>/) || "").toLowerCase();
    const status = statusRaw.includes("completed")
        ? "Completed"
        : statusRaw.includes("ongoing") || statusRaw.includes("publishing")
            ? "In Process"
            : statusRaw.includes("hiatus") || statusRaw.includes("cancel")
                ? "Paused"
                : null;
    const authorRaw = firstMatch(html, /<i class="fa fa-user">[\s\S]{0,200}?<p class="col-8">([^<]*)<\/p>/);
    const author = authorRaw && !/updating|^$/.test(authorRaw.toLowerCase()) ? unescapeHtml(authorRaw) : null;
    const cover = absUrl(firstMatch(html, /<meta property="og:image" content="([^"]+)"/) ?? "");
    const description = firstMatch(html, /<meta property="og:description" content="([^"]*)"/);
    return {
        id: `hentairead:${slug}`,
        provider: INFO.id,
        providerId: slug,
        slug: `hentairead-${slug}`,
        title: unescapeHtml(title),
        alternativeTitles,
        description: description ? unescapeHtml(description) : null,
        category,
        isAdult: true,
        coverImage: cover ? proxyImage(cover) : null,
        rating,
        popularity: views,
        genres,
        tags: genres,
        artists: author ? [author] : [],
        authors: author ? [author] : [],
        language: "English",
        status,
        updatedAt,
        publishedAt: null,
        providerUrl: `${BASE}/${slug}/`,
        readable: /class="version-chap"/.test(html), // chapter list rendered on the detail page
        colored: true, // hentairead content is predominantly full color
        adult: (0, adult_1.classifyHentairead)(originFromCategory(category)),
    };
}
/* ------------------------------------------------------------------ */
/* Fetch                                                               */
/* ------------------------------------------------------------------ */
function fetchHtml(path, ttl) {
    const url = path.startsWith("http") ? path : `${BASE}${path}`;
    return (0, http_1.cached)(`hentairead:html:${path}`, ttl ?? (path.includes("-") ? DETAIL_TTL : LISTING_TTL), async () => {
        try {
            // Send the site's own Referer — some edges treat direct hits differently.
            return await (0, http_1.rawText)(url, { timeoutMs: 15000, headers: { Referer: `${BASE}/` } });
        }
        catch (err) {
            throw new types_1.ProviderError(INFO.id, err.message, "network", true);
        }
    });
}
// Server-rendered rows and AJAX rows share this markup (whitespace varies):
// <li class="wp-manga-chapter">
//   <a href="/slug-123/chapter-4-145452/">Chapter 4</a>
//   <span class="chapter-release-date"><i>October 25, 2025</i></span>
// </li>
const CHAPTER_ITEM_RE = /<li class="wp-manga-chapter">\s*<a href="([^"]*\/chapter-[^"]+)"[^>]*>([^<]*)<\/a>\s*(?:<span class="chapter-release-date"><i>([^<]*)<\/i><\/span>)?/g;
function parseChapterItems(html) {
    const items = [];
    CHAPTER_ITEM_RE.lastIndex = 0;
    let m;
    while ((m = CHAPTER_ITEM_RE.exec(html))) {
        let path = m[1].replace(/^https?:\/\/[^/]+/i, ""); // tolerate absolute hrefs
        path = path.replace(/^\/+|\/+$/g, ""); // "slug/chapter-N-ID"
        if (!path.includes("/chapter-"))
            continue;
        items.push({ path, label: m[2].trim(), date: m[3] ? m[3].trim() : null });
    }
    return items;
}
/** Chapter number parsed from the label ("Chapter 12.5" -> "12.5"), else the path. */
function chapterNumberFrom(item) {
    const fromLabel = item.label.match(/chapter\s*([\d.]+)/i);
    if (fromLabel)
        return fromLabel[1];
    const fromPath = item.path.match(/\/chapter-([\d.]+?)(?:-\d+)?$/);
    return fromPath ? fromPath[1] : null;
}
/** "October 25, 2025" -> ISO string. Null when unparseable. */
function isoDateOrNull(raw) {
    if (!raw)
        return null;
    const t = Date.parse(raw);
    return Number.isFinite(t) ? new Date(t).toISOString() : null;
}
/** Hosts our display proxy allows (mirrored in /api/hentairead-image). */
function isAllowedImageHost(url) {
    try {
        const host = new URL(url).hostname;
        return (host === "hentairead.io" ||
            host.endsWith(".hentairead.io") ||
            host === "mgread.io" ||
            host.endsWith(".mgread.io"));
    }
    catch {
        return false;
    }
}
/* ------------------------------------------------------------------ */
/* Adapter                                                             */
/* ------------------------------------------------------------------ */
exports.hentairead = {
    getProviderInfo() {
        return INFO;
    },
    async getTrending(options = {}) {
        const limit = Math.min(options.limit ?? 20, 40);
        const want = options.categories?.length ? new Set(options.categories) : null;
        // Global hot feed (the site's real "trending") + the two category pages so
        // manhwa / manhua are guaranteed to be represented even when /hot/ skews to
        // one category. Genre pages are the authoritative category signal for their
        // own items; /hot/ items are classified by cross-referencing those sets.
        const [hotHtml, manhwaHtml, manhuaHtml] = await Promise.all([
            fetchHtml("/hot/"),
            fetchHtml("/genres/manhwa/"),
            fetchHtml("/genres/manhua/"),
        ]);
        const manhwaSlugs = new Set(parseCards(manhwaHtml).map((c) => c.slug));
        const manhuaSlugs = new Set(parseCards(manhuaHtml).map((c) => c.slug));
        const bySlug = new Map();
        // 1) Global /hot/ first — preserves the site's trending order.
        for (const card of parseCards(hotHtml)) {
            const cat = manhwaSlugs.has(card.slug)
                ? "manhwa"
                : manhuaSlugs.has(card.slug)
                    ? "manhua"
                    : "manga";
            bySlug.set(card.slug, buildListTitle(card, cat));
        }
        // 2) Category pages — fill in manhwa/manhua not present on /hot/.
        for (const card of parseCards(manhwaHtml)) {
            if (!bySlug.has(card.slug))
                bySlug.set(card.slug, buildListTitle(card, "manhwa"));
        }
        for (const card of parseCards(manhuaHtml)) {
            if (!bySlug.has(card.slug))
                bySlug.set(card.slug, buildListTitle(card, "manhua"));
        }
        let titles = [...bySlug.values()];
        if (want)
            titles = titles.filter((t) => !!t.category && want.has(t.category));
        return titles.slice(0, limit);
    },
    async getTitle(providerId) {
        try {
            const html = await fetchHtml(`/${providerId}/`);
            return buildDetailTitle(html, providerId);
        }
        catch {
            return null; // graceful: unknown/removed slug resolves to "unavailable"
        }
    },
    async searchTitles() {
        throw new types_1.ProviderError(INFO.id, "search is not supported by this source", "unsupported", false);
    },
    async getChapters(providerId, options = {}) {
        const slug = providerId.replace(/^hentairead-/, "");
        const html = await fetchHtml(`/${slug}/`);
        // Page 1 server-renders up to 51 rows inside the dedicated chapter list.
        const listUl = html.match(/<ul class="version-chap"[\s\S]*?<\/ul>/);
        const items = listUl ? parseChapterItems(listUl[0]) : [];
        // Longer titles page the remainder through the site's own AJAX endpoint
        // (function load_list_chapter defined in /layout/default/js/custom_new.js —
        // a real endpoint discovered in their front-end, not invented).
        const mangaId = firstMatch(html, /id="title-detail-manga"[^>]*data-manga="(\d+)"/) ?? firstMatch(html, /data-manga="(\d+)"/);
        const pageHints = [...html.matchAll(/load_list_chapter\((\d+)\)/g)];
        const totalPages = pageHints.reduce((max, m) => Math.max(max, Number(m[1]) || 0), 1);
        if (mangaId && totalPages > 1) {
            const wanted = Math.min(totalPages, MAX_CHAPTER_LIST_PAGES);
            const ajaxPath = (p) => `/?act=ajax&code=load_list_chapter&manga_id=${mangaId}&page_num=${p}&chap_id=0&keyword=`;
            for (let start = 2; start <= wanted; start += CHAPTER_PAGE_FETCH_CONCURRENCY) {
                const batch = [];
                for (let p = start; p <= Math.min(start + CHAPTER_PAGE_FETCH_CONCURRENCY - 1, wanted); p++)
                    batch.push(p);
                const results = await Promise.allSettled(batch.map(async (p) => {
                    const raw = await fetchHtml(ajaxPath(p), DETAIL_TTL);
                    // Response is JSON { list_chap, nav } whose HTML rows are string-
                    // escaped — parse the JSON first, then the rows.
                    let listHtml = raw;
                    try {
                        listHtml = String(JSON.parse(raw).list_chap ?? "");
                    }
                    catch {
                        /* not JSON — treat the body itself as row markup */
                    }
                    return parseChapterItems(listHtml);
                }));
                for (const r of results) {
                    if (r.status === "fulfilled")
                        items.push(...r.value);
                }
            }
        }
        // Dedupe (pages can repeat a boundary row). providerChapterId is the full
        // site path with "/" -> "__" so chapter pages are fetchable from the id
        // alone — the canonical slug inside the href may differ from the requested
        // slug (old aliases still serve 200s).
        const seen = new Set();
        let chapters = items
            .filter((it) => (seen.has(it.path) ? false : (seen.add(it.path), true)))
            .map((it) => ({
            id: `hentairead:${it.path}`,
            titleId: `hentairead:${slug}`,
            provider: INFO.id,
            providerChapterId: it.path.split("/").join("__"),
            chapterNumber: chapterNumberFrom(it),
            chapterTitle: it.label || null,
            language: "en",
            publishedAt: isoDateOrNull(it.date),
            pageCount: null,
            imageUrl: "",
            readable: true, // page images resolve at read time from the chapter page
        }));
        if (options.order === "asc")
            chapters = chapters.slice().reverse(); // site lists newest-first
        return chapters;
    },
    async getChapterPages(_providerId, chapterId) {
        // chapterId = "<canonical-slug>__chapter-<n>-<id>" (set in getChapters).
        const path = chapterId.replace(/__+/g, "/");
        const html = await fetchHtml(`/${path}/`, PAGES_TTL);
        // Reader pages carry data-index="N" and are served from the site's CDN
        // (cdn-ht.mgread.io), which hotlink-blocks foreign Referers — every src is
        // therefore routed through our display proxy below.
        const tagged = new Map();
        const tagRe = /<img[^>]*data-index="(\d+)"[^>]*>/g;
        let t;
        while ((t = tagRe.exec(html))) {
            const src = t[0].match(/src="([^"]+)"/)?.[1];
            if (!src)
                continue;
            const abs = absUrl(src);
            if (!isAllowedImageHost(abs))
                continue;
            const idx = Number(t[1]);
            if (!tagged.has(idx))
                tagged.set(idx, abs);
        }
        let sources = [...tagged.entries()]
            .sort((a, b) => a[0] - b[0])
            .map(([, src]) => src);
        if (sources.length === 0) {
            // Fallback: document order on the CDN hosts (in case data-index is absent).
            const seen = new Set();
            const re = /<img[^>]+src="([^"]+)"/g;
            let m;
            while ((m = re.exec(html))) {
                const abs = absUrl(m[1]);
                if (!/\.mgread\.io$/i.test(new URL(abs).hostname) || seen.has(abs))
                    continue;
                seen.add(abs);
                sources.push(abs);
            }
        }
        if (sources.length === 0) {
            throw new types_1.ProviderError(INFO.id, "no pages found in chapter", "parse", false);
        }
        return sources.map((src, index) => ({ index, imageUrl: proxyImage(src) }));
    },
};
