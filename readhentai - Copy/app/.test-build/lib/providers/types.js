"use strict";
// Normalized content models + the unified provider interface.
//
// Every upstream source (MangaDex, AniList, …) is isolated behind an adapter
// that produces these shapes. Provider-specific parsing never leaks into React
// components — components only ever see Normalized* models or the UI-facing
// `Manga` type produced by normalize.ts.
Object.defineProperty(exports, "__esModule", { value: true });
exports.ProviderError = exports.CATEGORY_LABEL = void 0;
exports.CATEGORY_LABEL = {
    manga: "Manga",
    manhwa: "Manhwa",
    manhua: "Manhua",
};
/** Thrown by adapters so the aggregator can fail over per-provider. */
class ProviderError extends Error {
    constructor(providerId, message, kind = "network", retryable = true) {
        super(`[${providerId}] ${message}`);
        this.providerId = providerId;
        this.kind = kind;
        this.retryable = retryable;
        this.name = "ProviderError";
    }
}
exports.ProviderError = ProviderError;
