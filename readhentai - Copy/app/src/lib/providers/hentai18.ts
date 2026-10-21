// Hentai18 adapter.
//
// Classification: VERIFIED_AND_AVAILABLE (search + trending + latest + title metadata + chapters + readable pages).
// Source: https://hentai18.net — an adult-only manga/manhwa/doujinshi catalogue.
// We request public pages with standard browser GETs and parse server-rendered HTML.
// Chapter page images live on Hentai18's CDN hosts (cdn.hentai18.net,
// media.hentai18.net), which hotlink-block foreign Referers (403) — every image
// is therefore served through our host-allowlisted display proxy
// (/api/hentairead-image) with Hentai18's own Referer. Bytes are piped through
// at read time, never stored; no access control is bypassed.

import { cached, rawText } from "./http";
import { classifyHentai18, type ContentOrigin } from "./adult";
import {
  ProviderError,
  type Category,
  type ChapterOptions,
  type ContentProvider,
  type NormalizedChapter,
  type NormalizedPage,
  type NormalizedTitle,
  type NormalizedUpdate,
  type PublicationStatus,
  type ProviderCapabilities,
  type ProviderInfo,
  type SearchOptions,
  type TrendingOptions,
  type UpdateOptions,
} from "./types";

const BASE = "https://hentai18.net";
const LISTING_TTL = 15 * 60 * 1000; // 15 min
const DETAIL_TTL = 60 * 60 * 1000; // 1 hr
const PAGES_TTL = 24 * 60 * 60 * 1000; // 24 hr

const CAPABILITIES: ProviderCapabilities = {
  search: true,
  getTitle: true,
  getChapters: true,
  getChapterPages: true,
  trending: true,
  latestUpdates: true,
  ratings: false,
};

const INFO: ProviderInfo = {
  id: "hentai18",
  name: "Hentai18",
  baseUrl: BASE,
  status: "VERIFIED_AND_AVAILABLE",
  attribution: "Content sourced from Hentai18 (hentai18.net).",
  capabilities: CAPABILITIES,
  adult: true,
};

/* ------------------------------------------------------------------ */
/* Parsing helpers                                                     */
/* ------------------------------------------------------------------ */

function unescapeHtml(s: string): string {
  return s
    .replace(/&#x([0-9a-f]+);/gi, (_, h) => String.fromCharCode(parseInt(h, 16)))
    .replace(/&#(\d+);/g, (_, d) => String.fromCharCode(Number(d)))
    .replace(/&nbsp;/g, " ")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/&amp;/g, "&");
}

function absUrl(src: string): string {
  if (/^https?:\/\//i.test(src)) return src;
  return `${BASE}/${src.replace(/^\//, "")}`;
}

/**
 * Hentai18's CDN hotlink-blocks foreign Referers (403), so a bare <img> from our
 * app never loads. Route image bytes through our host-allowlisted display proxy
 * (which sends Hentai18's own Referer); nothing is stored.
 */
function proxyImage(absoluteUrl: string): string {
  return `/api/hentairead-image?url=${encodeURIComponent(absoluteUrl)}`;
}

interface RawCard {
  slug: string;
  title: string;
  cover: string | null;
  latestChapter?: { slug: string; label: string } | null;
}

function parseCards(html: string): RawCard[] {
  const cards: RawCard[] = [];
  const seen = new Set<string>();
  const visualRe = /<div class="visual">([\s\S]*?)<\/div>\s*<\/li>/gi;
  let match: RegExpExecArray | null;

  while ((match = visualRe.exec(html))) {
    const block = match[1];
    const slugMatch =
      block.match(/href="https:\/\/hentai18\.net\/read-hentai\/([a-z0-9\-]+)"/i) ||
      block.match(/href="\/read-hentai\/([a-z0-9\-]+)"/i);
    if (!slugMatch) continue;
    const slug = slugMatch[1];
    if (slug.includes("-chapter-") || seen.has(slug)) continue;
    seen.add(slug);

    const titleMatch =
      block.match(/<h3 class="title">\s*<a[^>]*>([^<]+)<\/a>/i) ||
      block.match(/alt="([^"]+)"/i);
    const coverMatch =
      block.match(/data-original="([^"]+)"/i) || block.match(/src="([^"]+)"/i);
    const chapterMatch = block.match(
      /<div class="item-total-views">\s*<a href="\/read-hentai\/([^"]+)"[^>]*>([^<]+)<\/a>/i,
    );

    cards.push({
      slug,
      title: unescapeHtml(titleMatch ? titleMatch[1].trim() : slug),
      cover: coverMatch ? absUrl(coverMatch[1]) : null,
      latestChapter: chapterMatch
        ? { slug: chapterMatch[1], label: chapterMatch[2].trim() }
        : null,
    });
  }
  return cards;
}

