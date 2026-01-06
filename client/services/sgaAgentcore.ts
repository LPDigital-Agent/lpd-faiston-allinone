// =============================================================================
// SGA AgentCore Service - Faiston NEXO Inventory Management
// =============================================================================
// Purpose: Invoke AWS Bedrock AgentCore Runtime for SGA (Sistema de Gestao de
// Ativos) Inventory module using JWT Bearer Token authentication.
//
// This service handles all AI features for inventory management:
// - Asset search and tracking
// - NF-e processing (intake)
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
} from '@/lib/ativos/smartImportTypes';
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
// NF-e Processing (Intake)
// =============================================================================

/**
 * Process NF-e upload (XML or PDF) and extract items.
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
 * Confirm NF-e entry with item mappings.
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
 * Get presigned URL for NF-e upload.
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
 * Get pending NF-e entries awaiting confirmation.
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
 */
export async function executeImport(params: {
  import_id: string;
  file_content_base64: string;
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
 * Complete expedition after NF-e emission.
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
 * Returns extracted data similar to NF-e processing.
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
 * - XML/PDF/Image -> IntakeAgent (NF-e processing)
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
