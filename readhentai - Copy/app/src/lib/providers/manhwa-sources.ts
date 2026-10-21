/**
 * Manhwa Source Priority Configuration
 *
 * This file defines the priority order for Manhwa content sources.
 * The order determines which source is consulted first for metadata,
 * chapter lists, and chapter pages. Lower-priority sources are only
 * consulted when higher-priority sources are missing information.
 *
 * IMPORTANT: This is the INITIAL configuration. Each source must be
 * verified for capability support, legal compliance, and technical
 * feasibility before enabling. DO NOT enable a source until its
 * adapter is implemented and verified.
 *
 * Sources are ordered by priority (1 = highest priority).
 */

export interface ManhwaSourceConfig {
  id: string;
  name: string;
  baseUrl: string;
  /** Priority order (1 = highest). Lower number = higher priority. */
  priority: number;
  /** Whether this source is enabled. Must be false until adapter is verified. */
  enabled: boolean;
  /** Provider capabilities as declared by the adapter (to be filled in). */
  capabilities?: {
    search: boolean;
    getTitle: boolean;
    getChapters: boolean;
    getChapterPages: boolean;
    trending: boolean;
    latestUpdates: boolean;
    ratings: boolean;
  };
  /** Attribution / compliance note. */
  attribution?: string;
  /** Source status for admin UI. */
  status: "VERIFIED_AND_AVAILABLE" | "AUTHORIZED_WITH_RESTRICTIONS" | "METADATA_ONLY" | "SELF_HOST_REQUIRED" | "UNAVAILABLE" | "NOT_AUTHORIZED_FOR_INTENDED_USE" | "DISABLED" | "NOT_IMPLEMENTED";
  /** Notes for implementation. */
  notes?: string;
}

/**
 * Initial Manhwa source priority configuration (1 = highest priority).
 *
 * Sources are DISABLED by default. Enable only after:
 * 1. Adapter is implemented and tested
 * 2. Legal/compliance review is complete
 * 3. Capability verification is complete
 * 4. Rate limits and access restrictions are understood
 */
export const MANHWA_SOURCES: ManhwaSourceConfig[] = [
  {
    id: "omegascans",
    name: "OmegaScans",
    baseUrl: "https://omegascans.org/",
    priority: 1,
    enabled: false,
    status: "NOT_IMPLEMENTED",
    notes: "High-quality scans, active community. Verify API/HTML structure.",
  },
  {
    id: "hiperdex",
    name: "Hiperdex",
    baseUrl: "https://hiperdex.com/",
    priority: 2,
    enabled: false,
    status: "NOT_IMPLEMENTED",
    notes: "Popular Manhwa site. Check for API or HTML parsing needs.",
  },
  {
    id: "hentai20",
    name: "Hentai20",
    baseUrl: "https://hentai20.io/",
    priority: 3,
    enabled: false,
    status: "NOT_IMPLEMENTED",
    notes: "Adult Manhwa content. Verify adult content compliance.",
  },
  {
    id: "manhwax",
    name: "ManhwaX",
    baseUrl: "https://manhwax.top/",
    priority: 4,
    enabled: false,
    status: "NOT_IMPLEMENTED",
    notes: "Manhwa-focused site. Verify structure.",
  },
  {
    id: "manhwaclub",
    name: "ManhwaClub",
    baseUrl: "https://manhwaclub.net/",
    priority: 5,
    enabled: false,
    status: "NOT_IMPLEMENTED",
    notes: "Manhwa community site. Check for API access.",
  },
  {
    id: "manhwa18",
    name: "Manhwa18",
    baseUrl: "https://manhwa18.com/",
    priority: 6,
    enabled: false,
    status: "NOT_IMPLEMENTED",
    notes: "Adult Manhwa. Verify adult content compliance.",
  },
  {
    id: "lewdmanhwa",
    name: "LewdManhwa",
    baseUrl: "https://lewdmanhwa.com/",
    priority: 7,
    enabled: false,
    status: "NOT_IMPLEMENTED",
    notes: "Adult Manhwa. Verify adult content compliance.",
  },
  {
    id: "hasbicmanhwa",
    name: "HasbicManhwa",
    baseUrl: "https://hasbicmanhwa.com/",
    priority: 8,
    enabled: false,
    status: "NOT_IMPLEMENTED",
    notes: "Manhwa site. Verify structure.",
  },
  {
    id: "kairomanhwa",
    name: "KairoManhwa",
    baseUrl: "https://kairomanhwa.com/",
    priority: 9,
    enabled: false,
    status: "NOT_IMPLEMENTED",
    notes: "Manhwa site. Verify structure.",
  },
  {
    id: "doujiva-manhwa",
    name: "Doujiva Manhwa",
    baseUrl: "https://doujiva.com/manhwa",
    priority: 10,
    enabled: false,
    status: "NOT_IMPLEMENTED",
    notes: "Manhwa section of Doujiva. Verify if separate adapter needed.",
  },
  {
    id: "hentara",
    name: "Hentara",
    baseUrl: "https://hentara.com/",
    priority: 11,
    enabled: false,
    status: "NOT_IMPLEMENTED",
    notes: "Adult content. Verify compliance.",
  },
  {
    id: "manhwa18cc",
    name: "Manhwa18.cc",
    baseUrl: "https://manhwa18.cc/",
    priority: 12,
    enabled: false,
    status: "NOT_IMPLEMENTED",
    notes: "Alternative domain for Manhwa18. May share infrastructure.",
  },
  {
    id: "mangaforfree",
    name: "MangaForFree",
    baseUrl: "https://mangaforfree.com/",
    priority: 13,
    enabled: false,
    status: "NOT_IMPLEMENTED",
    notes: "General manga/manhwa site. Verify Manhwa content.",
  },
  {
    id: "manga18fx",
    name: "Manga18FX",
    baseUrl: "https://manga18fx.com/",
    priority: 14,
    enabled: false,
    status: "NOT_IMPLEMENTED",
    notes: "Adult content. Verify compliance.",
  },
  {
    id: "webtoonscan",
    name: "WebtoonScan",
    baseUrl: "https://webtoonscan.com/",
    priority: 15,
    enabled: false,
    status: "NOT_IMPLEMENTED",
    notes: "Webtoon/Manhwa site. Verify if Webtoon vs Manhwa focus.",
  },
  {
    id: "manga18club",
    name: "Manga18.club",
    baseUrl: "https://manga18.club/",
    priority: 16,
    enabled: false,
    status: "NOT_IMPLEMENTED",
    notes: "Adult content. Verify compliance.",
  },
];

