"use client";

import { createPortal } from "react-dom";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { Check, ChevronDown, Link2, Menu, Moon, Search, Settings, Sun, UserRoundPlus, X } from "lucide-react";
import { CONTENT_TYPE_OPTIONS, type ContentType } from "@/lib/manga";
import { setContentType, useContentType } from "@/lib/contentType";
import { useNoStopScroll } from "@/lib/noStopScroll";
import {
  LANGUAGES,
  type LanguageCode,
  setComicsLanguage,
  setLanguagesLinked,
  setSiteLanguage,
  useComicsLanguage,
  useLanguagesLinked,
  useSiteLanguage,
} from "@/lib/language";

function LanguageDropdown({
  value,
  onChange,
  disabled,
}: {
  value: LanguageCode;
  onChange: (code: LanguageCode) => void;
  disabled?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const [coords, setCoords] = useState<{ top: number; left: number; width: number } | null>(null);
  const rafRef = useRef<number>(0);

  const updatePosition = useCallback(() => {
    const el = triggerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    const menuHeight = menuRef.current?.offsetHeight ?? 260;
    const spaceBelow = window.innerHeight - rect.bottom;
    const openUp = spaceBelow < menuHeight && rect.top > menuHeight;
    const top = openUp ? Math.max(8, rect.top - menuHeight - 4) : rect.bottom + 4;
    const width = Math.min(240, window.innerWidth - 32);
    const left = Math.min(Math.max(8, rect.left), window.innerWidth - width - 8);
    setCoords({ top, left, width });
  }, []);

  const scheduleUpdate = useCallback(() => {
    if (rafRef.current) return;
    rafRef.current = requestAnimationFrame(() => {
      rafRef.current = 0;
      updatePosition();
    });
  }, [updatePosition]);

  useEffect(() => {
    if (!open) return;
    const raf = requestAnimationFrame(() => updatePosition());
    const onResize = () => scheduleUpdate();
    const onScroll = () => scheduleUpdate();
    window.addEventListener("resize", onResize);
    window.addEventListener("scroll", onScroll, true);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
      window.removeEventListener("scroll", onScroll, true);
      if (rafRef.current) {
        cancelAnimationFrame(rafRef.current);
        rafRef.current = 0;
      }
    };
  }, [open, updatePosition, scheduleUpdate]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    };
    const onClick = (e: MouseEvent) => {
      if (
        menuRef.current &&
        !menuRef.current.contains(e.target as Node) &&
        triggerRef.current &&
        !triggerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onClick);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onClick);
    };
  }, [open]);

  useEffect(() => {
    if (open && menuRef.current) {
      const sel = menuRef.current.querySelector('[aria-selected="true"]') as HTMLElement | null;
      (sel ?? menuRef.current.querySelector("button"))?.focus();
    }
  }, [open, coords]);

  const selected = LANGUAGES.find((l) => l.code === value);

  const handleSelect = (code: LanguageCode) => {
    onChange(code);
    setOpen(false);
    triggerRef.current?.focus();
  };

  const handleMenuKeyDown = (e: React.KeyboardEvent) => {
    const buttons = menuRef.current?.querySelectorAll("button[role='option']") ?? [];
    const arr = Array.from(buttons) as HTMLButtonElement[];
    const idx = arr.findIndex((b) => b === document.activeElement);
    if (e.key === "ArrowDown") {
      e.preventDefault();
      arr[(idx + 1) % arr.length]?.focus();
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      arr[(idx - 1 + arr.length) % arr.length]?.focus();
    } else if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      (document.activeElement as HTMLButtonElement)?.click();
    } else if (e.key === "Escape") {
      setOpen(false);
      triggerRef.current?.focus();
    }
  };

  return (
    <>
      <button
        ref={triggerRef}
        type="button"
        disabled={disabled}
        onClick={() => setOpen((v) => !v)}
        className="filter-button w-full"
        style={{ justifyContent: "space-between", minWidth: 0 }}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="filter-value">{selected?.label}</span>
        <ChevronDown className={`chevron mr-2 ${open ? "rotated" : ""}`} aria-hidden />
      </button>
      {open &&
        coords &&
        typeof document !== "undefined" &&
        createPortal(
          <div
            ref={menuRef}
            role="listbox"
            tabIndex={-1}
            onKeyDown={handleMenuKeyDown}
            className="genres-dropdown filter-options"
            style={{
              position: "fixed",
              top: coords.top,
              left: coords.left,
              width: coords.width,
              minWidth: 0,
              maxWidth: "calc(100vw - 32px)",
              background: "#1c1c1c",
              zIndex: 100,
              maxHeight: "40vh",
              overflowY: "auto",
            }}
          >
            {LANGUAGES.map((lang) => {
              const isSelected = lang.code === value;
              return (
                <button
                  key={lang.code}
                  type="button"
                  role="option"
                  aria-selected={isSelected}
                  onClick={() => handleSelect(lang.code)}
                  className={`dropdown-option${isSelected ? " selected" : ""}`}
                >
                  {lang.label}
                  {isSelected && <Check className="h-4 w-4" aria-hidden />}
                </button>
              );
            })}
          </div>,
          document.body
        )}
    </>
  );
}

