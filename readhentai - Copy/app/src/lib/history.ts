const KEY = "readhentai:history";
const MAX = 100;

export interface HistoryEntry {
  slug: string;
  title?: string;
  /** Epoch ms of the most recent open; 0 for legacy string-only entries. */
  at: number;
}

function normalize(parsed: unknown): HistoryEntry[] {
  if (!Array.isArray(parsed)) return [];
  return parsed.flatMap<HistoryEntry>((item) => {
    if (typeof item === "string") return item ? [{ slug: item, at: 0 }] : [];
    if (item && typeof item === "object") {
      const e = item as Partial<HistoryEntry>;
      if (typeof e.slug === "string" && e.slug) {
        return [
          {
            slug: e.slug,
            title: typeof e.title === "string" ? e.title : undefined,
            at: typeof e.at === "number" && Number.isFinite(e.at) ? e.at : 0,
          },
        ];
      }
    }
    return [];
  });
}

/** Full history, most-recently-opened first. */
export function getHistoryEntries(): HistoryEntry[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    const entries = normalize(raw ? JSON.parse(raw) : []);
    // Stable sort: newest first; legacy (at=0) keeps its stored order.
    return entries.sort((a, b) => b.at - a.at);
  } catch {
    return [];
  }
}

/** Slugs only (most-recent first) — used by the home carousel. */
export function getHistory(): string[] {
  return getHistoryEntries().map((e) => e.slug);
}

export function addHistory(slug: string, title?: string): void {
  if (typeof window === "undefined") return;
  try {
    const current = getHistoryEntries().filter((e) => e.slug !== slug);
    const next: HistoryEntry[] = [{ slug, title, at: Date.now() }, ...current].slice(0, MAX);
    window.localStorage.setItem(KEY, JSON.stringify(next));
    window.dispatchEvent(new Event("history-change"));
  } catch {
    /* ignore */
  }
}

export function clearHistory(): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(KEY);
    window.dispatchEvent(new Event("history-change"));
  } catch {
    /* ignore */
  }
}
