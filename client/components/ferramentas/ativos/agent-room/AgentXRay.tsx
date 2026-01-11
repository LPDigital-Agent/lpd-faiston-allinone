'use client';

/**
 * AgentXRay Panel
 *
 * Real-time agent activity traces panel for Agent Room.
 * Shows agent events grouped by session with expandable details.
 *
 * Features:
 * - Session grouping (collapsible accordions)
 * - Event type indicators (agent_activity, hil_decision, a2a_delegation, error)
 * - Duration badges
 * - Expandable JSON details
 * - HIL inline actions
 * - Real-time updates (1s polling)
 */

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  GlassCard,
  GlassCardHeader,
  GlassCardTitle,
  GlassCardContent,
} from '@/components/shared/glass-card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Search,
  RefreshCw,
  Radio,
  WifiOff,
  Filter,
  AlertCircle,
  ChevronDown,
  AlertTriangle,
  Activity,
  Send,
} from 'lucide-react';
import { useAgentRoomXRay } from '@/hooks/ativos';
import { XRaySessionGroup } from './XRaySessionGroup';
import { XRayEventCard } from './XRayEventCard';
import type { XRayEvent, XRayEventType } from '@/lib/ativos/agentRoomTypes';

// =============================================================================
// Constants
// =============================================================================

const EVENT_TYPE_OPTIONS: { value: XRayEventType | 'all'; label: string }[] = [
  { value: 'all', label: 'Todos os eventos' },
  { value: 'agent_activity', label: 'Atividade' },
  { value: 'hil_decision', label: 'Decisões HIL' },
  { value: 'a2a_delegation', label: 'Delegações' },
  { value: 'error', label: 'Erros' },
];

// =============================================================================
// Sub-Components
// =============================================================================

interface ConnectionBadgeProps {
  status: 'connected' | 'connecting' | 'reconnecting' | 'disconnected' | 'error';
  onReconnect: () => void;
}

function ConnectionBadge({ status, onReconnect }: ConnectionBadgeProps) {
  if (status === 'connecting') {
    return (
      <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-yellow-500/20 border border-yellow-500/30">
        <RefreshCw className="w-3 h-3 text-yellow-400 animate-spin" />
        <span className="text-xs text-yellow-400">Conectando</span>
      </div>
    );
  }

  if (status === 'reconnecting') {
    return (
      <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-orange-500/20 border border-orange-500/30">
        <RefreshCw className="w-3 h-3 text-orange-400 animate-spin" />
        <span className="text-xs text-orange-400">Reconectando</span>
      </div>
    );
  }

  if (status === 'error' || status === 'disconnected') {
    return (
      <Button
        variant="ghost"
        size="sm"
        onClick={onReconnect}
        className="flex items-center gap-1.5 px-2 py-0.5 h-auto rounded-full bg-red-500/20 border border-red-500/30 hover:bg-red-500/30"
      >
        <WifiOff className="w-3 h-3 text-red-400" />
        <span className="text-xs text-red-400">Reconectar</span>
      </Button>
    );
  }

  return (
    <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-green-500/20 border border-green-500/30">
      <Radio className="w-3 h-3 text-green-400 animate-pulse" />
      <span className="text-xs text-green-400">Ao Vivo</span>
    </div>
  );
}

interface EmptyStateProps {
  isFiltered: boolean;
}

