"use strict";
// Canonical chapter reconciliation.
//
// THE critical feature: a comic's chapters may exist across several eligible
// providers with different coverage. This module merges them into ONE unified,
// stably-ordered catalogue where each canonical chapter retains every known
// source version — so a chapter present only on a secondary provider still
// appears in the correct position, and a chapter present on several providers
// keeps all of its versions for source selection / fallback.
//
// Matching rules (deliberately conservative):
//   - Same confirmed series + same language + same chapter number -> merged.
//   - Different languages are NEVER merged.
//   - Chapter numbers are parsed decimal-aware: "10.5" stays 10.5, never 105.
//   - Numberless specials are matched by (type + normalized label), not by
//     number, and are kept separate when identity is uncertain.
//   - Original provider labels and IDs are always preserved.
Object.defineProperty(exports, "__esModule", { value: true });
exports.parseChapterLabel = parseChapterLabel;
exports.assignSortKeys = assignSortKeys;
exports.reconcileChapters = reconcileChapters;
/* ------------------------------------------------------------------ */
/* Chapter label parsing                                               */
/* ------------------------------------------------------------------ */
/**
 * Parse a provider chapter label into (number, type, volume).
 * The original label is always preserved by the caller — this only extracts
 * ordering metadata. Returns null number when the label carries no number.
 *
 * Tested against: "Chapter 12", "Ch. 12.5", "Vol. 3 Ch. 12", "12.5",
 * "Oneshot", "Prologue", "Extra #2", "Side Story", "Untitled".
 */
function parseChapterLabel(label) {
    const raw = (label ?? "").trim();
    const lower = raw.toLowerCase();
    // Volume, if present ("Vol. 3", "Volume 3").
    const volMatch = lower.match(/\b(?:vol|volume)\.?\s*(\d+(?:\.\d+)?)/);
    const volume = volMatch ? volMatch[1] : null;
    // Explicit chapter number. Anchored to a "chapter/ch/" word OR a bare number
    // that is the whole label. Decimal-aware so "10.5" -> 10.5 (never 105).
    const numMatch = lower.match(/\b(?:chapter|ch)\.?\s*(\d+(?:\.\d+)?)/) ??
        raw.match(/^\s*(\d+(?:\.\d+)?)\s*$/);
    const number = numMatch ? Number.parseFloat(numMatch[1]) : null;
    const hasNumber = number !== null && Number.isFinite(number);
    // Type classification from keywords (used for ordering + numberless matching).
    let type = hasNumber ? "main" : "unknown";
    if (/\boneshot\b/.test(lower))
        type = "oneshot";
    else if (/\bprologue\b/.test(lower))
        type = "prologue";
    else if (/\bepilogue\b/.test(lower))
        type = "epilogue";
    else if (/\bside\s*story\b|\bsidestory\b/.test(lower))
        type = "side_story";
    else if (/\bextra\b|\bbonus\b|\bspecial\b/.test(lower))
        type = "extra";
    else if (hasNumber && !/\b(?:chapter|ch)\b/.test(lower)) {
        // A bare decimal like "12.5" with no keyword is still a main chapter.
        type = "main";
    }
    return { number: hasNumber ? number : null, type, volume };
}
/** Normalize a label for numberless identity matching (case/punctuation-insensitive). */
function normalizeLabel(label) {
    return (label ?? "")
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, " ")
        .trim();
}
/* ------------------------------------------------------------------ */
/* Ordering                                                            */
/* ------------------------------------------------------------------ */
/**
 * Relative tier for chapters that carry NO number. Numbered chapters always
 * order by their own value; these tiers place numberless specials sensibly
 * around them without inventing a number.
 *
 * prologue  -> before numbered content
 * (numbered)-> by number
 * epilogue  -> after numbered content
 * side story/extra/oneshot/unknown -> after epilogue, in provider order
 */
const NUMBERTYPESS_TIER = {
    prologue: -1,
    main: 0,
    special: 0,
    epilogue: 1,
    side_story: 2,
    extra: 3,
    oneshot: 4,
    unknown: 5,
};
/**
 * Assign a deterministic sortKey to a set of parsed chapters.
 * Numbered chapters use their number directly (so 10 < 10.5 < 11). Numberless
 * chapters are placed by type tier relative to the numbered range, preserving
 * their original input order within the tier. Fully deterministic for a given
 * snapshot.
 */
