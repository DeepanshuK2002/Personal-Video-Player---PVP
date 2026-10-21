// GET /api/title/[slug]/chapter/[chapterId]/pages — ordered page images.
import { getPagesForChapter, getProvider } from "@/lib/providers/registry";
import { guard } from "@/lib/api-helpers";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ slug: string; chapterId: string }> },
) {
  const { slug, chapterId } = await params;

  // Provider normally comes from the slug's first segment (the reader base is
  // chapter-aware, so slug and chapter agree). A namespaced chapter id
  // ("<provider>:<ref>", e.g. "enma:688749__0") wins when the prefix is a real
  // registered provider — legacy links and API consumers may still send one.
  const nsAt = chapterId.indexOf(":");
  const nsPrefix = nsAt > 0 ? chapterId.slice(0, nsAt) : "";
  const nsProvider = nsPrefix && getProvider(nsPrefix) ? nsPrefix : "";
  const providerId = nsProvider || (slug.includes("-") ? slug.slice(0, slug.indexOf("-")) : slug);
  const chapterRef = nsProvider ? chapterId.slice(nsAt + 1) : chapterId;

  return guard(async () => {
    // chapterRef is the provider's own chapter uuid (stored on NormalizedChapter).
    const pages = await getPagesForChapter(providerId, chapterRef);
    return { pages };
  });
}
