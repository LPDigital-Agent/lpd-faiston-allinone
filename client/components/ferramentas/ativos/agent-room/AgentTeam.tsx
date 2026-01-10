'use client';

/**
 * AgentTeam Panel
 *
 * Shows the team of AI agents with their current status.
 * "Nossa Equipe de IA" - humanized agent profiles.
 */

import { useMemo } from 'react';
import {
  GlassCard,
  GlassCardHeader,
  GlassCardTitle,
  GlassCardContent,
} from '@/components/shared/glass-card';
import { Users, RefreshCw } from 'lucide-react';
import { AgentCard } from './AgentCard';
import { useAgentProfiles } from '@/hooks/ativos';
import { AGENT_PROFILES } from '@/lib/ativos/agentRoomConstants';
import type { AgentFriendlyStatus } from '@/lib/ativos/agentRoomTypes';

// =============================================================================
// Constants
// =============================================================================

// Primary agents to show (subset of all agents)
const PRIMARY_AGENTS = [
  'nexo_import',
  'intake',
  'import',
  'compliance',
  'learning',
  'stock_control',
];

// Default statuses when no real-time data is available
const DEFAULT_STATUSES: Record<string, { status: AgentFriendlyStatus; lastActivity?: string }> = {
  nexo_import: { status: 'disponivel', lastActivity: 'Pronto para ajudar' },
  intake: { status: 'disponivel', lastActivity: 'Aguardando notas fiscais' },
  import: { status: 'disponivel', lastActivity: 'Pronto para importar' },
  compliance: { status: 'disponivel', lastActivity: 'Verificando conformidade' },
  learning: { status: 'disponivel', lastActivity: 'Aprendendo continuamente' },
  stock_control: { status: 'disponivel', lastActivity: 'Monitorando estoque' },
};

// =============================================================================
// Main Component
// =============================================================================

export function AgentTeam() {
  const { agents, isConnected, error } = useAgentProfiles();

  // Merge real-time agent data with static profiles
  const agentCards = useMemo(() => {
    return PRIMARY_AGENTS.map((agentKey) => {
      const profile = AGENT_PROFILES[agentKey];
      if (!profile) return null;

      // Check if we have real-time data for this agent
      const realtimeAgent = agents.find(
        (a) => a.id === agentKey || a.technicalName?.toLowerCase().includes(agentKey)
      );

      const statusData = realtimeAgent
        ? { status: realtimeAgent.status, lastActivity: realtimeAgent.lastActivity }
        : DEFAULT_STATUSES[agentKey] || { status: 'disponivel' as const };

      return {
        key: agentKey,
        friendlyName: profile.friendlyName,
        description: profile.description,
        icon: profile.icon,
        color: profile.color,
        status: statusData.status,
        lastActivity: statusData.lastActivity,
      };
    }).filter(Boolean);
  }, [agents]);

  return (
    <GlassCard>
      <GlassCardHeader>
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2">
            <Users className="w-4 h-4 text-magenta-mid" />
            <GlassCardTitle>Nossa Equipe de IA</GlassCardTitle>
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
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {agentCards.map((agent) => agent && (
            <AgentCard
              key={agent.key}
              friendlyName={agent.friendlyName}
              description={agent.description}
              icon={agent.icon}
              color={agent.color}
              status={agent.status}
              lastActivity={agent.lastActivity}
            />
          ))}
        </div>

        {/* Footer hint */}
        <p className="text-xs text-text-muted text-center mt-4">
          Passe o mouse sobre um agente para ver sua última atividade
        </p>
      </GlassCardContent>
    </GlassCard>
  );
}
