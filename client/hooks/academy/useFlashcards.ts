// =============================================================================
// useFlashcards Hook - Faiston Academy
// =============================================================================
// Hook for flashcard generation and study functionality.
// Supports spaced repetition study sessions.
// =============================================================================

'use client';

import { useState, useCallback, useEffect } from 'react';
import { useMutation } from '@tanstack/react-query';
import { generateFlashcards } from '@/services/academyAgentcore';
import type { Flashcard, FlashcardsResponse } from '@/lib/academy/types';
import { ACADEMY_STORAGE_KEYS } from '@/lib/academy/constants';

interface UseFlashcardsOptions {
  courseId: string;
  episodeId: string;
}

interface FlashcardWithStudy extends Flashcard {
  studied: boolean;
  correct: boolean | null;
  studiedAt: Date | null;
}

interface FlashcardsState {
  flashcards: FlashcardWithStudy[];
  currentIndex: number;
  isFlipped: boolean;
  studyComplete: boolean;
  score: { correct: number; total: number };
}

const getStorageKey = (courseId: string, episodeId: string) =>
  `${ACADEMY_STORAGE_KEYS.FLASHCARDS_PREFIX}${courseId}_${episodeId}`;

export function useFlashcards({ courseId, episodeId }: UseFlashcardsOptions) {
  const [state, setState] = useState<FlashcardsState | null>(null);

  // Load from localStorage on mount
  useEffect(() => {
    const storageKey = getStorageKey(courseId, episodeId);
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        setState({
          ...parsed,
          flashcards: parsed.flashcards.map((fc: FlashcardWithStudy) => ({
            ...fc,
            studiedAt: fc.studiedAt ? new Date(fc.studiedAt) : null,
          })),
        });
      }
    } catch (e) {
      console.error('Failed to load flashcards:', e);
    }
  }, [courseId, episodeId]);

  // Save to localStorage when state changes
  useEffect(() => {
    if (state) {
      const storageKey = getStorageKey(courseId, episodeId);
      try {
        localStorage.setItem(storageKey, JSON.stringify(state));
      } catch (e) {
        console.error('Failed to save flashcards:', e);
      }
    }
  }, [state, courseId, episodeId]);

  // Generate mutation
  const generateMutation = useMutation({
    mutationFn: async (params: {
      transcription: string;
      difficulty?: 'easy' | 'medium' | 'hard';
      count?: number;
      custom_prompt?: string;
    }): Promise<FlashcardsResponse> => {
      const { data } = await generateFlashcards(params);
      return data;
    },
    onSuccess: (data) => {
      const flashcardsWithStudy: FlashcardWithStudy[] = data.flashcards.map(
        (fc, index) => ({
          ...fc,
          id: fc.id || `fc-${index}`,
          studied: false,
          correct: null,
          studiedAt: null,
        })
      );

      setState({
        flashcards: flashcardsWithStudy,
        currentIndex: 0,
        isFlipped: false,
        studyComplete: false,
        score: { correct: 0, total: 0 },
      });
    },
  });

  // Flip current card
  const flipCard = useCallback(() => {
    setState((prev) => (prev ? { ...prev, isFlipped: !prev.isFlipped } : null));
  }, []);

  // Mark current card as correct/incorrect
  const markCard = useCallback((correct: boolean) => {
    setState((prev) => {
      if (!prev) return null;

      const updatedFlashcards = [...prev.flashcards];
      const currentCard = updatedFlashcards[prev.currentIndex];
      currentCard.studied = true;
      currentCard.correct = correct;
      currentCard.studiedAt = new Date();

      const newScore = {
        correct: prev.score.correct + (correct ? 1 : 0),
        total: prev.score.total + 1,
      };

      const nextIndex = prev.currentIndex + 1;
      const studyComplete = nextIndex >= prev.flashcards.length;

      return {
        ...prev,
        flashcards: updatedFlashcards,
        currentIndex: studyComplete ? prev.currentIndex : nextIndex,
        isFlipped: false,
        studyComplete,
        score: newScore,
      };
    });
  }, []);

  // Go to specific card
  const goToCard = useCallback((index: number) => {
    setState((prev) => {
      if (!prev || index < 0 || index >= prev.flashcards.length) return prev;
      return { ...prev, currentIndex: index, isFlipped: false };
    });
  }, []);

  // Reset study session
  const resetStudy = useCallback(() => {
    setState((prev) => {
      if (!prev) return null;

      return {
        ...prev,
        flashcards: prev.flashcards.map((fc) => ({
          ...fc,
          studied: false,
          correct: null,
          studiedAt: null,
        })),
        currentIndex: 0,
        isFlipped: false,
        studyComplete: false,
        score: { correct: 0, total: 0 },
      };
    });
  }, []);

  // Clear all flashcards
  const clearFlashcards = useCallback(() => {
    setState(null);
    const storageKey = getStorageKey(courseId, episodeId);
    try {
      localStorage.removeItem(storageKey);
    } catch (e) {
      console.error('Failed to clear flashcards:', e);
    }
  }, [courseId, episodeId]);

  // Current card
  const currentCard = state?.flashcards[state.currentIndex] || null;

  return {
    // State
    flashcards: state?.flashcards || [],
    currentCard,
    currentIndex: state?.currentIndex ?? 0,
    isFlipped: state?.isFlipped ?? false,
    studyComplete: state?.studyComplete ?? false,
    score: state?.score ?? { correct: 0, total: 0 },

    // Actions
    generate: generateMutation.mutate,
    flipCard,
    markCard,
    goToCard,
    resetStudy,
    clearFlashcards,

    // Mutation state
    isGenerating: generateMutation.isPending,
    generateError: generateMutation.error,

    // Helpers
    hasFlashcards: state !== null && state.flashcards.length > 0,
    progress: state
      ? {
          current: state.currentIndex + 1,
          total: state.flashcards.length,
          studied: state.flashcards.filter((fc) => fc.studied).length,
        }
      : null,
  };
}
