"use client";

import { useEffect, useState } from "react";
import { Clock, Trash2 } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { CoverImage } from "@/components/CoverImage";
import { clearHistory, getHistoryEntries, type HistoryEntry } from "@/lib/history";
import { resolveSlugs } from "@/lib/content";
import type { Manga } from "@/lib/manga";

interface ResolvedEntry extends HistoryEntry {
  manga: Manga | null;
}

/** "just now" / "5m ago" / "3h ago" / "2d ago" / date. */
function openedLabel(at: number): string {
  if (!at) return "Recently";
  const diff = Date.now() - at;
  if (diff < 60_000) return "Just now";
  if (diff < 3_600_000) return `${Math.floor(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.floor(diff / 3_600_000)}h ago`;
  if (diff < 7 * 86_400_000) return `${Math.floor(diff / 86_400_000)}d ago`;
  return new Date(at).toLocaleDateString();
}

export default function HistoryPage() {
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [items, setItems] = useState<ResolvedEntry[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const sync = () => setEntries(getHistoryEntries());
    sync();
    window.addEventListener("history-change", sync);
    return () => window.removeEventListener("history-change", sync);
  }, []);

  // Resolve slugs against the live catalogue; missing titles keep their stored
  // name so a removed comic still shows in the list.
  useEffect(() => {
    let cancelled = false;
    if (entries.length === 0) {
      setItems([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    resolveSlugs(entries.map((e) => e.slug))
      .then((resolved) => {
        if (cancelled) return;
        setItems(
          entries.map((e, i) => ({
            ...e,
            manga: resolved[i] && !resolved[i]!.unavailable ? resolved[i]! : null,
          })),
        );
      })
      .catch(() => {
        if (!cancelled) setItems(entries.map((e) => ({ ...e, manga: null })));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [entries]);

  const handleClear = () => {
    clearHistory();
    setEntries([]);
  };

  return (
    <AppShell>
      <section className="mx-auto max-w-[1440px] px-4 pb-10 pt-6 sm:px-6 md:pt-10 lg:px-8">
        <div className="flex items-center justify-between gap-3">
          <h1 className="flex items-center gap-2 text-2xl font-medium tracking-tight text-ink">
            <Clock className="h-6 w-6 text-ink-soft" aria-hidden />
            History
          </h1>
          {entries.length > 0 && (
            <button
              type="button"
              onClick={handleClear}
              className="inline-flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-sm text-ink-soft transition hover:border-red-400/40 hover:text-red-300"
            >
              <Trash2 className="h-4 w-4" aria-hidden />
              Clear history
            </button>
          )}
        </div>

        {loading ? (
          <div className="mt-7 space-y-3" aria-busy="true">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-24 animate-pulse rounded-xl bg-white/5" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <p className="mt-8 text-center text-ink-muted">
            No history yet — comics you open will appear here.
          </p>
        ) : (
          <ol className="mt-7 space-y-3">
            {items.map((entry) => {
              const href = `/manga/${entry.slug}`;
              return (
                <li key={entry.slug}>
                  <a
                    href={href}
                    className="group flex items-center gap-3 rounded-xl border border-white/5 bg-white/5 p-2.5 transition hover:border-brand-soft/50 hover:bg-white/10 sm:gap-4 sm:p-3"
                  >
                    <div className="h-20 w-14 shrink-0 sm:h-24 sm:w-[68px]">
                      <CoverImage
                        src={entry.manga?.cover ?? ""}
                        alt={entry.manga?.title ?? entry.title ?? entry.slug}
                        className="h-full w-full rounded-lg"
                        imgClassName="transition-transform duration-300 group-hover:scale-[1.05]"
                      />
                    </div>
                    <div className="min-w-0 flex-1">
                      <h2 className="truncate text-sm font-semibold text-ink sm:text-base">
                        {entry.manga?.title ?? entry.title ?? entry.slug}
                      </h2>
                      <div className="mt-1.5 flex flex-wrap items-center gap-2 text-xs text-ink-faint">
                        {entry.manga?.contentType && (
                          <span className="rounded-full border border-white/15 px-2 py-0.5">
                            {entry.manga.contentType}
                          </span>
                        )}
                        <span className="inline-flex items-center gap-1">
                          <Clock className="h-3 w-3" aria-hidden />
                          Opened {openedLabel(entry.at)}
                        </span>
                        {entry.manga?.unavailable && (
                          <span className="text-red-300/80">Unavailable</span>
                        )}
                      </div>
                    </div>
                  </a>
                </li>
              );
            })}
          </ol>
        )}
      </section>
    </AppShell>
  );
}
