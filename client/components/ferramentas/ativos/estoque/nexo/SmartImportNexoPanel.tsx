'use client';

// =============================================================================
// SmartImportNexoPanel - NEXO Intelligent Import UI
// =============================================================================
// Inline UI component for the NEXO-guided import flow.
// Shows NEXO's analysis, reasoning trace, and clarification questions.
//
// Philosophy: NEXO guides user through import with intelligent analysis
// This component makes NEXO's thinking visible and interactive.
// =============================================================================

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Brain,
  Eye,
  MessageCircleQuestion,
  CheckCircle2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  FileSpreadsheet,
  Columns3,
  Lightbulb,
  Play,
  Loader2,
  Info,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  GlassCard,
  GlassCardHeader,
  GlassCardTitle,
  GlassCardContent,
} from '@/components/shared/glass-card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import {
  useSmartImportNexo,
  type NexoReasoningStep,
  type NexoQuestion,
  type NexoSheetAnalysis,
  type NexoColumnMapping,
} from '@/hooks/ativos/useSmartImportNexo';

// =============================================================================
// Types
// =============================================================================

interface SmartImportNexoPanelProps {
  file: File | null;
  onComplete: (sessionId: string) => void;
  onCancel: () => void;
}

// =============================================================================
// Sub-Components
// =============================================================================

/**
 * Displays NEXO's reasoning trace (thoughts, actions, observations).
 */
function ReasoningTrace({ steps }: { steps: NexoReasoningStep[] }) {
  const [isExpanded, setIsExpanded] = useState(false);

  if (steps.length === 0) return null;

  // Show only last 3 steps when collapsed
  const visibleSteps = isExpanded ? steps : steps.slice(-3);

  const getIcon = (type: NexoReasoningStep['type']) => {
    switch (type) {
      case 'thought':
        return <Brain className="w-4 h-4 text-purple-400" />;
      case 'action':
        return <Play className="w-4 h-4 text-cyan-400" />;
      case 'observation':
        return <Eye className="w-4 h-4 text-green-400" />;
    }
  };

  const getLabel = (type: NexoReasoningStep['type']) => {
    switch (type) {
      case 'thought':
        return 'Pensando';
      case 'action':
        return 'Ação';
      case 'observation':
        return 'Observação';
    }
  };

  return (
    <div className="space-y-2">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-sm text-text-muted hover:text-text-primary transition-colors"
      >
        <Lightbulb className="w-4 h-4" />
        <span>Como NEXO está pensando</span>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4" />
        ) : (
          <ChevronDown className="w-4 h-4" />
        )}
        <Badge variant="outline" className="ml-auto">
          {steps.length} passos
        </Badge>
      </button>

      <AnimatePresence>
        <motion.div
          initial={{ height: 0, opacity: 0 }}
          animate={{ height: 'auto', opacity: 1 }}
          className="space-y-2 pl-2 border-l-2 border-white/10"
        >
          {visibleSteps.map((step, index) => (
            <motion.div
              key={index}
              initial={{ x: -10, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ delay: index * 0.1 }}
              className="flex items-start gap-2 text-sm"
            >
              {getIcon(step.type)}
              <div>
                <span className="text-text-muted text-xs">
                  {getLabel(step.type)}:
                </span>
                <p className="text-text-secondary">{step.content}</p>
              </div>
            </motion.div>
          ))}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}

/**
 * Displays sheet analysis with purpose detection.
 */
