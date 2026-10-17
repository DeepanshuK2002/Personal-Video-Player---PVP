// GET /api/latest — latest chapter updates across providers.
import { aggregateLatest } from "@/lib/providers/registry";
import { toManga } from "@/lib/providers/normalize";
import { guard, intParam, strParam } from "@/lib/api-helpers";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const limit = intParam(url, "limit", 24, 50);
  const language = strParam(url, "language") ?? "en";

  return guard(async () => {
    const { updates, partial, errors } = await aggregateLatest(limit, language);
    return {
      items: updates.map((u) => ({
        ...toManga(u.title),
        // Carry the newest chapter so "latest" is genuinely the latest drop.
        chapters: 0,
        pages: u.chapter.pageCount ?? undefined,
      })),
      partial,
      errors,
    };
  });
}