function EmptyState({ isFiltered }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-8 text-center">
      <motion.div
        animate={{
          scale: [1, 1.05, 1],
          opacity: [0.5, 0.8, 0.5],
        }}
        transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
        className="relative mb-4"
      >
        <Search className="w-14 h-14 text-cyan-400" />
        <motion.div
          animate={{ scale: [1, 1.8], opacity: [0.6, 0] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }}
          className="absolute inset-0 rounded-full border-2 border-cyan-400/50"
        />
      </motion.div>
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="text-sm text-text-muted"
      >
        {isFiltered
          ? 'Nenhum evento encontrado com os filtros atuais'
          : 'Aguardando atividade dos agentes...'}
      </motion.p>
      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 0.2 }}
        className="text-xs text-text-muted/60 mt-1"
      >
        {isFiltered
          ? 'Tente ajustar os filtros'
          : 'Os eventos aparecerão aqui em tempo real'}
      </motion.p>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function AgentXRay() {
  const {
    events,
    sessions,
    noSessionEvents,
    filteredEvents,
    connectionStatus,
    isLoading,
    error,
    filter,
    setFilter,
    hilPendingCount,
    totalEvents,
    refetch,
    isPaused,
    setPaused,
    expandedSessions,
    toggleSessionExpanded,
    expandedEvents,
    toggleEventExpanded,
  } = useAgentRoomXRay();

  const [showFilters, setShowFilters] = useState(false);

  // Determine if filters are active
  const isFiltered = useMemo(() => {
    return !!(filter.agentId || filter.sessionId || filter.type || filter.showHILOnly);
  }, [filter]);

  // Handle type filter change
  const handleTypeChange = (value: string) => {
    if (value === 'all') {
      setFilter((prev) => ({ ...prev, type: undefined }));
    } else {
      setFilter((prev) => ({ ...prev, type: value as XRayEventType }));
    }
  };

  // Handle HIL only toggle
  const handleHILOnlyToggle = () => {
    setFilter((prev) => ({ ...prev, showHILOnly: !prev.showHILOnly }));
  };

  return (
    <GlassCard className="h-full">
      <GlassCardHeader>
        <div className="flex items-center justify-between w-full gap-2">
          <div className="flex items-center gap-2">
            <Search className="w-4 h-4 text-cyan-400" />
            <GlassCardTitle>X-Ray</GlassCardTitle>
          </div>

          <div className="flex items-center gap-2">
            {/* HIL Pending Badge */}
            {hilPendingCount > 0 && (
              <motion.div
                initial={{ scale: 0.8, opacity: 0 }}
                animate={{ scale: 1, opacity: 1 }}
                className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-yellow-500/20 border border-yellow-500/30"
              >
                <AlertTriangle className="w-3 h-3 text-yellow-400" />
                <span className="text-xs text-yellow-400 font-medium">
                  {hilPendingCount} HIL
                </span>
              </motion.div>
            )}

            {/* Filter Button */}
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setShowFilters(!showFilters)}
              className={`h-7 px-2 ${showFilters ? 'bg-white/10' : ''}`}
            >
              <Filter className="w-3.5 h-3.5" />
            </Button>

            {/* Connection Status */}
            <ConnectionBadge status={connectionStatus} onReconnect={refetch} />
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="flex items-center gap-2 mt-2 text-xs text-red-400">
            <AlertCircle className="w-3.5 h-3.5" />
            <span>{error}</span>
          </div>
        )}

        {/* Filters */}
        <AnimatePresence>
          {showFilters && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-white/10">
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button
                      variant="outline"
                      size="sm"
                      className="h-8 text-xs bg-white/5 border-white/10"
                    >
                      {EVENT_TYPE_OPTIONS.find((opt) => opt.value === (filter.type || 'all'))?.label || 'Tipo'}
                      <ChevronDown className="w-3.5 h-3.5 ml-1" />
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start">
                    {EVENT_TYPE_OPTIONS.map((opt) => (
                      <DropdownMenuItem
                        key={opt.value}
                        onClick={() => handleTypeChange(opt.value)}
                        className={filter.type === opt.value || (!filter.type && opt.value === 'all') ? 'bg-white/10' : ''}
                      >
                        {opt.label}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>

                <Button
                  variant={filter.showHILOnly ? 'default' : 'outline'}
                  size="sm"
                  onClick={handleHILOnlyToggle}
                  className="h-8 text-xs"
                >
                  <AlertTriangle className="w-3.5 h-3.5 mr-1" />
                  Apenas HIL
                </Button>

                {isFiltered && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => setFilter({})}
                    className="h-8 text-xs text-text-muted hover:text-text-primary"
                  >
                    Limpar filtros
                  </Button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </GlassCardHeader>

      <GlassCardContent className="p-0">
        {filteredEvents.length === 0 && !isLoading ? (
          <div className="p-4">
            <EmptyState isFiltered={isFiltered} />
          </div>
        ) : (
          <ScrollArea className="h-[280px]">
            <div className="p-4 space-y-3">
              {/* Sessions */}
              {sessions.map((session) => (
                <XRaySessionGroup
                  key={session.sessionId}
                  session={session}
                  isExpanded={expandedSessions.has(session.sessionId)}
                  onToggle={() => toggleSessionExpanded(session.sessionId)}
                  expandedEvents={expandedEvents}
                  onToggleEvent={toggleEventExpanded}
                />
              ))}

              {/* Events without session */}
              {noSessionEvents.length > 0 && (
                <div className="space-y-2">
                  {sessions.length > 0 && (
                    <div className="flex items-center gap-2 py-2">
                      <div className="h-px flex-1 bg-white/10" />
                      <span className="text-xs text-text-muted">Eventos avulsos</span>
                      <div className="h-px flex-1 bg-white/10" />
                    </div>
                  )}
                  {noSessionEvents.map((event, index) => (
                    <XRayEventCard
                      key={event.id}
                      event={event}
                      isExpanded={expandedEvents.has(event.id)}
                      onToggle={() => toggleEventExpanded(event.id)}
                      index={index}
                    />
                  ))}
                </div>
              )}
            </div>
          </ScrollArea>
        )}
      </GlassCardContent>
    </GlassCard>
  );
}
