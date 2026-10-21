"use client";

import { useEffect, useState } from "react";
import { AppShell } from "@/components/AppShell";
import { MangaCard } from "@/components/MangaCard";
import { Pagination } from "@/components/Pagination";
import { getSaved, type SavedItem } from "@/lib/saved";
import { resolveSlugs } from "@/lib/content";
import type { Manga } from "@/lib/manga";
import { useContentType } from "@/lib/contentType";

export default function SavedPage() {
  const contentType = useContentType();
  const [saved, setSaved] = useState<SavedItem[]>([]);
  const [resolved, setResolved] = useState<Manga[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setSaved(getSaved());
    const handler = () => setSaved(getSaved());
    window.addEventListener("saved-change", handler);
    return () => window.removeEventListener("saved-change", handler);
  }, []);

  // Resolve each saved slug against the live catalogue. Titles the provider no
  // longer serves are returned with `unavailable: true` and rendered as a
  // graceful "unavailable" card instead of being dropped.
  useEffect(() => {
    let cancelled = false;
    if (saved.length === 0) {
      setResolved([]);
      setLoading(false);
      return;
    }
    setLoading(true);
    resolveSlugs(saved.map((s) => s.slug))
      .then((items) => {
        if (cancelled) return;
        setResolved(items.filter((m): m is Manga => Boolean(m)));
      })
      .catch(() => {
        if (!cancelled) setResolved([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [saved]);

  const savedManga: Manga[] = resolved;

  const filteredManga =
    contentType === "All"
      ? savedManga
      : savedManga.filter((m) =>
          contentType === "Comics"
            ? m.contentType === "Manhua" || m.contentType === "Comics"
            : m.contentType === contentType,
        );

  return (
    <AppShell>
      <section className="mx-auto max-w-[1440px] bg-[linear-gradient(180deg,#6f0000_0%,#430000_38%,#180000_72%,#000000_100%)] px-4 pb-10 pt-6 sm:px-6 md:pt-10 lg:px-8">
        <h1 className="text-center text-2xl font-medium tracking-tight text-ink">Saved</h1>
        {loading ? (
          <div className="mt-7 grid grid-cols-2 gap-x-5 gap-y-8 md:grid-cols-4 xl:grid-cols-6" aria-busy="true">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="aspect-[2/3] w-full animate-pulse rounded-xl bg-white/5" />
            ))}
          </div>
        ) : filteredManga.length === 0 ? (
          <p className="mt-8 text-center text-ink-muted">No saved manga yet.</p>
        ) : (
          <div className="mt-7 grid grid-cols-2 gap-x-5 gap-y-8 md:grid-cols-4 xl:grid-cols-6">
            {filteredManga.map((manga) => (
              <MangaCard key={manga.slug} manga={manga} twoLineTitle />
            ))}
          </div>
        )}
      </section>
      
    </AppShell>
  );
}
