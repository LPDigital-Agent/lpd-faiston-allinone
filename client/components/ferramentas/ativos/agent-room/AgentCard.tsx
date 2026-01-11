'use client';

/**
 * AgentCard Component
 *
 * Individual agent card showing avatar, name, status, and last activity.
 * Part of the Agent Team panel in the Agent Room.
 */

import { motion, type Variants } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';
import type { AgentFriendlyStatus } from '@/lib/ativos/agentRoomTypes';
import { StatusIndicator } from './StatusIndicator';
import { AGENT_COLORS } from '@/lib/ativos/agentRoomConstants';

interface AgentCardProps {
  /** Animation index for stagger effect */
  index: number;
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
  /** Click handler to open detail panel */
  onClick: () => void;
}

// Animation variants
const cardVariants: Variants = {
  hidden: { opacity: 0, y: 20, scale: 0.95 },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      type: "spring" as const,
      stiffness: 100,
      damping: 12,
    },
  },
  hover: {
    y: -8,
    boxShadow: "0 20px 40px rgba(253, 17, 164, 0.15)",
    transition: { type: "spring" as const, stiffness: 300, damping: 20 },
  },
  tap: { scale: 0.98 },
};

export function AgentCard({
  index,
  friendlyName,
  description,
  icon: Icon,
  color,
  status,
  lastActivity,
  onClick,
}: AgentCardProps) {
  const colorClasses = AGENT_COLORS[color] || AGENT_COLORS.zinc;

  return (
    <motion.div
      variants={cardVariants}
      initial="hidden"
      animate="visible"
      whileHover="hover"
      whileTap="tap"
      onClick={onClick}
      className="relative flex flex-col items-center p-5 rounded-xl bg-white/5 border border-white/10 hover:border-magenta-mid/50 transition-colors cursor-pointer"
    >
      {/* Status Indicator */}
      <div className="absolute top-3 right-3">
        <StatusIndicator status={status} />
      </div>

      {/* Agent Avatar */}
      <div
        className={`w-16 h-16 rounded-full flex items-center justify-center ${colorClasses.bg} ${colorClasses.border} border-2 mb-3 transition-transform group-hover:scale-110`}
      >
        <Icon className={`w-8 h-8 ${colorClasses.text}`} />
      </div>

      {/* Agent Name */}
      <h3 className="text-sm font-semibold text-text-primary text-center">
        {friendlyName}
      </h3>

      {/* Description */}
      <p className="text-xs text-text-muted text-center mt-1.5 line-clamp-2 leading-relaxed">
        {description}
      </p>

      {/* Last Activity Hint */}
      {lastActivity && (
        <p className="text-xs text-magenta-mid/60 text-center mt-2 line-clamp-1">
          {lastActivity}
        </p>
      )}
    </motion.div>
  );
}
