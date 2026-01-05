'use client';

// =============================================================================
// Entrada de Materiais Page - SGA Inventory Module
// =============================================================================
// Unified material entry page with multiple input sources:
// - NF-e (XML/PDF) - Electronic invoice processing
// - Foto/Imagem (JPEG/PNG) - OCR via Gemini Vision
// - SAP Export (CSV/XLSX) - Full asset import from ERP
// - Manual - Direct entry without source file
// =============================================================================

import { useState } from 'react';
import Link from 'next/link';
import { AnimatePresence, motion } from 'framer-motion';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import {
  ArrowLeft,
  FileText,
  Camera,
  FileSpreadsheet,
  PenLine,
  X,
  FolderPlus,
  CheckCircle2,
  RefreshCw,
  Briefcase,
} from 'lucide-react';
import { useNFReader, useAssetManagement } from '@/hooks/ativos';

// Tab Components
import {
  EntradaNFTab,
  EntradaImagemTab,
  EntradaSAPTab,
  EntradaManualTab,
  PendingEntriesList,
} from './components';

// =============================================================================
// Tab Types
// =============================================================================

type EntradaTab = 'nfe' | 'image' | 'sap' | 'manual';

// =============================================================================
// Page Component
// =============================================================================

export default function EntradaPage() {
  const [activeTab, setActiveTab] = useState<EntradaTab>('nfe');

  // NF-e Reader Hook (used for NF-e and Image tabs)
  const {
    isUploading,
    uploadProgress,
    uploadError,
    extraction,
    suggestedMappings,
    confidenceScore,
    entryId,
    requiresReview,
    requiresProject,
    pendingEntries,
    pendingEntriesLoading,
    uploadNF,
    confirmEntry,
    assignProject,
    clearExtraction,
    mappings,
    updateMapping,
  } = useNFReader();

  // Asset Management Hook for master data
  const { projects, locations, partNumbers } = useAssetManagement();

  // Project Assignment Modal state
  const [projectModalOpen, setProjectModalOpen] = useState(false);
  const [projectModalEntryId, setProjectModalEntryId] = useState<string | null>(null);
  const [projectModalProject, setProjectModalProject] = useState('');
  const [isAssigningProject, setIsAssigningProject] = useState(false);

  // SAP Import state (placeholder - will be replaced by useSAPImport hook)
  const [sapProcessing, setSapProcessing] = useState(false);
  const [sapProgress, setSapProgress] = useState(0);
  const [sapError, setSapError] = useState<string | null>(null);
  const [sapPreview, setSapPreview] = useState<any>(null);

  // Manual Entry state (placeholder - will be replaced by useManualEntry hook)
  const [manualProcessing, setManualProcessing] = useState(false);
  const [manualError, setManualError] = useState<string | null>(null);

  // Handle opening project assignment modal
  const openProjectModal = (entryId: string) => {
    setProjectModalEntryId(entryId);
    setProjectModalProject('');
    setProjectModalOpen(true);
  };

  // Handle project assignment
  const handleAssignProject = async () => {
    if (!projectModalEntryId || !projectModalProject) return;

    setIsAssigningProject(true);
    try {
      await assignProject(projectModalEntryId, projectModalProject);
      setProjectModalOpen(false);
      setProjectModalEntryId(null);
      setProjectModalProject('');
    } catch {
      // Error handling
    } finally {
      setIsAssigningProject(false);
    }
  };

  // Handle NF-e upload
  const handleNFUpload = async (file: File, projectId: string | null, locationId: string) => {
    await uploadNF(file, projectId, locationId);
  };

  // Handle NF-e confirm
  const handleNFConfirm = async () => {
    if (!entryId) return;
    await confirmEntry(entryId, mappings);
  };

  // Handle Image upload (uses same backend as NF-e for now)
  const handleImageUpload = async (file: File, projectId: string | null, locationId: string) => {
    // For now, use the same NF upload - backend will detect image type
    // TODO: Replace with dedicated useImageOCR hook
    await uploadNF(file, projectId, locationId);
  };

  // Handle SAP preview (placeholder)
  const handleSAPPreview = async (file: File, projectId?: string, locationId?: string) => {
    setSapProcessing(true);
    setSapProgress(0);
    setSapError(null);

    try {
      // Simulate progress
      for (let i = 0; i <= 100; i += 20) {
        await new Promise((resolve) => setTimeout(resolve, 200));
        setSapProgress(i);
      }

      // TODO: Replace with actual useSAPImport hook
      // For now, create a mock preview
      setSapPreview({
        filename: file.name,
        total_rows: 100,
        matched_rows: 85,
        unmatched_rows: 15,
        match_rate: 85,
        is_sap_format: true,
        columns_detected: [
          'source_system', 'sap_material_code', 'part_number', 'asset_type',
          'manufacturer', 'serial_number', 'rfid', 'quantity', 'project_id',
          'project_name', 'status', 'sap_depot_code', 'technician_name',
        ],
        sample_data: [
          {
            part_number: 'SW-CISCO-9200',
            serial_number: '0IFD0TVBDIVU',
            quantity: '1',
            project_name: 'Stock Faiston',
            status: 'EM_ESTOQUE',
            technician_name: '',
          },
          {
            part_number: 'AP-CISCO-R640',
            serial_number: '8MDD4V30T9NT',
            quantity: '1',
            project_name: 'Evotech',
            status: 'DESCARTE',
            technician_name: '',
          },
        ],
        projects_detected: ['FAISTON', 'EVOTEC', 'TRAGUE', 'NTT', 'ARCDOU'],
        locations_detected: ['Barueri - Recebimento', 'Barueri - Descarte', 'Base Tecnica - Rio'],
        assets_to_create: 100,
      });
    } catch (err) {
      setSapError(err instanceof Error ? err.message : 'Erro ao processar arquivo');
    } finally {
      setSapProcessing(false);
    }
  };

  // Handle SAP execute (placeholder)
  const handleSAPExecute = async () => {
    setSapProcessing(true);
    try {
      // TODO: Implement actual import
      await new Promise((resolve) => setTimeout(resolve, 2000));
      setSapPreview(null);
    } catch (err) {
      setSapError(err instanceof Error ? err.message : 'Erro na importacao');
    } finally {
      setSapProcessing(false);
    }
  };

  // Handle Manual submit (placeholder)
  const handleManualSubmit = async (params: any) => {
    setManualProcessing(true);
    setManualError(null);
    try {
      // TODO: Implement actual manual entry
      await new Promise((resolve) => setTimeout(resolve, 1000));
    } catch (err) {
      setManualError(err instanceof Error ? err.message : 'Erro ao registrar entrada');
    } finally {
      setManualProcessing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href="/ferramentas/ativos/estoque/movimentacoes">
                <ArrowLeft className="w-4 h-4 mr-1" />
                Movimentacoes
              </Link>
            </Button>
          </div>
          <h1 className="text-xl font-semibold text-text-primary">
            Entrada de Materiais
          </h1>
          <p className="text-sm text-text-muted mt-1">
            Internalizacao via NF-e, imagem, SAP ou entrada manual
          </p>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as EntradaTab)}>
        <TabsList className="w-full grid grid-cols-4 bg-white/5 p-1 rounded-lg">
          <TabsTrigger
            value="nfe"
            className="flex items-center gap-2 data-[state=active]:bg-green-500/20 data-[state=active]:text-green-400"
          >
            <FileText className="w-4 h-4" />
            <span className="hidden sm:inline">NF-e</span>
          </TabsTrigger>
          <TabsTrigger
            value="image"
            className="flex items-center gap-2 data-[state=active]:bg-magenta-mid/20 data-[state=active]:text-magenta-mid"
          >
            <Camera className="w-4 h-4" />
            <span className="hidden sm:inline">Foto/Imagem</span>
          </TabsTrigger>
          <TabsTrigger
            value="sap"
            className="flex items-center gap-2 data-[state=active]:bg-cyan-500/20 data-[state=active]:text-cyan-400"
          >
            <FileSpreadsheet className="w-4 h-4" />
            <span className="hidden sm:inline">SAP Export</span>
          </TabsTrigger>
          <TabsTrigger
            value="manual"
            className="flex items-center gap-2 data-[state=active]:bg-purple-500/20 data-[state=active]:text-purple-400"
          >
            <PenLine className="w-4 h-4" />
            <span className="hidden sm:inline">Manual</span>
          </TabsTrigger>
        </TabsList>

        {/* NF-e Tab Content */}
        <TabsContent value="nfe" className="mt-6">
          <EntradaNFTab
            isUploading={isUploading}
            uploadProgress={uploadProgress}
            uploadError={uploadError}
            extraction={extraction}
            confidenceScore={confidenceScore}
            entryId={entryId}
            requiresReview={requiresReview}
            requiresProject={requiresProject}
            projects={projects}
            locations={locations}
            onUpload={handleNFUpload}
            onConfirm={handleNFConfirm}
            onClear={clearExtraction}
            onAssignProject={openProjectModal}
            mappings={mappings}
            updateMapping={updateMapping}
          />
        </TabsContent>

        {/* Image Tab Content */}
        <TabsContent value="image" className="mt-6">
          <EntradaImagemTab
            isUploading={isUploading}
            uploadProgress={uploadProgress}
            uploadError={uploadError}
            extraction={extraction}
            confidenceScore={confidenceScore}
            entryId={entryId}
            requiresReview={requiresReview}
            requiresProject={requiresProject}
            projects={projects}
            locations={locations}
            onUpload={handleImageUpload}
            onConfirm={handleNFConfirm}
            onClear={clearExtraction}
            onAssignProject={openProjectModal}
          />
        </TabsContent>

        {/* SAP Tab Content */}
        <TabsContent value="sap" className="mt-6">
          <EntradaSAPTab
            isProcessing={sapProcessing}
            progress={sapProgress}
            error={sapError}
            preview={sapPreview}
            projects={projects}
            locations={locations}
            onPreview={handleSAPPreview}
            onExecute={handleSAPExecute}
            onClear={() => setSapPreview(null)}
          />
        </TabsContent>

        {/* Manual Tab Content */}
        <TabsContent value="manual" className="mt-6">
          <EntradaManualTab
            isProcessing={manualProcessing}
            error={manualError}
            projects={projects}
            locations={locations}
            partNumbers={partNumbers}
            onSubmit={handleManualSubmit}
            onClear={() => setManualError(null)}
          />
        </TabsContent>
      </Tabs>

      {/* Pending Entries (shown when no extraction in progress) */}
      {!extraction && pendingEntries.length > 0 && (
        <PendingEntriesList
          entries={pendingEntries}
          isLoading={pendingEntriesLoading}
          onAssignProject={openProjectModal}
          onReview={(id) => console.log('Review entry:', id)}
        />
      )}

      {/* Project Assignment Modal */}
      <AnimatePresence>
        {projectModalOpen && (
          <motion.div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => !isAssigningProject && setProjectModalOpen(false)}
          >
            <motion.div
              className="bg-surface-elevated border border-border rounded-xl p-6 w-full max-w-md mx-4 shadow-xl"
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
            >
              {/* Modal Header */}
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-orange-500/20 flex items-center justify-center">
                    <FolderPlus className="w-5 h-5 text-orange-400" />
                  </div>
                  <div>
                    <h3 className="text-lg font-semibold text-text-primary">
                      Atribuir Projeto
                    </h3>
                    <p className="text-xs text-text-muted">
                      Selecione o projeto para esta entrada
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => !isAssigningProject && setProjectModalOpen(false)}
                  className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                  disabled={isAssigningProject}
                >
                  <X className="w-5 h-5 text-text-muted" />
                </button>
              </div>

              {/* Project Selection */}
              <div className="mb-6">
                <label className="text-sm font-medium text-text-primary mb-2 block">
                  <Briefcase className="w-4 h-4 inline mr-2" />
                  Projeto
                </label>
                <select
                  className="w-full px-3 py-2 bg-white/5 border border-border rounded-md text-sm text-text-primary"
                  value={projectModalProject}
                  onChange={(e) => setProjectModalProject(e.target.value)}
                  disabled={isAssigningProject}
                >
                  <option value="">Selecione o projeto...</option>
                  {projects.filter(p => p.is_active).map((project) => (
                    <option key={project.id} value={project.id}>
                      {project.code} - {project.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Actions */}
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  className="flex-1"
                  onClick={() => setProjectModalOpen(false)}
                  disabled={isAssigningProject}
                >
                  Cancelar
                </Button>
                <Button
                  className="flex-1 bg-orange-500 hover:bg-orange-600"
                  onClick={handleAssignProject}
                  disabled={!projectModalProject || isAssigningProject}
                >
                  {isAssigningProject ? (
                    <>
                      <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                      Atribuindo...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-4 h-4 mr-2" />
                      Atribuir Projeto
                    </>
                  )}
                </Button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
