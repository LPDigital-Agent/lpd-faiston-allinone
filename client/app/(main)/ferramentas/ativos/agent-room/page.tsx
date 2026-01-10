'use client';

// =============================================================================
// Agent Room Page - Sala de Transparência
// =============================================================================
// A transparency window for users and clients to understand what AI agents
// are doing "behind the scenes". NOT a DevOps monitoring dashboard.
// Features: Live Feed, Agent Team, Learning Stories, Workflow, Decisions
// Design: Apple TV frosted dark glass (NEXO Copilot pattern)
// =============================================================================

import { motion } from 'framer-motion';
import { Eye, Radio } from 'lucide-react';

// Agent Room Components
import { LiveFeed } from '@/components/ferramentas/ativos/agent-room/LiveFeed';
import { AgentTeam } from '@/components/ferramentas/ativos/agent-room/AgentTeam';
import { LearningStories } from '@/components/ferramentas/ativos/agent-room/LearningStories';
import { WorkflowTimeline } from '@/components/ferramentas/ativos/agent-room/WorkflowTimeline';
import { PendingDecisions } from '@/components/ferramentas/ativos/agent-room/PendingDecisions';

// =============================================================================
// Page Header Component
// =============================================================================

function PageHeader() {
  return (
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <div className="flex items-center gap-2">
          <Eye className="w-5 h-5 text-magenta-mid" />
          <h1 className="text-xl font-semibold text-text-primary">
            Agent Room
          </h1>
          <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-green-500/20 border border-green-500/30">
            <Radio className="w-3 h-3 text-green-400 animate-pulse" />
            <span className="text-xs text-green-400 font-medium">Ao Vivo</span>
          </div>
        </div>
        <p className="text-sm text-text-muted mt-1">
          Veja o que nossos agentes de IA estão fazendo por você
        </p>
      </div>
    </div>
  );
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function AgentRoomPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader />

      {/* Live Feed - Full Width Top Panel */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
      >
        <LiveFeed />
      </motion.div>

      {/* Main Grid - 2 columns */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="space-y-6">
          {/* Agent Team Panel */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
          >
            <AgentTeam />
          </motion.div>

          {/* Workflow Timeline Panel */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <WorkflowTimeline />
          </motion.div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Learning Stories Panel */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
          >
            <LearningStories />
          </motion.div>

          {/* Pending Decisions Panel */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <PendingDecisions />
          </motion.div>
        </div>
      </div>
    </div>
  );
}
