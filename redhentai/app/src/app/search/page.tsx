"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { ChevronDown, FunnelPlus, Search, Target } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { Pagination } from "@/components/Pagination";
import { SearchListCard } from "@/components/SearchListCard";
import { TagPickerModal } from "@/components/TagPickerModal";
import { STATUS_OPTIONS } from "@/lib/manga";
import type { Manga, Status } from "@/lib/manga";
import { useTitles } from "@/lib/content";
import { useContentType } from "@/lib/contentType";
import { useNoStopScroll } from "@/lib/noStopScroll";

/* ------------------------------------------------------------------ */
/* Static option tables (hoisted — the TSX parser here rejects inline  */
/* `as X[]` casts inside JSX).                                          */
/* ------------------------------------------------------------------ */

type PillKey = "All" | "Manhwa" | "Manga" | "Manhua";

interface CategoryPill {
  key: PillKey;
  /**
   * `contentType` value sent to `/api/titles`. The settings store spells the
   * manhua bucket "Comics", so the pill labelled "Manhua" must send that.
   */
  api: string;
  /** `Manga.contentType` value this pill matches ("" = no client-side filter). */
  match: string;
}

const CATEGORY_PILLS: CategoryPill[] = [
  { key: "All", api: "", match: "" },
  { key: "Manhwa", api: "Manhwa", match: "Manhwa" },
  { key: "Manga", api: "Manga", match: "Manga" },
  { key: "Manhua", api: "Comics", match: "Manhua" },
];

const STATUS_CHOICES: Status[] = [...STATUS_OPTIONS];

const PAGE_SIZE = 24;
const TYPE_DEBOUNCE_MS = 350;

