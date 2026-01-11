// =============================================================================
// SGA AgentCore Service - Faiston NEXO Inventory Management
// =============================================================================
// Purpose: Invoke AWS Bedrock AgentCore Runtime for SGA (Sistema de Gestao de
// Ativos) Inventory module using JWT Bearer Token authentication.
//
// This service handles all AI features for inventory management:
// - Asset search and tracking
// - NF processing (intake)
// - Reservations and expeditions
// - Transfers and returns (reversa)
// - Inventory counting campaigns
// - HIL (Human-in-the-Loop) task management
// - Compliance validation
// - NEXO AI chat for inventory queries
//
// Configuration: See @/lib/config/agentcore.ts for ARN configuration
// =============================================================================

import { SGA_AGENTCORE_ARN } from '@/lib/config/agentcore';
import { SGA_STORAGE_KEYS } from '@/lib/ativos/constants';
import {
  createAgentCoreService,
  type AgentCoreRequest,
  type AgentCoreResponse,
  type InvokeOptions,
} from './agentcoreBase';
import type {
  SmartImportUploadRequest,
  SmartImportUploadResponse,
  SmartImportPreview,
} from '@/lib/ativos/smartImportTypes';
import type {
  NexoObservation,
  GenerateObservationsRequest,
} from '@/lib/ativos/nexoObservationTypes';
import type {
  SGASearchAssetsRequest,
  SGASearchAssetsResponse,
  SGAGetBalanceRequest,
  SGAGetBalanceResponse,
  SGAWhereIsSerialRequest,
  SGAWhereIsSerialResponse,
  SGAProcessNFUploadRequest,
  SGAProcessNFUploadResponse,
  SGAConfirmNFEntryRequest,
  SGAConfirmNFEntryResponse,
  SGAGetUploadUrlRequest,
  SGAGetUploadUrlResponse,
  SGACreateReservationRequest,
  SGACreateReservationResponse,
  SGACancelReservationRequest,
  SGAProcessExpeditionRequest,
  SGAProcessExpeditionResponse,
  SGACreateTransferRequest,
  SGACreateTransferResponse,
  SGAProcessReturnRequest,
  SGAProcessReturnResponse,
  SGAGetPendingTasksRequest,
  SGAGetPendingTasksResponse,
  SGAApproveTaskRequest,
  SGAApproveTaskResponse,
  SGARejectTaskRequest,
  SGARejectTaskResponse,
  SGAStartCampaignRequest,
  SGAStartCampaignResponse,
  SGASubmitCountRequest,
  SGASubmitCountResponse,
  SGAAnalyzeDivergencesResponse,
  SGAProposeAdjustmentRequest,
  SGAProposeAdjustmentResponse,
  SGAValidateOperationRequest,
  SGAValidateOperationResponse,
  SGANexoChatRequest,
  SGANexoChatResponse,
  SGADashboardSummary,
  SGAPartNumber,
  SGALocation,
  SGAProject,
  InventoryCampaign,
  PendingNFEntry,
  SGAImportPreviewResponse,
  SGAImportExecuteResponse,
  SGAPNMappingValidationResponse,
  SGAGetAccuracyMetricsRequest,
  SGAGetAccuracyMetricsResponse,
  SGAReconcileSAPRequest,
  SGAReconcileSAPResponse,
  SGAApplyReconciliationActionRequest,
  SGAApplyReconciliationActionResponse,
  SGAExpeditionRequestPayload,
  SGAExpeditionResponse,
  SGAVerifyStockResponse,
  SGAConfirmSeparationPayload,
  SGAConfirmSeparationResponse,
  SGACompleteExpeditionPayload,
  SGACompleteExpeditionResponse,
  SGAGetQuotesRequest,
  SGAGetQuotesResponse,
  SGARecommendCarrierRequest,
  SGARecommendCarrierResponse,
  SGATrackShipmentRequest,
  SGATrackShipmentResponse,
  SGAProcessReturnRequestNew,
  SGAProcessReturnResponseNew,
  SGAValidateOriginRequest,
  SGAValidateOriginResponse,
  SGAEvaluateConditionRequest,
  SGAEvaluateConditionResponse,
} from '@/lib/ativos/types';

// =============================================================================
// Service Instance
// =============================================================================

const sgaService = createAgentCoreService({
  arn: SGA_AGENTCORE_ARN,
  sessionStorageKey: SGA_STORAGE_KEYS.AGENTCORE_SESSION,
  logPrefix: '[SGA AgentCore]',
  sessionPrefix: 'sga-session',
});

// =============================================================================
// Re-export Types
// =============================================================================

export type { AgentCoreRequest, AgentCoreResponse, InvokeOptions };

// =============================================================================
// Core Functions (delegated to base service)
// =============================================================================

export const invokeSGAAgentCore = sgaService.invoke;
export const getSGASessionId = sgaService.getSessionId;
export const clearSGASession = sgaService.clearSession;
export const getSGAAgentCoreConfig = sgaService.getConfig;

// =============================================================================
// Debug & Diagnostics
// =============================================================================

/**
 * Debug action to verify deployed code version.
 * Returns git commit SHA and deployment timestamp.
 * Use this to diagnose stale code issues.
 */
export async function debugVersion(): Promise<AgentCoreResponse<{
  success: boolean;
  code_marker: string;
  git_commit: string;
  deployed_at: string;
  action_received: string;
  has_get_nf_upload_url: boolean;
}>> {
  return invokeSGAAgentCore({
    action: 'debug_version',
  });
}

// =============================================================================
// Asset Queries
// =============================================================================

/**
 * Search assets with filters and pagination.
 */
export async function searchAssets(
  params: SGASearchAssetsRequest
): Promise<AgentCoreResponse<SGASearchAssetsResponse>> {
  return invokeSGAAgentCore<SGASearchAssetsResponse>({
    action: 'search_assets',
    ...params,
  });
}

/**
 * Get balance for a part number, optionally filtered by location/project.
 */
export async function getBalance(
  params: SGAGetBalanceRequest
): Promise<AgentCoreResponse<SGAGetBalanceResponse>> {
  return invokeSGAAgentCore<SGAGetBalanceResponse>({
    action: 'get_balance',
    ...params,
  });
}

/**
 * Find an asset by serial number with full timeline.
 */
export async function whereIsSerial(
  params: SGAWhereIsSerialRequest
): Promise<AgentCoreResponse<SGAWhereIsSerialResponse>> {
  return invokeSGAAgentCore<SGAWhereIsSerialResponse>({
    action: 'where_is_serial',
    ...params,
  });
}

// =============================================================================
// NF Processing (Intake)
// =============================================================================

/**
 * Process NF upload (XML or PDF) and extract items.
 */
export async function processNFUpload(
  params: SGAProcessNFUploadRequest
): Promise<AgentCoreResponse<SGAProcessNFUploadResponse>> {
  return invokeSGAAgentCore<SGAProcessNFUploadResponse>({
    action: 'process_nf_upload',
    ...params,
  });
}

