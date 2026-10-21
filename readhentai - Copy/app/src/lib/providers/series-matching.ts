// Canonical series matching — cross-provider duplicate detection.
//
// One real comic may appear on several providers. This module decides whether
// two provider records refer to the SAME work and, when confident, groups them
// into one CanonicalSeries (preserving every provider mapping). When confidence
// is insufficient the records are kept SEPARATE — a false merge is worse than a
// duplicate entry.
//
// Matching uses corroborated identity, never approximate title similarity alone:
//   - normalized exact title (or any alternative title on either side)
//   - token-overlap similarity as a weaker signal
//   - shared author/artist, same release year, same category as corroboration
//   - conflicting authors as a strong disqualifier
//
// There are no shared external IDs across MangaDex/Dynasty/AniList here, so the
// bar is deliberately high and fully covered by mocked unit tests.

import { DEFAULT_ADULT_POLICY, isEligible, type AdultClassification, type AdultContentMetadata, type AdultPolicy } from "./adult";
import type { CanonicalSeries, Category, NormalizedTitle, ProviderSeriesMapping } from "./types";

/* ------------------------------------------------------------------ */
/* Title normalization + similarity                                    */
/* ------------------------------------------------------------------ */

/** Lowercase, strip punctuation/diacritics, collapse whitespace. */
export function normalizeTitleForMatch(title: string): string {
  return (title ?? "")
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "") // strip combining diacritics
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

/** Significant tokens for overlap (drop very common filler words). */
const FILLER = new Set(["the", "a", "an", "of", "and", "to", "in", "on", "no"]);
function tokens(title: string): Set<string> {
  return new Set(
    normalizeTitleForMatch(title)
      .split(" ")
      .filter((w) => w.length > 1 && !FILLER.has(w)),
  );
}

/** Jaccard similarity over significant tokens, 0..1. */
export function tokenSimilarity(a: string, b: string): number {
  const ta = tokens(a);
  const tb = tokens(b);
  if (ta.size === 0 || tb.size === 0) return 0;
  let inter = 0;
  for (const t of ta) if (tb.has(t)) inter++;
  const union = ta.size + tb.size - inter;
  return union === 0 ? 0 : inter / union;
}

/* ------------------------------------------------------------------ */
/* Confidence scoring                                                  */
/* ------------------------------------------------------------------ */

export interface MatchResult {
  /** 0..1 confidence that the two records are the same work. */
  score: number;
  /** Human-readable signals that contributed (for diagnostics/tests). */
  reasons: string[];
}

const MATCH_THRESHOLD = 0.65;

/** All titles that can act as an identity key for a record. */
function identitySet(t: NormalizedTitle): Set<string> {
  const s = new Set<string>();
  const main = normalizeTitleForMatch(t.title);
  if (main) s.add(main);
  for (const alt of t.alternativeTitles ?? []) {
    const n = normalizeTitleForMatch(alt);
    if (n) s.add(n);
  }
  return s;
}

function overlap(a: Set<string>, b: Set<string>): boolean {
  for (const x of a) if (b.has(x)) return true;
  return false;
}

/**
 * Confidence that two provider records describe the same work, 0..1.
 * Additive signals, capped at 1, with author conflict as a hard penalty.
 */
export function seriesMatchConfidence(a: NormalizedTitle, b: NormalizedTitle): MatchResult {
  let score = 0;
  const reasons: string[] = [];

  // 1. Exact identity match (main or any alternative title) — strongest signal.
  const idA = identitySet(a);
  const idB = identitySet(b);
  if (overlap(idA, idB)) {
    score += 0.6;
    reasons.push("exact title/alt-title match");
  } else {
    // 2. Token-overlap similarity as a weaker, graded signal.
    const sim = tokenSimilarity(a.title, b.title);
    if (sim >= 0.8) {
      score += 0.45;
      reasons.push(`high title similarity ${sim.toFixed(2)}`);
    } else if (sim >= 0.5) {
      score += 0.3;
      reasons.push(`moderate title similarity ${sim.toFixed(2)}`);
    } else {
      reasons.push(`low title similarity ${sim.toFixed(2)}`);
    }
  }

  // 3. Corroborating metadata.
  const authorsA = new Set((a.authors ?? []).map((x) => x.toLowerCase().trim()));
  const authorsB = new Set((b.authors ?? []).map((x) => x.toLowerCase().trim()));
  const knownA = [...authorsA].filter(Boolean);
  const knownB = [...authorsB].filter(Boolean);

  if (knownA.length && knownB.length) {
    const shared = knownA.some((x) => authorsB.has(x));
    if (shared) {
      score += 0.25;
      reasons.push("shared author/artist");
    } else {
      // Disjoint known authors strongly indicate different works.
      score -= 0.4;
      reasons.push("conflicting authors");
    }
  }

  if (a.publishedAt && b.publishedAt && a.publishedAt === b.publishedAt) {
    score += 0.1;
    reasons.push("same release year");
  }

  if (a.category === b.category) {
    score += 0.05;
    reasons.push("same category");
  }

  return { score: Math.max(0, Math.min(1, score)), reasons };
}

/** Boolean decision at the default threshold (0.65). */
export function areSameSeries(
  a: NormalizedTitle,
  b: NormalizedTitle,
  threshold = MATCH_THRESHOLD,
): boolean {
  return seriesMatchConfidence(a, b).score >= threshold;
}

