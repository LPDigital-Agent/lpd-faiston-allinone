'use client';

/**
 * XRayHILCard Component
 *
 * Special card for HIL (Human-in-the-Loop) decision events in X-Ray panel.
 * Shows pending decisions with approve/reject buttons inline.
 */

import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Button } from '@/components/ui/button';
import {
  ChevronDown,
  ChevronUp,
  AlertTriangle,
  Check,
  X,
  Loader2,
  Clock,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import type { XRayEvent } from '@/lib/ativos/agentRoomTypes';
import { approveTask, rejectTask } from '@/services/sgaAgentcore';

// =============================================================================
// Types
// =============================================================================

interface XRayHILCardProps {
  event: XRayEvent;
  isExpanded: boolean;
  onToggle: () => void;
  compact?: boolean;
}

type HILActionState = 'idle' | 'loading' | 'success' | 'error';

// =============================================================================
// Helper Functions
// =============================================================================

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

function getTimeSince(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);

    if (diffSec < 60) return 'agora';
    if (diffMin < 60) return `${diffMin}min`;
    if (diffHour < 24) return `${diffHour}h`;
    return date.toLocaleDateString('pt-BR', { day: 'numeric', month: 'short' });
  } catch {
    return '';
  }
}

// =============================================================================
// Sub-Components
// =============================================================================

interface HILStatusBadgeProps {
  status: 'pending' | 'approved' | 'rejected';
}

function HILStatusBadge({ status }: HILStatusBadgeProps) {
  const config = {
    pending: {
      icon: AlertTriangle,
      color: 'text-yellow-400',
      bgColor: 'bg-yellow-500/20',
      borderColor: 'border-yellow-500/30',
      label: 'Pendente',
    },
    approved: {
      icon: CheckCircle2,
      color: 'text-green-400',
      bgColor: 'bg-green-500/20',
      borderColor: 'border-green-500/30',
      label: 'Aprovado',
    },
    rejected: {
      icon: XCircle,
      color: 'text-red-400',
      bgColor: 'bg-red-500/20',
      borderColor: 'border-red-500/30',
      label: 'Rejeitado',
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

export function XRayHILCard({
  event,
  isExpanded,
  onToggle,
  compact = false,
}: XRayHILCardProps) {
  const [actionState, setActionState] = useState<HILActionState>('idle');
  const [actionResult, setActionResult] = useState<'approved' | 'rejected' | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const isPending = event.hilStatus === 'pending' && !actionResult;
  const currentStatus = actionResult || event.hilStatus || 'pending';

  // Handle approve action
  const handleApprove = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!event.hilTaskId) return;

    setActionState('loading');
    setErrorMessage(null);

    try {
      const response = await approveTask({ task_id: event.hilTaskId });
      if (response.data?.action_executed || response.data?.task) {
        setActionState('success');
        setActionResult('approved');
      } else {
        throw new Error('Erro ao aprovar');
      }
    } catch (err) {
      setActionState('error');
      setErrorMessage(err instanceof Error ? err.message : 'Erro ao aprovar');
      setTimeout(() => {
        setActionState('idle');
        setErrorMessage(null);
      }, 3000);
    }
  }, [event.hilTaskId]);

  // Handle reject action
  const handleReject = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!event.hilTaskId) return;

    setActionState('loading');
    setErrorMessage(null);

    try {
      const response = await rejectTask({ task_id: event.hilTaskId, reason: 'Rejeitado via X-Ray' });
      if (response.data?.task) {
        setActionState('success');
        setActionResult('rejected');
      } else {
        throw new Error('Erro ao rejeitar');
      }
    } catch (err) {
      setActionState('error');
      setErrorMessage(err instanceof Error ? err.message : 'Erro ao rejeitar');
      setTimeout(() => {
        setActionState('idle');
        setErrorMessage(null);
      }, 3000);
    }
  }, [event.hilTaskId]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      className={`rounded-lg border-2 transition-all ${
        isPending
          ? 'border-yellow-500/40 bg-yellow-500/10'
          : currentStatus === 'approved'
          ? 'border-green-500/30 bg-green-500/5'
          : currentStatus === 'rejected'
          ? 'border-red-500/30 bg-red-500/5'
          : 'border-white/10 bg-white/5'
      }`}
    >
      {/* Card Header */}
      <button
        onClick={onToggle}
        className="w-full flex items-start gap-2 p-3 text-left"
      >
        {/* Warning Icon */}
        <div className="shrink-0 mt-0.5">
          {actionState === 'loading' ? (
            <Loader2 className="w-5 h-5 text-yellow-400 animate-spin" />
          ) : isPending ? (
            <motion.div
              animate={{ scale: [1, 1.1, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              <AlertTriangle className="w-5 h-5 text-yellow-400" />
            </motion.div>
          ) : currentStatus === 'approved' ? (
            <CheckCircle2 className="w-5 h-5 text-green-400" />
          ) : (
            <XCircle className="w-5 h-5 text-red-400" />
          )}
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-text-primary">
              {event.agentName}
            </span>
            <HILStatusBadge status={currentStatus as 'pending' | 'approved' | 'rejected'} />
          </div>

          {/* Question */}
          <p className="text-sm text-text-primary">
            {event.hilQuestion || event.message}
          </p>

          {/* Time */}
          <div className="flex items-center gap-1 mt-1.5 text-[10px] text-text-muted">
            <Clock className="w-3 h-3" />
            <span>{getTimeSince(event.timestamp)}</span>
            {!compact && <span className="ml-1">({formatTime(event.timestamp)})</span>}
          </div>

          {/* Error message */}
          {errorMessage && (
            <p className="text-xs text-red-400 mt-1">{errorMessage}</p>
          )}
        </div>

        {/* Expand indicator */}
        {event.details && Object.keys(event.details).length > 0 && (
          <div className="text-text-muted shrink-0">
            {isExpanded ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </div>
        )}
      </button>

      {/* Action Buttons (only for pending) */}
      {isPending && (
        <div className="flex items-center gap-2 px-3 pb-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleApprove}
            disabled={actionState === 'loading'}
            className="flex-1 h-8 text-xs bg-green-500/10 border-green-500/30 text-green-400 hover:bg-green-500/20 hover:text-green-300"
          >
            {actionState === 'loading' ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <>
                <Check className="w-3.5 h-3.5 mr-1" />
                Aprovar
              </>
            )}
          </Button>

          <Button
            variant="outline"
            size="sm"
            onClick={handleReject}
            disabled={actionState === 'loading'}
            className="flex-1 h-8 text-xs bg-red-500/10 border-red-500/30 text-red-400 hover:bg-red-500/20 hover:text-red-300"
          >
            {actionState === 'loading' ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <>
                <X className="w-3.5 h-3.5 mr-1" />
                Rejeitar
              </>
            )}
          </Button>
        </div>
      )}

      {/* HIL Options (if available) */}
      {isPending && event.hilOptions && event.hilOptions.length > 0 && (
        <div className="px-3 pb-3">
          <p className="text-[10px] text-text-muted mb-2">Opções disponíveis:</p>
          <div className="flex flex-wrap gap-1.5">
            {event.hilOptions.map((option, idx) => (
              <div
                key={idx}
                className="px-2 py-1 rounded-md bg-white/5 text-xs text-text-muted"
              >
                {option.label}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Expanded Details */}
      <AnimatePresence>
        {isExpanded && event.details && Object.keys(event.details).length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 border-t border-white/10 pt-3">
              <pre className="p-3 rounded-md bg-black/30 text-xs text-text-muted overflow-x-auto font-mono">
                {JSON.stringify(event.details, null, 2)}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
