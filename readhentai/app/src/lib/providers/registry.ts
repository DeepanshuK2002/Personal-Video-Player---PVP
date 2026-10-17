// Provider registry + aggregation services.
//
// A single place to enumerate providers, detect capabilities, and run
// failover-aware fan-out. A failing provider never takes the app down: each
// source is queried independently, failures are caught per-provider, and
// partial results are flagged so callers can tell them apart from full ones.

import { providerHealthy } from "./http";
import { anilist } from "./anilist";
import { mangadex } from "./mangadex";
import { dynasty } from "./dynasty";
import {
  DEFAULT_ADULT_POLICY,
  isEligible,
  type AdultPolicy,
} from "./adult";
import {
  ProviderError,
  type Category,
  type ContentProvider,
  type NormalizedChapter,
  type NormalizedPage,
  type NormalizedTitle,
  type NormalizedUpdate,
  type ProviderInfo,
} from "./types";

/* ------------------------------------------------------------------ */
/* Registry                                                            */
/* ------------------------------------------------------------------ */

const registry = new Map<string, ContentProvider>();

function register(provider: ContentProvider): void {
  registry.set(provider.getProviderInfo().id, provider);
}

// --- Enabled, verified providers ------------------------------------
register(mangadex); // metadata + chapters + pages
register(anilist); // metadata + ratings only
register(dynasty); // latest + metadata + pages-by-permalink (no search / no chapter list)

// --- Disabled providers ---------------------------------------------
// The former local `doujin-api` (nhentai scraper) is intentionally NOT
// registered. It used curl_cffi to impersonate Chrome and bypass TLS-fingerprint
// anti-bot protection, which violates upstream access controls and is outside
// the permitted use for this project (classification:
// NOT_AUTHORIZED_FOR_INTENDED_USE). See docs/PROVIDERS.md.

export function getProvider(id: string): ContentProvider | undefined {
  return registry.get(id);
}

export function listProviders(): ProviderInfo[] {
  return [...registry.values()].map((p) => p.getProviderInfo());
}

/** Providers currently able to serve requests (breaker closed). */
export function healthyProviders(): ContentProvider[] {
  return [...registry.values()].filter((p) => providerHealthy(p.getProviderInfo().id));
}

/* ------------------------------------------------------------------ */
/* Failover fan-out                                                    */
/* ------------------------------------------------------------------ */

/** Run fn across every provider that declares `capability`, isolating failures. */
async function fanOut<T>(
  capability: keyof ProviderInfo["capabilities"],
  fn: (provider: ContentProvider) => Promise<T[]>,
): Promise<{ results: T[]; partial: boolean; errors: string[] }> {
  const candidates = healthyProviders().filter((p) => p.getProviderInfo().capabilities[capability]);
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

  // Partial when some provider failed but we still have (or expected) results.
  const partial = errors.length > 0 && successes > 0;
  if (successes === 0 && errors.length > 0) {
    // Everything failed — surface as empty but record the cause.
    return { results: [], partial: true, errors };
  }
  return { results, partial, errors };
}

/* ------------------------------------------------------------------ */
/* Aggregation services                                                */
/* ------------------------------------------------------------------ */

export interface TitleQuery {
  query?: string;
  categories?: Category[];
  genres?: string[];
  limit?: number;
  offset?: number;
  order?: "latest" | "popular" | "rating" | "relevance";
}

/** Search/aggregate titles across every provider that supports search. */
export async function aggregateSearch(query: string, opts: TitleQuery = {}) {
  const limit = opts.limit ?? 24;
  const perProvider = Math.min(limit, 50);

  const { results, partial, errors } = await fanOut("search", (p) =>
    p.searchTitles(query, {
      limit: perProvider,
      offset: opts.offset ?? 0,
      categories: opts.categories,
      genres: opts.genres,
      order: opts.order,
    }),
  );

  const titles = dedupeTitles(filterTitles(results, opts.categories, opts.genres));
  return { titles: titles.slice(0, limit), partial, errors, total: titles.length };
}

/** Resolve one title by its stable app slug (`<provider>-<providerId>`). */
export async function resolveTitle(slug: string): Promise<NormalizedTitle | null> {
  const providerId = slug.includes("-") ? slug.slice(0, slug.indexOf("-")) : slug;
  const provider = registry.get(providerId);
  if (!provider) return null;
  const rawId = slug.slice(providerId.length + 1);
  return provider.getTitle(rawId);
}

