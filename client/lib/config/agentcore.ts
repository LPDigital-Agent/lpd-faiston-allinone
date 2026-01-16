/**
 * @file agentcore.ts
 * @description Centralized configuration for AWS Bedrock AgentCore endpoints
 *
 * All AgentCore ARNs and endpoints are defined here to avoid hardcoding
 * values across multiple service files.
 *
 * Environment Variables (optional, for overrides):
 * - NEXT_PUBLIC_AGENTCORE_ENDPOINT: Base AgentCore endpoint
 * - NEXT_PUBLIC_ACADEMY_AGENTCORE_ARN: Academy agent ARN
 * - NEXT_PUBLIC_SGA_AGENTCORE_ARN: SGA Inventory agent ARN
 * - NEXT_PUBLIC_PORTAL_AGENTCORE_ARN: Portal agent ARN
 */

// =============================================================================
// AWS Account Configuration
// =============================================================================

/** AWS Account ID for Faiston One */
const AWS_ACCOUNT_ID = '377311924364';

/** AWS Region for AgentCore */
const AWS_REGION = 'us-east-2';

// =============================================================================
// AgentCore Endpoints
// =============================================================================

/**
 * Base AgentCore Runtime endpoint
 */
export const AGENTCORE_ENDPOINT =
  process.env.NEXT_PUBLIC_AGENTCORE_ENDPOINT ||
  `https://bedrock-agentcore.${AWS_REGION}.amazonaws.com`;

// =============================================================================
// Agent Runtime IDs
// =============================================================================

/**
 * Runtime IDs for each AgentCore agent.
 * These are assigned by AWS on first deployment and remain stable.
 *
 * IMPORTANT: SGA uses specialized runtimes for different functions:
 * - nexo_import: Smart Import orchestrator (file analysis, HIL dialogue)
 * - Other SGA agents: via A2A delegation from nexo_import
 *
 * REFACTOR-001 (2026-01-16):
 * - Renamed from faiston_asset_management to faiston_inventory_orchestration
 * - TODO: Update runtime ID after new deployment completes
 * - Old ID: faiston_asset_management-uSuLPsFQNH (to be deleted)
 */
const RUNTIME_IDS = {
  /** Faiston Academy - Learning platform agent */
  academy: 'faiston_academy_agents-ODNvP6HxCD',

  /** SGA Inventory - HTTP Orchestrator (routes to A2A agents) */
  // TODO: Update with new runtime ID after faiston_inventory_orchestration deployment
  sga: 'faiston_inventory_orchestration-PENDING_DEPLOYMENT',

  /** Portal - Central NEXO orchestrator agent */
  portal: 'faiston_portal_agents-PENDING', // TODO: Update after first deployment
} as const;

// =============================================================================
// Agent ARNs
// =============================================================================

/**
 * Build ARN for an AgentCore runtime
 */
function buildAgentCoreArn(runtimeId: string): string {
  return `arn:aws:bedrock-agentcore:${AWS_REGION}:${AWS_ACCOUNT_ID}:runtime/${runtimeId}`;
}

/**
 * Academy AgentCore ARN
 * Handles: NEXO AI Chat, Flashcards, MindMap, Audio/Video Class, Reflections
 */
export const ACADEMY_AGENTCORE_ARN =
  process.env.NEXT_PUBLIC_ACADEMY_AGENTCORE_ARN ||
  buildAgentCoreArn(RUNTIME_IDS.academy);

/**
 * SGA Inventory AgentCore ARN
 * Handles: Asset management, NF processing, Inventory counts, Expeditions
 */
export const SGA_AGENTCORE_ARN =
  process.env.NEXT_PUBLIC_SGA_AGENTCORE_ARN ||
  buildAgentCoreArn(RUNTIME_IDS.sga);

/**
 * Portal AgentCore ARN
 * Handles: Central NEXO orchestrator, News, A2A delegation
 */
export const PORTAL_AGENTCORE_ARN =
  process.env.NEXT_PUBLIC_PORTAL_AGENTCORE_ARN ||
  buildAgentCoreArn(RUNTIME_IDS.portal);

// =============================================================================
// Configuration Export
// =============================================================================

/**
 * Complete AgentCore configuration
 */
export const agentCoreConfig = {
  /** Base endpoint for all AgentCore requests */
  endpoint: AGENTCORE_ENDPOINT,

  /** AWS Region */
  region: AWS_REGION,

  /** AWS Account ID */
  accountId: AWS_ACCOUNT_ID,

  /** Agent ARNs */
  arns: {
    academy: ACADEMY_AGENTCORE_ARN,
    sga: SGA_AGENTCORE_ARN,
    portal: PORTAL_AGENTCORE_ARN,
  },

  /** Runtime IDs (for reference) */
  runtimeIds: RUNTIME_IDS,
} as const;

/**
 * Check if AgentCore is properly configured
 */
export function isAgentCoreConfigured(): boolean {
  return !!(
    AGENTCORE_ENDPOINT &&
    ACADEMY_AGENTCORE_ARN &&
    SGA_AGENTCORE_ARN
  );
}

/**
 * Get configuration status for debugging
 */
export function getAgentCoreStatus(): {
  configured: boolean;
  endpoint: string;
  academy: { arn: string; runtimeId: string };
  sga: { arn: string; runtimeId: string };
  portal: { arn: string; runtimeId: string };
} {
  return {
    configured: isAgentCoreConfigured(),
    endpoint: AGENTCORE_ENDPOINT,
    academy: { arn: ACADEMY_AGENTCORE_ARN, runtimeId: RUNTIME_IDS.academy },
    sga: { arn: SGA_AGENTCORE_ARN, runtimeId: RUNTIME_IDS.sga },
    portal: { arn: PORTAL_AGENTCORE_ARN, runtimeId: RUNTIME_IDS.portal },
  };
}
