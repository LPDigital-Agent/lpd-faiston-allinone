'use client';

/**
 * AgentTeam Panel
 *
 * Shows the team of AI agents with their current status.
 * "Nossa Equipe de IA" - humanized agent profiles.
 */

import { useMemo, useState } from 'react';
import { motion, type Variants } from 'framer-motion';
import {
  GlassCard,
  GlassCardHeader,
  GlassCardTitle,
  GlassCardContent,
} from '@/components/shared/glass-card';
import { Users, RefreshCw } from 'lucide-react';
import { AgentCard } from './AgentCard';
import { AgentDetailPanel } from './AgentDetailPanel';
import { useAgentProfiles } from '@/hooks/ativos';
import { AGENT_PROFILES } from '@/lib/ativos/agentRoomConstants';
import type { AgentFriendlyStatus } from '@/lib/ativos/agentRoomTypes';

// =============================================================================
// Constants
// =============================================================================

// Primary agents to show (all agents from backend, grouped by function)
const PRIMARY_AGENTS = [
  // Importação & Entrada
  'nexo_import',
  'intake',
  'import',
  // Controle & Validação
  'estoque_control',
  'compliance',
  'reconciliacao',
  // Logística & Movimento
  'expedition',
  'carrier',
  'reverse',
  // Evolução & Aprendizado
  'schema_evolution',
  'learning',
  // Suporte & Pesquisa
  'observation',
  'equipment_research',
];

// Default statuses when no real-time data is available
const DEFAULT_STATUSES: Record<string, { status: AgentFriendlyStatus; lastActivity?: string }> = {
  nexo_import: { status: 'disponivel', lastActivity: 'Pronto para ajudar' },
  intake: { status: 'disponivel', lastActivity: 'Aguardando notas fiscais' },
  import: { status: 'disponivel', lastActivity: 'Pronto para importar' },
  estoque_control: { status: 'disponivel', lastActivity: 'Monitorando estoque' },
  compliance: { status: 'disponivel', lastActivity: 'Verificando conformidade' },
  reconciliacao: { status: 'disponivel', lastActivity: 'Detectando divergências' },
  expedition: { status: 'disponivel', lastActivity: 'Preparando expedições' },
  carrier: { status: 'disponivel', lastActivity: 'Gerenciando transportadoras' },
  reverse: { status: 'disponivel', lastActivity: 'Processando devoluções' },
  schema_evolution: { status: 'disponivel', lastActivity: 'Adaptando estrutura' },
  learning: { status: 'disponivel', lastActivity: 'Aprendendo continuamente' },
  observation: { status: 'disponivel', lastActivity: 'Monitorando mudanças' },
  equipment_research: { status: 'disponivel', lastActivity: 'Pesquisando equipamentos' },
};

// Animation variants
const containerVariants: Variants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.1,
    },
  },
};

// =============================================================================
// Main Component
// =============================================================================

export function AgentTeam() {
  const { agents, isConnected, error } = useAgentProfiles();
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);

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
        <motion.div
          variants={containerVariants}
          initial="hidden"
          animate="show"
          className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-5"
        >
          {agentCards.map((agent, index) => agent && (
            <AgentCard
              key={agent.key}
              index={index}
              friendlyName={agent.friendlyName}
              description={agent.description}
              icon={agent.icon}
              color={agent.color}
              status={agent.status}
              lastActivity={agent.lastActivity}
              onClick={() => setSelectedAgent(agent.key)}
            />
          ))}
        </motion.div>

        {/* Footer hint */}
        <p className="text-xs text-text-muted text-center mt-4">
          Clique em um agente para ver detalhes e atividades recentes
        </p>
      </GlassCardContent>

      {/* Agent Detail Panel */}
      {selectedAgent && agentCards.find(a => a?.key === selectedAgent) && (
        <AgentDetailPanel
          agent={agentCards.find(a => a?.key === selectedAgent)!}
          onClose={() => setSelectedAgent(null)}
        />
      )}
    </GlassCard>
  );
}
