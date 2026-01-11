'use client';

/**
 * StatusIndicator Component
 *
 * Animated status indicator for agent cards.
 * Shows a colored dot with optional pulse/ping animation.
 */

import { motion } from 'framer-motion';
import type { AgentFriendlyStatus } from '@/lib/ativos/agentRoomTypes';
import { STATUS_LABELS } from '@/lib/ativos/agentRoomConstants';

interface StatusIndicatorProps {
  status: AgentFriendlyStatus;
  showLabel?: boolean;
}

// Status color configurations
const STATUS_CONFIG: Record<AgentFriendlyStatus, {
  dotColor: string;
  ringColor: string;
  animate: boolean;
  animationType: 'pulse' | 'ping';
  label: string;
}> = {
  disponivel: {
    dotColor: 'bg-green-400',
    ringColor: 'border-green-400',
    animate: false,
    animationType: 'pulse',
    label: 'Disponível',
  },
  trabalhando: {
    dotColor: 'bg-blue-400',
    ringColor: 'border-blue-400',
    animate: true,
    animationType: 'pulse',
    label: 'Trabalhando',
  },
  esperando_voce: {
    dotColor: 'bg-yellow-400',
    ringColor: 'border-yellow-400',
    animate: true,
    animationType: 'ping',
    label: 'Esperando Você',
  },
  problema: {
    dotColor: 'bg-red-400',
    ringColor: 'border-red-400',
    animate: true,
    animationType: 'pulse',
    label: 'Problema',
  },
  descansando: {
    dotColor: 'bg-gray-400',
    ringColor: 'border-gray-400',
    animate: false,
    animationType: 'pulse',
    label: 'Descansando',
  },
};

export function StatusIndicator({ status, showLabel = false }: StatusIndicatorProps) {
  const config = STATUS_CONFIG[status];

  return (
    <div className="relative flex items-center gap-2 group">
      {/* Status Dot */}
      <div className="relative flex items-center justify-center">
        <div className={`w-2.5 h-2.5 rounded-full ${config.dotColor} z-10`} />

        {/* Animated Ring */}
        {config.animate && config.animationType === 'pulse' && (
          <motion.div
            className={`absolute inset-0 rounded-full border-2 ${config.ringColor}`}
            animate={{
              scale: [1, 1.5],
              opacity: [0.8, 0],
            }}
            transition={{
              duration: 1.5,
              repeat: Infinity,
              ease: "easeOut",
            }}
          />
        )}

        {/* Ping Animation */}
        {config.animate && config.animationType === 'ping' && (
          <>
            <motion.div
              className={`absolute inset-0 rounded-full ${config.dotColor}`}
              animate={{
                scale: [1, 2],
                opacity: [0.75, 0],
              }}
              transition={{
                duration: 1,
                repeat: Infinity,
              }}
            />
            <motion.div
              className={`absolute inset-0 rounded-full ${config.dotColor}`}
              animate={{
                scale: [1, 2],
                opacity: [0.75, 0],
              }}
              transition={{
                duration: 1,
                repeat: Infinity,
                delay: 0.5,
              }}
            />
          </>
        )}
      </div>

      {/* Optional Label */}
      {showLabel && (
        <span className="text-xs text-text-muted">{config.label}</span>
      )}

      {/* Tooltip on hover */}
      <div className="absolute bottom-full right-0 mb-2 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-50">
        <div className="bg-background/95 backdrop-blur-sm border border-white/20 rounded-lg px-2 py-1 shadow-lg whitespace-nowrap">
          <span className="text-xs text-text-primary">{config.label}</span>
        </div>
      </div>
    </div>
  );
}
