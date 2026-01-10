'use client';

/**
 * PendingDecisions Panel
 *
 * Shows decisions that need human input (HIL tasks).
 * "Precisa de Você" - humanized decision requests.
 */

import { useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  GlassCard,
  GlassCardHeader,
  GlassCardTitle,
  GlassCardContent,
} from '@/components/shared/glass-card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Hand, CheckCircle, Zap, RefreshCw } from 'lucide-react';
import { usePendingDecisions } from '@/hooks/ativos';
import { approveTask, rejectTask } from '@/services/sgaAgentcore';
import type { PendingDecision, DecisionPriority } from '@/lib/ativos/agentRoomTypes';

// =============================================================================
// Constants
// =============================================================================

const PRIORITY_COLORS: Record<DecisionPriority, string> = {
  alta: 'bg-red-500/20 text-red-400 border-red-500/30',
  normal: 'bg-zinc-500/20 text-zinc-400 border-zinc-500/30',
};

// =============================================================================
// Helper Functions
// =============================================================================

function formatTimeAgo(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / (1000 * 60));
  const diffHour = Math.floor(diffMin / 60);

  if (diffMin < 1) return 'agora';
  if (diffMin < 60) return `${diffMin} min`;
  if (diffHour < 24) return `${diffHour}h`;
  return `${Math.floor(diffHour / 24)}d`;
}

// =============================================================================
// Sub-Components
// =============================================================================

interface DecisionItemProps {
  decision: PendingDecision;
  index: number;
  onAction: (decisionId: string, action: string, hilTaskId?: string) => Promise<void>;
}

function DecisionItem({ decision, index, onAction }: DecisionItemProps) {
  const timeAgo = formatTimeAgo(new Date(decision.createdAt));

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className={`p-4 rounded-lg bg-white/5 border ${
        decision.priority === 'alta'
          ? 'border-red-500/30'
          : 'border-white/10'
      }`}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <Zap
            className={`w-4 h-4 ${
              decision.priority === 'alta' ? 'text-red-400' : 'text-yellow-400'
            }`}
          />
          <span className="text-xs text-text-muted">{decision.agentName}</span>
        </div>
        <div className="flex items-center gap-2">
          {decision.priority === 'alta' && (
            <Badge className={PRIORITY_COLORS.alta}>Urgente</Badge>
          )}
          <span className="text-xs text-text-muted">{timeAgo}</span>
        </div>
      </div>

      {/* Question */}
      <p className="text-sm text-text-primary mb-2">
        &ldquo;{decision.question}&rdquo;
      </p>

      {/* Context */}
      {decision.context && (
        <p className="text-xs text-text-muted mb-4">{decision.context}</p>
      )}

      {/* Action Buttons */}
      <div className="flex gap-2 flex-wrap">
        {decision.options.map((option, optIndex) => (
          <Button
            key={option.action}
            variant={optIndex === 0 ? 'default' : 'outline'}
            size="sm"
            onClick={() => onAction(decision.id, option.action, decision.hilTaskId)}
            className={
              optIndex === 0
                ? 'bg-magenta-mid hover:bg-magenta-mid/80'
                : ''
            }
          >
            {option.label}
          </Button>
        ))}
      </div>
    </motion.div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function PendingDecisions() {
  const { decisions, isConnected, error } = usePendingDecisions();

  const handleAction = useCallback(async (
    decisionId: string,
    action: string,
    hilTaskId?: string
  ) => {
    try {
      // If we have a HIL task ID, use the actual API
      if (hilTaskId) {
        if (action === 'approve' || action === 'create') {
          await approveTask({ task_id: hilTaskId });
        } else if (action === 'reject' || action === 'skip') {
          await rejectTask({ task_id: hilTaskId, reason: 'User decision from Agent Room' });
        }
      }

      // Log the action for now (will be replaced with real SSE integration)
      console.log('[Agent Room] Decision action:', { decisionId, action, hilTaskId });
    } catch (err) {
      console.error('[Agent Room] Decision action failed:', err);
    }
  }, []);

  return (
    <GlassCard>
      <GlassCardHeader>
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2">
            <Hand className="w-4 h-4 text-yellow-400" />
            <GlassCardTitle>Precisa de Você</GlassCardTitle>
            {decisions.length > 0 && (
              <Badge variant="destructive" className="text-xs">
                {decisions.length}
              </Badge>
            )}
          </div>
          {!isConnected && (
            <RefreshCw className="w-4 h-4 text-yellow-400 animate-spin" />
          )}
        </div>
        {error && (
          <p className="text-xs text-yellow-400 mt-1">{error}</p>
        )}
      </GlassCardHeader>

      <GlassCardContent>
        {decisions.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <CheckCircle className="w-12 h-12 text-green-400 mb-3" />
            <p className="text-sm text-text-muted">
              Nenhuma decisão pendente
            </p>
            <p className="text-xs text-text-muted mt-1">
              Os agentes estão trabalhando de forma autônoma
            </p>
          </div>
        ) : (
          <ScrollArea className="h-[220px]">
            <div className="space-y-3 pr-4">
              {decisions.map((decision, index) => (
                <DecisionItem
                  key={decision.id}
                  decision={decision}
                  index={index}
                  onAction={handleAction}
                />
              ))}
            </div>
          </ScrollArea>
        )}
      </GlassCardContent>
    </GlassCard>
  );
}