function assignSortKeys(items) {
    const numbers = items.filter((i) => i.number !== null).map((i) => i.number);
    const minN = numbers.length ? Math.min(...numbers) : 0;
    const maxN = numbers.length ? Math.max(...numbers) : 0;
    return items.map((item) => {
        if (item.number !== null)
            return item.number; // numeric ordering dominates
        const tier = NUMBERTYPESS_TIER[item.type];
        if (tier < 0) {
            // Before all numbered content; keep input order among prologues.
            return minN - 1 + item.inputIndex * 0.0001;
        }
        // After numbered content, grouped by tier, preserving input order.
        return maxN + 1 + tier + item.inputIndex * 0.0001;
    });
}
function toSourceVersion(c, number, volume) {
    return {
        providerId: c.providerId,
        providerSeriesId: c.providerSeriesId,
        providerChapterId: c.providerChapterId,
        chapterNumber: number !== null ? String(number) : null,
        volumeNumber: c.volumeNumber ?? volume,
        title: c.title ?? null,
        language: c.language || "und",
        releaseGroup: c.releaseGroup ?? null,
        sourceUrl: c.sourceUrl ?? null,
        pageAccessCapability: c.pageAccessCapability,
        pageCount: c.pageCount ?? null,
        publishedAt: c.publishedAt ?? null,
    };
}
/**
 * Merge chapter records from one or more providers into a unified catalogue.
 *
 * @param seriesId  stable canonical series id stamped on every result
 * @param inputs    chapters from all eligible providers for that series
 * @returns one CanonicalChapter per distinct (language, identity), each holding
 *          every source version, sorted into a stable reading order.
 *
 * Merge key:
 *   - numbered:   (language, chapterNumber)
 *   - numberless: (language, type, normalizedLabel) — kept separate when the
 *                 label is empty/ambiguous rather than force-merged.
 */
function reconcileChapters(seriesId, inputs) {
    const buckets = new Map();
    let index = 0;
    for (const c of inputs) {
        const language = c.language || "und";
        const parsed = parseChapterLabel(c.label);
        const number = parsed.number;
        const volume = c.volumeNumber ?? parsed.volume;
        // Identity key: language-qualified. Numbered chapters merge by number;
        // numberless ones merge only by (type + normalized label), and only when
        // the label is meaningful — ambiguous/empty labels stay separate.
        let key;
        if (number !== null) {
            key = `${language}::num::${number}`;
        }
        else {
            const norm = normalizeLabel(c.label);
            key = norm ? `${language}::${parsed.type}::${norm}` : `${language}::${parsed.type}::#idx${index}`;
        }
        const existing = buckets.get(key);
        if (existing) {
            existing.versions.push(toSourceVersion(c, number, volume));
        }
        else {
            buckets.set(key, {
                key,
                language,
                number,
                type: number !== null ? parsed.type : parsed.type,
                label: c.label,
                versions: [toSourceVersion(c, number, volume)],
                inputIndex: index,
            });
        }
        index++;
    }
    const list = [...buckets.values()];
    // Stable deterministic ordering across the whole set (mixed languages share
    // one ordering pass so the catalogue is stable regardless of provider order).
    const sortKeys = assignSortKeys(list.map((b) => ({ number: b.number, type: b.type, inputIndex: b.inputIndex })));
    const chapters = list.map((b, i) => ({
        id: `${seriesId}:ch:${b.key}`,
        seriesId,
        chapterNumber: b.number,
        // Preserve the first provider's label verbatim as the canonical label.
        label: b.label,
        volumeNumber: b.versions[0]?.volumeNumber ?? null,
        title: b.versions.find((v) => v.title)?.title ?? null,
        language: b.language,
        chapterType: b.type,
        sourceVersions: b.versions,
        sortKey: sortKeys[i],
    }));
    // Deterministic sort: sortKey, then label, then id (total order, no ties).
    chapters.sort((a, b) => a.sortKey !== b.sortKey
        ? a.sortKey - b.sortKey
        : a.label.localeCompare(b.label) || a.id.localeCompare(b.id));
    return chapters;
}