function SheetAnalysis({ sheets }: { sheets: NexoSheetAnalysis[] }) {
  const getPurposeLabel = (purpose: NexoSheetAnalysis['purpose']) => {
    const labels: Record<NexoSheetAnalysis['purpose'], string> = {
      items: 'Itens',
      serials: 'Seriais',
      metadata: 'Metadados',
      summary: 'Resumo',
      config: 'Configuração',
      unknown: 'Desconhecido',
    };
    return labels[purpose];
  };

  const getPurposeColor = (purpose: NexoSheetAnalysis['purpose']) => {
    const colors: Record<NexoSheetAnalysis['purpose'], string> = {
      items: 'bg-cyan-500/20 text-cyan-400',
      serials: 'bg-purple-500/20 text-purple-400',
      metadata: 'bg-yellow-500/20 text-yellow-400',
      summary: 'bg-green-500/20 text-green-400',
      config: 'bg-blue-500/20 text-blue-400',
      unknown: 'bg-gray-500/20 text-gray-400',
    };
    return colors[purpose];
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-sm text-text-muted">
        <FileSpreadsheet className="w-4 h-4" />
        <span>Abas detectadas</span>
        <Badge variant="outline">{sheets.length}</Badge>
      </div>

      <div className="grid gap-2">
        {sheets.map((sheet, index) => (
          <div
            key={index}
            className="flex items-center justify-between p-3 bg-white/5 rounded-lg border border-white/10"
          >
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded bg-white/10 flex items-center justify-center text-sm font-medium">
                {index + 1}
              </div>
              <div>
                <p className="text-sm font-medium">{sheet.name}</p>
                <p className="text-xs text-text-muted">
                  {sheet.row_count.toLocaleString()} linhas · {sheet.column_count} colunas
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Badge className={getPurposeColor(sheet.purpose)}>
                {getPurposeLabel(sheet.purpose)}
              </Badge>
              <Badge variant="outline">
                {Math.round(sheet.confidence * 100)}%
              </Badge>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Displays column mappings with confidence.
 */
function ColumnMappings({ mappings }: { mappings: NexoColumnMapping[] }) {
  const [showAll, setShowAll] = useState(false);

  // Group by confidence level
  const highConfidence = mappings.filter(m => m.confidence >= 0.8);
  const mediumConfidence = mappings.filter(m => m.confidence >= 0.5 && m.confidence < 0.8);
  const lowConfidence = mappings.filter(m => m.confidence < 0.5);

  const visibleMappings = showAll ? mappings : mappings.slice(0, 5);

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return 'text-green-400';
    if (confidence >= 0.5) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-text-muted">
          <Columns3 className="w-4 h-4" />
          <span>Mapeamento de colunas</span>
        </div>
        <div className="flex gap-2">
          <Badge className="bg-green-500/20 text-green-400">
            {highConfidence.length} alta
          </Badge>
          <Badge className="bg-yellow-500/20 text-yellow-400">
            {mediumConfidence.length} média
          </Badge>
          <Badge className="bg-red-500/20 text-red-400">
            {lowConfidence.length} baixa
          </Badge>
        </div>
      </div>

      <div className="space-y-1">
        {visibleMappings.map((mapping, index) => (
          <div
            key={index}
            className="flex items-center justify-between p-2 bg-white/5 rounded text-sm"
          >
            <div className="flex items-center gap-2">
              <span className="text-text-muted">{mapping.file_column}</span>
              <span className="text-text-muted">→</span>
              <span className="font-medium">{mapping.target_field}</span>
            </div>
            <span className={getConfidenceColor(mapping.confidence)}>
              {Math.round(mapping.confidence * 100)}%
            </span>
          </div>
        ))}
      </div>

      {mappings.length > 5 && (
        <button
          onClick={() => setShowAll(!showAll)}
          className="text-sm text-cyan-400 hover:underline"
        >
          {showAll ? 'Mostrar menos' : `Ver todas ${mappings.length} colunas`}
        </button>
      )}
    </div>
  );
}

/**
 * Interactive question panel for user input.
 */
function QuestionPanel({
  questions,
  answers,
  onAnswer,
  onSubmit,
  onSkip,
  isSubmitting,
}: {
  questions: NexoQuestion[];
  answers: Record<string, string>;
  onAnswer: (questionId: string, answer: string) => void;
  onSubmit: () => void;
  onSkip: () => void;
  isSubmitting: boolean;
}) {
  const criticalQuestions = questions.filter(q => q.importance === 'critical');
  const optionalQuestions = questions.filter(q => q.importance !== 'critical');

  const allCriticalAnswered = criticalQuestions.every(q => answers[q.id]);

  const getImportanceBadge = (importance: NexoQuestion['importance']) => {
    const styles: Record<NexoQuestion['importance'], string> = {
      critical: 'bg-red-500/20 text-red-400',
      high: 'bg-orange-500/20 text-orange-400',
      medium: 'bg-yellow-500/20 text-yellow-400',
      low: 'bg-gray-500/20 text-gray-400',
    };
    const labels: Record<NexoQuestion['importance'], string> = {
      critical: 'Obrigatório',
      high: 'Importante',
      medium: 'Opcional',
      low: 'Opcional',
    };
    return (
      <Badge className={styles[importance]}>{labels[importance]}</Badge>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <MessageCircleQuestion className="w-5 h-5 text-purple-400" />
        <h3 className="font-medium">NEXO precisa da sua ajuda</h3>
        <Badge variant="outline">{questions.length} perguntas</Badge>
      </div>

      {/* Critical questions first */}
      {criticalQuestions.length > 0 && (
        <div className="space-y-4">
          <p className="text-sm text-text-muted flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            Estas respostas são necessárias para continuar:
          </p>
          {criticalQuestions.map((question) => (
            <QuestionItem
              key={question.id}
              question={question}
              answer={answers[question.id]}
              onAnswer={onAnswer}
              importanceBadge={getImportanceBadge(question.importance)}
            />
          ))}
        </div>
      )}

      {/* Optional questions */}
      {optionalQuestions.length > 0 && (
        <div className="space-y-4 pt-4 border-t border-white/10">
          <p className="text-sm text-text-muted">
            Perguntas opcionais (respostas padrão serão usadas se não responder):
          </p>
          {optionalQuestions.map((question) => (
            <QuestionItem
              key={question.id}
              question={question}
              answer={answers[question.id]}
              onAnswer={onAnswer}
              importanceBadge={getImportanceBadge(question.importance)}
            />
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex justify-end gap-3 pt-4">
        <Button
          variant="outline"
          onClick={onSkip}
          disabled={isSubmitting}
        >
          Pular e usar padrões
        </Button>
        <Button
          onClick={onSubmit}
          disabled={!allCriticalAnswered || isSubmitting}
          className="bg-gradient-to-r from-cyan-500 to-purple-500"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              Processando...
            </>
          ) : (
            <>
              <CheckCircle2 className="w-4 h-4 mr-2" />
              Confirmar respostas
            </>
          )}
        </Button>
      </div>
    </div>
  );
}

/**
 * Single question item with radio options.
 */
function QuestionItem({
  question,
  answer,
  onAnswer,
  importanceBadge,
}: {
  question: NexoQuestion;
  answer?: string;
  onAnswer: (questionId: string, answer: string) => void;
  importanceBadge: React.ReactNode;
}) {
  return (
    <div className="p-4 bg-white/5 rounded-lg border border-white/10 space-y-3">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="font-medium">{question.question}</p>
          {question.context && (
            <p className="text-sm text-text-muted mt-1 flex items-start gap-2">
              <Info className="w-4 h-4 flex-shrink-0 mt-0.5" />
              {question.context}
            </p>
          )}
        </div>
        {importanceBadge}
      </div>

      <RadioGroup
        value={answer}
        onValueChange={(value: string) => onAnswer(question.id, value)}
        className="space-y-2"
      >
        {question.options.map((option) => (
          <div key={option.value} className="flex items-start space-x-3">
            <RadioGroupItem
              value={option.value}
              id={`${question.id}-${option.value}`}
              className="mt-1"
            />
            <Label
              htmlFor={`${question.id}-${option.value}`}
              className="flex-1 cursor-pointer"
            >
              <span className="font-medium">{option.label}</span>
              {option.description && (
                <p className="text-sm text-text-muted">{option.description}</p>
              )}
            </Label>
          </div>
        ))}
      </RadioGroup>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function SmartImportNexoPanel({
  file,
  onComplete,
  onCancel,
}: SmartImportNexoPanelProps) {
  const {
    state,
    isAnalyzing,
    hasQuestions,
    isReadyToProcess,
    startAnalysis,
    answerQuestion,
    submitAllAnswers,
    skipQuestions,
    prepareProcessing,
    reasoningTrace,
    currentThought,
  } = useSmartImportNexo();

  const [isSubmitting, setIsSubmitting] = useState(false);

  // Start analysis when file changes
  useMemo(() => {
    if (file && state.stage === 'idle') {
      startAnalysis(file).catch(console.error);
    }
  }, [file, state.stage, startAnalysis]);

  // Handle submit answers
  const handleSubmitAnswers = async () => {
    setIsSubmitting(true);
    try {
      await submitAllAnswers();
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle skip questions
  const handleSkipQuestions = async () => {
    setIsSubmitting(true);
    try {
      await skipQuestions();
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle continue to processing
  const handleContinue = async () => {
    setIsSubmitting(true);
    try {
      const config = await prepareProcessing();
      if (config.ready) {
        onComplete(state.analysis!.sessionId);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Loading state
  if (state.stage === 'uploading' || isAnalyzing) {
    return (
      <GlassCard>
        <GlassCardHeader>
          <div className="flex items-center gap-2">
            <Brain className="w-5 h-5 text-purple-400 animate-pulse" />
            <GlassCardTitle>NEXO Analisando</GlassCardTitle>
          </div>
        </GlassCardHeader>
        <GlassCardContent>
          <div className="space-y-4">
            <Progress value={state.progress.percent} className="h-2" />
            <p className="text-sm text-text-secondary text-center">
              {state.progress.message}
            </p>

            {currentThought && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex items-start gap-2 p-3 bg-purple-500/10 rounded-lg border border-purple-500/20"
              >
                <Brain className="w-4 h-4 text-purple-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-text-secondary">{currentThought}</p>
              </motion.div>
            )}
          </div>
        </GlassCardContent>
      </GlassCard>
    );
  }

  // Error state
  if (state.stage === 'error') {
    return (
      <GlassCard>
        <GlassCardHeader>
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-400" />
            <GlassCardTitle>Erro na Análise</GlassCardTitle>
          </div>
        </GlassCardHeader>
        <GlassCardContent>
          <div className="space-y-4">
            <p className="text-sm text-red-400">{state.error}</p>
            <Button variant="outline" onClick={onCancel}>
              Tentar novamente
            </Button>
          </div>
        </GlassCardContent>
      </GlassCard>
    );
  }

  // Analysis complete - show results
  if (state.analysis) {
    return (
      <GlassCard>
        <GlassCardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-purple-400" />
              <GlassCardTitle>Análise NEXO</GlassCardTitle>
            </div>
            <Badge
              className={
                state.analysis.overallConfidence >= 0.8
                  ? 'bg-green-500/20 text-green-400'
                  : state.analysis.overallConfidence >= 0.5
                  ? 'bg-yellow-500/20 text-yellow-400'
                  : 'bg-red-500/20 text-red-400'
              }
            >
              {Math.round(state.analysis.overallConfidence * 100)}% confiança
            </Badge>
          </div>
        </GlassCardHeader>

        <GlassCardContent>
          <div className="space-y-6">
            {/* File info */}
            <div className="flex items-center gap-3 p-3 bg-white/5 rounded-lg">
              <FileSpreadsheet className="w-5 h-5 text-cyan-400" />
              <div>
                <p className="font-medium">{state.analysis.filename}</p>
                <p className="text-sm text-text-muted">
                  {state.analysis.detectedType.toUpperCase()} · {state.analysis.recommendedStrategy}
                </p>
              </div>
            </div>

            {/* Reasoning trace */}
            <ReasoningTrace steps={reasoningTrace} />

            {/* Sheet analysis */}
            {state.analysis.sheets.length > 0 && (
              <SheetAnalysis sheets={state.analysis.sheets} />
            )}

            {/* Column mappings */}
            {state.analysis.columnMappings.length > 0 && (
              <ColumnMappings mappings={state.analysis.columnMappings} />
            )}

            {/* Questions section */}
            {hasQuestions && (
              <QuestionPanel
                questions={state.questions}
                answers={state.answers}
                onAnswer={answerQuestion}
                onSubmit={handleSubmitAnswers}
                onSkip={handleSkipQuestions}
                isSubmitting={isSubmitting}
              />
            )}

            {/* Ready to process */}
            {isReadyToProcess && !hasQuestions && (
              <div className="flex justify-end gap-3 pt-4 border-t border-white/10">
                <Button variant="outline" onClick={onCancel}>
                  Cancelar
                </Button>
                <Button
                  onClick={handleContinue}
                  disabled={isSubmitting}
                  className="bg-gradient-to-r from-cyan-500 to-purple-500"
                >
                  {isSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Preparando...
                    </>
                  ) : (
                    <>
                      <CheckCircle2 className="w-4 h-4 mr-2" />
                      Continuar para importação
                    </>
                  )}
                </Button>
              </div>
            )}
          </div>
        </GlassCardContent>
      </GlassCard>
    );
  }

  // No file yet
  return null;
}

export default SmartImportNexoPanel;