/**
 * Confirm NF entry with item mappings.
 */
export async function confirmNFEntry(
  params: SGAConfirmNFEntryRequest
): Promise<AgentCoreResponse<SGAConfirmNFEntryResponse>> {
  return invokeSGAAgentCore<SGAConfirmNFEntryResponse>({
    action: 'confirm_nf_entry',
    ...params,
  });
}

/**
 * Get presigned URL for NF upload.
 */
export async function getNFUploadUrl(
  params: SGAGetUploadUrlRequest
): Promise<AgentCoreResponse<SGAGetUploadUrlResponse>> {
  return invokeSGAAgentCore<SGAGetUploadUrlResponse>({
    action: 'get_nf_upload_url',
    ...params,
  });
}

/**
 * Get pending NF entries awaiting confirmation.
 */
export async function getPendingNFEntries(): Promise<AgentCoreResponse<{ entries: PendingNFEntry[] }>> {
  return invokeSGAAgentCore<{ entries: PendingNFEntry[] }>({
    action: 'get_pending_nf_entries',
  });
}

/**
 * Assign a project to an entry that is in PENDING_PROJECT status.
 * This resolves the project gate workflow.
 */
export async function assignProjectToEntry(
  entryId: string,
  projectId: string
): Promise<AgentCoreResponse<{ success: boolean; entry_id: string; new_status: string }>> {
  return invokeSGAAgentCore<{ success: boolean; entry_id: string; new_status: string }>({
    action: 'assign_project_to_entry',
    entry_id: entryId,
    project_id: projectId,
  });
}

// =============================================================================
// Reservations
// =============================================================================

/**
 * Create a reservation for expedition.
 */
export async function createReservation(
  params: SGACreateReservationRequest
): Promise<AgentCoreResponse<SGACreateReservationResponse>> {
  return invokeSGAAgentCore<SGACreateReservationResponse>({
    action: 'create_reservation',
    ...params,
  });
}

/**
 * Cancel an active reservation.
 */
export async function cancelReservation(
  params: SGACancelReservationRequest
): Promise<AgentCoreResponse<{ success: boolean }>> {
  return invokeSGAAgentCore<{ success: boolean }>({
    action: 'cancel_reservation',
    ...params,
  });
}

// =============================================================================
// Expeditions
// =============================================================================

/**
 * Process an expedition (outbound shipment).
 */
export async function processExpedition(
  params: SGAProcessExpeditionRequest
): Promise<AgentCoreResponse<SGAProcessExpeditionResponse>> {
  return invokeSGAAgentCore<SGAProcessExpeditionResponse>({
    action: 'process_expedition',
    ...params,
  });
}

// =============================================================================
// Transfers
// =============================================================================

/**
 * Create a transfer between locations.
 */
export async function createTransfer(
  params: SGACreateTransferRequest
): Promise<AgentCoreResponse<SGACreateTransferResponse>> {
  return invokeSGAAgentCore<SGACreateTransferResponse>({
    action: 'create_transfer',
    ...params,
  });
}

// =============================================================================
// Returns (Reversa)
// =============================================================================

/**
 * Process a return (reversa) from customer.
 */
export async function processReturn(
  params: SGAProcessReturnRequest
): Promise<AgentCoreResponse<SGAProcessReturnResponse>> {
  return invokeSGAAgentCore<SGAProcessReturnResponse>({
    action: 'process_return',
    ...params,
  });
}

/**
 * Get pending reversals (items with customer awaiting return).
 */
export async function getPendingReversals(): Promise<AgentCoreResponse<{ count: number; items: unknown[] }>> {
  return invokeSGAAgentCore<{ count: number; items: unknown[] }>({
    action: 'pending_reversals',
  });
}

// =============================================================================
// HIL (Human-in-the-Loop) Tasks
// =============================================================================

/**
 * Get pending tasks for the current user.
 */
export async function getPendingTasks(
  params?: SGAGetPendingTasksRequest
): Promise<AgentCoreResponse<SGAGetPendingTasksResponse>> {
  return invokeSGAAgentCore<SGAGetPendingTasksResponse>({
    action: 'get_pending_tasks',
    ...params,
  });
}

/**
 * Approve a HIL task.
 */
export async function approveTask(
  params: SGAApproveTaskRequest
): Promise<AgentCoreResponse<SGAApproveTaskResponse>> {
  return invokeSGAAgentCore<SGAApproveTaskResponse>({
    action: 'approve_task',
    ...params,
  });
}

/**
 * Reject a HIL task.
 */
export async function rejectTask(
  params: SGARejectTaskRequest
): Promise<AgentCoreResponse<SGARejectTaskResponse>> {
  return invokeSGAAgentCore<SGARejectTaskResponse>({
    action: 'reject_task',
    ...params,
  });
}

// =============================================================================
// Inventory Counting
// =============================================================================

/**
 * Start a new inventory counting campaign.
 */
export async function startCampaign(
  params: SGAStartCampaignRequest
): Promise<AgentCoreResponse<SGAStartCampaignResponse>> {
  return invokeSGAAgentCore<SGAStartCampaignResponse>({
    action: 'start_inventory_count',
    ...params,
  });
}

/**
 * Submit a count result for an item.
 */
export async function submitCount(
  params: SGASubmitCountRequest
): Promise<AgentCoreResponse<SGASubmitCountResponse>> {
  return invokeSGAAgentCore<SGASubmitCountResponse>({
    action: 'submit_count_result',
    ...params,
  });
}

/**
 * Analyze divergences for a campaign.
 */
export async function analyzeDivergences(
  campaignId: string
): Promise<AgentCoreResponse<SGAAnalyzeDivergencesResponse>> {
  return invokeSGAAgentCore<SGAAnalyzeDivergencesResponse>({
    action: 'analyze_divergences',
    campaign_id: campaignId,
  });
}

/**
 * Propose adjustment for a divergence.
 */
export async function proposeAdjustment(
  params: SGAProposeAdjustmentRequest
): Promise<AgentCoreResponse<SGAProposeAdjustmentResponse>> {
  return invokeSGAAgentCore<SGAProposeAdjustmentResponse>({
    action: 'propose_adjustment',
    ...params,
  });
}

/**
 * Get active inventory campaigns.
 */
export async function getActiveCampaigns(): Promise<AgentCoreResponse<{ campaigns: InventoryCampaign[] }>> {
  return invokeSGAAgentCore<{ campaigns: InventoryCampaign[] }>({
    action: 'get_active_campaigns',
  });
}

// =============================================================================
// Compliance
// =============================================================================

/**
 * Validate an operation against compliance rules.
 */
export async function validateOperation(
  params: SGAValidateOperationRequest
): Promise<AgentCoreResponse<SGAValidateOperationResponse>> {
  return invokeSGAAgentCore<SGAValidateOperationResponse>({
    action: 'validate_operation',
    ...params,
  });
}

// =============================================================================
// NEXO AI Chat (Inventory Assistant)
// =============================================================================

/**
 * Chat with NEXO about inventory queries.
 */