/** Fetch chapters for a title from providers that actually serve them. */
export async function getChaptersForTitle(
  title: NormalizedTitle,
  language = "en",
): Promise<{ chapters: NormalizedChapter[]; partial: boolean }> {
  const provider = registry.get(title.provider);
  if (!provider?.getProviderInfo().capabilities.getChapters) {
    return { chapters: [], partial: false };
  }
  try {
    const chapters = await provider.getChapters(title.providerId, { language, order: "asc" });
    return { chapters, partial: false };
  } catch (err) {
    return { chapters: [], partial: true };
  }
}

/** Resolve page images for a chapter. Only providers with the capability. */
export async function getPagesForChapter(
  providerId: string,
  chapterProviderId: string,
): Promise<NormalizedPage[]> {
  const provider = registry.get(providerId);
  if (!provider?.getProviderInfo().capabilities.getChapterPages) {
    throw new ProviderError(providerId, "no readable pages from this source", "unsupported", false);
  }
  return provider.getChapterPages(chapterProviderId, chapterProviderId);
}

/** Latest updates aggregated across providers that expose them. */
export async function aggregateLatest(limit = 24, language = "en") {
  const { results, partial, errors } = await fanOut("latestUpdates", (p) =>
    p.getLatestUpdates ? p.getLatestUpdates({ limit, language }) : Promise.resolve([] as NormalizedUpdate[]),
  );
  results.sort((a, b) => (b.chapter.publishedAt ?? "").localeCompare(a.chapter.publishedAt ?? ""));
  const seen = new Set<string>();
  const updates = results.filter((u) => {
    // Same central adult gate as search/trending — a secondary provider's
    // general-audience update must not slip into the adult latest feed.
    if (!isEligible(u.title.adult.classification, DEFAULT_ADULT_POLICY)) return false;
    return seen.has(u.title.id) ? false : (seen.add(u.title.id), true);
  });
  return { updates: updates.slice(0, limit), partial, errors };
}

/** Trending/popularity across providers that expose it. */
export async function aggregateTrending(limit = 24, categories?: Category[]) {
  const { results, partial, errors } = await fanOut("trending", (p) =>
    p.getTrending ? p.getTrending({ limit, categories }) : Promise.resolve([] as NormalizedTitle[]),
  );
  const titles = dedupeTitles(filterTitles(results, categories));
  // Interleave provider results so one source doesn't dominate the top slots.
  return { titles: interleave(titles).slice(0, limit), partial, errors };
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
function filterTitles(
  titles: NormalizedTitle[],
  categories?: Category[],
  genres?: string[],
  policy: AdultPolicy = DEFAULT_ADULT_POLICY,
): NormalizedTitle[] {
  return titles.filter((t) => {
    // Adult-content eligibility first: origin category is irrelevant if the
    // work cannot enter the adult catalogue at all.
    if (!isEligible(t.adult.classification, policy)) return false;
    if (categories?.length && !categories.includes(t.category)) return false;
    if (genres?.length && !genres.some((g) => [...t.genres, ...t.tags].includes(g))) return false;
    return true;
  });
}

/** Why a title was excluded — for diagnostics/tests, never shown to end users. */
export function exclusionReason(
  t: NormalizedTitle,
  policy: AdultPolicy = DEFAULT_ADULT_POLICY,
): string | null {
  if (isEligible(t.adult.classification, policy)) return null;
  return `${t.adult.classification} not eligible (${t.adult.reason ?? "no reason"})`;
}

function dedupeTitles(titles: NormalizedTitle[]): NormalizedTitle[] {
  const seen = new Set<string>();
  return titles.filter((t) => {
    const key = t.title.trim().toLowerCase();
    if (!key || seen.has(key)) return false;
    seen.add(key);
    return true;
  });
}

/** Round-robin interleave so trending isn't a single provider's list. */
function interleave<T>(items: T[]): T[] {
  const out: T[] = [];
  let i = 0;
  while (out.length < items.length) {
    if (i < items.length) out.push(items[i]);
    i += 3; // stride ~ number of active providers
  }
  return out;
}
