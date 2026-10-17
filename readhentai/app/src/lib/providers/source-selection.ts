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

import type { CanonicalChapter, ChapterSourceVersion } from "./types";

/* ------------------------------------------------------------------ */
/* Provider health / performance observations                          */
/* ------------------------------------------------------------------ */

export interface ProviderObservation {
  success: number;
  failure: number;
  /** Rolling average latency in ms, NaN until first sample. */
  latencyMs: number;
  lastSuccessAt: number | null;
  lastFailureAt: number | null;
}

/** In-memory rolling observations, updated from real request outcomes. */
const observations = new Map<string, ProviderObservation>();

/** Minimum samples before latency/reliability are trusted. */
const MIN_SAMPLES = 3;

export function recordSuccess(providerId: string, latencyMs: number): void {
  const o = ensure(providerId);
  o.success++;
  o.latencyMs = Number.isFinite(o.latencyMs)
    ? o.latencyMs * 0.7 + latencyMs * 0.3 // EWMA
    : latencyMs;
  o.lastSuccessAt = Date.now();
}

export function recordFailure(providerId: string): void {
  const o = ensure(providerId);
  o.failure++;
  o.lastFailureAt = Date.now();
}

export function getObservation(providerId: string): ProviderObservation | undefined {
  return observations.get(providerId);
}

/** Test hook: reset all observations. */
export function resetObservations(): void {
  observations.clear();
}

function ensure(id: string): ProviderObservation {
  let o = observations.get(id);
  if (!o) {
    o = { success: 0, failure: 0, latencyMs: NaN, lastSuccessAt: null, lastFailureAt: null };
    observations.set(id, o);
  }
  return o;
}

/* ------------------------------------------------------------------ */
/* Scoring                                                             */
/* ------------------------------------------------------------------ */

/** Configurable weights (sum = 1.0). Initial values, not mandatory. */
export const SCORE_WEIGHTS = {
  completeness: 0.3,
  languageMatch: 0.2,
  availability: 0.2,
  reliability: 0.15,
  latency: 0.1,
  freshness: 0.05,
} as const;

export interface ScoreContext {
  /** User's preferred language, e.g. "en". */
  preferredLanguage?: string;
  /** Reference timestamp for freshness (epoch ms). */
  now?: number;
  /** Whether the operation requires readable pages. */
  needsPages?: boolean;
}

/**
 * Eligibility filter. Returns the subset of versions that MAY serve the request.
 * A version is ineligible if it cannot provide the required capability, is in a
 * disallowed language (when a preference exists), or is marked unavailable.
 */
export function eligibleVersions(
  versions: ChapterSourceVersion[],
  ctx: ScoreContext = {},
): ChapterSourceVersion[] {
  return versions.filter((v) => {
    if (v.pageAccessCapability === "unavailable") return false;
    if (ctx.needsPages && v.pageAccessCapability !== "available") return false;
    if (ctx.preferredLanguage && v.language !== "und" && v.language !== ctx.preferredLanguage) {
      return false;
    }
    return true;
  });
}

/** Reliability 0..1 from rolling observations (neutral 0.5 when unknown). */
function reliabilityScore(providerId: string): number {
  const o = observations.get(providerId);
  if (!o) return 0.5;
  const total = o.success + o.failure;
  if (total < MIN_SAMPLES) return 0.5; // not enough evidence — stay neutral
  return o.success / total;
}

/** Latency 0..1 where lower ms scores HIGHER (0..cap scaled). Neutral 0.5 unknown. */
function latencyScore(providerId: string): number {
  const o = observations.get(providerId);
  if (!o || !Number.isFinite(o.latencyMs) || o.success < MIN_SAMPLES) return 0.5;
  // Map [0, 2000ms] -> [1, 0], clamped. 2s is a reasonable "slow" ceiling.
  const clamped = Math.min(Math.max(o.latencyMs, 0), 2000);
  return 1 - clamped / 2000;
}

