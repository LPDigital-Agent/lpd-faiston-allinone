/**
 * useAgentRoomWebSocket - Real-time Agent Activity via WebSocket
 *
 * Provides TRUE real-time agent activity events via WebSocket connection.
 * Replaces polling-based useAgentRoomXRay for <100ms latency.
 *
 * Architecture:
 * DynamoDB Streams → EventBridge Pipe → Lambda → WebSocket → This Hook
 *
 * Features:
 * - TRUE real-time (<100ms latency vs 1000ms polling)
 * - Session grouping (events grouped by session_id)
 * - Event type classification (agent_activity, hil_decision, a2a_delegation, error)
 * - Automatic reconnection with exponential backoff
 * - Latency tracking for UI display
 *
 * Compatible with useAgentRoomXRay interface for easy swap.
 */

'use client';

import { useState, useCallback, useMemo, useEffect, useRef } from 'react';
import type {
  XRayEvent,
  XRaySession,
  XRayFilter,
  XRayConnectionStatus,
} from '@/lib/ativos/agentRoomTypes';

// =============================================================================
// Configuration
// =============================================================================

const WS_URL = process.env.NEXT_PUBLIC_AGENTROOM_WS_URL || '';
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_BASE_DELAY = 1000; // 1 second
const RECONNECT_MAX_DELAY = 10000; // 10 seconds

// =============================================================================
// Types
// =============================================================================

export interface UseAgentRoomWebSocketOptions {
  /** User ID for connection tracking */
  userId?: string;
  /** Maximum events to keep in memory (default: 200) */
  maxEvents?: number;
  /** Enable auto-reconnect (default: true) */
  autoReconnect?: boolean;
  /** Initial filter */
  initialFilter?: XRayFilter;
  /** Enable connection (default: true) */
  enabled?: boolean;
}

export interface UseAgentRoomWebSocketReturn {
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
  /** Whether initially loading (for compatibility) */
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
  /** Manual reconnect */
  refetch: () => void;
  /** Pause/resume connection */
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
  /** Real-time latency in ms (WebSocket-specific) */
  latency: number | null;
}

// =============================================================================
// WebSocket Message Types
// =============================================================================

