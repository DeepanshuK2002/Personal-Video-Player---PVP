import { describe, expect, it } from 'vitest';
import { buildExportImageNames, deduplicateFilenames } from './exportUtils';
import { cleanFilename, getFileNameForDocument, getFormatedDateForFilename } from './utils.common';

describe('deduplicateFilenames', () => {
    it('returns the list unchanged when all names are unique', () => {
        expect(deduplicateFilenames(['a', 'b', 'c'])).toEqual(['a', 'b', 'c']);
    });

    it('returns an empty array for empty input', () => {
        expect(deduplicateFilenames([])).toEqual([]);
    });

    it('appends _001 to the second occurrence in a pair of duplicates', () => {
        expect(deduplicateFilenames(['ts1234', 'ts1234'])).toEqual(['ts1234', 'ts1234_001']);
    });

    it('handles a run of three identical names', () => {
        expect(deduplicateFilenames(['ts1234', 'ts1234', 'ts1234'])).toEqual(['ts1234', 'ts1234_001', 'ts1234_002']);
    });

    it('resets the counter for each new run', () => {
        expect(deduplicateFilenames(['a', 'a', 'b', 'b'])).toEqual(['a', 'a_001', 'b', 'b_001']);
    });

    it('pads the suffix to three digits', () => {
        const names = Array(11).fill('x');
        const result = deduplicateFilenames(names);
        expect(result[10]).toBe('x_010');
    });

    it('does not rename non-consecutive duplicates', () => {
        // 'a' appears at index 0 and 2, but they are not adjacent
        expect(deduplicateFilenames(['a', 'b', 'a'])).toEqual(['a', 'b', 'a']);
    });

    it('handles a single entry without modification', () => {
        expect(deduplicateFilenames(['only'])).toEqual(['only']);
    });

    it('does not mutate the input array', () => {
        const input = ['x', 'x'];
        deduplicateFilenames(input);
        expect(input).toEqual(['x', 'x']);
    });
});

// ─── buildExportImageNames ────────────────────────────────────────────────────
//
// End-to-end regression coverage for the "rename documents on export" feature:
// creation dates -> user filename format -> forbidden-character sanitising ->
// collision suffixes. A change to any link in that chain must break a test here.

describe('buildExportImageNames', () => {
    // Two pages captured within the same second: with a second-resolution
    // format they collide, which is exactly what the suffixing exists to solve.
    const FIRST = new Date(2024, 2, 15, 10, 30, 0).getTime();
    const SECOND = FIRST + 400;

    it('formats each creation date with the given format', () => {
        expect(buildExportImageNames([FIRST], 'YYYY-MM-DD')).toEqual(['2024-03-15']);
    });

    it('suffixes pages that collide after formatting', () => {
        expect(buildExportImageNames([FIRST, SECOND], 'YYYY-MM-DD')).toEqual(['2024-03-15', '2024-03-15_001']);
    });

    it('keeps distinct dates untouched', () => {
        const nextDay = FIRST + 24 * 3600 * 1000;
        expect(buildExportImageNames([FIRST, nextDay], 'YYYY-MM-DD')).toEqual(['2024-03-15', '2024-03-16']);
    });

    it('sanitises characters the format would otherwise put in a filename', () => {
        // A format containing ':' and ' ' must never reach the filesystem raw.
        const [name] = buildExportImageNames([FIRST], 'YYYY-MM-DD HH:mm');
        expect(name).not.toMatch(/[:\s]/);
        expect(name).toBe('2024-03-15_10_30');
    });

    it('never produces two identical names for a batch of same-second pages', () => {
        const dates = [FIRST, FIRST + 1, FIRST + 2, FIRST + 3];
        const names = buildExportImageNames(dates, 'YYYY-MM-DD_HH-mm-ss');
        expect(new Set(names).size).toBe(dates.length);
    });

    it('falls back to the stored "timestamp" format when none is given', () => {
        // ApplicationSettings is mocked to return defaults, so the configured
        // format resolves to FILENAME_DATE_FORMAT ('timestamp').
        expect(buildExportImageNames([FIRST])).toEqual([String(FIRST)]);
    });

    it('returns an empty list for an empty export', () => {
        expect(buildExportImageNames([])).toEqual([]);
    });
});

// ─── export filename pipeline ─────────────────────────────────────────────────
//
// Guards the naming rules the export screen relies on, using the real
// production helpers rather than a copy of their logic.

describe('export filename pipeline', () => {
    it('uses the document name (sanitised) for a single named export', () => {
        const document: any = { name: 'Invoice: Q1/2024' };
        expect(getFileNameForDocument(document, true)).toBe('Invoice__Q1_2024');
    });

    it('falls back to a date-based name when the document has no name', () => {
        const timestamp = new Date(2024, 2, 15).getTime();
        expect(getFileNameForDocument({ name: '' } as any, true, timestamp, 'YYYY-MM-DD')).toBe('2024-03-15');
    });

    it('produces names that survive a round-trip through cleanFilename', () => {
        // Sanitising an already-sanitised name must be a no-op, otherwise
        // filenames would drift each time they pass through the export path.
        const once = getFileNameForDocument({ name: 'a b:c/d' } as any, true);
        expect(cleanFilename(once)).toBe(once);
    });

    it('keeps the date format setting authoritative over the document name when disabled', () => {
        const document: any = { name: 'Should Be Ignored' };
        expect(getFileNameForDocument(document, false, new Date(2024, 0, 2).getTime(), 'YYYY-MM-DD')).toBe('2024-01-02');
    });

    it('leaves an already-safe name completely unchanged', () => {
        expect(getFormatedDateForFilename(new Date(2024, 0, 2).getTime(), 'YYYY-MM-DD')).toBe('2024-01-02');
    });
});
