// Normalized content models + the unified provider interface.
//
// Every upstream source (MangaDex, AniList, …) is isolated behind an adapter
// that produces these shapes. Provider-specific parsing never leaks into React
// components — components only ever see Normalized* models or the UI-facing
// `Manga` type produced by normalize.ts.

import type { AdultContentMetadata, ContentOrigin } from "./adult";

/** Coarse content category. Kept in sync with the existing UI selector. */
export type Category = "manga" | "manhwa" | "manhua";

export const CATEGORY_LABEL: Record<Category, string> = {
  manga: "Manga",
  manhwa: "Manhwa",
  manhua: "Manhua",
};

/** Publication status as surfaced by providers, normalized to UI options. */
export type PublicationStatus = "Completed" | "In Process" | "Paused";

export interface NormalizedTitle {
  /** Globally-stable app id, e.g. "mangadex:<uuid>". Never fabricated. */
  id: string;
  /** Provider that produced this record. */
  provider: string;
  /** The provider's own identifier (used for follow-up provider calls). */
  providerId: string;
  /** Stable app slug used in URLs. Derived from id, safe to persist. */
  slug: string;
  title: string;
  alternativeTitles: string[];
  description: string | null;
  category: Category;
  isAdult: boolean;
  coverImage: string | null;
  /** Real provider rating (AniList averageScore 0..100, or null if unknown). */
  rating: number | null;
  /** Real popularity signal (AniList popularity / MangaDex follows), or null. */
  popularity: number | null;
  genres: string[];
  tags: string[];
  artists: string[];
  authors: string[];
  /** Best-effort language of available translations, or null if unknown. */
  language: string | null;
  status: PublicationStatus | null;
  /** ISO timestamp of the most recent update, or null if unknown. */
  updatedAt: string | null;
  /** ISO publication/release date, or null if unknown. */
  publishedAt: string | null;
  /** Link back to the provider page for attribution, or null. */
  providerUrl: string | null;
  /** Whether this provider can serve actual readable chapter pages. */
  readable: boolean;
  /**
   * Centralized adult classification (see adult.ts). Populated by every adapter
   * so the data pipeline can filter before results reach the UI. `origin` is the
   * manga/manhwa/manhua/doujinshi axis, separate from the age classification.
   */
  adult: AdultContentMetadata;
  /** Alternative-language / original-language titles, when the provider gives them. */
  originalLanguage?: string | null;
}

/* ------------------------------------------------------------------ */
/* Canonical series + chapter model (cross-provider)                  */
/* ------------------------------------------------------------------ */

/**
 * One canonical work that may exist on several providers. A canonical series is
 * the unit the catalogue stores and the UI links to; provider records are mapped
 * onto it. Stable even when the preferred provider changes.
 */
export interface CanonicalSeries {
  /** Stable app id, e.g. "series:<hash>". Derived from matched identities. */
  id: string;
  slug: string;
  title: string;
  alternativeTitles: string[];
  category: Category;
  origin: ContentOrigin;
  isAdult: boolean;
  adult: AdultContentMetadata;
  description: string | null;
  coverUrl: string | null;
  genres: string[];
  tags: string[];
  authors: string[];
  artists: string[];
  status: PublicationStatus | null;
  originalLanguage: string | null;
  availableLanguages: string[];
  releaseYear: number | null;
  rating: number | null;
  popularity: number | null;
  /** Every provider record confidently matched to this work. */
  providerMappings: ProviderSeriesMapping[];
  createdAt: string;
  updatedAt: string | null;
}

export interface ProviderSeriesMapping {
  providerId: string;
  providerSeriesId: string;
  sourceUrl: string | null;
  /** Which operations this provider can perform for THIS series. */
  capabilities: {
    search: boolean;
    metadata: boolean;
    chapters: boolean;
    reader: boolean;
  };
}

/** A single chapter in the unified catalogue, with all known source versions. */
export interface CanonicalChapter {
  /** Stable id, e.g. "series:<sid>:ch:<sortKey>". */
  id: string;
  seriesId: string;
  /** Parsed chapter number (decimal-aware), or null for specials. */
  chapterNumber: number | null;
  /** Original provider label, preserved verbatim. */
  label: string;
  volumeNumber: string | null;
  title: string | null;
  language: string;
  chapterType: ChapterType;
  /** Every eligible provider version of this chapter. */
  sourceVersions: ChapterSourceVersion[];
  /** Deterministic sort key used for stable ordering. */
  sortKey: number;
}

