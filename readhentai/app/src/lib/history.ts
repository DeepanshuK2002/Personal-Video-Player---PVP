const KEY = "readhentai:history";
const MAX = 12;

export function getHistory(): string[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function addHistory(slug: string): void {
  if (typeof window === "undefined") return;
  try {
    const current = getHistory().filter((s) => s !== slug);
    const next = [slug, ...current].slice(0, MAX);
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
