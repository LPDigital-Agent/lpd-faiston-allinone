'use client';

/**
 * LearningStories Panel
 *
 * Shows what the agents have learned from interactions.
 * "O que Aprendemos" - learning stories in first-person.
 */

import { motion } from 'framer-motion';
import {
  GlassCard,
  GlassCardHeader,
  GlassCardTitle,
  GlassCardContent,
} from '@/components/shared/glass-card';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Lightbulb, Brain, Calendar, RefreshCw } from 'lucide-react';
import { useLearningStories } from '@/hooks/ativos';
import {
  CONFIDENCE_LABELS,
  CONFIDENCE_COLORS,
} from '@/lib/ativos/agentRoomConstants';
import type { LearningStory } from '@/lib/ativos/agentRoomTypes';

// =============================================================================
// Helper Functions
// =============================================================================

function formatDate(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Hoje';
  if (diffDays === 1) return 'Ontem';
  if (diffDays < 7) return `${diffDays} dias atrás`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} semanas atrás`;
  return date.toLocaleDateString('pt-BR', { day: 'numeric', month: 'short' });
}

// =============================================================================
// Sub-Components
// =============================================================================

interface LearningStoryItemProps {
  story: LearningStory;
  index: number;
}

function LearningStoryItem({ story, index }: LearningStoryItemProps) {
  const confidenceLabel = CONFIDENCE_LABELS[story.confidence];
  const confidenceColor = CONFIDENCE_COLORS[story.confidence];
  const learnedDate = formatDate(new Date(story.learnedAt));

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1 }}
      className="flex gap-3 p-3 rounded-lg bg-white/5 hover:bg-white/10 transition-colors"
    >
      <div className="shrink-0 mt-0.5">
        <div className="w-8 h-8 rounded-full bg-purple-500/20 flex items-center justify-center">
          <Lightbulb className="w-4 h-4 text-purple-400" />
        </div>
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-text-primary leading-relaxed">
          &ldquo;{story.story}&rdquo;
        </p>
        <div className="flex items-center gap-3 mt-2 flex-wrap">
          <div className="flex items-center gap-1">
            <Brain className="w-3 h-3 text-text-muted" />
            <span className="text-xs text-text-muted">{story.agentName}</span>
          </div>
          <div className="flex items-center gap-1">
            <Calendar className="w-3 h-3 text-text-muted" />
            <span className="text-xs text-text-muted">{learnedDate}</span>
          </div>
          <span className={`text-xs ${confidenceColor}`}>
            {confidenceLabel}
          </span>
        </div>
        {story.context && (
          <p className="text-xs text-text-muted mt-1">
            Contexto: {story.context}
          </p>
        )}
      </div>
    </motion.div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function LearningStories() {
  const { stories, isConnected, error } = useLearningStories();

  return (
    <GlassCard>
      <GlassCardHeader>
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-purple-400" />
            <GlassCardTitle>O que Aprendemos</GlassCardTitle>
          </div>
          {!isConnected && (
            <RefreshCw className="w-4 h-4 text-yellow-400 animate-spin" />
          )}
        </div>
        {error && (
          <p className="text-xs text-yellow-400 mt-1">{error}</p>
        )}
      </GlassCardHeader>

      <GlassCardContent>
        {stories.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Lightbulb className="w-12 h-12 text-text-muted mb-3" />
            <p className="text-sm text-text-muted">
              Ainda estamos aprendendo...
            </p>
            <p className="text-xs text-text-muted mt-1">
              Os aprendizados aparecerão aqui conforme usamos o sistema
            </p>
          </div>
        ) : (
          <ScrollArea className="h-[200px]">
            <div className="space-y-3 pr-4">
              {stories.map((story, index) => (
                <LearningStoryItem key={story.id} story={story} index={index} />
              ))}
            </div>
          </ScrollArea>
        )}
      </GlassCardContent>
    </GlassCard>
  );
}
