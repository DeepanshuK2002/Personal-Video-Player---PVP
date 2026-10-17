// GET /api/title/[slug]/chapter/[chapterId]/pages — ordered page images.
import { getPagesForChapter } from "@/lib/providers/registry";
import { guard } from "@/lib/api-helpers";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ slug: string; chapterId: string }> },
) {
  const { slug, chapterId } = await params;
  const providerId = slug.includes("-") ? slug.slice(0, slug.indexOf("-")) : slug;

  return guard(async () => {
    // chapterId is the provider's own chapter uuid (stored on NormalizedChapter).
    const pages = await getPagesForChapter(providerId, chapterId);
    return { pages };
  });
}
