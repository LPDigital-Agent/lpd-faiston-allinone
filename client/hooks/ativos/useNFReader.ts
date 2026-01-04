// =============================================================================
// useNFReader Hook - SGA Inventory Module
// =============================================================================
// NF-e (Nota Fiscal Eletronica) upload and processing.
// Handles file upload, extraction, and entry confirmation.
// =============================================================================

'use client';

import { useState, useCallback } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  getNFUploadUrl,
  processNFUpload,
  confirmNFEntry,
  getPendingNFEntries,
} from '@/services/sgaAgentcore';
import type {
  NFExtraction,
  NFItemMapping,
  PendingNFEntry,
  SGAProcessNFUploadResponse,
  SGAConfirmNFEntryResponse,
  ConfidenceScore,
} from '@/lib/ativos/types';

// =============================================================================
// Types
// =============================================================================

interface UseNFReaderReturn {
  // Upload state
  isUploading: boolean;
  uploadProgress: number;
  uploadError: string | null;

  // Extraction state
  extraction: NFExtraction | null;
  suggestedMappings: NFItemMapping[];
  confidenceScore: ConfidenceScore | null;
  entryId: string | null;
  requiresReview: boolean;

  // Pending entries
  pendingEntries: PendingNFEntry[];
  pendingEntriesLoading: boolean;
  refreshPendingEntries: () => void;

  // Actions
  uploadNF: (file: File, projectId: string, destinationLocationId: string) => Promise<SGAProcessNFUploadResponse>;
  confirmEntry: (entryId: string, itemMappings: NFItemMapping[], notes?: string) => Promise<SGAConfirmNFEntryResponse>;
  clearExtraction: () => void;

  // Item mapping helpers
  updateMapping: (index: number, mapping: Partial<NFItemMapping>) => void;
  mappings: NFItemMapping[];
}

// =============================================================================
// Query Keys
// =============================================================================

const PENDING_ENTRIES_KEY = 'sga-pending-nf-entries';

// =============================================================================
// Hook
// =============================================================================

export function useNFReader(): UseNFReaderReturn {
  const queryClient = useQueryClient();

  // Upload state
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);

  // Extraction state
  const [extraction, setExtraction] = useState<NFExtraction | null>(null);
  const [suggestedMappings, setSuggestedMappings] = useState<NFItemMapping[]>([]);
  const [mappings, setMappings] = useState<NFItemMapping[]>([]);
  const [confidenceScore, setConfidenceScore] = useState<ConfidenceScore | null>(null);
  const [entryId, setEntryId] = useState<string | null>(null);
  const [requiresReview, setRequiresReview] = useState(false);

  // Fetch pending entries
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
  });

  // Upload NF file
  const uploadNF = useCallback(async (
    file: File,
    projectId: string,
    destinationLocationId: string
  ): Promise<SGAProcessNFUploadResponse> => {
    setIsUploading(true);
    setUploadProgress(0);
    setUploadError(null);

    try {
      // 1. Get presigned URL
      setUploadProgress(10);
      const fileType = file.name.toLowerCase().endsWith('.xml') ? 'xml' : 'pdf';
      const urlResult = await getNFUploadUrl({
        filename: file.name,
        content_type: file.type || (fileType === 'xml' ? 'application/xml' : 'application/pdf'),
      });

      // 2. Upload to S3
      setUploadProgress(30);
      const uploadResponse = await fetch(urlResult.data.upload_url, {
        method: 'PUT',
        body: file,
        headers: {
          'Content-Type': file.type || (fileType === 'xml' ? 'application/xml' : 'application/pdf'),
        },
      });

      if (!uploadResponse.ok) {
        throw new Error('Falha no upload do arquivo');
      }

      // 3. Process NF
      setUploadProgress(60);
      const processResult = await processNFUpload({
        s3_key: urlResult.data.s3_key,
        file_type: fileType,
        project_id: projectId,
        destination_location_id: destinationLocationId,
      });

      setUploadProgress(100);

      // Update state
      setExtraction(processResult.data.extraction);
      setSuggestedMappings(processResult.data.suggested_mappings);
      setMappings(processResult.data.suggested_mappings);
      setConfidenceScore(processResult.data.confidence_score);
      setEntryId(processResult.data.entry_id);
      setRequiresReview(processResult.data.requires_review);

      // Refresh pending entries
      refreshPendingEntries();

      return processResult.data;
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Erro ao processar NF';
      setUploadError(message);
      throw error;
    } finally {
      setIsUploading(false);
    }
  }, [refreshPendingEntries]);

  // Confirm entry mutation
  const confirmEntryMutation = useMutation({
    mutationFn: async ({
      entryId,
      itemMappings,
      notes,
    }: {
      entryId: string;
      itemMappings: NFItemMapping[];
      notes?: string;
    }) => {
      const result = await confirmNFEntry({
        entry_id: entryId,
        item_mappings: itemMappings,
        notes,
      });
      return result.data;
    },
    onSuccess: () => {
      // Clear extraction state
      clearExtraction();
      // Refresh pending entries
      refreshPendingEntries();
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: ['sga-assets'] });
      queryClient.invalidateQueries({ queryKey: ['sga-balance'] });
      queryClient.invalidateQueries({ queryKey: ['sga-movements'] });
    },
  });

  // Confirm entry wrapper
  const confirmEntry = useCallback(async (
    entryId: string,
    itemMappings: NFItemMapping[],
    notes?: string
  ): Promise<SGAConfirmNFEntryResponse> => {
    return confirmEntryMutation.mutateAsync({ entryId, itemMappings, notes });
  }, [confirmEntryMutation]);

  // Clear extraction state
  const clearExtraction = useCallback(() => {
    setExtraction(null);
    setSuggestedMappings([]);
    setMappings([]);
    setConfidenceScore(null);
    setEntryId(null);
    setRequiresReview(false);
    setUploadError(null);
    setUploadProgress(0);
  }, []);

  // Update mapping
  const updateMapping = useCallback((index: number, mapping: Partial<NFItemMapping>) => {
    setMappings(prev =>
      prev.map((m, i) => (i === index ? { ...m, ...mapping } : m))
    );
  }, []);

  return {
    isUploading,
    uploadProgress,
    uploadError,
    extraction,
    suggestedMappings,
    confidenceScore,
    entryId,
    requiresReview,
    pendingEntries: pendingEntriesData ?? [],
    pendingEntriesLoading,
    refreshPendingEntries,
    uploadNF,
    confirmEntry,
    clearExtraction,
    updateMapping,
    mappings,
  };
}

// Re-export types
export type { NFExtraction, NFItemMapping, PendingNFEntry, ConfidenceScore };
