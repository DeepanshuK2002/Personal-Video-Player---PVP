import { describe, expect, it } from 'vitest';
import { concatTwoColorMatrices } from './color_matrix';
import { DEFAULT_BRIGHTNESS, DEFAULT_CONTRAST } from './constants';
import { ColorMatricesTypes, getColorMatrix, getPageColorMatrix } from './matrix';

// The colour matrix a page is rendered with drives every preview, export and
// PDF render. These tests pin which matrix wins when a page has a filter, a
// per-page brightness/contrast, or both.

const MATRIX_LENGTH = 20;

describe('getColorMatrix', () => {
    it('returns a 20-entry matrix for a known filter', () => {
        expect(getColorMatrix('grayscale')).toHaveLength(MATRIX_LENGTH);
    });

    it('returns null for an unknown filter instead of throwing', () => {
        expect(getColorMatrix('does-not-exist' as any)).toBeNull();
    });

    it('passes arguments through to the filter function', () => {
        const withDefaults = getColorMatrix('brightnessAndContrast', DEFAULT_BRIGHTNESS, DEFAULT_CONTRAST);
        const withBrightness = getColorMatrix('brightnessAndContrast', 0.5, DEFAULT_CONTRAST);
        expect(withBrightness).not.toEqual(withDefaults);
    });
});

describe('ColorMatricesTypes', () => {
    it('exposes the user-facing filters in the intended order', () => {
        expect(ColorMatricesTypes.map((entry) => entry.id)).toEqual(['normal', 'grayscale', 'bw', 'sepia', 'invert', 'polaroid']);
    });

    it('carries the filter function alongside the id', () => {
        ColorMatricesTypes.forEach((entry) => {
            expect(entry.fn, `${entry.id} has no fn`).toBeTypeOf('function');
        });
    });
});

describe('getPageColorMatrix', () => {
    it('returns undefined when there is no page', () => {
        expect(getPageColorMatrix(undefined as any)).toBeUndefined();
    });

    it('returns null for a page with no filter and default adjustments', () => {
        const page: any = { brightness: DEFAULT_BRIGHTNESS, contrast: DEFAULT_CONTRAST };
        expect(getPageColorMatrix(page)).toBeNull();
    });

    it('uses the matrix stored on the page when present', () => {
        // An explicit matrix on the page wins over its colorType.
        const stored = new Array(MATRIX_LENGTH).fill(0);
        const page: any = { colorMatrix: stored, colorType: 'grayscale' };
        expect(getPageColorMatrix(page)).toBe(stored);
    });

    it('falls back to the page colorType when no matrix is stored', () => {
        expect(getPageColorMatrix({ colorType: 'grayscale' } as any)).toEqual(getColorMatrix('grayscale'));
    });

    it('lets a forced colour type override both the stored matrix and colorType', () => {
        const page: any = { colorMatrix: new Array(MATRIX_LENGTH).fill(0), colorType: 'grayscale' };
        expect(getPageColorMatrix(page, 'sepia')).toEqual(getColorMatrix('sepia'));
    });

    it('composes brightness over the filter', () => {
        const page: any = { colorType: 'grayscale', brightness: 0.5, contrast: DEFAULT_CONTRAST };
        const expected = concatTwoColorMatrices(getColorMatrix('brightnessAndContrast', 0.5, DEFAULT_CONTRAST), getColorMatrix('grayscale'));
        expect(getPageColorMatrix(page)).toEqual(expected);
    });

    it('composes contrast over the filter', () => {
        const page: any = { colorType: 'grayscale', brightness: DEFAULT_BRIGHTNESS, contrast: 2 };
        const expected = concatTwoColorMatrices(getColorMatrix('brightnessAndContrast', DEFAULT_BRIGHTNESS, 2), getColorMatrix('grayscale'));
        expect(getPageColorMatrix(page)).toEqual(expected);
    });

    it('returns the adjustment matrix alone when the page has no filter', () => {
        const page: any = { brightness: 0.5, contrast: DEFAULT_CONTRAST };
        expect(getPageColorMatrix(page)).toEqual(getColorMatrix('brightnessAndContrast', 0.5, DEFAULT_CONTRAST));
    });

    it('ignores brightness and contrast left at their defaults', () => {
        const page: any = { colorType: 'sepia', brightness: DEFAULT_BRIGHTNESS, contrast: DEFAULT_CONTRAST };
        expect(getPageColorMatrix(page)).toEqual(getColorMatrix('sepia'));
    });

    it('ignores NaN adjustments rather than producing a NaN matrix', () => {
        const page: any = { colorType: 'sepia', brightness: NaN, contrast: NaN };
        expect(getPageColorMatrix(page)).toEqual(getColorMatrix('sepia'));
    });

    it('lets explicit brightness and contrast arguments override the page values', () => {
        const page: any = { colorType: 'grayscale', brightness: 0.1, contrast: 3 };
        const expected = concatTwoColorMatrices(getColorMatrix('brightnessAndContrast', 0.5, 2), getColorMatrix('grayscale'));
        expect(getPageColorMatrix(page, undefined, 0.5, 2)).toEqual(expected);
    });

    it('still produces a 20-entry matrix once adjustments are composed', () => {
        const page: any = { colorType: 'grayscale', brightness: 0.5, contrast: 2 };
        expect(getPageColorMatrix(page)).toHaveLength(MATRIX_LENGTH);
    });
});
