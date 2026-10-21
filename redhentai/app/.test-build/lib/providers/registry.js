"use strict";
// Provider registry + aggregation services.
//
// A single place to enumerate providers, detect capabilities, and run
// failover-aware fan-out. A failing provider never takes the app down: each
// source is queried independently, failures are caught per-provider, and
// partial results are flagged so callers can tell them apart from full ones.
Object.defineProperty(exports, "__esModule", { value: true });
exports.getProvider = getProvider;
exports.listProviders = listProviders;
exports.healthyProviders = healthyProviders;
exports.aggregateSearch = aggregateSearch;
exports.resolveTitle = resolveTitle;
exports.getChaptersForTitle = getChaptersForTitle;
exports.findChaptersByTitleMatch = findChaptersByTitleMatch;
exports.getPagesForChapter = getPagesForChapter;
exports.aggregateLatest = aggregateLatest;
exports.aggregateTrending = aggregateTrending;
exports.exclusionReason = exclusionReason;
exports.interleave = interleave;
const http_1 = require("./http");
const source_selection_1 = require("./source-selection");
const series_matching_1 = require("./series-matching");
const reconcile_1 = require("./reconcile");
const anilist_1 = require("./anilist");
const dynasty_1 = require("./dynasty");
const hentairead_1 = require("./hentairead");
const hentai18_1 = require("./hentai18");
const hentaireadmoe_1 = require("./hentaireadmoe");
const enma_1 = require("./enma");
const omegascans_1 = require("./omegascans");
const hiperdex_1 = require("./hiperdex");
const adult_1 = require("./adult");
const types_1 = require("./types");
/* ------------------------------------------------------------------ */
/* Registry                                                            */
/* ------------------------------------------------------------------ */
const registry = new Map();
function register(provider) {
    registry.set(provider.getProviderInfo().id, provider);
}
// --- Enabled, verified providers ------------------------------------
register(anilist_1.anilist); // metadata + ratings only
register(dynasty_1.dynasty); // latest + metadata + pages-by-permalink (no search / no chapter list)
register(hentairead_1.hentairead); // trending + title metadata + chapters + in-app reader (via display proxy)
register(hentai18_1.hentai18); // search + trending + latest + metadata + chapters + reader pages
register(hentaireadmoe_1.hentaireadmoe); // trending + latest + metadata + chapters + reader pages
register(enma_1.enma); // nhentai (official API v2) via the local Enma sidecar — SELF_HOST_REQUIRED
// Manhwa providers
register(omegascans_1.omegascans); // trending + title metadata + chapters + in-app reader (via display proxy)
register(hiperdex_1.hiperdex); // trending + title metadata + chapters + in-app reader (via display proxy)
// --- Disabled providers ---------------------------------------------
// The former local `doujin-api` (nhentai scraper) is intentionally NOT
// registered. It used curl_cffi to impersonate Chrome and bypass TLS-fingerprint
// anti-bot protection, which violates upstream access controls and is outside
// the permitted use for this project (classification:
// NOT_AUTHORIZED_FOR_INTENDED_USE). See docs/PROVIDERS.md.
function getProvider(id) {
    return registry.get(id);
}
function listProviders() {
    return [...registry.values()].map((p) => p.getProviderInfo());
}
/** Providers currently able to serve requests (breaker closed). */
function healthyProviders() {
    return [...registry.values()].filter((p) => (0, http_1.providerHealthy)(p.getProviderInfo().id));
}
/* ------------------------------------------------------------------ */
/* Failover fan-out                                                    */
/* ------------------------------------------------------------------ */
/** Run fn across every provider that declares `capability`, isolating failures. */
async function fanOut(capability, fn) {
    const candidates = healthyProviders().filter((p) => p.getProviderInfo().capabilities[capability]);
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
    // Partial when some provider failed but we still have (or expected) results.
    const partial = errors.length > 0 && successes > 0;
    if (successes === 0 && errors.length > 0) {
        // Everything failed — surface as empty but record the cause.
        return { results: [], partial: true, errors };
    }
    return { results, partial, errors };
}
/** Search/aggregate titles across every provider that supports search, grouping into canonical series with merged chapters. */
async function aggregateSearch(query, opts = {}) {
    const limit = opts.limit ?? 24;
    const perProvider = Math.min(limit, 50);
    const { results, partial, errors } = await fanOut("search", (p) => p.searchTitles(query, {
        limit: perProvider,
        offset: opts.offset ?? 0,
        categories: opts.categories,
        genres: opts.genres,
        order: opts.order,
    }));
    const filtered = filterTitles(results, opts.categories, opts.genres);
    const deduped = dedupeTitles(filtered);
    // Group into canonical series (cross-provider deduplication)
    const series = (0, series_matching_1.groupIntoCanonicalSeries)(deduped);
    // For each canonical series, fetch and reconcile chapters from all providers
    const chapterProviders = [...registry.values()].filter((p) => p.getProviderInfo().capabilities.getChapters);
    const seriesWithChapters = await Promise.all(series.map(async (s) => {
        // Collect chapter inputs from all providers that have this series
        const chapterInputs = [];
        for (const mapping of s.providerMappings) {
            const provider = registry.get(mapping.providerId);
            if (!provider?.getProviderInfo().capabilities.getChapters)
                continue;
            try {
                const chapters = await provider.getChapters(mapping.providerSeriesId, {
                    language: "en",
                    order: "asc",
                });
                for (const ch of chapters) {
                    chapterInputs.push({
                        providerId: provider.getProviderInfo().id,
                        providerSeriesId: mapping.providerSeriesId,
                        providerChapterId: ch.providerChapterId,
                        label: ch.chapterTitle ?? ch.chapterNumber ?? `Chapter ${ch.chapterNumber ?? "?"}`,
                        title: ch.chapterTitle ?? null,
                        volumeNumber: ch.volumeNumber,
                        language: ch.language ?? "en",
                        releaseGroup: null,
                        sourceUrl: mapping.sourceUrl,
                        pageAccessCapability: provider.getProviderInfo().capabilities.getChapterPages ? "available" : "metadata_only",
                        pageCount: ch.pageCount ?? null,
                        publishedAt: ch.publishedAt ?? null,
                    });
                }
            }
            catch {
                // Provider failed - skip, other providers may still have chapters
            }
        }
        // Reconcile chapters from all providers
        const reconciled = (0, reconcile_1.reconcileChapters)(s.id, chapterInputs);
        return {
            ...s,
            chapters: reconciled,
            readable: reconciled.some((c) => c.sourceVersions.some((v) => v.pageAccessCapability === "available")),
        };
    }));
    // Sort by most recent update (or relevance for search)
    const ordered = opts.order === "relevance"
        ? seriesWithChapters
        : seriesWithChapters.sort((a, b) => {
            const dateA = a.chapters[a.chapters.length - 1]?.sourceVersions[0]?.publishedAt ?? "";
            const dateB = b.chapters[b.chapters.length - 1]?.sourceVersions[0]?.publishedAt ?? "";
            return dateB.localeCompare(dateA);
        });
    return { series: ordered.slice(0, limit), partial, errors, total: ordered.length };
}
/** Resolve one title by its stable app slug (`<provider>-<providerId>`). */
async function resolveTitle(slug) {
    const providerId = slug.includes("-") ? slug.slice(0, slug.indexOf("-")) : slug;
    const provider = registry.get(providerId);
    if (!provider)
        return null;
    const rawId = slug.slice(providerId.length + 1);
    return provider.getTitle(rawId);
}
/** Fetch chapters for a title from providers that actually serve them.
 *
 * Phase 1: chapter-capable providers are asked with the title's own
 * `providerId` (works when ids coincide across slug-based sources), ordered by
 * provider priority (see `PROVIDER_PRIORITY` in source-selection) and
 * `preferredProviders` first. Duplicate chapter numbers are deduplicated,
 * keeping the highest-priority provider's version.
 *
 * Phase 2: if nobody answered (metadata-only records like AniList/Dynasty, or
 * a foreign id), other chapter-capable providers are searched by TITLE and the
 * first confident series match supplies the chapters — so every profile page
 * gets something to read instead of an empty collection.
 */
