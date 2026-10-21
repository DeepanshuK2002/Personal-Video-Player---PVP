"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, RotateCcw, Search, Target } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { MangaCard } from "@/components/MangaCard";
import { Pagination } from "@/components/Pagination";
import { GENRE_LIST } from "@/lib/manga";
import { useTitles } from "@/lib/content";
import { useContentType } from "@/lib/contentType";
import type { Manga } from "@/lib/manga";
import { useNoStopScroll } from "@/lib/noStopScroll";

/* ------------------------------------------------------------------ */
/* Static option tables (hoisted — the TSX parser here rejects inline  */
/* `as X[]` casts inside JSX).                                          */
/* ------------------------------------------------------------------ */

type CategoryKey = "Manga" | "Manhwa" | "Manhua" | "Comics";

interface CategoryPill {
  key: CategoryKey;
  label: string;
  on: string;
  dot: string;
}

/** Real content-type categories — filtered on `Manga.contentType`. */
const CATEGORY_PILLS: CategoryPill[] = [
  { key: "Manga", label: "Manga", on: "bg-green-500/15 border-green-500 text-green-400", dot: "bg-green-500" },
  { key: "Manhwa", label: "Manhwa", on: "bg-blue-500/15 border-blue-500 text-blue-400", dot: "bg-blue-500" },
  { key: "Manhua", label: "Manhua", on: "bg-purple-500/15 border-purple-500 text-purple-400", dot: "bg-purple-500" },
  { key: "Comics", label: "Comics", on: "bg-orange-500/15 border-orange-500 text-orange-400", dot: "bg-orange-500" },
];

interface AdvField {
  key: string;
  placeholder: string;
}

/** Metadata search fields — folded into the real `q` provider text search. */
const ADV_FIELDS: AdvField[] = [
  { key: "artists", placeholder: "Artists" },
  { key: "collections", placeholder: "Collections" },
  { key: "characters", placeholder: "Characters" },
  { key: "conventions", placeholder: "Conventions" },
  { key: "circles", placeholder: "Circles" },
];

type FieldKey =
  | "artists"
  | "collections"
  | "characters"
  | "conventions"
  | "circles";

interface SearchDraft {
  categories: CategoryKey[];
  fields: Record<FieldKey, string>;
  tags: string[];
  pages: number;
}

const EMPTY_FIELDS: Record<FieldKey, string> = {
  artists: "",
  collections: "",
  characters: "",
  conventions: "",
  circles: "",
};

const EMPTY_DRAFT: SearchDraft = {
  categories: [],
  fields: EMPTY_FIELDS,
  tags: [],
  pages: 0,
};

