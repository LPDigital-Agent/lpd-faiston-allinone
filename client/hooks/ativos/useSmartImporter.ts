// =============================================================================
// useSmartImporter Hook - SGA Inventory Module
// =============================================================================
// Universal file importer with auto-detection.
// Handles file upload, type detection, and routes to appropriate processor.
//
// Philosophy: Observe -> Think -> Learn -> Act
// The hook OBSERVES the file, THINKS about its type, LEARNS from detection,
// and ACTS by routing to the appropriate backend agent.
// =============================================================================

'use client';

import { useState, useCallback } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getNFUploadUrl,
  invokeSmartImport,
  confirmNFEntry,
  getPendingNFEntries,
  assignProjectToEntry,
} from '@/services/sgaAgentcore';
import type {
  SmartFileType,
  SmartSourceType,
  SmartImportPreview,
  SmartImportProgress,
  UseSmartImporterReturn,
  SmartImportUploadResponse,
} from '@/lib/ativos/smartImportTypes';
import type { PendingNFEntry } from '@/lib/ativos/types';
import {
  detectFileTypeFromFile,
  validateSmartImportFile,
  requiresHILReview,
  isNFImportResult,
  isSpreadsheetImportResult,
  isTextImportResult,
  getFileTypeLabel,
} from '@/lib/ativos/smartImportTypes';
import type { NFItemMapping, SGAConfirmNFEntryResponse } from '@/lib/ativos/types';

// =============================================================================
// Constants
// =============================================================================

const INITIAL_PROGRESS: SmartImportProgress = {
  stage: 'idle',
  percent: 0,
  message: '',
};

// Query key for pending entries
const PENDING_ENTRIES_KEY = 'sga-pending-nf-entries';

// =============================================================================
// Hook
// =============================================================================

