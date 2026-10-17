// GET /api/title/[slug] — one title's metadata + its readable chapters.
import { resolveTitle, getChaptersForTitle } from "@/lib/providers/registry";
import { toManga } from "@/lib/providers/normalize";
import { guard } from "@/lib/api-helpers";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ slug: string }> },
) {
  const { slug } = await params;

  return guard(async () => {
    const title = await resolveTitle(slug);
    if (!title) {
      return { error: "not_found", item: null, chapters: [] };
    }
    const language = "en";
    const { chapters, partial } = await getChaptersForTitle(title, language);
    return {
      item: toManga(title),
      chapters: chapters.map((c) => ({
        id: c.id,
        number: c.chapterNumber,
        title: c.chapterTitle,
        pages: c.pageCount,
        readable: c.readable,
        publishedAt: c.publishedAt,
      })),
      chapterCount: chapters.length,
      partial,
    };
  });
}
