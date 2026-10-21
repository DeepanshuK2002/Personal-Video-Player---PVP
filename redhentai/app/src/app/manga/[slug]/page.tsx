import { BookOpen, Eye, MessageSquare, Tag } from "lucide-react";
import { AppShell } from "@/components/AppShell";
import { CoverImage } from "@/components/CoverImage";
import { MangaActions } from "@/components/MangaActions";
import { MangaCard } from "@/components/MangaCard";
import { CollectionSection } from "@/components/CollectionSection";
import { CategoryRating } from "@/components/CategoryRating";
import { RatingDisplay } from "@/components/RatingDisplay";
import { resolveTitle, getChaptersForTitle, aggregateSearch } from "@/lib/providers/registry";
import { readerBaseSlug, toManga, canonicalToManga } from "@/lib/providers/normalize";
import type { Manga } from "@/lib/manga";
import { notFound } from "next/navigation";

// With cacheComponents enabled, this route streams real provider data per
// request (backed by an in-process cache). We mark it non-instant so Next
// renders it as a blocking dynamic route instead of trying to prerender a
// static shell — any title a provider serves is reachable at /manga/<slug>.
export const instant = false;

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 py-1.5 text-sm">
      <span className="shrink-0 text-ink-faint">{label}</span>
      <span className="text-right text-ink">{value}</span>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mt-8 flex items-center gap-2 text-lg font-medium tracking-tight text-ink">
      {children}
    </h2>
  );
}

/** A short, real "more like this" list from the same provider. */
async function moreLikeThis(slug: string, title: string): Promise<Manga[]> {
  try {
    const { series } = await aggregateSearch(title, { limit: 25 });
    return series
      .filter((s) => s.slug !== slug)
      .slice(0, 12)
      .map(canonicalToManga);
  } catch {
    return [];
  }
}

