/**
 * useAgentRoomXRay - Real-time Agent Activity Traces
 *
 * Provides real-time agent activity events for the X-Ray panel in Agent Room.
 * Uses fast polling (1s interval) to simulate SSE-like real-time behavior.
 *
 * Features:
 * - Session grouping (events grouped by session_id)
 * - Event type classification (agent_activity, hil_decision, a2a_delegation, error)
 * - Duration calculations between events
 * - HIL integration inline
 * - Filters (by agent, session, HIL only)
 * - Automatic reconnection with exponential backoff
 */

'use client';

import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getXRayEvents,
  type XRayEventsResponse,
  type XRayEventBackend,
  type XRaySessionBackend,
} from '@/services/sgaAgentcore';
import type {
  XRayEvent,
  XRaySession,
  XRayFilter,
  XRayConnectionStatus,
} from '@/lib/ativos/agentRoomTypes';

// =============================================================================
// Types
// =============================================================================

export interface UseAgentRoomXRayOptions {
  /** Enable polling (default: true) */
  enabled?: boolean;
  /** Polling interval in ms (default: 1000 for real-time-like behavior) */
  refetchInterval?: number;
  /** Maximum events to keep in memory (default: 200) */
  maxEvents?: number;
  /** Initial filter */
  initialFilter?: XRayFilter;
}

export interface UseAgentRoomXRayReturn {
  /** All events (newest first) */
  events: XRayEvent[];
  /** Events grouped by session */
  sessions: XRaySession[];
  /** Events without session grouping */
  noSessionEvents: XRayEvent[];
  /** Filtered events based on current filter */
  filteredEvents: XRayEvent[];
  /** Current connection status */
  connectionStatus: XRayConnectionStatus;
  /** Whether data is loading */
  isLoading: boolean;
  /** Error message if any */
  error: string | null;
  /** Current filter */
  filter: XRayFilter;
  /** Update filter */
  setFilter: (filter: XRayFilter | ((prev: XRayFilter) => XRayFilter)) => void;
  /** Count of pending HIL decisions */
  hilPendingCount: number;
  /** Total events count */
  totalEvents: number;
  /** Last update timestamp */
  lastUpdatedAt: string | null;
  /** Manual refetch */
  refetch: () => void;
  /** Pause/resume polling */
  isPaused: boolean;
  setPaused: (paused: boolean) => void;
  /** Clear all events */
  clearEvents: () => void;
  /** Expand/collapse session */
  expandedSessions: Set<string>;
  toggleSessionExpanded: (sessionId: string) => void;
  /** Expand/collapse event details */
  expandedEvents: Set<string>;
  toggleEventExpanded: (eventId: string) => void;
}

// =============================================================================
// Data Transformation
// =============================================================================

/**
 * Transform backend event to frontend XRayEvent format.
 */
function transformEvent(event: XRayEventBackend): XRayEvent {
  return {
    id: event.id,
    timestamp: event.timestamp,
    type: event.type,
    agentId: event.agentId,
    agentName: event.agentName,
    action: event.action as XRayEvent['action'],
    message: event.message,
    sessionId: event.sessionId,
    sessionName: event.sessionName,
    targetAgent: event.targetAgent,
    targetAgentName: event.targetAgentName,
    duration: event.duration,
    details: event.details,
    hilTaskId: event.hilTaskId,
    hilStatus: event.hilStatus,
    hilQuestion: event.hilQuestion,
    hilOptions: event.hilOptions,
  };
}

/**
 * Transform backend session to frontend XRaySession format.
 */
