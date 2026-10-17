import { beforeEach, describe, expect, it, vi } from 'vitest';

// vitest.setup.ts stubs the whole plugin so that translation lookups echo their key. The
// plural resolution is exactly what is under test here, so the real implementation is used.
vi.unmock('@nativescript-community/l');

import { lcp, loadLocaleJSON, lp, pluralKey, setPluralLocale } from '@nativescript-community/l';

// mirrors the shape of app/i18n/*.json after the plural migration
const LOCALE = {
    selected_one: '%1$s selected',
    selected_other: '%1$s selected',
    documents_count_one: '%1$s document',
    documents_count_other: '%1$s documents',
    // a russian style locale defining the extra CLDR forms weblate generates
    pages_one: '%1$s страница',
    pages_few: '%1$s страницы',
    pages_many: '%1$s страниц',
    pages_other: '%1$s страницы',
    // a key with no plural forms at all
    cancel: 'cancel',
    // the count selects the form but is not the printed argument
    ocr_computing_document_one: 'detecting text in document (%1$s%%)',
    ocr_computing_document_other: 'detecting text in documents (%1$s%%)'
};

describe('plural localization', () => {
    beforeEach(() => {
        loadLocaleJSON('en', LOCALE, null);
    });

    it('selects the singular form for a count of one', () => {
        expect(lp('documents_count', 1)).toBe('1 document');
    });

    it('selects the plural form for any other count', () => {
        expect(lp('documents_count', 0)).toBe('0 documents');
        expect(lp('documents_count', 2)).toBe('2 documents');
    });

    it('passes the count as the first format argument', () => {
        expect(lp('selected', 3)).toBe('3 selected');
    });

    it('capitalizes with lcp', () => {
        expect(lcp('documents_count', 2)).toBe('2 documents');
        expect(lcp('ocr_computing_document', 2, 40)).toBe('Detecting text in documents (2%)');
    });

    it('falls back to the bare key when it has no plural forms', () => {
        expect(pluralKey('cancel', 2)).toBe('cancel');
        expect(lp('cancel', 2)).toBe('cancel');
    });

    it('falls back to the other form when the CLDR category is missing', () => {
        setPluralLocale('ru');
        // russian has no `two` category for 2, but polish-like `few`: documents_count only
        // defines one/other so `few` must degrade to `_other`
        expect(pluralKey('documents_count', 2)).toBe('documents_count_other');
    });

    it('uses the extra CLDR categories when the locale defines them', () => {
        setPluralLocale('ru');
        expect(pluralKey('pages', 1)).toBe('pages_one');
        expect(pluralKey('pages', 3)).toBe('pages_few');
        expect(pluralKey('pages', 5)).toBe('pages_many');
    });

    it('applies the plural rules of the language subtag only', () => {
        setPluralLocale('fr_CA');
        // french treats 0 and 1 as singular
        expect(pluralKey('documents_count', 0)).toBe('documents_count_one');
        expect(pluralKey('documents_count', 2)).toBe('documents_count_other');
    });

    it('falls back to english rules for an unknown language', () => {
        setPluralLocale('zz');
        expect(pluralKey('documents_count', 0)).toBe('documents_count_other');
        expect(pluralKey('documents_count', 1)).toBe('documents_count_one');
    });

    it('selects on the count even when the count is not the printed argument', () => {
        expect(lp(pluralKey('ocr_computing_document', 1), 42)).toBe('detecting text in document (42%)');
        expect(lp(pluralKey('ocr_computing_document', 3), 42)).toBe('detecting text in documents (42%)');
    });
});
