'use client';

/**
 * WorkflowTimeline Panel
 *
 * Visual timeline showing the current workflow progress.
 * "Fluxo Atual" - animated step-by-step workflow.
 */

import { motion } from 'framer-motion';
import {
  GlassCard,
  GlassCardHeader,
  GlassCardTitle,
  GlassCardContent,
} from '@/components/shared/glass-card';
import {
  ArrowRight,
  FileText,
  Search,
  CheckCircle,
  Package,
  Clock,
  RefreshCw,
} from 'lucide-react';
import { useWorkflowTimeline } from '@/hooks/ativos';
import type { WorkflowStep, WorkflowStepStatus } from '@/lib/ativos/agentRoomTypes';

// =============================================================================
// Constants
// =============================================================================

const STEP_ICONS: Record<string, React.ElementType> = {
  FileText,
  Search,
  CheckCircle,
  Package,
  Clock,
};

const STEP_STATUS_COLORS: Record<WorkflowStepStatus, { bg: string; text: string; border: string }> = {
  concluido: {
    bg: 'bg-green-500/20',
    text: 'text-green-400',
    border: 'border-green-500/30',
  },
  atual: {
    bg: 'bg-magenta-mid/20',
    text: 'text-magenta-light',
    border: 'border-magenta-mid/30',
  },
  pendente: {
    bg: 'bg-zinc-500/20',
    text: 'text-zinc-400',
    border: 'border-zinc-500/30',
  },
};

// =============================================================================
// Sub-Components
// =============================================================================

interface WorkflowStepItemProps {
  step: WorkflowStep;
  index: number;
  isLast: boolean;
}

function WorkflowStepItem({ step, index, isLast }: WorkflowStepItemProps) {
  const Icon = STEP_ICONS[step.icon] || FileText;
  const colors = STEP_STATUS_COLORS[step.status];
  const isCurrent = step.status === 'atual';

  return (
    <div className="flex items-center">
      {/* Step Circle */}
      <motion.div
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ delay: index * 0.1 }}
        className="flex flex-col items-center"
      >
        <div
          className={`relative w-12 h-12 rounded-full flex items-center justify-center ${colors.bg} ${colors.border} border-2 ${
            isCurrent ? 'ring-2 ring-magenta-mid/50 ring-offset-2 ring-offset-background' : ''
          }`}
        >
          {isCurrent && (
            <motion.div
              className="absolute inset-0 rounded-full bg-magenta-mid/30"
              animate={{ scale: [1, 1.2, 1] }}
              transition={{ repeat: Infinity, duration: 2 }}
            />
          )}
          <Icon className={`w-5 h-5 ${colors.text} relative z-10`} />
        </div>
        <span
          className={`text-xs mt-2 text-center ${
            step.status === 'pendente' ? 'text-text-muted' : 'text-text-primary'
          }`}
        >
          {step.label}
        </span>
        {step.detail && (
          <span className="text-xs text-text-muted mt-0.5">{step.detail}</span>
        )}
      </motion.div>

      {/* Arrow Connector */}
      {!isLast && (
        <div className="flex-1 flex items-center px-2 -mt-5">
          <div
            className={`h-0.5 flex-1 ${
              step.status === 'concluido' ? 'bg-green-500/50' : 'bg-zinc-500/30'
            }`}
          />
          <ArrowRight
            className={`w-4 h-4 ${
              step.status === 'concluido' ? 'text-green-400' : 'text-zinc-500'
            }`}
          />
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function WorkflowTimeline() {
  const { workflow, isConnected, error } = useWorkflowTimeline();

  // No active workflow
  if (!workflow) {
    return (
      <GlassCard>
        <GlassCardHeader>
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-2">
              <RefreshCw className="w-4 h-4 text-blue-400" />
              <GlassCardTitle>Fluxo Atual</GlassCardTitle>
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
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Clock className="w-12 h-12 text-text-muted mb-3" />
            <p className="text-sm text-text-muted">
              Nenhum fluxo em andamento
            </p>
            <p className="text-xs text-text-muted mt-1">
              Os fluxos aparecerão aqui quando algo estiver sendo processado
            </p>
          </div>
        </GlassCardContent>
      </GlassCard>
    );
  }

  return (
    <GlassCard>
      <GlassCardHeader>
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2">
            <RefreshCw className="w-4 h-4 text-blue-400 animate-spin" />
            <GlassCardTitle>Fluxo Atual</GlassCardTitle>
          </div>
          <span className="text-xs text-text-muted">{workflow.name}</span>
        </div>
        {error && (
          <p className="text-xs text-yellow-400 mt-1">{error}</p>
        )}
      </GlassCardHeader>

      <GlassCardContent>
        {/* Workflow Description */}
        {workflow.description && (
          <p className="text-sm text-text-muted mb-4">{workflow.description}</p>
        )}

        {/* Timeline */}
        <div className="flex items-start justify-between overflow-x-auto pb-2">
          {workflow.steps.map((step, index) => (
            <WorkflowStepItem
              key={step.id}
              step={step}
              index={index}
              isLast={index === workflow.steps.length - 1}
            />
          ))}
        </div>

        {/* Current Agent */}
        {workflow.currentAgent && (
          <div className="mt-4 pt-4 border-t border-white/10 flex items-center justify-center gap-2">
            <div className="w-2 h-2 rounded-full bg-magenta-mid animate-pulse" />
            <span className="text-xs text-text-muted">
              {workflow.currentAgent} está trabalhando...
            </span>
          </div>
        )}
      </GlassCardContent>
    </GlassCard>
  );
}