export async function nexoEstoqueChat(
  params: SGANexoChatRequest
): Promise<AgentCoreResponse<SGANexoChatResponse>> {
  return invokeSGAAgentCore<SGANexoChatResponse>({
    action: 'chat',
    question: params.question,
    context: params.context || {},
    conversation_history: params.conversation_history || [],
  });
}

// =============================================================================
// Dashboard & Reporting
// =============================================================================

/**
 * Get dashboard summary metrics.
 */
export async function getDashboardSummary(): Promise<AgentCoreResponse<SGADashboardSummary>> {
  return invokeSGAAgentCore<SGADashboardSummary>({
    action: 'get_dashboard_summary',
  });
}

// =============================================================================
// Master Data
// =============================================================================

/**
 * Get all part numbers.
 */
export async function getPartNumbers(): Promise<AgentCoreResponse<{ part_numbers: SGAPartNumber[] }>> {
  return invokeSGAAgentCore<{ part_numbers: SGAPartNumber[] }>({
    action: 'get_part_numbers',
  });
}

/**
 * Get all locations.
 */
export async function getLocations(): Promise<AgentCoreResponse<{ locations: SGALocation[] }>> {
  return invokeSGAAgentCore<{ locations: SGALocation[] }>({
    action: 'get_locations',
  });
}

/**
 * Get all projects.
 */
export async function getProjects(): Promise<AgentCoreResponse<{ projects: SGAProject[] }>> {
  return invokeSGAAgentCore<{ projects: SGAProject[] }>({
    action: 'get_projects',
  });
}

/**
 * Create a new part number (requires HIL approval).
 */
export async function createPartNumber(
  params: Omit<SGAPartNumber, 'id' | 'created_at' | 'updated_at' | 'created_by'>
): Promise<AgentCoreResponse<{ part_number?: SGAPartNumber; hil_task_id?: string }>> {
  return invokeSGAAgentCore<{ part_number?: SGAPartNumber; hil_task_id?: string }>({
    action: 'create_part_number',
    ...params,
  });
}

/**
 * Create a new location.
 */
export async function createLocation(
  params: Omit<SGALocation, 'id' | 'created_at' | 'updated_at'>
): Promise<AgentCoreResponse<{ location: SGALocation }>> {
  return invokeSGAAgentCore<{ location: SGALocation }>({
    action: 'create_location',
    ...params,
  });
}

/**
 * Create a new project.
 */
export async function createProject(
  params: Omit<SGAProject, 'id' | 'created_at' | 'updated_at'>
): Promise<AgentCoreResponse<{ project: SGAProject }>> {
  return invokeSGAAgentCore<{ project: SGAProject }>({
    action: 'create_project',
    ...params,
  });
}

// =============================================================================
// Evidence Upload
// =============================================================================

/**
 * Get presigned URL for evidence upload (photos, documents).
 */
export async function getEvidenceUploadUrl(
  filename: string,
  contentType: string
): Promise<AgentCoreResponse<SGAGetUploadUrlResponse>> {
  return invokeSGAAgentCore<SGAGetUploadUrlResponse>({
    action: 'get_evidence_upload_url',
    filename,
    content_type: contentType,
  });
}

// =============================================================================
// Bulk Import
// =============================================================================

/**
 * Preview an import file before processing.
 * Parses CSV/Excel, auto-detects columns, and attempts PN matching.
 */
export async function previewImport(params: {
  file_content_base64: string;
  filename: string;
  project_id?: string;
  destination_location_id?: string;
}): Promise<AgentCoreResponse<SGAImportPreviewResponse>> {
  return invokeSGAAgentCore<SGAImportPreviewResponse>({
    action: 'preview_import',
    ...params,
  });
}

/**
 * Execute the import after preview/confirmation.
 * Creates entry movements for all valid rows.
 *
 * For NEXO flow: use s3_key (file already uploaded during analysis)
 * For direct flow: use file_content_base64
 */
export async function executeImport(params: {
  import_id: string;
  file_content_base64?: string;  // Optional if s3_key provided
  s3_key?: string;               // NEXO flow: file already in S3
  filename: string;
  column_mappings: Array<{ file_column: string; target_field: string }>;
  pn_overrides?: Record<number, string>;
  project_id?: string;
  destination_location_id?: string;
}): Promise<AgentCoreResponse<SGAImportExecuteResponse>> {
  return invokeSGAAgentCore<SGAImportExecuteResponse>({
    action: 'execute_import',
    ...params,
  });
}

/**
 * Execute NEXO import: Insert into pending_entry_items (not movements).
 *
 * FIX (January 2026): NEXO Import was incorrectly using executeImport which
 * creates movements directly (requiring valid part_numbers). NEXO should
 * insert into pending_entry_items for operator review first.
 */
export async function executeNexoImport(params: {
  session_state: Record<string, unknown>;  // Full session state for STATELESS architecture
  s3_key: string;
  filename: string;
  column_mappings: Array<{ file_column: string; target_field: string }>;
  project_id?: string;
  destination_location_id?: string;
}): Promise<AgentCoreResponse<SGAImportExecuteResponse>> {
  return invokeSGAAgentCore<SGAImportExecuteResponse>({
    action: 'nexo_execute_import',
    ...params,
  });
}

/**
 * Validate a part number mapping suggestion.
 * Used by operator to confirm or override AI suggestions.
 */
export async function validatePNMapping(params: {
  description: string;
  suggested_pn_id?: string;
}): Promise<AgentCoreResponse<SGAPNMappingValidationResponse>> {
  return invokeSGAAgentCore<SGAPNMappingValidationResponse>({
    action: 'validate_pn_mapping',
    ...params,
  });
}

// =============================================================================
// Expedition (ExpeditionAgent - SAP-Ready)
// =============================================================================

/**
 * Process a new expedition request with SAP-ready data.
 */
export async function processExpeditionRequest(
  params: SGAExpeditionRequestPayload
): Promise<AgentCoreResponse<SGAExpeditionResponse>> {
  return invokeSGAAgentCore<SGAExpeditionResponse>({
    action: 'process_expedition_request',
    ...params,
  });
}

/**
 * Verify stock availability for an item.
 */
export async function verifyExpeditionStock(params: {
  pn_id: string;
  serial?: string;
  quantity: number;
}): Promise<AgentCoreResponse<SGAVerifyStockResponse>> {
  return invokeSGAAgentCore<SGAVerifyStockResponse>({
    action: 'verify_expedition_stock',
    ...params,
  });
}

/**
 * Confirm physical separation and packaging.
 */
export async function confirmSeparation(
  params: SGAConfirmSeparationPayload
): Promise<AgentCoreResponse<SGAConfirmSeparationResponse>> {
  return invokeSGAAgentCore<SGAConfirmSeparationResponse>({
    action: 'confirm_separation',
    ...params,
  });
}

/**
 * Complete expedition after NF emission.
 */