async function getChaptersForTitle(title, language = "en", preferredProviders = []) {
    const providers = [...registry.values()].filter((p) => p.getProviderInfo().capabilities.getChapters);
    // Order: preferredProviders first (in given order), then by priority score,
    // then the title's own provider, then everything else.
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
        const sa = (0, source_selection_1.priorityScore)(idA);
        const sb = (0, source_selection_1.priorityScore)(idB);
        if (sa !== sb)
            return sb - sa;
        // Title's own provider gets a small bump for continuity.
        const ta = idA === title.provider ? 1 : 0;
        const tb = idB === title.provider ? 1 : 0;
        return tb - ta;
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
    // Cross-provider fallback: nobody served this provider's id. Search other
    // chapter-capable sources for the same series and use their chapters.
    if (chapters.length === 0) {
        const matched = await findChaptersByTitleMatch(title, language, ordered);
        for (const ch of matched) {
            if (seenNumbers.has(ch.chapterNumber))
                continue;
            seenNumbers.add(ch.chapterNumber);
            chapters.push(ch);
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
    return { chapters, partial };
}
/** Cross-provider chapter fallback used by `getChaptersForTitle`.
 *
 * Searches each chapter-capable, search-capable provider (except the title's
 * own — its id already produced nothing) for the same series, then returns
 * that match's chapters, marked `readable` from the serving provider's
 * capability. A hit counts as the same series when its normalized title/alt-
 * title set intersects exactly (the strongest identity signal) OR when
 * `areSameSeries` confirms it from corroborating metadata — adult sources
 * often lack year/author data, so exact identity alone must suffice. A wrong
 * series can never leak in: non-matching search hits are skipped.
 * Returns `[]` when no source carries the series. Never throws — a dead
 * search endpoint or failing chapter fetch just moves to the next candidate.
 */
async function findChaptersByTitleMatch(title, language, ordered) {
    const candidates = ordered
        .filter((p) => {
        const caps = p.getProviderInfo().capabilities;
        return caps.search && caps.getChapters && p.getProviderInfo().id !== title.provider;
    })
        .slice(0, 4); // bound worst-case latency (sequential search per source)
    const queries = [title.title, ...title.alternativeTitles]
        .map((q) => q?.trim())
        .filter((q) => Boolean(q))
        .slice(0, 2);
    const identityTokens = (t) => new Set([t.title, ...t.alternativeTitles]
        .map((s) => (0, series_matching_1.normalizeTitleForMatch)(s ?? ""))
        .filter(Boolean));
    const idQuery = identityTokens(title);
    for (const provider of candidates) {
        const canReadPages = provider.getProviderInfo().capabilities.getChapterPages;
        for (const query of queries) {
            let hits = [];
            try {
                hits = await provider.searchTitles(query, { limit: 10 });
            }
            catch {
                continue; // dead search endpoint — next source
            }
            const match = hits.find((hit) => {
                const idHit = identityTokens(hit);
                for (const tok of idQuery)
                    if (idHit.has(tok))
                        return true;
                return (0, series_matching_1.areSameSeries)(title, hit);
            });
            if (!match)
                continue;
            try {
                const fetched = await provider.getChapters(match.providerId, {
                    language,
                    order: "asc",
                });
                if (fetched.length > 0) {
                    return fetched.map((ch) => ({ ...ch, readable: canReadPages }));
                }
            }
            catch {
                // matched, but its chapter list failed — next source
            }
        }
    }
    return [];
}
/** Resolve page images for a chapter. Only providers with the capability. */
async function getPagesForChapter(providerId, chapterProviderId) {
    const provider = registry.get(providerId);
    if (!provider?.getProviderInfo().capabilities.getChapterPages) {
        throw new types_1.ProviderError(providerId, "no readable pages from this source", "unsupported", false);
    }
    return provider.getChapterPages(chapterProviderId, chapterProviderId);
}
/** Latest updates aggregated across providers that expose them. */
async function aggregateLatest(limit = 24, language = "en", offset = 0) {
    const { results, partial, errors } = await fanOut("latestUpdates", (p) => p.getLatestUpdates
        ? p.getLatestUpdates({ limit: limit + offset, language })
        : Promise.resolve([]));
    results.sort((a, b) => (b.chapter.publishedAt ?? "").localeCompare(a.chapter.publishedAt ?? ""));
    const seen = new Set();
    const updates = results.filter((u) => {
        // Same central adult gate as search/trending — a secondary provider's
        // general-audience update must not slip into the adult latest feed.
        if (!(0, adult_1.isEligible)(u.title.adult.classification, adult_1.DEFAULT_ADULT_POLICY))
            return false;
        return seen.has(u.title.id) ? false : (seen.add(u.title.id), true);
    });
    return { updates: updates.slice(offset, offset + limit), partial, errors, total: updates.length };
}
/** Trending/popularity across providers that expose it. */
async function aggregateTrending(limit = 24, categories, offset = 0, period, genres) {
    // `period` is accepted for API compatibility; providers expose a single
    // trending list, so all periods use it (documented fallback).
    void period;
    const { results, partial, errors } = await fanOut("trending", (p) => p.getTrending ? p.getTrending({ limit: Math.max(limit + offset, limit), categories }) : Promise.resolve([]));
    const titles = dedupeTitles(filterTitles(results, categories, genres));
    const ordered = interleave(titles);
    // Interleave provider results so one source doesn't dominate the top slots.
    return {
        titles: ordered.slice(offset, offset + limit),
        partial,
        errors,
        total: ordered.length,
    };
}
/* ------------------------------------------------------------------ */
/* Helpers                                                             */
/* ------------------------------------------------------------------ */
/**
 * Central eligibility filter. Applied to EVERY aggregation path before results
 * reach the UI — this is the data-layer adult gate. A general-audience title
 * returned by a secondary provider cannot leak through here, and neither can an
 * unclassified ("unknown") title under the conservative default policy.
 */
function filterTitles(titles, categories, genres, policy = adult_1.DEFAULT_ADULT_POLICY) {
    return titles.filter((t) => {
        // Adult-content eligibility first: origin category is irrelevant if the
        // work cannot enter the adult catalogue at all.
        if (!(0, adult_1.isEligible)(t.adult.classification, policy))
            return false;
        if (categories?.length && (!t.category || !categories.includes(t.category)))
            return false;
        if (genres?.length && !genres.some((g) => [...t.genres, ...t.tags].includes(g)))
            return false;
        return true;
    });
}
/** Why a title was excluded — for diagnostics/tests, never shown to end users. */
function exclusionReason(t, policy = adult_1.DEFAULT_ADULT_POLICY) {
    if ((0, adult_1.isEligible)(t.adult.classification, policy))
        return null;
    return `${t.adult.classification} not eligible (${t.adult.reason ?? "no reason"})`;
}
const COMMON_SUFFIXES = [
    "raw",
    "uncensored",
    "decensored",
    "english",
    "colored",
    "colour",
    "digital",
    "fan colored",
    "fan-coloured",
    "official",
    "scanlation",
];
/** Normalize title for deduplication: lowercase, strip common suffixes & punctuation. */
function normalizeTitleForDedupe(title) {
    let key = title.trim().toLowerCase();
    // Remove parenthetical suffixes like "(Raw)", "[Uncensored]", etc.
    key = key.replace(/[\(\[].*?[\)\]]/g, "").trim();
    // Remove common suffixes at end
    for (const suffix of COMMON_SUFFIXES) {
        const pattern = new RegExp(`(?:\\s|[-_])${suffix}$`);
        if (pattern.test(key)) {
            key = key.replace(pattern, "").trim();
        }
    }
    // Collapse whitespace/punctuation
    key = key.replace(/[^a-z0-9]+/g, " ").trim();
    return key;
}
function dedupeTitles(titles) {
    const seen = new Set();
    return titles.filter((t) => {
        const key = normalizeTitleForDedupe(t.title);
        if (!key || seen.has(key))
            return false;
        seen.add(key);
        return true;
    });
}
/**
 * Interleave so one provider's contiguous block doesn't dominate the top of
 * trending. `fanOut` pushes each provider's results contiguously, so lifting
 * every `stride`-th item pulls one item from each provider block to the front;
 * a second pass then appends all remaining items in order.
 *
 * Guarantees: ALWAYS terminates and preserves EVERY input item. The previous
 * implementation re-incremented `i` past the end while `out.length` could never
 * reach `items.length`, causing an infinite synchronous loop that blocked Node's
 * event loop for any list of length >= 2 (and dropped ~2/3 of results).
 */
/** Round-robin interleave so trending isn't a single provider's list.
 * Exported for regression tests (see __tests__/registry.test.ts). */
function interleave(items) {
    const n = items.length;
    if (n <= 1)
        return items;
    const stride = 3; // ~ number of registered providers
    const emitted = new Array(n).fill(false);
    const out = [];
    for (let i = 0; i < n; i += stride) {
        out.push(items[i]);
        emitted[i] = true;
    }
    for (let i = 0; i < n; i++) {
        if (!emitted[i])
            out.push(items[i]);
    }
    return out;
}
