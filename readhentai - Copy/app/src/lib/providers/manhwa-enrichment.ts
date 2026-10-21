/**
 * Manhwa Field-Level Metadata Enrichment Engine
 *
 * This module implements the field-level enrichment logic described in the spec.
 * For each field of a canonical Manhwa record, it queries providers in priority
 * order until a valid value is found or all eligible sources are exhausted.
 */

import {
  type NormalizedTitle,
  type CanonicalSeries,
  type ProviderCapabilities,
  type ProviderInfo,
} from "./types";
import { MANHWA_SOURCES, getManhwaSource, getEnabledManhwaSources } from "./manhwa-sources";
import { manhwaRegistry, getManhwaProvider, healthyManhwaProviders, manhwaPriorityScore } from "./manhwa-registry";
import { calculateManhwaMatchConfidence } from "./manhwa-identity";

/* ------------------------------------------------------------------ */
/* Types                                                               */
/* ------------------------------------------------------------------ */

export interface EnrichmentResult<T> {
  value: T | null;
  sourceProviderId: string | null;
  confidence: number; // 0-1, based on provider priority and data quality
  timestamp: string;
}

export interface EnrichedCanonicalSeries {
  canonical: import("./types").CanonicalSeries;
  fieldSources: Map<string, EnrichmentResult<unknown>>;
  lastEnriched: string;
  completeness: number; // 0-1, fraction of fields populated
}

export interface EnrichmentPolicy {
  /** Minimum confidence threshold for accepting a value (0-1). */
  minConfidence: number;
  /** Whether to overwrite existing values with higher-priority sources. */
  allowOverwrite: boolean;
  /** Fields that should never be overwritten once set. */
  immutableFields: string[];
  /** Maximum number of providers to query per field. */
  maxProvidersPerField: number;
}

/** Default enrichment policy. */
export const DEFAULT_ENRICHMENT_POLICY: EnrichmentPolicy = {
  minConfidence: 0.3,
  allowOverwrite: true,
  immutableFields: ["id", "slug", "providerMappings"],
  maxProvidersPerField: 5,
};

/* ------------------------------------------------------------------ */
/* Field Definitions                                                   */
/* ------------------------------------------------------------------ */

export type CanonicalSeriesField =
  | "title"
  | "alternativeTitles"
  | "description"
  | "coverUrl"
  | "genres"
  | "tags"
  | "authors"
  | "artists"
  | "status"
  | "originalLanguage"
  | "availableLanguages"
  | "releaseYear"
  | "rating"
  | "popularity"
  | "adult"
  | "coverUrl"
  | "category"
  | "origin"
  | "isAdult"
  | "providerMappings";

/**
 * Field extraction functions - extract a field from a provider's NormalizedTitle.
 * Returns null if the field is not available or invalid.
 */
const FIELD_EXTRACTORS: Record<string, (title: NormalizedTitle) => unknown | null> = {
  title: (t) => t.title || null,
  alternativeTitles: (t) => t.alternativeTitles?.length ? [...t.alternativeTitles] : null,
  description: (t) => t.description || null,
genres: (t) => t.genres?.length ? [...t.genres] : null,
    tags: (t) => t.tags?.length ? [...t.tags] : null,
    authors: (t) => t.authors?.length ? [...t.authors] : null,
    artists: (t) => t.artists?.length ? [...t.artists] : null,
    status: (t) => t.status || null,
    originalLanguage: (t) => t.language || null,
    availableLanguages: (t) => t.language ? [t.language] : null,
    releaseYear: (t) => t.publishedAt ? parseInt(t.publishedAt.slice(0, 4), 10) || null : null,
    rating: (t) => t.rating !== null && t.rating !== undefined ? t.rating : null,
    popularity: (t) => t.popularity !== null && t.popularity !== undefined ? t.popularity : null,
    adult: (t) => t.adult || null,
    coverUrl: (t) => t.coverImage || null,
    category: (t) => t.category || null,
    origin: (t) => t.adult?.origin || null,
    isAdult: (t) => t.isAdult,
    // providerMappings is handled separately
};

/**
 * Field validators - check if a value is valid for a given field.
 */
const FIELD_VALIDATORS: Record<string, (value: unknown) => boolean> = {
  title: (v) => typeof v === "string" && v.trim().length > 0,
  alternativeTitles: (v) => Array.isArray(v) && v.every(x => typeof x === "string" && x.trim().length > 0),
  description: (v) => typeof v === "string" && v.trim().length > 0,
  coverUrl: (v) => typeof v === "string" && v.trim().length > 0,
  genres: (v) => Array.isArray(v) && v.every(x => typeof x === "string" && x.trim().length > 0),
  tags: (v) => Array.isArray(v) && v.every(x => typeof x === "string" && x.trim().length > 0),
  authors: (v) => Array.isArray(v) && v.every(x => typeof x === "string" && x.trim().length > 0),
  artists: (v) => Array.isArray(v) && v.every(x => typeof x === "string" && x.trim().length > 0),
  status: (v) => typeof v === "string" && v.trim().length > 0,
  originalLanguage: (v) => typeof v === "string" && v.trim().length > 0,
  availableLanguages: (v) => Array.isArray(v) && v.every(x => typeof x === "string" && x.trim().length > 0),
  releaseYear: (v) => typeof v === "number" && !isNaN(v) && v > 1900 && v <= new Date().getFullYear() + 1,
  rating: (v) => typeof v === "number" && !isNaN(v) && v >= 0 && v <= 10,
  popularity: (v) => typeof v === "number" && !isNaN(v) && v >= 0,
  adult: (v) => v !== null && typeof v === "object",
  category: (v) => typeof v === "string" && ["manga", "manhwa", "manhua"].includes(v),
  origin: (v) => typeof v === "string" && ["manga", "manhwa", "manhua", "doujinshi", "other"].includes(v),
  isAdult: (v) => typeof v === "boolean",
};

