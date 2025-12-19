"use client";

import { cn } from "@/lib/utils";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { useState } from "react";
import dynamic from "next/dynamic";

/**
 * AppShell - Main layout wrapper for Faiston One
 *
 * Combines Sidebar, Header, and main content area.
 * Handles the Command Palette state.
 */

// Lazy load Command Palette for better initial load
const CommandPalette = dynamic(
  () => import("@/components/command-palette/command-palette"),
  { ssr: false }
);

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState(false);

  return (
    <div className="min-h-screen bg-faiston-bg">
      {/* Sidebar */}
      <Sidebar />

      {/* Main Content Area */}
      <div className="pl-[72px] lg:pl-[240px] transition-all duration-200">
        {/* Header */}
        <Header onOpenCommandPalette={() => setIsCommandPaletteOpen(true)} />

        {/* Page Content */}
        <main className={cn("min-h-[calc(100vh-4rem)]", "p-6")}>
          {children}
        </main>
      </div>

      {/* Command Palette */}
      <CommandPalette
        open={isCommandPaletteOpen}
        onOpenChange={setIsCommandPaletteOpen}
      />
    </div>
  );
}

export default AppShell;
