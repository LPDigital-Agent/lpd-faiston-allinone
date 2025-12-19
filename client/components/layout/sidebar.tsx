"use client";

import { cn } from "@/lib/utils";
import { FaistonLogo } from "@/components/shared/faiston-logo";
import {
  LayoutDashboard,
  Newspaper,
  Calendar,
  MessageSquare,
  Settings,
  HelpCircle,
  ChevronLeft,
  ChevronRight,
  Package,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";

/**
 * Sidebar - Main navigation sidebar for Faiston One
 *
 * Features:
 * - Collapsible sidebar with smooth animations
 * - Active state highlighting
 * - Tooltips when collapsed
 * - Faiston brand integration
 */

interface NavItem {
  label: string;
  icon: React.ElementType;
  href: string;
  badge?: number;
}

const mainNavItems: NavItem[] = [
  { label: "Dashboard", icon: LayoutDashboard, href: "/" },
  { label: "Notícias", icon: Newspaper, href: "/noticias" },
  { label: "Calendário", icon: Calendar, href: "/calendario" },
  { label: "Teams", icon: MessageSquare, href: "/teams", badge: 5 },
];

const toolsNavItems: NavItem[] = [
  { label: "Gestão de Ativos", icon: Package, href: "/ferramentas/ativos/dashboard" },
];

const secondaryNavItems: NavItem[] = [
  { label: "Configurações", icon: Settings, href: "/configuracoes" },
  { label: "Ajuda", icon: HelpCircle, href: "/ajuda" },
];

export function Sidebar() {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const pathname = usePathname();

  return (
    <TooltipProvider delayDuration={0}>
      <motion.aside
        initial={false}
        animate={{ width: isCollapsed ? 72 : 240 }}
        transition={{ duration: 0.2, ease: "easeOut" }}
        className={cn(
          "fixed left-0 top-0 z-40 h-screen",
          "flex flex-col",
          "bg-faiston-bg border-r border-border",
          "transition-all duration-200"
        )}
      >
        {/* Logo */}
        <div className="flex items-center justify-between p-4 h-16 border-b border-border">
          <AnimatePresence mode="wait">
            {!isCollapsed ? (
              <motion.div
                key="full-logo"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
              >
                <FaistonLogo variant="color" size="md" />
              </motion.div>
            ) : (
              <motion.div
                key="icon-logo"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="w-10 h-10 rounded-lg gradient-nexo flex items-center justify-center"
              >
                <span className="text-white font-bold text-lg">F</span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Main Navigation */}
        <nav className="flex-1 overflow-y-auto py-4 px-2">
          <div className="space-y-1">
            {mainNavItems.map((item) => (
              <NavLink
                key={item.href}
                item={item}
                isActive={pathname === item.href}
                isCollapsed={isCollapsed}
              />
            ))}
          </div>

          {/* Tools Section */}
          <div className="mt-6 pt-4 border-t border-border">
            <AnimatePresence mode="wait">
              {!isCollapsed && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  className="px-3 text-xs font-semibold text-text-muted uppercase tracking-wider"
                >
                  Ferramentas
                </motion.span>
              )}
            </AnimatePresence>
            <div className="mt-2 space-y-1">
              {toolsNavItems.map((item) => {
                // For tools, check if pathname is within the module base path
                // e.g., /ferramentas/ativos/* should highlight "Gestão de Ativos"
                const basePath = item.href.replace(/\/dashboard$/, "");
                const isActive = pathname === item.href || pathname.startsWith(basePath + "/");
                return (
                  <NavLink
                    key={item.href}
                    item={item}
                    isActive={isActive}
                    isCollapsed={isCollapsed}
                  />
                );
              })}
            </div>
          </div>
        </nav>

        {/* Secondary Navigation */}
        <div className="border-t border-border py-4 px-2">
          <div className="space-y-1">
            {secondaryNavItems.map((item) => (
              <NavLink
                key={item.href}
                item={item}
                isActive={pathname === item.href}
                isCollapsed={isCollapsed}
              />
            ))}
          </div>
        </div>

        {/* Collapse Toggle */}
        <div className="border-t border-border p-2">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className={cn(
              "w-full flex items-center justify-center gap-2",
              "text-text-muted hover:text-text-primary",
              "hover:bg-white/5"
            )}
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <>
                <ChevronLeft className="w-4 h-4" />
                <span className="text-sm">Recolher</span>
              </>
            )}
          </Button>
        </div>
      </motion.aside>
    </TooltipProvider>
  );
}

interface NavLinkProps {
  item: NavItem;
  isActive: boolean;
  isCollapsed: boolean;
}

function NavLink({ item, isActive, isCollapsed }: NavLinkProps) {
  const Icon = item.icon;

  const content = (
    <Link
      href={item.href}
      className={cn(
        "flex items-center gap-3 px-3 py-2.5 rounded-lg",
        "transition-all duration-150",
        "group relative",
        isActive
          ? "bg-white/10 text-text-primary"
          : "text-text-secondary hover:text-text-primary hover:bg-white/5"
      )}
    >
      {/* Active indicator */}
      {isActive && (
        <motion.div
          layoutId="activeNav"
          className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-6 rounded-r-full gradient-action"
          transition={{ type: "spring", stiffness: 500, damping: 30 }}
        />
      )}

      <Icon className={cn("w-5 h-5 shrink-0", isActive && "text-accent-primary")} />

      <AnimatePresence mode="wait">
        {!isCollapsed && (
          <motion.span
            initial={{ opacity: 0, width: 0 }}
            animate={{ opacity: 1, width: "auto" }}
            exit={{ opacity: 0, width: 0 }}
            transition={{ duration: 0.15 }}
            className="text-sm font-medium whitespace-nowrap overflow-hidden"
          >
            {item.label}
          </motion.span>
        )}
      </AnimatePresence>

      {/* Badge */}
      {item.badge && !isCollapsed && (
        <span className="ml-auto px-2 py-0.5 text-xs font-medium rounded-full bg-accent-primary text-white">
          {item.badge}
        </span>
      )}

      {/* Badge dot when collapsed */}
      {item.badge && isCollapsed && (
        <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-accent-primary" />
      )}
    </Link>
  );

  if (isCollapsed) {
    return (
      <Tooltip>
        <TooltipTrigger asChild>{content}</TooltipTrigger>
        <TooltipContent side="right" className="flex items-center gap-2">
          {item.label}
          {item.badge && (
            <span className="px-1.5 py-0.5 text-xs font-medium rounded-full bg-accent-primary text-white">
              {item.badge}
            </span>
          )}
        </TooltipContent>
      </Tooltip>
    );
  }

  return content;
}

export default Sidebar;