/* ------------------------------------------------------------------ */
/* Enrichment Engine                                                   */
/* ------------------------------------------------------------------ */

/**
 * Get provider IDs in priority order for enrichment.
 * Only includes enabled, healthy providers that support the required capability.
 */
function getEnrichmentProviders(capability: keyof import("./types").ProviderCapabilities): string[] {
  const providers = healthyManhwaProviders()
    .filter(p => p.getProviderInfo().capabilities[capability])
    .sort((a, b) => manhwaPriorityScore(b.getProviderInfo().id) - manhwaPriorityScore(a.getProviderInfo().id));
  return providers.map(p => p.getProviderInfo().id);
}

/**
 * Get a field value from a provider's title record.
 */
function extractFieldFromTitle(providerId: string, title: NormalizedTitle, field: string): unknown | null {
  const extractor = FIELD_EXTRACTORS[field];
  if (!extractor) return null;
  return extractor(title);
}

/**
 * Validate a field value.
 */
function validateField(field: string, value: unknown): boolean {
  const validator = FIELD_VALIDATORS[field];
  if (!validator) return true; // No validator = accept any value
  return validator(value);
}

/**
 * Calculate confidence score for a field value from a specific provider.
 */
function calculateFieldConfidence(providerId: string, field: string, value: unknown): number {
  // Base confidence from provider priority
  const source = getManhwaSource(providerId);
  let priorityScore = 0.5;
  if (source && source.enabled) {
    priorityScore = 1.0 - (source.priority - 1) / 16;
  }

  // Quality adjustments based on field type
  let qualityScore = 1.0;
  if (field === "coverUrl" && typeof value === "string") {
    // Prefer HTTPS, valid image extensions
    if (value.startsWith("https://") && /\.(jpg|jpeg|png|webp)($|\?)/i.test(value)) qualityScore = 1.0;
    else if (value.startsWith("http://")) qualityScore = 0.7;
    else qualityScore = 0.5;
  }
  if (field === "description" && typeof value === "string") {
    // Prefer longer, more detailed descriptions
    if (value.length > 500) qualityScore = 1.0;
    else if (value.length > 200) qualityScore = 0.9;
    else if (value.length > 50) qualityScore = 0.7;
    else qualityScore = 0.5;
  }
  if (["genres", "tags"].includes(field) && Array.isArray(value)) {
    // More tags = more complete
    if (value.length >= 5) qualityScore = 1.0;
    else if (value.length >= 3) qualityScore = 0.8;
    else if (value.length >= 1) qualityScore = 0.6;
    else qualityScore = 0.3;
  }

  return priorityScore * 0.7 + qualityScore * 0.3;
}

/* ------------------------------------------------------------------ */
/* Main Enrichment Functions                                           */
/* ------------------------------------------------------------------ */

export interface EnrichmentOptions {
  policy?: Partial<EnrichmentPolicy>;
  targetFields?: string[];
  /** Provider IDs to prioritize (overrides priority order). */
  preferredProviders?: string[];
  /** Callback for progress reporting. */
  onProgress?: (field: string, providerId: string, result: EnrichmentResult<unknown>) => void;
}

/**
 * Enrich a single field of a canonical series by querying providers in priority order.
 */
