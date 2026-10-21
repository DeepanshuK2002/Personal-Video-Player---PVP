"use strict";
// Source selection + chapter-level fallback.
//
// Given a canonical chapter with several source versions, choose the best
// ELIGIBLE version and, if it fails to load, fall back to another eligible
// version of the SAME chapter. Eligibility is checked BEFORE scoring: a source
// is never selected for a capability it does not support or a use that is not
// authorized. Fallback is bounded and observable — never retries forever and
// never substitutes a different chapter.
//
// Scores are normalized to 0..1. Raw milliseconds are never used as a score;
// lower latency yields a higher latency score. Reliability/latency are only
// trusted past a minimum sample size — otherwise a neutral value is used.
Object.defineProperty(exports, "__esModule", { value: true });
exports.SCORE_WEIGHTS = exports.PROVIDER_PRIORITY = void 0;
exports.recordSuccess = recordSuccess;
exports.recordFailure = recordFailure;
exports.getObservation = getObservation;
exports.resetObservations = resetObservations;
exports.priorityScore = priorityScore;
exports.manhwaPriorityScore = manhwaPriorityScore;
exports.eligibleVersions = eligibleVersions;
exports.scoreVersion = scoreVersion;
exports.rankVersions = rankVersions;
exports.selectBestVersion = selectBestVersion;
exports.resolveWithFallback = resolveWithFallback;
const manhwa_sources_1 = require("./manhwa-sources");
/** In-memory rolling observations, updated from real request outcomes. */
const observations = new Map();
/** Minimum samples before latency/reliability are trusted. */
const MIN_SAMPLES = 3;
function recordSuccess(providerId, latencyMs) {
    const o = ensure(providerId);
    o.success++;
    o.latencyMs = Number.isFinite(o.latencyMs)
        ? o.latencyMs * 0.7 + latencyMs * 0.3 // EWMA
        : latencyMs;
    o.lastSuccessAt = Date.now();
}
function recordFailure(providerId) {
    const o = ensure(providerId);
    o.failure++;
    o.lastFailureAt = Date.now();
}
function getObservation(providerId) {
    return observations.get(providerId);
}
/** Test hook: reset all observations. */
function resetObservations() {
    observations.clear();
}
function ensure(id) {
    let o = observations.get(id);
    if (!o) {
        o = { success: 0, failure: 0, latencyMs: NaN, lastSuccessAt: null, lastFailureAt: null };
        observations.set(id, o);
    }
    return o;
}
/* ------------------------------------------------------------------ */
/* Provider priority                                                   */
/* ------------------------------------------------------------------ */
/**
 * Static provider priority (0..1). Higher = preferred as a chapter source.
 * Omega Scans is set highest due to its image quality.
 * Manhwa sources are ranked by their configured priority (1=highest).
 * All other providers default to neutral 0.5.
 */
exports.PROVIDER_PRIORITY = {
    "omega-scans": 1.0,
    // Manhwa sources (priority 1=highest, mapped to 1.0 down to ~0.06)
    "omegascans": 1.0,
    "hiperdex": 0.94,
    "hentai20": 0.88,
    "manhwax": 0.81,
    "manhwaclub": 0.75,
    "manhwa18": 0.69,
    "lewdmanhwa": 0.63,
    "hasbicmanhwa": 0.56,
    "kairomanhwa": 0.5,
    "doujiva-manhwa": 0.44,
    "hentara": 0.38,
    "manhwa18cc": 0.31,
    "mangaforfree": 0.25,
    "manga18fx": 0.19,
    "webtoonscan": 0.13,
    "manga18club": 0.06,
};
/** Priority score 0..1 for a provider id. Unknown providers are neutral 0.5. */
function priorityScore(providerId) {
    return exports.PROVIDER_PRIORITY[providerId] ?? 0.5;
}
/** Get priority from Manhwa source config if available, else fallback to PROVIDER_PRIORITY. */
function manhwaPriorityScore(providerId) {
    // Check if it's a Manhwa source
    const manhwaSource = manhwa_sources_1.MANHWA_SOURCES?.find?.((s) => s.id === providerId);
    if (manhwaSource && manhwaSource.enabled) {
        // Priority 1 = 1.0, priority 16 = ~0.06
        return 1.0 - (manhwaSource.priority - 1) / 16;
    }
    return exports.PROVIDER_PRIORITY[providerId] ?? 0.5;
}
/* Scoring                                                             */
/* ------------------------------------------------------------------ */
/** Configurable weights (sum = 1.0). Initial values, not mandatory. */
exports.SCORE_WEIGHTS = {
    completeness: 0.2,
    languageMatch: 0.2,
    availability: 0.2,
    reliability: 0.15,
    latency: 0.1,
    freshness: 0.05,
    priority: 0.1,
};
/**
 * Eligibility filter. Returns the subset of versions that MAY serve the request.
 * A version is ineligible if it cannot provide the required capability, is in a
 * disallowed language (when a preference exists), or is marked unavailable.
 */