function AdvancedSearchContent() {
  const contentType = useContentType();
  const [noStopScroll] = useNoStopScroll();

  // Live, editable form state (applied only when "Search" is pressed).
  const [draft, setDraft] = useState<SearchDraft>(EMPTY_DRAFT);
  const [tagQuery, setTagQuery] = useState("");
  const [applied, setApplied] = useState<SearchDraft>(EMPTY_DRAFT);
  const [textQuery, setTextQuery] = useState("");
  const [page, setPage] = useState<number>(1);
  const [accumulated, setAccumulated] = useState<Manga[]>([]);
  const sentinelRef = useRef<HTMLDivElement>(null);
  /* Stays false until the URL has been read client-side, so we never request
   * a blank query before `?q=` is known. */
  const [urlRead, setUrlRead] = useState(false);

  /* ---- deep-linked `?q=` ------------------------------------------
   * Read from `window.location` instead of `useSearchParams()` — deep links
   * from the regular search (`/advanced-search?q=…`) prefill the box, and
   * because this runs after every commit, client-side navigations and
   * back/forward are picked up too. The setters are value-equal, so it
   * settles rather than looping.
   *
   * `useSearchParams()` is avoided on purpose: on a prerendered route it
   * forces this subtree through a CSR bailout that must be wrapped in
   * `<Suspense>`, and that boundary never resolves in dev — the streamed
   * markup stays parked in the out-of-order container and the page sits on
   * its fallback forever. */
  useEffect(() => {
    const next = new URLSearchParams(window.location.search).get("q") ?? "";
    if (!urlRead) {
      setUrlRead(true);
      setTextQuery(next);
      setApplied((prev) => ({ ...prev }));
      setPage(1);
      return;
    }
    if (next !== textQuery) {
      setTextQuery(next);
      setApplied((prev) => ({ ...prev }));
      setPage(1);
    }
  });

  const genreQuery = applied.tags.map((g) => `genre=${encodeURIComponent(g)}`).join("&");
  const offset = (page - 1) * 24;
  // `null` until the deep-linked `?q=` has been read: `useTitles(null)` is a
  // no-op, so we never request a query we already know we're about to replace.
  const apiPath: string | null = urlRead
    ? `/api/titles?limit=24&offset=${offset}&q=${encodeURIComponent(textQuery)}&contentType=${encodeURIComponent(contentType)}${genreQuery ? `&${genreQuery}` : ""}`
    : null;

  const { items: workingSet, loading, data } = useTitles(apiPath);
  /* "No response yet" counts as busy: while the URL read is pending,
   * `useTitles(null)` clears `loading`, which would flash the empty state. */
  const busy = loading || data === null;

  useEffect(() => {
    // Discrete pagination must show that page's own results; only infinite
    // scroll (noStopScroll) grows one ever-accumulating list. Appending on a
    // page click too left page 1's items on top, so "page 2" just scrolled
    // back to the same content.
    if (page === 1 || !noStopScroll) {
      setAccumulated(workingSet);
    } else {
      setAccumulated((prev) => {
        const seen = new Set(prev.map((m) => m.slug));
        return [...prev, ...workingSet.filter((m) => !seen.has(m.slug))];
      });
    }
  }, [workingSet, page, noStopScroll]);

  useEffect(() => {
    if (!noStopScroll) return;
    const el = sentinelRef.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && !busy && workingSet.length >= 24) {
          setPage((p) => p + 1);
        }
      },
      { rootMargin: "300px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [noStopScroll, busy, workingSet.length]);

  const filteredResults = useMemo(() => {
    let list = accumulated.slice();

    if (applied.categories.length > 0) {
      list = list.filter((m) => m.contentType != null && applied.categories.includes(m.contentType as CategoryKey));
    }

    return list;
  }, [accumulated, applied.categories]);

  const toggleCategory = (key: CategoryKey) => {
    setDraft((d) => ({
      ...d,
      categories: d.categories.includes(key) ? d.categories.filter((k) => k !== key) : [...d.categories, key],
    }));
  };

  const toggleTag = (tag: string) => {
    setDraft((d) => ({
      ...d,
      tags: d.tags.includes(tag) ? d.tags.filter((t) => t !== tag) : [...d.tags, tag],
    }));
  };

  const setField = (key: FieldKey, value: string) => {
    setDraft((d) => ({ ...d, fields: { ...d.fields, [key]: value } }));
  };

  const applySearch = () => {
    setApplied(draft);
    setPage(1);
  };

  const resetAll = () => {
    setDraft(EMPTY_DRAFT);
    setTagQuery("");
    setApplied(EMPTY_DRAFT);
    setPage(1);
  };

  const pct = Math.min(100, Math.max(0, draft.pages));

  const visibleGenres = useMemo(() => {
    if (!tagQuery) return GENRE_LIST;
    const q = tagQuery.toLowerCase();
    return GENRE_LIST.filter((g) => g.toLowerCase().includes(q));
  }, [tagQuery]);

  const backHref = textQuery.trim() ? `/search?q=${encodeURIComponent(textQuery.trim())}` : "/search";

  return (
    <section className="pb-16">
      {/* Gradient banner: header + categories + first field sit on the red glow */}
      <div className="bg-[linear-gradient(180deg,#5a0000_0%,#2a0000_38%,#000000_72%)]">
        <div className="mx-auto max-w-[1440px] px-4 pt-6 sm:px-6 md:pt-8 lg:px-8">
          <div className="flex items-center gap-2.5">
            <Target className="h-7 w-7 shrink-0 text-brand-soft" aria-hidden />
            <h1 className="text-2xl font-semibold tracking-tight text-brand-soft md:text-3xl">
              Advance Search
            </h1>
          </div>
          <p className="mt-1 pl-9 text-xs text-ink-soft/80">
            Note : This feature are still in testing phase
          </p>

          <Link
            href={backHref}
            className="mt-3 inline-flex items-center gap-1.5 pl-9 text-xs text-ink-muted transition hover:text-brand-soft"
          >
            <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
            Back to regular search
          </Link>

          {/* Categories */}
          <h2 className="mt-7 text-xl font-medium text-ink md:text-2xl">Categories</h2>
          <div className="mt-3 flex flex-wrap gap-2.5">
            {CATEGORY_PILLS.map((pill) => {
              const active = draft.categories.includes(pill.key);
              return (
                <button
                  key={pill.key}
                  type="button"
                  aria-pressed={active}
                  onClick={() => toggleCategory(pill.key)}
                  className={`flex items-center gap-2 rounded-full border px-4 py-1.5 text-sm font-medium transition ${
                    active ? pill.on : "border-white/15 bg-white/[0.03] text-ink-soft hover:border-white/30"
                  }`}
                >
                  <span className={`h-2 w-2 rounded-full ${active ? pill.dot : "bg-white/25"}`} aria-hidden />
                  {pill.label}
                </button>
              );
            })}
          </div>

          {/* Metadata search fields */}
          <div className="mt-5 space-y-3">
            {ADV_FIELDS.map((f) => (
              <input
                key={f.key}
                type="text"
                value={draft.fields[f.key as FieldKey]}
                onChange={(e) => setField(f.key as FieldKey, e.target.value)}
                placeholder={f.placeholder}
                className="w-full rounded-xl border border-white/10 bg-[#1c1c1c] px-4 py-3.5 text-sm text-ink outline-none transition placeholder:text-ink-muted focus:border-brand-soft/60"
              />
            ))}
          </div>

          {/* Tags box */}
          <div className="mt-6 overflow-hidden rounded-xl border border-white/10 bg-[#141414]">
            <div className="flex items-center gap-3 border-b border-white/10 px-4 py-3">
              <span className="shrink-0 text-sm font-medium text-ink">Tags</span>
              <input
                type="text"
                value={tagQuery}
                onChange={(e) => setTagQuery(e.target.value)}
                placeholder="Search Tag"
                className="w-full rounded-full border border-white/10 bg-[#1c1c1c] px-3 py-1.5 text-xs text-ink outline-none transition placeholder:text-ink-muted focus:border-brand-soft/60"
              />
            </div>
            <div className="max-h-64 overflow-y-auto p-3">
              <div className="flex flex-wrap gap-2">
                {visibleGenres.map((genre) => {
                  const selected = draft.tags.includes(genre);
                  return (
                    <button
                      key={genre}
                      type="button"
                      aria-pressed={selected}
                      onClick={() => toggleTag(genre)}
                      className={`rounded-full border px-3 py-1 text-xs transition ${
                        selected
                          ? "border-brand-soft bg-brand-deep/40 text-ink"
                          : "border-white/12 bg-white/[0.03] text-ink-soft hover:border-white/30 hover:text-ink"
                      }`}
                    >
                      {genre}
                    </button>
                  );
                })}
                {visibleGenres.length === 0 && (
                  <p className="px-1 py-2 text-xs text-ink-muted">No tags match.</p>
                )}
              </div>
            </div>
          </div>

          {/* Pages slider */}
          <div className="mt-7 w-full">
            <p className="text-base font-semibold text-ink">Pages</p>
            <div className="relative mt-4">
              <input
                type="range"
                min={0}
                max={100}
                value={draft.pages}
                aria-label="Minimum number of pages"
                onChange={(e) => setDraft((d) => ({ ...d, pages: Number(e.target.value) }))}
                className="w-full accent-[#ff0000]"
              />
              <div
                className="pointer-events-none absolute -top-1.5 -translate-x-1/2 rounded bg-brand px-1.5 py-0.5 text-[10px] font-semibold text-white"
                style={{ left: `calc(${pct}% + ${(0.5 - pct / 100) * 16}px)` }}
              >
                {draft.pages}
              </div>
            </div>
            <div className="mt-1 flex justify-between text-xs text-ink-muted">
              <span>0</span>
              <span>100</span>
            </div>
          </div>

          {/* Actions */}
          <div className="mt-7 flex items-center justify-center gap-4">
            <button
              type="button"
              onClick={resetAll}
              className="flex items-center gap-1.5 px-2 py-2 text-sm font-medium text-ink-soft transition hover:text-ink"
            >
              <RotateCcw className="h-4 w-4" aria-hidden />
              Reset
            </button>
            <button
              type="button"
              onClick={applySearch}
              className="rounded-md bg-brand-deep/60 px-6 py-2 text-sm font-semibold text-brand-soft ring-1 ring-inset ring-brand/40 transition hover:bg-brand-deep"
            >
              <Search className="mr-1 inline h-4 w-4" aria-hidden />
              Search
            </button>
          </div>

          <div className="mt-8 border-t border-white/10" />
        </div>
      </div>

      <div className="mx-auto max-w-[1440px] px-4 sm:px-6 lg:px-8">
        {/* Results */}
        <div className="mt-6">
          <h2 className="text-xl font-bold text-ink md:text-2xl">
            Search Results ({busy && accumulated.length === 0 ? "?" : filteredResults.length})
          </h2>

          {busy && accumulated.length === 0 ? (
            <div
              className="mt-6 grid grid-cols-2 gap-x-5 gap-y-8 md:grid-cols-4 xl:grid-cols-6"
              aria-busy="true"
            >
              {Array.from({ length: 12 }).map((_, i) => (
                <div key={i} className="aspect-[2/3] w-full animate-pulse rounded-xl bg-white/5" />
              ))}
            </div>
          ) : filteredResults.length > 0 ? (
            <div className="mt-6 grid grid-cols-2 gap-x-5 gap-y-8 md:grid-cols-4 xl:grid-cols-6">
              {filteredResults.map((manga) => (
                <MangaCard key={manga.slug} manga={manga} twoLineTitle />
              ))}
            </div>
          ) : (
            <div className="mt-10 flex flex-col items-center justify-center text-center">
              <p className="text-base font-medium text-ink-soft">No manga found.</p>
              <p className="mt-1 text-xs text-ink-muted">
                Try different keywords, categories, or tags.
              </p>
            </div>
          )}

          {!noStopScroll && (
            <Pagination
              page={page}
              totalPages={filteredResults.length >= 24 ? page + 1 : page}
              onPageChange={(p) => {
                setPage(p);
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
            />
          )}
          {noStopScroll && <div ref={sentinelRef} className="h-10" />}
        </div>
      </div>
    </section>
  );
}

export default function AdvancedSearchPage() {
  return (
    <AppShell>
      <AdvancedSearchContent />
    </AppShell>
  );
}
