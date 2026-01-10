/**
 * useAgentRoomStream - SSE Connection for Agent Room
 *
 * Provides real-time streaming of agent events via Server-Sent Events.
 * Handles connection management, reconnection, and event parsing.
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { getAccessToken } from '@/services/authService';
import { AGENTCORE_ENDPOINT, SGA_AGENTCORE_ARN } from '@/lib/config/agentcore';
import type {
  LiveMessage,
  AgentProfile,
  LearningStory,
  ActiveWorkflow,
  PendingDecision,
  AgentRoomEvent,
  AgentRoomEventType,
} from '@/lib/ativos/agentRoomTypes';
import {
  MOCK_LIVE_MESSAGES,
  MOCK_LEARNING_STORIES,
  MOCK_PENDING_DECISIONS,
  MOCK_ACTIVE_WORKFLOW,
} from '@/lib/ativos/agentRoomConstants';

// =============================================================================
// Types
// =============================================================================

export interface AgentRoomStreamState {
  /** Whether SSE connection is active */
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
  /** Timestamp of last received event */
  lastEventAt: string | null;
}

export interface UseAgentRoomStreamOptions {
  /** Auto-connect on mount (default: true) */
  autoConnect?: boolean;
  /** Max messages to keep in memory (default: 100) */
  maxMessages?: number;
  /** Reconnection delay in ms (default: 5000) */
  reconnectDelay?: number;
  /** Use mock data instead of real SSE (default: false) */
  useMockData?: boolean;
}

export interface UseAgentRoomStreamReturn extends AgentRoomStreamState {
  /** Manually connect to SSE stream */
  connect: () => void;
  /** Disconnect from SSE stream */
  disconnect: () => void;
  /** Clear all messages */
  clearMessages: () => void;
  /** Pause/resume stream processing */
  isPaused: boolean;
  setPaused: (paused: boolean) => void;
}

// =============================================================================
// Initial State
// =============================================================================

const initialState: AgentRoomStreamState = {
  isConnected: false,
  messages: [],
  agents: [],
  learningStories: [],
  activeWorkflow: null,
  pendingDecisions: [],
  error: null,
  lastEventAt: null,
};

// =============================================================================
// Hook Implementation
// =============================================================================