function buildTitleFromCard(card: RawCard): NormalizedTitle {
  return {
    id: `hentai18:${card.slug}`,
    provider: INFO.id,
    providerId: card.slug,
    slug: `hentai18-${card.slug}`,
    title: card.title,
    alternativeTitles: [],
    description: null,
    category: "manga",
    isAdult: true,
    coverImage: card.cover ? proxyImage(card.cover) : null,
    rating: null,
    popularity: null,
    colored: true, // hentai18 content is predominantly full color
    genres: [],
    tags: [],
    artists: [],
    authors: [],
    language: "English",
    status: null,
    updatedAt: null,
    publishedAt: null,
    providerUrl: `${BASE}/read-hentai/${card.slug}`,
    readable: true,
    adult: classifyHentai18(),
  };
}

/* ------------------------------------------------------------------ */
/* Detail & Chapter parsing                                            */
/* ------------------------------------------------------------------ */

interface RawDetail {
  title: string;
  altTitles: string[];
  cover: string | null;
  description: string | null;
  category: Category;
  artists: string[];
  tags: string[];
  status: PublicationStatus | null;
  views: number | null;
  chapters: Array<{
    slug: string;
    label: string;
    number: string | null;
    date: string | null;
  }>;
}

function parseDetail(html: string, slug: string): RawDetail {
  const titleMatch = html.match(/<h1[^>]*>([^<]+)<\/h1>/i);
  const altMatch = html.match(/<h2 class="alternative">([^<]+)<\/h2>/i);
  const ogImg = html.match(/<meta property="og:image" content="([^"]+)"/i);
  const ogDesc = html.match(/<meta property="og:description" content="([^"]*)"/i);

  // Category
  const catMatch = html.match(/Category:[\s\S]*?<a class="item-tag\s*"[^>]*>([^<]+)<\/a>/i);
  const categoryRaw = catMatch ? catMatch[1].toLowerCase() : "manga";
  const category: Category = categoryRaw.includes("manhwa")
    ? "manhwa"
    : categoryRaw.includes("manhua")
      ? "manhua"
      : "manga";

  // Artists
  const artistBlock = html.match(/Artists:[\s\S]*?<span class="line-content">([\s\S]*?)<\/span>/i);
  const artists: string[] = [];
  if (artistBlock) {
    const are = /<a[^>]*>([^<]+)<\/a>/g;
    let am: RegExpExecArray | null;
    while ((am = are.exec(artistBlock[1]))) artists.push(unescapeHtml(am[1].trim()));
  }

  // Tags
  const tagBlock = html.match(/Tags:[\s\S]*?<span class="line-content">([\s\S]*?)<\/span>/i);
  const tags: string[] = [];
  if (tagBlock) {
    const tre = /<a[^>]*>([^<]+)<\/a>/g;
    let tm: RegExpExecArray | null;
    while ((tm = tre.exec(tagBlock[1]))) tags.push(unescapeHtml(tm[1].trim()));
  }

  // Status
  const statusMatch = html.match(/Status:[\s\S]*?<span class="line-content">\s*([^<]+)<\/span>/i);
  const statusRaw = statusMatch ? statusMatch[1].trim().toLowerCase() : "";
  const status: PublicationStatus | null = statusRaw.includes("completed")
    ? "Completed"
    : statusRaw.includes("ongoing")
      ? "In Process"
      : null;

  // Views
  const viewsMatch = html.match(/has\s+([\d,]+)\s+views/i);
  const views = viewsMatch ? parseInt(viewsMatch[1].replace(/,/g, ""), 10) : null;

  // Chapters
  const chapters: RawDetail["chapters"] = [];
  const chRe =
    /<li class="citem"[^>]*>\s*<a href="(?:\/read-hentai\/|https:\/\/hentai18\.net\/read-hentai\/)([^"]+)"[^>]*>([^<]+)<\/a>(?:[\s\S]*?<span class="time">([^<]+)<\/span>)?/gi;
  let chM: RegExpExecArray | null;
  while ((chM = chRe.exec(html))) {
    const chSlug = chM[1].replace(/^\/+|\/+$/g, "");
    const label = chM[2].trim();
    const date = chM[3] ? chM[3].trim() : null;
    const numMatch = label.match(/chapter\s*([\d.]+)/i);
    const num = numMatch ? numMatch[1] : null;
    chapters.push({
      slug: chSlug,
      label,
      number: num,
      date,
    });
  }

  return {
    title: unescapeHtml(titleMatch ? titleMatch[1].trim() : slug),
    altTitles: altMatch ? [unescapeHtml(altMatch[1].trim())] : [],
    cover: ogImg ? absUrl(ogImg[1]) : null,
    description: ogDesc ? unescapeHtml(ogDesc[1].trim()) : null,
    category,
    artists,
    tags,
    status,
    views,
    chapters,
  };
}

