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
  | "nfe"           // NF-e (Nota Fiscal Eletrônica)
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
