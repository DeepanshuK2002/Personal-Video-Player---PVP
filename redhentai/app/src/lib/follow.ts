const KEY = "readhentai-follow";
const EVENT = "follow-change";

/**
 * A title the user follows. Unlike the bookmark/"Watch Later" store, a follow
 * is about *updates*: we remember the newest chapter the user has already seen
 * so the My List page can flag chapters that dropped since.
 */
export type FollowItem = {
  slug: string;
  title: string;
  followedAt: number;
  /** Newest chapter id acknowledged by the user; null until a baseline is set. */
  seenChapterId: string | null;
  /** Human-readable number of the acknowledged chapter (e.g. "101"). */
  seenChapterNumber: string | null;
};

function normalize(raw: unknown): FollowItem[] {
  if (!Array.isArray(raw)) return [];
  const out: FollowItem[] = [];
  for (const entry of raw) {
    if (typeof entry === "string") {
      out.push({ slug: entry, title: entry, followedAt: 0, seenChapterId: null, seenChapterNumber: null });
      continue;
    }
    if (entry && typeof entry === "object") {
      const e = entry as {
        slug?: unknown;
        id?: unknown;
        title?: unknown;
        name?: unknown;
        followedAt?: unknown;
        seenChapterId?: unknown;
        seenChapterNumber?: unknown;
      };
      const slug = String(e.slug ?? e.id ?? "");
      if (!slug) continue;
      out.push({
        slug,
        title: String(e.title ?? e.name ?? slug),
        followedAt: typeof e.followedAt === "number" ? e.followedAt : 0,
        seenChapterId: e.seenChapterId == null ? null : String(e.seenChapterId),
        seenChapterNumber: e.seenChapterNumber == null ? null : String(e.seenChapterNumber),
      });
    }
  }
  const seen = new Set<string>();
  return out.filter((item) => {
    if (seen.has(item.slug)) return false;
    seen.add(item.slug);
    return true;
  });
}

function write(next: FollowItem[]): void {
  localStorage.setItem(KEY, JSON.stringify(next));
  window.dispatchEvent(new CustomEvent(EVENT));
}

export function getFollows(): FollowItem[] {
  if (typeof window === "undefined") return [];
  try {
    return normalize(JSON.parse(localStorage.getItem(KEY) || "[]"));
  } catch {
    return [];
  }
}

export function getFollowedSlugs(): string[] {
  return getFollows().map((item) => item.slug);
}

export function isFollowed(slug: string): boolean {
  return getFollows().some((item) => item.slug === slug);
}

export function toggleFollow(slug: string, title?: string): boolean {
  const current = getFollows();
  const exists = current.some((item) => item.slug === slug);
  const next = exists
    ? current.filter((item) => item.slug !== slug)
    : [...current, { slug, title: title || slug, followedAt: Date.now(), seenChapterId: null, seenChapterNumber: null }];
  write(next);
  return next.some((item) => item.slug === slug);
}

export function removeFollow(slug: string): void {
  write(getFollows().filter((item) => item.slug !== slug));
}

/**
 * Record the newest chapter the user has acknowledged. Used both to seed a
 * baseline for freshly-followed titles (so they don't falsely read as "new")
 * and to clear the "new" flag once the user has caught up.
 */
export function setSeenChapters(
  entries: Array<{ slug: string; chapterId: string; chapterNumber?: string | null }>,
): void {
  if (typeof window === "undefined" || entries.length === 0) return;
  const map = new Map(entries.map((e) => [e.slug, e]));
  let changed = false;
  const next = getFollows().map((item) => {
    const entry = map.get(item.slug);
    if (!entry) return item;
    const number = entry.chapterNumber ?? item.seenChapterNumber;
    if (entry.chapterId === item.seenChapterId && number === item.seenChapterNumber) return item;
    changed = true;
    return { ...item, seenChapterId: entry.chapterId, seenChapterNumber: number ?? null };
  });
  if (changed) write(next);
}