function SearchContent() {
  const contentType = useContentType();
  const [noStopScroll] = useNoStopScroll();

  /* ---- query state -------------------------------------------------
   * `input` is the text in the box; `query` is what we actually search.
   * `committed` records the last value we deliberately searched so a
   * deep-linked `?q=` from the header form is applied exactly once and
   * never fights the live-typing debounce. */
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const committed = useRef("");
  /* Stays false until the URL has been read client-side, so we never issue a
   * request for a blank query before `?q=` is known. */
  const [urlRead, setUrlRead] = useState(false);

  const [filterOpen, setFilterOpen] = useState(false);
  const [category, setCategory] = useState<PillKey>("All");
  const [status, setStatus] = useState<Status>("All");
  const [tags, setTags] = useState<string[]>([]);
  const [tagPickerOpen, setTagPickerOpen] = useState(false);
  const [page, setPage] = useState(1);
  const [accumulated, setAccumulated] = useState<Manga[]>([]);
  const sentinelRef = useRef<HTMLDivElement>(null);

  /* ---- deep-linked `?q=` ------------------------------------------
   * Read from `window.location` instead of `useSearchParams()`. The header
   * form posts natively (a full page load) and every other entry point
   * mounts this component fresh, so the location is always current — and
   * because this runs after every commit, client-side navigations and
   * back/forward are picked up too. Both setters are value-equal, so it
   * settles rather than looping.
   *
   * `useSearchParams()` is avoided on purpose: on a prerendered route it
   * forces this whole subtree through a CSR bailout that must be wrapped in
   * `<Suspense>`, and that boundary never resolves in dev — the streamed
   * markup stays parked in the out-of-order container and the page sits on
   * its fallback forever. */
  useEffect(() => {
    const next = new URLSearchParams(window.location.search).get("q") ?? "";
    if (!urlRead) {
      setUrlRead(true);
      setInput(next);
      setQuery(next);
      committed.current = next;
      return;
    }
    // Apply a changed URL only while the box still matches what we searched,
    // i.e. the user isn't mid-typing.
    if (next !== committed.current && input === committed.current) {
      setInput(next);
      setQuery(next);
      committed.current = next;
      setPage(1);
    }
  });

  // Typing searches live, debounced so we don't fire a request per keystroke.
  useEffect(() => {
    if (input === committed.current) return;
    const timer = setTimeout(() => {
      committed.current = input;
      setQuery(input);
      setPage(1);
    }, TYPE_DEBOUNCE_MS);
    return () => clearTimeout(timer);
  }, [input]);

  /* ---- request ------------------------------------------------------ */
  const pill =
    CATEGORY_PILLS.find((p) => p.key === category) ?? CATEGORY_PILLS[0];
  // "All" falls back to the site-wide content type from the Settings popup.
  const effectiveContentType = pill.api || contentType;
  const genreQuery = tags
    .map((g) => `genre=${encodeURIComponent(g)}`)
    .join("&");
  const offset = (page - 1) * PAGE_SIZE;
  // `null` until the deep-linked `?q=` has been read: `useTitles(null)` is a
  // no-op, so we never request a query we already know we're about to replace.
  const apiPath: string | null = urlRead
    ? `/api/titles?limit=${PAGE_SIZE}&offset=${offset}` +
      `&q=${encodeURIComponent(query)}` +
      `&contentType=${encodeURIComponent(effectiveContentType)}` +
      (genreQuery ? `&${genreQuery}` : "")
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
        if (entries[0].isIntersecting && !busy && workingSet.length >= PAGE_SIZE) {
          setPage((p) => p + 1);
        }
      },
      { rootMargin: "300px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [noStopScroll, busy, workingSet.length]);

  // Safety net for the category pills + the status filter (both client-side so
  // they always agree with what is rendered; category also goes server-side).
  const filtered = useMemo(() => {
    let list = accumulated;
    if (pill.match) {
      list = list.filter((m) => m.contentType === pill.match);
    }
    if (status !== "All") {
      list = list.filter((m) => m.status === status);
    }
    return list;
  }, [accumulated, pill.match, status]);

  /* ---- handlers ----------------------------------------------------- */
  const submitQuery = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    committed.current = input;
    setQuery(input);
    setPage(1);
  };

  const selectCategory = (key: PillKey) => {
    setCategory(key);
    setPage(1);
  };

  const onStatusChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setStatus(event.target.value as Status);
    setPage(1);
  };

  const applyTags = (next: string[]) => {
    setTags(next);
    setPage(1);
  };

  const advancedHref = query.trim()
    ? `/advanced-search?q=${encodeURIComponent(query.trim())}`
    : "/advanced-search";

  return (
    <section className="pb-16">
      {/* Subtle brand glow behind the search bar, per the reference design. */}
      <div className="bg-[linear-gradient(180deg,#2a0000_0%,#150000_30%,#000000_68%)]">
        <div className="mx-auto max-w-[1180px] px-4 pt-6 sm:px-6 sm:pt-8 lg:px-8">
          {/* Search bar + filter toggle */}
          <div className="flex items-center gap-1 rounded-full border border-white/10 bg-[#141414] p-2 pl-4 shadow-lg shadow-black/40">
            <form onSubmit={submitQuery} className="flex min-w-0 flex-1 items-center gap-3">
              <Search className="h-5 w-5 shrink-0 text-ink-muted" aria-hidden />
              <input
                type="search"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Search..."
                aria-label="Search titles"
                className="min-w-0 flex-1 bg-transparent py-1.5 text-base text-ink outline-none placeholder:text-ink-muted [&::-webkit-search-cancel-button]:cursor-pointer"
              />
            </form>
            <button
              type="button"
              onClick={() => setFilterOpen((v) => !v)}
              aria-expanded={filterOpen}
              aria-label="Toggle filters"
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full transition hover:bg-white/5"
            >
              <FunnelPlus
                className={`h-5 w-5 transition ${
                  filterOpen ? "text-brand" : "text-ink-soft"
                }`}
                aria-hidden
              />
            </button>
          </div>

          {/* Quick filters (collapsible) */}
          {filterOpen && (
            <div className="mt-3 rounded-2xl border border-white/10 bg-[#141414] p-3.5 sm:p-4">
              <div className="flex flex-wrap items-center gap-2.5">
                {/* Category */}
                <div className="flex overflow-hidden rounded-lg border border-white/12">
                  {CATEGORY_PILLS.map((p) => (
                    <button
                      key={p.key}
                      type="button"
                      aria-pressed={category === p.key}
                      onClick={() => selectCategory(p.key)}
                      className={`px-3.5 py-2 text-xs transition ${
                        category === p.key
                          ? "bg-white/[0.14] font-medium text-ink"
                          : "bg-white/[0.03] text-ink-muted hover:text-ink"
                      }`}
                    >
                      {p.key}
                    </button>
                  ))}
                </div>

                {/* Status */}
                <div className="relative">
                  <select
                    value={status}
                    onChange={onStatusChange}
                    aria-label="Filter by status"
                    className="appearance-none rounded-lg border border-white/12 bg-white/[0.03] py-2 pl-3.5 pr-9 text-xs text-ink-soft outline-none transition hover:border-white/30"
                  >
                    {STATUS_CHOICES.map((s) => (
                      <option key={s} value={s} className="bg-[#1c1c1c] text-ink">
                        {s}
                      </option>
                    ))}
                  </select>
                  <ChevronDown
                    className="pointer-events-none absolute right-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-muted"
                    aria-hidden
                  />
                </div>

                {/* Tags / Genres */}
                <div className="flex items-stretch overflow-hidden rounded-lg border border-white/12 text-xs">
                  <button
                    type="button"
                    onClick={() => setTagPickerOpen(true)}
                    className="bg-white/[0.03] px-3.5 py-2 text-ink-soft transition hover:text-ink"
                  >
                    Tags/Genres
                  </button>
                  <button
                    type="button"
                    onClick={() => setTagPickerOpen(true)}
                    aria-label={`${tags.length} tags selected`}
                    className="border-l border-white/12 bg-white/[0.03] px-3.5 py-2 font-medium tabular-nums text-ink-soft transition hover:text-ink"
                  >
                    {tags.length}
                  </button>
                </div>
              </div>

              {/* Selected tags + link to the advanced page */}
              <div className="mt-3 flex items-start justify-between gap-4">
                <p className="min-w-0 text-xs leading-relaxed">
                  {tags.length > 0 && (
                    <>
                      <span className="font-bold text-ink">tags :</span>{" "}
                      <span className="text-ink-soft">{tags.join(", ")}</span>
                    </>
                  )}
                </p>
                <Link
                  href={advancedHref}
                  className="flex shrink-0 items-center gap-1.5 text-xs text-ink-muted transition hover:text-brand-soft"
                >
                  <Target className="h-3.5 w-3.5" aria-hidden />
                  Advanced search
                </Link>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="mx-auto max-w-[1180px] px-4 sm:px-6 lg:px-8">
        <div className="mt-5 space-y-3.5">
          {busy && accumulated.length === 0 ? (
            <div aria-busy="true" className="space-y-3.5">
              {Array.from({ length: 4 }).map((_, i) => (
                <div
                  key={i}
                  className="h-[176px] w-full animate-pulse rounded-2xl bg-white/5"
                />
              ))}
            </div>
          ) : filtered.length > 0 ? (
            filtered.map((manga) => <SearchListCard key={manga.slug} manga={manga} />)
          ) : (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <p className="text-base font-medium text-ink-soft">No manga found.</p>
              <p className="mt-1 text-xs text-ink-muted">
                Try different keywords, categories, or tags.
              </p>
            </div>
          )}
        </div>

        {!noStopScroll && (
          <Pagination
            page={page}
            totalPages={filtered.length >= PAGE_SIZE ? page + 1 : page}
            onPageChange={(p) => {
              setPage(p);
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
          />
        )}
        {noStopScroll && <div ref={sentinelRef} className="h-10" />}
      </div>

      <TagPickerModal
        open={tagPickerOpen}
        selected={tags}
        onChange={applyTags}
        onClose={() => setTagPickerOpen(false)}
      />
    </section>
  );
}

export default function SearchPage() {
  return (
    <AppShell>
      <SearchContent />
    </AppShell>
  );
}
