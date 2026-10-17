"use strict";
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
Object.defineProperty(exports, "__esModule", { value: true });
exports.DEFAULT_ADULT_POLICY = void 0;
exports.isEligible = isEligible;
exports.classifyMangaDex = classifyMangaDex;
exports.classifyAniList = classifyAniList;
exports.classifyDynasty = classifyDynasty;
exports.inferOrigin = inferOrigin;
/**
 * Default policy for READHENTAI 18+: adult + mature are eligible; general
 * audience and unknown are excluded (conservative).
 */
exports.DEFAULT_ADULT_POLICY = {
    allowConfirmedAdult: true,
    allowMature: true,
    allowUnknown: false,
};
/** Whether a classification may enter the catalogue under a policy. */
function isEligible(classification, policy = exports.DEFAULT_ADULT_POLICY) {
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
const MANGADEX_RATING_MAP = {
    safe: "general_audience",
    suggestive: "mature_non_explicit",
    erotica: "mature_non_explicit",
    pornographic: "confirmed_adult",
};
function classifyMangaDex(contentRating, origin = "manga") {
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
function classifyAniList(isAdult, origin = "manga") {
    const classification = isAdult ? "confirmed_adult" : "general_audience";
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
function classifyDynasty(tagNames, origin = "manga") {
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
/* ------------------------------------------------------------------ */
/* Content-origin heuristics (kept separate from age)                 */
/* ------------------------------------------------------------------ */
/** Derive origin from country/demographic/tag hints. Never from age rating. */
function inferOrigin(hints) {
    const tags = (hints.tags ?? []).map((t) => t.toLowerCase());
    if (tags.includes("doujinshi") || tags.includes("doujin"))
        return "doujinshi";
    if (tags.includes("manhwa") || (hints.countryOfOrigin ?? "").toUpperCase() === "KR")
        return "manhwa";
    if (tags.includes("manhua") || ["CN", "TW", "HK"].includes((hints.countryOfOrigin ?? "").toUpperCase()))
        return "manhua";
    if (tags.includes("manga") || (hints.countryOfOrigin ?? "").toUpperCase() === "JP")
        return "manga";
    return "manga"; // conservative default for the primary category
}