/**
 * Get enabled sources sorted by priority (highest first).
 */
export function getEnabledManhwaSources(): typeof MANHWA_SOURCES {
  return MANHWA_SOURCES
    .filter((s) => s.enabled)
    .sort((a, b) => a.priority - b.priority);
}

/**
 * Get all sources sorted by priority.
 */
export function getAllManhwaSources(): typeof MANHWA_SOURCES {
  return [...MANHWA_SOURCES].sort((a, b) => a.priority - b.priority);
}

/**
 * Get source by ID.
 */
export function getManhwaSource(id: string): typeof MANHWA_SOURCES[0] | undefined {
  return MANHWA_SOURCES.find((s) => s.id === id);
}

/**
 * Update source enabled status (for admin UI).
 */
export function setManhwaSourceEnabled(id: string, enabled: boolean): void {
  const source = MANHWA_SOURCES.find((s) => s.id === id);
  if (source) {
    source.enabled = enabled;
  }
}

/**
 * Update source priority (for admin UI).
 */
export function setManhwaSourcePriority(id: string, priority: number): void {
  const source = MANHWA_SOURCES.find((s) => s.id === id);
  if (source) {
    source.priority = priority;
  }
}

/**
 * Get enabled source IDs in priority order (for provider registry).
 */
export function getEnabledManhwaSourceIds(): string[] {
  return getEnabledManhwaSources().map((s) => s.id);
}

/**
 * Get source capability declaration for registry (to be filled by adapters).
 */
export function getManhwaSourceCapabilities(id: string) {
  const source = getManhwaSource(id);
  return source?.capabilities ?? {
    search: false,
    getTitle: false,
    getChapters: false,
    getChapterPages: false,
    trending: false,
    latestUpdates: false,
    ratings: false,
  };
}

/**
 * Validate that a source is ready to be enabled.
 */
export function validateManhwaSource(id: string): { valid: boolean; errors: string[] } {
  const source = getManhwaSource(id);
  if (!source) return { valid: false, errors: ["Source not found"] };
  if (source.status === "NOT_IMPLEMENTED") return { valid: false, errors: ["Adapter not implemented"] };
  if (source.status === "DISABLED") return { valid: false, errors: ["Source is disabled"] };
  if (source.status === "NOT_AUTHORIZED_FOR_INTENDED_USE") return { valid: false, errors: ["Not authorized for intended use"] };
  if (source.status === "UNAVAILABLE") return { valid: false, errors: ["Source unavailable"] };
  return { valid: true, errors: [] };
}