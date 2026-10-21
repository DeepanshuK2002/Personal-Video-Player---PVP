// Provider registry + aggregation services.
//
// A single place to enumerate providers, detect capabilities, and run
// failover-aware fan-out. A failing provider never takes the app down: each
// source is queried independently, failures are caught per-provider, and
// partial results are flagged so callers can tell them apart from full ones.

import { providerHealthy } from "./http";
import { priorityScore } from "./source-selection";
import { areSameSeries, normalizeTitleForMatch } from "./series-matching";
import { anilist } from "./anilist";
import { dynasty } from "./dynasty";
import { hentairead } from "./hentairead";
import { hentai18 } from "./hentai18";
import { hentaireadmoe } from "./hentaireadmoe";
import { enma } from "./enma";
import { mangadex } from "./mangadex";
import { omegascans } from "./omegascans";
import { hiperdex } from "./hiperdex";
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

// Manhwa-specific registry (new)
import { manhwaRegistry, listManhwaProviders, healthyManhwaProviders, manhwaPriorityScore, registerManhwaProvider } from "./manhwa-registry";
import { MANHWA_SOURCES, getEnabledManhwaSources, getEnabledManhwaSourceIds } from "./manhwa-sources";

/* ------------------------------------------------------------------ */
/* Registry                                                            */
/* ------------------------------------------------------------------ */

const registry = new Map<string, ContentProvider>();

function register(provider: ContentProvider): void {
  registry.set(provider.getProviderInfo().id, provider);
}

// --- Enabled, verified providers ------------------------------------
register(anilist); // metadata + ratings only
register(dynasty); // latest + metadata + pages-by-permalink (no search / no chapter list)
register(hentairead); // trending + title metadata + chapters + in-app reader (via display proxy)
register(hentai18); // search + trending + latest + metadata + chapters + reader pages
register(hentaireadmoe); // trending + latest + metadata + chapters + reader pages
register(enma); // nhentai (official API v2) via the local Enma sidecar — SELF_HOST_REQUIRED
// Manhwa providers
register(omegascans); // trending + title metadata + chapters + in-app reader (via display proxy)
register(hiperdex); // trending + title metadata + chapters + in-app reader (via display proxy)

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
  // Interleave BEFORE slicing: `fanOut` pushes each provider's block
  // contiguously and AniList is registered first, so without this a plain
  // `slice(0, limit)` kept 100% AniList (metadata-only, no readable chapters)
  // and dropped every hentai18 result. Same round-robin used for trending.
  const ordered = interleave(titles);
  return { titles: ordered.slice(0, limit), partial, errors, total: ordered.length };
}