export async function completeExpedition(
  params: SGACompleteExpeditionPayload
): Promise<AgentCoreResponse<SGACompleteExpeditionResponse>> {
  return invokeSGAAgentCore<SGACompleteExpeditionResponse>({
    action: 'complete_expedition',
    ...params,
  });
}

// =============================================================================
// Carrier Quotes (CarrierAgent)
// =============================================================================

/**
 * Get shipping quotes from multiple carriers.
 */
export async function getShippingQuotes(
  params: SGAGetQuotesRequest
): Promise<AgentCoreResponse<SGAGetQuotesResponse>> {
  return invokeSGAAgentCore<SGAGetQuotesResponse>({
    action: 'get_shipping_quotes',
    ...params,
  });
}

/**
 * Get AI recommendation for best carrier.
 */
export async function recommendCarrier(
  params: SGARecommendCarrierRequest
): Promise<AgentCoreResponse<SGARecommendCarrierResponse>> {
  return invokeSGAAgentCore<SGARecommendCarrierResponse>({
    action: 'recommend_carrier',
    ...params,
  });
}

/**
 * Track a shipment by tracking code.
 */
export async function trackShipment(
  params: SGATrackShipmentRequest
): Promise<AgentCoreResponse<SGATrackShipmentResponse>> {
  return invokeSGAAgentCore<SGATrackShipmentResponse>({
    action: 'track_shipment',
    ...params,
  });
}

// =============================================================================
// Reverse Logistics (ReverseAgent)
// =============================================================================

/**
 * Process an equipment return (reversa).
 */
export async function processReturnNew(
  params: SGAProcessReturnRequestNew
): Promise<AgentCoreResponse<SGAProcessReturnResponseNew>> {
  return invokeSGAAgentCore<SGAProcessReturnResponseNew>({
    action: 'process_return',
    ...params,
  });
}

/**
 * Validate the origin of a return shipment.
 */
export async function validateReturnOrigin(
  params: SGAValidateOriginRequest
): Promise<AgentCoreResponse<SGAValidateOriginResponse>> {
  return invokeSGAAgentCore<SGAValidateOriginResponse>({
    action: 'validate_return_origin',
    ...params,
  });
}

/**
 * Evaluate equipment condition and determine destination depot.
 */
export async function evaluateReturnCondition(
  params: SGAEvaluateConditionRequest
): Promise<AgentCoreResponse<SGAEvaluateConditionResponse>> {
  return invokeSGAAgentCore<SGAEvaluateConditionResponse>({
    action: 'evaluate_return_condition',
    ...params,
  });
}

// =============================================================================
// Accuracy Metrics (Dashboard Analytics)
// =============================================================================

/**
 * Get accuracy metrics for the dashboard.
 * Returns extraction accuracy, entry success rate, HIL time, divergence rate.
 */
export async function getAccuracyMetrics(
  params: SGAGetAccuracyMetricsRequest = {}
): Promise<AgentCoreResponse<SGAGetAccuracyMetricsResponse>> {
  return invokeSGAAgentCore<SGAGetAccuracyMetricsResponse>({
    action: 'get_accuracy_metrics',
    ...params,
  });
}

// =============================================================================
// SAP Reconciliation
// =============================================================================

/**
 * Reconcile SAP export data with SGA inventory.
 * Compares quantities and identifies deltas (FALTA_SGA, SOBRA_SGA).
 */
export async function reconcileSAPExport(
  params: SGAReconcileSAPRequest
): Promise<AgentCoreResponse<SGAReconcileSAPResponse>> {
  return invokeSGAAgentCore<SGAReconcileSAPResponse>({
    action: 'reconcile_sap_export',
    ...params,
  });
}

/**
 * Apply an action to a reconciliation delta.
 * Actions: CREATE_ADJUSTMENT, IGNORE, INVESTIGATE.
 */
export async function applyReconciliationAction(
  params: SGAApplyReconciliationActionRequest
): Promise<AgentCoreResponse<SGAApplyReconciliationActionResponse>> {
  return invokeSGAAgentCore<SGAApplyReconciliationActionResponse>({
    action: 'apply_reconciliation_action',
    delta_id: params.delta_id,
    reconciliation_action: params.action,
    reason: params.reason,
  });
}

// =============================================================================
// Image OCR Processing
// =============================================================================

/**
 * Process an image (scanned NF, mobile photo) with OCR via Gemini Vision.
 * Returns extracted data similar to NF processing.
 */
export async function processImageOCR(params: {
  s3_key: string;
  project_id?: string;
  destination_location_id: string;
}): Promise<AgentCoreResponse<SGAProcessNFUploadResponse>> {
  return invokeSGAAgentCore<SGAProcessNFUploadResponse>({
    action: 'process_image_ocr',
    s3_key: params.s3_key,
    project_id: params.project_id,
    destination_location_id: params.destination_location_id,
    file_type: 'image',
  });
}

// =============================================================================
// SAP Import (Full Asset Creation)
// =============================================================================

export interface SAPImportPreviewRequest {
  file_content: string;
  filename: string;
  project_id?: string;
  destination_location_id?: string;
  full_asset_creation?: boolean;
}

export interface SAPImportPreviewResponse {
  import_id: string;
  filename: string;
  file_type: 'csv' | 'xlsx';
  total_rows: number;
  matched_rows: number;
  unmatched_rows: number;
  match_rate: number;
  is_sap_format: boolean;
  columns_detected: string[];
  column_mappings: Array<{
    file_column: string;
    sap_field: string;
    target_field: string;
    confidence: number;
    is_required: boolean;
    sample_values: string[];
  }>;
  sample_data: Array<{
    row_number: number;
    part_number: string;
    part_number_id?: string;
    description: string;
    serial_number?: string;
    rfid?: string;
    quantity: number;
    status?: string;
    project_id?: string;
    project_name?: string;
    location_code?: string;
    technician_name?: string;
    match_confidence: number;
    is_matched: boolean;
    warnings: string[];
  }>;
  projects_detected: string[];
  locations_detected: string[];
  assets_to_create: number;
  warnings: string[];
}

export interface SAPImportExecuteRequest {
  import_id: string;
  pn_overrides?: Record<number, string>;
  full_asset_creation?: boolean;
}

export interface SAPImportExecuteResponse {
  success: boolean;
  import_id: string;
  assets_created: number;
  movements_created: number;
  errors: string[];
  warnings: string[];
}

/**
 * Preview a SAP export file (CSV/XLSX) before importing.
 * Detects SAP format columns and maps them to SGA fields.
 */
export async function previewSAPImport(
  params: SAPImportPreviewRequest
): Promise<AgentCoreResponse<SAPImportPreviewResponse>> {
  return invokeSGAAgentCore<SAPImportPreviewResponse>({
    action: 'preview_sap_import',
    ...params,
  });
}

/**
 * Execute SAP import with full asset creation.
 * Creates assets with serial numbers, RFID, technician data, etc.
 */
export async function executeSAPImport(
  params: SAPImportExecuteRequest
): Promise<AgentCoreResponse<SAPImportExecuteResponse>> {
  return invokeSGAAgentCore<SAPImportExecuteResponse>({
    action: 'execute_sap_import',
    ...params,
  });
}

