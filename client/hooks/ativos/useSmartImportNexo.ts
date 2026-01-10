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
  type NexoSessionState,  // STATELESS: Full session state type
} from '@/services/sgaAgentcore';

// =============================================================================
// Constants - Rotating Messages for Re-Analysis (Phase 3 fix)
// =============================================================================

/**
 * Rotating loading messages shown during re-analysis with Gemini.
 * User sees these while waiting 15-30 seconds for AI processing.
 */
const RE_ANALYZING_MESSAGES = [
  'NEXO refinando mapeamentos...',
  'Validando contra schema PostgreSQL...',
  'Aplicando suas respostas...',
  'Reavaliando confiança...',
  'Verificando colunas obrigatórias...',
  'Consultando padrões aprendidos...',
  'Analisando consistência dos dados...',
  'Confirmando tipos de dados...',
];

/**
 * Extract human-readable message from validation error.
 * Backend returns objects like { field, message, severity } but we need just the message.
 */
const formatValidationError = (error: unknown): string => {
  if (typeof error === 'string') return error;
  if (typeof error === 'object' && error !== null && 'message' in error) {
    return (error as { message: string }).message;
  }
  return String(error);
};

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
  | 're-analyzing'   // NEXO re-analyzing with user answers (RE-THINK) - Phase 3 fix
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
 * New column requested for dynamic schema evolution.
 */
export interface NexoNewColumn {
  name: string;
  originalName: string;
  userIntent: string;
  inferredType: string;
  sourceFileColumn: string;
  approved: boolean;
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
  // Aggregation config (January 2026) - when CSV has no quantity column
  aggregation?: {
    enabled: boolean;
    strategy: string;
    uniqueParts: number;
    totalRows: number;
    partNumberColumn?: string;
  } | null;
  // New columns for dynamic schema evolution (January 2026)
  // These are columns that will be created in the database
  newColumns?: NexoNewColumn[];
}

/**
 * State of the NEXO intelligent import.
 * STATELESS ARCHITECTURE: Stores full session state for passing to backend.
 */
export interface NexoImportState {
  stage: NexoImportStage;
  progress: NexoImportProgress;
  analysis: NexoAnalysisResult | null;
  sessionState: NexoSessionState | null;  // STATELESS: Full session state
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
  submitAllAnswers: (userFeedback?: string, overrideAnswers?: Record<string, string>) => Promise<void>;
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
  sessionState: null,  // STATELESS: Full session state
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
          console.log('[NEXO] Adaptive threshold:', adaptiveThreshold, thresholdResult.data.reason || '(default)');
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