function parseChapterPages(html: string): NormalizedPage[] {
  const pages: NormalizedPage[] = [];
  const contentMatch =
    html.match(/class="chapter-content">([\s\S]*?)<\/div>\s*<div class="ads-block/i) ||
    html.match(/class="chapter-content">([\s\S]*?)<\/div>/i);
  const area = contentMatch ? contentMatch[1] : html;
  const imgRe = /<img[^>]+src="([^"]+)"[^>]*>/gi;
  let m: RegExpExecArray | null;
  let idx = 0;
  while ((m = imgRe.exec(area))) {
    const src = m[1];
    if (src.includes("cdn.hentai18.net/images/manga/")) {
      pages.push({ index: idx++, imageUrl: proxyImage(src) });
    }
  }
  return pages;
}

/* ------------------------------------------------------------------ */
/* Fetch helper                                                        */
/* ------------------------------------------------------------------ */

function fetchHtml(path: string, ttl: number): Promise<string> {
  const url = path.startsWith("http") ? path : `${BASE}${path}`;
  const key = `hentai18:html:${path}`;
  return cached(key, ttl, async () => {
    try {
      return await rawText(url, {
        timeoutMs: 15_000,
        headers: {
          Referer: `${BASE}/`,
        },
      });
    } catch (err) {
      throw new ProviderError(INFO.id, (err as Error).message, "network", true);
    }
  });
}

/* ------------------------------------------------------------------ */
/* Adapter                                                             */
/* ------------------------------------------------------------------ */