export default async function MangaDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const title = await resolveTitle(slug);
  if (!title) notFound();

  const manga = toManga(title);
  const { chapters } = await getChaptersForTitle(title, "en", ["omegascans"]);
  const readableChapters = chapters.filter((c) => c.readable);
  const lastReadable = readableChapters[readableChapters.length - 1];

  // Collection = this comic's own chapters (not other manga). Built as UI Manga
  // entries whose slug carries the chapter id for the reader route. The reader
  // base is derived from each CHAPTER (not the profile slug) so cross-provider
  // chapters still resolve their own source in the reader/pages routes.
  const collection: Manga[] = readableChapters.map((c) => ({
    ...manga,
    slug: `${readerBaseSlug(c)}#${c.providerChapterId}`,
    title: c.chapterTitle
      ? `Ch. ${c.chapterNumber ?? "?"} — ${c.chapterTitle}`
      : `Chapter ${c.chapterNumber ?? "?"}`,
    pages: c.pageCount ?? undefined,
    rating: null,
    views: "",
    updatedDays: c.publishedAt
      ? Math.max(0, Math.floor((Date.now() - Date.parse(c.publishedAt)) / 86_400_000))
      : undefined,
  }));

  const moreLikeThisList = await moreLikeThis(slug, title.title);

  // Real page previews come from the newest readable chapter; none if unreadable.
  let previewPages: string[] = [];
  if (readableChapters.length > 0) {
    // Leave preview as a placeholder strip; actual page fetch happens in reader.
    previewPages = [];
  }

  const uploadedStr = title.updatedAt
    ? new Date(title.updatedAt).toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "—";

  const pages = manga.pages ?? 0;

  return (
    <AppShell>
      <article className="mx-auto max-w-[1440px] px-4 pb-16 pt-4 sm:px-6 md:pt-6 lg:px-8">
        {/* Category + rating — hidden on desktop per design */}
        <CategoryRating slug={manga.slug} category={manga.contentType ?? "Manga"} />

        {/* Header — stacked on mobile, cover-left / info-right on desktop */}
        <div className="flex flex-col lg:grid lg:grid-cols-[minmax(0,340px)_minmax(0,1fr)] lg:items-start lg:gap-10">
          {/* Left column: cover, rating, read now, actions */}
          <div className="contents lg:block">
            {/* Cover */}
            <div className="order-1 mx-auto mt-4 w-full max-w-sm lg:mx-0 lg:mt-0 lg:max-w-none">
              <CoverImage
                src={manga.cover}
                alt={manga.title}
                className="aspect-[3/4] w-full rounded-xl"
              />
            </div>

            {/* Rating (below cover on desktop, after info on mobile) */}
            <div className="order-7 mt-4 lg:mt-4">
              <RatingDisplay slug={manga.slug} />
            </div>

            {/* Read Now — only when readable chapters actually exist */}
            {lastReadable && (
              <div className="order-4 mt-6 flex justify-center lg:mt-5 lg:justify-start">
                <a
                  href={`/read/${readerBaseSlug(lastReadable)}/${lastReadable.providerChapterId}`}
                  className="inline-flex w-full max-w-sm items-center justify-center gap-2 rounded-full border-2 border-brand-soft bg-brand-soft/10 px-6 py-3 text-sm font-semibold text-brand-soft transition hover:bg-brand-soft hover:text-white"
                >
                  <BookOpen className="h-5 w-5" aria-hidden />
                  Read Now
                </a>
              </div>
            )}

            {/* Like / Dislike / Save */}
            <div className="order-5 mt-3">
              <MangaActions slug={manga.slug} title={manga.title} />
            </div>
          </div>

          {/* Right column: title, badges, info */}
          <div className="contents lg:block">
            {/* Title */}
            <div className="order-2 mt-6 lg:mt-0">
              <h1 className="text-center text-2xl font-semibold tracking-tight text-ink lg:text-left">
                {manga.title}
              </h1>
              {manga.subtitle && (
                <p className="mt-1.5 text-center text-sm text-ink-soft lg:text-left">
                  {manga.subtitle}
                </p>
              )}
            </div>

            {/* Meta badges */}
            <div className="order-3 mt-3 flex items-center justify-center gap-3 text-sm text-ink-faint lg:justify-start">
              <span className="inline-flex items-center gap-1 rounded-full border border-white/10 px-2.5 py-0.5">
                <BookOpen className="h-3.5 w-3.5" aria-hidden />
                {manga.colored ? "Color" : "B&W"}
              </span>
              {manga.views && (
                <span className="inline-flex items-center gap-1">
                  <Eye className="h-3.5 w-3.5" aria-hidden />
                  {manga.views}
                </span>
              )}
            </div>

            {/* Info + Tags */}
            <div className="order-6">
              <section className="mt-8 rounded-xl border border-white/10 bg-white/5 p-4">
                <div className="grid gap-x-8 sm:grid-cols-2">
                  <div>
                    <InfoRow label="Language" value={manga.language ?? "English"} />
                    <InfoRow label="Category" value={manga.contentType ?? "Manga"} />
                    <InfoRow label="Artist" value={manga.artist ?? "—"} />
                    <InfoRow label="Circle" value={manga.circle ?? "—"} />
                    <InfoRow label="Pages" value={pages > 0 ? String(pages) : "—"} />
                    <InfoRow
                      label="Collection"
                      value={readableChapters.length > 0 ? String(readableChapters.length) : "—"}
                    />
                  </div>
                  <div>
                    <InfoRow label="Doujinshi" value={title.isAdult ? "Yes" : "No"} />
                    <InfoRow label="Parody" value={manga.parody ?? "Original"} />
                    <InfoRow label="Release Year" value={manga.releaseYear ? String(manga.releaseYear) : "—"} />
                    <InfoRow label="Uploaded" value={uploadedStr} />
                    <InfoRow label="Status" value={manga.status ?? "—"} />
                  </div>
                </div>

                {/* Tags */}
                {(manga.genres && manga.genres.length > 0) && (
                  <div className="mt-4 border-t border-white/10 pt-3">
                    <p className="mb-2 flex items-center gap-1.5 text-xs font-medium text-ink-faint">
                      <Tag className="h-3.5 w-3.5" aria-hidden />
                      Tags
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {manga.genres.map((g) => (
                        <span
                          key={g}
                          className="rounded-full border border-white/15 bg-surface px-2.5 py-1 text-xs text-ink-soft"
                        >
                          {g}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </section>
            </div>
          </div>
        </div>

        {/* Preview — real pages are only shown in the reader; the preview strip
            is hidden when a provider doesn't expose thumbnails here. */}
        {previewPages.length > 0 && (
          <section>
            <SectionTitle>Preview</SectionTitle>
          </section>
        )}

        {/* Collection — only when the title has readable chapters */}
        {readableChapters.length > 0 && <CollectionSection items={collection} />}

        {/* More like this */}
        {moreLikeThisList.length > 0 && (
          <section>
            <SectionTitle>More like this</SectionTitle>
            <div className="mt-4 grid grid-cols-2 gap-x-5 gap-y-8 md:grid-cols-4 xl:grid-cols-6">
              {moreLikeThisList.map((item) => (
                <MangaCard key={item.slug} manga={item} />
              ))}
            </div>
          </section>
        )}

        {/* Comments */}
        <section>
          <SectionTitle>
            <MessageSquare className="h-5 w-5" aria-hidden />
            Comments
          </SectionTitle>
          <div className="mt-4 flex min-h-40 items-center justify-center rounded-xl border border-white/10 bg-white/5 p-6 text-center text-sm text-ink-faint">
            Comment section via Artalk
          </div>
        </section>
      </article>

      {/* Footer */}
      <footer className="border-t border-white/10 py-6 text-center text-xs text-ink-faint">
        readhentai - We did not store any of the above content on our server. We are just an
        aggregator
      </footer>
    </AppShell>
  );
}
