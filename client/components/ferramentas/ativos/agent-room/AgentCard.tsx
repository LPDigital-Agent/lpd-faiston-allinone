'use client';

/**
 * AgentCard Component
 *
 * Individual agent card showing avatar, name, status, and last activity.
 * Part of the Agent Team panel in the Agent Room.
 */

import { motion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import type { AgentFriendlyStatus } from '@/lib/ativos/agentRoomTypes';
import {
  STATUS_DOT_COLORS,
  STATUS_LABELS,
  AGENT_COLORS,
} from '@/lib/ativos/agentRoomConstants';

interface AgentCardProps {
  /** Human-friendly agent name */
  friendlyName: string;
  /** Agent description */
  description: string;
  /** Lucide icon component */
  icon: LucideIcon;
  /** Agent color theme */
  color: string;
  /** Current status */
  status: AgentFriendlyStatus;
  /** Last activity description */
  lastActivity?: string;
}

export function AgentCard({
  friendlyName,
  description,
  icon: Icon,
  color,
  status,
  lastActivity,
}: AgentCardProps) {
  const colorClasses = AGENT_COLORS[color] || AGENT_COLORS.zinc;
  const statusDotColor = STATUS_DOT_COLORS[status];
  const statusLabel = STATUS_LABELS[status];

  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="relative flex flex-col items-center p-4 rounded-xl bg-white/5 border border-white/10 hover:border-white/20 transition-all cursor-pointer group"
    >
      {/* Status Dot */}
      <div className="absolute top-2 right-2">
        <div className={`w-2.5 h-2.5 rounded-full ${statusDotColor}`} />
      </div>

      {/* Agent Avatar */}
      <div
        className={`w-14 h-14 rounded-full flex items-center justify-center ${colorClasses.bg} ${colorClasses.border} border mb-3`}
      >
        <Icon className={`w-7 h-7 ${colorClasses.text}`} />
      </div>

      {/* Agent Name */}
      <h3 className="text-sm font-medium text-text-primary text-center">
        {friendlyName}
      </h3>

      {/* Description */}
      <p className="text-xs text-text-muted text-center mt-1 line-clamp-2">
        {description}
      </p>

      {/* Status Label */}
      <div className="mt-2 px-2 py-0.5 rounded-full bg-white/5 border border-white/10">
        <span className="text-xs text-text-muted">{statusLabel}</span>
      </div>

      {/* Last Activity (on hover) */}
      {lastActivity && (
        <motion.div
          initial={{ opacity: 0, y: 5 }}
          whileHover={{ opacity: 1, y: 0 }}
          className="absolute inset-0 flex items-center justify-center bg-background/95 backdrop-blur-sm rounded-xl opacity-0 group-hover:opacity-100 transition-opacity p-3"
        >
          <p className="text-xs text-text-muted text-center">{lastActivity}</p>
        </motion.div>
      )}
    </motion.div>
  );
}
