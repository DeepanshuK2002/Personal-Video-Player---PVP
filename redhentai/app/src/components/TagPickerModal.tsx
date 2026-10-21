"use client";

import { useEffect, useMemo, useState } from "react";
import { Search, X } from "lucide-react";
import { GENRE_LIST } from "@/lib/manga";

interface TagGroup {
  letter: string;
  tags: string[];
}

/**
 * Group a tag list alphabetically (A, B, C …). Letters without any matching
 * tag are omitted so the panel stays scannable.
 */
function groupByLetter(tags: readonly string[]): TagGroup[] {
  const buckets = new Map<string, string[]>();
  for (const tag of tags) {
    const letter = tag.charAt(0).toUpperCase();
    const bucket = buckets.get(letter);
    if (bucket) bucket.push(tag);
    else buckets.set(letter, [tag]);
  }
  return Array.from(buckets.entries())
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([letter, list]) => ({ letter, tags: list }));
}

/** Zero-padded selection counter shown next to the search field ("01", "04"). */
function padCount(count: number): string {
  return count < 10 ? `0${count}` : String(count);
}

export function TagPickerModal({
  open,
  selected,
  onChange,
  onClose,
}: {
  open: boolean;
  selected: string[];
  onChange: (tags: string[]) => void;
  onClose: () => void;
}) {
  const [query, setQuery] = useState("");

  // Escape closes; focus stays inside the portal-free dialog.
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const visible = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return GENRE_LIST;
    return GENRE_LIST.filter((genre) => genre.toLowerCase().includes(term));
  }, [query]);

  const groups = useMemo(() => groupByLetter(visible), [visible]);
  const selectedSet = useMemo(() => new Set(selected), [selected]);

  const toggle = (tag: string) => {
    onChange(
      selectedSet.has(tag)
        ? selected.filter((t) => t !== tag)
        : [...selected, tag],
    );
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-label="Select tags"
    >
      <button
        type="button"
        aria-label="Close tag picker"
        onClick={onClose}
        className="absolute inset-0 cursor-default bg-black/75 backdrop-blur-sm"
      />

      <div className="relative flex max-h-[88vh] w-full max-w-[880px] flex-col overflow-hidden rounded-[28px] border border-white/10 bg-[#1c1c1c] shadow-2xl shadow-black/60">
        <div className="flex items-center justify-between px-5 pb-4 pt-6 sm:px-8 sm:pt-7">
          <h2 className="text-2xl font-normal text-ink-soft">Select tags</h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close"
            className="flex h-9 w-9 items-center justify-center rounded-full text-ink-soft transition hover:bg-white/10 hover:text-ink"
          >
            <X className="h-5 w-5" aria-hidden />
          </button>
        </div>

        <div className="px-5 sm:px-8">
          <div className="flex items-center gap-3">
            <div className="relative min-w-0 flex-1">
              <input
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="search"
                aria-label="Search tags"
                className="w-full rounded-full border border-white/10 bg-[#262626] py-3.5 pl-5 pr-12 text-sm text-ink outline-none transition placeholder:text-ink-muted focus:border-brand-soft/50"
              />
              <Search
                className="pointer-events-none absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-muted"
                aria-hidden
              />
            </div>
            <span className="shrink-0 rounded-full border border-white/10 bg-[#262626] px-5 py-3.5 text-sm font-semibold tabular-nums text-ink-soft">
              {padCount(selected.length)}
            </span>
          </div>

          {selected.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {selected.map((tag) => (
                <button
                  key={tag}
                  type="button"
                  onClick={() => toggle(tag)}
                  aria-label={`Remove ${tag}`}
                  className="flex items-center gap-2 rounded-full border border-brand px-3.5 py-1.5 text-xs text-ink transition hover:bg-brand-deep/30"
                >
                  {tag}
                  <span className="flex h-4 w-4 items-center justify-center rounded-full bg-brand text-white">
                    <X className="h-2.5 w-2.5" aria-hidden />
                  </span>
                </button>
              ))}
            </div>
          )}

          <div className="mt-4 border-t border-white/10" />
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 pb-8 pt-5 sm:px-8">
          {groups.length === 0 ? (
            <p className="py-6 text-sm text-ink-muted">No tags match.</p>
          ) : (
            groups.map((group) => (
              <div key={group.letter} className="mb-5 last:mb-0">
                <p className="mb-2.5 text-lg text-ink-faint">{group.letter}</p>
                <div className="flex flex-wrap gap-2">
                  {group.tags.map((tag) => {
                    const on = selectedSet.has(tag);
                    return (
                      <button
                        key={tag}
                        type="button"
                        aria-pressed={on}
                        onClick={() => toggle(tag)}
                        className={`rounded-full border px-4 py-1.5 text-sm transition ${
                          on
                            ? "border-brand text-ink"
                            : "border-white/10 bg-white/[0.04] text-ink-soft hover:border-white/30 hover:text-ink"
                        }`}
                      >
                        {tag}
                      </button>
                    );
                  })}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
