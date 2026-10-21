"use client";

import { ChevronLeft, ChevronRight } from "lucide-react";

export function Pagination({
  page = 1,
  totalPages = 5,
  onPageChange,
}: {
  page?: number;
  totalPages?: number;
  onPageChange?: (page: number) => void;
}) {
  if (totalPages <= 1) return null;

  const handlePageClick = (p: number) => {
    if (p >= 1 && p <= totalPages && p !== page) {
      onPageChange?.(p);
    }
  };

  // Generate a sliding window of visible page numbers
  const maxButtons = 5;
  let start = Math.max(1, page - Math.floor(maxButtons / 2));
  let end = start + maxButtons - 1;
  if (end > totalPages) {
    end = totalPages;
    start = Math.max(1, end - maxButtons + 1);
  }
  const pages: number[] = [];
  for (let i = start; i <= end; i++) {
    pages.push(i);
  }

  return (
    <nav
      aria-label="Pagination"
      className="mx-auto mt-10 flex max-w-[1440px] items-center justify-center gap-2 px-4 pb-10 sm:px-6 lg:px-8"
    >
      <button
        type="button"
        aria-label="Previous page"
        disabled={page <= 1}
        onClick={() => handlePageClick(page - 1)}
        className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-ink-soft transition hover:bg-white/10 hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
      >
        <ChevronLeft className="h-4 w-4" aria-hidden />
      </button>

      {start > 1 && (
        <>
          <button
            type="button"
            onClick={() => handlePageClick(1)}
            className="flex h-9 w-9 items-center justify-center rounded-full text-sm font-medium transition border-0 bg-transparent text-ink-soft hover:text-brand-soft"
          >
            1
          </button>
          {start > 2 && <span className="text-ink-faint">…</span>}
        </>
      )}

      {pages.map((p) => (
        <button
          key={p}
          type="button"
          aria-current={p === page ? "page" : undefined}
          onClick={() => handlePageClick(p)}
          className={`flex h-9 w-9 items-center justify-center rounded-full text-sm font-medium transition ${
            p === page
              ? "border-0 bg-brand-deep/40 text-brand-soft"
              : "border-0 bg-transparent text-ink-soft hover:text-brand-soft"
          }`}
        >
          {p}
        </button>
      ))}

      {end < totalPages && (
        <>
          {end < totalPages - 1 && <span className="text-ink-faint">…</span>}
          <button
            type="button"
            onClick={() => handlePageClick(totalPages)}
            className="flex h-9 w-9 items-center justify-center rounded-full text-sm font-medium transition border-0 bg-transparent text-ink-soft hover:text-brand-soft"
          >
            {totalPages}
          </button>
        </>
      )}

      <button
        type="button"
        aria-label="Next page"
        disabled={page >= totalPages}
        onClick={() => handlePageClick(page + 1)}
        className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 bg-white/5 text-ink-soft transition hover:bg-white/10 hover:text-ink disabled:cursor-not-allowed disabled:opacity-40"
      >
        <ChevronRight className="h-4 w-4" aria-hidden />
      </button>
    </nav>
  );
}
