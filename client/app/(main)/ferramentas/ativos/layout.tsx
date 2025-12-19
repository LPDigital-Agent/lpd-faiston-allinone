"use client";

import { AssetManagementNav } from "@/components/ferramentas/ativos/asset-management-nav";
import { Package } from "lucide-react";
import { motion } from "framer-motion";

/**
 * AssetManagementLayout - Layout wrapper for Gestão de Ativos platform
 *
 * This layout provides:
 * - Module title/branding area
 * - Horizontal tab navigation between modules
 * - Consistent padding and spacing
 * - Smooth page transitions
 *
 * The layout wraps all pages under /ferramentas/ativos/* and provides
 * a "sub-platform" experience within Faiston One.
 *
 * Note: This layout runs INSIDE the AppShell (via ferramentas/layout.tsx),
 * so we use negative margins to extend the header edge-to-edge while
 * keeping content properly padded.
 */

interface AssetManagementLayoutProps {
  children: React.ReactNode;
}

export default function AssetManagementLayout({
  children,
}: AssetManagementLayoutProps) {
  return (
    <div className="flex flex-col min-h-[calc(100vh-4rem-3rem)]">
      {/* Module Header - Uses negative margin to extend to edges */}
      <div className="-mx-6 -mt-6 border-b border-border bg-faiston-bg/80 backdrop-blur-sm sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-6">
          {/* Module Title */}
          <div className="flex items-center gap-3 py-4">
            <div className="w-10 h-10 rounded-lg gradient-action flex items-center justify-center">
              <Package className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-text-primary">
                Gestão de Ativos
              </h1>
              <p className="text-xs text-text-muted">
                Controle completo do seu inventário
              </p>
            </div>
          </div>

          {/* Navigation Tabs */}
          <AssetManagementNav />
        </div>
      </div>

      {/* Page Content */}
      <motion.main
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: "easeOut" }}
        className="flex-1 pt-6"
      >
        <div className="max-w-7xl mx-auto">
          {children}
        </div>
      </motion.main>
    </div>
  );
}
