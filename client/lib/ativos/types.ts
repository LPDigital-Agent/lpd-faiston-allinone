/**
 * Types for Gestão de Ativos (Asset Management) module
 *
 * These types define the core data structures used throughout
 * the asset management platform within Faiston One.
 */

// =============================================================================
// Core Asset Types
// =============================================================================

/**
 * Asset status representing the current state of an asset
 */
export type AssetStatus =
  | "disponivel"    // Available for use
  | "em_uso"        // Currently in use
  | "manutencao"    // Under maintenance
  | "em_transito"   // In transit/shipping
  | "baixado";      // Decommissioned/written off

/**
 * Asset category for classification
 */
export type AssetCategory =
  | "hardware"      // Computers, phones, equipment
  | "mobiliario"    // Furniture
  | "veiculos"      // Vehicles
  | "equipamentos"  // General equipment
  | "software"      // Software licenses
  | "outros";       // Other

/**
 * Location type for asset tracking
 */
export type LocationType =
  | "filial"        // Branch office
  | "departamento"  // Department
  | "estoque"       // Warehouse/storage
  | "externo";      // External location

/**
 * Location where an asset is stored or assigned
 */
export interface AssetLocation {
  id: string;
  nome: string;
  tipo: LocationType;
  endereco?: string;
  cidade?: string;
  estado?: string;
}

/**
 * User/responsible person for an asset
 */
export interface AssetResponsavel {
  id: string;
  nome: string;
  email?: string;
  departamento?: string;
  avatar?: string;
}

/**
 * Main Asset interface representing a physical or logical asset
 */
export interface Asset {
  id: string;
  codigo: string;              // Asset code (e.g., "FAI-NB-001")
  nome: string;                // Asset name/description
  categoria: AssetCategory;
  status: AssetStatus;
  localizacao: AssetLocation;
  responsavel: AssetResponsavel;
  dataAquisicao: string;       // ISO date string
  valorAquisicao: number;      // Original value in BRL
  valorAtual: number;          // Current depreciated value
  garantiaAte?: string;        // Warranty expiration date
  numeroSerie?: string;        // Serial number
  fabricante?: string;         // Manufacturer
  modelo?: string;             // Model
  notaFiscal?: string;         // Invoice number
  observacoes?: string;        // Notes
  createdAt: string;
  updatedAt: string;
}

// =============================================================================
// Movement & History Types
// =============================================================================

/**
 * Type of asset movement/transaction
 */
export type MovementType =
  | "entrada"       // Asset received/added
  | "saida"         // Asset dispatched
  | "transferencia" // Transfer between locations
  | "baixa"         // Write-off/decommission
  | "manutencao";   // Sent to maintenance

/**
 * Asset movement/transaction record
 */
export interface AssetMovement {
  id: string;
  ativoId: string;
  tipo: MovementType;
  origem?: AssetLocation;
  destino?: AssetLocation;
  responsavel: AssetResponsavel;
  data: string;
  observacao?: string;
  documentoRef?: string;       // Reference document (NF, etc)
}

// =============================================================================
// Shipping/Expedition Types
// =============================================================================

/**
 * Shipping order status
 */
export type ShippingStatus =
  | "aguardando"    // Waiting for dispatch
  | "em_transito"   // In transit
  | "entregue"      // Delivered
  | "cancelado";    // Cancelled

/**
 * Shipping priority
 */
export type ShippingPriority = "normal" | "alta" | "urgente";

/**
 * Shipping order/expedition
 */
export interface ShippingOrder {
  id: string;
  codigo: string;              // Order code (e.g., "EXP-2024-001")
  cliente: string;
  destino: AssetLocation;
  status: ShippingStatus;
  prioridade: ShippingPriority;
  responsavel: AssetResponsavel;
  itens: ShippingItem[];
  dataCriacao: string;
  dataPrevista: string;
  dataEnvio?: string;
  dataEntrega?: string;
  rastreio?: string;
  observacoes?: string;
}

/**
 * Item within a shipping order
 */
export interface ShippingItem {
  ativoId: string;
  ativoCodigo: string;
  ativoNome: string;
  quantidade: number;
}

// =============================================================================
// Return/Reversal Types
// =============================================================================

/**
 * Return request status
 */
export type ReturnStatus =
  | "solicitado"    // Requested
  | "em_transito"   // In transit back
  | "recebido"      // Received
  | "rejeitado";    // Rejected

/**
 * Return reason
 */
export type ReturnReason =
  | "defeito"       // Defective
  | "garantia"      // Warranty claim
  | "troca"         // Exchange
  | "desuso"        // No longer in use
  | "outro";        // Other

/**
 * Timeline event for return request
 */
export interface ReturnTimelineEvent {
  id: string;
  data: string;
  descricao: string;
  responsavel?: string;
}

/**
 * Return/reversal request
 */
export interface ReturnRequest {
  id: string;
  codigo: string;              // Request code (e.g., "REV-2024-001")
  ativoId: string;
  cliente: string;
  solicitante: AssetResponsavel;
  motivo: ReturnReason;
  status: ReturnStatus;
  descricao: string;
  dataSolicitacao: string;
  dataConclusao?: string;
  responsavel?: AssetResponsavel;
  timeline: ReturnTimelineEvent[];
}

// =============================================================================
// Dashboard & Analytics Types
// =============================================================================

/**
 * Alert severity level
 */
export type AlertLevel = "info" | "warning" | "error";

/**
 * Dashboard alert
 */
export interface DashboardAlert {
  id: string;
  tipo: AlertLevel;
  mensagem: string;
  link?: string;
  createdAt: string;
}

/**
 * Dashboard statistics summary
 */
export interface DashboardStats {
  totalAtivos: number;
  ativosDisponiveis: number;
  ativosEmUso: number;
  ativosEmTransito: number;
  ativosManutencao: number;
  ativosBaixados: number;
  valorTotal: number;
  valorDepreciacao: number;
  alertas: DashboardAlert[];
}

