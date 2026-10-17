// UI-facing content model + shared constants.
//
// The `Manga` type is the single shape every component consumes. It is now
// populated from real providers via the normalization bridge
// (providers/normalize.ts) — NOT from a hardcoded mock catalog. Fields a
// provider cannot supply are optional and render as an explicit unknown
// ("—"/hidden) instead of a fabricated value.

import type { ContentType } from "./providers/category";

export const GENRE_LIST = [
  "Adult", "Action", "Adaptation", "Adventure", "Anime", "Comedy", "Completed",
  "Cooking", "Crime", "Crossdressin", "Delinquents", "Demons", "Detective",
  "Drama", "Ecchi", "Fantasy", "Game", "Ghosts", "Hentai", "Harem", "Historical",
  "Horror", "Isekai", "Josei", "Magic", "Magical", "Manhua", "Manhwa",
  "Martial Arts", "Mature", "Mecha", "Medical", "Military", "Moder", "Monsters",
  "Music", "Mystery", "Office Workers", "One shot", "Philosophical", "Police",
  "Reincarnation", "Reverse", "Reverse harem", "Romance", "Royal family", "Smut",
  "School Life", "Sci-fi", "Seinen", "Shoujo", "Shoujo Ai", "Shounen",
  "Shounen Ai", "Slice of Life", "Sports", "Super power", "Superhero",
  "Supernatural", "Survival", "Thriller", "Time Travel", "Tragedy", "Vampire",
  "Villainess", "Webtoons", "Yaoi", "Yuri", "Zombies",
] as const;

export const STATUS_OPTIONS = ["All", "Completed", "In Process", "Paused"] as const;

export const SORT_OPTIONS = [
  "Latest Update",
  "Hot",
  "New",
  "Top All",
  "Top Month",
  "Top Week",
  "Top Day",
  "Saved",
  "No. of Chapter",
] as const;

export type Status = (typeof STATUS_OPTIONS)[number];
export type SortOption = (typeof SORT_OPTIONS)[number];

export const CONTENT_TYPE_OPTIONS = ["All", "Manga", "Manhwa", "Manhua"] as const;
export type { ContentType };

export type Manga = {
  /** Stable app slug used in URLs; provider-backed and safe to persist. */
  slug: string;
  title: string;
  /** Real provider rating on a 0..5 scale, or null when unavailable. */
  rating: number | null;
  /** Number of readable chapters; 0 hides the Collection section. */
  chapters: number;
  /** Real popularity count formatted compactly, or "" when unavailable. */
  views: string;
  /** Cover image URL; may be "" when the provider has no cover. */
  cover: string;
  colored?: boolean;
  /** Page count of the first/most-recent chapter, when known. */
  pages?: number;
  genres?: string[];
  status?: Status;
  contentType?: Exclude<ContentType, "All">;
  artist?: string;
  circle?: string;
  subtitle?: string;
  language?: string;
  parody?: string;
  releaseYear?: number;
  /** Whole days since the last chapter dropped — lower is more recent. */
  updatedDays?: number;
  /** True when the source can actually serve readable pages. */
  readable?: boolean;
  /** Attribution link back to the provider page. */
  sourceUrl?: string;
  /** True when a listed title could not be resolved (provider removed it). */
  unavailable?: boolean;
};

export type TrendingManga = Manga & { rank: number };

/** "1.2M" / "346k" / "89k" -> raw number, for sorting by popularity. */
export function parseViews(views: string): number {
  if (!views) return 0;
  const match = views.trim().match(/^([\d.]+)\s*([kKmM])?$/);
  if (!match) return 0;
  const value = Number(match[1]);
  const unit = match[2]?.toLowerCase();
  if (unit === "m") return value * 1_000_000;
  if (unit === "k") return value * 1_000;
  return value;
}

/** Stable rating fallback used by cards when a provider rating is missing. */
export function displayRating(m: Manga): string {
  return m.rating != null && m.rating > 0 ? m.rating.toFixed(1) : "—";
}
