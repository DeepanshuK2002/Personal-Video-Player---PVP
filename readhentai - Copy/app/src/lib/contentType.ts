"use client";

import { useEffect, useState } from "react";
import type { ContentType } from "@/lib/manga";

const KEY = "readhentai-content-type";
const EVENT = "content-type-change";
const DEFAULT: ContentType = "All";

export function getContentType(): ContentType {
  if (typeof window === "undefined") return DEFAULT;
  return (localStorage.getItem(KEY) as ContentType) || DEFAULT;
}

export function setContentType(value: ContentType): void {
  if (value === DEFAULT) localStorage.removeItem(KEY);
  else localStorage.setItem(KEY, value);
  window.dispatchEvent(new CustomEvent(EVENT));
}

/** Subscribe to content-type changes; returns the current selection. */
export function useContentType(): ContentType {
  const [value, setValue] = useState<ContentType>(DEFAULT);

  useEffect(() => {
    setValue(getContentType());
    const sync = () => setValue(getContentType());
    window.addEventListener(EVENT, sync);
    return () => window.removeEventListener(EVENT, sync);
  }, []);

  return value;
}
