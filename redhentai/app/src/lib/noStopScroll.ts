"use client";

import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "readhentai:noStopScroll";
const EVENT = "no-stop-scroll-change";

function read(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return window.localStorage.getItem(STORAGE_KEY) === "1";
  } catch {
    return false;
  }
}

function write(value: boolean): void {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, value ? "1" : "0");
  } catch {
    // ignore
  }
  window.dispatchEvent(new CustomEvent(EVENT, { detail: value }));
}

export function useNoStopScroll(): [boolean, (value: boolean) => void] {
  const [value, setValue] = useState<boolean>(() => read());

  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<boolean>).detail;
      setValue(typeof detail === "boolean" ? detail : read());
    };
    const storageHandler = () => setValue(read());
    window.addEventListener(EVENT, handler);
    window.addEventListener("storage", storageHandler);
    return () => {
      window.removeEventListener(EVENT, handler);
      window.removeEventListener("storage", storageHandler);
    };
  }, []);

  const set = useCallback((v: boolean) => {
    setValue(v);
    write(v);
  }, []);

  return [value, set];
}
