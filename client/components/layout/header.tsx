"use client";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import {
  Command,
  Search,
  Bell,
  MessageSquare,
  ChevronDown,
} from "lucide-react";
import { getGreeting, getInitials } from "@/lib/utils";

/**
 * Header - Top header bar for Faiston One
 *
 * Features:
 * - Search trigger (opens Command Palette)
 * - Notifications
 * - User profile
 */

// Mock user data - will come from auth context later
const mockUser = {
  name: "Fábio Santos",
  email: "fabio@faiston.com",
  avatar: null,
  role: "Desenvolvedor",
};

interface HeaderProps {
  onOpenCommandPalette?: () => void;
}

export function Header({ onOpenCommandPalette }: HeaderProps) {
  const greeting = getGreeting();
  const initials = getInitials(mockUser.name);

  return (
    <header
      className={cn(
        "sticky top-0 z-30",
        "h-16 px-6",
        "flex items-center justify-between gap-4",
        "bg-faiston-bg/80 backdrop-blur-md",
        "border-b border-border"
      )}
    >
      {/* Left section - Greeting & Search */}
      <div className="flex items-center gap-6">
        {/* Greeting */}
        <div className="hidden md:block">
          <p className="text-sm text-text-secondary">
            {greeting},{" "}
            <span className="text-text-primary font-medium">
              {mockUser.name.split(" ")[0]}
            </span>
          </p>
        </div>

        {/* Search Trigger */}
        <Button
          variant="outline"
          onClick={onOpenCommandPalette}
          className={cn(
            "w-64 justify-start gap-2",
            "bg-white/5 border-border hover:bg-white/10",
            "text-text-muted hover:text-text-secondary",
            "transition-all duration-150"
          )}
        >
          <Search className="w-4 h-4" />
          <span className="flex-1 text-left text-sm">Buscar...</span>
          <kbd className="hidden sm:inline-flex items-center gap-1 px-2 py-0.5 text-xs font-mono bg-white/10 rounded">
            <Command className="w-3 h-3" />K
          </kbd>
        </Button>
      </div>

      {/* Right section - Actions & Profile */}
      <div className="flex items-center gap-2">
        {/* Notifications */}
        <Button
          variant="ghost"
          size="icon"
          className="relative text-text-secondary hover:text-text-primary hover:bg-white/5"
        >
          <Bell className="w-5 h-5" />
          <Badge
            className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center bg-accent-warning text-white text-xs"
          >
            3
          </Badge>
        </Button>

        {/* Messages */}
        <Button
          variant="ghost"
          size="icon"
          className="relative text-text-secondary hover:text-text-primary hover:bg-white/5"
        >
          <MessageSquare className="w-5 h-5" />
          <Badge
            className="absolute -top-1 -right-1 h-5 w-5 p-0 flex items-center justify-center bg-accent-primary text-white text-xs"
          >
            5
          </Badge>
        </Button>

        {/* Divider */}
        <div className="w-px h-8 bg-border mx-2" />

        {/* User Profile */}
        <Button
          variant="ghost"
          className="flex items-center gap-3 px-2 hover:bg-white/5"
        >
          <Avatar className="h-8 w-8">
            <AvatarImage src={mockUser.avatar || undefined} alt={mockUser.name} />
            <AvatarFallback className="bg-gradient-to-br from-blue-mid to-magenta-mid text-white text-sm">
              {initials}
            </AvatarFallback>
          </Avatar>
          <div className="hidden lg:block text-left">
            <p className="text-sm font-medium text-text-primary">{mockUser.name}</p>
            <p className="text-xs text-text-muted">{mockUser.role}</p>
          </div>
          <ChevronDown className="w-4 h-4 text-text-muted hidden lg:block" />
        </Button>
      </div>
    </header>
  );
}

export default Header;
