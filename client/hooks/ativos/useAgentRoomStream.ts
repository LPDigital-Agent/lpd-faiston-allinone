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
import {
  MOCK_LIVE_MESSAGES,
  MOCK_LEARNING_STORIES,
  MOCK_PENDING_DECISIONS,
  MOCK_ACTIVE_WORKFLOW,
  AGENT_PROFILES,
} from '@/lib/ativos/agentRoomConstants';
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
  /** Use mock data instead of real API (default: false) */
  useMockData?: boolean;
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
 */
function getMockAgentProfiles(): AgentProfile[] {
  return Object.entries(AGENT_PROFILES).slice(0, 6).map(([id, config]) => ({
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
    useMockData = false, // Set to false to use real backend
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
    queryKey: ['agent-room-data'],
    queryFn: async (): Promise<AgentRoomDataResponse | null> => {
      if (useMockData) {
        // Return mock data structure
        return {
          success: true,
          timestamp: new Date().toISOString(),
          agents: [],
          liveFeed: [],
          learningStories: [],
          activeWorkflow: null,
          pendingDecisions: [],
        };
      }

      try {
        const response = await getAgentRoomData();
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
    retry: 2,
    retryDelay: 1000,
  });

  // =============================================================================
  // Transform Data
  // =============================================================================

  const state = useMemo((): AgentRoomStreamState => {
    // Use mock data if enabled or if no backend data
    if (useMockData || !data) {
      return {
        isLoading,
        isConnected: !isLoading && !error,
        messages: MOCK_LIVE_MESSAGES.filter((m) => !clearedMessages.includes(m.id)),
        agents: getMockAgentProfiles(),
        learningStories: MOCK_LEARNING_STORIES,
        activeWorkflow: MOCK_ACTIVE_WORKFLOW,
        pendingDecisions: MOCK_PENDING_DECISIONS,
        error: error ? String(error) : null,
        lastEventAt: useMockData ? new Date().toISOString() : null,
      };
    }

    // Transform backend data (with defensive null checks for all arrays)
    return {
      isLoading,
      isConnected: data.success,
      messages: transformMessages(data.liveFeed || []).filter((m) => !clearedMessages.includes(m.id)),
      agents: (data.agents?.length ?? 0) > 0 ? transformAgents(data.agents) : getMockAgentProfiles(),
      learningStories: (data.learningStories?.length ?? 0) > 0
        ? transformLearningStories(data.learningStories)
        : MOCK_LEARNING_STORIES,
      activeWorkflow: transformWorkflow(data.activeWorkflow) ?? MOCK_ACTIVE_WORKFLOW,
      pendingDecisions: transformDecisions(data.pendingDecisions || []),
      error: data.success ? null : 'Erro ao carregar dados',
      lastEventAt: data.timestamp,
    };
  }, [data, isLoading, error, useMockData, clearedMessages]);

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
