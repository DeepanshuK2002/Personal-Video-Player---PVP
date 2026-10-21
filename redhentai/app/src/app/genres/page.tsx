"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Check, ChevronDown, Plus, X } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { MangaCard } from "@/components/MangaCard";
import { Pagination } from "@/components/Pagination";
import {
  GENRE_LIST,
  SORT_OPTIONS,
  STATUS_OPTIONS,
  parseViews,
  type SortOption,
  type Manga,
} from "@/lib/manga";
import { useTitles } from "@/lib/content";
import { isSaved } from "@/lib/saved";
import { useContentType } from "@/lib/contentType";
import { useNoStopScroll } from "@/lib/noStopScroll";

function recencyScore(views: string, updatedDays: number, window: number): number {
  return parseViews(views) / (1 + updatedDays / window);
}

function FilterDropdown({
  label,
  value,
  options,
  onChange,
  sort,
}: {
  label: string;
  value: string;
  options: readonly string[];
  onChange: (value: string) => void;
  sort?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: PointerEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div ref={menuRef} className="filter-wrapper">
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className={`filter-button${sort ? " sort-button" : ""}`}
      >
        <span className="filter-label">{label}:</span>
        <span className="filter-value">{value}</span>
        <ChevronDown
          className={`chevron${open ? " rotated" : ""}`}
          aria-hidden
        />
      </button>

      {open && (
        <ul role="listbox" aria-label={label} className="genres-dropdown filter-options">
          {options.map((option) => {
            const selected = option === value;
            return (
              <li key={option}>
                <button
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onClick={() => {
                    onChange(option);
                    setOpen(false);
                  }}
                  className={`dropdown-option${selected ? " selected" : ""}`}
                >
                  {option}
                  {selected && <Check className="h-4 w-4" aria-hidden />}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export default function GenresPage() {
  const contentType = useContentType();
  const [noStopScroll] = useNoStopScroll();
  const [genreOpen, setGenreOpen] = useState(false);
  const [pendingGenres, setPendingGenres] = useState<string[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [status, setStatus] = useState<string>("All");
  const [sort, setSort] = useState<string>("Latest Update");
  const [savedTick, setSavedTick] = useState(0);
  const [page, setPage] = useState<number>(1);
  useEffect(() => {
    setPage(1);
  }, [selected, contentType]);
  const [accumulated, setAccumulated] = useState<Manga[]>([]);
  const sentinelRef = useRef<HTMLDivElement>(null);

  // Genre filtering happens server-side (providers understand tags); status and
  // sort stay client-side so they flip instantly over the fetched working set.
  const genreQuery = selected.map((g) => `genre=${encodeURIComponent(g)}`).join("&");
  const { items: workingSet, loading } = useTitles(
    `/api/titles?limit=50&offset=${(page - 1) * 50}&contentType=${encodeURIComponent(contentType)}${genreQuery ? `&${genreQuery}` : ""}`,
  );

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
        if (entries[0].isIntersecting && !loading && workingSet.length >= 50) {
          setPage((p) => p + 1);
        }
      },
      { rootMargin: "300px" },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, [noStopScroll, loading, workingSet.length]);

  useEffect(() => {
    const handler = () => setSavedTick((v) => v + 1);
    window.addEventListener("saved-change", handler);
    return () => window.removeEventListener("saved-change", handler);
  }, []);

  const results = useMemo(() => {
    let list = accumulated.slice();

    if (status !== "All") {
      list = list.filter((manga) => manga.status === status);
    }

    const recentFirst = (a: (typeof list)[number], b: (typeof list)[number]) =>
      (a.updatedDays ?? 0) - (b.updatedDays ?? 0);
    const viewsDesc = (a: (typeof list)[number], b: (typeof list)[number]) =>
      parseViews(b.views) - parseViews(a.views);

    switch (sort as SortOption) {
      case "Latest Update":
        list.sort(recentFirst);
        break;
      case "New":
        list.sort((a, b) => (b.updatedDays ?? 0) - (a.updatedDays ?? 0));
        break;
      case "Hot":
        list.sort((a, b) => recencyScore(b.views, b.updatedDays ?? 0, 7) - recencyScore(a.views, a.updatedDays ?? 0, 7));
        break;
      case "Top All":
        list.sort(viewsDesc);
        break;
      case "Top Month":
        list.sort((a, b) => recencyScore(b.views, b.updatedDays ?? 0, 30) - recencyScore(a.views, a.updatedDays ?? 0, 30));
        break;
      case "Top Week":
        list.sort((a, b) => recencyScore(b.views, b.updatedDays ?? 0, 7) - recencyScore(a.views, a.updatedDays ?? 0, 7));
        break;
      case "Top Day":
        list.sort((a, b) => recencyScore(b.views, b.updatedDays ?? 0, 1) - recencyScore(a.views, a.updatedDays ?? 0, 1));
        break;
      case "Saved":
        list = list.filter((manga) => isSaved(manga.slug));
        list.sort(recentFirst);
        break;
      case "No. of Chapter":
        list.sort((a, b) => b.chapters - a.chapters);
        break;
    }

    return list;
  }, [accumulated, status, sort, savedTick]);

  const openGenrePopup = () => {
    setPendingGenres(selected);
    setGenreOpen(true);
  };

  const togglePending = (genre: string) => {
    setPendingGenres((prev) =>
      prev.includes(genre) ? prev.filter((g) => g !== genre) : [...prev, genre]
    );
  };

  const applyGenres = () => {
    setSelected(pendingGenres);
    setGenreOpen(false);
  };

  const clearGenres = () => {
    setPendingGenres([]);
  };

  const removeGenre = (genre: string) => {
    setSelected((prev) => prev.filter((g) => g !== genre));
    setPendingGenres((prev) => prev.filter((g) => g !== genre));
  };

  return (
    <AppShell>
      <section className="genres-section">
        <h1 className="genres-title">Genres</h1>

        <div className="genres-toolbar">
          <button
            type="button"
            onClick={openGenrePopup}
            className="genre-select-button"
          >
            <Plus size={14} strokeWidth={2.5} aria-hidden />
            {selected.length > 0
              ? `${selected.length} genres selected`
              : "Select your genre"}
          </button>

          <FilterDropdown
            label="Status"
            value={status}
            options={STATUS_OPTIONS}
            onChange={setStatus}
          />
          <FilterDropdown
            label="Sort by"
            value={sort}
            options={SORT_OPTIONS}
            onChange={setSort}
            sort
          />
        </div>

        {selected.length > 0 && (
          <div
            style={{
              marginTop: 16,
              display: "flex",
              flexWrap: "wrap",
              justifyContent: "center",
              gap: 8,
            }}
          >
            {selected.map((genre) => (
              <span key={genre} className="genre-badge">
                {genre}
                <button
                  type="button"
                  aria-label={`Remove ${genre}`}
                  onClick={() => removeGenre(genre)}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </span>
            ))}
          </div>
        )}

        {loading && accumulated.length === 0 ? (
          <div
            style={{
              marginTop: 32,
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
              gap: 20,
              maxWidth: 1100,
              marginLeft: "auto",
              marginRight: "auto",
            }}
            aria-busy="true"
          >
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={i}
                style={{ aspectRatio: "2 / 3", borderRadius: 12, background: "rgba(255,255,255,0.05)" }}
                className="animate-pulse"
              />
            ))}
          </div>
        ) : results.length > 0 ? (
          <div
            style={{
              marginTop: 32,
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(160px, 1fr))",
              gap: 20,
              maxWidth: 1100,
              marginLeft: "auto",
              marginRight: "auto",
            }}
          >
            {results.map((manga) => (
              <MangaCard key={manga.slug} manga={manga} />
            ))}
          </div>
        ) : (
          <p
            style={{
              marginTop: 40,
              textAlign: "center",
              fontSize: 14,
              color: "rgba(255,255,255,0.65)",
            }}
          >
            No titles match these filters.
          </p>
        )}
      </section>

      {genreOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="relative max-h-[80vh] w-full max-w-2xl overflow-y-auto rounded-xl border border-white/10 bg-[#1c1c1c] p-5 shadow-2xl">
            <button
              type="button"
              aria-label="Close"
              onClick={() => setGenreOpen(false)}
              className="absolute right-3 top-3 rounded-full p-1.5 text-ink-soft transition hover:bg-white/10 hover:text-ink"
            >
              <X className="h-5 w-5" />
            </button>
            <h2 className="mb-4 text-lg font-medium text-ink">Select genres</h2>
            <div className="flex flex-wrap gap-2">
              {GENRE_LIST.map((genre) => {
                const checked = pendingGenres.includes(genre);
                return (
                  <button
                    key={genre}
                    type="button"
                    onClick={() => togglePending(genre)}
                    className={`rounded-full border px-3 py-1.5 text-sm transition ${
                      checked
                        ? "border-brand-soft bg-brand-deep/40 text-ink"
                        : "border-white/10 bg-surface text-ink-soft hover:border-brand-soft hover:text-ink"
                    }`}
                  >
                    {genre}
                    {checked && <Check className="ml-1 inline h-3.5 w-3.5" aria-hidden />}
                  </button>
                );
              })}
            </div>
            <div className="mt-4 flex justify-between gap-2">
              <button
                type="button"
                onClick={clearGenres}
                className="rounded-lg px-4 py-2 text-sm font-medium text-ink-soft transition hover:bg-white/5 hover:text-ink"
              >
                Clear
              </button>
              <button
                type="button"
                onClick={applyGenres}
                className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-ink transition hover:bg-brand-soft"
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      )}
{!noStopScroll && (
          <Pagination
            page={page}
            totalPages={workingSet.length >= 50 ? page + 1 : page}
            onPageChange={(p) => {
              setPage(p);
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
          />
        )}
        {noStopScroll && <div ref={sentinelRef} className="h-10" />}
    </AppShell>
  );
}
