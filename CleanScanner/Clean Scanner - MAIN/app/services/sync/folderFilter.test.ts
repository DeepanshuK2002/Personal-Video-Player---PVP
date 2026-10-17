import { describe, expect, it } from 'vitest';
import { type FolderedDocument, filterBySyncFolders, filterPagedBySyncFolders, syncsAllFolders } from './folderFilter';

type TestDocument = FolderedDocument & { id: string };

// Per-sync-service folder filtering. The rules encoded here are behavioural
// decisions, not implementation details: an unrestricted service syncs
// everything, and a restricted one skips documents outside its folders —
// including documents that live in no folder at all.

const inbox: TestDocument = { id: 'inbox', folders: [1] };
const archive: TestDocument = { id: 'archive', folders: [2] };
const both: TestDocument = { id: 'both', folders: [1, 2] };
const unfiled: TestDocument = { id: 'unfiled', folders: [] };
const noFolderField: TestDocument = { id: 'no-field' };

const documents: TestDocument[] = [inbox, archive, both, unfiled, noFolderField];

describe('syncsAllFolders', () => {
    it('treats undefined as no restriction', () => {
        expect(syncsAllFolders(undefined)).toBe(true);
    });

    it('treats an empty list as no restriction rather than "sync nothing"', () => {
        expect(syncsAllFolders([])).toBe(true);
    });

    it('reports a restriction once at least one folder is selected', () => {
        expect(syncsAllFolders([1])).toBe(false);
    });
});

describe('filterBySyncFolders', () => {
    it('returns every document when no folder filter is set', () => {
        expect(filterBySyncFolders(undefined, documents)).toEqual(documents);
        expect(filterBySyncFolders([], documents)).toEqual(documents);
    });

    it('returns the same array reference when unrestricted', () => {
        // The unfiltered path must stay allocation-free for large libraries.
        expect(filterBySyncFolders(undefined, documents)).toBe(documents);
    });

    it('keeps only documents inside the selected folder', () => {
        expect(filterBySyncFolders([1], documents)).toEqual([inbox, both]);
    });

    it('matches a document that is in any one of several selected folders', () => {
        expect(filterBySyncFolders([2], documents)).toEqual([archive, both]);
    });

    it('does not duplicate a document that matches several selected folders', () => {
        expect(filterBySyncFolders([1, 2], documents)).toEqual([inbox, archive, both]);
    });

    it('excludes documents with an empty folder list when a filter is active', () => {
        expect(filterBySyncFolders([1], [unfiled])).toEqual([]);
    });

    it('excludes documents missing the folders field entirely', () => {
        expect(filterBySyncFolders([1], [noFolderField])).toEqual([]);
    });

    it('returns nothing when the selected folders match no document', () => {
        expect(filterBySyncFolders([99], documents)).toEqual([]);
    });

    it('does not mutate the input array', () => {
        const input = [...documents];
        filterBySyncFolders([1], input);
        expect(input).toEqual(documents);
    });

    it('handles an empty document list', () => {
        expect(filterBySyncFolders([1], [])).toEqual([]);
    });
});

describe('filterPagedBySyncFolders', () => {
    const pages = documents.map((document, index) => ({ page: `page-${index}`, document }));

    it('returns every entry when no folder filter is set', () => {
        expect(filterPagedBySyncFolders(undefined, pages)).toBe(pages);
    });

    it('filters on the wrapped document folders', () => {
        expect(filterPagedBySyncFolders([1], pages).map((entry) => entry.document)).toEqual([inbox, both]);
    });

    it('excludes entries whose document is in no folder', () => {
        expect(filterPagedBySyncFolders([1], [{ page: 'page-x', document: unfiled }])).toEqual([]);
    });

    it('applies the same rule as the document filter', () => {
        // The image/PDF sync paths must never diverge from the data sync path.
        const selected = [1, 2];
        const viaDocuments = filterBySyncFolders(selected, documents);
        const viaPages = filterPagedBySyncFolders(selected, pages).map((entry) => entry.document);
        expect(viaPages).toEqual(viaDocuments);
    });
});