export function useSmartImporter(): UseSmartImporterReturn {
  const queryClient = useQueryClient();

  // Detection state
  const [detectedType, setDetectedType] = useState<SmartFileType | null>(null);

  // Fetch pending entries (reuse same key as useNFReader for cache sharing)
  const {
    data: pendingEntriesData,
    isLoading: pendingEntriesLoading,
    refetch: refreshPendingEntries,
  } = useQuery({
    queryKey: [PENDING_ENTRIES_KEY],
    queryFn: async () => {
      const result = await getPendingNFEntries();
      return result.data.entries;
    },
    staleTime: 60000, // 1 minute
    retry: 1,
  });

  // Processing state
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState<SmartImportProgress>(INITIAL_PROGRESS);
  const [error, setError] = useState<string | null>(null);

  // Result state
  const [preview, setPreview] = useState<SmartImportPreview | null>(null);
  const [response, setResponse] = useState<SmartImportUploadResponse | null>(null);

  /**
   * Upload file and process with smart import.
   * Auto-detects file type and routes to appropriate agent.
   * projectId and locationId are optional - can be set in preview after analysis.
   */
  const uploadAndProcess = useCallback(async (
    file: File,
    projectId: string | null,
    locationId: string | null
  ): Promise<SmartImportPreview> => {
    setIsProcessing(true);
    setError(null);
    setPreview(null);
    setResponse(null);
    setProgress({ stage: 'detecting', percent: 5, message: 'Detectando tipo de arquivo...' });

    try {
      // =======================================================================
      // OBSERVE: Validate and detect file type (client-side heuristic)
      // =======================================================================
      const validationError = validateSmartImportFile(file);
      if (validationError) {
        throw new Error(validationError);
      }

      const fileType = detectFileTypeFromFile(file);
      setDetectedType(fileType);
      setProgress({
        stage: 'detecting',
        percent: 10,
        message: `Tipo detectado: ${getFileTypeLabel(fileType)}`,
      });

      if (fileType === 'unknown') {
        throw new Error('Formato de arquivo não suportado');
      }

      // =======================================================================
      // THINK: Get presigned URL for upload
      // =======================================================================
      setProgress({ stage: 'uploading', percent: 20, message: 'Obtendo URL de upload...' });

      const contentType = file.type || getContentTypeForFileType(fileType);
      const urlResult = await getNFUploadUrl({
        filename: file.name,
        content_type: contentType,
      });

      // Defensive validation - ensure we got a valid response
      if (!urlResult.data || !urlResult.data.upload_url || !urlResult.data.s3_key) {
        const errorMsg = (urlResult.data as { error?: string })?.error || 'Falha ao obter URL de upload';
        throw new Error(errorMsg);
      }

      // =======================================================================
      // LEARN: Upload file to S3
      // =======================================================================
      setProgress({ stage: 'uploading', percent: 40, message: 'Enviando arquivo...' });

      const uploadResponse = await fetch(urlResult.data.upload_url, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': contentType,
        },
      });

      if (!uploadResponse.ok) {
        throw new Error('Falha no upload do arquivo');
      }

      // =======================================================================
      // ACT: Call smart import (backend will detect and route)
      // =======================================================================
      setProgress({ stage: 'processing', percent: 70, message: 'Processando arquivo...' });

      const smartResult = await invokeSmartImport({
        s3_key: urlResult.data.s3_key,
        filename: file.name,
        content_type: contentType,
        project_id: projectId || undefined,
        destination_location_id: locationId || undefined,
      });

      // =======================================================================
      // Complete: Set result state
      // =======================================================================
      setProgress({ stage: 'complete', percent: 100, message: 'Processamento concluído!' });

      // DEBUG: Log the actual response to diagnose modal issue
      console.log('[SmartImporter] Raw smartResult:', JSON.stringify(smartResult, null, 2));
      console.log('[SmartImporter] smartResult.data:', smartResult.data);
      console.log('[SmartImporter] smartResult.data.preview:', smartResult.data?.preview);
      console.log('[SmartImporter] smartResult.data.source_type:', smartResult.data?.source_type);

      // Handle both OLD format (no preview wrapper) and NEW format (with preview wrapper)
      // OLD: { source_type, items, ... } directly
      // NEW: { success, preview: { source_type, items, ... } }
      const responseData = smartResult.data;
      const previewResult = responseData?.preview ||
        (responseData?.source_type ? responseData as unknown as SmartImportPreview : null);

      console.log('[SmartImporter] Resolved previewResult:', previewResult);

      setPreview(previewResult);
      setResponse(smartResult.data);

      // Update detected type from backend (more reliable)
      const detectedType = smartResult.data?.detected_type ||
        (previewResult as Record<string, unknown>)?.detected_file_type as SmartFileType | undefined;
      setDetectedType(detectedType || null);

      return previewResult;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao processar arquivo';
      setError(message);
      setProgress({ stage: 'error', percent: 0, message });
      throw err;
    } finally {
      setIsProcessing(false);
    }
  }, []);

  /**
   * Clear preview and reset state.
   */
  const clearPreview = useCallback(() => {
    setPreview(null);
    setResponse(null);
    setDetectedType(null);
    setError(null);
    setProgress(INITIAL_PROGRESS);
  }, []);

  /**
   * Confirm entry and create movements.
   * Implementation varies based on source_type.
   */
  const confirmEntry = useCallback(async () => {
    if (!preview) {
      throw new Error('Nenhum preview disponível para confirmar');
    }

    // Confirm based on source type
    if (isNFImportResult(preview)) {
      // NF confirmation
      const result = await confirmNFEntry({
        entry_id: preview.entry_id,
        item_mappings: preview.suggested_mappings,
        notes: undefined,
      });

      if (!result.data.success) {
        throw new Error(result.data.errors?.join(', ') || 'Erro ao confirmar entrada');
      }

      // Invalidate queries
      queryClient.invalidateQueries({ queryKey: ['sga-assets'] });
      queryClient.invalidateQueries({ queryKey: ['sga-balance'] });
      queryClient.invalidateQueries({ queryKey: ['sga-movements'] });
      queryClient.invalidateQueries({ queryKey: ['sga-pending-nf-entries'] });

      clearPreview();
      return;
    }

    if (isSpreadsheetImportResult(preview)) {
      // Spreadsheet confirmation - TODO: Call executeImport
      // For now, just clear preview
      console.warn('Spreadsheet confirmation not yet implemented');
      clearPreview();
      return;
    }

    if (isTextImportResult(preview)) {
      // Text import always requires HIL - cannot auto-confirm
      throw new Error('Importações de texto requerem revisão manual antes de confirmar');
    }

    throw new Error('Tipo de preview desconhecido');
  }, [preview, queryClient, clearPreview]);

  /**
   * Assign a project to a pending entry.
   */
  const assignProject = useCallback(async (entryId: string, projectId: string): Promise<void> => {
    try {
      await assignProjectToEntry(entryId, projectId);
      // Invalidate pending entries to refresh the list
      queryClient.invalidateQueries({ queryKey: [PENDING_ENTRIES_KEY] });
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao atribuir projeto';
      throw new Error(message);
    }
  }, [queryClient]);

  return {
    detectedType,
    isProcessing,
    progress,
    error,
    preview,
    response,
    uploadAndProcess,
    clearPreview,
    confirmEntry,
    // Pending entries support
    pendingEntries: pendingEntriesData ?? [],
    pendingEntriesLoading,
    refreshPendingEntries,
    assignProject,
  };
}

// =============================================================================
// Helpers
// =============================================================================

/**
 * Get MIME content type for a detected file type.
 */
function getContentTypeForFileType(fileType: SmartFileType): string {
  const contentTypeMap: Record<SmartFileType, string> = {
    xml: 'application/xml',
    pdf: 'application/pdf',
    image: 'image/jpeg',
    csv: 'text/csv',
    xlsx: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    txt: 'text/plain',
    unknown: 'application/octet-stream',
  };

  return contentTypeMap[fileType] || 'application/octet-stream';
}

// =============================================================================
// Re-export types for convenience
// =============================================================================

export type {
  SmartFileType,
  SmartSourceType,
  SmartImportPreview,
  SmartImportProgress,
  UseSmartImporterReturn,
  SmartImportUploadResponse,
};

export {
  detectFileTypeFromFile,
  validateSmartImportFile,
  requiresHILReview,
  isNFImportResult,
  isSpreadsheetImportResult,
  isTextImportResult,
  getFileTypeLabel,
  SMART_IMPORT_FORMATS,
} from '@/lib/ativos/smartImportTypes';
