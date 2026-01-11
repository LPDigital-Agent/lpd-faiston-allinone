'use client';

// =============================================================================
// Agent Room Page - Sala de Transparência
// =============================================================================
// A transparency window for users and clients to understand what AI agents
// are doing "behind the scenes". NOT a DevOps monitoring dashboard.
// Features: Live Feed, Agent Team, Learning Stories, Workflow, Decisions
// Design: Apple TV frosted dark glass (NEXO Copilot pattern)
// =============================================================================

import { Suspense } from 'react';
import { motion } from 'framer-motion';
import {
  Eye,
  Radio,
  WifiOff,
  RefreshCw,
  AlertCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';

// Agent Room Components
import {
  LiveFeed,
  AgentTeam,
  LearningStories,
  WorkflowTimeline,
  AgentXRay,
  LiveFeedSkeleton,
  AgentTeamSkeleton,
  LearningStoriesSkeleton,
  WorkflowTimelineSkeleton,
  AgentXRaySkeleton,
} from '@/components/ferramentas/ativos/agent-room';

// Hook for connection status
import { useAgentRoomStream } from '@/hooks/ativos';

// =============================================================================
// Connection Status Badge
// =============================================================================

interface ConnectionStatusProps {
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
}

function ConnectionStatus({
  isConnected,
  isLoading,
  error,
  onRetry,
}: ConnectionStatusProps) {
  if (isLoading) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <div
              className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-yellow-500/20 border border-yellow-500/30"
              role="status"
              aria-label="Conectando aos agentes"
            >
              <RefreshCw className="w-3 h-3 text-yellow-400 animate-spin" aria-hidden="true" />
              <span className="text-xs text-yellow-400 font-medium">Conectando</span>
            </div>
          </TooltipTrigger>
          <TooltipContent>
            <p>Estabelecendo conexão com os agentes...</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  if (error || !isConnected) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              variant="ghost"
              size="sm"
              onClick={onRetry}
              className="flex items-center gap-1.5 px-2 py-0.5 h-auto rounded-full bg-red-500/20 border border-red-500/30 hover:bg-red-500/30"
              aria-label="Reconectar aos agentes"
            >
              <WifiOff className="w-3 h-3 text-red-400" aria-hidden="true" />
              <span className="text-xs text-red-400 font-medium">Desconectado</span>
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            <p>{error || 'Conexão perdida. Clique para reconectar.'}</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <div
            className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-green-500/20 border border-green-500/30"
            role="status"
            aria-live="polite"
            aria-label="Conectado e recebendo dados ao vivo"
          >
            <Radio className="w-3 h-3 text-green-400 animate-pulse" aria-hidden="true" />
            <span className="text-xs text-green-400 font-medium">Ao Vivo</span>
          </div>
        </TooltipTrigger>
        <TooltipContent>
          <p>Recebendo atualizações em tempo real</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

// =============================================================================
// Page Header Component
// =============================================================================

interface PageHeaderProps {
  isConnected: boolean;
  isLoading: boolean;
  error: string | null;
  onRetry: () => void;
}

function PageHeader({ isConnected, isLoading, error, onRetry }: PageHeaderProps) {
  return (
    <header className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
      <div>
        <div className="flex items-center gap-2 flex-wrap">
          <Eye className="w-5 h-5 text-magenta-mid" aria-hidden="true" />
          <h1 className="text-xl font-semibold text-text-primary">
            Agent Room
          </h1>
          <ConnectionStatus
            isConnected={isConnected}
            isLoading={isLoading}
            error={error}
            onRetry={onRetry}
          />
        </div>
        <p className="text-sm text-text-muted mt-1">
          Veja o que nossos agentes de IA estão fazendo por você
        </p>
      </div>

      {/* Keyboard Navigation Help (visible on focus) */}
      <div className="hidden sm:block">
        <p className="text-xs text-text-muted sr-only focus:not-sr-only">
          Use Tab para navegar entre os painéis
        </p>
      </div>
    </header>
  );
}

// =============================================================================
// Error Fallback
// =============================================================================

interface ErrorFallbackProps {
  error: string;
  onRetry: () => void;
}

function ErrorFallback({ error, onRetry }: ErrorFallbackProps) {
  return (
    <div
      className="flex flex-col items-center justify-center py-12 text-center"
      role="alert"
      aria-live="assertive"
    >
      <AlertCircle className="w-12 h-12 text-red-400 mb-4" aria-hidden="true" />
      <h2 className="text-lg font-medium text-text-primary mb-2">
        Não foi possível carregar o Agent Room
      </h2>
      <p className="text-sm text-text-muted mb-4 max-w-md">
        {error || 'Ocorreu um erro ao conectar com os agentes. Verifique sua conexão e tente novamente.'}
      </p>
      <Button onClick={onRetry} className="gap-2">
        <RefreshCw className="w-4 h-4" aria-hidden="true" />
        Tentar novamente
      </Button>
    </div>
  );
}

// =============================================================================
// Main Page Component
// =============================================================================

export default function AgentRoomPage() {
  // PRODUCTION: Always uses real data from backend via AgentCore Gateway
  const { isConnected, isLoading, error, refetch } = useAgentRoomStream();

  // Show error state if critical error
  const hasCriticalError = error && !isConnected && !isLoading;

  return (
    <main
      className="space-y-6"
      role="main"
      aria-label="Painel de transparência dos agentes de IA"
    >
      {/* Page Header with Connection Status */}
      <PageHeader
        isConnected={isConnected}
        isLoading={isLoading}
        error={error}
        onRetry={refetch}
      />

      {hasCriticalError ? (
        <ErrorFallback error={error} onRetry={refetch} />
      ) : (
        <>
          {/* Live Feed - Full Width Top Panel */}
          <motion.section
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            aria-labelledby="live-feed-title"
          >
            <h2 id="live-feed-title" className="sr-only">
              Feed de atividades ao vivo
            </h2>
            <Suspense fallback={<LiveFeedSkeleton />}>
              <LiveFeed />
            </Suspense>
          </motion.section>

          {/* Agent Team - FULL WIDTH Primary Panel */}
          <motion.section
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            aria-labelledby="agent-team-title"
          >
            <h2 id="agent-team-title" className="sr-only">
              Nossa equipe de agentes de IA
            </h2>
            <Suspense fallback={<AgentTeamSkeleton />}>
              <AgentTeam />
            </Suspense>
          </motion.section>

          {/* Row 1: Learning Stories + X-Ray (2 columns) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 sm:gap-6">
            {/* Learning Stories Panel */}
            <motion.section
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              aria-labelledby="learning-title"
            >
              <h2 id="learning-title" className="sr-only">
                O que os agentes aprenderam
              </h2>
              <Suspense fallback={<LearningStoriesSkeleton />}>
                <LearningStories />
              </Suspense>
            </motion.section>

            {/* X-Ray Panel (Real-time Agent Traces) */}
            <motion.section
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.35 }}
              aria-labelledby="xray-title"
            >
              <h2 id="xray-title" className="sr-only">
                X-Ray - Rastreamento de atividades em tempo real
              </h2>
              <Suspense fallback={<AgentXRaySkeleton />}>
                <AgentXRay />
              </Suspense>
            </motion.section>
          </div>

          {/* Row 2: Workflow Timeline (full width) */}
          <motion.section
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            aria-labelledby="workflow-title"
          >
            <h2 id="workflow-title" className="sr-only">
              Fluxo de trabalho atual
            </h2>
            <Suspense fallback={<WorkflowTimelineSkeleton />}>
              <WorkflowTimeline />
            </Suspense>
          </motion.section>
        </>
      )}

      {/* Skip Link Target (for keyboard navigation) */}
      <div id="main-content" tabIndex={-1} className="sr-only">
        Conteúdo principal do Agent Room
      </div>
    </main>
  );
}
