/**
 * useAgentRoomStream - Polling-Based Data Fetching for Agent Room
 *
 * Provides real-time-like data fetching for the Agent Room transparency window.
 * Uses TanStack Query for efficient polling with automatic background refetching.
 *
 * Architecture:
 * - Polling-first approach (more reliable with AgentCore Gateway)
 * - Single endpoint returns all Agent Room data
 * - Fallback to mock data when backend is unavailable
 * - Ready for SSE upgrade when needed
 */

import { useState, useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  getAgentRoomData,
  type AgentRoomDataResponse,
  type AgentRoomAgent,
  type AgentRoomLiveMessage,
  type AgentRoomLearningStory,
  type AgentRoomWorkflow,
  type AgentRoomDecision,
} from '@/services/sgaAgentcore';
import { AGENT_PROFILES } from '@/lib/ativos/agentRoomConstants';
import type {
  LiveMessage,
  AgentProfile,
  LearningStory,
  ActiveWorkflow,
  PendingDecision,
} from '@/lib/ativos/agentRoomTypes';

// =============================================================================
// Types
// =============================================================================

export interface AgentRoomStreamState {
  /** Whether data is being fetched */
  isLoading: boolean;
  /** Whether connection/polling is active */
  isConnected: boolean;
  /** Live feed messages */
  messages: LiveMessage[];
  /** Agent profiles with current status */
  agents: AgentProfile[];
  /** Learning stories */
  learningStories: LearningStory[];
  /** Current active workflow */
  activeWorkflow: ActiveWorkflow | null;
  /** Pending decisions requiring human input */
  pendingDecisions: PendingDecision[];
  /** Last error message */
  error: string | null;
  /** Timestamp of last received data */
  lastEventAt: string | null;
}

export interface UseAgentRoomStreamOptions {
  /** Enable polling (default: true) */
  enabled?: boolean;
  /** Polling interval in ms (default: 5000) */
  refetchInterval?: number;
  /** Filter events by session ID (A2A session context) */
  sessionId?: string;
  /** Maximum number of live feed events to return (default: 50) */
  limit?: number;
}

export interface UseAgentRoomStreamReturn extends AgentRoomStreamState {
  /** Manually refetch data */
  refetch: () => void;
  /** Clear all messages */
  clearMessages: () => void;
  /** Pause/resume polling */
  isPaused: boolean;
  setPaused: (paused: boolean) => void;
}

// =============================================================================
// Data Transformation
// =============================================================================

/**
 * Transform backend agent data to frontend AgentProfile format.
 */
function transformAgents(agents: AgentRoomAgent[]): AgentProfile[] {
  return agents.map((agent) => ({
    id: agent.id,
    technicalName: agent.technicalName,
    friendlyName: agent.friendlyName,
    description: agent.description,
    avatar: agent.avatar,
    color: agent.color as AgentProfile['color'],
    status: agent.status as AgentProfile['status'],
    lastActivity: agent.lastActivity ?? undefined,
  }));
}

/**
 * Transform backend live messages to frontend LiveMessage format.
 */
function transformMessages(messages: AgentRoomLiveMessage[]): LiveMessage[] {
  return messages.map((msg) => ({
    id: msg.id,
    timestamp: msg.timestamp,
    agentName: msg.agentName,
    message: msg.message,
    type: msg.type,
  }));
}

/**
 * Transform backend learning stories to frontend LearningStory format.
 */
function transformLearningStories(stories: AgentRoomLearningStory[]): LearningStory[] {
  return stories.map((story) => ({
    id: story.id,
    learnedAt: story.learnedAt,
    agentName: story.agentName,
    story: story.story,
    confidence: story.confidence,
  }));
}

/**
 * Transform backend workflow to frontend ActiveWorkflow format.
 */
function transformWorkflow(workflow: AgentRoomWorkflow | null): ActiveWorkflow | null {
  if (!workflow) return null;

  return {
    id: workflow.id,
    name: workflow.name,
    startedAt: workflow.startedAt,
    steps: workflow.steps.map((step) => ({
      id: step.id,
      label: step.label,
      icon: step.icon,
      status: step.status,
    })),
  };
}

/**
 * Transform backend decisions to frontend PendingDecision format.
 */
function transformDecisions(decisions: AgentRoomDecision[]): PendingDecision[] {
  return decisions.map((decision) => ({
    id: decision.id,
    question: decision.question,
    options: decision.options,
    priority: decision.priority,
    createdAt: decision.createdAt,
    agentName: 'Sistema', // Default agent name for backend decisions
  }));
}

/**
 * Get mock agent profiles from constants.
 * Returns ALL agents defined in AGENT_PROFILES (no artificial limit).
 */
