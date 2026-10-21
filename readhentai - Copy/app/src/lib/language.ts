"use client";

import { useEffect, useState } from "react";

export const LANGUAGES = [
  { code: "en", label: "English (EN)" },
  { code: "es", label: "Español (ES)" },
  { code: "fr", label: "Français (FR)" },
  { code: "it", label: "Italiano (IT)" },
  { code: "pt", label: "Português (PT)" },
  { code: "ru", label: "Русский (RU)" },
  { code: "ko", label: "Korean" },
  { code: "zh", label: "Chinese (Simplified)" },
] as const;

export type LanguageCode = (typeof LANGUAGES)[number]["code"];

const SITE_KEY = "readhentai-site-language";
const COMICS_KEY = "readhentai-comics-language";
const LINK_KEY = "readhentai-languages-linked";
const SITE_EVENT = "site-language-change";
const COMICS_EVENT = "comics-language-change";
const LINK_EVENT = "languages-linked-change";
const DEFAULT: LanguageCode = "en";

export function getSiteLanguage(): LanguageCode {
  if (typeof window === "undefined") return DEFAULT;
  return (localStorage.getItem(SITE_KEY) as LanguageCode) || DEFAULT;
}

export function getComicsLanguage(): LanguageCode {
  if (typeof window === "undefined") return DEFAULT;
  return (localStorage.getItem(COMICS_KEY) as LanguageCode) || DEFAULT;
}

export function getLanguagesLinked(): boolean {
  if (typeof window === "undefined") return true;
  const v = localStorage.getItem(LINK_KEY);
  return v === null ? true : v === "1";
}

export function setSiteLanguage(code: LanguageCode): void {
  localStorage.setItem(SITE_KEY, code);
  window.dispatchEvent(new CustomEvent(SITE_EVENT));
  if (getLanguagesLinked()) {
    localStorage.setItem(COMICS_KEY, code);
    window.dispatchEvent(new CustomEvent(COMICS_EVENT));
  }
}

export function setComicsLanguage(code: LanguageCode): void {
  localStorage.setItem(COMICS_KEY, code);
  window.dispatchEvent(new CustomEvent(COMICS_EVENT));
  if (getLanguagesLinked()) {
    localStorage.setItem(SITE_KEY, code);
    window.dispatchEvent(new CustomEvent(SITE_EVENT));
  }
}

export function setLanguagesLinked(linked: boolean): void {
  localStorage.setItem(LINK_KEY, linked ? "1" : "0");
  window.dispatchEvent(new CustomEvent(LINK_EVENT));
  if (linked) {
    // sync comics to site
    const site = getSiteLanguage();
    localStorage.setItem(COMICS_KEY, site);
    window.dispatchEvent(new CustomEvent(COMICS_EVENT));
  }
}

export function useSiteLanguage(): LanguageCode {
  const [value, setValue] = useState<LanguageCode>(DEFAULT);
  useEffect(() => {
    setValue(getSiteLanguage());
    const sync = () => setValue(getSiteLanguage());
    window.addEventListener(SITE_EVENT, sync);
    return () => window.removeEventListener(SITE_EVENT, sync);
  }, []);
  return value;
}

export function useComicsLanguage(): LanguageCode {
  const [value, setValue] = useState<LanguageCode>(DEFAULT);
  useEffect(() => {
    setValue(getComicsLanguage());
    const sync = () => setValue(getComicsLanguage());
    window.addEventListener(COMICS_EVENT, sync);
    return () => window.removeEventListener(COMICS_EVENT, sync);
  }, []);
  return value;
}

export function useLanguagesLinked(): boolean {
  const [value, setValue] = useState<boolean>(true);
  useEffect(() => {
    setValue(getLanguagesLinked());
    const sync = () => setValue(getLanguagesLinked());
    window.addEventListener(LINK_EVENT, sync);
    return () => window.removeEventListener(LINK_EVENT, sync);
  }, []);
  return value;
}