// =============================================================================
// Manual Entry
// =============================================================================

export interface ManualEntryRequest {
  items: Array<{
    part_number_id: string;
    quantity: number;
    serial_numbers?: string[];
    unit_value?: number;
    notes?: string;
  }>;
  project_id?: string;
  destination_location_id: string;
  document_reference?: string;
  notes?: string;
}

export interface ManualEntryResponse {
  success: boolean;
  entry_id: string;
  movements_created: number;
  assets_created: number;
  total_quantity: number;
  errors: string[];
  warnings: string[];
}

/**
 * Create a manual entry without source file.
 * Useful for donations, adjustments, or entries from other sources.
 */
export async function createManualEntry(
  params: ManualEntryRequest
): Promise<AgentCoreResponse<ManualEntryResponse>> {
  return invokeSGAAgentCore<ManualEntryResponse>({
    action: 'create_manual_entry',
    ...params,
  });
}

// =============================================================================
// Smart Import (Universal File Importer)
// =============================================================================

/**
 * Smart import that auto-detects file type and routes to appropriate agent.
 *
 * Philosophy: Observe -> Think -> Learn -> Act
 * - OBSERVE: Downloads file from S3 and examines magic bytes
 * - THINK: Determines file type (XML, PDF, Image, CSV, XLSX, TXT)
 * - LEARN: Routes to appropriate agent based on type
 * - ACT: Returns preview with extraction results
 *
 * Supported file types:
 * - XML/PDF/Image -> IntakeAgent (NF processing)
 * - CSV/XLSX -> ImportAgent (spreadsheet processing)
 * - TXT -> ImportAgent (Gemini AI text interpretation)
 *
 * @param params.s3_key - S3 key of uploaded file
 * @param params.filename - Original filename with extension
 * @param params.content_type - Optional MIME type from upload
 * @param params.project_id - Optional project ID for entry
 * @param params.destination_location_id - Required destination location
 * @returns Preview with detected type and extraction results
 */
export async function invokeSmartImport(
  params: SmartImportUploadRequest
): Promise<AgentCoreResponse<SmartImportUploadResponse>> {
  return invokeSGAAgentCore<SmartImportUploadResponse>({
    action: 'smart_import_upload',
    s3_key: params.s3_key,
    filename: params.filename,
    content_type: params.content_type,
    project_id: params.project_id,
    destination_location_id: params.destination_location_id,
  });
}

// =============================================================================
// NEXO Intelligent Import (Agentic AI-First)
// =============================================================================
// ReAct Pattern: OBSERVE → THINK → ASK → LEARN → ACT
//
// Philosophy: NEXO guides user through import with intelligent analysis
// - Multi-sheet XLSX analysis with purpose detection
// - Clarification questions when uncertain
// - Learning from user answers for future imports
// - Explicit reasoning trace for transparency

/**
 * Request for NEXO intelligent file analysis.
 */
export interface NexoAnalyzeFileRequest {
  s3_key: string;
  filename: string;
  content_type?: string;
  prior_knowledge?: Record<string, unknown>;
}

/**
 * Sheet analysis result from NEXO.
 */
export interface NexoSheetAnalysis {
  name: string;
  purpose: 'items' | 'serials' | 'metadata' | 'summary' | 'config' | 'unknown';
  row_count: number;
  column_count: number;
  columns: Array<{
    name: string;
    sample_values: string[];
    detected_type: string;
    suggested_mapping: string | null;
    confidence: number;
  }>;
  confidence: number;
}

/**
 * Column mapping suggestion from NEXO.
 */
export interface NexoColumnMapping {
  file_column: string;
  target_field: string;
  confidence: number;
  reasoning: string;
  alternatives?: Array<{
    field: string;
    confidence: number;
  }>;
}

/**
 * Clarification question from NEXO.
 */
export interface NexoQuestion {
  id: string;
  question: string;
  context?: string;
  importance: 'critical' | 'high' | 'medium' | 'low';
  topic: 'column_mapping' | 'sheet_selection' | 'movement_type' | 'data_validation' | 'other';
  options: Array<{
    value: string;
    label: string;
    description?: string;
  }>;
  default_value?: string;
}

/**
 * Reasoning step in NEXO's thinking trace.
 */
export interface NexoReasoningStep {
  type: 'thought' | 'action' | 'observation';
  content: string;
  timestamp?: string;
  tool?: string;       // Tool used for action steps (e.g., 'sheet_analyzer', 'learning_agent')
  result?: string;     // Result from tool execution
}

/**
 * Response from NEXO file analysis.
 * STATELESS ARCHITECTURE: Returns full session state for frontend storage.
 */
export interface NexoAnalyzeFileResponse {
  success: boolean;
  error?: string;  // Error message when success is false
  import_session_id: string;
  filename: string;
  detected_file_type: string;
  analysis: {
    sheet_count: number;
    total_rows: number;
    sheets: NexoSheetAnalysis[];
    recommended_strategy: string;
  };
  column_mappings: NexoColumnMapping[];
  overall_confidence: number;
  questions: NexoQuestion[];
  reasoning_trace: NexoReasoningStep[];
  user_id?: string;
  session_id?: string;
  // STATELESS: Full session state returned for frontend storage
  session_state?: NexoSessionState;
}

/**
 * Response from getting questions.
 */
export interface NexoGetQuestionsResponse {
  success: boolean;
  import_session_id: string;
  questions: NexoQuestion[];
  questions_answered: number;
  questions_remaining: number;
  session?: NexoSessionState;  // STATELESS: Updated session state
}

/**
 * Request for getting questions (STATELESS architecture).
 */
export interface NexoGetQuestionsRequest {
  session_state: NexoSessionState;  // Full session state from frontend
}

/**
 * Request for preparing processing (STATELESS architecture).
 */
export interface NexoPrepareProcessingRequest {
  session_state: NexoSessionState;  // Full session state from frontend
}

/**
 * Full session state for stateless architecture.
 * Frontend maintains this state and passes it with each request.
 */
export interface NexoSessionState {
  session_id: string;
  filename: string;
  s3_key: string;
  stage: string;
  file_analysis?: Record<string, unknown>;
  reasoning_trace: Array<{ type: string; content: string; tool?: string; result?: string; timestamp?: string }>;
  questions: Array<{ id: string; question: string; context?: string; options: unknown[]; importance: string; topic: string; column?: string }>;
  answers: Record<string, string>;
  learned_mappings: Record<string, string>;
  column_mappings?: Record<string, string>;
  // FIX (January 2026): AI instructions from "Outros:" answers - MUST be preserved across rounds!
  ai_instructions?: Record<string, { column: string; instruction: string; question: string }>;
  // FEATURE (January 2026): Dynamic schema evolution - columns user wants to create
  requested_new_columns?: Array<{
    name: string;
    original_name: string;
    user_intent: string;
    inferred_type: string;
    sample_values: string[];
    source_file_column: string;
    approved: boolean;
  }>;
  // NOTE: confidence format MUST match Python ConfidenceScore dataclass
  confidence?: {
    overall: number;
    extraction_quality: number;
    evidence_strength: number;
    historical_match: number;
    risk_level: string;
    factors: string[];
    requires_hil: boolean;
  } | null;
  error?: string | null;
  // FIX (January 2026): Track user for audit trail in schema evolution
  user_id?: string;
  created_at: string;
  updated_at: string;
}

