"use client";

// Chapter reader — comix.to inspired immersive viewer.
// Features:
//   • Full-page centered image scaled to fit viewport (like comix.to).
//   • Right sidebar with floating action buttons (home, library, comments,
//     menu, fullscreen, play/pause, settings, help).
//   • Top-right chapter counter "Ch. X / Y" with prev/next arrows.
//   • Bottom-right zoom controls.
//   • Keyboard: ←/→ pages, ↑/↓ chapters, F fullscreen, Esc exit.
//   • Settings modal: reading direction, strip margin, keyboard scrolling,
//     step size, auto-scroll speed, progress bar position, preload images,
//     greyscale pages, dim pages.
//   • Chapters modal: search, filters (group/chapter/volume/date), lock
//     option, chapter list, pagination.
//   • Touch swipe for page turns.

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  ArrowLeft,
  ArrowRight,
  ArrowDown,
  ChevronLeft,
  ChevronRight,
  BookOpen,
  X as CrossIcon,
  Expand,
  Image as ImageIcon,
  Home,
  Layout,
  Minimize2,
  Menu,
  Play,
  Square,
  Settings,
  User,
  X,
} from "lucide-react";

import { useChapterPages, useTitleDetail } from "@/lib/content";
import { MangaActions } from "@/components/MangaActions";
import { addHistory } from "@/lib/history";

type PageFit = "contain" | "cover" | "actual";
type Direction = "ltr" | "rtl" | "ttb";
type ScrollMode = "fast" | "smooth";
type ProgressPos = "top-left" | "top-right" | "bottom-left" | "bottom-right" | "none";

interface ReaderSettings {
  pageFit: PageFit;
  direction: Direction;
  scrollMode: ScrollMode;
  stepSize: number;
  autoScrollSpeed: number;
  progressBar: ProgressPos;
  preloadImages: "some" | "all";
  greyscale: boolean;
  dimPages: number;
  showControls: boolean;
  background: "black" | "dark" | "sepia" | "white";
}

const DEFAULT_SETTINGS: ReaderSettings = {
  pageFit: "contain",
  direction: "ttb",
  scrollMode: "smooth",
  stepSize: 100,
  autoScrollSpeed: 150,
  progressBar: "bottom-right",
  preloadImages: "some",
  greyscale: false,
  dimPages: 0,
  showControls: true,
  background: "black",
};

const DIRECTION_LABELS: Record<Direction, string> = {
  ltr: "Left to right",
  rtl: "Right to left",
  ttb: "Top to bottom",
};

const SCROLL_MODE_LABELS: Record<ScrollMode, string> = {
  fast: "Scroll fast",
  smooth: "Scroll smooth",
};

const PROGRESS_POS_LABELS: Record<ProgressPos, string> = {
  "top-left": "Top left",
  "top-right": "Top right",
  "bottom-left": "Bottom left",
  "bottom-right": "Bottom right",
  none: "None",
};

const DIRECTION_OPTIONS: Direction[] = ["ltr", "rtl", "ttb"];
const SCROLL_MODE_OPTIONS: ScrollMode[] = ["fast", "smooth"];
const PROGRESS_POS_OPTIONS: ProgressPos[] = [
  "top-left",
  "top-right",
  "bottom-left",
  "bottom-right",
  "none",
];