export const hentai18: ContentProvider = {
  getProviderInfo(): ProviderInfo {
    return INFO;
  },

  async searchTitles(query: string, options: SearchOptions = {}): Promise<NormalizedTitle[]> {
    const limit = Math.min(options.limit ?? 24, 50);
    const offset = Math.max(0, options.offset ?? 0);
    const q = query?.trim() ?? "";
    const path = q ? `/search?s=${encodeURIComponent(q)}` : "/top-hentai";

    try {
      const html = await fetchHtml(path, LISTING_TTL);
      const cards = parseCards(html);
      const titles = cards.map((c) => buildTitleFromCard(c));
      // Hentai18's search has no page parameter (verified: the results page
      // emits no `page=N` links), so there is only ever ONE page of results.
      // Honour `offset` by slicing that page so aggregateSearch's paging stays
      // honest: pages past the end return [] from here instead of re-serving
      // page 1, which used to inject duplicate cards into every merged page.
      return titles.slice(offset, offset + limit);
    } catch (err) {
      throw new ProviderError(INFO.id, (err as Error).message, "network", true);
    }
  },

  async getTitle(providerId: string): Promise<NormalizedTitle | null> {
    const slug = providerId.replace(/^hentai18-/, "");
    try {
      const html = await fetchHtml(`/read-hentai/${slug}`, DETAIL_TTL);
      const detail = parseDetail(html, slug);

      return {
        id: `hentai18:${slug}`,
        provider: INFO.id,
        providerId: slug,
        slug: `hentai18-${slug}`,
        title: detail.title,
        alternativeTitles: detail.altTitles,
        description: detail.description,
        category: detail.category,
        isAdult: true,
        coverImage: detail.cover ? proxyImage(detail.cover) : null,
        rating: null,
        popularity: detail.views,
        genres: detail.tags,
        tags: detail.tags,
        artists: detail.artists,
        authors: detail.artists,
        language: "English",
        status: detail.status,
        updatedAt: null,
        publishedAt: null,
        providerUrl: `${BASE}/read-hentai/${slug}`,
        readable: detail.chapters.length > 0,
        colored: true, // hentai18 content is predominantly full color
        adult: classifyHentai18(detail.category),
      };
    } catch {
      return null;
    }
  },

  async getChapters(providerId: string, options: ChapterOptions = {}): Promise<NormalizedChapter[]> {
    const slug = providerId.replace(/^hentai18-/, "");
    try {
      const html = await fetchHtml(`/read-hentai/${slug}`, DETAIL_TTL);
      const detail = parseDetail(html, slug);
      const order = options.order ?? "desc";

      let chapters: NormalizedChapter[] = detail.chapters.map((ch) => ({
        id: `hentai18:${ch.slug}`,
        titleId: `hentai18:${slug}`,
        provider: INFO.id,
        providerChapterId: ch.slug,
        chapterNumber: ch.number,
        chapterTitle: ch.label,
        language: "en",
        publishedAt: ch.date ? new Date(ch.date).toISOString() : null,
        pageCount: null,
        imageUrl: "",
        readable: true,
      }));

      if (order === "asc") {
        chapters = chapters.slice().reverse();
      }

      return chapters;
    } catch (err) {
      throw new ProviderError(INFO.id, (err as Error).message, "network", true);
    }
  },

  async getChapterPages(providerId: string, chapterId: string): Promise<NormalizedPage[]> {
    const chSlug = chapterId.replace(/^hentai18-/, "");
    try {
      const html = await fetchHtml(`/read-hentai/${chSlug}`, PAGES_TTL);
      const pages = parseChapterPages(html);
      if (pages.length === 0) {
        throw new ProviderError(INFO.id, "no pages found in chapter", "parse", false);
      }
      return pages;
    } catch (err) {
      if (err instanceof ProviderError) throw err;
      throw new ProviderError(INFO.id, (err as Error).message, "network", true);
    }
  },

  async getTrending(options: TrendingOptions = {}): Promise<NormalizedTitle[]> {
    const limit = Math.min(options.limit ?? 24, 50);
    try {
      const html = await fetchHtml("/top-hentai", LISTING_TTL);
      const cards = parseCards(html);
      return cards.slice(0, limit).map((c) => buildTitleFromCard(c));
    } catch (err) {
      throw new ProviderError(INFO.id, (err as Error).message, "network", true);
    }
  },

  async getLatestUpdates(options: UpdateOptions = {}): Promise<NormalizedUpdate[]> {
    const limit = Math.min(options.limit ?? 24, 50);
    try {
      const html = await fetchHtml("/new-manga-hentai", LISTING_TTL);
      const cards = parseCards(html);
      const updates: NormalizedUpdate[] = [];

      for (const card of cards.slice(0, limit)) {
        const title = buildTitleFromCard(card);
        const chapterSlug = card.latestChapter?.slug ?? `${card.slug}-chapter-1`;
        const chapterNumMatch = card.latestChapter?.label?.match(/chapter\s*([\d.]+)/i);
        const chapter: NormalizedChapter = {
          id: `hentai18:${chapterSlug}`,
          titleId: title.id,
          provider: INFO.id,
          providerChapterId: chapterSlug,
          chapterNumber: chapterNumMatch ? chapterNumMatch[1] : null,
          chapterTitle: card.latestChapter?.label ?? null,
          language: "en",
          publishedAt: null,
          pageCount: null,
          imageUrl: "",
          readable: true,
        };
        updates.push({ title, chapter });
      }

      return updates;
    } catch (err) {
      throw new ProviderError(INFO.id, (err as Error).message, "network", true);
    }
  },
};