/**
 * Request for submitting answers (STATELESS architecture).
 */
export interface NexoSubmitAnswersRequest {
  session_state: NexoSessionState;  // Full session state from frontend
  answers: Record<string, string>;
  user_feedback?: string;  // FIX (January 2026): Global user instructions for AI interpretation
}

/**
 * Aggregation configuration for files without quantity column.
 * When enabled, rows with the same part_number are counted as quantity.
 */
export interface NexoAggregationConfig {
  enabled: boolean;
  strategy: 'count_rows' | 'use_one';
  part_number_column?: string;
  merge_strategy?: 'first' | 'last' | 'most_common';
  unique_parts?: number;
  total_rows?: number;
}

/**
 * Response after submitting answers.
 */
export interface NexoSubmitAnswersResponse {
  success: boolean;
  error?: string;  // Error type when success is false (e.g., "re_reasoning_failed")
  message?: string;  // Human-readable error message
  session: NexoSessionState;  // Updated session state
  applied_mappings: Record<string, string>;
  ready_for_processing: boolean;
  remaining_questions?: NexoQuestion[];  // If more questions remain (multi-round Q&A)
  // New fields from re-reasoning flow (January 2026)
  validation_errors?: string[];  // Schema pre-validation errors
  re_reasoning_applied?: boolean;  // Whether Gemini re-analyzed with user answers
  re_reasoning_error?: string;  // Detailed error message when re_reasoning_applied is false
  confidence?: {
    overall: number;
    extraction_quality: number;
    evidence_strength: number;
    historical_match: number;
    risk_level: string;
    factors: string[];
    requires_hil: boolean;
  };
  // Aggregation config (January 2026) - for files without quantity column
  aggregation?: NexoAggregationConfig | null;
  manual_override?: boolean;  // True if user chose to continue with manual mappings
}

/**
 * Request for learning from import (STATELESS architecture).
 */
export interface NexoLearnFromImportRequest {
  session_state: NexoSessionState;  // Full session state from frontend
  import_result: Record<string, unknown>;
  user_corrections?: Record<string, unknown>;
}

/**
 * Response after learning.
 */
export interface NexoLearnFromImportResponse {
  success: boolean;
  patterns_stored: number;
  message: string;
}

/**
 * Processing configuration from NEXO.
 */
export interface NexoProcessingConfig {
  success: boolean;
  import_session_id: string;
  ready: boolean;
  column_mappings: Array<{
    file_column: string;
    target_field: string;
  }>;
  selected_sheets: string[];
  movement_type: string;
  special_handling: Record<string, unknown>;
  final_confidence: number;
  // Error fields for schema validation failures (Phase 2 fix)
  error?: string;
  validation_errors?: string[];
  validation_warnings?: string[];
  suggestions?: string[];
  // FIX (January 2026): Import blocking when columns are missing
  import_blocked?: boolean;
  missing_columns?: Array<{
    name: string;
    type: string;
    source: string;
    user_intent?: string;
  }>;
  message?: string;
}

/**
 * NEXO intelligent file analysis (OBSERVE + THINK phases).
 *
 * Uses ReAct pattern to:
 * 1. OBSERVE: Analyze file structure (sheets, columns, rows)
 * 2. THINK: Reason about column mappings with Gemini AI
 * 3. Prepare questions for user when uncertain
 *
 * @param params.s3_key - S3 key of uploaded file
 * @param params.filename - Original filename
 * @param params.content_type - Optional MIME type
 * @param params.prior_knowledge - Optional context from previous imports
 * @returns Analysis with sheets, mappings, reasoning trace, and questions
 */
export async function nexoAnalyzeFile(
  params: NexoAnalyzeFileRequest
): Promise<AgentCoreResponse<NexoAnalyzeFileResponse>> {
  return invokeSGAAgentCore<NexoAnalyzeFileResponse>({
    action: 'nexo_analyze_file',
    s3_key: params.s3_key,
    filename: params.filename,
    content_type: params.content_type,
    prior_knowledge: params.prior_knowledge,
  });
}

/**
 * Get clarification questions for current import session (ASK phase).
 * STATELESS ARCHITECTURE: Receives full session state from frontend.
 *
 * Returns questions generated during analysis that require user input.
 *
 * @param params.session_state - Full session state from frontend
 * @returns List of questions with options and importance levels
 */
export async function nexoGetQuestions(
  params: NexoGetQuestionsRequest
): Promise<AgentCoreResponse<NexoGetQuestionsResponse>> {
  return invokeSGAAgentCore<NexoGetQuestionsResponse>({
    action: 'nexo_get_questions',
    session_state: params.session_state,  // STATELESS: Pass full state
  });
}

/**
 * Submit user answers to clarification questions (ASK → LEARN phases).
 * STATELESS ARCHITECTURE: Receives full session state from frontend.
 *
 * Processes user's answers and refines the analysis.
 * Stores answers for learning and future improvement.
 *
 * @param params.session_state - Full session state from frontend
 * @param params.answers - Dict mapping question IDs to selected answers
 * @returns Updated analysis with refined mappings and new session state
 */
export async function nexoSubmitAnswers(
  params: NexoSubmitAnswersRequest
): Promise<AgentCoreResponse<NexoSubmitAnswersResponse>> {
  return invokeSGAAgentCore<NexoSubmitAnswersResponse>({
    action: 'nexo_submit_answers',
    session_state: params.session_state,  // STATELESS: Pass full state
    answers: params.answers,
    // FIX (January 2026): Pass global user feedback for AI interpretation
    ...(params.user_feedback ? { user_feedback: params.user_feedback } : {}),
  });
}

/**
 * Store learned patterns from successful import (LEARN phase).
 * STATELESS ARCHITECTURE: Receives full session state from frontend.
 *
 * Called after import confirmation to build knowledge base.
 * Uses AgentCore Episodic Memory for cross-session learning.
 *
 * @param params.session_state - Full session state from frontend
 * @param params.import_result - Result of the executed import
 * @param params.user_corrections - Any manual corrections made by user
 * @returns Learning confirmation with patterns stored
 */
export async function nexoLearnFromImport(
  params: NexoLearnFromImportRequest
): Promise<AgentCoreResponse<NexoLearnFromImportResponse>> {
  return invokeSGAAgentCore<NexoLearnFromImportResponse>({
    action: 'nexo_learn_from_import',
    session_state: params.session_state,  // STATELESS: Pass full state
    import_result: params.import_result,
    user_corrections: params.user_corrections,
  });
}