export type ChapterType =
  | "main"
  | "special"
  | "oneshot"
  | "prologue"
  | "epilogue"
  | "extra"
  | "side_story"
  | "unknown";

export interface ChapterSourceVersion {
  providerId: string;
  providerSeriesId: string;
  providerChapterId: string;
  chapterNumber: string | null;
  volumeNumber: string | null;
  title: string | null;
  language: string;
  releaseGroup: string | null;
  sourceUrl: string | null;
  /** Whether we can actually load page images from this version. */
  pageAccessCapability: "available" | "link_out_only" | "metadata_only" | "unavailable";
  pageCount: number | null;
  publishedAt: string | null;
}

export interface NormalizedChapter {
  /** Globally-stable app id, e.g. "mangadex:<chapter-uuid>". */
  id: string;
  titleId: string;
  provider: string;
  providerChapterId: string;
  chapterNumber: string | null;
  chapterTitle: string | null;
  language: string | null;
  publishedAt: string | null;
  pageCount: number | null;
  /** True only when getChapterPages() is actually supported for this source. */
  readable: boolean;
}

export interface NormalizedPage {
  index: number;
  imageUrl: string;
  width?: number;
  height?: number;
  /** Optional expiry for signed/expiring image URLs. */
  expiresAt?: string | null;
}

/** One title's latest chapter drop — used by "Latest updates" listings. */
export interface NormalizedUpdate {
  title: NormalizedTitle;
  chapter: NormalizedChapter;
}

export interface SearchOptions {
  query?: string;
  limit?: number;
  offset?: number;
  categories?: Category[];
  genres?: string[];
  status?: PublicationStatus | null;
  isAdult?: boolean;
  language?: string | null;
  order?: "latest" | "popular" | "rating" | "relevance";
}

export interface ChapterOptions {
  language?: string | null;
  limit?: number;
  offset?: number;
  order?: "asc" | "desc";
}

export interface TrendingOptions {
  window?: "daily" | "weekly" | "monthly" | "all";
  limit?: number;
  categories?: Category[];
  isAdult?: boolean;
}

export interface UpdateOptions {
  limit?: number;
  categories?: Category[];
  isAdult?: boolean;
  language?: string | null;
}

/** Explicit capability declaration — unsupported ops are surfaced, not faked. */
export interface ProviderCapabilities {
  search: boolean;
  getTitle: boolean;
  getChapters: boolean;
  getChapterPages: boolean;
  trending: boolean;
  latestUpdates: boolean;
  /** Real provider ratings available (vs. only local user votes). */
  ratings: boolean;
}

export type ProviderStatus =
  | "VERIFIED_AND_AVAILABLE"
  | "AUTHORIZED_WITH_RESTRICTIONS"
  | "METADATA_ONLY"
  | "SELF_HOST_REQUIRED"
  | "UNAVAILABLE"
  | "NOT_AUTHORIZED_FOR_INTENDED_USE"
  | "DISABLED";

export interface ProviderInfo {
  id: string;
  name: string;
  /** Human-readable origin, e.g. "https://api.mangadex.org". */
  baseUrl: string;
  status: ProviderStatus;
  /** Attribution / terms note surfaced for compliance. */
  attribution?: string;
  capabilities: ProviderCapabilities;
  /** True when this adapter also serves adult/doujinshi content. */
  adult: boolean;
}

/** Thrown by adapters so the aggregator can fail over per-provider. */
export class ProviderError extends Error {
  constructor(
    public readonly providerId: string,
    message: string,
    public readonly kind: "timeout" | "rate_limited" | "network" | "http" | "parse" | "unsupported" = "network",
    public readonly retryable = true,
  ) {
    super(`[${providerId}] ${message}`);
    this.name = "ProviderError";
  }
}

/** The single interface every content source must implement. */
export interface ContentProvider {
  getProviderInfo(): ProviderInfo;

  searchTitles(query: string, options?: SearchOptions): Promise<NormalizedTitle[]>;

  getTitle(providerId: string): Promise<NormalizedTitle | null>;

  getChapters(providerId: string, options?: ChapterOptions): Promise<NormalizedChapter[]>;

  getChapterPages(providerId: string, chapterId: string): Promise<NormalizedPage[]>;

  getTrending?(options?: TrendingOptions): Promise<NormalizedTitle[]>;

  getLatestUpdates?(options?: UpdateOptions): Promise<NormalizedUpdate[]>;
}
