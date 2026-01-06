// =============================================================================
// useSmartImportNexo Hook - NEXO Intelligent Import (Agentic AI-First)
// =============================================================================
// Manages the intelligent import flow using the ReAct pattern:
// OBSERVE → THINK → ASK → LEARN → ACT
//
// Philosophy: NEXO guides user through import with intelligent analysis
// - Multi-sheet XLSX analysis with purpose detection
// - Clarification questions when uncertain
// - Learning from user answers for future imports
// - Explicit reasoning trace for transparency
//
// This hook orchestrates the 5-phase flow defined in the plan.
// =============================================================================

'use client';

import { useState, useCallback, useMemo } from 'react';
import {
  nexoAnalyzeFile,
  nexoGetQuestions,
  nexoSubmitAnswers,
  nexoLearnFromImport,
  nexoPrepareProcessing,
  nexoGetPriorKnowledge,
  nexoGetAdaptiveThreshold,
  getNFUploadUrl,
  executeImport,
  clearSGASession,
  type NexoAnalyzeFileResponse,
  type NexoQuestion,
  type NexoColumnMapping,
  type NexoReasoningStep,
  type NexoSheetAnalysis,
  type NexoProcessingConfig,
  type NexoPriorKnowledge,
} from '@/services/sgaAgentcore';

// =============================================================================
// Types
// =============================================================================

/**
 * Current stage in the NEXO intelligent import flow.
 */
export type NexoImportStage =
  | 'idle'           // No import in progress
  | 'uploading'      // Uploading file to S3
  | 'recalling'      // NEXO recalling prior knowledge (RECALL)
  | 'analyzing'      // NEXO analyzing file (OBSERVE + THINK)
  | 'questioning'    // Waiting for user answers (ASK)
  | 'reviewing'      // NEXO shows summary for user approval (HIL)
  | 'processing'     // Preparing final configuration (ACT)
  | 'importing'      // Executing the import
  | 'learning'       // Storing learned patterns (LEARN)
  | 'complete'       // Import completed successfully
  | 'error';         // Error occurred

/**
 * Progress state for the import flow.
 */
export interface NexoImportProgress {
  stage: NexoImportStage;
  percent: number;
  message: string;
  currentStep?: string;
}

/**
 * Analysis result from NEXO.
 */
export interface NexoAnalysisResult {
  sessionId: string;
  filename: string;
  detectedType: string;
  sheets: NexoSheetAnalysis[];
  columnMappings: NexoColumnMapping[];
  overallConfidence: number;
  recommendedStrategy: string;
  reasoningTrace: NexoReasoningStep[];
}

/**
 * Review summary shown before final import approval.
 */
export interface NexoReviewSummary {
  filename: string;
  mainSheet: string;
  totalItems: number;
  projectName: string | null;
  newPartNumbers: number;
  validations: string[];
  warnings: string[];
  recommendation: string;
  readyToImport: boolean;
  userFeedback: string | null;
}

/**
 * State of the NEXO intelligent import.
 */
export interface NexoImportState {
  stage: NexoImportStage;
  progress: NexoImportProgress;
  analysis: NexoAnalysisResult | null;
  questions: NexoQuestion[];
  answers: Record<string, string>;
  processingConfig: NexoProcessingConfig | null;
  priorKnowledge: NexoPriorKnowledge | null;
  adaptiveThreshold: number;
  reviewSummary: NexoReviewSummary | null;
  userFeedback: string | null;
  error: string | null;
}

/**
 * Return type for the hook.
 */
export interface UseSmartImportNexoReturn {
  // State
  state: NexoImportState;
  isAnalyzing: boolean;
  isRecalling: boolean;
  hasQuestions: boolean;
  isReadyToProcess: boolean;
  isReviewing: boolean;

  // Actions
  startAnalysis: (file: File) => Promise<NexoAnalysisResult>;
  answerQuestion: (questionId: string, answer: string) => void;
  submitAllAnswers: (userFeedback?: string) => Promise<void>;
  skipQuestions: () => Promise<void>;
  approveAndImport: () => Promise<void>;
  backToQuestions: () => void;
  prepareProcessing: () => Promise<NexoProcessingConfig>;
  executeNexoImport: (projectId?: string, locationId?: string) => Promise<void>;
  learnFromResult: (result: Record<string, unknown>, corrections?: Record<string, unknown>) => Promise<void>;
  reset: () => void;

