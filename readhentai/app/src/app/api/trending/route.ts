// GET /api/trending — popularity-ranked titles across providers.
import { aggregateTrending } from "@/lib/providers/registry";
import { contentToCategories, type ContentType } from "@/lib/providers/category";
import { toManga } from "@/lib/providers/normalize";
import { guard, intParam, strParam } from "@/lib/api-helpers";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const limit = intParam(url, "limit", 24, 50);
  const contentType = (strParam(url, "contentType") ?? "All") as ContentType;

  return guard(async () => {
    const { titles, partial, errors } = await aggregateTrending(limit, contentToCategories(contentType));
    return {
      items: titles.map((t, i) => ({ ...toManga(t), rank: i + 1 })),
      partial,
      errors,
    };
  });
}
