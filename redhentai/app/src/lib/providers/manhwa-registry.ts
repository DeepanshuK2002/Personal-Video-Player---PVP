/**
 * Manhwa Provider Registry
 *
 * This registry manages Manhwa-specific content providers.
 * It uses the Manhwa source priority configuration and provides
 * aggregation services specifically for Manhwa content.
 */

import { providerHealthy } from "./http";
import { priorityScore } from "./source-selection";
import {
  type Category,
  type ContentProvider,
  type NormalizedChapter,
  type NormalizedPage,
  type NormalizedTitle,
  type NormalizedUpdate,
  type ProviderCapabilities,
  type ProviderError,
  type ProviderInfo,
  type SearchOptions,
} from "./types";
import { MANHWA_SOURCES, getEnabledManhwaSources, getManhwaSource, getEnabledManhwaSourceIds } from "./manhwa-sources";

/* ------------------------------------------------------------------ */
/* Registry                                                            */
/* ------------------------------------------------------------------ */

const manhwaRegistry = new Map<string, ContentProvider>();

/** Register a Manhwa provider adapter. */
export function registerManhwaProvider(provider: ContentProvider): void {
  manhwaRegistry.set(provider.getProviderInfo().id, provider);
}

/** Get a registered Manhwa provider by ID. */
export function getManhwaProvider(id: string): ContentProvider | undefined {
  return manhwaRegistry.get(id);
}

/** List all registered Manhwa providers. */
export function listManhwaProviders(): import("./types").ProviderInfo[] {
  return [...manhwaRegistry.values()].map((p) => p.getProviderInfo());
}

/** Get registered providers that are currently healthy. */
export function healthyManhwaProviders(): ContentProvider[] {
  return [...manhwaRegistry.values()].filter((p) => providerHealthy(p.getProviderInfo().id));
}

/** Get the registry map for external access. */
export { manhwaRegistry };

/** Get enabled source IDs in priority order. */
export { getEnabledManhwaSourceIds };

/* ------------------------------------------------------------------ */
/* Source Priority Integration                                         */
/* ------------------------------------------------------------------ */

/** Get provider priority from Manhwa source config, fallback to generic priority. */
export function manhwaPriorityScore(providerId: string): number {
  const source = getManhwaSource(providerId);
  if (source && source.enabled) {
    // Convert priority (1=highest) to score (1.0=highest)
    // Max priority is 16, so score = 1.0 - (priority-1)/16
    return 1.0 - (source.priority - 1) / 16;
  }
  // Fallback to generic priority
  return priorityScore(providerId);
}

/** Get enabled Manhwa source IDs in priority order. */
export function getManhwaSourcePriorityOrder(): string[] {
  return getEnabledManhwaSources().map((s) => s.id);
}

/* ------------------------------------------------------------------ */
/* Failover fan-out (Manhwa-specific)                                 */
/* ------------------------------------------------------------------ */

async function manhwaFanOut<T>(
  capability: keyof ProviderCapabilities,
  fn: (provider: ContentProvider) => Promise<T[]>,
): Promise<{ results: T[]; partial: boolean; errors: string[] }> {
  const candidates = healthyManhwaProviders()
    .filter((p) => p.getProviderInfo().capabilities[capability])
    // Sort by Manhwa priority
    .sort((a, b) => manhwaPriorityScore(b.getProviderInfo().id) - manhwaPriorityScore(a.getProviderInfo().id));

  const settled = await Promise.allSettled(candidates.map((p) => fn(p)));

  const results: T[] = [];
  const errors: string[] = [];
  let successes = 0;

  settled.forEach((outcome, i) => {
    const id = candidates[i]?.getProviderInfo().id ?? "unknown";
    if (outcome.status === "fulfilled") {
      successes++;
      results.push(...outcome.value);
    } else {
      errors.push(`${id}: ${(outcome.reason as Error)?.message ?? "failed"}`);
    }
  });

  const partial = errors.length > 0 && successes > 0;
  if (successes === 0 && errors.length > 0) {
    return { results: [], partial: true, errors };
  }
  return { results, partial, errors };
}

/* ------------------------------------------------------------------ */
/* Aggregation Services (Manhwa-specific)                             */
/* ------------------------------------------------------------------ */

export interface ManhwaTitleQuery {
  query?: string;
  genres?: string[];
  limit?: number;
  offset?: number;
  order?: "latest" | "popular" | "rating" | "relevance";
  status?: "Completed" | "In Process" | "Paused";
  isAdult?: boolean;
}