/**
 * Category breakdown for charts
 */
export interface CategoryBreakdown {
  categoria: AssetCategory;
  quantidade: number;
  valor: number;
  percentual: number;
}

/**
 * Status breakdown for charts
 */
export interface StatusBreakdown {
  status: AssetStatus;
  quantidade: number;
  percentual: number;
}

// =============================================================================
// Navigation Types
// =============================================================================

/**
 * Navigation module item for asset management tabs
 */
export interface AssetNavModule {
  id: string;
  label: string;
  labelShort?: string;         // Short label for mobile
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: number;              // Notification count
  disabled?: boolean;
}

// =============================================================================
// Fiscal/Tax Types
// =============================================================================

/**
 * Fiscal document type
 */
export type FiscalDocType =
  | "nfe"           // NF (Nota Fiscal Eletrônica)
  | "nfse"          // NFS-e (Nota Fiscal de Serviço)
  | "cte";          // CT-e (Conhecimento de Transporte)

/**
 * Fiscal document status
 */
export type FiscalStatus =
  | "autorizado"    // Authorized
  | "pendente"      // Pending authorization
  | "cancelado"     // Cancelled
  | "denegado";     // Denied

/**
 * Fiscal document
 */
export interface FiscalDocument {
  id: string;
  numero: string;
  tipo: FiscalDocType;
  status: FiscalStatus;
  valor: number;
  dataEmissao: string;
  cliente?: string;
  chaveAcesso?: string;
}

/**
 * Tax obligation deadline
 */
export interface TaxObligation {
  id: string;
  nome: string;
  prazo: string;
  status: "pendente" | "enviado" | "atrasado";
  descricao?: string;
}

// =============================================================================
// Communication Types
// =============================================================================

/**
 * Message priority
 */
export type MessagePriority = "alta" | "normal" | "baixa";

/**
 * Message category
 */
export type MessageCategory = "geral" | "solicitacao" | "aprovacao" | "alerta";

/**
 * Internal message
 */
export interface InternalMessage {
  id: string;
  assunto: string;
  conteudo: string;
  remetente: AssetResponsavel;
  remetenteId: string;
  departamento: string;
  categoria: MessageCategory;
  prioridade: MessagePriority;
  lida: boolean;
  favorita: boolean;
  dataEnvio: string;
  anexos?: string[];
}

// =============================================================================
// Filter & Search Types
// =============================================================================

/**
 * Asset list filters
 */
export interface AssetFilters {
  search?: string;
  categoria?: AssetCategory;
  status?: AssetStatus;
  localizacao?: string;
  responsavel?: string;
  dataInicio?: string;
  dataFim?: string;
}

/**
 * Pagination info
 */
export interface PaginationInfo {
  page: number;
  pageSize: number;
  total: number;
  totalPages: number;
}

/**
 * Paginated response wrapper
 */
export interface PaginatedResponse<T> {
  data: T[];
  pagination: PaginationInfo;
}

// =============================================================================
// SGA (Sistema de Gestao de Ativos) - Inventory Module Types
// =============================================================================
// Extended types for the AI-powered inventory management system.
// These types align with the DynamoDB single-table design and AgentCore agents.
// =============================================================================

// =============================================================================
// SGA Base Types & Enums
// =============================================================================

/**
 * SGA Movement types (event sourcing pattern).
 */
export type SGAMovementType =
  | 'ENTRY'           // Inbound from NF
  | 'EXIT'            // Outbound expedition
  | 'TRANSFER'        // Internal location transfer
  | 'ADJUSTMENT_IN'   // Inventory adjustment (+)
  | 'ADJUSTMENT_OUT'  // Inventory adjustment (-)
  | 'RESERVE'         // Block for expedition
  | 'UNRESERVE'       // Release reservation
  | 'RETURN';         // Reversa (customer return)

/**
 * SGA Asset status lifecycle.
 */
export type SGAAssetStatus =
  | 'AVAILABLE'       // Ready for use
  | 'RESERVED'        // Blocked for expedition
  | 'IN_TRANSIT'      // Being moved
  | 'WITH_CUSTOMER'   // Deployed at customer site
  | 'IN_REPAIR'       // Under maintenance
  | 'QUARANTINE'      // Quality hold
  | 'DISPOSED';       // Scrapped/discarded

/**
 * HIL Task status for approval workflows.
 */
export type HILTaskStatus =
  | 'PENDING'         // Awaiting action
  | 'APPROVED'        // Approved by reviewer
  | 'REJECTED'        // Rejected by reviewer
  | 'EXPIRED'         // TTL exceeded
  | 'CANCELLED';      // Cancelled by requestor

/**
 * HIL Task types.
 */
export type HILTaskType =
  | 'ADJUSTMENT_APPROVAL'
  | 'ENTRY_REVIEW'
  | 'TRANSFER_APPROVAL'
  | 'DISPOSAL_APPROVAL'
  | 'NEW_PN_APPROVAL';

/**
 * Divergence types from inventory counting.
 */
export type DivergenceType =
  | 'POSITIVE'           // Count > expected
  | 'NEGATIVE'           // Count < expected
  | 'SERIAL_MISMATCH'    // Different serial found
  | 'LOCATION_MISMATCH'; // Asset in wrong location

/**
 * Severity levels for compliance.
 */
export type Severity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

/**
 * Approval roles in hierarchy.
 */
export type ApprovalRole = 'OPERATOR' | 'MANAGER' | 'SUPERVISOR' | 'DIRECTOR';

/**
 * Notification priority.
 */
export type NotificationPriority = 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';

/**
 * Notification channels.
 */
export type NotificationChannel = 'SYSTEM' | 'EMAIL' | 'WHATSAPP';

/**
 * NF entry status.
 */