export default function ReaderPage({
  params,
}: {
  params: Promise<{ slug: string; chapterId: string }>;
}) {
  const [resolved, setResolved] = useState<{ slug: string; chapterId: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    params.then((p) => {
      if (!cancelled) setResolved(p);
    });
    return () => {
      cancelled = true;
    };
  }, [params]);

  const slug = resolved?.slug ?? null;
  const chapterId = resolved?.chapterId ?? null;
  const baseSlug = slug?.split("#")[0] ?? "";

  useEffect(() => {
    if (baseSlug) addHistory(baseSlug);
  }, [baseSlug]);

  const { pages, loading, error } = useChapterPages(slug, chapterId);
  const { detail } = useTitleDetail(baseSlug);

  const [settings, setSettings] = useState<ReaderSettings>(() => {
    try {
      const raw = localStorage.getItem("readhentai:reader");
      return raw ? { ...DEFAULT_SETTINGS, ...JSON.parse(raw) } : DEFAULT_SETTINGS;
    } catch {
      return DEFAULT_SETTINGS;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem("readhentai:reader", JSON.stringify(settings));
    } catch {
      // ignore
    }
  }, [settings]);

  const [settingsOpen, setSettingsOpen] = useState(false);
  const [chaptersOpen, setChaptersOpen] = useState(false);
  const [chapterSearch, setChapterSearch] = useState("");
  const [chapterPage, setChapterPage] = useState(1);
  const [fullscreen, setFullscreen] = useState(false);
  const [controlsVisible, setControlsVisible] = useState(true);
  const controlsTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [pageIndex, setPageIndex] = useState(0);
  const [scrollProgress, setScrollProgress] = useState(0);
  const [zoom, setZoom] = useState(100);
  const [autoScrollEnabled, setAutoScrollEnabled] = useState(true);
  const [autoScrollActive, setAutoScrollActive] = useState(false);
  const autoScrollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState<Set<number>>(new Set());
  const [hoverPage, setHoverPage] = useState<number | null>(null);

  const { prevChapter, nextChapter, currentChapter } = useMemo(() => {
    if (!detail?.chapters || !chapterId) {
      return { prevChapter: null, nextChapter: null, currentChapter: null };
    }
    const readable = detail.chapters.filter((c) => c.readable);
    const sorted = readable.slice().sort((a, b) => {
      const numA = a.number !== null ? parseFloat(a.number) : NaN;
      const numB = b.number !== null ? parseFloat(b.number) : NaN;
      if (!isNaN(numA) && !isNaN(numB)) return numA - numB;
      return 0;
    });
    const idx = sorted.findIndex(
      (c) =>
        c.providerChapterId === chapterId ||
        c.id === chapterId ||
        c.id.endsWith(`:${chapterId}`),
    );
    const current = idx !== -1 ? sorted[idx] : null;
    const prev = idx > 0 ? sorted[idx - 1] : null;
    const next = idx !== -1 && idx < sorted.length - 1 ? sorted[idx + 1] : null;
    return { prevChapter: prev, nextChapter: next, currentChapter: current };
  }, [detail, chapterId]);

  const backHref = baseSlug ? `/manga/${baseSlug}` : "/";
  const chapterDisplayTitle =
    currentChapter?.title ??
    (currentChapter?.number ? `Chapter ${currentChapter.number}` : "Chapter");
  const mangaTitle = detail?.item?.title ?? baseSlug;
  const totalPages = pages.length;
  const chapterNum = currentChapter?.number ?? "?";
  const totalChapters = detail?.chapters.filter((c) => c.readable).length ?? 0;

  const toggleFullscreen = useCallback(() => {
    const el = containerRef.current;
    if (!el) return;
    if (!fullscreen) {
      el.requestFullscreen?.().then(() => setFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen?.().then(() => setFullscreen(false)).catch(() => {});
    }
  }, [fullscreen]);

  const exitFullscreen = useCallback(() => {
    if (fullscreen) {
      document.exitFullscreen?.().then(() => setFullscreen(false)).catch(() => {});
    }
  }, [fullscreen]);

  useEffect(() => {
    const onChange = () => setFullscreen(!!document.fullscreenElement);
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  const resetControlsTimer = useCallback(() => {
    if (controlsTimerRef.current) clearTimeout(controlsTimerRef.current);
    setControlsVisible(true);
    if (settings.showControls && !settingsOpen && !chaptersOpen) {
      const t = setTimeout(() => setControlsVisible(false), 3000);
      controlsTimerRef.current = t;
    }
  }, [settings.showControls, settingsOpen, chaptersOpen]);

  // Track scroll progress for the long-strip (top-to-bottom) reader.
  useEffect(() => {
    if (settings.direction !== "ttb") return;
    const onScroll = () => {
      const doc = document.documentElement;
      const scrollTop = window.scrollY || doc.scrollTop;
      const scrollHeight = doc.scrollHeight - window.innerHeight;
      setScrollProgress(scrollHeight > 0 ? Math.min(1, Math.max(0, scrollTop / scrollHeight)) : 0);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, [settings.direction, pages.length]);

  useEffect(() => {
    const onMove = () => resetControlsTimer();
    const onKey = () => resetControlsTimer();
    window.addEventListener("mousemove", onMove);
    window.addEventListener("keydown", onKey);
    const t = setTimeout(() => setControlsVisible(false), 3000);
    controlsTimerRef.current = t;
    return () => {
      if (t) clearTimeout(t);
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("keydown", onKey);
    };
  }, [resetControlsTimer]);

  useEffect(() => {
    if (!autoScrollActive) {
      if (autoScrollRef.current) clearInterval(autoScrollRef.current);
      return;
    }
    autoScrollRef.current = setInterval(() => {
    window.scrollBy(0, settings.autoScrollSpeed / 60);
  }, 1000 / 60);
  return () => {
    if (autoScrollRef.current) clearInterval(autoScrollRef.current);
  };
}, [autoScrollActive, settings.autoScrollSpeed]);

  const toggleAutoScroll = useCallback(() => {
    setAutoScrollActive((prev) => !prev);
  }, []);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      if (settingsOpen || chaptersOpen) return;

      switch (e.key) {
        case "ArrowLeft":
          e.preventDefault();
          goToPage(pageIndex - 1);
          break;
        case "ArrowRight":
          e.preventDefault();
          goToPage(pageIndex + 1);
          break;
        case "ArrowUp":
          e.preventDefault();
          window.scrollBy({ top: -((settings.stepSize / 100) * window.innerHeight), behavior: "smooth" });
          break;
        case "ArrowDown":
          e.preventDefault();
          window.scrollBy({ top: ((settings.stepSize / 100) * window.innerHeight), behavior: "smooth" });
          break;
        case "f":
        case "F":
          e.preventDefault();
          toggleFullscreen();
          break;
        case "Escape":
          exitFullscreen();
          break;
        case "s":
        case "S":
          e.preventDefault();
          setSettingsOpen((o) => !o);
          break;
        case "c":
        case "C":
          e.preventDefault();
          setChaptersOpen((o) => !o);
          break;
        case " ":
          e.preventDefault();
          if (autoScrollEnabled) toggleAutoScroll();
          break;
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [
    pageIndex,
    settings.direction,
    settingsOpen,
    chaptersOpen,
    toggleFullscreen,
    exitFullscreen,
    toggleAutoScroll,
  ]);

  const touchStartRef = useRef<{ x: number; y: number } | null>(null);
  const handleTouchStart = (e: React.TouchEvent) => {
    touchStartRef.current = { x: e.touches[0].clientX, y: e.touches[0].clientY };
  };
  const handleTouchEnd = (e: React.TouchEvent) => {
    if (!touchStartRef.current) return;
    const dx = e.changedTouches[0].clientX - touchStartRef.current.x;
    const dy = e.changedTouches[0].clientY - touchStartRef.current.y;
    const absDx = Math.abs(dx);
    const absDy = Math.abs(dy);
    if (Math.max(absDx, absDy) < 50) return;
    e.preventDefault();
    if (absDx > absDy) {
      dx > 0 ? goToPage(pageIndex - 1) : goToPage(pageIndex + 1);
    } else {
      dy > 0 ? goToNextChapter() : goToPrevChapter();
    }
    touchStartRef.current = null;
  };

  const goToPage = useCallback((index: number) => {
    if (index < 0) {
      if (prevChapter) goToChapter(prevChapter);
      return;
    }
    if (index >= totalPages) {
      if (nextChapter) goToChapter(nextChapter);
      return;
    }
    setPageIndex(index);
    resetControlsTimer();
  }, [totalPages, prevChapter, nextChapter, resetControlsTimer]);

  const goToChapter = useCallback((chapter: { id: string; providerChapterId?: string | null }) => {
    const chId = chapter.providerChapterId ?? chapter.id.split(":").pop();
    if (!chId) return;
    window.location.href = `/read/${baseSlug}/${chId}`;
  }, [baseSlug]);

  const goToPrevChapter = useCallback(() => {
    if (prevChapter) goToChapter(prevChapter);
  }, [prevChapter, goToChapter]);

  const goToNextChapter = useCallback(() => {
    if (nextChapter) goToChapter(nextChapter);
  }, [nextChapter, goToChapter]);

  useEffect(() => {
    setPageIndex(0);
    setZoom(100);
    setFailed(new Set());
  }, [chapterId]);

  const currentSrc = pages[pageIndex];
  const isFirstPage = pageIndex <= 0;
  const isLastPage = pageIndex >= totalPages - 1;

  const bgColor =
    settings.background === "black"
      ? "#000000"
      : settings.background === "dark"
      ? "#121212"
      : settings.background === "sepia"
      ? "#f5ecd9"
      : "#ffffff";

  const imgFilter =
    settings.greyscale || settings.dimPages > 0
      ? `grayscale(${settings.greyscale ? 1 : 0}) brightness(${100 - settings.dimPages}%)`
      : "none";

  return (
    <div className="min-h-dvh bg-black">
      <div
        ref={containerRef}
        className="min-h-[dvh] w-full flex flex-col"
        style={{
          minHeight: "calc(100dvh - 80px)",
          backgroundColor: bgColor,
        }}
        onTouchStart={handleTouchStart}
        onTouchEnd={handleTouchEnd}
      >
        {/* Top progress bar — comix.to style page scrubber */}
        {pages.length > 0 && (
          <div
            className="fixed top-0 left-0 right-0 z-40 h-[3px] flex transition-colors duration-200"
            style={{
              backgroundColor:
                settings.background === "white" || settings.background === "sepia"
                  ? "rgba(0, 0, 0, 0.3)"
                  : "rgba(255, 255, 255, 0.15)",
            }}
          >
            {/* Progress fill (read portion) */}
            <div
              className="h-full bg-brand transition-all duration-200"
              style={{ width: `${Math.max(0, Math.min(100, (pageIndex / Math.max(1, totalPages - 1))) * 100)}%` }}
            />
            {/* Page segments */}
            <div className="absolute top-0 left-0 right-0 bottom-0 flex px-1">
              {pages.map((_, i) => {
                const isCurrent = i === pageIndex;
                const isHovered = hoverPage === i;
                return (
                  <button
                    key={i}
                    onMouseEnter={() => setHoverPage(i)}
                    onMouseLeave={() => setHoverPage(null)}
                    onClick={() => goToPage(i)}
                    className="w-full h-full flex items-center justify-center p-[1px] transition-colors duration-100 group"
                    title={`Page ${i + 1}`}
                  >
                    <div
                      className={`w-[2px] rounded-sm transition-all duration-100 ${
                        isCurrent
                          ? "bg-brand"
                          : isHovered
                          ? "bg-white/60"
                          : "bg-white/20"
                      }`}
                    />
                  </button>
                );
              })}
            </div>

            {/* Hover tooltip */}
            {hoverPage !== null && (
              <div
                className="absolute -top-6 left-1/2 -translate-x-1/2 z-50 px-2 py-1 rounded bg-black/90 border-0 text-xs text-white whitespace-nowrap pointer-events-none"
                style={{ left: `${Math.max(0, Math.min(100, (hoverPage / Math.max(1, totalPages - 1))) * 100)}%` }}
              >
                Page {hoverPage + 1}
              </div>
            )}
          </div>
        )}

        {/* Top-right chapter counter & nav */}
        <div
          className={`fixed top-4 right-4 z-40 flex items-center gap-2 px-1.5 py-0.5 rounded-full border-0 bg-black/60 backdrop-blur-md transition-opacity duration-300 ${
            controlsVisible ? "opacity-100" : "opacity-0 pointer-events-none"
          }`}
        >
          <button
            onClick={(e) => { e.preventDefault(); goToPrevChapter(); }}
            disabled={!prevChapter}
            className="w-8 h-8 my-1 rounded-full border-0 bg-white/5 flex items-center justify-center disabled:opacity-30 transition"
            title="Previous chapter"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <span className="text-xs font-medium text-ink">
            Ch. {chapterNum}
          </span>
          <span className="text-xs text-ink-muted">/</span>
          <span className="text-xs font-medium text-ink">{totalChapters}</span>
          <button
            onClick={(e) => { e.preventDefault(); goToNextChapter(); }}
            disabled={!nextChapter}
            className="w-8 h-8 my-1 rounded-full border-0 bg-white/5 flex items-center justify-center disabled:opacity-30 transition"
            title="Next chapter"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>

        {/* Bottom-right zoom controls */}
        <div
          className={`fixed bottom-4 right-4 z-40 flex items-center gap-1 px-1.5 py-0.5 rounded-full border-0 bg-black/60 backdrop-blur-md transition-opacity duration-300 ${
            controlsVisible ? "opacity-100" : "opacity-0 pointer-events-none"
          }`}
        >
          <button
            onClick={() => setZoom((z) => Math.max(50, z - 10))}
            className="w-6 h-6 mx-1 my-1 rounded-full border-0 bg-white/5 flex items-center justify-center text-xs transition hover:bg-white/10"
          >
            −
          </button>
          <span className="w-12 text-xs text-ink text-center font-mono">{zoom}%</span>
          <button
            onClick={() => setZoom((z) => Math.min(200, z + 10))}
            className="w-6 h-6 mx-1 my-1 rounded-full border-0 bg-white/5 flex items-center justify-center text-xs transition hover:bg-white/10"
          >
            +
          </button>
        </div>

        {/* Right sidebar - floating action buttons */}
        <div
          className={`fixed top-1/2 -translate-y-1/2 right-4 z-40 flex flex-col gap-1.5 transition-opacity duration-300 ${
            controlsVisible ? "opacity-100" : "opacity-0 pointer-events-none"
          }`}
        >
          <button
            onClick={() => (window.location.href = backHref)}
            className="w-10 h-10 rounded-full border-0 bg-white/5 flex items-center justify-center hover:bg-white/10 transition"
            title="Back to title"
          >
            <BookOpen className="h-5 w-5" />
          </button>
          <button
            onClick={() => (window.location.href = "/")}
            className="w-10 h-10 rounded-full border-0 bg-white/5 flex items-center justify-center hover:bg-white/10 transition"
            title="Home"
          >
            <Home className="h-5 w-5" />
          </button>
          <button
            onClick={toggleFullscreen}
            className="w-10 h-10 rounded-full border-0 bg-white/5 flex items-center justify-center hover:bg-white/10 transition"
            title={fullscreen ? "Exit fullscreen" : "Fullscreen"}
          >
            {fullscreen ? <Minimize2 className="h-5 w-5" /> : <Expand className="h-5 w-5" />}
          </button>
          <button
            onClick={() => setSettingsOpen((o) => !o)}
            className="w-10 h-10 rounded-full border-0 bg-white/5 flex items-center justify-center hover:bg-white/10 transition"
            title="Settings (S)"
          >
            <Settings className="h-5 w-5" />
          </button>
          <button
            onClick={() => {
              const all = (detail?.chapters ?? []).filter((c) => c.readable);
              const idx = all.findIndex((c) => c.id === chapterId || c.id.endsWith(`:${chapterId}`));
              const pg = idx >= 0 ? Math.floor(idx / 10) + 1 : 1;
              setChapterPage(pg);
              setChaptersOpen((o) => !o);
            }}
            className="w-10 h-10 rounded-full border-0 bg-white/5 flex items-center justify-center hover:bg-white/10 transition"
            title="Chapters (C)"
          >
            <Menu className="h-5 w-5" />
          </button>
          {autoScrollEnabled && (
            <button
              onClick={() => setAutoScrollActive((prev) => !prev)}
              className={`w-10 h-10 rounded-full border-0 flex items-center justify-center hover:bg-white/10 transition ${
                autoScrollActive ? "bg-brand text-white" : "bg-white/5"
              }`}
              title="Auto-scroll"
            >
              {autoScrollActive ? <Square className="h-5 w-5" /> : <Play className="h-5 w-5" />}
            </button>
          )}
        </div>

        {/* Page viewer */}
        <div
          className="relative w-full flex-1 flex items-center justify-center overflow-hidden"
          style={{ minHeight: "calc(100dvh - 80px)" }}
        >
          {loading && (
            <div className="z-10 flex flex-col items-center justify-center gap-4 text-ink-muted">
              <div className="w-16 h-16 rounded-full border-4 border-white/10 border-t-brand animate-spin" />
              <p className="text-sm">Loading pages...</p>
            </div>
          )}

          {error && !loading && pages.length === 0 && (
            <div className="z-10 flex flex-col items-center justify-center gap-3 text-center p-6">
              <p className="text-sm font-medium text-ink-soft">This chapter is currently unavailable.</p>
              <p className="text-xs text-ink-faint">{error}</p>
              <button
                onClick={() => window.location.href = backHref}
                className="mt-2 text-xs text-brand-soft hover:underline"
              >
                Return to manga details
              </button>
            </div>
          )}

          {!loading && !error && pages.length === 0 && (
            <div className="z-10 flex flex-col items-center justify-center gap-3 text-center p-6">
              <p className="text-sm text-ink-faint">No readable pages available for this chapter.</p>
            </div>
          )}

          {pages.length > 0 && currentSrc && (
            <>
              {settings.direction !== "ttb" && (
                <>
                  {!isFirstPage && (
                    <button
                      onClick={(e) => { e.stopPropagation(); goToPage(pageIndex - 1); }}
                      className="absolute top-0 bottom-0 left-0 w-1/4 z-20 flex items-center justify-start pl-6 pr-2 opacity-0 hover:opacity-100 transition-opacity duration-200"
                      aria-label="Previous page"
                    >
                      <ChevronLeft className="h-16 w-16 text-white/60 hover:text-brand" />
                    </button>
                  )}
                  {!isLastPage && (
                    <button
                      onClick={(e) => { e.stopPropagation(); goToPage(pageIndex + 1); }}
                      className="absolute top-0 bottom-0 right-0 w-1/4 z-20 flex items-center justify-end pr-6 pl-2 opacity-0 hover:opacity-100 transition-opacity duration-200"
                      aria-label="Next page"
                    >
                      <ChevronRight className="h-16 w-16 text-white/60 hover:text-brand" />
                    </button>
                  )}
                </>
              )}

              {settings.direction === "ttb" ? (
                <div className="relative z-10 w-full max-w-3xl mx-auto flex flex-col gap-0">
                  {pages.map((src, i) => (
                    <img
                      key={i}
                      src={src}
                      alt={`Page ${i + 1} of ${totalPages}`}
                      loading={i < 3 ? "eager" : "lazy"}
                      style={{
                        filter: imgFilter,
                        transform: `scale(${zoom / 100})`,
                        transformOrigin: "center",
                      }}
                      className="w-full object-contain"
                      onError={() => {
                        setFailed((prev) => {
                          const next = new Set(prev);
                          next.add(i);
                          return next;
                        });
                      }}
                    />
                  ))}
                </div>
              ) : (
                <div className="relative z-10 max-w-full max-h-full flex items-center justify-center">
                  <img
                    src={currentSrc}
                    alt={`Page ${pageIndex + 1} of ${totalPages}`}
                    loading="eager"
                    style={{
                      transform: `scale(${zoom / 100})`,
                      filter: imgFilter,
                      transformOrigin: "center",
                    }}
                    className="max-w-full max-h-full object-contain shadow-2xl rounded-lg border-0"
                    onError={() => {
                      setFailed((prev) => {
                        const next = new Set(prev);
                        next.add(pageIndex);
                        return next;
                      });
                    }}
                    onLoad={() => resetControlsTimer()}
                  />
                </div>
              )}

              {failed.has(pageIndex) && (
                <div className="absolute inset-0 z-20 flex flex-col items-center justify-center rounded-lg border-0 bg-white/5 p-4 text-center text-xs text-ink-faint">
                  <ImageIcon className="h-6 w-6 mx-auto" />
                  <p>Page failed to load</p>
                  <button
                    onClick={() => {
                      setFailed((prev) => {
                        const next = new Set(prev);
                        next.delete(pageIndex);
                        return next;
                      });
                    }}
                    className="mt-1 text-xs text-brand-soft hover:underline"
                  >
                    Retry
                  </button>
                </div>
              )}
            </>
          )}

          {pages.length > 0 && (
            <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-30 flex items-center gap-2 px-3 py-1.5 rounded-full border-0 bg-white/10 backdrop-blur text-xs font-medium text-ink">
              <span>{pageIndex + 1}</span>
              <span className="text-ink-muted">/</span>
              <span>{totalPages}</span>
            </div>
          )}
        </div>

        {/* Bottom actions */}
        {pages.length > 0 && (
          <div
            className={`fixed bottom-4 left-1/2 -translate-x-1/2 z-40 flex items-center gap-2 px-1.5 py-0.5 rounded-full border-0 bg-black/60 backdrop-blur-md transition-opacity duration-300 ${
              controlsVisible ? "opacity-100" : "opacity-0 pointer-events-none"
            }`}
          >
            <MangaActions slug={baseSlug} title={mangaTitle} showCounts={false} />
          </div>
        )}

        {/* Progress bar attached to the top margin */}
        {settings.progressBar !== "none" && pages.length > 0 && (
          <div className="fixed top-0 left-0 right-0 z-40 h-1 bg-white/10">
            <div
              className="h-full bg-brand transition-all duration-150"
              style={{
                width: `${
                  settings.direction === "ttb"
                    ? scrollProgress * 100
                    : totalPages > 0
                    ? ((pageIndex + 1) / totalPages) * 100
                    : 0
                }%`,
              }}
            />
          </div>
        )}

        {/* Settings modal */}
        {settingsOpen ? (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center" onClick={() => setSettingsOpen(false)}>
            <div
              className="bg-[#1c1c1c] border-0 rounded-xl p-6 w-full max-w-md shadow-2xl max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold text-white">Settings</h2>
                <button
                  onClick={() => setSettingsOpen(false)}
                  className="w-8 h-8 rounded-full border-0 bg-white/5 flex items-center justify-center hover:bg-white/10 transition"
                >
                  <CrossIcon className="h-4 w-4" />
                </button>
              </div>

              <div className="space-y-6">
                <div>
                  <h3 className="text-xs text-ink-muted mb-3 uppercase tracking-wider">Reading direction</h3>
                  <div
                    role="tablist"
                    aria-label="Reading direction"
                    className="inline-flex w-full items-center gap-1 rounded-full border-0 bg-white/5 p-1"
                  >
                    {DIRECTION_OPTIONS.map((dir) => (
                      <button
                        key={dir}
                        type="button"
                        role="tab"
                        aria-selected={settings.direction === dir}
                        onClick={() => setSettings((s) => ({ ...s, direction: dir }))}
                        className={`flex-1 rounded-full px-3 py-1.5 text-xs font-medium transition ${
                          settings.direction === dir
                            ? "bg-brand text-white shadow-sm"
                            : "text-ink-soft hover:text-ink"
                        }`}
                      >
                        {DIRECTION_LABELS[dir]}
                      </button>
                    ))}
                  </div>
                </div>


                <div>
                  <h3 className="text-xs text-ink-muted mb-3 uppercase tracking-wider">Step size</h3>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => setSettings((s) => ({ ...s, stepSize: Math.max(10, s.stepSize - 10) }))}
                      className="w-8 h-8 rounded-full border-0 bg-white/5 flex items-center justify-center text-xs transition"
                    >
                      −
                    </button>
                    <span className="w-16 text-xs text-ink text-center font-mono">{settings.stepSize}%</span>
                    <button
                      onClick={() => setSettings((s) => ({ ...s, stepSize: Math.min(200, s.stepSize + 10) }))}
                      className="w-8 h-8 rounded-full border-0 bg-white/5 flex items-center justify-center text-xs transition"
                    >
                      +
                    </button>
                  </div>
                  <p className="text-xs text-ink-muted mt-1">
                    Step size for Arrow / Space / W / S keys, as percent of the viewport height.
                  </p>
                </div>

                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-xs text-ink-muted uppercase tracking-wider">Auto-scroll speed</h3>
                    <button
                      onClick={() => setAutoScrollEnabled((prev) => !prev)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
                        autoScrollEnabled ? "bg-brand" : "bg-white/10"
                      }`}
                      aria-pressed={autoScrollEnabled}
                      aria-label="Toggle auto-scroll"
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                          autoScrollEnabled ? "translate-x-6" : "translate-x-1"
                        }`}
                      />
                    </button>
                  </div>
                  <div className={`relative transition-opacity ${autoScrollEnabled ? "opacity-100" : "opacity-40 pointer-events-none"}`}>
                    <input
                      type="range"
                      min="10"
                      max="500"
                      step="10"
                      value={settings.autoScrollSpeed}
                      disabled={!autoScrollEnabled}
                      onChange={(e) =>
                        setSettings((s) => ({ ...s, autoScrollSpeed: Number(e.target.value) }))
                      }
                      className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-brand"
                    />
                    <span className="text-xs text-ink-muted mt-1">
                      {settings.autoScrollSpeed} px/s
                    </span>
                  </div>
                  <p className="text-xs text-ink-muted mt-1">
                    Press Space to start/stop auto-scroll.
                  </p>
                </div>

                <div>
                  <h3 className="text-xs text-ink-muted mb-3 uppercase tracking-wider">Progress bar</h3>
                  <div className="grid grid-cols-3 gap-2">
                    {PROGRESS_POS_OPTIONS.map((pos) => (
                      <button
                        key={pos}
                        onClick={() => setSettings((s) => ({ ...s, progressBar: pos }))}
                        className={`h-10 rounded-lg border-0 text-xs font-medium transition ${
                          settings.progressBar === pos
                            ? " bg-brand/10 text-brand"
                            : "border-white/10 bg-white/5 text-ink-soft hover:border-white/20"
                        }`}
                      >
                        {PROGRESS_POS_LABELS[pos]}
                      </button>
                    ))}
                  </div>
                </div>

                <div>
                  <h3 className="text-xs text-ink-muted mb-3 uppercase tracking-wider">Preload images</h3>
                  <div
                    role="tablist"
                    aria-label="Preload images"
                    className="inline-flex w-full items-center gap-1 rounded-full border-0 bg-white/5 p-1"
                  >
                    {(["some", "all"] as const).map((opt) => (
                      <button
                        key={opt}
                        type="button"
                        role="tab"
                        aria-selected={settings.preloadImages === opt}
                        onClick={() => setSettings((s) => ({ ...s, preloadImages: opt }))}
                        className={`flex-1 rounded-full px-3 py-1.5 text-xs font-medium transition ${
                          settings.preloadImages === opt
                            ? "bg-brand text-white shadow-sm"
                            : "text-ink-soft hover:text-ink"
                        }`}
                      >
                        {opt === "some" ? "Preload some" : "Preload all"}
                      </button>
                    ))}
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={settings.greyscale}
                    onChange={() => setSettings((s) => ({ ...s, greyscale: !s.greyscale }))}
                    className="w-4 h-4 rounded border-white/10 bg-[#1a1a1a] text-brand focus:ring-brand"
                  />
                  <label className="text-xs text-ink-soft">Greyscale pages</label>
                </div>

                <div>
                  <h3 className="text-xs text-ink-muted mb-2 uppercase tracking-wider">Dim pages</h3>
                  <div className="relative">
                    <input
                      type="range"
                      min="0"
                      max="100"
                      step="5"
                      value={settings.dimPages}
                      onChange={(e) =>
                        setSettings((s) => ({ ...s, dimPages: Number(e.target.value) }))
                      }
                      className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-brand"
                    />
                    <span className="text-xs text-ink-muted">{settings.dimPages}%</span>
                  </div>
                </div>

                <div className="pt-4 border-t border-white/10">
                  <button
                    onClick={() => setSettings(DEFAULT_SETTINGS)}
                    className="w-full py-2 rounded-lg border-0 text-xs text-ink-soft hover:bg-white/5 transition"
                  >
                    Reset to defaults
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : null}

        {/* Chapters modal */}
        {chaptersOpen ? (
          <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center" onClick={() => setChaptersOpen(false)}>
            <div
              className="bg-[#1c1c1c] border-0 rounded-xl p-6 w-full max-w-2xl shadow-2xl flex flex-col max-h-[90vh] overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold text-white">Chapters</h2>
                <button
                  onClick={() => setChaptersOpen(false)}
                  className="w-8 h-8 rounded-full border-0 bg-white/5 flex items-center justify-center hover:bg-white/10 transition"
                >
                  <CrossIcon className="h-4 w-4" />
                </button>
              </div>

              <div className="mb-4">
                <input
                  type="text"
                  value={chapterSearch}
                  onChange={(e) => {
                    setChapterSearch(e.target.value);
                    setChapterPage(1);
                  }}
                  placeholder="Search chapters"
                  className="w-full px-4 py-2 rounded-full border-0 bg-[#0a0a0a] text-xs text-ink focus:outline-none focus:border-brand"
                />
              </div>

              {(() => {
                const allChapters = (detail?.chapters ?? []).filter((c) => c.readable);
                const filtered = chapterSearch.trim()
                  ? allChapters.filter((c) =>
                      (c.title ?? "").toLowerCase().includes(chapterSearch.toLowerCase()) ||
                      String(c.number ?? "").includes(chapterSearch),
                    )
                  : allChapters;
                const pageSize = 10;
                const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
                const safePage = Math.min(chapterPage, totalPages);
                const start = (safePage - 1) * pageSize;
                const pageChapters = filtered.slice(start, start + pageSize);

                // Determine current page from the currently reading chapter.
                const currentIndex = filtered.findIndex(
                  (c) => c.id === chapterId || c.id.endsWith(`:${chapterId}`),
                );
                const currentPage = currentIndex >= 0 ? Math.floor(currentIndex / pageSize) + 1 : safePage;

                return (
                  <>
                    <div className="flex-1 overflow-y-auto pr-2 mb-4 no-scrollbar space-y-2">
                      {pageChapters.map((ch, i) => {
                        const isCurrent = ch.id === chapterId || ch.id.endsWith(`:${chapterId}`);
                        return (
                          <button
                            key={ch.id}
                            onClick={() => {
                              setChaptersOpen(false);
                              goToChapter(ch);
                            }}
                            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border-0 text-left transition ${
                              isCurrent
                                ? " bg-brand/10 text-brand"
                                : "bg-white/5 text-ink-soft hover:bg-white/10 hover:border-white/20"
                            }`}
                          >
                            <span className="w-6 shrink-0 text-center text-xs font-bold text-ink-faint">
                              {String(start + i + 1).padStart(2, "0")}
                            </span>
                            <div className="flex-1 flex items-center justify-between gap-3">
                              <div>
                                <div className="text-sm font-medium">{ch.title ?? `Chapter ${ch.number ?? "?"}`}</div>
                              </div>
                              <div className="text-xs text-ink-muted shrink-0">
                                {ch.publishedAt ? new Date(ch.publishedAt).toLocaleDateString() : ""}
                              </div>
                            </div>
                          </button>
                        );
                      })}
                    </div>

                    <div className="flex items-center justify-center gap-2">
                      <button
                        onClick={() => setChapterPage(Math.max(1, safePage - 1))}
                        disabled={safePage <= 1}
                        className="w-8 h-8 rounded-full border-0 bg-white/5 text-xs text-ink-soft disabled:opacity-30"
                      >
                        ‹
                      </button>
                      {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => {
                        const inWindow =
                          p >= Math.max(1, safePage - 2) && p <= Math.min(totalPages, safePage + 2);
                        const show = p === 1 || p === totalPages || inWindow;
                        if (!show) {
                          if (p === 2 && safePage > 3) {
                            return (
                              <span key={`ellipsis-${p}`} className="px-1 text-xs text-ink-muted">
                                …
                              </span>
                            );
                          }
                          if (p === totalPages - 1 && safePage < totalPages - 2) {
                            return (
                              <span key={`ellipsis-${p}`} className="px-1 text-xs text-ink-muted">
                                …
                              </span>
                            );
                          }
                          return null;
                        }
                        return (
                          <button
                            key={p}
                            onClick={() => setChapterPage(p)}
                            className={`w-8 h-8 rounded-full border-0 text-xs font-medium transition ${
                              p === safePage
                                ? " bg-brand/10 text-brand"
                                : "bg-white/5 text-ink-soft hover:bg-white/10"
                            }`}
                          >
                            {p}
                          </button>
                        );
                      })}
                      <button
                        onClick={() => setChapterPage(Math.min(totalPages, safePage + 1))}
                        disabled={safePage >= totalPages}
                        className="w-8 h-8 rounded-full border-0 bg-white/5 text-xs text-ink-soft disabled:opacity-30"
                      >
                        ›
                      </button>
                    </div>
                  </>
                );
              })()}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
}