/** Resolve one title by its stable app slug (`<provider>-<providerId>`). */
export async function resolveTitle(slug: string): Promise<NormalizedTitle | null> {
  const providerId = slug.includes("-") ? slug.slice(0, slug.indexOf("-")) : slug;
  const provider = registry.get(providerId);
  if (!provider) return null;
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
export async function getChaptersForTitle(
  title: NormalizedTitle,
  language = "en",
  preferredProviders: string[] = [],
): Promise<{ chapters: NormalizedChapter[]; partial: boolean }> {
  const providers = [...registry.values()].filter(
    (p) => p.getProviderInfo().capabilities.getChapters,
  );

  // Order: preferredProviders first (in given order), then by priority score,
  // then the title's own provider, then everything else.
  const ordered = [...providers].sort((a, b) => {
    const idA = a.getProviderInfo().id;
    const idB = b.getProviderInfo().id;
    const pa = preferredProviders.indexOf(idA);
    const pb = preferredProviders.indexOf(idB);
    if (pa !== -1 && pb !== -1) return pa - pb;
    if (pa !== -1) return -1;
    if (pb !== -1) return 1;
    const sa = priorityScore(idA);
    const sb = priorityScore(idB);
    if (sa !== sb) return sb - sa;
    // Title's own provider gets a small bump for continuity.
    const ta = idA === title.provider ? 1 : 0;
    const tb = idB === title.provider ? 1 : 0;
    return tb - ta;
  });

  const seenNumbers = new Set<string | null>();
  const chapters: NormalizedChapter[] = [];
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
        chapters.push({ ...ch, readable: canReadPages } as NormalizedChapter & { readable: boolean });
      }
    } catch (err) {
      partial = true;
    }
  }

  // Cross-provider fallback: nobody served this provider's id. Search other
  // chapter-capable sources for the same series and use their chapters.
  if (chapters.length === 0) {
    const matched = await findChaptersByTitleMatch(title, language, ordered);
    for (const ch of matched) {
      if (seenNumbers.has(ch.chapterNumber)) continue;
      seenNumbers.add(ch.chapterNumber);
      chapters.push(ch);
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
export async function findChaptersByTitleMatch(
  title: NormalizedTitle,
  language: string,
  ordered: ContentProvider[],
): Promise<NormalizedChapter[]> {
  const candidates = ordered
    .filter((p) => {
      const caps = p.getProviderInfo().capabilities;
      return caps.search && caps.getChapters && p.getProviderInfo().id !== title.provider;
    })
    .slice(0, 4); // bound worst-case latency (sequential search per source)

  const queries = [title.title, ...title.alternativeTitles]
    .map((q) => q?.trim())
    .filter((q): q is string => Boolean(q))
    .slice(0, 2);

  const identityTokens = (t: NormalizedTitle): Set<string> =>
    new Set(
      [t.title, ...t.alternativeTitles]
        .map((s) => normalizeTitleForMatch(s ?? ""))
        .filter(Boolean),
    );
  const idQuery = identityTokens(title);

  for (const provider of candidates) {
    const canReadPages = provider.getProviderInfo().capabilities.getChapterPages;
    for (const query of queries) {
      let hits: NormalizedTitle[] = [];
      try {
        hits = await provider.searchTitles(query, { limit: 10 });
      } catch {
        continue; // dead search endpoint — next source
      }
      const match = hits.find((hit) => {
        const idHit = identityTokens(hit);
        for (const tok of idQuery) if (idHit.has(tok)) return true;
        return areSameSeries(title, hit);
      });
      if (!match) continue;
      try {
        const fetched = await provider.getChapters(match.providerId, {
          language,
          order: "asc",
        });
        if (fetched.length > 0) {
          return fetched.map(
            (ch) =>
              ({ ...ch, readable: canReadPages } as NormalizedChapter & {
                readable: boolean;
              }),
          );
        }
      } catch {
        // matched, but its chapter list failed — next source
      }
    }
  }
  return [];
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
export async function aggregateLatest(limit = 24, language = "en", offset = 0) {
  const { results, partial, errors } = await fanOut("latestUpdates", (p) =>
    p.getLatestUpdates
      ? p.getLatestUpdates({ limit: limit + offset, language })
      : Promise.resolve([] as NormalizedUpdate[]),
  );
  results.sort((a, b) => (b.chapter.publishedAt ?? "").localeCompare(a.chapter.publishedAt ?? ""));
  const seen = new Set<string>();
  const updates = results.filter((u) => {
    // Same central adult gate as search/trending — a secondary provider's
    // general-audience update must not slip into the adult latest feed.
    if (!isEligible(u.title.adult.classification, DEFAULT_ADULT_POLICY)) return false;
    return seen.has(u.title.id) ? false : (seen.add(u.title.id), true);
  });
  return { updates: updates.slice(offset, offset + limit), partial, errors, total: updates.length };
}

/** Trending/popularity across providers that expose it. */
export async function aggregateTrending(
  limit = 24,
  categories?: Category[],
  offset = 0,
  period?: string,
  genres?: string[],
) {
  // `period` is accepted for API compatibility; providers expose a single
  // trending list, so all periods use it (documented fallback).
  void period;
  const { results, partial, errors } = await fanOut("trending", (p) =>
    p.getTrending ? p.getTrending({ limit: Math.max(limit + offset, limit), categories }) : Promise.resolve([] as NormalizedTitle[]),
  );
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
    if (categories?.length && (!t.category || !categories.includes(t.category as Category))) return false;
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
export function interleave<T>(items: T[]): T[] {
  const n = items.length;
  if (n <= 1) return items;
  const stride = 3; // ~ number of registered providers
  const emitted = new Array<boolean>(n).fill(false);
  const out: T[] = [];
  for (let i = 0; i < n; i += stride) {
    out.push(items[i]);
    emitted[i] = true;
  }
  for (let i = 0; i < n; i++) {
    if (!emitted[i]) out.push(items[i]);
  }
  return out;
}