"use client";

import { useState } from "react";
import { Header } from "./Header";
import { ScrollToTop } from "./ScrollToTop";
import { Sidebar } from "./Sidebar";

export function AppShell({ children }: { children: React.ReactNode }) {
  const [menuOpen, setMenuOpen] = useState(false);

  return (
    <div className="min-h-dvh">
      <Header onMenu={() => setMenuOpen(true)} />
      <Sidebar open={menuOpen} onClose={() => setMenuOpen(false)} />
      <main>{children}</main>
      <ScrollToTop />
    </div>
  );
}
