"use client";

import { Fragment, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Bookmark,
  BowArrow,
  Copy,
  Eye,
  Filter,
  Flame,
  LayoutGrid,
  Repeat,
  ScanSearch,
  Shuffle,
  UserRoundStar,
  X,
  type LucideIcon,
} from "lucide-react";

type Entry = {
  label: string;
  icon: LucideIcon;
  note?: string;
  disabled?: boolean;
};

const GROUPS: Entry[][] = [
  [
    { label: "Trending", icon: Flame },
    { label: "Most Watched", icon: Eye },
    { label: "Most Like", icon: UserRoundStar },
  ],
  [
    { label: "Random", icon: Repeat },
    { label: "List", icon: Copy },
    { label: "Genres", icon: LayoutGrid },
    { label: "Filter Search", icon: Filter },
    { label: "Watch Later", icon: Bookmark },
    { label: "Advance Search", icon: ScanSearch },
  ],
  [{ label: "RedArrow", icon: BowArrow, disabled: true, note: "coming soon" }],
];

export function Sidebar({ open, onClose }: { open: boolean; onClose: () => void }) {
  const router = useRouter();
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.documentElement.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.documentElement.style.overflow = "";
      window.removeEventListener("keydown", onKey);
    };
  }, [open, onClose]);

  return (
    <>
      <div
        aria-hidden={!open}
        onClick={onClose}
        className={`fixed inset-0 z-40 bg-black/60 transition-opacity duration-300 ${
          open ? "opacity-100" : "pointer-events-none opacity-0"
        }`}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-label="Site menu"
        aria-hidden={!open}
        className={`fixed inset-y-0 left-0 z-50 flex w-[70%] max-w-[260px] flex-col bg-surface shadow-2xl shadow-black/60 transition-transform duration-300 ease-out ${
          open ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="flex h-16 shrink-0 items-center justify-between bg-black px-5">
          <span className="text-xl font-semibold tracking-tight text-ink">
            read<span className="text-brand">hentai</span>
          </span>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close menu"
            className="rounded-full p-1.5 text-ink transition hover:bg-white/10"
          >
            <X className="h-6 w-6" />
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-4 py-4">
          {GROUPS.map((group, groupIndex) => (
            <Fragment key={group[0].label}>
              {groupIndex > 0 && <div className="mx-1 my-3 h-px bg-white/10" />}
              <ul>
                {group.map((entry) => (
                  <li key={entry.label}>
                    <button
                      type="button"
                      disabled={entry.disabled}
                      onClick={() => {
                        if (entry.label === "Genres") {
                          onClose();
                          router.push("/genres");
                        } else if (entry.label === "Trending") {
                          onClose();
                          router.push("/trending");
                        } else if (entry.label === "Watch Later") {
                          onClose();
                          router.push("/saved");
                        } else {
                          onClose();
                        }
                      }}
                      className="flex w-full items-center gap-4 rounded-xl px-3 py-3 text-left text-[15px] font-medium text-ink-soft transition enabled:hover:bg-white/5 enabled:hover:text-ink disabled:cursor-not-allowed disabled:text-ink-faint"
                    >
                      <entry.icon className="h-5 w-5 shrink-0" strokeWidth={1.8} aria-hidden />
                      <span>{entry.label}</span>
                      {entry.note && (
                        <span className="ml-auto text-xs font-normal text-ink-faint">{entry.note}</span>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            </Fragment>
          ))}
        </nav>
      </aside>
    </>
  );
}
