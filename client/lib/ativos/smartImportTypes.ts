// =============================================================================
// Smart Import Types - Universal File Importer
// =============================================================================
// Types for the AI-powered smart import system that auto-detects file types
// and routes to the appropriate processing agent.
//
// Philosophy: Observe -> Think -> Learn -> Act
// The agent OBSERVES the file, THINKS about its type, LEARNS from patterns,
// and ACTS with the appropriate processor.
// =============================================================================

import type {
  NFExtraction,
  NFItemMapping,
  ImportColumnMapping,
  ImportPreviewRow,
  ConfidenceScore,
  PendingNFEntry,
} from './types';

// =============================================================================
// File Type Detection
// =============================================================================

/**
 * Detected file types from magic bytes + extension analysis.
 * Matches backend `FileType` in `tools/file_detector.py`.
 */
export type SmartFileType =
  | 'xml'       // XML files (NF-e)
  | 'pdf'       // PDF documents
  | 'image'     // JPG, PNG, GIF, WebP
  | 'csv'       // CSV spreadsheets
  | 'xlsx'      // Excel spreadsheets
  | 'txt'       // Plain text files
  | 'unknown';  // Unrecognized format

/**
 * Source type after processing - determines which preview to show.
 * More specific than SmartFileType as it indicates the processing path.
 */
export type SmartSourceType =
  | 'nf_xml'        // NF-e processed from XML
  | 'nf_pdf'        // NF-e processed from PDF (text extraction)
  | 'nf_image'      // NF-e processed from image (Vision OCR)
  | 'spreadsheet'   // CSV/XLSX processed by ImportAgent
  | 'text'          // TXT processed by ImportAgent + Gemini AI
  | 'unknown';

/**
 * Human-friendly labels for file types (Portuguese).
 * Matches backend `FILE_TYPE_LABELS`.
 */
export const FILE_TYPE_LABELS: Record<SmartFileType, string> = {
  xml: 'XML (Nota Fiscal)',
  pdf: 'PDF (Documento)',
  image: 'Imagem (JPG/PNG)',
  csv: 'CSV (Planilha)',
  xlsx: 'Excel (XLSX)',
  txt: 'Texto (TXT)',
  unknown: 'Formato desconhecido',
};

// =============================================================================
// Accepted Formats Configuration
// =============================================================================

/**
 * Accepted file formats for the SmartUploadZone.
 * These are the formats the backend can process.
 */
export const SMART_IMPORT_FORMATS = {
  /** HTML accept attribute string */
  accept: '.xml,.pdf,.jpg,.jpeg,.png,.csv,.xlsx,.txt',

  /** Allowed MIME types for validation */
  mimeTypes: [
    'application/xml',
    'text/xml',
    'application/pdf',
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
    'text/csv',
    'application/csv',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel',
    'text/plain',
  ] as const,

  /** Maximum file size in bytes (50MB) */
  maxFileSize: 50 * 1024 * 1024,
};

// =============================================================================
// Text Import Types (Gemini AI Processing)
// =============================================================================

/**
 * Item extracted from unstructured text by Gemini AI.
 */
export interface TextImportItem {
  part_number: string;
  quantity: number;
  description: string;
  serial?: string;
  unit?: string;
  raw_text?: string;      // Original text that generated this item
  confidence?: number;    // Per-item confidence
}

/**
 * Result from text import processing.
 */
export interface TextImportResult {
  success: boolean;
  source_type: 'text';
  filename: string;
  items: TextImportItem[];
  confidence: number;
  notes: string;
  raw_text_preview?: string;
  requires_hil: true;     // Text imports ALWAYS require human review
  project_id?: string;
  destination_location_id?: string;
  error?: string;
}

// =============================================================================
// Spreadsheet Import Types (CSV/XLSX)
// =============================================================================

/**
 * Result from spreadsheet import processing.
 * Reuses types from main types.ts (ImportColumnMapping, ImportPreviewRow).
 */
