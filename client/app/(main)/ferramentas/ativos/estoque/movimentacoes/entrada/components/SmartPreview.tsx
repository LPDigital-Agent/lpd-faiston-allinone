'use client';

// =============================================================================
// SmartPreview - Preview Router Component
// =============================================================================
// Routes to the appropriate preview component based on source_type.
// This is the entry point for displaying smart import results.
// =============================================================================

import { useState } from 'react';
import type { SmartImportPreview, SmartSourceType } from '@/lib/ativos/smartImportTypes';
import {
  isNFImportResult,
  isSpreadsheetImportResult,
  isTextImportResult,
} from '@/lib/ativos/smartImportTypes';
import { NFPreview } from './previews/NFPreview';
import { SpreadsheetPreview } from './previews/SpreadsheetPreview';
import { TextPreview } from './previews/TextPreview';
import {
  GlassCard,
  GlassCardHeader,
  GlassCardTitle,
  GlassCardContent,
} from '@/components/shared/glass-card';
import { AlertTriangle, FileQuestion } from 'lucide-react';
import { Button } from '@/components/ui/button';

// =============================================================================
// Types
// =============================================================================

interface SmartPreviewProps {
  preview: SmartImportPreview;
  onConfirm: () => Promise<void>;
  onCancel: () => void;
}

// =============================================================================
// Component
// =============================================================================

export function SmartPreview({
  preview,
  onConfirm,
  onCancel,
}: SmartPreviewProps) {
  const [isConfirming, setIsConfirming] = useState(false);

  // Handle confirm with loading state
  const handleConfirm = async () => {
    setIsConfirming(true);
    try {
      await onConfirm();
    } finally {
      setIsConfirming(false);
    }
  };

  // Route to appropriate preview based on source_type
  if (isNFImportResult(preview)) {
    return (
      <NFPreview
        preview={preview}
        onConfirm={handleConfirm}
        onCancel={onCancel}
        isConfirming={isConfirming}
      />
    );
  }

  if (isSpreadsheetImportResult(preview)) {
    return (
      <SpreadsheetPreview
        preview={preview}
        onConfirm={handleConfirm}
        onCancel={onCancel}
        isConfirming={isConfirming}
      />
    );
  }

  if (isTextImportResult(preview)) {
    return (
      <TextPreview
        preview={preview}
        onConfirm={handleConfirm}
        onCancel={onCancel}
        isConfirming={isConfirming}
      />
    );
  }

  // Fallback for unknown preview types (this shouldn't happen with proper typing)
  // Cast to SmartImportPreview to access source_type for the error display
  const unknownPreview = preview as SmartImportPreview;
  return (
    <UnknownPreview
      sourceType={unknownPreview.source_type}
      onCancel={onCancel}
    />
  );
}

// =============================================================================
// Fallback Component
// =============================================================================

interface UnknownPreviewProps {
  sourceType: SmartSourceType;
  onCancel: () => void;
}

function UnknownPreview({ sourceType, onCancel }: UnknownPreviewProps) {
  return (
    <GlassCard>
      <GlassCardHeader>
        <div className="flex items-center gap-2">
          <FileQuestion className="w-4 h-4 text-yellow-400" />
          <GlassCardTitle>Preview Nao Disponivel</GlassCardTitle>
        </div>
      </GlassCardHeader>

      <GlassCardContent>
        <div className="text-center py-8">
          <AlertTriangle className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
          <p className="text-sm text-text-primary mb-2">
            Tipo de preview desconhecido
          </p>
          <p className="text-xs text-text-muted mb-6">
            O tipo de fonte "{sourceType}" nao possui um preview implementado.
          </p>
          <Button variant="outline" onClick={onCancel}>
            Voltar
          </Button>
        </div>
      </GlassCardContent>
    </GlassCard>
  );
}