  // Reasoning trace (for UI display)
  reasoningTrace: NexoReasoningStep[];
  currentThought: string | null;

  // Prior knowledge from episodic memory
  priorKnowledge: NexoPriorKnowledge | null;

  // Review summary for approval step
  reviewSummary: NexoReviewSummary | null;
}

// =============================================================================
// Initial State
// =============================================================================

const INITIAL_PROGRESS: NexoImportProgress = {
  stage: 'idle',
  percent: 0,
  message: '',
};

const INITIAL_STATE: NexoImportState = {
  stage: 'idle',
  progress: INITIAL_PROGRESS,
  analysis: null,
  questions: [],
  answers: {},
  processingConfig: null,
  priorKnowledge: null,
  adaptiveThreshold: 0.75, // Default confidence threshold
  reviewSummary: null,
  userFeedback: null,
  error: null,
};

// =============================================================================
// Hook Implementation
// =============================================================================

export function useSmartImportNexo(): UseSmartImportNexoReturn {
  const [state, setState] = useState<NexoImportState>(INITIAL_STATE);

  // ==========================================================================
  // Derived State
  // ==========================================================================

  const isAnalyzing = useMemo(
    () => state.stage === 'analyzing',
    [state.stage]
  );

  const isRecalling = useMemo(
    () => state.stage === 'recalling',
    [state.stage]
  );

  const hasQuestions = useMemo(
    () => state.questions.length > 0 && state.stage === 'questioning',
    [state.questions, state.stage]
  );

  const isReadyToProcess = useMemo(
    () =>
      state.analysis !== null &&
      (state.questions.length === 0 ||
        Object.keys(state.answers).length >= state.questions.filter(q => q.importance === 'critical').length),
    [state.analysis, state.questions, state.answers]
  );

  const currentThought = useMemo(() => {
    if (!state.analysis?.reasoningTrace) return null;
    const thoughts = state.analysis.reasoningTrace.filter(s => s.type === 'thought');
    return thoughts.length > 0 ? thoughts[thoughts.length - 1].content : null;
  }, [state.analysis?.reasoningTrace]);

  const isReviewing = useMemo(
    () => state.stage === 'reviewing',
    [state.stage]
  );

  // ==========================================================================
  // Helper: Update Progress
  // ==========================================================================

  const updateProgress = useCallback((
    stage: NexoImportStage,
    percent: number,
    message: string,
    currentStep?: string
  ) => {
    setState(prev => ({
      ...prev,
      stage,
      progress: { stage, percent, message, currentStep },
    }));
  }, []);

  // ==========================================================================
  // Action: Start Analysis (OBSERVE + THINK)
  // ==========================================================================

  const startAnalysis = useCallback(async (file: File): Promise<NexoAnalysisResult> => {
    updateProgress('uploading', 5, 'Preparando upload...', 'upload');

    // Clear session to force cold start with latest code
    clearSGASession();

    try {
      // Step 1: Get presigned URL
      updateProgress('uploading', 10, 'Obtendo URL de upload...');

      const contentType = file.type || 'application/octet-stream';
      const urlResult = await getNFUploadUrl({
        filename: file.name,
        content_type: contentType,
      });

      if (!urlResult.data?.upload_url || !urlResult.data?.s3_key) {
        throw new Error('Falha ao obter URL de upload');
      }

      // Step 2: Upload file to S3
      updateProgress('uploading', 30, 'Enviando arquivo...');

      const uploadResponse = await fetch(urlResult.data.upload_url, {
        method: 'PUT',
        body: file,
        headers: { 'Content-Type': contentType },
      });

      if (!uploadResponse.ok) {
        throw new Error('Falha no upload do arquivo');
      }

      // Step 3: RECALL - Fetch prior knowledge from episodic memory
      updateProgress('recalling', 35, 'NEXO consultando memória...', 'recall');

      let priorKnowledge: NexoPriorKnowledge | null = null;
      let adaptiveThreshold = 0.75;

      try {
        // Fetch prior knowledge (non-blocking, failure is OK)
        const priorResult = await nexoGetPriorKnowledge({ filename: file.name });
        if (priorResult.data?.success && priorResult.data?.has_prior_knowledge) {
          priorKnowledge = priorResult.data.prior_knowledge;
          console.log('[NEXO] Prior knowledge retrieved:', priorKnowledge);
        }

        // Fetch adaptive threshold
        const thresholdResult = await nexoGetAdaptiveThreshold({ filename: file.name });
        if (thresholdResult.data?.success) {
          adaptiveThreshold = thresholdResult.data.threshold;
          console.log('[NEXO] Adaptive threshold:', adaptiveThreshold, thresholdResult.data.reason);
        }
      } catch (recallError) {
        // Prior knowledge retrieval failure is not critical
        console.warn('[NEXO] Prior knowledge retrieval failed (continuing):', recallError);
      }

      // Update state with prior knowledge
      setState(prev => ({
        ...prev,
        priorKnowledge,
        adaptiveThreshold,
      }));

      // Step 4: NEXO Analysis (OBSERVE + THINK)
      updateProgress('analyzing', 50, 'NEXO analisando arquivo...', 'observe');

      const analysisResult = await nexoAnalyzeFile({
        s3_key: urlResult.data.s3_key,
        filename: file.name,
        content_type: contentType,
        prior_knowledge: priorKnowledge ? {
          suggested_mappings: priorKnowledge.suggested_mappings,
          confidence_boost: priorKnowledge.confidence_boost,
          reflections: priorKnowledge.reflections,
        } : undefined,
      });

      if (!analysisResult.data?.success) {
        const errorMsg = analysisResult.data?.error || 'Falha na análise (sem detalhes)';
        console.error('[NEXO] Analysis failed with error:', errorMsg, analysisResult.data);
        throw new Error(errorMsg);
      }

      const data = analysisResult.data as NexoAnalyzeFileResponse;

      // Build analysis result
      const analysis: NexoAnalysisResult = {
        sessionId: data.import_session_id,
        filename: data.filename,
        detectedType: data.detected_file_type,
        sheets: data.analysis.sheets,
        columnMappings: data.column_mappings,
        overallConfidence: data.overall_confidence,
        recommendedStrategy: data.analysis.recommended_strategy,
        reasoningTrace: data.reasoning_trace,
      };

      // Check if we have questions
      const hasQuestionsToAsk = data.questions && data.questions.length > 0;

      if (hasQuestionsToAsk) {
        updateProgress('questioning', 70, 'NEXO tem perguntas para você...', 'ask');
        setState(prev => ({
          ...prev,
          stage: 'questioning',
          analysis,
          questions: data.questions,
          progress: { stage: 'questioning', percent: 70, message: 'Aguardando suas respostas...', currentStep: 'ask' },
        }));
      } else {
        // No questions - ready to process
        updateProgress('processing', 80, 'Preparando para processamento...', 'act');
        setState(prev => ({
          ...prev,
          stage: 'processing',
          analysis,
          questions: [],
          progress: { stage: 'processing', percent: 80, message: 'Pronto para processar', currentStep: 'act' },
        }));
      }

      return analysis;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro na análise';
      setState(prev => ({
        ...prev,
        stage: 'error',
        error: message,
        progress: { stage: 'error', percent: 0, message },
      }));
      throw err;
    }
  }, [updateProgress]);

  // ==========================================================================
  // Action: Answer Question
  // ==========================================================================

  const answerQuestion = useCallback((questionId: string, answer: string) => {
    setState(prev => ({
      ...prev,
      answers: { ...prev.answers, [questionId]: answer },
    }));
  }, []);

  // ==========================================================================
  // Action: Submit All Answers
  // ==========================================================================

  const submitAllAnswers = useCallback(async (userFeedback?: string) => {
    if (!state.analysis?.sessionId) {
      throw new Error('Nenhuma sessão de importação ativa');
    }

    updateProgress('processing', 75, 'Processando respostas...', 'learn');

    try {
      const result = await nexoSubmitAnswers({
        import_session_id: state.analysis.sessionId,
        answers: state.answers,
      });

      if (!result.data?.success) {
        // Extract error message from backend response
        const errorMsg = result.data?.error
          || 'Sessão expirada. Por favor, faça upload do arquivo novamente.';
        throw new Error(errorMsg);
      }

      // Check if more questions remain
      if (result.data.remaining_questions && result.data.remaining_questions.length > 0) {
        setState(prev => ({
          ...prev,
          questions: result.data!.remaining_questions,
          progress: { stage: 'questioning', percent: 75, message: 'Mais perguntas...', currentStep: 'ask' },
        }));
      } else {
        // Generate client-side review summary for HIL approval
        const mainSheet = state.analysis.sheets.find(s => s.purpose === 'items') || state.analysis.sheets[0];
        const projectAnswer = state.answers['project'] || state.answers['projeto'] || null;

        // Count high confidence mappings as validations
        const highConfMappings = state.analysis.columnMappings.filter(m => m.confidence >= 0.8);
        const lowConfMappings = state.analysis.columnMappings.filter(m => m.confidence < 0.5);

        const reviewSummary: NexoReviewSummary = {
          filename: state.analysis.filename,
          mainSheet: mainSheet?.name || 'Desconhecida',
          totalItems: mainSheet?.row_count || 0,
          projectName: projectAnswer,
          newPartNumbers: 0, // Will be calculated by backend
          validations: [
            `${highConfMappings.length} colunas mapeadas com alta confiança`,
            'Estrutura do arquivo validada',
            mainSheet ? `Aba principal identificada: ${mainSheet.name}` : '',
          ].filter(Boolean),
          warnings: lowConfMappings.length > 0
            ? [`${lowConfMappings.length} colunas com baixa confiança (usando valores padrão)`]
            : [],
          recommendation: 'Acho que está tudo certo! Podemos prosseguir com a importação.',
          readyToImport: true,
          userFeedback: userFeedback || null,
        };

        // Go to reviewing stage for HIL approval
        updateProgress('reviewing', 80, 'Aguardando aprovação', 'review');
        setState(prev => ({
          ...prev,
          stage: 'reviewing',
          questions: [],
          reviewSummary,
          userFeedback: userFeedback || null,
        }));
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao processar respostas';
      setState(prev => ({ ...prev, error: message }));
      throw err;
    }
  }, [state.analysis, state.answers, updateProgress]);

  // ==========================================================================
  // Action: Skip Questions (use default answers)
  // ==========================================================================

  const skipQuestions = useCallback(async () => {
    if (!state.analysis?.sessionId) {
      throw new Error('Nenhuma sessão de importação ativa');
    }

    // Auto-fill with default values
    const defaultAnswers: Record<string, string> = {};
    state.questions.forEach(q => {
      if (q.default_value) {
        defaultAnswers[q.id] = q.default_value;
      } else if (q.options.length > 0) {
        defaultAnswers[q.id] = q.options[0].value;
      }
    });

    setState(prev => ({ ...prev, answers: { ...prev.answers, ...defaultAnswers } }));

    // Submit with defaults
    await submitAllAnswers();
  }, [state.analysis?.sessionId, state.questions, submitAllAnswers]);

  // ==========================================================================
  // Action: Back to Questions (from review screen)
  // ==========================================================================

  const backToQuestions = useCallback((): void => {
    // Go back to questioning stage to allow user to modify answers
    updateProgress('questioning', 70, 'Revise suas respostas...', 'ask');
    setState(prev => ({
      ...prev,
      stage: 'questioning',
      reviewSummary: null,
      // Keep answers and questions so user can modify them
    }));
  }, [updateProgress]);

  // ==========================================================================
  // Action: Prepare Processing (ACT)
  // ==========================================================================

  const prepareProcessing = useCallback(async (): Promise<NexoProcessingConfig> => {
    if (!state.analysis?.sessionId) {
      throw new Error('Nenhuma sessão de importação ativa');
    }

    updateProgress('processing', 85, 'Preparando configuração final...', 'act');

    try {
      const result = await nexoPrepareProcessing(state.analysis.sessionId);

      if (!result.data?.success || !result.data?.ready) {
        throw new Error('Configuração não está pronta');
      }

      setState(prev => ({
        ...prev,
        processingConfig: result.data!,
        progress: { stage: 'processing', percent: 90, message: 'Configuração pronta!', currentStep: 'act' },
      }));

      return result.data;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro ao preparar processamento';
      setState(prev => ({ ...prev, error: message }));
      throw err;
    }
  }, [state.analysis?.sessionId, updateProgress]);

  // ==========================================================================
  // Action: Execute NEXO Import
  // ==========================================================================

  const executeNexoImport = useCallback(async (
    projectId?: string,
    locationId?: string
  ): Promise<void> => {
    if (!state.analysis?.sessionId || !state.processingConfig) {
      throw new Error('Preparação não concluída');
    }

    updateProgress('importing', 92, 'Executando importação...', 'act');

    try {
      const result = await executeImport({
        import_id: state.analysis.sessionId,
        file_content_base64: '', // Already uploaded to S3
        filename: state.analysis.filename,
        column_mappings: state.processingConfig.column_mappings,
        project_id: projectId,
        destination_location_id: locationId,
      });

      if (!result.data?.success) {
        const errorMsg = result.data?.error
          || (result.data?.failed_rows && result.data.failed_rows.length > 0
            ? result.data.failed_rows.map(r => r.reason).join(', ')
            : 'Falha na importação');
        throw new Error(errorMsg);
      }

      updateProgress('complete', 100, 'Importação concluída!', 'complete');
      setState(prev => ({
        ...prev,
        stage: 'complete',
      }));
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Erro na importação';
      setState(prev => ({
        ...prev,
        stage: 'error',
        error: message,
        progress: { stage: 'error', percent: 0, message },
      }));
      throw err;
    }
  }, [state.analysis, state.processingConfig, updateProgress]);

  // ==========================================================================
  // Action: Learn From Result (LEARN)
  // ==========================================================================

  const learnFromResult = useCallback(async (
    result: Record<string, unknown>,
    corrections?: Record<string, unknown>
  ): Promise<void> => {
    if (!state.analysis?.sessionId) {
      return; // Silent return if no session
    }

    updateProgress('learning', 95, 'NEXO aprendendo com este importação...', 'learn');

    try {
      await nexoLearnFromImport({
        import_session_id: state.analysis.sessionId,
        import_result: result,
        user_corrections: corrections,
      });

      console.log('[NEXO] Aprendizado concluído');
    } catch (err) {
      // Learning failure is not critical - just log it
      console.warn('[NEXO] Falha ao aprender:', err);
    }
  }, [state.analysis?.sessionId, updateProgress]);

  // ==========================================================================
  // Action: Approve and Import (HIL - Human-in-the-Loop approval)
  // ==========================================================================

  const approveAndImport = useCallback(async (): Promise<void> => {
    if (!state.analysis?.sessionId || !state.reviewSummary) {
      throw new Error('Nenhuma sessão de revisão ativa');
    }

    // User approved - proceed to processing
    updateProgress('processing', 85, 'Preparando importação...', 'act');
    setState(prev => ({
      ...prev,
      stage: 'processing',
    }));

    // Prepare processing configuration
    await prepareProcessing();

    // Execute the import
    await executeNexoImport(
      state.answers['project'] || state.answers['projeto'] || undefined,
      state.answers['location'] || state.answers['local'] || undefined
    );

    // Learn from this import for future improvements
    await learnFromResult(
      { success: true, items_imported: state.reviewSummary.totalItems },
      state.userFeedback ? { user_feedback: state.userFeedback } : undefined
    );
  }, [
    state.analysis?.sessionId,
    state.reviewSummary,
    state.answers,
    state.userFeedback,
    updateProgress,
    prepareProcessing,
    executeNexoImport,
    learnFromResult,
  ]);

  // ==========================================================================
  // Action: Reset
  // ==========================================================================

  const reset = useCallback(() => {
    setState(INITIAL_STATE);
  }, []);

  // ==========================================================================
  // Return
  // ==========================================================================

  return {
    // State
    state,
    isAnalyzing,
    isRecalling,
    hasQuestions,
    isReadyToProcess,
    isReviewing,

    // Actions
    startAnalysis,
    answerQuestion,
    submitAllAnswers,
    skipQuestions,
    approveAndImport,
    backToQuestions,
    prepareProcessing,
    executeNexoImport,
    learnFromResult,
    reset,

    // Reasoning trace (for UI display)
    reasoningTrace: state.analysis?.reasoningTrace || [],
    currentThought,

    // Prior knowledge from episodic memory
    priorKnowledge: state.priorKnowledge,

    // Review summary for approval step
    reviewSummary: state.reviewSummary,
  };
}

// =============================================================================
// Re-export Types
// =============================================================================

export type {
  NexoQuestion,
  NexoColumnMapping,
  NexoReasoningStep,
  NexoSheetAnalysis,
  NexoProcessingConfig,
  NexoPriorKnowledge,
};