export type NFEntryStatus =
  | 'PENDING_UPLOAD'        // Awaiting file upload
  | 'PROCESSING'            // Being extracted
  | 'PENDING_CONFIRMATION'  // Awaiting user confirmation
  | 'PENDING_APPROVAL'      // Awaiting HIL approval (unmatched items)
  | 'PENDING_PROJECT'       // Awaiting project assignment (no project_id)
  | 'PENDING'               // Legacy: pending confirmation
  | 'CONFIRMED'             // User confirmed, ready for movement
  | 'COMPLETED'             // Movements created
  | 'REJECTED'              // Entry rejected
  | 'PARTIAL'               // Partially confirmed
  | 'FAILED'                // Processing failed
  | 'CANCELLED';            // Entry cancelled

/**
 * Inventory campaign status.
 */
export type CampaignStatus = 'DRAFT' | 'ACTIVE' | 'ANALYSIS' | 'COMPLETED' | 'CANCELLED';

// =============================================================================
// SGA Core Entity Types
// =============================================================================

/**
 * Part Number (catalog item/SKU).
 */
export interface SGAPartNumber {
  id: string;
  part_number: string;
  description: string;
  category: string;
  unit_of_measure: string;
  manufacturer?: string;
  ncm_code?: string;
  unit_cost?: number;
  minimum_stock?: number;
  maximum_stock?: number;
  reorder_point?: number;
  lead_time_days?: number;
  is_serialized: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  created_by: string;
}

/**
 * SGA Asset with serial number.
 */
