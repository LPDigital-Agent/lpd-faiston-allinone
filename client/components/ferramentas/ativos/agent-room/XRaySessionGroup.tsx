'use client';

/**
 * XRaySessionGroup Component
 *
 * Collapsible session accordion for X-Ray panel.
 * Groups related events by session_id.
 */

import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import {
  ChevronDown,
  ChevronRight,
  Clock,
  CheckCircle2,
  XCircle,
  Activity,
} from 'lucide-react';
import type { XRaySession } from '@/lib/ativos/agentRoomTypes';
import { XRayEventCard } from './XRayEventCard';

// =============================================================================
// Types
// =============================================================================

interface XRaySessionGroupProps {
  session: XRaySession;
  isExpanded: boolean;
  onToggle: () => void;
  expandedEvents: Set<string>;
  onToggleEvent: (eventId: string) => void;
}

// =============================================================================
// Helper Functions
// =============================================================================

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  if (ms < 3600000) return `${Math.floor(ms / 60000)}min ${Math.floor((ms % 60000) / 1000)}s`;
  return `${Math.floor(ms / 3600000)}h ${Math.floor((ms % 3600000) / 60000)}min`;
}

function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('pt-BR', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return '--:--:--';
  }
}

// =============================================================================
// Sub-Components
// =============================================================================

interface SessionStatusBadgeProps {
  status: XRaySession['status'];
}

function SessionStatusBadge({ status }: SessionStatusBadgeProps) {
  const config = {
    active: {
      icon: Activity,
      color: 'text-cyan-400',
      bgColor: 'bg-cyan-500/20',
      borderColor: 'border-cyan-500/30',
      label: 'Ativo',
    },
    completed: {
      icon: CheckCircle2,
      color: 'text-green-400',
      bgColor: 'bg-green-500/20',
      borderColor: 'border-green-500/30',
      label: 'Concluído',
    },
    error: {
      icon: XCircle,
      color: 'text-red-400',
      bgColor: 'bg-red-500/20',
      borderColor: 'border-red-500/30',
      label: 'Erro',
    },
  };

  const { icon: Icon, color, bgColor, borderColor, label } = config[status];

  return (
    <div
      className={`flex items-center gap-1 px-1.5 py-0.5 rounded-full ${bgColor} border ${borderColor}`}
    >
      <Icon className={`w-3 h-3 ${color}`} />
      <span className={`text-[10px] ${color}`}>{label}</span>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function XRaySessionGroup({
  session,
  isExpanded,
  onToggle,
  expandedEvents,
  onToggleEvent,
}: XRaySessionGroupProps) {
  // Sort events chronologically (oldest first for timeline)
  const sortedEvents = [...session.events].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );

  return (
    <div className="rounded-lg bg-white/5 border border-white/10 overflow-hidden">
      {/* Session Header */}
      <Button
        variant="ghost"
        onClick={onToggle}
        className="w-full flex items-center justify-between p-3 h-auto hover:bg-white/5"
      >
        <div className="flex items-center gap-2 min-w-0">
          {isExpanded ? (
            <ChevronDown className="w-4 h-4 text-text-muted shrink-0" />
          ) : (
            <ChevronRight className="w-4 h-4 text-text-muted shrink-0" />
          )}

          <div className="flex flex-col items-start min-w-0">
            <span className="text-sm font-medium text-text-primary truncate">
              {session.sessionName}
            </span>
            <span className="text-[10px] text-text-muted">
              {formatTime(session.startTime)} - {session.eventCount} eventos
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {/* Duration */}
          {session.totalDuration !== undefined && session.totalDuration > 0 && (
            <div className="flex items-center gap-1 text-xs text-text-muted">
              <Clock className="w-3 h-3" />
              <span>{formatDuration(session.totalDuration)}</span>
            </div>
          )}

          {/* Status Badge */}
          <SessionStatusBadge status={session.status} />
        </div>
      </Button>

      {/* Events Timeline */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="border-t border-white/10 p-3 space-y-2">
              {/* Timeline line */}
              <div className="relative">
                {/* Vertical timeline line */}
                <div className="absolute left-3 top-0 bottom-0 w-px bg-white/10" />

                {/* Events */}
                <div className="space-y-2 pl-8">
                  {sortedEvents.map((event, index) => (
                    <motion.div
                      key={event.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="relative"
                    >
                      {/* Timeline dot */}
                      <div
                        className={`absolute -left-8 top-3 w-2 h-2 rounded-full ${
                          event.type === 'error'
                            ? 'bg-red-400'
                            : event.type === 'hil_decision'
                            ? 'bg-yellow-400'
                            : event.type === 'a2a_delegation'
                            ? 'bg-purple-400'
                            : 'bg-cyan-400'
                        }`}
                      />

                      <XRayEventCard
                        event={event}
                        isExpanded={expandedEvents.has(event.id)}
                        onToggle={() => onToggleEvent(event.id)}
                        index={index}
                        compact
                      />
                    </motion.div>
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
