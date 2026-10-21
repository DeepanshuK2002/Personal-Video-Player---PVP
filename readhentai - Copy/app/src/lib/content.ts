"use client";

// Client content store: fetches from the app's own /api routes (which call
// providers server-side). Provides cache-first reads, background refresh,
// request deduplication, cancellation, and stale-response protection so fast
// category/filter switching never renders results for a superseded query.

import { useCallback, useEffect, useRef, useState } from "react";
import type { Manga } from "@/lib/manga";
import { getFollows, setSeenChapters, type FollowItem } from "@/lib/follow";

export interface TitleResult {
  items: Manga[];
  partial?: boolean;
  total?: number;
  stale?: boolean;
}

/** Bounded in-memory cache keyed by request path, with a short TTL. */
const CACHE_TTL = 60_000;
const cache = new Map<string, { data: TitleResult; at: number }>();
const inflight = new Map<string, Promise<TitleResult>>();

/**
 * Stable placeholder for the loading/empty state. `useTitles` must never hand
 * back a freshly-allocated `[]`: while `path` is null (or `data` is unset) a
 * new reference on every render re-triggers any effect keyed on `items`, which
 * loops — "Maximum update depth exceeded".
 */
const EMPTY_ITEMS: Manga[] = [];

async function fetchTitles(path: string): Promise<TitleResult> {
  const existing = inflight.get(path);
  if (existing) return existing;

  const promise = (async () => {
    const res = await fetch(path, { headers: { Accept: "application/json" } });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const json = await res.json();
    const data: TitleResult = {
      items: Array.isArray(json.items) ? json.items : [],
      partial: json.partial,
      total: json.total,
    };
    cache.set(path, { data, at: Date.now() });
    return data;
  })().finally(() => inflight.delete(path));

  inflight.set(path, promise);
  return promise;
}

export interface UseTitlesOptions {
  /** Immediately return cached data (even if stale) while refreshing. */
  cacheFirst?: boolean;
}

/**
 * Subscribe to a title-list endpoint. `path` fully identifies the query, so
 * changing filters is a cache read + optional background refresh.
 */
export function useTitles(path: string | null, options: UseTitlesOptions = {}) {
  const { cacheFirst = true } = options;
  const [data, setData] = useState<TitleResult | null>(() => {
    if (!path || !cacheFirst) return null;
    const hit = cache.get(path);
    return hit ? { ...hit.data, stale: Date.now() - hit.at > CACHE_TTL } : null;
  });
  const [loading, setLoading] = useState<boolean>(() => {
    if (!path || !cacheFirst) return true;
    return !cache.has(path);
  });
  const [error, setError] = useState<string | null>(null);

  // Monotonic token to drop stale responses (stale-response protection).
  const requestToken = useRef(0);

  useEffect(() => {
    if (!path) {
      setData(null);
      setLoading(false);
      return;
    }

    const token = ++requestToken.current;
    const hit = cache.get(path);
    const isStale = !hit || Date.now() - hit.at > CACHE_TTL;

    if (hit && cacheFirst) {
      setData({ ...hit.data, stale: isStale });
      setLoading(isStale); // show cached instantly, refresh in background
    } else {
      setLoading(true);
    }

    let cancelled = false;
    fetchTitles(path)
      .then((result) => {
        // Ignore responses that arrived after a newer request started.
        if (cancelled || token !== requestToken.current) return;
        setData(result);
        setError(null);
      })
      .catch((err) => {
        if (cancelled || token !== requestToken.current) return;
        setError((err as Error).message);
      })
      .finally(() => {
        if (!cancelled && token === requestToken.current) setLoading(false);
      });

    return () => {
      cancelled = true; // cancel on unmount / path change
    };
  }, [path, cacheFirst]);

  const refresh = useCallback(() => {
    if (!path) return;
    cache.delete(path);
    requestToken.current++;
    setLoading(true);
    fetchTitles(path)
      .then((result) => setData(result))
      .catch((err) => setError((err as Error).message))
      .finally(() => setLoading(false));
  }, [path]);

  return { data, items: data?.items ?? EMPTY_ITEMS, loading, error, refresh };
}

/* ------------------------------------------------------------------ */
/* Single title + chapters                                             */
/* ------------------------------------------------------------------ */

export interface TitleDetail {
  item: Manga | null;
  chapters: Array<{
    id: string;
    providerChapterId?: string;
    number: string | null;
    title: string | null;
    pages: number | null;
    readable: boolean;
    publishedAt: string | null;
  }>;
  chapterCount: number;
  partial?: boolean;
}

const detailCache = new Map<string, { data: TitleDetail; at: number }>();

