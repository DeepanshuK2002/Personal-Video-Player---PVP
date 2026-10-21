/**
 * Manhwa Canonical Identity Resolution
 *
 * This module implements reliable matching of Manhwa records across providers.
 * It builds on the existing series-matching module with Manhwa-specific enhancements.
 */

import {
  type NormalizedTitle,
  type CanonicalSeries,
  type Category,
  type PublicationStatus,
} from "./types";
import {
  normalizeTitleForMatch,
  tokenSimilarity,
  groupIntoCanonicalSeries,
} from "./series-matching";

/* ------------------------------------------------------------------ */
/* Manhwa-Specific Configuration                                       */
/* ------------------------------------------------------------------ */

export const MANHWA_MATCH_THRESHOLD = 0.75;

export const MANHWA_SIGNAL_WEIGHTS = {
  titleExact: 0.30,
  titleFuzzy: 0.20,
  altTitleMatch: 0.15,
  authorMatch: 0.15,
  coverSimilarity: 0.10,
  metadataConsistency: 0.10,
};

/* ------------------------------------------------------------------ */
/* Normalization Helpers                                               */
/* ------------------------------------------------------------------ */

function normalizeAuthor(name: string): string {
  return name.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim();
}

function levenshteinDistance(a: string, b: string): number {
  if (a.length === 0) return b.length;
  if (b.length === 0) return a.length;
  const m = Array.from({ length: a.length + 1 }, () => Array(b.length + 1).fill(0));
  for (let i = 0; i <= a.length; i++) m[i][0] = i;
  for (let j = 0; j <= b.length; j++) m[0][j] = j;
  for (let i = 1; i <= a.length; i++) {
    for (let j = 1; j <= b.length; j++) {
      m[i][j] = a[i-1] === b[j-1] ? m[i-1][j-1] : Math.min(m[i-1][j]+1, m[i][j-1]+1, m[i-1][j-1]+1);
    }
  }
  return m[a.length][b.length];
}

/* ------------------------------------------------------------------ */
/* Signal Calculations                                                 */
/* ------------------------------------------------------------------ */

function calcTitleExactScore(t1: NormalizedTitle, t2: NormalizedTitle): number {
  const n1 = t1.title?.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim() ?? "";
  const n2 = t2.title?.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim() ?? "";
  return n1 === n2 ? 1 : 0;
}

function calcTitleFuzzyScore(t1: NormalizedTitle, t2: NormalizedTitle): number {
  const a = t1.title?.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim() ?? "";
  const b = t2.title?.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim() ?? "";
  if (!a || !b) return 0;
  const d = levenshteinDistance(a, b);
  return Math.max(0, 1 - d / Math.max(a.length, b.length));
}

function calcAltTitleScore(alt1: string[], alt2: string[]): number {
  const s1 = new Set(alt1.map(x => x.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim()).filter(Boolean));
  const s2 = new Set(alt2.map(x => x.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim()).filter(Boolean));
  if (!s1.size && !s2.size) return 0;
  if (!s1.size || !s2.size) return 0;
  let m = 0; for (const t of s1) if (s2.has(t)) m++;
  return m / Math.max(s1.size, s2.size);
}

function calcAuthorScore(a1: string[], ar1: string[], a2: string[], ar2: string[]): number {
  const s1 = new Set([...a1, ...ar1].map(x => x.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim()).filter(Boolean));
  const s2 = new Set([...a2, ...ar2].map(x => x.toLowerCase().replace(/[^\p{L}\p{N}\s]/gu, " ").replace(/\s+/g, " ").trim()).filter(Boolean));
  if (!s1.size && !s2.size) return 0;
  if (!s1.size || !s2.size) return 0;
  let m = 0; for (const x of s1) if (s2.has(x)) m++;
  return m / Math.max(s1.size, s2.size);
}

function calcCoverScore(c1: string | null, c2: string | null): number {
  return c1 && c2 && c1 === c2 ? 1 : 0;
}

