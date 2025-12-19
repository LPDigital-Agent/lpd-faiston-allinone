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
 */

interface AssetManagementLayoutProps {
  children: React.ReactNode;
}

export default function AssetManagementLayout({
  children,
}: AssetManagementLayoutProps) {
  return (
    <div className="flex flex-col h-full">
      {/* Module Header */}
      <div className="border-b border-border bg-faiston-bg/50 backdrop-blur-sm sticky top-16 z-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
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
        className="flex-1 overflow-auto"
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
          {children}
        </div>
      </motion.main>
    </div>
  );
}