/**
 * Prepare final processing after questions answered (ACT phase).
 * STATELESS ARCHITECTURE: Receives full session state from frontend.
 *
 * Generates the final processing configuration with:
 * - Confirmed column mappings
 * - Sheet selection
 * - Movement type
 * - Any special handling
 *
 * @param params.session_state - Full session state from frontend
 * @returns Processing configuration ready for execute_import
 */
export async function nexoPrepareProcessing(
  params: NexoPrepareProcessingRequest
): Promise<AgentCoreResponse<NexoProcessingConfig>> {
  return invokeSGAAgentCore<NexoProcessingConfig>({
    action: 'nexo_prepare_processing',
    session_state: params.session_state,  // STATELESS: Pass full state
  });
}

// =============================================================================
// NEXO Prior Knowledge & Adaptive Learning
// =============================================================================

/**
 * Request for getting prior knowledge before analysis.
 */
export interface NexoGetPriorKnowledgeRequest {
  filename: string;
  file_analysis?: {
    sheets?: Array<{ columns: string[] }>;
    detected_type?: string;
  };
}

/**
 * Prior knowledge from episodic memory.
 */
export interface NexoPriorKnowledge {
  similar_episodes: number;
  suggested_mappings: Record<string, string>;
  confidence_boost: boolean;
  reflections: string[];
  last_import_date?: string;
  success_rate?: number;
}

/**
 * Response from prior knowledge retrieval.
 */
export interface NexoGetPriorKnowledgeResponse {
  success: boolean;
  has_prior_knowledge: boolean;
  prior_knowledge: NexoPriorKnowledge;
  message: string;
}

/**
 * Request for adaptive threshold.
 */
export interface NexoGetAdaptiveThresholdRequest {
  filename: string;
  detected_type?: string;
}

/**
 * Response with adaptive confidence threshold.
 */
export interface NexoGetAdaptiveThresholdResponse {
  success: boolean;
  threshold: number;
  reason: string;
  based_on_episodes: number;
}

/**
 * Retrieve prior knowledge before analysis (RECALL phase).
 *
 * Queries AgentCore Episodic Memory for similar past imports.
 * Returns suggested mappings and confidence boosts based on history.
 *
 * @param params.filename - Filename being imported
 * @param params.file_analysis - Optional initial file analysis
 * @returns Prior knowledge with suggested mappings and reflections
 */
export async function nexoGetPriorKnowledge(
  params: NexoGetPriorKnowledgeRequest
): Promise<AgentCoreResponse<NexoGetPriorKnowledgeResponse>> {
  return invokeSGAAgentCore<NexoGetPriorKnowledgeResponse>({
    action: 'nexo_get_prior_knowledge',
    filename: params.filename,
    file_analysis: params.file_analysis,
  });
}

/**
 * Get adaptive confidence threshold based on historical success.
 *
 * Uses episodic memory reflections to determine optimal threshold:
 * - High success rate → Lower threshold (trust auto-mapping)
 * - High failure rate → Higher threshold (require confirmation)
 * - New pattern → Default threshold
 *
 * @param params.filename - Filename being imported
 * @param params.detected_type - Optional detected file type
 * @returns Adaptive threshold and reasoning
 */
export async function nexoGetAdaptiveThreshold(
  params: NexoGetAdaptiveThresholdRequest
): Promise<AgentCoreResponse<NexoGetAdaptiveThresholdResponse>> {
  return invokeSGAAgentCore<NexoGetAdaptiveThresholdResponse>({
    action: 'nexo_get_adaptive_threshold',
    filename: params.filename,
    detected_type: params.detected_type,
  });
}

// =============================================================================
// NEXO AI Observations
// =============================================================================

/**
 * Generate NEXO AI observations for import preview data.
 *
 * Called before user confirms import to display AI commentary
 * in the confirmation modal. NEXO analyzes the data following
 * the "Observe -> Learn -> Act" pattern.
 *
 * @param preview - Import preview data to analyze
 * @param context - Optional context (project_id, location_id, user_notes)
 * @returns NexoObservation with confidence, patterns, suggestions, and commentary
 */
export async function generateImportObservations(
  preview: SmartImportPreview,
  context?: GenerateObservationsRequest['context']
): Promise<AgentCoreResponse<NexoObservation>> {
  // Transform preview to request format
  const previewData: GenerateObservationsRequest['preview'] = {
    source_type: preview.source_type,
    items_count: 'items' in preview && Array.isArray(preview.items) ? preview.items.length : 0,
    total_value: 'total_value' in preview ? (preview as Record<string, unknown>).total_value as number | undefined : undefined,
    supplier_name: 'supplier' in preview && typeof preview.supplier === 'object' && preview.supplier !== null
      ? (preview.supplier as Record<string, unknown>).name as string | undefined
      : undefined,
    nf_number: 'nf_number' in preview ? (preview as Record<string, unknown>).nf_number as string | undefined : undefined,
    validation_warnings: 'warnings' in preview && Array.isArray((preview as Record<string, unknown>).warnings)
      ? (preview as Record<string, unknown>).warnings as string[]
      : [],
    hil_required: 'hil_required' in preview ? (preview as Record<string, unknown>).hil_required as boolean | undefined : undefined,
  };

  return invokeSGAAgentCore<NexoObservation>({
    action: 'generate_import_observations',
    preview: previewData,
    context,
  });
}

// =============================================================================
// Equipment Documentation Research (Knowledge Base)
// =============================================================================

import type {
  KBCitation,
  KBQueryResponse,
  EquipmentResearchResult,
  EquipmentResearchBatchResult,
  EquipmentResearchStatusResponse,
  ResearchEquipmentRequest,
  QueryEquipmentDocsRequest,
  EquipmentDocument,
} from '@/lib/ativos/types';

/**
 * Research documentation for a single piece of equipment.
 *
 * Uses Gemini 3.0 Pro with google_search grounding to find official
 * documentation from manufacturer websites. Documents are downloaded
 * and stored in S3 for Bedrock Knowledge Base ingestion.
 *
 * @param params.part_number - Equipment part number / SKU
 * @param params.description - Equipment description
 * @param params.serial_number - Optional serial number
 * @param params.manufacturer - Optional manufacturer name
 * @returns Research result with status, sources found, and documents downloaded
 */
export async function researchEquipment(
  params: ResearchEquipmentRequest
): Promise<AgentCoreResponse<EquipmentResearchResult>> {
  return invokeSGAAgentCore<EquipmentResearchResult>({
    action: 'research_equipment',
    part_number: params.part_number,
    description: params.description,
    serial_number: params.serial_number,
    manufacturer: params.manufacturer,
    additional_info: params.additional_info,
  });
}

/**
 * Research documentation for multiple equipment items in batch.
 *
 * Processes items sequentially to respect Google Search rate limits.
 * Useful after bulk imports to enrich all new items.
 *
 * @param equipment_list - List of equipment dicts with part_number, description, etc.
 * @returns Batch result with status for each item
 */