function transformSession(session: XRaySessionBackend): XRaySession {
  return {
    sessionId: session.sessionId,
    sessionName: session.sessionName,
    startTime: session.startTime,
    endTime: session.endTime,
    status: session.status,
    events: session.events.map(transformEvent),
    totalDuration: session.totalDuration,
    eventCount: session.eventCount,
  };
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useAgentRoomXRay(
  options: UseAgentRoomXRayOptions = {}
): UseAgentRoomXRayReturn {
  const {
    enabled = true,
    refetchInterval = 1000, // 1 second for real-time-like behavior
    maxEvents = 200,
    initialFilter = {},
  } = options;

  const queryClient = useQueryClient();

  // State
  const [isPaused, setPaused] = useState(false);
  const [filter, setFilter] = useState<XRayFilter>(initialFilter);
  const [expandedSessions, setExpandedSessions] = useState<Set<string>>(new Set());
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());
  const [clearedEventIds, setClearedEventIds] = useState<Set<string>>(new Set());
  const [connectionStatus, setConnectionStatus] = useState<XRayConnectionStatus>('connecting');

  // Track last successful fetch for incremental updates
  const lastFetchTimestamp = useRef<string | null>(null);
  const reconnectAttempts = useRef(0);
  const MAX_RECONNECT_ATTEMPTS = 5;

  // =============================================================================
  // TanStack Query for Fast Polling
  // =============================================================================

  const {
    data,
    isLoading,
    error,
    refetch,
    dataUpdatedAt,
  } = useQuery({
    queryKey: ['xray-events', filter],
    queryFn: async (): Promise<XRayEventsResponse | null> => {
      try {
        const response = await getXRayEvents({
          // Use incremental updates for efficiency
          sinceTimestamp: lastFetchTimestamp.current ?? undefined,
          filterSessionId: filter.sessionId,
          filterAgentId: filter.agentId,
          showHILOnly: filter.showHILOnly,
          limit: maxEvents,
        });

        if (response.data?.success) {
          // Update timestamp for next incremental fetch
          lastFetchTimestamp.current = response.data.timestamp;
          reconnectAttempts.current = 0;
          setConnectionStatus('connected');
        }

        return response.data;
      } catch (err) {
        console.error('[X-Ray] Failed to fetch events:', err);

        // Handle reconnection
        if (reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          reconnectAttempts.current++;
          setConnectionStatus('reconnecting');
        } else {
          setConnectionStatus('error');
        }

        throw err;
      }
    },
    enabled: enabled && !isPaused,
    refetchInterval: isPaused ? false : refetchInterval,
    refetchIntervalInBackground: false,
    staleTime: refetchInterval / 2,
    retry: 3,
    retryDelay: (attemptIndex) => Math.min(1000 * Math.pow(2, attemptIndex), 5000),
    refetchOnWindowFocus: true,
    refetchOnReconnect: true,
  });

  // Update connection status based on loading state
  useEffect(() => {
    if (isLoading && connectionStatus !== 'reconnecting') {
      setConnectionStatus('connecting');
    }
  }, [isLoading, connectionStatus]);

  // =============================================================================
  // Memoized Transformations
  // =============================================================================

  const { events, sessions, noSessionEvents } = useMemo(() => {
    if (!data?.success) {
      return {
        events: [],
        sessions: [],
        noSessionEvents: [],
      };
    }

    // Filter out cleared events
    const allEvents = data.events
      .filter((e) => !clearedEventIds.has(e.id))
      .map(transformEvent);

    const allSessions = data.sessions.map(transformSession);

    const noSession = data.noSessionEvents
      .filter((e) => !clearedEventIds.has(e.id))
      .map(transformEvent);

    return {
      events: allEvents,
      sessions: allSessions,
      noSessionEvents: noSession,
    };
  }, [data, clearedEventIds]);

  // Apply client-side filters
  const filteredEvents = useMemo(() => {
    let filtered = events;

    if (filter.agentId) {
      filtered = filtered.filter((e) => e.agentId === filter.agentId);
    }

    if (filter.sessionId) {
      filtered = filtered.filter((e) => e.sessionId === filter.sessionId);
    }

    if (filter.type) {
      filtered = filtered.filter((e) => e.type === filter.type);
    }

    if (filter.showHILOnly) {
      filtered = filtered.filter((e) => e.type === 'hil_decision');
    }

    return filtered;
  }, [events, filter]);

  // =============================================================================
  // Actions
  // =============================================================================

  const clearEvents = useCallback(() => {
    const currentIds = events.map((e) => e.id);
    setClearedEventIds((prev) => new Set([...prev, ...currentIds]));
    lastFetchTimestamp.current = null; // Reset to fetch fresh data
  }, [events]);

  const toggleSessionExpanded = useCallback((sessionId: string) => {
    setExpandedSessions((prev) => {
      const next = new Set(prev);
      if (next.has(sessionId)) {
        next.delete(sessionId);
      } else {
        next.add(sessionId);
      }
      return next;
    });
  }, []);

  const toggleEventExpanded = useCallback((eventId: string) => {
    setExpandedEvents((prev) => {
      const next = new Set(prev);
      if (next.has(eventId)) {
        next.delete(eventId);
      } else {
        next.add(eventId);
      }
      return next;
    });
  }, []);

  const handleRefetch = useCallback(() => {
    lastFetchTimestamp.current = null; // Reset to fetch all events
    reconnectAttempts.current = 0;
    setConnectionStatus('connecting');
    refetch();
  }, [refetch]);

  // =============================================================================
  // Return
  // =============================================================================

  return {
    events,
    sessions,
    noSessionEvents,
    filteredEvents,
    connectionStatus,
    isLoading,
    error: error ? String(error) : null,
    filter,
    setFilter,
    hilPendingCount: data?.hilPendingCount ?? 0,
    totalEvents: data?.totalEvents ?? 0,
    lastUpdatedAt: data?.timestamp ?? null,
    refetch: handleRefetch,
    isPaused,
    setPaused,
    clearEvents,
    expandedSessions,
    toggleSessionExpanded,
    expandedEvents,
    toggleEventExpanded,
  };
}

// =============================================================================
// Specialized Hooks
// =============================================================================

/**
 * Hook for just HIL decisions in X-Ray.
 */
export function useXRayHILDecisions(options?: UseAgentRoomXRayOptions) {
  return useAgentRoomXRay({
    ...options,
    initialFilter: { showHILOnly: true },
  });
}

/**
 * Hook for a specific session's events.
 */
export function useXRaySession(sessionId: string, options?: UseAgentRoomXRayOptions) {
  return useAgentRoomXRay({
    ...options,
    initialFilter: { sessionId },
  });
}

/**
 * Hook for a specific agent's events.
 */
export function useXRayAgent(agentId: string, options?: UseAgentRoomXRayOptions) {
  return useAgentRoomXRay({
    ...options,
    initialFilter: { agentId },
  });
}
