"use client";

import { useState } from "react";

type CoverImageProps = {
  src: string;
  alt: string;
  className?: string;
  imgClassName?: string;
  children?: React.ReactNode;
};

/**
 * Cover art with a graceful fallback: if the artwork fails to load, the
 * "readhentai" wordmark is shown in its place. Overlays (badges, meta) are
 * passed as children and render above both the image and the fallback.
 */
export function CoverImage({ src, alt, className = "", imgClassName = "", children }: CoverImageProps) {
  const [failed, setFailed] = useState(false);

  return (
    <div className={`relative overflow-hidden bg-surface ${className}`}>
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 flex items-center justify-center text-sm font-semibold tracking-[0.05em] text-ink-muted"
      >
        read<span className="text-brand-soft">hentai</span>
      </span>

      {!failed && (
        <img
          src={src}
          alt={alt}
          loading="lazy"
          onError={() => setFailed(true)}
          className={`absolute inset-0 h-full w-full object-cover ${imgClassName}`}
        />
      )}

      {children}
    </div>
  );
}