/** Search/aggregate Manhwa titles across enabled providers. */
export async function aggregateManhwaSearch(query: string, opts: ManhwaTitleQuery = {}) {
  const limit = opts.limit ?? 24;
  const perProvider = Math.min(limit, 50);

  const { results, partial, errors } = await manhwaFanOut("search", (p) =>
    p.searchTitles(query, {
      limit: perProvider,
      offset: opts.offset ?? 0,
      categories: ["manhwa"],
      genres: opts.genres,
      order: opts.order,
      isAdult: opts.isAdult,
    }),
  );

  // Filter to Manhwa category
  const titles = results.filter((t) => t.category === "manhwa");
  // Deduplicate by title (case-insensitive)
  const seen = new Set<string>();
  const deduped = titles.filter((t) => {
    const key = t.title.trim().toLowerCase();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  return { titles: deduped.slice(0, limit), partial, errors, total: deduped.length };
}

/** Resolve one Manhwa title by its stable app slug. */
export async function resolveManhwaTitle(slug: string): Promise<import("./types").NormalizedTitle | null> {
  const providerId = slug.includes("-") ? slug.slice(0, slug.indexOf("-")) : slug;
  const provider = getManhwaProvider(providerId);
  if (!provider) return null;
  const rawId = slug.slice(providerId.length + 1);
  return provider.getTitle(rawId);
}

/** Fetch chapters for a Manhwa title from providers that serve them. */
export async function getChaptersForManhwaTitle(
  title: import("./types").NormalizedTitle,
  language = "en",
  preferredProviders: string[] = [],
): Promise<{ chapters: import("./types").NormalizedChapter[]; partial: boolean }> {
  const providers = [...manhwaRegistry.values()].filter(
    (p) => p.getProviderInfo().capabilities.getChapters,
  );

  // Order: preferredProviders first, then by Manhwa priority
  const ordered = [...providers].sort((a, b) => {
    const idA = a.getProviderInfo().id;
    const idB = b.getProviderInfo().id;
    const pa = preferredProviders.indexOf(idA);
    const pb = preferredProviders.indexOf(idB);
    if (pa !== -1 && pb !== -1) return pa - pb;
    if (pa !== -1) return -1;
    if (pb !== -1) return 1;
    return manhwaPriorityScore(idB) - manhwaPriorityScore(idA);
  });

  const seenNumbers = new Set<string | null>();
  const chapters: import("./types").NormalizedChapter[] = [];
  let partial = false;

  for (const provider of ordered) {
    try {
      const fetched = await provider.getChapters(title.providerId, {
        language,
        order: "asc",
      });
      const canReadPages = provider.getProviderInfo().capabilities.getChapterPages;
      for (const ch of fetched) {
        if (seenNumbers.has(ch.chapterNumber)) continue;
        seenNumbers.add(ch.chapterNumber);
        chapters.push({ ...ch, readable: canReadPages } as import("./types").NormalizedChapter & { readable: boolean });
      }
    } catch (err) {
      partial = true;
    }
  }

  // Stable sort by chapter number (numeric), then by input order.
  chapters.sort((a, b) => {
    const na = a.chapterNumber !== null ? parseFloat(a.chapterNumber) : NaN;
    const nb = b.chapterNumber !== null ? parseFloat(b.chapterNumber) : NaN;
    if (!isNaN(na) && !isNaN(nb)) return na - nb;
    if (isNaN(na) && !isNaN(nb)) return 1;
    if (!isNaN(na) && isNaN(nb)) return -1;
    return 0;
  });

  return { chapters, partial: false };
}

/** Resolve page images for a chapter. */
export async function getPagesForManhwaChapter(
  providerId: string,
  chapterProviderId: string,
): Promise<import("./types").NormalizedPage[]> {
  const provider = getManhwaProvider(providerId);
  if (!provider?.getProviderInfo().capabilities.getChapterPages) {
    throw new Error(`Provider ${providerId} does not support chapter pages`);
  }
  return provider.getChapterPages(chapterProviderId, chapterProviderId);
}

/** Latest Manhwa updates across providers. */
export async function aggregateManhwaLatest(limit = 24, language = "en", offset = 0) {
  const { results, partial, errors } = await manhwaFanOut("latestUpdates", (p) =>
    p.getLatestUpdates
      ? p.getLatestUpdates({ limit: limit + offset, language })
      : Promise.resolve([] as import("./types").NormalizedUpdate[]),
  );
  results.sort((a, b) => (b.chapter.publishedAt ?? "").localeCompare(a.chapter.publishedAt ?? ""));
  const seen = new Set<string>();
  const updates = results.filter((u) => {
    if (u.title.category !== "manhwa") return false;
    return seen.has(u.title.id) ? false : (seen.add(u.title.id), true);
  });
  return { updates: updates.slice(offset, offset + limit), partial, errors, total: updates.length };
}

/** Trending Manhwa across providers. */
export async function aggregateManhwaTrending(
  limit = 24,
  offset = 0,
  genres?: string[],
) {
  const { results, partial, errors } = await manhwaFanOut("trending", (p) =>
    p.getTrending ? p.getTrending({ limit: Math.max(limit + offset, limit), categories: ["manhwa"] }) : Promise.resolve([] as import("./types").NormalizedTitle[]),
  );
  const titles = results.filter((t) => t.category === "manhwa" && (!genres?.length || genres.some((g) => [...t.genres, ...t.tags].includes(g))));
  return { titles: titles.slice(offset, offset + limit), partial, errors, total: titles.length };
}

/* ------------------------------------------------------------------ */
/* Manhwa-specific capability helpers                                 */
/* ------------------------------------------------------------------ */

/** Get all registered providers that support a specific capability. */
export function getManhwaProvidersWithCapability(capability: keyof ProviderCapabilities): ContentProvider[] {
  return [...manhwaRegistry.values()].filter((p) => p.getProviderInfo().capabilities[capability]);
}

/** Check if a provider is enabled and healthy. */
export function isManhwaProviderReady(id: string): boolean {
  const provider = getManhwaProvider(id);
  if (!provider) return false;
  return providerHealthy(provider.getProviderInfo().id);
}

/** Get source config for a registered provider. */
export function getManhwaProviderConfig(id: string) {
  return getManhwaSource(id);
}

/** Validate all enabled sources have implementations. */
export function validateManhwaRegistry(): { valid: boolean; missing: string[] } {
  const enabledIds = getEnabledManhwaSourceIds();
  const registeredIds = [...manhwaRegistry.keys()];
  const missing = enabledIds.filter((id) => !registeredIds.includes(id));
  return { valid: missing.length === 0, missing };
}