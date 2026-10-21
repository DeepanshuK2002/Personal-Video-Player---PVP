// GET /api/trending — popularity-ranked titles across providers.
import { aggregateTrending } from "@/lib/providers/registry";
import { contentToCategories, type ContentType } from "@/lib/providers/category";
import { toManga } from "@/lib/providers/normalize";
import { guard, intParam, listParam, strParam } from "@/lib/api-helpers";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const limit = intParam(url, "limit", 24, 50);
  const offset = intParam(url, "offset", 0, 100000);
  const page = intParam(url, "page", 1, 100000);
  const resolvedOffset = url.searchParams.has("offset") ? offset : (page - 1) * limit;
  const contentType = (strParam(url, "contentType") ?? strParam(url, "category") ?? "All") as ContentType;
  const genres = listParam(url, "genre");
  // Period is accepted for API compatibility; providers currently expose a single
  // trending list, so all periods fall back to that list (documented fallback).
  const period = strParam(url, "period") ?? "all-time";

  return guard(async () => {
    const { titles, partial, errors, total } = await aggregateTrending(
      limit,
      contentToCategories(contentType),
      resolvedOffset,
      period,
      genres,
    );
    return {
      items: titles.map((t, i) => ({ ...toManga(t), rank: resolvedOffset + i + 1 })),
      partial,
      errors,
      total,
      hasMore: resolvedOffset + titles.length < (total ?? titles.length),
    };
  });
}