interface WebSocketMessage {
  type: 'agent_events';
  events: XRayEvent[];
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useAgentRoomWebSocket(
  options: UseAgentRoomWebSocketOptions = {}
): UseAgentRoomWebSocketReturn {
  const {
    userId = 'anonymous',
    maxEvents = 200,
    autoReconnect = true,
    initialFilter = {},
    enabled = true,
  } = options;

  // =============================================================================
  // State
  // =============================================================================

  const [events, setEvents] = useState<XRayEvent[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<XRayConnectionStatus>('connecting');
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<XRayFilter>(initialFilter);
  const [isPaused, setPaused] = useState(false);
  const [expandedSessions, setExpandedSessions] = useState<Set<string>>(new Set());
  const [expandedEvents, setExpandedEventsState] = useState<Set<string>>(new Set());
  const [latency, setLatency] = useState<number | null>(null);
  const [lastUpdatedAt, setLastUpdatedAt] = useState<string | null>(null);

  // =============================================================================
  // Refs
  // =============================================================================

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);

  // =============================================================================
  // WebSocket Connection
  // =============================================================================

  const connect = useCallback(() => {
    // Skip if no WebSocket URL configured or disabled
    if (!WS_URL || !enabled || isPaused) {
      console.log('[AgentRoom WS] Skipping connection (disabled or no URL)');
      return;
    }

    // Close existing connection
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }

    // Build connection URL with user ID
    const wsUrl = `${WS_URL}?user_id=${encodeURIComponent(userId)}`;

    console.log('[AgentRoom WS] Connecting...');
    setConnectionStatus('connecting');

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('[AgentRoom WS] Connected');
        setConnectionStatus('connected');
        setError(null);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data);

          if (data.type === 'agent_events' && Array.isArray(data.events)) {
            const receivedAt = Date.now();

            setEvents((prev) => {
              // Deduplicate by ID
              const newEvents = data.events.filter(
                (e) => !prev.some((existing) => existing.id === e.id)
              );

              if (newEvents.length === 0) {
                return prev;
              }

              // Calculate latency from most recent event
              const mostRecent = newEvents[0];
              if (mostRecent?.timestamp) {
                const eventTime = new Date(mostRecent.timestamp).getTime();
                const calculatedLatency = receivedAt - eventTime;
                setLatency(calculatedLatency > 0 ? calculatedLatency : 0);
              }

              // Update last updated timestamp
              setLastUpdatedAt(new Date().toISOString());

              // Prepend new events and limit total
              return [...newEvents, ...prev].slice(0, maxEvents);
            });
          }
        } catch (err) {
          console.error('[AgentRoom WS] Parse error:', err);
        }
      };

      ws.onclose = (event) => {
        console.log('[AgentRoom WS] Disconnected', event.code, event.reason);
        setConnectionStatus('error');

        // Auto-reconnect with exponential backoff
        if (autoReconnect && !isPaused && reconnectAttempts.current < MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(
            RECONNECT_BASE_DELAY * Math.pow(2, reconnectAttempts.current),
            RECONNECT_MAX_DELAY
          );

          console.log(`[AgentRoom WS] Reconnecting in ${delay}ms (attempt ${reconnectAttempts.current + 1}/${MAX_RECONNECT_ATTEMPTS})`);
          setConnectionStatus('reconnecting');

          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        } else if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
          setError('Conexão perdida. Clique em reconectar.');
        }
      };

      ws.onerror = (err) => {
        console.error('[AgentRoom WS] Connection error:', err);
      };
    } catch (err) {
      console.error('[AgentRoom WS] Failed to create WebSocket:', err);
      setConnectionStatus('error');
      setError('Falha ao conectar ao servidor de eventos.');
    }
  }, [userId, maxEvents, autoReconnect, enabled, isPaused]);

  const disconnect = useCallback(() => {
    // Clear reconnection timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    // Close WebSocket
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    setConnectionStatus('error');
  }, []);

  const reconnect = useCallback(() => {
    disconnect();
    reconnectAttempts.current = 0;
    setError(null);
    setTimeout(connect, 100);
  }, [connect, disconnect]);

  // =============================================================================
  // Lifecycle
  // =============================================================================

  // Auto-connect on mount, disconnect on unmount
  useEffect(() => {
    if (enabled && !isPaused) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [connect, disconnect, enabled, isPaused]);

  // Handle pause/resume
  useEffect(() => {
    if (isPaused) {
      disconnect();
    } else if (enabled) {
      connect();
    }
  }, [isPaused, enabled, connect, disconnect]);

  // =============================================================================
  // Session Grouping
  // =============================================================================

  const { sessions, noSessionEvents } = useMemo(() => {
    const sessionMap = new Map<string, XRayEvent[]>();
    const noSession: XRayEvent[] = [];

    events.forEach((event) => {
      if (event.sessionId) {
        const list = sessionMap.get(event.sessionId) || [];
        list.push(event);
        sessionMap.set(event.sessionId, list);
      } else {
        noSession.push(event);
      }
    });

    const result: XRaySession[] = [];

    sessionMap.forEach((sessionEvents, sid) => {
      const sorted = sessionEvents.sort(
        (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
      );
      const firstEvent = sorted[0];
      const lastEvent = sorted[sorted.length - 1];
      const totalDuration = sorted.reduce((sum, e) => sum + (e.duration || 0), 0);

      result.push({
        sessionId: sid,
        sessionName: firstEvent.sessionName || `Sessão ${sid.slice(0, 8)}`,
        startTime: firstEvent.timestamp,
        endTime: lastEvent.action === 'concluido' ? lastEvent.timestamp : undefined,
        status:
          lastEvent.action === 'erro'
            ? 'error'
            : lastEvent.action === 'concluido'
            ? 'completed'
            : 'active',
        events: sorted,
        totalDuration,
        eventCount: sorted.length,
      });
    });

    // Sort sessions by start time (newest first)
    result.sort((a, b) => new Date(b.startTime).getTime() - new Date(a.startTime).getTime());

    return { sessions: result, noSessionEvents: noSession };
  }, [events]);

  // =============================================================================
  // Filtering
  // =============================================================================

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
  // HIL Count
  // =============================================================================

  const hilPendingCount = useMemo(() => {
    return events.filter(
      (e) => e.type === 'hil_decision' && e.hilStatus === 'pending'
    ).length;
  }, [events]);

  // =============================================================================
  // Actions
  // =============================================================================

  const clearEvents = useCallback(() => {
    setEvents([]);
    setLatency(null);
    setLastUpdatedAt(null);
  }, []);

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
    setExpandedEventsState((prev) => {
      const next = new Set(prev);
      if (next.has(eventId)) {
        next.delete(eventId);
      } else {
        next.add(eventId);
      }
      return next;
    });
  }, []);

  // =============================================================================
  // Return
  // =============================================================================

  return {
    events,
    sessions,
    noSessionEvents,
    filteredEvents,
    connectionStatus,
    isLoading: connectionStatus === 'connecting',
    error,
    filter,
    setFilter,
    hilPendingCount,
    totalEvents: events.length,
    lastUpdatedAt,
    refetch: reconnect,
    isPaused,
    setPaused,
    clearEvents,
    expandedSessions,
    toggleSessionExpanded,
    expandedEvents,
    toggleEventExpanded,
    latency,
  };
}

// =============================================================================
// Specialized Hooks
// =============================================================================

/**
 * Hook for just HIL decisions via WebSocket.
 */
export function useWebSocketHILDecisions(options?: UseAgentRoomWebSocketOptions) {
  return useAgentRoomWebSocket({
    ...options,
    initialFilter: { showHILOnly: true },
  });
}

/**
 * Hook for a specific session's events via WebSocket.
 */
export function useWebSocketSession(sessionId: string, options?: UseAgentRoomWebSocketOptions) {
  return useAgentRoomWebSocket({
    ...options,
    initialFilter: { sessionId },
  });
}

/**
 * Hook for a specific agent's events via WebSocket.
 */
export function useWebSocketAgent(agentId: string, options?: UseAgentRoomWebSocketOptions) {
  return useAgentRoomWebSocket({
    ...options,
    initialFilter: { agentId },
  });
}