function eligibleVersions(versions, ctx = {}) {
    return versions.filter((v) => {
        if (v.pageAccessCapability === "unavailable")
            return false;
        if (ctx.needsPages && v.pageAccessCapability !== "available")
            return false;
        if (ctx.preferredLanguage && v.language !== "und" && v.language !== ctx.preferredLanguage) {
            return false;
        }
        return true;
    });
}
/** Reliability 0..1 from rolling observations (neutral 0.5 when unknown). */
function reliabilityScore(providerId) {
    const o = observations.get(providerId);
    if (!o)
        return 0.5;
    const total = o.success + o.failure;
    if (total < MIN_SAMPLES)
        return 0.5; // not enough evidence — stay neutral
    return o.success / total;
}
/** Latency 0..1 where lower ms scores HIGHER (0..cap scaled). Neutral 0.5 unknown. */
function latencyScore(providerId) {
    const o = observations.get(providerId);
    if (!o || !Number.isFinite(o.latencyMs) || o.success < MIN_SAMPLES)
        return 0.5;
    // Map [0, 2000ms] -> [1, 0], clamped. 2s is a reasonable "slow" ceiling.
    const clamped = Math.min(Math.max(o.latencyMs, 0), 2000);
    return 1 - clamped / 2000;
}
/** Availability 0..1: readable pages > link-out > metadata-only. */
function availabilityScore(v) {
    switch (v.pageAccessCapability) {
        case "available":
            return 1;
        case "link_out_only":
            return 0.5;
        case "metadata_only":
            return 0.25;
        case "unavailable":
            return 0;
    }
}
/** Freshness 0..1 from publishedAt recency (neutral 0.5 when unknown). */
function freshnessScore(v, now) {
    if (!v.publishedAt)
        return 0.5;
    const t = Date.parse(v.publishedAt);
    if (!Number.isFinite(t))
        return 0.5;
    const ageDays = Math.max(0, (now - t) / 86400000);
    // 30+ days old -> 0; published today -> 1.
    return Math.max(0, 1 - ageDays / 30);
}
/** Language match 0..1 (exact 1, unknown 0.5, mismatch 0). */
function languageScore(v, preferred) {
    if (!preferred)
        return 0.5;
    if (v.language === "und")
        return 0.5;
    return v.language === preferred ? 1 : 0;
}
/**
 * Completeness proxy 0..1: a version that reports a page count and a number is
 * more likely to be a complete, well-formed chapter than one reporting neither.
 * (Provider-level completeness across the whole series is handled by merging.)
 */
