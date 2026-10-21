"use strict";
/**
 * Manhwa Provider Registry
 *
 * This registry manages Manhwa-specific content providers.
 * It uses the Manhwa source priority configuration and provides
 * aggregation services specifically for Manhwa content.
 */
Object.defineProperty(exports, "__esModule", { value: true });
exports.getEnabledManhwaSourceIds = exports.manhwaRegistry = void 0;
exports.registerManhwaProvider = registerManhwaProvider;
exports.getManhwaProvider = getManhwaProvider;
exports.listManhwaProviders = listManhwaProviders;
exports.healthyManhwaProviders = healthyManhwaProviders;
exports.manhwaPriorityScore = manhwaPriorityScore;
exports.getManhwaSourcePriorityOrder = getManhwaSourcePriorityOrder;
exports.aggregateManhwaSearch = aggregateManhwaSearch;
exports.resolveManhwaTitle = resolveManhwaTitle;
exports.getChaptersForManhwaTitle = getChaptersForManhwaTitle;
exports.getPagesForManhwaChapter = getPagesForManhwaChapter;
exports.aggregateManhwaLatest = aggregateManhwaLatest;
exports.aggregateManhwaTrending = aggregateManhwaTrending;
exports.getManhwaProvidersWithCapability = getManhwaProvidersWithCapability;
exports.isManhwaProviderReady = isManhwaProviderReady;
exports.getManhwaProviderConfig = getManhwaProviderConfig;
exports.validateManhwaRegistry = validateManhwaRegistry;
const http_1 = require("./http");
const source_selection_1 = require("./source-selection");
const manhwa_sources_1 = require("./manhwa-sources");
Object.defineProperty(exports, "getEnabledManhwaSourceIds", { enumerable: true, get: function () { return manhwa_sources_1.getEnabledManhwaSourceIds; } });
/* ------------------------------------------------------------------ */
/* Registry                                                            */
/* ------------------------------------------------------------------ */
const manhwaRegistry = new Map();
exports.manhwaRegistry = manhwaRegistry;
/** Register a Manhwa provider adapter. */
function registerManhwaProvider(provider) {
    manhwaRegistry.set(provider.getProviderInfo().id, provider);
}
/** Get a registered Manhwa provider by ID. */
function getManhwaProvider(id) {
    return manhwaRegistry.get(id);
}
/** List all registered Manhwa providers. */
function listManhwaProviders() {
    return [...manhwaRegistry.values()].map((p) => p.getProviderInfo());
}
/** Get registered providers that are currently healthy. */
function healthyManhwaProviders() {
    return [...manhwaRegistry.values()].filter((p) => (0, http_1.providerHealthy)(p.getProviderInfo().id));
}
/* ------------------------------------------------------------------ */
/* Source Priority Integration                                         */
/* ------------------------------------------------------------------ */
/** Get provider priority from Manhwa source config, fallback to generic priority. */
function manhwaPriorityScore(providerId) {
    const source = (0, manhwa_sources_1.getManhwaSource)(providerId);
    if (source && source.enabled) {
        // Convert priority (1=highest) to score (1.0=highest)
        // Max priority is 16, so score = 1.0 - (priority-1)/16
        return 1.0 - (source.priority - 1) / 16;
    }
    // Fallback to generic priority
    return (0, source_selection_1.priorityScore)(providerId);
}
/** Get enabled Manhwa source IDs in priority order. */
function getManhwaSourcePriorityOrder() {
    return (0, manhwa_sources_1.getEnabledManhwaSources)().map((s) => s.id);
}
/* ------------------------------------------------------------------ */
/* Failover fan-out (Manhwa-specific)                                 */
/* ------------------------------------------------------------------ */
async function manhwaFanOut(capability, fn) {
    const candidates = healthyManhwaProviders()
        .filter((p) => p.getProviderInfo().capabilities[capability])
        // Sort by Manhwa priority
        .sort((a, b) => manhwaPriorityScore(b.getProviderInfo().id) - manhwaPriorityScore(a.getProviderInfo().id));
    const settled = await Promise.allSettled(candidates.map((p) => fn(p)));
    const results = [];
    const errors = [];
    let successes = 0;
    settled.forEach((outcome, i) => {
        const id = candidates[i]?.getProviderInfo().id ?? "unknown";
        if (outcome.status === "fulfilled") {
            successes++;
            results.push(...outcome.value);
        }
        else {
            errors.push(`${id}: ${outcome.reason?.message ?? "failed"}`);
        }
    });
    const partial = errors.length > 0 && successes > 0;
    if (successes === 0 && errors.length > 0) {
        return { results: [], partial: true, errors };
    }
    return { results, partial, errors };
}
/** Search/aggregate Manhwa titles across enabled providers. */
async function aggregateManhwaSearch(query, opts = {}) {
    const limit = opts.limit ?? 24;
    const perProvider = Math.min(limit, 50);
    const { results, partial, errors } = await manhwaFanOut("search", (p) => p.searchTitles(query, {
        limit: perProvider,
        offset: opts.offset ?? 0,
        categories: ["manhwa"],
        genres: opts.genres,
        order: opts.order,
        isAdult: opts.isAdult,
    }));
    // Filter to Manhwa category
    const titles = results.filter((t) => t.category === "manhwa");
    // Deduplicate by title (case-insensitive)
    const seen = new Set();
    const deduped = titles.filter((t) => {
        const key = t.title.trim().toLowerCase();
        if (!key || seen.has(key))
            return false;
        seen.add(key);
        return true;
    });
    return { titles: deduped.slice(0, limit), partial, errors, total: deduped.length };
}
/** Resolve one Manhwa title by its stable app slug. */
async function resolveManhwaTitle(slug) {
    const providerId = slug.includes("-") ? slug.slice(0, slug.indexOf("-")) : slug;
    const provider = getManhwaProvider(providerId);
    if (!provider)
        return null;
    const rawId = slug.slice(providerId.length + 1);
    return provider.getTitle(rawId);
}
/** Fetch chapters for a Manhwa title from providers that serve them. */
async function getChaptersForManhwaTitle(title, language = "en", preferredProviders = []) {
    const providers = [...manhwaRegistry.values()].filter((p) => p.getProviderInfo().capabilities.getChapters);
    // Order: preferredProviders first, then by Manhwa priority
    const ordered = [...providers].sort((a, b) => {
        const idA = a.getProviderInfo().id;
        const idB = b.getProviderInfo().id;
        const pa = preferredProviders.indexOf(idA);
        const pb = preferredProviders.indexOf(idB);
        if (pa !== -1 && pb !== -1)
            return pa - pb;
        if (pa !== -1)
            return -1;
        if (pb !== -1)
            return 1;
        return manhwaPriorityScore(idB) - manhwaPriorityScore(idA);
    });
    const seenNumbers = new Set();
    const chapters = [];
    let partial = false;
    for (const provider of ordered) {
        try {
            const fetched = await provider.getChapters(title.providerId, {
                language,
                order: "asc",
            });
            const canReadPages = provider.getProviderInfo().capabilities.getChapterPages;
            for (const ch of fetched) {
                if (seenNumbers.has(ch.chapterNumber))
                    continue;
                seenNumbers.add(ch.chapterNumber);
                chapters.push({ ...ch, readable: canReadPages });
            }
        }
        catch (err) {
            partial = true;
        }
    }
    // Stable sort by chapter number (numeric), then by input order.
    chapters.sort((a, b) => {
        const na = a.chapterNumber !== null ? parseFloat(a.chapterNumber) : NaN;
        const nb = b.chapterNumber !== null ? parseFloat(b.chapterNumber) : NaN;
        if (!isNaN(na) && !isNaN(nb))
            return na - nb;
        if (isNaN(na) && !isNaN(nb))
            return 1;
        if (!isNaN(na) && isNaN(nb))
            return -1;
        return 0;
    });
    return { chapters, partial: false };
}
/** Resolve page images for a chapter. */
async function getPagesForManhwaChapter(providerId, chapterProviderId) {
    const provider = getManhwaProvider(providerId);
    if (!provider?.getProviderInfo().capabilities.getChapterPages) {
        throw new Error(`Provider ${providerId} does not support chapter pages`);
    }
    return provider.getChapterPages(chapterProviderId, chapterProviderId);
}
/** Latest Manhwa updates across providers. */
async function aggregateManhwaLatest(limit = 24, language = "en", offset = 0) {
    const { results, partial, errors } = await manhwaFanOut("latestUpdates", (p) => p.getLatestUpdates
        ? p.getLatestUpdates({ limit: limit + offset, language })
        : Promise.resolve([]));
    results.sort((a, b) => (b.chapter.publishedAt ?? "").localeCompare(a.chapter.publishedAt ?? ""));
    const seen = new Set();
    const updates = results.filter((u) => {
        if (u.title.category !== "manhwa")
            return false;
        return seen.has(u.title.id) ? false : (seen.add(u.title.id), true);
    });
    return { updates: updates.slice(offset, offset + limit), partial, errors, total: updates.length };
}
/** Trending Manhwa across providers. */
async function aggregateManhwaTrending(limit = 24, offset = 0, genres) {
    const { results, partial, errors } = await manhwaFanOut("trending", (p) => p.getTrending ? p.getTrending({ limit: Math.max(limit + offset, limit), categories: ["manhwa"] }) : Promise.resolve([]));
    const titles = results.filter((t) => t.category === "manhwa" && (!genres?.length || genres.some((g) => [...t.genres, ...t.tags].includes(g))));
    return { titles: titles.slice(offset, offset + limit), partial, errors, total: titles.length };
}
/* ------------------------------------------------------------------ */
/* Manhwa-specific capability helpers                                 */
/* ------------------------------------------------------------------ */
/** Get all registered providers that support a specific capability. */
function getManhwaProvidersWithCapability(capability) {
    return [...manhwaRegistry.values()].filter((p) => p.getProviderInfo().capabilities[capability]);
}
/** Check if a provider is enabled and healthy. */
function isManhwaProviderReady(id) {
    const provider = getManhwaProvider(id);
    if (!provider)
        return false;
    return (0, http_1.providerHealthy)(provider.getProviderInfo().id);
}
/** Get source config for a registered provider. */
function getManhwaProviderConfig(id) {
    return (0, manhwa_sources_1.getManhwaSource)(id);
}
/** Validate all enabled sources have implementations. */
function validateManhwaRegistry() {
    const enabledIds = (0, manhwa_sources_1.getEnabledManhwaSourceIds)();
    const registeredIds = [...manhwaRegistry.keys()];
    const missing = enabledIds.filter((id) => !registeredIds.includes(id));
    return { valid: missing.length === 0, missing };
}