export interface SGAAsset {
  id: string;
  part_number_id: string;
  part_number: string;
  serial_number: string;
  description: string;
  status: SGAAssetStatus;
  location_id: string;
  location_name?: string;
  project_id?: string;
  project_name?: string;
  batch_number?: string;
  acquisition_date?: string;
  warranty_expiry?: string;
  last_movement_at?: string;
  last_movement_type?: SGAMovementType;
  notes?: string;
  custom_fields?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

/**
 * SGA Stock location.
 */
export interface SGALocation {
  id: string;
  name: string;
  code: string;
  type: 'WAREHOUSE' | 'SHELF' | 'BIN' | 'CUSTOMER' | 'TRANSIT' | 'VIRTUAL';
  parent_location_id?: string;
  address?: string;
  is_restricted: boolean;
  restriction_type?: 'COFRE' | 'QUARENTENA' | 'DESCARTE';
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

/**
 * SGA Project/client.
 */
export interface SGAProject {
  id: string;
  code: string;
  name: string;
  client_name: string;
  is_active: boolean;
  start_date?: string;
  end_date?: string;
  manager_id?: string;
  manager_name?: string;
  created_at: string;
  updated_at: string;
}

/**
 * Stock balance projection.
 */
export interface SGABalance {
  part_number_id: string;
  part_number: string;
  location_id: string;
  location_name?: string;
  project_id?: string;
  project_name?: string;
  quantity_available: number;
  quantity_reserved: number;
  quantity_total: number;
  last_updated: string;
}

/**
 * SGA Movement event (immutable).
 */
export interface SGAMovement {
  id: string;
  type: SGAMovementType;
  part_number_id: string;
  part_number: string;
  quantity: number;
  serial_numbers?: string[];
  source_location_id?: string;
  source_location_name?: string;
  destination_location_id?: string;
  destination_location_name?: string;
  project_id?: string;
  project_name?: string;
  document_number?: string;
  document_type?: 'NF' | 'CHAMADO' | 'INTERNAL';
  reference_id?: string;
  reason?: string;
  notes?: string;
  created_by: string;
  created_by_name?: string;
  created_at: string;
  evidence_urls?: string[];
}

/**
 * Stock reservation.
 */
export interface SGAReservation {
  id: string;
  part_number_id: string;
  part_number: string;
  quantity: number;
  project_id: string;
  project_name?: string;
  location_id: string;
  location_name?: string;
  chamado_number?: string;
  reserved_by: string;
  reserved_by_name?: string;
  reserved_at: string;
  expires_at: string;
  status: 'ACTIVE' | 'FULFILLED' | 'CANCELLED' | 'EXPIRED';
  notes?: string;
}

// =============================================================================
// HIL (Human-in-the-Loop) Types
// =============================================================================

/**
 * HIL task for approval workflows.
 */
export interface HILTask {
  id: string;
  type: HILTaskType;
  title: string;
  description: string;
  status: HILTaskStatus;
  priority: NotificationPriority;
  requested_by: string;
  requested_by_name?: string;
  assigned_to?: string;
  assigned_to_name?: string;
  required_role: ApprovalRole;
  entity_type: string;
  entity_id: string;
  context: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  expires_at?: string;
  resolved_at?: string;
  resolved_by?: string;
  resolution_notes?: string;
}

// =============================================================================
// NF Processing Types
// =============================================================================

/**
 * NF item extracted from XML/PDF.
 */
export interface NFItem {
  item_number: number;
  product_code: string;
  description: string;
  ncm_code?: string;
  cfop?: string;
  unit_of_measure: string;
  quantity: number;
  unit_value: number;
  total_value: number;
  serial_numbers?: string[];
}

/**
 * NF extraction result.
 */
export interface NFExtraction {
  nf_number: string;
  nf_series: string;
  nf_key?: string;
  issue_date: string;
  supplier_cnpj: string;
  supplier_name: string;
  total_value: number;
  items: NFItem[];
  raw_xml_url?: string;
  confidence_score: number;
  extraction_warnings?: string[];
}

/**
 * Pending NF entry awaiting confirmation.
 */
export interface PendingNFEntry {
  id: string;
  nf_number: string;
  nf_series: string;
  supplier_name: string;
  total_items: number;
  total_value: number;
  destination_location_id: string;
  destination_location_name?: string;
  project_id: string;
  project_name?: string;
  status: NFEntryStatus;
  extraction: NFExtraction;
  item_mappings?: NFItemMapping[];
  uploaded_by: string;
  uploaded_by_name?: string;
  uploaded_at: string;
  confirmed_by?: string;
  confirmed_at?: string;
  notes?: string;
}

/**
 * Mapping between NF item and part number.
 */
export interface NFItemMapping {
  nf_item_number: number;
  part_number_id: string;
  part_number: string;
  quantity_confirmed: number;
  serial_numbers?: string[];
  match_confidence: number;
  match_method: 'EXACT' | 'SUPPLIER_CODE' | 'DESCRIPTION' | 'NCM' | 'MANUAL';
}

// =============================================================================
// Inventory Counting Types
// =============================================================================

/**
 * Inventory counting campaign.
 */
export interface InventoryCampaign {
  id: string;
  name: string;
  description?: string;
  status: CampaignStatus;
  location_ids: string[];
  project_ids?: string[];
  part_numbers?: string[];
  require_double_count: boolean;
  created_by: string;
  created_by_name?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  total_items_to_count: number;
  items_counted: number;
  divergences_found: number;
}

/**
 * Individual count result.
 */
export interface CountResult {
  id: string;
  campaign_id: string;
  part_number_id: string;
  part_number: string;
  location_id: string;
  expected_quantity: number;
  counted_quantity: number;
  serial_numbers_found?: string[];
  count_number: number;
  counted_by: string;
  counted_by_name?: string;
  counted_at: string;
  notes?: string;
}

/**
 * Divergence detected during counting.
 */
export interface Divergence {
  id: string;
  campaign_id: string;
  part_number_id: string;
  part_number: string;
  location_id: string;
  location_name?: string;
  type: DivergenceType;
  expected_quantity: number;
  counted_quantity: number;
  difference: number;
  serial_expected?: string;
  serial_found?: string;
  status: 'OPEN' | 'ADJUSTMENT_PROPOSED' | 'ADJUSTED' | 'IGNORED';
  resolution?: string;
  resolved_by?: string;
  resolved_at?: string;
}

/**
 * Adjustment proposal for divergence.
 */
export interface AdjustmentProposal {
  id: string;
  divergence_id: string;
  campaign_id: string;
  part_number_id: string;
  part_number: string;
  location_id: string;
  adjustment_type: 'ADJUSTMENT_IN' | 'ADJUSTMENT_OUT';
  quantity: number;
  reason: string;
  proposed_by: string;
  proposed_by_name?: string;
  proposed_at: string;
  hil_task_id?: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
}

// =============================================================================
// Compliance Types
// =============================================================================

/**
 * Compliance validation result.
 */
export interface ComplianceValidation {
  is_valid: boolean;
  requires_approval: boolean;
  approval_role?: ApprovalRole;
  violations: ComplianceViolation[];
  warnings: string[];
}

/**
 * Compliance violation record.
 */
export interface ComplianceViolation {
  id: string;
  entity_type: string;
  entity_id: string;
  violation_type: string;
  description: string;
  severity: Severity;
  flagged_by: string;
  flagged_at: string;
  resolved?: boolean;
  resolved_by?: string;
  resolved_at?: string;
  resolution_notes?: string;
}

// =============================================================================
// Confidence Scoring Types
// =============================================================================

/**
 * AI decision confidence score.
 */
export interface ConfidenceScore {
  overall: number;
  extraction_quality: number;
  evidence_strength: number;
  historical_match: number;
  risk_level: 'low' | 'medium' | 'high';
  factors: string[];
}

// =============================================================================
// SGA AgentCore Request Types
// =============================================================================

export interface SGASearchAssetsRequest {
  query?: string;
  part_number?: string;
  location_id?: string;
  project_id?: string;
  status?: SGAAssetStatus;
  page?: number;
  page_size?: number;
}

export interface SGAGetBalanceRequest {
  part_number: string;
  location_id?: string;
  project_id?: string;
}

export interface SGAWhereIsSerialRequest {
  serial_number: string;
}

export interface SGAProcessNFUploadRequest {
  s3_key: string;
  file_type: 'xml' | 'pdf';
  project_id: string;
  destination_location_id: string;
}

export interface SGAConfirmNFEntryRequest {
  entry_id: string;
  item_mappings: NFItemMapping[];
  notes?: string;
}

export interface SGAGetUploadUrlRequest {
  filename: string;
  content_type: string;
}

export interface SGACreateReservationRequest {
  part_number: string;
  quantity: number;
  project_id: string;
  location_id?: string;
  chamado_number?: string;
  notes?: string;
}

export interface SGACancelReservationRequest {
  reservation_id: string;
  reason: string;
}

export interface SGAProcessExpeditionRequest {
  reservation_id: string;
  part_number: string;
  quantity: number;
  serial_numbers?: string[];
  destination_location_id: string;
  technician_id?: string;
  notes?: string;
  evidence_urls?: string[];
}

export interface SGACreateTransferRequest {
  part_number: string;
  quantity: number;
  serial_numbers?: string[];
  source_location_id: string;
  destination_location_id: string;
  project_id?: string;
  reason: string;
  notes?: string;
}

export interface SGAProcessReturnRequest {
  part_number: string;
  quantity: number;
  serial_numbers?: string[];
  source_location_id: string;
  destination_location_id: string;
  project_id?: string;
  chamado_number?: string;
  condition: 'GOOD' | 'DAMAGED' | 'FOR_REPAIR';
  notes?: string;
}

export interface SGAGetPendingTasksRequest {
  assigned_to?: string;
  type?: HILTaskType;
  status?: HILTaskStatus;
}

export interface SGAApproveTaskRequest {
  task_id: string;
  notes?: string;
}

export interface SGARejectTaskRequest {
  task_id: string;
  reason: string;
}

export interface SGAStartCampaignRequest {
  name: string;
  description?: string;
  location_ids: string[];
  project_ids?: string[];
  part_numbers?: string[];
  require_double_count?: boolean;
}

export interface SGASubmitCountRequest {
  campaign_id: string;
  part_number: string;
  location_id: string;
  counted_quantity: number;
  serial_numbers_found?: string[];
  notes?: string;
}

export interface SGAProposeAdjustmentRequest {
  campaign_id: string;
  part_number: string;
  location_id: string;
  reason: string;
}

export interface SGAValidateOperationRequest {
  operation_type: SGAMovementType;
  part_number: string;
  quantity: number;
  source_location_id?: string;
  destination_location_id?: string;
  project_id?: string;
}

export interface SGANexoChatRequest {
  question: string;
  context?: Record<string, unknown>;
  conversation_history?: Array<{ role: string; content: string }>;
}

// =============================================================================
// SGA AgentCore Response Types
// =============================================================================

export interface SGASearchAssetsResponse {
  assets: SGAAsset[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface SGAGetBalanceResponse {
  balances: SGABalance[];
  total_available: number;
  total_reserved: number;
}

export interface SGAWhereIsSerialResponse {
  found: boolean;
  asset?: SGAAsset;
  timeline?: SGAMovement[];
}

export interface SGAProcessNFUploadResponse {
  entry_id: string;
  extraction: NFExtraction;
  suggested_mappings: NFItemMapping[];
  requires_review: boolean;
  confidence_score: ConfidenceScore;
}

export interface SGAConfirmNFEntryResponse {
  success: boolean;
  movements_created: number;
  assets_created: number;
  errors?: string[];
}

export interface SGAGetUploadUrlResponse {
  upload_url: string;
  s3_key: string;
  expires_in: number;
}

export interface SGACreateReservationResponse {
  reservation: SGAReservation;
  requires_approval: boolean;
  hil_task_id?: string;
}

export interface SGAProcessExpeditionResponse {
  movement: SGAMovement;
  assets_updated: number;
}

export interface SGACreateTransferResponse {
  movement?: SGAMovement;
  requires_approval: boolean;
  hil_task_id?: string;
}

export interface SGAProcessReturnResponse {
  movement: SGAMovement;
  condition_assessment?: string;
}

export interface SGAGetPendingTasksResponse {
  tasks: HILTask[];
  total: number;
}

export interface SGAApproveTaskResponse {
  task: HILTask;
  action_executed: boolean;
  result?: Record<string, unknown>;
}

export interface SGARejectTaskResponse {
  task: HILTask;
}

export interface SGAStartCampaignResponse {
  campaign: InventoryCampaign;
  items_to_count: number;
}

export interface SGASubmitCountResponse {
  count_result: CountResult;
  divergence_detected?: boolean;
  divergence?: Divergence;
}

export interface SGAAnalyzeDivergencesResponse {
  divergences: Divergence[];
  total_positive: number;
  total_negative: number;
  summary: string;
}

export interface SGAProposeAdjustmentResponse {
  proposal: AdjustmentProposal;
  hil_task_id: string;
}

export interface SGAValidateOperationResponse {
  validation: ComplianceValidation;
}

export interface SGANexoChatResponse {
  answer: string;
  data?: Record<string, unknown>;
  suggestions?: string[];
}

// =============================================================================
// SGA UI State Types
// =============================================================================

/**
 * SGA Asset filter state.
 */
export interface SGAAssetFilters {
  search: string;
  part_number?: string;
  location_id?: string;
  project_id?: string;
  status?: SGAAssetStatus;
  date_from?: string;
  date_to?: string;
}

/**
 * SGA Movement filter state.
 */
export interface SGAMovementFilters {
  search: string;
  type?: SGAMovementType;
  part_number?: string;
  location_id?: string;
  project_id?: string;
  date_from?: string;
  date_to?: string;
}

/**
 * Sort configuration.
 */
export interface SGASortConfig {
  field: string;
  direction: 'asc' | 'desc';
}

/**
 * Offline sync queue item.
 */
export interface SGAOfflineQueueItem {
  id: string;
  action: string;
  payload: Record<string, unknown>;
  created_at: string;
  retries: number;
  last_error?: string;
}

// =============================================================================
// SGA Dashboard Types
// =============================================================================

/**
 * KPI metric for dashboard.
 */
export interface SGAKPIMetric {
  label: string;
  value: number | string;
  unit?: string;
  change?: number;
  change_period?: string;
  trend?: 'up' | 'down' | 'stable';
  icon?: string;
}

/**
 * Dashboard summary.
 */
export interface SGADashboardSummary {
  total_assets: number;
  total_part_numbers: number;
  total_locations: number;
  total_projects: number;
  pending_tasks: number;
  pending_entries: number;
  pending_reversals: number;
  movements_today: number;
  movements_this_week: number;
  active_campaigns: number;
  open_divergences: number;
}

// =============================================================================
// Bulk Import Types
// =============================================================================

/**
 * Column mapping from import file to system fields.
 */
export interface ImportColumnMapping {
  file_column: string;
  target_field: string;
  confidence: number;
  sample_values: string[];
}

/**
 * Single row from import preview.
 */
export interface ImportPreviewRow {
  row_number: number;
  mapped_data: Record<string, string>;
  validation_errors: string[];
  pn_match: SGAPartNumber | null;
  match_confidence: number;
  match_method: 'supplier_code' | 'description_ai' | 'ncm' | 'none';
}

/**
 * Import preview response.
 */
export interface SGAImportPreviewResponse {
  success: boolean;
  import_id: string;
  filename: string;
  file_type: 'csv' | 'xlsx';
  total_rows: number;
  column_mappings: ImportColumnMapping[];
  unmapped_columns: string[];
  matched_rows: ImportPreviewRow[];
  unmatched_rows: ImportPreviewRow[];
  stats: {
    preview_rows_shown: number;
    matched_count: number;
    unmatched_count: number;
    match_rate: number;
    total_quantity: number;
  };
  confidence_score: ConfidenceScore;
  requires_review: boolean;
  project_id?: string;
  destination_location_id?: string;
  error?: string;
}

/**
 * Created movement from import.
 */
export interface ImportCreatedMovement {
  row_number: number;
  movement_id: string;
  pn_id: string;
  pn_number: string;
  quantity: number;
}

/**
 * Failed or skipped row from import.
 */
export interface ImportFailedRow {
  row_number: number;
  reason: string;
  data: Record<string, string>;
}

/**
 * Import execution response.
 */
export interface SGAImportExecuteResponse {
  success: boolean;
  import_id: string;
  total_rows: number;
  created_count: number;
  failed_count: number;
  skipped_count: number;
  success_rate: number;
  created_movements: ImportCreatedMovement[];
  failed_rows: ImportFailedRow[];
  skipped_rows: ImportFailedRow[];
  message: string;
  error?: string;
}

/**
 * PN mapping validation response.
 */
export interface SGAPNMappingValidationResponse {
  success: boolean;
  description: string;
  suggested_pn: SGAPartNumber | null;
  ai_match: SGAPartNumber | null;
  ai_confidence: number;
  alternatives: SGAPartNumber[];
  error?: string;
}

// =============================================================================
// Expedition Agent Types (SAP-Ready)
// =============================================================================

/**
 * Item for expedition request.
 */
export interface SGAExpeditionItem {
  pn_id: string;
  serial?: string;
  quantity: number;
}

/**
 * Urgency level for expedition.
 */
export type SGAExpeditionUrgency = 'LOW' | 'NORMAL' | 'HIGH' | 'URGENT';

/**
 * Natureza da operação for NF.
 */
export type SGAExpeditionNature =
  | 'USO_CONSUMO'      // REMESSA PARA USO E CONSUMO
  | 'CONSERTO'         // REMESSA PARA CONSERTO
  | 'DEMONSTRACAO'     // REMESSA PARA DEMONSTRAÇÃO
  | 'DEVOLUCAO'        // DEVOLUÇÃO
  | 'GARANTIA';        // REMESSA EM GARANTIA

/**
 * Expedition request payload.
 */
export interface SGAExpeditionRequestPayload {
  chamado_id: string;
  project_id: string;
  items: SGAExpeditionItem[];
  destination_client: string;
  destination_address: string;
  urgency: SGAExpeditionUrgency;
  nature: SGAExpeditionNature;
  notes?: string;
}

/**
 * SAP-ready data for NF copy/paste.
 */
export interface SGASAPFormatData {
  cliente: string;
  item_numero: string;
  quantidade: number;
  deposito: string;
  utilizacao: string;
  incoterms: string;
  transportadora: string;
  natureza_operacao: string;
  observacao: string;
  peso_liquido?: string;
  peso_bruto?: string;
  embalagem?: string;
}

/**
 * Expedition status.
 */
export type SGAExpeditionStatus =
  | 'PENDING'
  | 'STOCK_VERIFIED'
  | 'SEPARATED'
  | 'COMPLETED'
  | 'CANCELLED';

/**
 * Expedition item result.
 */
export interface SGAExpeditionItemResult {
  pn_id: string;
  pn_number: string;
  serial: string | null;
  quantity: number;
  available: boolean;
  reserved_id?: string;
  sap_data: SGASAPFormatData;
}

/**
 * Expedition response.
 */
export interface SGAExpeditionResponse {
  success: boolean;
  expedition_id: string;
  status: SGAExpeditionStatus;
  chamado_id: string;
  project_id: string;
  items: SGAExpeditionItemResult[];
  sap_ready_data: SGASAPFormatData[];
  all_items_available: boolean;
  requires_carrier_quote: boolean;
  message: string;
  created_at: string;
  error?: string;
}

/**
 * Stock verification response.
 */
export interface SGAVerifyStockResponse {
  success: boolean;
  pn_id: string;
  serial?: string;
  quantity_requested: number;
  quantity_available: number;
  available: boolean;
  location_id: string;
  location_name: string;
  reserved_assets?: SGAAsset[];
  error?: string;
}

/**
 * Separation confirmation payload.
 */
export interface SGAConfirmSeparationPayload {
  expedition_id: string;
  items_confirmed: Array<{
    pn_id: string;
    serial: string;
    quantity: number;
  }>;
  package_info: {
    packages: number;
    net_weight_kg: number;
    gross_weight_kg: number;
    dimensions?: string;
  };
}

/**
 * Separation confirmation response.
 */
export interface SGAConfirmSeparationResponse {
  success: boolean;
  expedition_id: string;
  status: SGAExpeditionStatus;
  items_confirmed: number;
  package_info: {
    packages: number;
    net_weight_kg: number;
    gross_weight_kg: number;
  };
  ready_for_nf: boolean;
  error?: string;
}

/**
 * Complete expedition payload.
 */
export interface SGACompleteExpeditionPayload {
  expedition_id: string;
  nf_number: string;
  nf_key: string;
  carrier: string;
  tracking_code?: string;
}

/**
 * Complete expedition response.
 */
export interface SGACompleteExpeditionResponse {
  success: boolean;
  expedition_id: string;
  movements_created: SGAMovement[];
  nf_number: string;
  carrier: string;
  tracking_code?: string;
  message: string;
  error?: string;
}

// =============================================================================
// Carrier Quote Types
// =============================================================================

/**
 * Carrier types.
 */
export type SGACarrierType =
  | 'CORREIOS'
  | 'LOGGI'
  | 'GOLLOG'
  | 'TRANSPORTADORA'
  | 'DEDICADO';

/**
 * Shipping modal.
 */
export type SGAShippingModal =
  | 'GROUND'
  | 'EXPRESS'
  | 'AIR'
  | 'SAME_DAY'
  | 'PAC'
  | 'SEDEX'
  | 'AEREO';

/**
 * Shipping quote from a carrier.
 */
export interface SGAShippingQuote {
  carrier: string;
  carrier_type: SGACarrierType;
  modal: SGAShippingModal;
  price: number;
  delivery_days: number;
  delivery_date: string;
  weight_limit: number;
  dimensions_limit: string;
  available: boolean;
  reason?: string;
}

/**
 * Get quotes request.
 */
export interface SGAGetQuotesRequest {
  origin_cep: string;
  destination_cep: string;
  weight_kg: number;
  dimensions: {
    length: number;
    width: number;
    height: number;
  };
  value: number;
  urgency: SGAExpeditionUrgency;
}

/**
 * Carrier recommendation.
 */
export interface SGACarrierRecommendation {
  carrier: string;
  modal: SGAShippingModal;
  price?: number;
  delivery_days?: number;
  reason: string;
  confidence: number;
}

/**
 * Get quotes response.
 */
export interface SGAGetQuotesResponse {
  success: boolean;
  quotes: SGAShippingQuote[];
  recommendation: SGACarrierRecommendation;
  note?: string;
  error?: string;
}

/**
 * Recommend carrier request.
 */
export interface SGARecommendCarrierRequest {
  urgency: SGAExpeditionUrgency;
  weight_kg: number;
  value: number;
  destination_state: string;
  same_city: boolean;
}

/**
 * Recommend carrier response.
 */
export interface SGARecommendCarrierResponse {
  success: boolean;
  recommendation: SGACarrierRecommendation;
  alternatives: Array<{ carrier: string; modal: SGAShippingModal }>;
  error?: string;
}

/**
 * Tracking event.
 */
export interface SGATrackingEvent {
  date: string;
  status: string;
  location: string;
}

/**
 * Track shipment request.
 */
export interface SGATrackShipmentRequest {
  tracking_code: string;
  carrier?: string;
}

/**
 * Track shipment response.
 */
export interface SGATrackShipmentResponse {
  success: boolean;
  tracking: {
    tracking_code: string;
    carrier: string;
    status: string;
    last_update: string;
    events: SGATrackingEvent[];
    estimated_delivery: string;
  };
  note?: string;
  error?: string;
}

// =============================================================================
// Reverse Logistics Types
// =============================================================================

/**
 * Origin type for reverse.
 */
export type SGAReverseOriginType =
  | 'CUSTOMER'
  | 'FIELD_TECH'
  | 'BRANCH'
  | 'THIRD_PARTY';

/**
 * Equipment owner.
 */
export type SGAEquipmentOwner = 'FAISTON' | 'NTT' | 'TERCEIROS';

/**
 * Equipment condition.
 */
export type SGAEquipmentCondition = 'FUNCIONAL' | 'DEFEITUOSO' | 'INSERVIVEL';

/**
 * Return reason.
 */
export type SGAReturnReason =
  | 'CONSERTO_CONCLUIDO'
  | 'DEVOLUCAO_CLIENTE'
  | 'FIM_CONTRATO'
  | 'UPGRADE'
  | 'TROCA_GARANTIA'
  | 'EQUIPAMENTO_DEFEITUOSO'
  | 'OUTRO';

/**
 * SAP depot codes.
 */
export interface SGADepotMapping {
  '01': 'Recebimento';
  '03': 'BAD';
  '03.01': 'BAD_NTT';
  '04': 'Descarte';
  '05': 'Itens de terceiros';
  '06': 'Depósito de terceiros';
}

/**
 * Process return request.
 */
export interface SGAProcessReturnRequestNew {
  serial: string;
  origin_type: SGAReverseOriginType;
  origin_address: string;
  owner: SGAEquipmentOwner;
  condition: SGAEquipmentCondition;
  return_reason: SGAReturnReason;
  chamado_id?: string;
  project_id?: string;
  notes?: string;
}

/**
 * Process return response.
 */
export interface SGAProcessReturnResponseNew {
  success: boolean;
  return_id: string;
  serial: string;
  owner: SGAEquipmentOwner;
  condition: SGAEquipmentCondition;
  destination_depot: string;
  destination_depot_name: string;
  movement_created: boolean;
  movement_id?: string;
  requires_analysis: boolean;
  analysis_task_id?: string;
  message: string;
  error?: string;
}

/**
 * Validate origin request.
 */
export interface SGAValidateOriginRequest {
  serial: string;
  claimed_origin: string;
}

/**
 * Validate origin response.
 */
export interface SGAValidateOriginResponse {
  success: boolean;
  serial: string;
  found: boolean;
  asset?: SGAAsset;
  last_known_location?: string;
  last_movement_date?: string;
  origin_matches: boolean;
  confidence: number;
  error?: string;
}

/**
 * Evaluate condition request.
 */
export interface SGAEvaluateConditionRequest {
  serial: string;
  owner: SGAEquipmentOwner;
  condition_description: string;
  photos_s3_keys?: string[];
}

/**
 * Evaluate condition response.
 */
export interface SGAEvaluateConditionResponse {
  success: boolean;
  serial: string;
  detected_condition: SGAEquipmentCondition;
  recommended_depot: string;
  recommended_depot_name: string;
  confidence: number;
  reasoning: string;
  requires_manual_inspection: boolean;
  defects_detected?: string[];
  error?: string;
}

// =============================================================================
// Accuracy Metrics Types (Phase 3.4)
// =============================================================================

/**
 * Period filter for metrics queries.
 */
export type SGAMetricsPeriod = '7d' | '30d' | '90d' | 'ytd';

/**
 * Single metric with trend information.
 */
export interface SGAMetricValue {
  value: number;
  unit: string;
  trend: 'up' | 'down' | 'stable';
  change: number;
}

/**
 * PN matching breakdown by method.
 */
export interface SGAPNMatchByMethod {
  supplier_code: number;
  description_ai: number;
  ncm: number;
  manual: number;
}

/**
 * Movements summary by type.
 */
export interface SGAMovementsSummary {
  entrada: number;
  saida: number;
  transferencia: number;
  ajuste: number;
  reserva: number;
}

/**
 * Pending items summary.
 */
export interface SGAPendingItems {
  pending_project: number;
  pending_hil: number;
  pending_reconciliation: number;
}

/**
 * Accuracy metrics response from AgentCore.
 */
export interface SGAAccuracyMetrics {
  extraction_accuracy: SGAMetricValue;
  entry_success_rate: SGAMetricValue;
  avg_hil_time: SGAMetricValue;
  divergence_rate: SGAMetricValue;
  pn_match_by_method: SGAPNMatchByMethod;
  movements_summary: SGAMovementsSummary;
  pending_items: SGAPendingItems;
}

/**
 * Get accuracy metrics request.
 */
export interface SGAGetAccuracyMetricsRequest {
  period?: SGAMetricsPeriod;
}

/**
 * Get accuracy metrics response.
 */
export interface SGAGetAccuracyMetricsResponse {
  success: boolean;
  period: SGAMetricsPeriod;
  metrics: SGAAccuracyMetrics;
  generated_at: string;
  error?: string;
}

// =============================================================================
// SAP Reconciliation Types (Phase 3.5)
// =============================================================================

/**
 * SAP export item for reconciliation.
 */
export interface SGASAPExportItem {
  part_number: string;
  location: string;
  quantity: number;
  serial?: string;
  description?: string;
}

/**
 * Delta type for reconciliation.
 */
export type SGADeltaType = 'FALTA_SGA' | 'SOBRA_SGA';

/**
 * Reconciliation delta item.
 */
export interface SGAReconciliationDelta {
  id: string;
  part_number: string;
  location: string;
  sap_quantity: number;
  sga_quantity: number;
  delta: number;
  delta_type: SGADeltaType;
}

/**
 * Reconciliation summary.
 */
export interface SGAReconciliationSummary {
  falta_sga: number;
  sobra_sga: number;
}

/**
 * Reconcile SAP export request.
 */
export interface SGAReconcileSAPRequest {
  sap_data: SGASAPExportItem[];
}

/**
 * Reconcile SAP export response.
 */
export interface SGAReconcileSAPResponse {
  success: boolean;
  reconciliation_id: string;
  total_sap_items: number;
  match_rate: number;
  deltas: SGAReconciliationDelta[];
  summary: SGAReconciliationSummary;
  error?: string;
}

/**
 * Action types for reconciliation deltas.
 */
export type SGAReconciliationAction = 'CREATE_ADJUSTMENT' | 'IGNORE' | 'INVESTIGATE';

/**
 * Apply reconciliation action request.
 */
export interface SGAApplyReconciliationActionRequest {
  delta_id: string;
  action: SGAReconciliationAction;
  reason?: string;
}

/**
 * Apply reconciliation action response.
 */
export interface SGAApplyReconciliationActionResponse {
  success: boolean;
  delta_id: string;
  action_taken: SGAReconciliationAction;
  adjustment_id?: string;
  message: string;
  error?: string;
}

// =============================================================================
// Equipment Documentation / Knowledge Base Types (Phase 6)
// =============================================================================

/**
 * Research status for equipment documentation.
 */
export type EquipmentResearchStatus =
  | 'NOT_RESEARCHED'
  | 'PENDING'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'NO_DOCS_FOUND'
  | 'FAILED'
  | 'RATE_LIMITED';

/**
 * Document type categories.
 */
export type EquipmentDocumentType =
  | 'manual'
  | 'datasheet'
  | 'spec'
  | 'guide'
  | 'firmware'
  | 'driver'
  | 'unknown';

/**
 * Citation from Knowledge Base query result.
 */
export interface KBCitation {
  document_id: string;
  s3_uri: string;
  part_number?: string;
  document_type?: EquipmentDocumentType;
  title?: string;
  excerpt: string;
  score: number;
  download_url?: string;
}

/**
 * Knowledge Base query response.
 */
export interface KBQueryResponse {
  success: boolean;
  answer: string;
  citations: KBCitation[];
  query: string;
  error?: string;
}

/**
 * Downloaded equipment document metadata.
 */
export interface EquipmentDocument {
  s3_key: string;
  filename: string;
  document_type: EquipmentDocumentType;
  size_bytes: number;
  source_url?: string;
  last_modified?: string;
}

/**
 * Research result for equipment documentation.
 */
export interface EquipmentResearchResult {
  success: boolean;
  part_number: string;
  status: EquipmentResearchStatus;
  search_queries: string[];
  sources_found: number;
  documents_downloaded: EquipmentDocument[];
  s3_prefix: string;
  summary: string;
  confidence?: ConfidenceScore;
  reasoning_trace: Array<{
    type: string;
    content: string;
    timestamp: string;
  }>;
  error?: string;
}

/**
 * Research batch result.
 */
export interface EquipmentResearchBatchResult {
  success: boolean;
  total_items: number;
  completed: number;
  no_docs_found: number;
  failed: number;
  rate_limited: number;
  results: Array<{
    part_number: string;
    status: EquipmentResearchStatus;
    documents_downloaded: number;
    summary: string;
  }>;
}

/**
 * Research status check response.
 */
export interface EquipmentResearchStatusResponse {
  success: boolean;
  part_number: string;
  status: EquipmentResearchStatus;
  documents: EquipmentDocument[];
  s3_prefix?: string;
  error?: string;
}

/**
 * Request to research equipment documentation.
 */
export interface ResearchEquipmentRequest {
  part_number: string;
  description: string;
  serial_number?: string;
  manufacturer?: string;
  additional_info?: Record<string, unknown>;
}

/**
 * Request to query equipment documentation KB.
 */
export interface QueryEquipmentDocsRequest {
  query: string;
  part_number?: string;
  max_results?: number;
}
