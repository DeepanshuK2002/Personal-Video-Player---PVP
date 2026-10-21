// Centralized adult-content classification + eligibility.
//
// READHENTAI is an adult-oriented platform, so classification is a first-class
// concern that must live in the DATA PIPELINE (not the UI). Every provider
// adapter produces a provider-native maturity signal; this module maps it onto a
// single normalized taxonomy and applies the platform eligibility policy.
//
// Two orthogonal concepts are kept separate, per the platform rules:
//   - Content ORIGIN:    manga | manhwa | manhua | doujinshi | other
//   - Age CLASSIFICATION: confirmed_adult | mature_non_explicit |
//                         general_audience | unknown
// An adult Korean comic is still manhwa. An unknown classification is NEVER
// treated as confirmed adult (conservative by default).

/** Where the work originates — independent of how explicit it is. */
export type ContentOrigin = "manga" | "manhwa" | "manhua" | "doujinshi" | "other";

/** Normalized age classification, derived from provider-native signals. */
export type AdultClassification =
  | "confirmed_adult"
  | "mature_non_explicit"
  | "general_audience"
  | "unknown";

export interface AdultContentMetadata {
  classification: AdultClassification;
  isAdult: boolean;
  isExplicit: boolean;
  origin: ContentOrigin;
  /** The provider field/value the decision was based on, for diagnostics. */
  sourceProvider: string;
  sourceClassification?: string;
  /** Human-readable reason, surfaced in exclusion diagnostics. */
  reason?: string;
}

/** Platform eligibility policy for what may enter the production catalogue. */
export interface AdultPolicy {
  /** Include works classified confirmed_adult. */
  allowConfirmedAdult: boolean;
  /** Include mature_non_explicit (erotica / suggestive). */
  allowMature: boolean;
  /** Include works whose classification could not be established. */
  allowUnknown: boolean;
}

/**
 * Default policy for READHENTAI 18+: adult + mature are eligible; general
 * audience and unknown are excluded (conservative).
 */
export const DEFAULT_ADULT_POLICY: AdultPolicy = {
  allowConfirmedAdult: true,
  allowMature: true,
  allowUnknown: false,
};

/** Whether a classification may enter the catalogue under a policy. */
export function isEligible(
  classification: AdultClassification,
  policy: AdultPolicy = DEFAULT_ADULT_POLICY,
): boolean {
  switch (classification) {
    case "confirmed_adult":
      return policy.allowConfirmedAdult;
    case "mature_non_explicit":
      return policy.allowMature;
    case "general_audience":
      return false; // never eligible for the adult catalogue
    case "unknown":
      return policy.allowUnknown;
  }
}

/* ------------------------------------------------------------------ */
/* Provider-native signals                                            */
/* ------------------------------------------------------------------ */

/**
 * MangaDex exposes an explicit `contentRating` on every title. This is the most
 * reliable maturity signal of any integrated provider.
 *   safe       -> general_audience
 *   suggestive -> mature_non_explicit
 *   erotica    -> mature_non_explicit   (borderline; treated as mature, not explicit)
 *   pornographic -> confirmed_adult
 */
const MANGADEX_RATING_MAP: Record<string, AdultClassification> = {
  safe: "general_audience",
  suggestive: "mature_non_explicit",
  erotica: "mature_non_explicit",
  pornographic: "confirmed_adult",
};

export function classifyMangaDex(
  contentRating: string | null | undefined,
  origin: ContentOrigin = "manga",
): AdultContentMetadata {
  const key = (contentRating ?? "").toLowerCase();
  const classification = MANGADEX_RATING_MAP[key] ?? "unknown";
  return {
    classification,
    isAdult: classification === "confirmed_adult",
    isExplicit: classification === "confirmed_adult",
    origin,
    sourceProvider: "mangadex",
    sourceClassification: contentRating ?? undefined,
    reason: contentRating
      ? `mangadex.contentRating=${contentRating}`
      : "mangadex.contentRating missing",
  };
}

/**
 * AniList flags hentai/mature works with a single boolean `isAdult`. It does not
 * distinguish mature from explicit, so confirmed_adult maps to isAdult=true and
 * everything else is general_audience (AniList's catalogue is otherwise SFW).
 */
export function classifyAniList(
  isAdult: boolean | undefined,
  origin: ContentOrigin = "manga",
): AdultContentMetadata {
  const classification: AdultClassification = isAdult ? "confirmed_adult" : "general_audience";
  return {
    classification,
    isAdult: Boolean(isAdult),
    isExplicit: Boolean(isAdult),
    origin,
    sourceProvider: "anilist",
    sourceClassification: isAdult ? "isAdult=true" : "isAdult=false",
    reason: "anilist.isAdult",
  };
}

