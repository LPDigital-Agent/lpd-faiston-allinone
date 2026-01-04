// =============================================================================
// SGA Inventory Module - Hooks Index
// =============================================================================
// Central export for all SGA (Sistema de Gestão de Ativos) hooks.
// =============================================================================

// Asset hooks
export { useAssets } from './useAssets';
export type { SGAAssetFilters } from './useAssets';

export { useAssetDetail } from './useAssetDetail';

// Balance hook
export { useBalanceQuery } from './useBalanceQuery';

// Movement hooks
export { useMovements } from './useMovements';
export type { SGAMovementFilters } from './useMovements';

export { useMovementMutations } from './useMovementMutations';

export { useMovementValidation } from './useMovementValidation';
export type { SGAMovementType, ComplianceValidation } from './useMovementValidation';

// Master data hooks
export { useLocations } from './useLocations';
export type { SGALocation } from './useLocations';

export { usePartNumbers } from './usePartNumbers';
export type { SGAPartNumber } from './usePartNumbers';

export { useProjects } from './useProjects';
export type { SGAProject } from './useProjects';

// NF-e hook
export { useNFReader } from './useNFReader';
export type { NFExtraction, NFItemMapping, PendingNFEntry, ConfidenceScore } from './useNFReader';

// Scanner hook
export { useSerialScanner } from './useSerialScanner';
export type { ScanMode, ScanResult } from './useSerialScanner';

// Context-based hooks (re-exported from contexts for convenience)
export {
  useAssetManagement,
  useTaskInbox,
  useNexoEstoque,
  useInventoryOperations,
  useInventoryCount,
  useOfflineSync,
} from '@/contexts/ativos';