function calcMetadataScore(t1: NormalizedTitle, t2: NormalizedTitle): number {
  let s = 0, f = 0;
  if (t1.publishedAt && t2.publishedAt) {
    const y1 = parseInt(t1.publishedAt.slice(0,4),10), y2 = parseInt(t2.publishedAt.slice(0,4),10);
    if (!isNaN(y1) && !isNaN(y2) && y1===y2) s++; f++;
  }
  if (t1.status && t2.status && t1.status===t2.status) { s++; f++; }
  if (t1.category && t2.category && t1.category===t2.category) { s++; f++; }
  return f ? s/f : 0;
}

/* ------------------------------------------------------------------ */
/* Main Matching Function                                              */
/* ------------------------------------------------------------------ */

export interface ManhwaMatchResult {
  score: number;
  matched: boolean;
  signals: {
    titleExact: number; titleFuzzy: number; altTitle: number;
    author: number; cover: number; metadata: number;
  };
}

export function calculateManhwaMatchConfidence(t1: NormalizedTitle, t2: NormalizedTitle) {
  const signals = {
    titleExact: calcTitleExactScore(t1, t2),
    titleFuzzy: calcTitleFuzzyScore(t1, t2),
    altTitle: calcAltTitleScore(t1.alternativeTitles, t2.alternativeTitles),
    author: calcAuthorScore(t1.authors, t1.artists, t2.authors, t2.artists),
    cover: calcCoverScore(t1.coverImage, t2.coverImage),
    metadata: calcMetadataScore(t1, t2),
  };
  const score = signals.titleExact * 0.30 + signals.titleFuzzy * 0.20 +
    signals.altTitle * 0.15 + signals.author * 0.15 +
    signals.cover * 0.10 + signals.metadata * 0.10;
  return { score, matched: score >= 0.75, signals };
}

/* ------------------------------------------------------------------ */
/* Canonical Series Building                                           */
/* ------------------------------------------------------------------ */

export function clusterManhwaIntoCanonicalSeries(titles: NormalizedTitle[]): import("./types").CanonicalSeries[] {
  const manhwaTitles = titles.filter(t => t.category === "manhwa");
  return groupIntoCanonicalSeries(manhwaTitles) as import("./types").CanonicalSeries[];
}

export function mergeManhwaRecords(clusters: import("./types").CanonicalSeries[]): import("./types").CanonicalSeries[] {
  return clusters.map(enhanceCanonicalSeries);
}

function enhanceCanonicalSeries(c: import("./types").CanonicalSeries): import("./types").CanonicalSeries {
  if (c.category !== "manhwa") return { ...c, category: "manhwa" };
  return c;
}

/* ------------------------------------------------------------------ */
/* Cross-Provider Identity Utilities                                   */
/* ------------------------------------------------------------------ */

export function findMatchingManhwaProviders(
  canonical: import("./types").CanonicalSeries,
  allTitles: NormalizedTitle[],
  threshold = 0.75
): NormalizedTitle[] {
  const canonicalAsTitle: NormalizedTitle = {
    id: canonical.id, provider: "", providerId: "", slug: canonical.slug,
    title: canonical.title, alternativeTitles: canonical.alternativeTitles,
    description: canonical.description, category: canonical.category,
    isAdult: canonical.isAdult, coverImage: canonical.coverUrl,
    rating: canonical.rating, popularity: canonical.popularity,
    genres: canonical.genres, tags: canonical.tags,
    artists: canonical.artists, authors: canonical.authors,
    language: canonical.originalLanguage, status: canonical.status,
    updatedAt: canonical.updatedAt,
    publishedAt: canonical.releaseYear ? `${canonical.releaseYear}-01-01` : null,
    providerUrl: canonical.providerMappings[0]?.sourceUrl ?? null,
    readable: false, adult: canonical.adult,
    originalLanguage: canonical.originalLanguage, colored: false,
  };
  return allTitles.filter(t => {
    const m = calculateManhwaMatchConfidence(canonicalAsTitle, t);
    return m.matched && m.score >= threshold;
  });
}