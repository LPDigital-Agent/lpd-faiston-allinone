'use client';

/**
 * XRayEventCard Component
 *
 * Individual event card for X-Ray panel.
 * Shows event details with expandable JSON payload.
 */

import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import {
  ChevronDown,
  ChevronUp,
  Clock,
  ArrowRight,
  Bot,
  AlertTriangle,
  AlertCircle,
  Activity,
  Send,
  Play,
  CheckCircle2,
} from 'lucide-react';
import type { XRayEvent, XRayEventType, XRayEventAction } from '@/lib/ativos/agentRoomTypes';
import { XRayHILCard } from './XRayHILCard';

// =============================================================================
// Types
// =============================================================================

interface XRayEventCardProps {
  event: XRayEvent;
  isExpanded: boolean;
  onToggle: () => void;
  index?: number;
  compact?: boolean;
}

// =============================================================================
// Constants
// =============================================================================

const EVENT_TYPE_CONFIG: Record<
  XRayEventType,
  { icon: typeof Bot; color: string; bgColor: string; label: string }
> = {
  agent_activity: {
    icon: Activity,
    color: 'text-cyan-400',
    bgColor: 'bg-cyan-500/20',
    label: 'Atividade',
  },
  hil_decision: {
    icon: AlertTriangle,
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/20',
    label: 'Decisão HIL',
  },
  a2a_delegation: {
    icon: Send,
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/20',
    label: 'Delegação',
  },
  error: {
    icon: AlertCircle,
    color: 'text-red-400',
    bgColor: 'bg-red-500/20',
    label: 'Erro',
  },
  session_start: {
    icon: Play,
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    label: 'Início',
  },
  session_end: {
    icon: CheckCircle2,
    color: 'text-green-400',
    bgColor: 'bg-green-500/20',
    label: 'Fim',
  },
};

const ACTION_LABELS: Record<XRayEventAction, string> = {
  trabalhando: 'Trabalhando',
  delegando: 'Delegando',
  concluido: 'Concluído',
  erro: 'Erro',
  esperando: 'Aguardando',
  hil_pending: 'Aguardando decisão',
  hil_approved: 'Aprovado',
  hil_rejected: 'Rejeitado',
};

// =============================================================================
// Helper Functions
// =============================================================================

function formatDuration(ms?: number): string {
  if (ms === undefined || ms === null) return '';
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.floor(ms / 60000)}min ${Math.floor((ms % 60000) / 1000)}s`;
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

interface JSONViewerProps {
  data: Record<string, unknown>;
}

function JSONViewer({ data }: JSONViewerProps) {
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      className="overflow-hidden"
    >
      <pre className="mt-2 p-3 rounded-md bg-black/30 text-xs text-text-muted overflow-x-auto font-mono">
        {JSON.stringify(data, null, 2)}
      </pre>
    </motion.div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function XRayEventCard({
  event,
  isExpanded,
  onToggle,
  index = 0,
  compact = false,
}: XRayEventCardProps) {
  const typeConfig = EVENT_TYPE_CONFIG[event.type];
  const TypeIcon = typeConfig.icon;

  // Special handling for HIL events
  if (event.type === 'hil_decision') {
    return (
      <XRayHILCard
        event={event}
        isExpanded={isExpanded}
        onToggle={onToggle}
        compact={compact}
      />
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.03 }}
      className={`rounded-lg transition-all ${
        compact
          ? 'bg-white/3 hover:bg-white/5'
          : 'bg-white/5 border border-white/10 hover:border-white/20'
      }`}
    >
      {/* Event Header */}
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2 p-2 text-left"
      >
        {/* Type Icon */}
        <div
          className={`shrink-0 w-6 h-6 rounded-full ${typeConfig.bgColor} flex items-center justify-center`}
        >
          <TypeIcon className={`w-3.5 h-3.5 ${typeConfig.color}`} />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {/* Agent name */}
            <span className="text-sm font-medium text-text-primary truncate">
              {event.agentName}
            </span>

            {/* A2A Delegation Arrow */}
            {event.targetAgentName && (
              <>
                <ArrowRight className="w-3 h-3 text-purple-400 shrink-0" />
                <span className="text-sm text-purple-400 truncate">
                  {event.targetAgentName}
                </span>
              </>
            )}
          </div>

          {/* Message */}
          <p className="text-xs text-text-muted truncate mt-0.5">
            {event.message || ACTION_LABELS[event.action] || event.action}
          </p>
        </div>

        {/* Meta info */}
        <div className="flex items-center gap-2 shrink-0">
          {/* Duration */}
          {event.duration !== undefined && event.duration > 0 && (
            <div className="flex items-center gap-1 px-1.5 py-0.5 rounded-full bg-white/5">
              <Clock className="w-3 h-3 text-text-muted" />
              <span className="text-[10px] text-text-muted">
                {formatDuration(event.duration)}
              </span>
            </div>
          )}

          {/* Time */}
          {!compact && (
            <span className="text-[10px] text-text-muted">
              {formatTime(event.timestamp)}
            </span>
          )}

          {/* Expand indicator */}
          {event.details && Object.keys(event.details).length > 0 && (
            <div className="text-text-muted">
              {isExpanded ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </div>
          )}
        </div>
      </button>

      {/* Expanded Details */}
      <AnimatePresence>
        {isExpanded && event.details && Object.keys(event.details).length > 0 && (
          <div className="px-2 pb-2">
            <JSONViewer data={event.details} />
          </div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