/** Availability 0..1: readable pages > link-out > metadata-only. */
function availabilityScore(v: ChapterSourceVersion): number {
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
function freshnessScore(v: ChapterSourceVersion, now: number): number {
  if (!v.publishedAt) return 0.5;
  const t = Date.parse(v.publishedAt);
  if (!Number.isFinite(t)) return 0.5;
  const ageDays = Math.max(0, (now - t) / 86_400_000);
  // 30+ days old -> 0; published today -> 1.
  return Math.max(0, 1 - ageDays / 30);
}

/** Language match 0..1 (exact 1, unknown 0.5, mismatch 0). */
function languageScore(v: ChapterSourceVersion, preferred?: string): number {
  if (!preferred) return 0.5;
  if (v.language === "und") return 0.5;
  return v.language === preferred ? 1 : 0;
}

/**
 * Completeness proxy 0..1: a version that reports a page count and a number is
 * more likely to be a complete, well-formed chapter than one reporting neither.
 * (Provider-level completeness across the whole series is handled by merging.)
 */
function completenessScore(v: ChapterSourceVersion): number {
  let s = 0.5;
  if (v.pageCount && v.pageCount > 0) s += 0.3;
  if (v.chapterNumber !== null && v.chapterNumber !== undefined) s += 0.2;
  return Math.min(1, s);
}

/** Aggregate weighted score for one version, 0..1. */
export function scoreVersion(
  v: ChapterSourceVersion,
  ctx: ScoreContext = {},
): number {
  const now = ctx.now ?? Date.now();
  return (
    SCORE_WEIGHTS.completeness * completenessScore(v) +
    SCORE_WEIGHTS.languageMatch * languageScore(v, ctx.preferredLanguage) +
    SCORE_WEIGHTS.availability * availabilityScore(v) +
    SCORE_WEIGHTS.reliability * reliabilityScore(v.providerId) +
    SCORE_WEIGHTS.latency * latencyScore(v.providerId) +
    SCORE_WEIGHTS.freshness * freshnessScore(v, now)
  );
}

export interface RankedVersion {
  version: ChapterSourceVersion;
  score: number;
  eligible: boolean;
  reason?: string;
}

/** Rank every version of a chapter; ineligible versions are kept but flagged. */
export function rankVersions(
  chapter: CanonicalChapter,
  ctx: ScoreContext = {},
): RankedVersion[] {
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

function ineligibleReason(v: ChapterSourceVersion, ctx: ScoreContext): string {
  if (v.pageAccessCapability === "unavailable") return "source unavailable";
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
export function selectBestVersion(
  chapter: CanonicalChapter,
  ctx: ScoreContext = {},
): ChapterSourceVersion | null {
  const ranked = rankVersions(chapter, ctx)
    .filter((r) => r.eligible)
    .sort((a, b) => b.score - a.score);
  return ranked[0]?.version ?? null;
}

/* ------------------------------------------------------------------ */
/* Chapter-level fallback                                              */
/* ------------------------------------------------------------------ */

export interface FallbackAttempt {
  providerId: string;
  providerChapterId: string;
  ok: boolean;
  error?: string;
}

export interface FallbackResult<T> {
  value: T | null;
  attempts: FallbackAttempt[];
  /** The providerId that ultimately served the result, if any. */
  servedBy: string | null;
}

export interface FallbackOptions {
  ctx?: ScoreContext;
  /** Hard cap on attempts (default 3). Bounds retries — never infinite. */
  maxAttempts?: number;
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
export async function resolveWithFallback<T>(
  chapter: CanonicalChapter,
  load: (version: ChapterSourceVersion) => Promise<T>,
  opts: FallbackOptions = {},
): Promise<FallbackResult<T>> {
  const ctx = opts.ctx ?? {};
  const max = opts.maxAttempts ?? 3;

  const candidates = rankVersions(chapter, ctx)
    .filter((r) => r.eligible)
    .sort((a, b) => b.score - a.score)
    .slice(0, max);

  const attempts: FallbackAttempt[] = [];

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
    } catch (err) {
      const message = (err as Error)?.message ?? "failed";
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
