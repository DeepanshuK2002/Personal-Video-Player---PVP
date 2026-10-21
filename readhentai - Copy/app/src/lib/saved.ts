const KEY = "readhentai-saved";

export type SavedItem = { slug: string; title: string };

function normalize(raw: unknown): SavedItem[] {
  if (!Array.isArray(raw)) return [];
  const out: SavedItem[] = [];
  for (const entry of raw) {
    if (typeof entry === "string") {
      out.push({ slug: entry, title: entry });
    } else if (entry && typeof entry === "object") {
      const e = entry as { slug?: unknown; title?: unknown; id?: unknown; name?: unknown };
      const slug = String(e.slug ?? e.id ?? "");
      if (!slug) continue;
      const title = String(e.title ?? e.name ?? slug);
      out.push({ slug, title });
    }
  }
  // de-dupe by slug, keep first
  const seen = new Set<string>();
  return out.filter((item) => {
    if (seen.has(item.slug)) return false;
    seen.add(item.slug);
    return true;
  });
}

export function getSaved(): SavedItem[] {
  if (typeof window === "undefined") return [];
  try {
    return normalize(JSON.parse(localStorage.getItem(KEY) || "[]"));
  } catch {
    return [];
  }
}

/** Back-compat: slugs only. */
export function getSavedSlugs(): string[] {
  return getSaved().map((item) => item.slug);
}

export function isSaved(slug: string): boolean {
  return getSaved().some((item) => item.slug === slug);
}

export function toggleSaved(slug: string, title?: string): boolean {
  const current = getSaved();
  const exists = current.some((item) => item.slug === slug);
  const next = exists
    ? current.filter((item) => item.slug !== slug)
    : [...current, { slug, title: title || slug }];
  localStorage.setItem(KEY, JSON.stringify(next));
  window.dispatchEvent(new CustomEvent("saved-change"));
  return next.some((item) => item.slug === slug);
}