export function useAgentRoomStream(
  options: UseAgentRoomStreamOptions = {}
): UseAgentRoomStreamReturn {
  const {
    autoConnect = true,
    maxMessages = 100,
    reconnectDelay = 5000,
    useMockData = true, // Default to mock while backend is being developed
  } = options;

  const [state, setState] = useState<AgentRoomStreamState>(initialState);
  const [isPaused, setPaused] = useState(false);

  const eventSourceRef = useRef<EventSource | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);

  // =============================================================================
  // Event Handlers
  // =============================================================================

  const handleEvent = useCallback((event: AgentRoomEvent) => {
    if (isPaused) return;

    setState((prev) => {
      switch (event.type) {
        case 'live_message': {
          const message = event.data as LiveMessage;
          const messages = [message, ...prev.messages].slice(0, maxMessages);
          return { ...prev, messages, lastEventAt: event.timestamp };
        }

        case 'agent_status': {
          const update = event.data as { agentId: string; status: string; lastActivity?: string };
          const agents = prev.agents.map((agent) =>
            agent.id === update.agentId
              ? { ...agent, status: update.status as AgentProfile['status'], lastActivity: update.lastActivity }
              : agent
          );
          return { ...prev, agents, lastEventAt: event.timestamp };
        }

        case 'learning': {
          const story = event.data as LearningStory;
          const learningStories = [story, ...prev.learningStories].slice(0, 20);
          return { ...prev, learningStories, lastEventAt: event.timestamp };
        }

        case 'workflow_update': {
          const workflow = event.data as ActiveWorkflow;
          return { ...prev, activeWorkflow: workflow, lastEventAt: event.timestamp };
        }

        case 'decision_created': {
          const decision = event.data as PendingDecision;
          const pendingDecisions = [decision, ...prev.pendingDecisions];
          return { ...prev, pendingDecisions, lastEventAt: event.timestamp };
        }

        case 'decision_resolved': {
          const { decisionId } = event.data as { decisionId: string };
          const pendingDecisions = prev.pendingDecisions.filter((d) => d.id !== decisionId);
          return { ...prev, pendingDecisions, lastEventAt: event.timestamp };
        }

        case 'heartbeat':
          return { ...prev, lastEventAt: event.timestamp };

        default:
          return prev;
      }
    });
  }, [isPaused, maxMessages]);

  // =============================================================================
  // SSE Connection Management
  // =============================================================================

  const connect = useCallback(async () => {
    // If using mock data, load mock data instead of connecting
    if (useMockData) {
      setState((prev) => ({
        ...prev,
        isConnected: true,
        messages: MOCK_LIVE_MESSAGES,
        learningStories: MOCK_LEARNING_STORIES,
        pendingDecisions: MOCK_PENDING_DECISIONS,
        activeWorkflow: MOCK_ACTIVE_WORKFLOW,
        error: null,
      }));
      return;
    }

    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const token = await getAccessToken();
      if (!token) {
        setState((prev) => ({ ...prev, error: 'Não autenticado' }));
        return;
      }

      // Build SSE URL with auth
      const encodedArn = encodeURIComponent(SGA_AGENTCORE_ARN);
      const url = `${AGENTCORE_ENDPOINT}/runtimes/${encodedArn}/stream?action=agent_room_stream`;

      // Note: EventSource doesn't support custom headers directly
      // We'll need to use fetch with ReadableStream for SSE with auth
      // For now, this is a placeholder that will be updated when backend is ready

      const eventSource = new EventSource(url);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        if (isMountedRef.current) {
          setState((prev) => ({ ...prev, isConnected: true, error: null }));
        }
      };

      eventSource.onmessage = (event) => {
        try {
          const parsed = JSON.parse(event.data) as AgentRoomEvent;
          handleEvent(parsed);
        } catch {
          console.warn('[Agent Room] Failed to parse SSE event:', event.data);
        }
      };

      eventSource.onerror = () => {
        if (isMountedRef.current) {
          setState((prev) => ({
            ...prev,
            isConnected: false,
            error: 'Conexão perdida. Reconectando...',
          }));

          // Schedule reconnection
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
          }
          reconnectTimeoutRef.current = setTimeout(() => {
            if (isMountedRef.current) {
              connect();
            }
          }, reconnectDelay);
        }
      };
    } catch (error) {
      console.error('[Agent Room] Connection error:', error);
      setState((prev) => ({
        ...prev,
        isConnected: false,
        error: 'Erro ao conectar',
      }));
    }
  }, [useMockData, handleEvent, reconnectDelay]);

  const disconnect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    setState((prev) => ({ ...prev, isConnected: false }));
  }, []);

  const clearMessages = useCallback(() => {
    setState((prev) => ({ ...prev, messages: [] }));
  }, []);

  // =============================================================================
  // Lifecycle
  // =============================================================================

  useEffect(() => {
    isMountedRef.current = true;

    if (autoConnect) {
      connect();
    }

    return () => {
      isMountedRef.current = false;
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  // =============================================================================
  // Return
  // =============================================================================

  return {
    ...state,
    connect,
    disconnect,
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
  const { messages, isConnected, error, isPaused, setPaused, clearMessages } =
    useAgentRoomStream(options);
  return { messages, isConnected, error, isPaused, setPaused, clearMessages };
}

/**
 * Hook for agent profiles with status.
 */
export function useAgentProfiles(options?: UseAgentRoomStreamOptions) {
  const { agents, isConnected, error } = useAgentRoomStream(options);
  return { agents, isConnected, error };
}

/**
 * Hook for learning stories.
 */
export function useLearningStories(options?: UseAgentRoomStreamOptions) {
  const { learningStories, isConnected, error } = useAgentRoomStream(options);
  return { stories: learningStories, isConnected, error };
}

/**
 * Hook for active workflow timeline.
 */
export function useWorkflowTimeline(options?: UseAgentRoomStreamOptions) {
  const { activeWorkflow, isConnected, error } = useAgentRoomStream(options);
  return { workflow: activeWorkflow, isConnected, error };
}

/**
 * Hook for pending decisions.
 */
export function usePendingDecisions(options?: UseAgentRoomStreamOptions) {
  const { pendingDecisions, isConnected, error } = useAgentRoomStream(options);
  return { decisions: pendingDecisions, isConnected, error };
}