function completenessScore(v) {
    let s = 0.5;
    if (v.pageCount && v.pageCount > 0)
        s += 0.3;
    if (v.chapterNumber !== null && v.chapterNumber !== undefined)
        s += 0.2;
    return Math.min(1, s);
}
/** Aggregate weighted score for one version, 0..1. */
function scoreVersion(v, ctx = {}) {
    const now = ctx.now ?? Date.now();
    return (exports.SCORE_WEIGHTS.completeness * completenessScore(v) +
        exports.SCORE_WEIGHTS.languageMatch * languageScore(v, ctx.preferredLanguage) +
        exports.SCORE_WEIGHTS.availability * availabilityScore(v) +
        exports.SCORE_WEIGHTS.reliability * reliabilityScore(v.providerId) +
        exports.SCORE_WEIGHTS.latency * latencyScore(v.providerId) +
        exports.SCORE_WEIGHTS.freshness * freshnessScore(v, now) +
        exports.SCORE_WEIGHTS.priority * priorityScore(v.providerId));
}
/** Rank every version of a chapter; ineligible versions are kept but flagged. */
function rankVersions(chapter, ctx = {}) {
    const eligible = new Set(eligibleVersions(chapter.sourceVersions, ctx));
    return chapter.sourceVersions.map((v) => {
        const isElig = eligible.has(v);
        return {
            version: v,
            eligible: isElig,
            score: scoreVersion(v, ctx),
            reason: isElig ? undefined : ineligibleReason(v, ctx),
        };
    });
}
function ineligibleReason(v, ctx) {
    if (v.pageAccessCapability === "unavailable")
        return "source unavailable";
    if (ctx.needsPages && v.pageAccessCapability !== "available") {
        return `cannot serve pages (${v.pageAccessCapability})`;
    }
    if (ctx.preferredLanguage && v.language !== "und" && v.language !== ctx.preferredLanguage) {
        return `language ${v.language} != preferred ${ctx.preferredLanguage}`;
    }
    return "not eligible";
}
/**
 * Choose the single best eligible version for a chapter (highest score).
 * Returns null when no eligible version exists — the caller must surface an
 * honest "unavailable" state rather than substituting another chapter.
 */
function selectBestVersion(chapter, ctx = {}) {
    const ranked = rankVersions(chapter, ctx)
        .map((r, i) => ({ r, i }))
        .filter(({ r }) => r.eligible)
        .sort((a, b) => {
        const d = b.r.score - a.r.score;
        if (Math.abs(d) < 1e-9)
            return a.i - b.i;
        return d;
    })
        .map(({ r }) => r);
    return ranked[0]?.version ?? null;
}
/**
 * Try eligible versions of the SAME chapter in score order until one loads.
 *
 * Guarantees:
 *   - Only versions of the requested chapter are ever tried (never a different
 *     chapter / never fabricated).
 *   - Attempts are bounded by `maxAttempts`.
 *   - Every attempt is recorded for observability.
 *   - Returns null (with attempts) when all eligible versions fail, so the UI
 *     can show an honest error instead of silently swapping content.
 */
async function resolveWithFallback(chapter, load, opts = {}) {
    const ctx = opts.ctx ?? {};
    const max = opts.maxAttempts ?? 3;
    const candidates = rankVersions(chapter, ctx)
        .map((r, i) => ({ r, i }))
        .filter(({ r }) => r.eligible)
        .sort((a, b) => {
        const d = b.r.score - a.r.score;
        if (Math.abs(d) < 1e-9)
            return a.i - b.i;
        return d;
    })
        .map(({ r }) => r)
        .slice(0, max);
    const attempts = [];
    for (const c of candidates) {
        try {
            const value = await load(c.version);
            recordSuccess(c.version.providerId, 0); // success, latency unknown here
            attempts.push({
                providerId: c.version.providerId,
                providerChapterId: c.version.providerChapterId,
                ok: true,
            });
            return { value, attempts, servedBy: c.version.providerId };
        }
        catch (err) {
            const message = err?.message ?? "failed";
            recordFailure(c.version.providerId);
            attempts.push({
                providerId: c.version.providerId,
                providerChapterId: c.version.providerChapterId,
                ok: false,
                error: message,
            });
        }
    }
    return { value: null, attempts, servedBy: null };
}