export { MATCH_THRESHOLD };

/* ------------------------------------------------------------------ */
/* Adult-signal combination across matched records                     */
/* ------------------------------------------------------------------ */

const ADULT_RANK: Record<AdultClassification, number> = {
  confirmed_adult: 3,
  mature_non_explicit: 2,
  general_audience: 1,
  unknown: 0,
};

/**
 * Combine adult classifications from several provider records for the SAME
 * canonical series.
 *
 * Policy: explicit adult/mature evidence from ANY integrated provider is
 * honored (an explicit `pornographic`/`isAdult` flag is specific positive
 * evidence). A series is only classified general_audience when NO provider
 * reports adult/mature evidence, and `unknown` only when nothing is known.
 * This never invents adult status — it only trusts a provider's own explicit
 * flag — and keeps the age classification separate from origin category.
 */
export function combineAdultSignals(
  records: AdultContentMetadata[],
): AdultContentMetadata {
  if (records.length === 0) {
    return {
      classification: "unknown",
      isAdult: false,
      isExplicit: false,
      origin: "other",
      sourceProvider: "aggregate",
      reason: "no provider records",
    };
  }

  // Highest positive evidence wins (confirmed_adult > mature > general > unknown).
  let best = records[0];
  for (const r of records) {
    if (ADULT_RANK[r.classification] > ADULT_RANK[best.classification]) best = r;
  }

  // Preserve origin from the first record that isn't "other".
  const origin = records.find((r) => r.origin && r.origin !== "other")?.origin ?? best.origin;

  return {
    ...best,
    origin,
    isAdult: best.classification === "confirmed_adult",
    isExplicit: best.classification === "confirmed_adult",
    sourceProvider: records.map((r) => r.sourceProvider).join("+"),
    reason: `combined from ${records.length} record(s); strongest=${best.classification}`,
  };
}

/* ------------------------------------------------------------------ */
/* Grouping into canonical series                                      */
/* ------------------------------------------------------------------ */

function slugify(title: string): string {
  return normalizeTitleForMatch(title).replace(/\s+/g, "-").slice(0, 80) || "untitled";
}

/**
 * Group provider titles into canonical series using confident matches.
 * Titles that don't confidently match anything become single-provider series.
 * Adult eligibility is applied so an ineligible record can never seed a series
 * that then leaks into the catalogue.
 */
export function groupIntoCanonicalSeries(
  titles: NormalizedTitle[],
  policy: AdultPolicy = DEFAULT_ADULT_POLICY,
): CanonicalSeries[] {
  // Drop records that cannot enter the adult catalogue before grouping.
  const eligible = titles.filter((t) => isEligible(t.adult.classification, policy));

  const used = new Array<boolean>(eligible.length).fill(false);
  const series: CanonicalSeries[] = [];
  const now = new Date().toISOString();

  for (let i = 0; i < eligible.length; i++) {
    if (used[i]) continue;
    const members: NormalizedTitle[] = [eligible[i]];
    used[i] = true;

    // Greedily attach any later record that confidently matches a current member.
    for (let j = i + 1; j < eligible.length; j++) {
      if (used[j]) continue;
      const matchesMember = members.some((m) => areSameSeries(m, eligible[j]));
      if (matchesMember) {
        members.push(eligible[j]);
        used[j] = true;
      }
    }

    const primary = members[0];
    const adult = combineAdultSignals(members.map((m) => m.adult));

    const providerMappings: ProviderSeriesMapping[] = members.map((m) => ({
      providerId: m.provider,
      providerSeriesId: m.providerId,
      sourceUrl: m.providerUrl,
      capabilities: {
        search: true,
        metadata: true,
        chapters: false, // refined per-provider by the caller when known
        reader: m.readable,
      },
    }));

    series.push({
      id: `series:${slugify(primary.title)}`,
      slug: slugify(primary.title),
      title: primary.title,
      alternativeTitles: [
        ...new Set(members.flatMap((m) => m.alternativeTitles ?? [])),
      ].filter((t) => t !== primary.title),
      category: primary.category as Category,
      origin: adult.origin,
      isAdult: adult.isAdult,
      adult,
      description: primary.description ?? members.find((m) => m.description)?.description ?? null,
      coverUrl: primary.coverImage ?? members.find((m) => m.coverImage)?.coverImage ?? null,
      genres: [...new Set(members.flatMap((m) => m.genres ?? []))],
      tags: [...new Set(members.flatMap((m) => m.tags ?? []))],
      authors: [...new Set(members.flatMap((m) => m.authors ?? []))],
      artists: [...new Set(members.flatMap((m) => m.artists ?? []))],
      status: primary.status ?? members.find((m) => m.status)?.status ?? null,
      originalLanguage: primary.originalLanguage ?? null,
      availableLanguages: [...new Set(members.map((m) => m.language).filter((l): l is string => Boolean(l)))],
      releaseYear: primary.publishedAt ? Number(primary.publishedAt) : null,
      rating: primary.rating ?? members.find((m) => m.rating != null)?.rating ?? null,
      popularity: primary.popularity ?? members.find((m) => m.popularity != null)?.popularity ?? null,
      providerMappings,
      createdAt: now,
      updatedAt: null,
    });
  }

  return series;
}
