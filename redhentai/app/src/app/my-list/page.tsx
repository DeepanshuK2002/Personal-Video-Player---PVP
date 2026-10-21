"use client";

import { useMemo } from "react";
import { CheckCheck } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { MangaCard } from "@/components/MangaCard";
import { useFollowUpdates } from "@/lib/content";
import { setSeenChapters } from "@/lib/follow";
import type { Manga } from "@/lib/manga";

export default function MyListPage() {
  const { follows, updates, loading } = useFollowUpdates();

  const rows = useMemo(() => {
    return follows
      .map((follow) => ({ follow, entry: updates[follow.slug] }))
      .filter((row): row is { follow: (typeof follows)[number]; entry: NonNullable<(typeof updates)[string]> } =>
        Boolean(row.entry),
      )
      .map((row) => {
        const latest = row.entry.latestChapter;
        const isNew =
          row.follow.seenChapterId != null &&
          latest != null &&
          latest.id !== row.follow.seenChapterId;
        return { ...row, latest, isNew };
      })
      .sort((a, b) => {
        if (a.isNew !== b.isNew) return a.isNew ? -1 : 1;
        const at = a.latest?.publishedAt ?? "";
        const bt = b.latest?.publishedAt ?? "";
        return bt.localeCompare(at);
      });
  }, [follows, updates]);

  const newCount = rows.filter((r) => r.isNew).length;

  const markAllSeen = () => {
    const entries = rows
      .map((r) => ({ slug: r.follow.slug, chapterId: r.latest?.id, chapterNumber: r.latest?.number }))
      .filter((e): e is { slug: string; chapterId: string; chapterNumber: string | null } =>
        Boolean(e.chapterId),
      );
    if (entries.length > 0) setSeenChapters(entries);
  };

  return (
    <AppShell>
      <section className="mx-auto max-w-[1440px] bg-[linear-gradient(180deg,#6f0000_0%,#430000_38%,#180000_72%,#000000_100%)] px-4 pb-10 pt-6 sm:px-6 md:pt-10 lg:px-8">
        <div className="flex items-center justify-center gap-3">
          <h1 className="text-center text-2xl font-medium tracking-tight text-ink">My List</h1>
          {newCount > 0 && (
            <span className="rounded-full bg-brand px-2.5 py-0.5 text-xs font-bold text-white">
              {newCount} new
            </span>
          )}
        </div>

        {!loading && rows.length > 0 && newCount > 0 && (
          <div className="mt-4 flex justify-center">
            <button
              type="button"
              onClick={markAllSeen}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-ink-soft transition hover:border-brand-soft hover:text-ink"
            >
              <CheckCheck className="h-4 w-4" aria-hidden />
              Mark all as seen
            </button>
          </div>
        )}

        {loading ? (
          <div className="mt-7 grid grid-cols-2 gap-x-5 gap-y-8 md:grid-cols-4 xl:grid-cols-6" aria-busy="true">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="aspect-[2/3] w-full animate-pulse rounded-xl bg-white/5" />
            ))}
          </div>
        ) : rows.length === 0 ? (
          <p className="mt-8 text-center text-ink-muted">
            No titles in your list yet. Follow titles to see their newest updates here.
          </p>
        ) : (
          <div className="mt-7 grid grid-cols-2 gap-x-5 gap-y-8 md:grid-cols-4 xl:grid-cols-6">
            {rows.map(({ follow, entry, latest, isNew }) => {
              const manga: Manga = { ...entry.manga, title: follow.title || entry.manga.title };
              const caption = latest
                ? latest.number
                  ? `Latest: Ch. ${latest.number}`
                  : "New chapter"
                : "No chapters yet";
              return (
                <MangaCard
                  key={follow.slug}
                  manga={manga}
                  twoLineTitle
                  badge={isNew ? "New" : undefined}
                  caption={caption}
                />
              );
            })}
          </div>
        )}
      </section>
    </AppShell>
  );
}