/**
 * Dynasty exposes no boolean maturity flag. Its catalogue is predominantly
 * Yuri/GL; explicit works, when present, are tagged. Because we cannot establish
 * maturity reliably from metadata alone, the conservative default is `unknown`
 * unless a known adult tag is present.
 */
const DYNASTY_ADULT_TAGS = new Set([
  "nsfw",
  "hentai",
  "smut",
  "erotica",
  "adult",
  "explicit",
  "r18",
  "r-18",
]);

export function classifyDynasty(
  tagNames: string[],
  origin: ContentOrigin = "manga",
): AdultContentMetadata {
  const matched = tagNames.filter((t) => DYNASTY_ADULT_TAGS.has(t.toLowerCase()));
  if (matched.length > 0) {
    return {
      classification: "confirmed_adult",
      isAdult: true,
      isExplicit: true,
      origin,
      sourceProvider: "dynasty",
      sourceClassification: matched.join(","),
      reason: `dynasty adult tags: ${matched.join(",")}`,
    };
  }
  return {
    classification: "unknown",
    isAdult: false,
    isExplicit: false,
    origin,
    sourceProvider: "dynasty",
    reason: "dynasty exposes no reliable maturity flag; no adult tag matched",
  };
}

/**
 * Hentairead.io is an adult-only hentai catalogue (manga / manhwa / manhua).
 * Every title on the platform is explicit by definition, so the classification
 * is always `confirmed_adult`; only the ORIGIN (manga/manhwa/manhua) varies and
 * is supplied by the caller from the scraped genre/category.
 */
export function classifyHentairead(origin: ContentOrigin): AdultContentMetadata {
  return {
    classification: "confirmed_adult",
    isAdult: true,
    isExplicit: true,
    origin,
    sourceProvider: "hentairead",
    sourceClassification: "hentairead.io (adult-only catalogue)",
    reason: "hentairead.io is an adult-only hentai source",
  };
}

/**
 * Hentai18.net is an adult-only manga/manhwa/doujinshi catalogue.
 * Every title is explicit by definition.
 */
export function classifyHentai18(origin: ContentOrigin = "manga"): AdultContentMetadata {
  return {
    classification: "confirmed_adult",
    isAdult: true,
    isExplicit: true,
    origin,
    sourceProvider: "hentai18",
    sourceClassification: "hentai18.net (adult-only catalogue)",
    reason: "hentai18.net is an adult-only hentai catalogue",
  };
}

/**
 * Enma is a multi-source library exposed through the local sidecar
 * (`services/enma-api`); the sidecar reports which Enma source served a record.
 * Classification therefore depends on that source:
 *   - nhentai: adult-only doujinshi catalogue (official API v2) -> confirmed_adult.
 *   - anything else (mangadex, manganato, …): Enma surfaces no maturity flag for
 *     those sources here, so the honest answer is `unknown` — never promoted to
 *     adult by the mere fact of coming from Enma.
 */
export function classifyEnma(
  source: string | null | undefined,
  origin: ContentOrigin = "doujinshi",
): AdultContentMetadata {
  if (source === "nhentai") {
    return {
      classification: "confirmed_adult",
      isAdult: true,
      isExplicit: true,
      origin,
      sourceProvider: "enma",
      sourceClassification: "nhentai (adult-only catalogue, official API v2)",
      reason: "nhentai.net is an adult-only doujinshi catalogue",
    };
  }
  return {
    classification: "unknown",
    isAdult: false,
    isExplicit: false,
    origin,
    sourceProvider: "enma",
    sourceClassification: source ? `enma source: ${source}` : "enma source: (not reported)",
    reason: source
      ? `enma source '${source}' exposes no maturity signal`
      : "sidecar did not report which Enma source served this record",
  };
}

/* ------------------------------------------------------------------ */
/* Content-origin heuristics (kept separate from age)                 */
/* ------------------------------------------------------------------ */

/** Derive origin from country/demographic/tag hints. Never from age rating. */
export function inferOrigin(hints: {
  countryOfOrigin?: string | null;
  demographic?: string | null;
  tags?: string[];
}): ContentOrigin {
  const tags = (hints.tags ?? []).map((t) => t.toLowerCase());
  if (tags.includes("doujinshi") || tags.includes("doujin")) return "doujinshi";
  if (tags.includes("manhwa") || (hints.countryOfOrigin ?? "").toUpperCase() === "KR") return "manhwa";
  if (tags.includes("manhua") || ["CN", "TW", "HK"].includes((hints.countryOfOrigin ?? "").toUpperCase()))
    return "manhua";
  if (tags.includes("manga") || (hints.countryOfOrigin ?? "").toUpperCase() === "JP") return "manga";
  return "manga"; // conservative default for the primary category
}
