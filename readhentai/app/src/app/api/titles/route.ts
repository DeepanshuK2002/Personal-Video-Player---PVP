// GET /api/titles — aggregated title search across enabled providers.
import { aggregateSearch } from "@/lib/providers/registry";
import { contentToCategories, type ContentType } from "@/lib/providers/category";
import { toManga } from "@/lib/providers/normalize";
import { guard, intParam, listParam, strParam } from "@/lib/api-helpers";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const query = strParam(url, "q") ?? "";
  const contentType = (strParam(url, "contentType") ?? "All") as ContentType;
  const genres = listParam(url, "genre");
  const limit = intParam(url, "limit", 24, 50);
  const offset = intParam(url, "offset", 0);
  const order = (strParam(url, "order") ?? "latest") as "latest" | "popular" | "rating" | "relevance";

  return guard(async () => {
    const result = await aggregateSearch(query, {
      categories: contentToCategories(contentType),
      genres,
      limit,
      offset,
      order,
    });
    return {
      items: result.titles.map(toManga),
      partial: result.partial,
      total: result.total,
      errors: result.errors,
    };
  });
}
