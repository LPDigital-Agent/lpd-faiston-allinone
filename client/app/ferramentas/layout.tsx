"use client";

import { AppShell } from "@/components/layout/app-shell";

/**
 * FerramentasLayout - Layout wrapper for all tools/ferramentas pages
 *
 * This layout ensures that all pages under /ferramentas/* are wrapped
 * with the main AppShell, providing:
 * - Sidebar navigation (Faiston One menu)
 * - Header with search, notifications, user profile
 * - Command Palette
 *
 * Each tool (like Gestão de Ativos) can have its own nested layout
 * for module-specific navigation.
 */

interface FerramentasLayoutProps {
  children: React.ReactNode;
}

export default function FerramentasLayout({
  children,
}: FerramentasLayoutProps) {
  return <AppShell>{children}</AppShell>;
}
