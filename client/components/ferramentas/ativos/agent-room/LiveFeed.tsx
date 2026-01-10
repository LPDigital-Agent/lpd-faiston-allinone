'use client';

/**
 * LiveFeed Panel
 *
 * Real-time stream of agent activities in humanized language.
 * Shows what agents are doing in first-person Portuguese.
 */

import { useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  GlassCard,
  GlassCardHeader,
  GlassCardTitle,
  GlassCardContent,
} from '@/components/shared/glass-card';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Radio,
  Pause,
  Play,
  Info,
  CheckCircle,
  AlertTriangle,
  Hand,
  RefreshCw,
} from 'lucide-react';
import { useLiveFeed } from '@/hooks/ativos';
import { MESSAGE_TYPE_COLORS } from '@/lib/ativos/agentRoomConstants';
import type { LiveMessage, LiveMessageType } from '@/lib/ativos/agentRoomTypes';

// =============================================================================
// Constants
// =============================================================================

const MESSAGE_ICONS: Record<LiveMessageType, React.ElementType> = {
  info: Info,
  success: CheckCircle,
  warning: AlertTriangle,
  action_needed: Hand,
};

const MESSAGE_ICON_COLORS: Record<LiveMessageType, string> = {
  info: 'text-blue-400',
  success: 'text-green-400',
  warning: 'text-yellow-400',
  action_needed: 'text-magenta-mid',
};

// =============================================================================
// Helper Functions
// =============================================================================

function formatTimeAgo(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);

  if (diffSec < 10) return 'agora';
  if (diffSec < 60) return `${diffSec}s`;
  if (diffMin < 60) return `${diffMin}m`;
  return `${diffHour}h`;
}

// =============================================================================
// Sub-Components
// =============================================================================

interface LiveMessageItemProps {
  message: LiveMessage;
}

function LiveMessageItem({ message }: LiveMessageItemProps) {
  const Icon = MESSAGE_ICONS[message.type];
  const iconColor = MESSAGE_ICON_COLORS[message.type];
  const bgColor = MESSAGE_TYPE_COLORS[message.type];
  const timeAgo = formatTimeAgo(new Date(message.timestamp));

  return (
    <motion.div
      initial={{ opacity: 0, x: -20 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: 20 }}
      className={`flex gap-3 p-3 rounded-lg border-l-2 ${bgColor}`}
    >
      <div className="shrink-0 mt-0.5">
        <Icon className={`w-4 h-4 ${iconColor}`} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-xs font-medium text-text-primary">
            {message.agentName}
          </span>
          <span className="text-xs text-text-muted">{timeAgo}</span>
        </div>
        <p className="text-sm text-text-secondary">{message.message}</p>
        {message.relatedEntity && (
          <span className="inline-block mt-1 text-xs text-magenta-mid hover:underline cursor-pointer">
            Ver {message.relatedEntity.label}
          </span>
        )}
      </div>
    </motion.div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function LiveFeed() {
  const { messages, isConnected, error, isPaused, setPaused, clearMessages } = useLiveFeed();
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to top when new messages arrive
  useEffect(() => {
    if (!isPaused && scrollRef.current) {
      scrollRef.current.scrollTop = 0;
    }
  }, [messages, isPaused]);

  return (
    <GlassCard className="relative">
      <GlassCardHeader>
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2">
            {isConnected ? (
              <Radio className="w-4 h-4 text-green-400 animate-pulse" />
            ) : (
              <RefreshCw className="w-4 h-4 text-yellow-400 animate-spin" />
            )}
            <GlassCardTitle>Ao Vivo</GlassCardTitle>
            <span className="text-xs text-text-muted">
              {messages.length} mensagens
            </span>
            {error && (
              <span className="text-xs text-yellow-400">{error}</span>
            )}
          </div>
          <div className="flex items-center gap-2">
            {messages.length > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearMessages}
                className="text-xs"
              >
                Limpar
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setPaused(!isPaused)}
              className="gap-1"
            >
              {isPaused ? (
                <>
                  <Play className="w-3 h-3" />
                  <span className="text-xs">Retomar</span>
                </>
              ) : (
                <>
                  <Pause className="w-3 h-3" />
                  <span className="text-xs">Pausar</span>
                </>
              )}
            </Button>
          </div>
        </div>
      </GlassCardHeader>

      <GlassCardContent>
        <ScrollArea className="h-[200px]" ref={scrollRef}>
          <div className="space-y-2 pr-4">
            {messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-8 text-center">
                <Radio className="w-8 h-8 text-text-muted mb-2" />
                <p className="text-sm text-text-muted">
                  Aguardando atividades...
                </p>
                <p className="text-xs text-text-muted mt-1">
                  As mensagens aparecerão aqui quando os agentes começarem a trabalhar
                </p>
              </div>
            ) : (
              <AnimatePresence mode="popLayout">
                {messages.map((message) => (
                  <LiveMessageItem key={message.id} message={message} />
                ))}
              </AnimatePresence>
            )}
          </div>
        </ScrollArea>

        {/* Paused Overlay */}
        {isPaused && messages.length > 0 && (
          <div className="absolute inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center rounded-lg">
            <div className="text-center">
              <Pause className="w-8 h-8 text-text-muted mx-auto mb-2" />
              <p className="text-sm text-text-muted">Feed pausado</p>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setPaused(false)}
                className="mt-2"
              >
                Retomar
              </Button>
            </div>
          </div>
        )}
      </GlassCardContent>
    </GlassCard>
  );
}
