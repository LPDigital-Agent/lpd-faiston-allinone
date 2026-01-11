/**
 * Agent Room Types - Sala de Transparência
 *
 * TypeScript interfaces for the Agent Room feature.
 * All types are user-friendly (not technical DevOps metrics).
 */

import type { LucideIcon } from "lucide-react";

// =============================================================================
// Agent Status Types
// =============================================================================

/**
 * User-friendly agent statuses (not technical states).
 * These map to internal technical states but are presented in human terms.
 */
export type AgentFriendlyStatus =
  | "disponivel" // idle - Agent is ready and waiting
  | "trabalhando" // processing - Agent is actively working
  | "esperando_voce" // pending_hil - Agent needs human input
  | "problema" // error - Agent encountered an issue
  | "descansando"; // inactive - Agent is not currently active

// =============================================================================
// Agent Profile Types
// =============================================================================

/**
 * Configuration for how an agent is displayed in the UI.
 */
export interface AgentProfileConfig {
  /** Human-friendly name shown to users */
  friendlyName: string;
  /** Short description of what this agent does */
  description: string;
  /** Lucide icon component */
  icon: LucideIcon;
  /** Theme color for the agent's visual identity */
  color: "magenta" | "blue" | "cyan" | "green" | "purple" | "orange" | "yellow" | "red" | "zinc";
}

/**
 * Runtime agent profile with current status.
 */
export interface AgentProfile {
  /** Unique identifier (technical name) */
  id: string;
  /** Technical agent name (e.g., "NexoImportAgent") */
  technicalName: string;
  /** Human-friendly name (e.g., "NEXO") */
  friendlyName: string;
  /** Description of what the agent does */
  description: string;
  /** Lucide icon name for the avatar */
  avatar: string;
  /** Theme color for the agent's visual identity */
  color: "magenta" | "blue" | "cyan" | "green" | "purple" | "orange" | "yellow" | "red" | "zinc" | "slate" | "teal" | "indigo" | "pink" | "violet";
  /** Current status */
  status: AgentFriendlyStatus;
  /** Last activity in human-readable format (e.g., "Importei 47 itens há 5 min") */
  lastActivity?: string;
  /** When the last activity occurred */
  lastActivityAt?: string;
}

// =============================================================================
// Live Feed Types
// =============================================================================

/**
 * Message types for visual differentiation in the live feed.
 */
export type LiveMessageType = "info" | "success" | "warning" | "action_needed";

/**
 * A message in the live feed stream.
 * Messages are in first-person Portuguese, humanized language.
 */
export interface LiveMessage {
  /** Unique message identifier */
  id: string;
  /** When the message was created */
  timestamp: string;
  /** Human-friendly agent name (e.g., "NEXO") */
  agentName: string;
  /** Message content in natural language */
  message: string;
  /** Message type for styling */
  type: LiveMessageType;
  /** Related entity (optional link to asset, import, etc.) */
  relatedEntity?: {
    type: string;
    id: string;
    label: string;
  };
}

// =============================================================================
// Learning Stories Types
// =============================================================================

/**
 * Confidence level for a learning.
 */
export type LearningConfidence = "alta" | "media" | "baixa";

/**
 * A learning story - something an agent learned from interactions.
 * Presented in first-person: "Aprendi que..."
 */
export interface LearningStory {
  /** Unique identifier */
  id: string;
  /** When the learning was recorded */
  learnedAt: string;
  /** Human-friendly agent name */
  agentName: string;
  /** The learning story in natural language */
  story: string;
  /** How confident the agent is about this learning */
  confidence: LearningConfidence;
  /** Related context (e.g., file type, customer) */
  context?: string;
}

// =============================================================================
// Workflow Timeline Types
// =============================================================================

/**
 * Status of a workflow step.
 */
export type WorkflowStepStatus = "concluido" | "atual" | "pendente";

/**
 * A step in the current workflow timeline.
 */
export interface WorkflowStep {
  /** Step identifier */
  id: string;
  /** Human-readable label */
  label: string;
  /** Current status of this step */
  status: WorkflowStepStatus;
  /** Lucide icon name for this step */
  icon: string;
  /** Optional detail text */
  detail?: string;
}

/**
 * A complete workflow with its steps.
 */
export interface ActiveWorkflow {
  /** Workflow identifier */
  id: string;
  /** Workflow name (e.g., "Importação de NF") */
  name: string;
  /** Brief description */
  description?: string;
  /** Steps in this workflow */
  steps: WorkflowStep[];
  /** When the workflow started */
  startedAt: string;
  /** Agent currently executing */
  currentAgent?: string;
}

// =============================================================================
// Pending Decisions Types
// =============================================================================

/**
 * Priority level for a pending decision.
 */
export type DecisionPriority = "alta" | "normal";

/**
 * An action option for a pending decision.
 */
export interface DecisionOption {
  /** Button label */
  label: string;
  /** Action identifier to trigger */
  action: string;
  /** Optional variant for styling */
  variant?: "primary" | "secondary" | "destructive";
}

/**
 * A decision that requires human input (HIL task).
 * Presented in friendly, non-technical language.
 */