export interface SpreadsheetImportResult {
  success: boolean;
  source_type: 'spreadsheet';
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

// =============================================================================
// NF-e Import Types (XML/PDF/Image)
// =============================================================================

/**
 * Result from NF-e processing (XML, PDF, or Image via Vision OCR).
 */
export interface NFImportResult {
  success: boolean;
  source_type: 'nf_xml' | 'nf_pdf' | 'nf_image';
  entry_id: string;
  extraction: NFExtraction;
  suggested_mappings: NFItemMapping[];
  confidence_score: ConfidenceScore;
  requires_review: boolean;
  requires_hil?: boolean;
  project_id?: string;
  destination_location_id?: string;
  raw_xml_url?: string;
  evidence_url?: string;
  error?: string;
}

// =============================================================================
// Unified Smart Import Preview
// =============================================================================

/**
 * Unified preview result from smart_import_upload action.
 * Type narrows based on `source_type` field.
 */
export type SmartImportPreview =
  | NFImportResult
  | SpreadsheetImportResult
  | TextImportResult;

/**
 * Type guard for NF-e import result.
 */
export function isNFImportResult(preview: SmartImportPreview): preview is NFImportResult {
  return ['nf_xml', 'nf_pdf', 'nf_image'].includes(preview.source_type);
}

/**
 * Type guard for spreadsheet import result.
 */
export function isSpreadsheetImportResult(preview: SmartImportPreview): preview is SpreadsheetImportResult {
  return preview.source_type === 'spreadsheet';
}

/**
 * Type guard for text import result.
 */
export function isTextImportResult(preview: SmartImportPreview): preview is TextImportResult {
  return preview.source_type === 'text';
}

// =============================================================================
// Smart Import Request Types
// =============================================================================

/**
 * Request payload for smart_import_upload action.
 */
export interface SmartImportUploadRequest {
  s3_key: string;
  filename: string;
  content_type?: string;
  project_id?: string;
  /** Optional - can be detected from file or set in preview after analysis */
  destination_location_id?: string;
}

/**
 * Response from smart_import_upload action.
 */
export interface SmartImportUploadResponse {
  success: boolean;
  detected_type: SmartFileType;
  detected_type_label: string;
  source_type: SmartSourceType;
  preview: SmartImportPreview;
  message?: string;
  error?: string;
}

// =============================================================================
// Hook State Types
// =============================================================================

/**
 * Upload progress state.
 */
export interface SmartImportProgress {
  stage: 'idle' | 'uploading' | 'detecting' | 'processing' | 'complete' | 'error';
  percent: number;
  message: string;
}

/**
 * Return type for useSmartImporter hook.
 */
export interface UseSmartImporterReturn {
  /** Detected file type (set during upload) */
  detectedType: SmartFileType | null;

  /** Whether processing is in progress */
  isProcessing: boolean;

  /** Upload and processing progress */
  progress: SmartImportProgress;

  /** Error message if processing failed */
  error: string | null;

  /** Preview result after successful processing */
  preview: SmartImportPreview | null;

  /** Full response from backend */
  response: SmartImportUploadResponse | null;

  /**
   * Upload file and process with smart import.
   * @param file - File to upload
   * @param projectId - Optional project ID
   * @param locationId - Optional destination location ID (can be set in preview after analysis)
   * @returns Promise with preview result
   */
  uploadAndProcess: (
    file: File,
    projectId: string | null,
    locationId: string | null
  ) => Promise<SmartImportPreview>;

  /** Clear preview and reset state */
  clearPreview: () => void;

  /**
   * Confirm entry and create movements.
   * Implementation depends on source_type.
   */
  confirmEntry: () => Promise<void>;

  // =========================================================================
  // Pending Entries Support
  // =========================================================================

  /** List of pending entries awaiting review */
  pendingEntries: PendingNFEntry[];

  /** Whether pending entries are loading */
  pendingEntriesLoading: boolean;

  /** Refresh pending entries list */
  refreshPendingEntries: () => void;

