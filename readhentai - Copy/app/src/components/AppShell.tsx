"use client";

import { useEffect, useState } from "react";
import { Header } from "./Header";
import { ScrollToTop } from "./ScrollToTop";
import { Sidebar } from "./Sidebar";
import { useSiteLanguage } from "@/lib/language";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const siteLanguage = useSiteLanguage();

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = siteLanguage;
    }
  }, [siteLanguage]);

  return (
    <div className="min-h-dvh">
      <Header onMenu={() => setMenuOpen(true)} />
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
      <main>{children}</main>
      <ScrollToTop />
    </div>
  );
}
