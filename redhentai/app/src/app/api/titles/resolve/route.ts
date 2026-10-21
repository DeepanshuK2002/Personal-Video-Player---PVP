// POST /api/titles/resolve — resolve a batch of stable slugs to titles.
// Used by History and Watch Later, which persist only slugs + titles and need
// to hydrate them against the live catalogue. Slugs that no longer resolve are
// returned with `unavailable: true` so the UI can render a graceful state
// instead of dropping the user's saved/history entry.
import { resolveTitle } from "@/lib/providers/registry";
import { toManga } from "@/lib/providers/normalize";
import { guard } from "@/lib/api-helpers";
import type { Manga } from "@/lib/manga";

interface ResolveBody {
  slugs?: string[];
  titles?: Array<{ slug: string; title?: string }>;
}

export async function POST(request: Request) {
  return guard(async () => {
    let body: ResolveBody = {};
    try {
      body = await request.json();
    } catch {
      body = {};
    }

    const entries: Array<{ slug: string; title?: string }> = Array.isArray(body.titles)
      ? body.titles
      : (body.slugs ?? []).map((slug) => ({ slug }));

    // Bound concurrency; a handful at a time is plenty for history/saved.
    const results: Manga[] = [];
    const BATCH = 6;
    for (let i = 0; i < entries.length; i += BATCH) {
      const chunk = entries.slice(i, i + BATCH);
      const resolved = await Promise.all(
        chunk.map(async (entry) => {
          const title = await resolveTitle(entry.slug);
          if (title) {
            const manga = toManga(title);
            // Preserve the title the user saved/bookmarked at the time.
            return entry.title ? { ...manga, title: entry.title } : manga;
          }
          // Unresolved: keep a minimal, clearly-unavailable placeholder.
          return {
            slug: entry.slug,
            title: entry.title ?? entry.slug,
            rating: null,
            chapters: 0,
            views: "",
            cover: "",
            unavailable: true,
          } satisfies Manga;
        }),
      );
      results.push(...resolved);
    }

    return { items: results };
  });
}