export async function enrichCanonicalField(
  canonical: import("./types").CanonicalSeries,
  field: string,
  options: EnrichmentOptions = {}
): Promise<EnrichmentResult<unknown>> {
  const policy = { ...DEFAULT_ENRICHMENT_POLICY, ...options.policy };
  const preferredProviders = options.preferredProviders || [];

  // Check if field is immutable
  if (policy.immutableFields.includes(field) && canonical[field as keyof typeof canonical] != null) {
    return { value: canonical[field as keyof typeof canonical], sourceProviderId: "canonical", confidence: 1.0, timestamp: new Date().toISOString() };
  }

  // Determine providers to query
  let providerIds = getEnrichmentProviders("getTitle");
  if (preferredProviders.length > 0) {
    providerIds = preferredProviders.filter(id => providerIds.includes(id));
  }
  providerIds = providerIds.slice(0, policy.maxProvidersPerField);

  let bestResult: EnrichmentResult<unknown> = { value: null, sourceProviderId: null, confidence: 0, timestamp: new Date().toISOString() };

  for (const providerId of providerIds) {
    const provider = getManhwaProvider(providerId);
    if (!provider) continue;

    try {
      // Try to get title from this provider
      const providerTitle = await provider.getTitle(canonical.providerMappings.find(m => m.providerId === providerId)?.providerSeriesId || "");
      if (!providerTitle) continue;

      const value = extractFieldFromTitle(providerId, providerTitle, field);
      if (value === null || !validateField(field, value)) continue;

      const confidence = calculateFieldConfidence(providerId, field, providerTitle);
      if (confidence < policy.minConfidence) continue;

      const result: EnrichmentResult<unknown> = {
        value,
        sourceProviderId: providerId,
        confidence,
        timestamp: new Date().toISOString(),
      };

      if (confidence > bestResult.confidence) {
        bestResult = result;
      }

      options.onProgress?.(field, providerId, result);

      // If confidence is high enough, we can stop early
      if (confidence >= 0.9) break;
    } catch (err) {
      // Provider error, continue to next
      console.warn(`Enrichment failed for ${field} from ${providerId}:`, err);
    }
  }

  return bestResult;
}

/**
 * Enrich all fields of a canonical series.
 */
export async function enrichCanonicalSeries(
  canonical: import("./types").CanonicalSeries,
  options: EnrichmentOptions = {}
): Promise<EnrichedCanonicalSeries> {
  const policy = { ...DEFAULT_ENRICHMENT_POLICY, ...options.policy };
  const fieldsToEnrich = options.targetFields || Object.keys(FIELD_EXTRACTORS) as string[];
  const fieldSources = new Map<string, EnrichmentResult<unknown>>();

  for (const field of fieldsToEnrich) {
    if (field === "providerMappings") continue; // Handled separately
    const result = await enrichCanonicalField(canonical, field, options);
    fieldSources.set(field, result);

    // Apply the result if it has sufficient confidence
    if (result.value !== null && result.confidence >= 0.3) {
      const currentValue = canonical[field as keyof typeof canonical];
      if (currentValue === null || currentValue === undefined || policy.allowOverwrite) {
        (canonical as any)[field] = result.value;
      }
    }
  }

  // Calculate completeness
  const totalFields = fieldsToEnrich.length;
  const populatedFields = Array.from(fieldSources.values()).filter(r => r.value !== null).length;
  const completeness = totalFields > 0 ? populatedFields / totalFields : 0;

  return {
    canonical,
    fieldSources,
    lastEnriched: new Date().toISOString(),
    completeness,
  };
}

/**
 * Enrich multiple canonical series in batch.
 */
export async function enrichCanonicalSeriesBatch(
  canonicals: import("./types").CanonicalSeries[],
  options: EnrichmentOptions = {}
): Promise<EnrichedCanonicalSeries[]> {
  const results: EnrichedCanonicalSeries[] = [];
  for (const canonical of canonicals) {
    const enriched = await enrichCanonicalSeries(canonical, options);
    results.push(enriched);
  }
  return results;
}

/* ------------------------------------------------------------------ */
/* Provider Enrichment Utilities                                       */
/* ------------------------------------------------------------------ */

/**
 * Get all available fields for a provider.
 */
export function getProviderAvailableFields(providerId: string): string[] {
  const source = getManhwaSource(providerId);
  const caps = (source?.capabilities || {}) as {
    search?: boolean;
    getTitle?: boolean;
    getChapters?: boolean;
    getChapterPages?: boolean;
    trending?: boolean;
    latestUpdates?: boolean;
    ratings?: boolean;
  };
  const fields: string[] = [];
  if (caps.search) fields.push("title", "alternativeTitles", "description", "coverUrl", "genres", "tags", "authors", "artists", "status", "originalLanguage", "releaseYear", "rating", "popularity", "adult", "category", "origin", "isAdult");
  if (caps.getTitle) fields.push("title", "alternativeTitles", "description", "coverUrl", "genres", "tags", "authors", "artists", "status", "originalLanguage", "releaseYear", "rating", "popularity", "adult", "category", "origin", "isAdult");
  if (caps.getChapters) fields.push("chapters");
  if (caps.getChapterPages) fields.push("chapterPages");
  // Remove duplicates
  return [...new Set(fields)];
}

/**
 * Get enrichment status for a canonical series.
 */
export function getEnrichmentStatus(enriched: EnrichedCanonicalSeries): { field: string; status: "missing" | "partial" | "complete"; source?: string; confidence?: number }[] {
  const statusList: { field: string; status: "missing" | "partial" | "complete"; source?: string; confidence?: number }[] = [];
  for (const [field, result] of enriched.fieldSources) {
    if (result.value === null) statusList.push({ field, status: "missing" });
    else if (result.confidence >= 0.8) statusList.push({ field, status: "complete", source: result.sourceProviderId ?? undefined, confidence: result.confidence });
    else statusList.push({ field, status: "partial", source: result.sourceProviderId ?? undefined, confidence: result.confidence });
  }
  return statusList;
}