  /** Assign a project to a pending entry */
  assignProject: (entryId: string, projectId: string) => Promise<void>;
}

// =============================================================================
// Confidence Matrix (Reference)
// =============================================================================

/**
 * Confidence thresholds for different source types.
 * Items below threshold require HIL review.
 */
export const CONFIDENCE_THRESHOLDS: Record<SmartSourceType, number> = {
  nf_xml: 0.90,      // XML is highly reliable
  nf_pdf: 0.80,      // PDF text extraction is reliable
  nf_image: 0.70,    // Vision OCR is less reliable
  spreadsheet: 0.80, // Depends on column mapping
  text: 0.0,         // Text ALWAYS requires HIL (set to 0 to force)
  unknown: 0.0,
};

/**
 * Check if preview requires human-in-the-loop review.
 */
export function requiresHILReview(preview: SmartImportPreview): boolean {
  // Text imports always require HIL
  if (preview.source_type === 'text') {
    return true;
  }

  // Check requires_hil flag if present
  if ('requires_hil' in preview && preview.requires_hil) {
    return true;
  }

  // Check requires_review flag
  if ('requires_review' in preview && preview.requires_review) {
    return true;
  }

  // Check confidence score against threshold
  if ('confidence_score' in preview && preview.confidence_score) {
    const threshold = CONFIDENCE_THRESHOLDS[preview.source_type];
    return preview.confidence_score.overall < threshold;
  }

  // Check raw confidence for text imports
  if ('confidence' in preview && typeof (preview as { confidence?: number }).confidence === 'number') {
    const threshold = CONFIDENCE_THRESHOLDS[preview.source_type];
    return (preview as { confidence: number }).confidence < threshold;
  }

  return false;
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Get human-friendly label for a file type.
 */
export function getFileTypeLabel(fileType: SmartFileType): string {
  return FILE_TYPE_LABELS[fileType] || 'Formato desconhecido';
}

/**
 * Detect file type from File object (client-side heuristic).
 * Uses extension since magic bytes require reading file content.
 */
export function detectFileTypeFromFile(file: File): SmartFileType {
  const ext = file.name.toLowerCase().split('.').pop() || '';

  const extMap: Record<string, SmartFileType> = {
    xml: 'xml',
    pdf: 'pdf',
    jpg: 'image',
    jpeg: 'image',
    png: 'image',
    gif: 'image',
    webp: 'image',
    csv: 'csv',
    xlsx: 'xlsx',
    xls: 'xlsx',
    txt: 'txt',
    text: 'txt',
    md: 'txt',
  };

  return extMap[ext] || 'unknown';
}

/**
 * Validate if file is acceptable for smart import.
 * @returns Error message if invalid, null if valid
 */
export function validateSmartImportFile(file: File): string | null {
  // Check file size
  if (file.size > SMART_IMPORT_FORMATS.maxFileSize) {
    const maxMB = SMART_IMPORT_FORMATS.maxFileSize / (1024 * 1024);
    return `Arquivo muito grande. Tamanho máximo: ${maxMB}MB`;
  }

  // Check file type
  const fileType = detectFileTypeFromFile(file);
  if (fileType === 'unknown') {
    const ext = file.name.split('.').pop() || '';
    return `Formato ".${ext}" não suportado. Use: XML, PDF, CSV, XLSX, JPG, PNG ou TXT`;
  }

  return null;
}

/**
 * Get icon name for a source type (for use with Lucide icons).
 */
export function getSourceTypeIcon(sourceType: SmartSourceType): string {
  const iconMap: Record<SmartSourceType, string> = {
    nf_xml: 'FileCode',
    nf_pdf: 'FileText',
    nf_image: 'Image',
    spreadsheet: 'Table',
    text: 'FileType',
    unknown: 'File',
  };

  return iconMap[sourceType] || 'File';
}

/**
 * Get color class for a source type (Tailwind).
 */
export function getSourceTypeColor(sourceType: SmartSourceType): string {
  const colorMap: Record<SmartSourceType, string> = {
    nf_xml: 'text-green-400',
    nf_pdf: 'text-red-400',
    nf_image: 'text-blue-400',
    spreadsheet: 'text-emerald-400',
    text: 'text-yellow-400',
    unknown: 'text-gray-400',
  };

  return colorMap[sourceType] || 'text-gray-400';
}