      // STATELESS: Build session state from response (or use returned session_state)
      // NOTE: stage MUST be a valid Python ImportStage enum value:
      // analyzing, reasoning, questioning, awaiting, learning, processing, complete
      const sessionState: NexoSessionState = data.session_state || {
        session_id: data.import_session_id,
        filename: data.filename,
        s3_key: urlResult.data.s3_key,
        stage: data.questions && data.questions.length > 0 ? 'questioning' : 'processing',
        file_analysis: {
          sheets: data.analysis.sheets,
          sheet_count: data.analysis.sheet_count,
          total_rows: data.analysis.total_rows,
          detected_type: data.detected_file_type,
          recommended_strategy: data.analysis.recommended_strategy,
        },
        reasoning_trace: data.reasoning_trace,
        questions: data.questions,
        answers: {},
        learned_mappings: {},
        // FIX (January 2026): Initialize ai_instructions for "Outros:" answers
        ai_instructions: {},
        // FEATURE (January 2026): Initialize requested_new_columns for dynamic schema
        requested_new_columns: [],
        column_mappings: data.column_mappings.reduce((acc, m) => {
          acc[m.file_column] = m.target_field;
          return acc;
        }, {} as Record<string, string>),
        // NOTE: confidence format MUST match Python ConfidenceScore dataclass:
        // overall, extraction_quality, evidence_strength, historical_match, risk_level, factors, requires_hil
        confidence: {
          overall: data.overall_confidence,
          extraction_quality: 1.0,
          evidence_strength: 1.0,
          historical_match: 1.0,
          risk_level: data.overall_confidence >= 0.8 ? 'low' : data.overall_confidence >= 0.5 ? 'medium' : 'high',
          factors: [],
          requires_hil: data.overall_confidence < 0.6,
        },
        error: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      // Check if we have questions
      const hasQuestionsToAsk = data.questions && data.questions.length > 0;

      if (hasQuestionsToAsk) {
        updateProgress('questioning', 70, 'NEXO tem perguntas para você...', 'ask');
        setState(prev => ({
          ...prev,
          stage: 'questioning',
          analysis,
          sessionState,  // STATELESS: Store full session state
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
          sessionState,  // STATELESS: Store full session state
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
  // FIX (January 2026): Added overrideAnswers parameter to fix "__other__" race condition
  // When user selects "Outros" option, the value "__other__" was being sent to backend
  // because React state updates are async. Now the component passes pre-corrected answers.

  const submitAllAnswers = useCallback(async (
    userFeedback?: string,
    overrideAnswers?: Record<string, string>
  ) => {
    if (!state.sessionState) {
      throw new Error('Nenhuma sessão de importação ativa');
    }

    // Use override answers if provided (fixes "__other__" race condition)
    // Otherwise fall back to state.answers for backward compatibility
    const answersToUse = overrideAnswers || state.answers;

    // Phase 3 fix: Use 're-analyzing' stage with rotating messages
    updateProgress('re-analyzing', 70, 'NEXO reanalisando com suas respostas...', 're-think');

    // Simulate progress during Gemini call (15-30s)
    let messageIndex = 0;
    const progressInterval = setInterval(() => {
      setState(prev => {
        const newPercent = Math.min(prev.progress.percent + 2, 90);
        messageIndex = (messageIndex + 1) % RE_ANALYZING_MESSAGES.length;
        return {
          ...prev,
          progress: {
            ...prev.progress,
            percent: newPercent,
            message: RE_ANALYZING_MESSAGES[messageIndex],
          },
        };
      });
    }, 2000);

    try {
      // STATELESS: Merge answers into session state before sending
      // Use overrideAnswers if provided (pre-corrected, no "__other__" values)
      const updatedSessionState: NexoSessionState = {
        ...state.sessionState,
        answers: { ...state.sessionState.answers, ...answersToUse },
        updated_at: new Date().toISOString(),
      };

      const result = await nexoSubmitAnswers({
        session_state: updatedSessionState,  // STATELESS: Pass full state
        answers: answersToUse,  // Use corrected answers (no "__other__")
      });

      // Clear progress interval
      clearInterval(progressInterval);

      // Debug logging for re-reasoning flow
      console.log('[NEXO] Submit answers response:', {
        success: result.data?.success,
        remaining_questions: result.data?.remaining_questions?.length || 0,
        ready_for_processing: result.data?.ready_for_processing,
        will_continue_questioning: Boolean(result.data?.remaining_questions?.length),
        confidence: result.data?.confidence,
        validation_errors: result.data?.validation_errors,
        re_reasoning_applied: result.data?.re_reasoning_applied,
      });

      if (!result.data?.success) {
        // FIX (January 2026): Handle re-reasoning failure with HIL recovery
        // Previously this threw an error and broke the flow
        if (result.data?.error === 're_reasoning_failed') {
          console.warn('[NEXO] Re-reasoning failed, HIL required:', result.data.re_reasoning_error);

          // Show the HIL question about continuing - this is a recovery path, not an error
          if (result.data.remaining_questions && result.data.remaining_questions.length > 0) {
            setState(prev => ({
              ...prev,
              stage: 'questioning',
              sessionState: result.data!.session || prev.sessionState,
              questions: result.data!.remaining_questions!,
              progress: {
                stage: 'questioning',
                percent: 70,
                message: 'Análise automática falhou. Revisão necessária.',
                currentStep: 'hil'
              },
              error: null, // Clear error since we have a recovery path via HIL
            }));
            // Clear interval and return - let user answer HIL question
            clearInterval(progressInterval);
            return;
          }
        }

        // Check for schema validation errors (pre-validation against PostgreSQL)
        if (result.data?.validation_errors && result.data.validation_errors.length > 0) {
          console.warn('[NEXO] Schema validation failed:', result.data.validation_errors);
          const errorList = result.data.validation_errors.map(formatValidationError).join('\n• ');
          throw new Error(`Validação de schema falhou:\n• ${errorList}`);
        }

        // Extract error message from backend response
        const errorMsg = result.data?.error
          || 'Sessão expirada. Por favor, faça upload do arquivo novamente.';
        throw new Error(errorMsg);
      }

      // STATELESS: Update session state from backend response
      const newSessionState = result.data.session || updatedSessionState;

      // Check if more questions remain
      if (result.data.remaining_questions && result.data.remaining_questions.length > 0) {
        setState(prev => ({
          ...prev,
          stage: 'questioning',  // FIX: Must update stage to show questions UI
          sessionState: newSessionState,  // STATELESS: Store updated state
          questions: result.data!.remaining_questions!,
          progress: { stage: 'questioning', percent: 75, message: 'Mais perguntas...', currentStep: 'ask' },
        }));
      } else {
        // Generate client-side review summary for HIL approval
        const mainSheet = state.analysis!.sheets.find(s => s.purpose === 'items') || state.analysis!.sheets[0];
        const projectAnswer = state.answers['project'] || state.answers['projeto'] || null;

        // Count high confidence mappings as validations
        const highConfMappings = state.analysis!.columnMappings.filter(m => m.confidence >= 0.8);
        const lowConfMappings = state.analysis!.columnMappings.filter(m => m.confidence < 0.5);

        // Build validations list
        const validations: string[] = [
          `${highConfMappings.length} colunas mapeadas com alta confiança`,
          'Estrutura do arquivo validada',
          mainSheet ? `Aba principal identificada: ${mainSheet.name}` : '',
        ].filter(Boolean);

        // Build warnings list
        const warnings: string[] = lowConfMappings.length > 0
          ? [`${lowConfMappings.length} colunas com baixa confiança (usando valores padrão)`]
          : [];

        // Handle aggregation config from backend response
        let aggregationInfo: NexoReviewSummary['aggregation'] = null;
        const aggConfig = result.data?.aggregation;

        if (aggConfig?.enabled) {
          aggregationInfo = {
            enabled: true,
            strategy: aggConfig.strategy,
            uniqueParts: aggConfig.unique_parts || 0,
            totalRows: aggConfig.total_rows || 0,
            partNumberColumn: aggConfig.part_number_column,
          };

          // Add aggregation to validations
          validations.push(
            `Agregação ativa: ${aggConfig.total_rows} linhas → ${aggConfig.unique_parts} Part Numbers únicos`
          );

          console.log('[NEXO] Aggregation enabled:', aggregationInfo);
        }

        // Extract new columns from session state for user approval display
        const newColumnsFromSession: NexoReviewSummary['newColumns'] = (
          newSessionState.requested_new_columns || []
        )
          .filter(col => col.approved)  // Only show approved columns
          .map(col => ({
            name: col.name,
            originalName: col.original_name,
            userIntent: col.user_intent,
            inferredType: col.inferred_type,
            sourceFileColumn: col.source_file_column,
            approved: col.approved,
          }));

        // Add new columns info to validations if any
        if (newColumnsFromSession.length > 0) {
          validations.push(
            `${newColumnsFromSession.length} novo(s) campo(s) será(ão) criado(s) no banco de dados`
          );
        }

        const reviewSummary: NexoReviewSummary = {
          filename: state.analysis!.filename,
          mainSheet: mainSheet?.name || 'Desconhecida',
          totalItems: aggregationInfo?.enabled ? aggregationInfo.uniqueParts : (mainSheet?.row_count || 0),
          projectName: projectAnswer,
          newPartNumbers: 0, // Will be calculated by backend
          validations,
          warnings,
          recommendation: 'Acho que está tudo certo! Podemos prosseguir com a importação.',
          readyToImport: true,
          userFeedback: userFeedback || null,
          aggregation: aggregationInfo,
          newColumns: newColumnsFromSession.length > 0 ? newColumnsFromSession : undefined,
        };

        // Go to reviewing stage for HIL approval
        // FIX (January 2026): Added logging to debug stage transition issues
        console.log('[NEXO] Transitioning to reviewing stage with reviewSummary:', {
          filename: reviewSummary.filename,
          totalItems: reviewSummary.totalItems,
          validations: reviewSummary.validations.length,
          readyToImport: reviewSummary.readyToImport,
        });

        updateProgress('reviewing', 80, 'Aguardando aprovação', 'review');
        setState(prev => ({
          ...prev,
          stage: 'reviewing',
          sessionState: newSessionState,  // STATELESS: Store updated state
          questions: [],
          reviewSummary,
          userFeedback: userFeedback || null,
        }));
      }
    } catch (err) {
      // Ensure interval is cleared on error
      clearInterval(progressInterval);
      const message = err instanceof Error ? err.message : 'Erro ao processar respostas';
      setState(prev => ({ ...prev, error: message }));
      throw err;
    }
  }, [state.analysis, state.sessionState, state.answers, updateProgress]);

  // ==========================================================================
  // Action: Skip Questions (use default answers)
  // ==========================================================================

  const skipQuestions = useCallback(async () => {
    if (!state.sessionState) {
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
  }, [state.sessionState, state.questions, submitAllAnswers]);

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
    if (!state.sessionState) {
      throw new Error('Nenhuma sessão de importação ativa');
    }

    console.log('[NEXO] prepareProcessing: Starting with session:', {
      session_id: state.sessionState.session_id,
      filename: state.sessionState.filename,
      learned_mappings_count: Object.keys(state.sessionState.learned_mappings || {}).length,
      requested_new_columns_count: (state.sessionState.requested_new_columns || []).length,
    });

    updateProgress('processing', 85, 'Preparando configuração final...', 'act');

    try {
      const result = await nexoPrepareProcessing({
        session_state: state.sessionState,  // STATELESS: Pass full state
      });

      console.log('[NEXO] prepareProcessing: Backend response:', {
        success: result.data?.success,
        ready: result.data?.ready,
        error: result.data?.error,
        validation_errors: result.data?.validation_errors,
        column_mappings_count: result.data?.column_mappings?.length,
      });

      if (!result.data?.success || !result.data?.ready) {
        // Show specific validation errors if available (Phase 2 fix)
        if (result.data?.validation_errors && result.data.validation_errors.length > 0) {
          console.warn('[NEXO] Schema validation failed:', result.data.validation_errors);
          const errorList = result.data.validation_errors.map(formatValidationError).join('\n• ');
          throw new Error(`Validação de schema falhou:\n• ${errorList}`);
        }
        throw new Error(result.data?.error || 'Configuração não está pronta');
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
  }, [state.sessionState, updateProgress]);

  // ==========================================================================
  // Action: Execute NEXO Import
  // ==========================================================================

  const executeNexoImport = useCallback(async (
    projectId?: string,
    locationId?: string,
    configOverride?: NexoProcessingConfig // Allow passing config directly to avoid stale closure
  ): Promise<void> => {
    // Use passed config OR state config (stale closure fix)
    const config = configOverride || state.processingConfig;

    if (!state.sessionState || !config) {
      throw new Error('Preparação não concluída');
    }

    console.log('[NEXO] executeNexoImport: Starting with params:', {
      import_id: state.sessionState.session_id,
      s3_key: state.sessionState.s3_key,
      filename: state.sessionState.filename,
      column_mappings_count: config.column_mappings?.length,
      projectId,
      locationId,
    });

    updateProgress('importing', 92, 'Executando importação...', 'act');

    try {
      const result = await executeImport({
        import_id: state.sessionState.session_id,  // STATELESS: Use session_id from state
        s3_key: state.sessionState.s3_key,         // NEXO flow: file already in S3
        filename: state.sessionState.filename,
        column_mappings: config.column_mappings,
        project_id: projectId,
        destination_location_id: locationId,
      });

      console.log('[NEXO] executeNexoImport: Backend response:', {
        success: result.data?.success,
        error: result.data?.error,
        created_count: result.data?.created_count,
        failed_rows_count: result.data?.failed_rows?.length,
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
  }, [state.sessionState, state.processingConfig, updateProgress]);

  // ==========================================================================
  // Action: Learn From Result (LEARN)
  // ==========================================================================

  const learnFromResult = useCallback(async (
    result: Record<string, unknown>,
    corrections?: Record<string, unknown>
  ): Promise<void> => {
    if (!state.sessionState) {
      return; // Silent return if no session
    }

    updateProgress('learning', 95, 'NEXO aprendendo com este importação...', 'learn');

    try {
      await nexoLearnFromImport({
        session_state: state.sessionState,  // STATELESS: Pass full state
        import_result: result,
        user_corrections: corrections,
      });

      console.log('[NEXO] Aprendizado concluído');
    } catch (err) {
      // Learning failure is not critical - just log it
      console.warn('[NEXO] Falha ao aprender:', err);
    }
  }, [state.sessionState, updateProgress]);

  // ==========================================================================
  // Action: Approve and Import (HIL - Human-in-the-Loop approval)
  // ==========================================================================

  const approveAndImport = useCallback(async (): Promise<void> => {
    if (!state.sessionState || !state.reviewSummary) {
      throw new Error('Nenhuma sessão de revisão ativa');
    }

    console.log('[NEXO] approveAndImport: Starting import process...');

    // User approved - proceed to processing
    updateProgress('processing', 85, 'Preparando importação...', 'act');
    setState(prev => ({
      ...prev,
      stage: 'processing',
    }));

    // Prepare processing configuration - capture returned config to avoid stale closure
    console.log('[NEXO] approveAndImport: Calling prepareProcessing...');
    const config = await prepareProcessing();
    console.log('[NEXO] approveAndImport: prepareProcessing returned:', {
      success: config?.success,
      ready: config?.ready,
      mappingsCount: config?.column_mappings?.length,
    });

    // Execute the import - pass config directly to avoid React state timing issue
    console.log('[NEXO] approveAndImport: Calling executeNexoImport...');
    await executeNexoImport(
      state.answers['project'] || state.answers['projeto'] || undefined,
      state.answers['location'] || state.answers['local'] || undefined,
      config // Pass config directly to avoid stale closure
    );
    console.log('[NEXO] approveAndImport: executeNexoImport completed successfully');

    // Learn from this import for future improvements
    console.log('[NEXO] approveAndImport: Calling learnFromResult...');
    await learnFromResult(
      { success: true, items_imported: state.reviewSummary.totalItems },
      state.userFeedback ? { user_feedback: state.userFeedback } : undefined
    );
    console.log('[NEXO] approveAndImport: Import process completed!');
  }, [
    state.sessionState,
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
  NexoSessionState,  // STATELESS: Export session state type
};
