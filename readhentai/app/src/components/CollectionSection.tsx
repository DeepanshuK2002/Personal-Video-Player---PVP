"use client";

import { useState } from "react";
import { Columns3, Eye, Images, List } from "lucide-react";
import { CoverImage } from "@/components/CoverImage";
import { MangaCard } from "@/components/MangaCard";
import type { Manga } from "@/lib/manga";

/**
 * Collection list with a list/column view toggle inline to the right of the
 * heading. Rendered only when the title actually has readable chapters. Chapter
 * slugs carry a `#ch-<chapterId>` suffix and link to the reader route.
 */
function readerHref(slug: string): string {
  const hashAt = slug.indexOf("#ch-");
  if (hashAt === -1) return `/manga/${slug}`;
  const base = slug.slice(0, hashAt);
  const chapterId = slug.slice(hashAt + 4);
  return `/read/${base}/${chapterId}`;
}

export function CollectionSection({ items }: { items: Manga[] }) {
  const [view, setView] = useState<"list" | "column">("column");

  return (
    <section>
      <div className="mt-8 flex items-center justify-between gap-3">
        <h2 className="text-lg font-medium tracking-tight text-ink">Collection</h2>

        <div
          role="tablist"
          aria-label="Collection view mode"
          className="inline-flex shrink-0 items-center gap-1 rounded-full border border-white/10 bg-white/5 p-1"
        >
          <button
            type="button"
            role="tab"
            aria-selected={view === "list"}
            aria-label="List view"
            onClick={() => setView("list")}
            className={`flex h-7 w-7 items-center justify-center rounded-full transition sm:h-8 sm:w-8 ${
              view === "list" ? "bg-brand text-white shadow-sm" : "text-ink-soft hover:text-ink"
            }`}
          >
            <List className="h-3.5 w-3.5 sm:h-4 sm:w-4" aria-hidden />
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={view === "column"}
            aria-label="Column view"
            onClick={() => setView("column")}
            className={`flex h-7 w-7 items-center justify-center rounded-full transition sm:h-8 sm:w-8 ${
              view === "column" ? "bg-brand text-white shadow-sm" : "text-ink-soft hover:text-ink"
            }`}
          >
            <Columns3 className="h-3.5 w-3.5 sm:h-4 sm:w-4" aria-hidden />
          </button>
        </div>
      </div>

      {view === "column" ? (
        <div className="mt-4 grid grid-cols-2 gap-x-5 gap-y-8 md:grid-cols-4 xl:grid-cols-6">
          {items.map((item, i) => (
            <MangaCard
              key={item.slug}
              manga={item}
              titlePrefix={String(i + 1).padStart(2, "0")}
            />
          ))}
        </div>
      ) : (
        <ol className="mt-4 space-y-3">
          {items.map((item, i) => (
            <li key={item.slug}>
              <a
                href={readerHref(item.slug)}
                className="group flex items-center gap-3 rounded-xl border border-white/5 bg-white/5 p-2.5 transition hover:border-brand-soft/50 hover:bg-white/10 sm:gap-4 sm:p-3"
              >
                <span className="w-6 shrink-0 text-center text-lg font-bold text-ink-faint sm:w-8 sm:text-xl">
                  {String(i + 1).padStart(2, "0")}
                </span>

                <CoverImage
                  src={item.cover}
                  alt={item.title}
                  className="h-20 w-14 shrink-0 rounded-lg sm:h-24 sm:w-[68px]"
                  imgClassName="transition-transform duration-300 group-hover:scale-[1.05]"
                />

                <div className="min-w-0 flex-1">
                  <h3 className="truncate text-sm font-semibold text-ink sm:text-base">
                    {item.title}
                  </h3>
                  <div className="mt-2 flex items-center gap-3 text-xs text-ink-faint sm:gap-4">
                    <span className="inline-flex items-center gap-1">
                      <Eye className="h-3.5 w-3.5" aria-hidden />
                      {item.views} Views
                    </span>
                    <span className="inline-flex items-center gap-1">
                      <Images className="h-3.5 w-3.5" aria-hidden />
                      {item.pages ?? 0}
                    </span>
                  </div>
                </div>
              </a>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