export function Header({ onMenu }: { onMenu: () => void }) {
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [mobileSearchOpen, setMobileSearchOpen] = useState(false);
  const [theme, setTheme] = useState<"dark" | "light">("dark");
  const contentType = useContentType();
  const [noStopScroll, setNoStopScroll] = useNoStopScroll();
  const siteLanguage = useSiteLanguage();
  const comicsLanguage = useComicsLanguage();
  const languagesLinked = useLanguagesLinked();
  const modalRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!settingsOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [settingsOpen]);

  useEffect(() => {
    if (!settingsOpen) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSettingsOpen(false);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [settingsOpen]);

  return (
    <header className="sticky top-0 z-50 bg-black">
      <div className="relative mx-auto flex h-16 max-w-[1440px] items-center gap-3 px-4 sm:px-6 md:h-20 lg:px-8">
        <button
          type="button"
          onClick={onMenu}
          aria-label="Open menu"
          className="-ml-2 rounded-full p-2 text-ink transition hover:bg-white/10"
        >
          <Menu className="h-6 w-6" strokeWidth={2.5} />
        </button>

        <a href="/" className="hidden text-xl font-semibold tracking-tight text-ink md:block">
          readhentai
        </a>

        <a
          href="/"
          className="absolute left-1/2 -translate-x-1/2 text-xl font-semibold tracking-tight text-ink md:hidden"
        >
          readhentai
        </a>

        <form action="/search" className="hidden flex-1 justify-center md:flex">
          <label className="flex w-full max-w-md items-center gap-2.5 rounded-full bg-surface px-4 py-2.5 ring-1 ring-inset ring-white/5 transition focus-within:ring-brand-soft/60">
            <Search className="h-4 w-4 shrink-0 text-ink-faint" aria-hidden />
            <input
              type="search"
              name="q"
              placeholder="Search manga…"
              className="w-full bg-transparent text-sm text-ink outline-none placeholder:text-ink-faint"
            />
          </label>
        </form>

        <div className="ml-auto flex items-center gap-1 md:ml-0">
          <button
            type="button"
            aria-label="Search"
            onClick={() => setMobileSearchOpen((v) => !v)}
            className={`rounded-full p-1.5 transition md:hidden sm:p-2 ${
              mobileSearchOpen ? "bg-white/10 text-brand-soft" : "text-ink hover:bg-white/10"
            }`}
          >
            <Search className="h-5 w-5 sm:h-6 sm:w-6" />
          </button>
          <button
            type="button"
            aria-label="Settings"
            onClick={() => setSettingsOpen(true)}
            className="rounded-full p-1.5 text-ink transition hover:bg-white/10 sm:p-2"
          >
            <Settings className="h-5 w-5 sm:h-6 sm:w-6" />
          </button>
          <button
            type="button"
            aria-label="Sign in"
            className="rounded-full p-1.5 text-ink transition hover:bg-white/10 sm:p-2"
          >
            <UserRoundPlus className="h-5 w-5 sm:h-6 sm:w-6" />
          </button>
        </div>
      </div>

      {mobileSearchOpen && (
        <div className="border-t border-white/10 bg-black px-4 py-2.5 md:hidden">
          <form action="/search" onSubmit={() => setMobileSearchOpen(false)}>
            <label className="flex w-full items-center gap-2.5 rounded-full bg-surface px-4 py-2 ring-1 ring-inset ring-white/5 focus-within:ring-brand-soft/60">
              <Search className="h-4 w-4 shrink-0 text-ink-faint" aria-hidden />
              <input
                type="search"
                name="q"
                autoFocus
                placeholder="Search manga…"
                className="w-full bg-transparent text-sm text-ink outline-none placeholder:text-ink-faint"
              />
            </label>
          </form>
        </div>
      )}

      {settingsOpen && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/55 p-4">
          <div
            ref={modalRef}
            className="relative flex max-h-[calc(100dvh-48px)] w-full max-w-sm flex-col rounded-xl border border-white/10 bg-[#1c1c1c] shadow-2xl"
          >
            <div className="flex shrink-0 items-center justify-between px-5 py-4">
              <h2 className="text-lg font-medium text-ink">Settings</h2>
              <button
                type="button"
                aria-label="Close"
                onClick={() => setSettingsOpen(false)}
                className="rounded-full p-1.5 text-ink-soft transition hover:bg-white/10 hover:text-ink"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div ref={contentRef} className="flex-1 overflow-y-auto px-5 py-4">
              <div className="space-y-4">
                <div>
                  <p className="mb-2 text-sm font-medium text-ink-soft">Theme</p>
                  <div className="flex items-center gap-1 rounded-full bg-white/5 p-1">
                    <button
                      type="button"
                      onClick={() => setTheme("dark")}
                      className={`flex flex-1 items-center justify-center gap-2 rounded-full px-3 py-2 text-sm font-medium transition ${
                        theme === "dark"
                          ? "bg-brand text-white shadow-sm"
                          : "text-ink-soft hover:text-ink"
                      }`}
                    >
                      <Moon className="h-4 w-4" aria-hidden />
                      Dark
                    </button>
                    <button
                      type="button"
                      onClick={() => setTheme("light")}
                      className={`flex flex-1 items-center justify-center gap-2 rounded-full px-3 py-2 text-sm font-medium transition ${
                        theme === "light"
                          ? "bg-[#ff555e] text-white shadow-sm"
                          : "text-ink-soft hover:text-ink"
                      }`}
                    >
                      <Sun className="h-4 w-4" aria-hidden />
                      Light
                    </button>
                  </div>
                </div>

                <div>
                  <p className="mb-2 text-sm font-medium text-ink-soft">Content type</p>
                  <div className="flex items-center gap-1 rounded-full bg-white/5 p-1">
                    {CONTENT_TYPE_OPTIONS.map((option: ContentType) => (
                      <button
                        key={option}
                        type="button"
                        onClick={() => setContentType(option)}
                        className={`flex flex-1 items-center justify-center rounded-full px-2 py-2 text-sm font-medium transition ${
                          contentType === option
                            ? "bg-brand text-white shadow-sm"
                            : "text-ink-soft hover:text-ink"
                        }`}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                </div>

                {/* No-stop scrolling */}
                <div className="rounded-lg border border-white/10 bg-white/5 p-3">
                  <p className="mb-2 text-sm font-medium text-ink-soft">No-stop scrolling</p>
                  <p className="mb-3 text-xs text-ink-faint">
                    Doom-scroll instead of using page numbers.
                  </p>
                  <button
                    type="button"
                    onClick={() => setNoStopScroll(!noStopScroll)}
                    className={`flex w-full items-center justify-between rounded-full px-4 py-2 text-sm font-medium transition ${
                      noStopScroll
                        ? "bg-brand text-white shadow-sm"
                        : "bg-surface text-ink-soft hover:text-ink"
                    }`}
                  >
                    <span>{noStopScroll ? "On" : "Off"}</span>
                    <span className="text-xs opacity-80">{noStopScroll ? "Unlimited" : "Paginated"}</span>
                  </button>
                </div>

                {/* Language settings */}
                <div className="space-y-3 rounded-lg border border-white/10 bg-white/5 p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="flex-1 min-w-0">
                      <label className="mb-1 block text-xs font-medium text-ink-faint">Site language</label>
                      <LanguageDropdown
                        value={siteLanguage}
                        onChange={setSiteLanguage}
                      />
                    </div>
                    <button
                      type="button"
                      onClick={() => setLanguagesLinked(!languagesLinked)}
                      className={`mt-5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full transition ${
                        languagesLinked
                          ? "bg-brand-deep/40 text-brand-soft"
                          : "bg-surface text-ink-soft hover:text-ink"
                      }`}
                      aria-pressed={languagesLinked}
                      title={languagesLinked ? "Linked: both change together" : "Unlinked: change independently"}
                    >
                      <Link2 className="h-4 w-4 rotate-12" aria-hidden />
                    </button>
                    <div className="flex-1 min-w-0">
                      <label className="mb-1 block text-xs font-medium text-ink-faint">Comics language</label>
                      <LanguageDropdown
                        value={comicsLanguage}
                        onChange={setComicsLanguage}
                        disabled={languagesLinked}
                      />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </header>
  );
}


