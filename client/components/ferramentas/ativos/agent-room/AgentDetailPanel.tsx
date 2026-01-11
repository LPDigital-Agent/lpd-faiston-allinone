'use client';

/**
 * AgentDetailPanel Component
 *
 * Slide-in panel showing detailed information about an agent.
 * Opens from the right side when an agent card is clicked.
 */

import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Activity } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import type { AgentFriendlyStatus } from '@/lib/ativos/agentRoomTypes';
import { StatusIndicator } from './StatusIndicator';
import { AGENT_COLORS } from '@/lib/ativos/agentRoomConstants';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';

interface AgentDetailPanelProps {
  agent: {
    key: string;
    friendlyName: string;
    description: string;
    icon: LucideIcon;
    color: string;
    status: AgentFriendlyStatus;
    lastActivity?: string;
  };
  onClose: () => void;
}

export function AgentDetailPanel({ agent, onClose }: AgentDetailPanelProps) {
  const colorClasses = AGENT_COLORS[agent.color] || AGENT_COLORS.zinc;
  const Icon = agent.icon;

  // Close on ESC key
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex justify-end">
        {/* Backdrop */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          onClick={onClose}
          className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        />

        {/* Panel */}
        <motion.div
          initial={{ x: "100%", opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: "100%", opacity: 0 }}
          transition={{ type: "spring", damping: 25, stiffness: 200 }}
          className="relative w-full max-w-md h-full bg-background/95 backdrop-blur-xl border-l border-white/20 shadow-2xl"
        >
          <div className="flex flex-col h-full">
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-white/10">
              <h2 className="text-lg font-semibold text-text-primary">
                Detalhes do Agente
              </h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                className="shrink-0"
              >
                <X className="w-5 h-5" />
              </Button>
            </div>

            {/* Content */}
            <ScrollArea className="flex-1">
              <div className="p-6 space-y-6">
                {/* Agent Avatar and Name */}
                <div className="flex flex-col items-center text-center">
                  <div
                    className={`w-24 h-24 rounded-full flex items-center justify-center ${colorClasses.bg} ${colorClasses.border} border-4 mb-4`}
                  >
                    <Icon className={`w-12 h-12 ${colorClasses.text}`} />
                  </div>
                  <h3 className="text-xl font-bold text-text-primary mb-2">
                    {agent.friendlyName}
                  </h3>
                  <p className="text-sm text-text-muted leading-relaxed max-w-sm">
                    {agent.description}
                  </p>
                </div>

                {/* Current Status */}
                <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                  <div className="flex items-center justify-between mb-3">
                    <h4 className="text-sm font-semibold text-text-primary">
                      Status Atual
                    </h4>
                    <StatusIndicator status={agent.status} showLabel />
                  </div>
                  {agent.lastActivity && (
                    <p className="text-sm text-text-secondary">
                      {agent.lastActivity}
                    </p>
                  )}
                </div>

                {/* Recent Activity */}
                <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                  <div className="flex items-center gap-2 mb-3">
                    <Activity className="w-4 h-4 text-magenta-mid" />
                    <h4 className="text-sm font-semibold text-text-primary">
                      Atividades Recentes
                    </h4>
                  </div>
                  <div className="space-y-3">
                    {/* Recent activity items would come from props in a real implementation */}
                    {agent.lastActivity ? (
                      <div className="flex gap-3 text-sm">
                        <div className="shrink-0 mt-1.5">
                          <div className="w-1.5 h-1.5 rounded-full bg-magenta-mid" />
                        </div>
                        <div>
                          <p className="text-text-secondary leading-relaxed">
                            {agent.lastActivity}
                          </p>
                          <span className="text-xs text-text-muted">
                            Agora mesmo
                          </span>
                        </div>
                      </div>
                    ) : (
                      <p className="text-sm text-text-muted italic">
                        Nenhuma atividade recente
                      </p>
                    )}
                  </div>
                </div>

                {/* Agent Capabilities */}
                <div className="bg-white/5 rounded-xl p-4 border border-white/10">
                  <h4 className="text-sm font-semibold text-text-primary mb-3">
                    Capacidades
                  </h4>
                  <div className="space-y-2">
                    <div className="flex items-start gap-2">
                      <div className="shrink-0 mt-1">
                        <div className={`w-1.5 h-1.5 rounded-full ${colorClasses.bg}`} />
                      </div>
                      <p className="text-sm text-text-secondary">
                        {getAgentCapability(agent.key)}
                      </p>
                    </div>
                  </div>
                </div>

                {/* Agent ID (for debugging) */}
                <div className="text-center pt-4 border-t border-white/10">
                  <p className="text-xs text-text-muted font-mono">
                    ID: {agent.key}
                  </p>
                </div>
              </div>
            </ScrollArea>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}

/**
 * Helper function to get agent capability description
 * In a real implementation, this would come from the agent profile
 */
function getAgentCapability(agentKey: string): string {
  const capabilities: Record<string, string> = {
    nexo_import: 'Processa importações inteligentes com análise de NF e planilhas',
    intake: 'Recebe e valida notas fiscais de entrada',
    import: 'Importa dados de planilhas Excel e CSV',
    estoque_control: 'Monitora e controla movimentações de estoque',
    compliance: 'Verifica conformidade com políticas e regulamentos',
    reconciliacao: 'Detecta e resolve divergências de inventário',
    expedition: 'Gerencia processos de expedição e saída',
    carrier: 'Coordena transportadoras e logística',
    reverse: 'Processa devoluções e logística reversa',
    schema_evolution: 'Adapta estrutura de dados dinamicamente',
    learning: 'Aprende continuamente com interações',
    observation: 'Monitora mudanças e eventos do sistema',
    equipment_research: 'Pesquisa informações sobre equipamentos',
  };

  return capabilities[agentKey] || 'Executa tarefas especializadas no sistema';
}