function getMockAgentProfiles(): AgentProfile[] {
  return Object.entries(AGENT_PROFILES).map(([id, config]) => ({
    id,
    technicalName: id,
    friendlyName: config.friendlyName,
    description: config.description,
    avatar: config.icon.displayName || 'Bot',
    color: config.color as AgentProfile['color'],
    status: 'disponivel' as const,
    lastActivity: undefined,
  }));
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useAgentRoomStream(
  options: UseAgentRoomStreamOptions = {}
): UseAgentRoomStreamReturn {
  const {
    enabled = true,
    refetchInterval = 5000,
    sessionId,
    limit,
  } = options;

  const [isPaused, setPaused] = useState(false);
  const [clearedMessages, setClearedMessages] = useState<string[]>([]);

  // =============================================================================
  // TanStack Query for Polling
  // =============================================================================

  const {
    data,
    isLoading,
    error,
    refetch,
    dataUpdatedAt,
  } = useQuery({
    // Include sessionId in query key for proper cache separation
    queryKey: ['agent-room-data', sessionId ?? 'all'],
    queryFn: async (): Promise<AgentRoomDataResponse | null> => {
      // PRODUCTION: Always fetch real data from backend
      try {
        const response = await getAgentRoomData({ sessionId, limit });
        console.log('[Agent Room] Data fetched:', {
          success: response.data?.success,
          liveFeedCount: response.data?.liveFeed?.length ?? 0,
          agentsCount: response.data?.agents?.length ?? 0,
          sessionId: sessionId ?? 'all',
        });
        return response.data;
      } catch (err) {
        console.error('[Agent Room] Failed to fetch data:', err);
        throw err;
      }
    },
    enabled: enabled && !isPaused,
    refetchInterval: isPaused ? false : refetchInterval,
    refetchIntervalInBackground: false,
    staleTime: refetchInterval / 2,
    // Increased retry for network resilience - Agent Room should keep trying
    retry: 5,
    retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 10000),
    // Keep polling even after errors - Agent Room is critical for visibility
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });

  // =============================================================================
  // Transform Data
  // =============================================================================

  const state = useMemo((): AgentRoomStreamState => {
    // No data yet - return loading/empty state (NO MOCK DATA - PRODUCTION)
    if (!data) {
      return {
        isLoading,
        isConnected: !isLoading && !error,
        messages: [],
        agents: getMockAgentProfiles(), // Static agent list from AGENT_PROFILES
        learningStories: [],
        activeWorkflow: null,
        pendingDecisions: [],
        error: error ? String(error) : null,
        lastEventAt: null,
      };
    }

    // Transform backend data - NO FAKE FALLBACKS (PRODUCTION)
    // Empty arrays and null are valid states, not errors
    return {
      isLoading,
      isConnected: data.success,
      messages: transformMessages(data.liveFeed || []).filter((m) => !clearedMessages.includes(m.id)),
      agents: (data.agents?.length ?? 0) > 0 ? transformAgents(data.agents) : getMockAgentProfiles(),
      learningStories: transformLearningStories(data.learningStories || []),
      activeWorkflow: transformWorkflow(data.activeWorkflow),
      pendingDecisions: transformDecisions(data.pendingDecisions || []),
      error: data.success ? null : 'Erro ao carregar dados',
      lastEventAt: data.timestamp,
    };
  }, [data, isLoading, error, clearedMessages]);

  // =============================================================================
  // Actions
  // =============================================================================

  const clearMessages = useCallback(() => {
    setClearedMessages((prev) => [
      ...prev,
      ...state.messages.map((m) => m.id),
    ]);
  }, [state.messages]);

  const handleRefetch = useCallback(() => {
    refetch();
  }, [refetch]);

  // =============================================================================
  // Return
  // =============================================================================

  return {
    ...state,
    refetch: handleRefetch,
    clearMessages,
    isPaused,
    setPaused,
  };
}

// =============================================================================
// Specialized Hooks (for individual components)
// =============================================================================

/**
 * Hook for just the live feed messages.
 */
export function useLiveFeed(options?: UseAgentRoomStreamOptions) {
  const { messages, isConnected, isLoading, error, isPaused, setPaused, clearMessages } =
    useAgentRoomStream(options);
  return { messages, isConnected, isLoading, error, isPaused, setPaused, clearMessages };
}

/**
 * Hook for agent profiles with status.
 */
export function useAgentProfiles(options?: UseAgentRoomStreamOptions) {
  const { agents, isConnected, isLoading, error } = useAgentRoomStream(options);
  return { agents, isConnected, isLoading, error };
}

/**
 * Hook for learning stories.
 */
export function useLearningStories(options?: UseAgentRoomStreamOptions) {
  const { learningStories, isConnected, isLoading, error } = useAgentRoomStream(options);
  return { stories: learningStories, isConnected, isLoading, error };
}

/**
 * Hook for active workflow timeline.
 */
export function useWorkflowTimeline(options?: UseAgentRoomStreamOptions) {
  const { activeWorkflow, isConnected, isLoading, error } = useAgentRoomStream(options);
  return { workflow: activeWorkflow, isConnected, isLoading, error };
}

/**
 * Hook for pending decisions.
 */
export function usePendingDecisions(options?: UseAgentRoomStreamOptions) {
  const { pendingDecisions, isConnected, isLoading, error } = useAgentRoomStream(options);
  return { decisions: pendingDecisions, isConnected, isLoading, error };
}
