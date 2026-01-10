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
