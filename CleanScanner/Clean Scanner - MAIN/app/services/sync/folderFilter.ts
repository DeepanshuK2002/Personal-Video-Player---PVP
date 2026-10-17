/**
 * Per-sync-service folder filtering.
 *
 * A sync service can be restricted to a subset of folders (`syncFolders`).
 * These helpers are kept free of worker/device dependencies so the filtering
 * rules can be unit-tested directly.
 */

/** Minimal shape needed to decide whether a document belongs to a synced folder. */
export interface FolderedDocument {
    folders?: number[];
}

/**
 * Returns true when the service syncs everything, i.e. no folder restriction is
 * configured. An empty `syncFolders` list means "no filter", not "sync nothing".
 */
export function syncsAllFolders(syncFolders?: number[]): boolean {
    return !syncFolders?.length;
}

/**
 * Filters documents down to those living in one of the service's folders.
 *
 * Documents not assigned to any folder are intentionally excluded when a folder
 * filter is active.
 */
export function filterBySyncFolders<T extends FolderedDocument>(syncFolders: number[] | undefined, documents: T[]): T[] {
    if (syncsAllFolders(syncFolders)) {
        return documents;
    }
    const folderSet = new Set(syncFolders);
    return documents.filter((document) => document.folders?.some((folderId) => folderSet.has(folderId)));
}

/**
 * Same rule as {@link filterBySyncFolders}, for the page-oriented lists used by
 * the image and PDF sync paths, where each entry wraps its document.
 */
export function filterPagedBySyncFolders<T extends { document: FolderedDocument }>(syncFolders: number[] | undefined, documents: T[]): T[] {
    if (syncsAllFolders(syncFolders)) {
        return documents;
    }
    const folderSet = new Set(syncFolders);
    return documents.filter((item) => item.document.folders?.some((folderId) => folderSet.has(folderId)));
}