export async function researchEquipmentBatch(
  equipment_list: ResearchEquipmentRequest[]
): Promise<AgentCoreResponse<EquipmentResearchBatchResult>> {
  return invokeSGAAgentCore<EquipmentResearchBatchResult>({
    action: 'research_equipment_batch',
    equipment_list,
  });
}

/**
 * Get research status for a part number.
 *
 * Checks if documentation research has been completed for this item
 * and returns list of available documents if any.
 *
 * @param part_number - Part number to check
 * @returns Research status with documents if available
 */
export async function getResearchStatus(
  part_number: string
): Promise<AgentCoreResponse<EquipmentResearchStatusResponse>> {
  return invokeSGAAgentCore<EquipmentResearchStatusResponse>({
    action: 'get_research_status',
    part_number,
  });
}

/**
 * Query equipment documentation using Bedrock Knowledge Base.
 *
 * Searches the KB for relevant documentation and returns
 * answers with citations to source documents. Uses RAG
 * (Retrieval Augmented Generation) for accurate responses.
 *
 * @param params.query - Natural language question about equipment
 * @param params.part_number - Optional filter by specific part number
 * @param params.max_results - Maximum number of citations (default 5)
 * @returns Answer with citations to source documents
 */
export async function queryEquipmentDocs(
  params: QueryEquipmentDocsRequest
): Promise<AgentCoreResponse<KBQueryResponse>> {
  return invokeSGAAgentCore<KBQueryResponse>({
    action: 'query_equipment_docs',
    query: params.query,
    part_number: params.part_number,
    max_results: params.max_results ?? 5,
  });
}

// =============================================================================
// Agent Room (Sala de Transparencia)
// =============================================================================

/**
 * Options for getting Agent Room data.
 */
export interface GetAgentRoomDataOptions {
  /** Filter events by session ID (A2A session context) */
  sessionId?: string;
  /** Maximum number of live feed events to return (default: 50) */
  limit?: number;
}

/**
 * Get all Agent Room data for the transparency window.
 *
 * Returns humanized agent statuses, live feed events, learning stories,
 * active workflows, and pending decisions in a single call.
 *
 * @param options - Optional filters (sessionId for A2A context, limit)
 * @returns Agent Room data with all panels
 */
export async function getAgentRoomData(
  options?: GetAgentRoomDataOptions,
): Promise<AgentCoreResponse<AgentRoomDataResponse>> {
  return invokeSGAAgentCore<AgentRoomDataResponse>({
    action: 'get_agent_room_data',
    ...(options?.sessionId && { session_id: options.sessionId }),
    ...(options?.limit && { limit: options.limit }),
  });
}

// Agent Room response type
export interface AgentRoomDataResponse {
  success: boolean;
  timestamp: string;
  agents: AgentRoomAgent[];
  liveFeed: AgentRoomLiveMessage[];
  learningStories: AgentRoomLearningStory[];
  activeWorkflow: AgentRoomWorkflow | null;
  pendingDecisions: AgentRoomDecision[];
}

export interface AgentRoomAgent {
  id: string;
  technicalName: string;
  friendlyName: string;
  description: string;
  avatar: string;
  color: string;
  status: string;
  statusLabel: string;
  lastActivity: string | null;
}

export interface AgentRoomLiveMessage {
  id: string;
  timestamp: string;
  agentName: string;
  message: string;
  type: 'info' | 'success' | 'warning' | 'action_needed';
  eventType: string;
}

export interface AgentRoomLearningStory {
  id: string;
  learnedAt: string;
  agentName: string;
  story: string;
  confidence: 'alta' | 'media' | 'baixa';
}

export interface AgentRoomWorkflow {
  id: string;
  name: string;
  startedAt: string;
  steps: AgentRoomWorkflowStep[];
}

export interface AgentRoomWorkflowStep {
  id: string;
  label: string;
  icon: string;
  status: 'concluido' | 'atual' | 'pendente';
}

export interface AgentRoomDecision {
  id: string;
  question: string;
  options: { label: string; action: string }[];
  priority: 'alta' | 'normal';
  createdAt: string;
  taskType: string;
  entityId?: string;
}

// =============================================================================
// Agent Room X-Ray (Real-time Agent Traces)
// =============================================================================

/**
 * Options for getting X-Ray events.
 */
export interface GetXRayEventsOptions {
  /** Fetch events newer than this timestamp (for incremental updates) */
  sinceTimestamp?: string;
  /** Filter by specific session ID */
  filterSessionId?: string;
  /** Filter by specific agent ID */
  filterAgentId?: string;
  /** Only return HIL decision events */
  showHILOnly?: boolean;
  /** Maximum events to return (default: 50) */
  limit?: number;
}

/**
 * X-Ray event from backend.
 */
export interface XRayEventBackend {
  id: string;
  timestamp: string;
  type: 'agent_activity' | 'hil_decision' | 'a2a_delegation' | 'error' | 'session_start' | 'session_end';
  agentId: string;
  agentName: string;
  action: string;
  message: string;
  sessionId?: string;
  sessionName?: string;
  targetAgent?: string;
  targetAgentName?: string;
  duration?: number;
  details?: Record<string, unknown>;
  hilTaskId?: string;
  hilStatus?: 'pending' | 'approved' | 'rejected';
  hilQuestion?: string;
  hilOptions?: Array<{ label: string; value: string }>;
}

/**
 * X-Ray session from backend.
 */
export interface XRaySessionBackend {
  sessionId: string;
  sessionName: string;
  startTime: string;
  endTime?: string;
  status: 'active' | 'completed' | 'error';
  events: XRayEventBackend[];
  eventCount: number;
  totalDuration?: number;
}

/**
 * Response from get_xray_events action.
 */
export interface XRayEventsResponse {
  success: boolean;
  timestamp: string;
  events: XRayEventBackend[];
  sessions: XRaySessionBackend[];
  noSessionEvents: XRayEventBackend[];
  totalEvents: number;
  hilPendingCount: number;
}

/**
 * Get X-Ray events for Agent Room traces panel.
 *
 * Returns enriched agent activity events with session grouping,
 * duration calculations, and HIL task integration.
 *
 * @param options - Optional filters (sinceTimestamp for incremental updates)
 * @returns X-Ray events with session grouping
 */
export async function getXRayEvents(
  options?: GetXRayEventsOptions,
): Promise<AgentCoreResponse<XRayEventsResponse>> {
  return invokeSGAAgentCore<XRayEventsResponse>({
    action: 'get_xray_events',
    ...(options?.sinceTimestamp && { since_timestamp: options.sinceTimestamp }),
    ...(options?.filterSessionId && { filter_session_id: options.filterSessionId }),
    ...(options?.filterAgentId && { filter_agent_id: options.filterAgentId }),
    ...(options?.showHILOnly && { show_hil_only: options.showHILOnly }),
    ...(options?.limit && { limit: options.limit }),
  });
}

// Re-export types for consumer convenience
export type {
  KBCitation,
  KBQueryResponse,
  EquipmentResearchResult,
  EquipmentResearchBatchResult,
  EquipmentResearchStatusResponse,
  EquipmentDocument,
};
