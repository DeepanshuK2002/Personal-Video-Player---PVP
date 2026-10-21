// Bridges the UI-facing ContentType selector (All/Manga/Manhwa/Comics) with the
// provider-level Category enum. Keeps the existing settings store semantics
// intact while normalizing to what providers understand.

import type { Category } from "./types";

export const CONTENT_TYPES = ["All", "Manga", "Manhwa", "Comics"] as const;
export type ContentType = (typeof CONTENT_TYPES)[number];

export const CATEGORY_TO_CONTENT: Record<Category, Exclude<ContentType, "All"> | "Manhua"> = {
  manga: "Manga",
  manhwa: "Manhwa",
  manhua: "Manhua",
};

export const CONTENT_TO_CATEGORY: Record<Exclude<ContentType, "All">, Category> = {
  Manga: "manga",
  Manhwa: "manhwa",
  Comics: "manhua",
};

/** Expand a UI content-type selection into the provider categories it covers. */
export function contentToCategories(type: ContentType): Category[] | undefined {
  if (type === "All") return undefined;
  return [CONTENT_TO_CATEGORY[type]];
}