/** Fetch one title and its chapters by stable slug. */
export function useTitleDetail(slug: string | null) {
  const [data, setData] = useState<TitleDetail | null>(() => {
    if (!slug) return null;
    const hit = detailCache.get(slug);
    return hit ? hit.data : null;
  });
  const [loading, setLoading] = useState(!slug || !detailCache.has(slug));
  const [error, setError] = useState<string | null>(null);
  const token = useRef(0);

  useEffect(() => {
    if (!slug) {
      setData(null);
      setLoading(false);
      return;
    }
    const t = ++token.current;
    let cancelled = false;

    const hit = detailCache.get(slug);
    if (hit) setData(hit.data);
    setLoading(!hit);

    fetch(`/api/title/${slug}`, { headers: { Accept: "application/json" } })
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = (await res.json()) as TitleDetail;
        detailCache.set(slug, { data: json, at: Date.now() });
        if (!cancelled && t === token.current) {
          setData(json);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled && t === token.current) setError((err as Error).message);
      })
      .finally(() => {
        if (!cancelled && t === token.current) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [slug]);

  return { detail: data, loading, error };
}

/* ------------------------------------------------------------------ */
/* Followed-title updates (My List / home "New Chapters" rail)         */
/* ------------------------------------------------------------------ */

export interface FollowUpdateChapter {
  id: string;
  providerChapterId: string;
  number: string | null;
  title: string | null;
  pages: number | null;
  publishedAt: string | null;
  readable: boolean;
}

export interface FollowUpdateEntry {
  manga: Manga;
  latestChapter: FollowUpdateChapter | null;
}

/**
 * Subscribe to the followed titles and their newest chapter each. Also seeds a
 * baseline `seenChapterId` for freshly-followed titles so they don't read as
 * "new" until a chapter actually drops afterwards.
 */
export function useFollowUpdates() {
  const [follows, setFollows] = useState<FollowItem[]>([]);
  const [updates, setUpdates] = useState<Record<string, FollowUpdateEntry>>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setFollows(getFollows());
    const handler = () => setFollows(getFollows());
    window.addEventListener("follow-change", handler);
    return () => window.removeEventListener("follow-change", handler);
  }, []);

  const slugsKey = follows.map((f) => f.slug).join(",");

  useEffect(() => {
    let cancelled = false;
    const slugs = slugsKey ? slugsKey.split(",") : [];
    if (slugs.length === 0) {
      setUpdates({});
      setLoading(false);
      return;
    }
    setLoading(true);
    fetch("/api/titles/updates", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ slugs }),
    })
      .then((res) => (res.ok ? res.json() : { items: [] }))
      .then((json) => {
        if (cancelled) return;
        const map: Record<string, FollowUpdateEntry> = {};
        for (const entry of (json.items ?? []) as FollowUpdateEntry[]) {
          if (entry?.manga?.slug) map[entry.manga.slug] = entry;
        }
        setUpdates(map);
      })
      .catch(() => {
        if (!cancelled) setUpdates({});
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [slugsKey]);

  // Seed baselines once updates arrive; after that this is a no-op.
  useEffect(() => {
    if (loading) return;
    const pending = follows
      .filter((f) => f.seenChapterId == null)
      .map((f) => {
        const latest = updates[f.slug]?.latestChapter;
        return { slug: f.slug, chapterId: latest?.id, chapterNumber: latest?.number };
      })
      .filter((e): e is { slug: string; chapterId: string; chapterNumber: string | null } =>
        Boolean(e.chapterId),
      );
    if (pending.length > 0) setSeenChapters(pending);
  }, [follows, updates, loading]);

  return { follows, updates, loading };
}

/* ------------------------------------------------------------------ */
/* Reader pages                                                        */
/* ------------------------------------------------------------------ */

/* ------------------------------------------------------------------ */
/* Batch resolve (History / Watch Later)                               */
/* ------------------------------------------------------------------ */

const resolveCache = new Map<string, Manga>();
const resolveInflight = new Map<string, Promise<Manga | null>>();

/** Resolve one stable slug to a live title; null when it no longer exists. */
export async function resolveSlug(slug: string): Promise<Manga | null> {
  const cachedManga = resolveCache.get(slug);
  if (cachedManga) return cachedManga;

  const existing = resolveInflight.get(slug);
  if (existing) return existing;

  const promise = (async () => {
    try {
      const res = await fetch("/api/titles/resolve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ slugs: [slug] }),
      });
      if (!res.ok) return null;
      const json = await res.json();
      const item: Manga | undefined = json.items?.[0];
      if (item && !item.unavailable) {
        resolveCache.set(slug, item);
        return item;
      }
      return item ?? null;
    } catch {
      return null;
    } finally {
      resolveInflight.delete(slug);
    }
  })();

  resolveInflight.set(slug, promise);
  return promise;
}

/** Resolve a batch of slugs, preserving input order. */
export async function resolveSlugs(slugs: string[]): Promise<Array<Manga | null>> {
  return Promise.all(slugs.map((s) => resolveSlug(s)));
}

export function useChapterPages(slug: string | null, chapterId: string | null) {
  const [pages, setPages] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const token = useRef(0);

  useEffect(() => {
    if (!slug || !chapterId) {
      setPages([]);
      return;
    }
    const t = ++token.current;
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch(`/api/title/${slug}/chapter/${chapterId}/pages`, {
      headers: { Accept: "application/json" },
    })
      .then(async (res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (cancelled || t !== token.current) return;
        // Preserve provider page order exactly as returned.
        const sorted: Array<{ index: number; imageUrl: string }> = Array.isArray(json.pages)
          ? [...json.pages].sort((a, b) => a.index - b.index)
          : [];
        setPages(sorted.map((p) => p.imageUrl));
      })
      .catch((err) => {
        if (!cancelled && t === token.current) setError((err as Error).message);
      })
      .finally(() => {
        if (!cancelled && t === token.current) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [slug, chapterId]);

  return { pages, loading, error };
}
