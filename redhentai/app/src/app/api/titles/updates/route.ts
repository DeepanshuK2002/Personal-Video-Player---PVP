// POST /api/titles/updates — resolve followed titles and report each one's
// newest chapter. Powers the "My List" update feed: the client stores only
// slugs + the last chapter it has seen, and compares against `latestChapter.id`
// to flag titles that dropped new chapters.
import { resolveTitle, getChaptersForTitle } from "@/lib/providers/registry";
import { toManga } from "@/lib/providers/normalize";
import { guard } from "@/lib/api-helpers";
import type { Manga } from "@/lib/manga";

interface UpdatesBody {
  slugs?: string[];
}

export async function POST(request: Request) {
  return guard(async () => {
    let body: UpdatesBody = {};
    try {
      body = await request.json();
    } catch {
      body = {};
    }

    // Bound the work so a huge follow list can't hammer upstream providers.
    const slugs = Array.isArray(body.slugs) ? body.slugs.slice(0, 60) : [];

    const items: Array<{
      manga: Manga;
      latestChapter: {
        id: string;
        providerChapterId: string;
        number: string | null;
        title: string | null;
        pages: number | null;
        publishedAt: string | null;
        readable: boolean;
      } | null;
    }> = [];

    const BATCH = 6;
    for (let i = 0; i < slugs.length; i += BATCH) {
      const chunk = slugs.slice(i, i + BATCH);
      const resolved = await Promise.all(
        chunk.map(async (slug) => {
          const title = await resolveTitle(slug);
          if (!title) {
            return {
              manga: {
                slug,
                title: slug,
                rating: null,
                chapters: 0,
                views: "",
                cover: "",
                unavailable: true,
              } satisfies Manga,
              latestChapter: null,
            };
          }
          const { chapters } = await getChaptersForTitle(title, "en");
          // Chapters are requested ascending, so the newest drop is last.
          const latest = chapters.length ? chapters[chapters.length - 1] : null;
return {
              manga: toManga(title),
              latestChapter: latest
                ? {
                    id: latest.id,
                    providerChapterId: latest.providerChapterId,
                    number: latest.chapterNumber,
                    title: latest.chapterTitle,
                    pages: latest.pageCount,
                    publishedAt: latest.publishedAt,
                    readable: latest.readable ?? false,
                  }
                : null,
            };
        }),
      );
      items.push(...resolved);
    }

    return { items };
  });
}