export interface PendingDecision {
  /** Unique identifier */
  id: string;
  /** HIL task ID (technical reference) */
  hilTaskId?: string;
  /** The question in natural language */
  question: string;
  /** Available action options */
  options: DecisionOption[];
  /** Priority level */
  priority: DecisionPriority;
  /** When the decision was created */
  createdAt: string;
  /** Which agent is asking */
  agentName: string;
  /** Additional context */
  context?: string;
}

// =============================================================================
// SSE Event Types
// =============================================================================

/**
 * Event types received from the SSE stream.
 */
export type AgentRoomEventType =
  | "agent_status" // Agent status changed
  | "live_message" // New message in feed
  | "learning" // New learning recorded
  | "workflow_update" // Workflow step changed
  | "decision_created" // New decision needed
  | "decision_resolved" // Decision was made
  | "heartbeat"; // Keep-alive

/**
 * Base SSE event structure.
 */
export interface AgentRoomEvent<T = unknown> {
  /** Event type */
  type: AgentRoomEventType;
  /** Event payload */
  data: T;
  /** Server timestamp */
  timestamp: string;
}

// =============================================================================
// API Response Types
// =============================================================================

/**
 * Response from get_agent_profiles action.
 */
export interface AgentProfilesResponse {
  agents: AgentProfile[];
  updatedAt: string;
}

/**
 * Response from get_learning_stories action.
 */
export interface LearningStoriesResponse {
  stories: LearningStory[];
  total: number;
}

/**
 * Response from get_current_workflow action.
 */
export interface CurrentWorkflowResponse {
  workflow: ActiveWorkflow | null;
  recentWorkflows?: ActiveWorkflow[];
}

/**
 * Response from get_pending_decisions action.
 */
export interface PendingDecisionsResponse {
  decisions: PendingDecision[];
  total: number;
}

// =============================================================================
// X-Ray Types (Real-time Agent Activity Traces)
// =============================================================================

/**
 * Event types for X-Ray classification.
 */
export type XRayEventType =
  | "agent_activity"   // Normal agent activity
  | "hil_decision"     // Human-in-the-loop decision point
  | "a2a_delegation"   // Agent-to-agent delegation
  | "error"            // Error occurred
  | "session_start"    // Session started
  | "session_end";     // Session ended

/**
 * Action types for X-Ray events.
 */
export type XRayEventAction =
  | "trabalhando"      // Agent is working
  | "delegando"        // Agent is delegating to another
  | "concluido"        // Task completed
  | "erro"             // Error occurred
  | "esperando"        // Waiting for something
  | "hil_pending"      // HIL decision pending
  | "hil_approved"     // HIL decision approved
  | "hil_rejected";    // HIL decision rejected

/**
 * A single event in the X-Ray trace timeline.
 * Represents one step in an agent's execution.
 */
export interface XRayEvent {
  /** Unique event identifier */
  id: string;
  /** ISO timestamp when this event occurred */
  timestamp: string;
  /** Event classification */
  type: XRayEventType;
  /** Agent that generated this event */
  agentId: string;
  /** Human-friendly agent name */
  agentName: string;
  /** What action is being taken */
  action: XRayEventAction;
  /** Human-readable message describing what's happening */
  message: string;

  // Session tracking
  /** Session ID for grouping related events */
  sessionId?: string;
  /** Human-readable session name (e.g., "Importação NF #12345") */
  sessionName?: string;

  // A2A delegation
  /** Target agent ID when delegating */
  targetAgent?: string;
  /** Target agent friendly name */
  targetAgentName?: string;

  // Performance metrics
  /** Duration since previous event in this session (milliseconds) */
  duration?: number;
  /** API latency if available (milliseconds) */
  latency?: number;

  // Expandable details
  /** Full event payload for inspection */
  details?: Record<string, unknown>;

  // HIL specific fields
  /** HIL task ID for actions */
  hilTaskId?: string;
  /** Current HIL status */
  hilStatus?: "pending" | "approved" | "rejected";
  /** HIL question text */
  hilQuestion?: string;
  /** Available HIL options */
  hilOptions?: Array<{ label: string; value: string }>;
}

/**
 * A session groups related X-Ray events together.
 * Represents one complete workflow execution.
 */
export interface XRaySession {
  /** Session identifier */
  sessionId: string;
  /** Human-readable session name */
  sessionName: string;
  /** When this session started */
  startTime: string;
  /** When this session ended (null if still active) */
  endTime?: string;
  /** Current session status */
  status: "active" | "completed" | "error";
  /** Events in this session (chronologically sorted) */
  events: XRayEvent[];
  /** Total duration of all events (milliseconds) */
  totalDuration?: number;
  /** Number of events in this session */
  eventCount: number;
}

/**
 * Filter options for X-Ray events.
 */
export interface XRayFilter {
  /** Filter by specific agent */
  agentId?: string;
  /** Filter by specific session */
  sessionId?: string;
  /** Filter by event type */
  type?: XRayEventType;
  /** Show only HIL decisions */
  showHILOnly?: boolean;
}

/**
 * Connection status for SSE stream.
 */
export type XRayConnectionStatus =
  | "connected"
  | "connecting"
  | "reconnecting"
  | "disconnected"
  | "error";
