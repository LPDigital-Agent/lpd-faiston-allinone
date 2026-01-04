// =============================================================================
// Academy Constants - Faiston Academy
// =============================================================================
// Constants and configuration for Faiston Academy module.
// =============================================================================

import {
  LayoutDashboard,
  GraduationCap,
  Brain,
  Video,
  BookOpen,
  Trophy,
  Sparkles,
  LucideIcon,
} from 'lucide-react';

// =============================================================================
// Navigation Modules
// =============================================================================

export interface AcademyNavModule {
  id: string;
  label: string;
  icon: LucideIcon;
  href: string;
  description?: string;
}

export const ACADEMY_NAV_MODULES: AcademyNavModule[] = [
  {
    id: 'dashboard',
    label: 'Dashboard',
    icon: LayoutDashboard,
    href: '/ferramentas/academy/dashboard',
    description: 'Visao geral do seu progresso',
  },
  {
    id: 'cursos',
    label: 'Cursos',
    icon: GraduationCap,
    href: '/ferramentas/academy/cursos',
    description: 'Catalogo de cursos disponiveis',
  },
  {
    id: 'treinamentos',
    label: 'NEXO Tutor',
    icon: Brain,
    href: '/ferramentas/academy/treinamentos',
    description: 'Crie treinamentos personalizados',
  },
  {
    id: 'ao-vivo',
    label: 'Ao Vivo',
    icon: Video,
    href: '/ferramentas/academy/ao-vivo',
    description: 'Sessoes ao vivo com instrutores',
  },
];

// =============================================================================
// Classroom Panel Types
// =============================================================================

export type ClassroomPanelId =
  | 'video'
  | 'transcription'
  | 'nexo'
  | 'flashcards'
  | 'mindmap'
  | 'audioclass'
  | 'slidedeck'
  | 'library'
  | 'notes'
  | 'extraclass'
  | 'videoclass'
  | 'reflection';

export interface PanelPosition {
  x: number;
  y: number;
}

export interface PanelSize {
  width: number;
  height: number;
}

export interface PanelState {
  position: PanelPosition;
  size: PanelSize;
  isVisible: boolean;
  isMinimized: boolean;
  isMaximized: boolean;
  zIndex: number;
}

export const DEFAULT_PANEL_STATES: Record<ClassroomPanelId, PanelState> = {
  video: {
    position: { x: 20, y: 20 },
    size: { width: 800, height: 500 },
    isVisible: true,
    isMinimized: false,
    isMaximized: false,
    zIndex: 100,
  },
  transcription: {
    position: { x: 840, y: 20 },
    size: { width: 400, height: 500 },
    isVisible: false,
    isMinimized: false,
    isMaximized: false,
    zIndex: 101,
  },
  nexo: {
    position: { x: 20, y: 540 },
    size: { width: 400, height: 400 },
    isVisible: false,
    isMinimized: false,
    isMaximized: false,
    zIndex: 102,
  },
  flashcards: {
    position: { x: 440, y: 540 },
    size: { width: 500, height: 400 },
    isVisible: false,
    isMinimized: false,
    isMaximized: false,
    zIndex: 103,
  },
  mindmap: {
    position: { x: 450, y: 100 },
    size: { width: 700, height: 500 },
    isVisible: false,
    isMinimized: false,
    isMaximized: false,
    zIndex: 104,
  },
  audioclass: {
    position: { x: 300, y: 200 },
    size: { width: 500, height: 450 },
    isVisible: false,
    isMinimized: false,
    isMaximized: false,
    zIndex: 105,
  },
  slidedeck: {
    position: { x: 100, y: 100 },
    size: { width: 900, height: 600 },
    isVisible: false,
    isMinimized: false,
    isMaximized: false,
    zIndex: 106,
  },
  library: {
    position: { x: 200, y: 150 },
    size: { width: 600, height: 500 },
    isVisible: false,
    isMinimized: false,
    isMaximized: false,
    zIndex: 107,
  },
  notes: {
    position: { x: 600, y: 200 },
    size: { width: 400, height: 500 },
    isVisible: false,
    isMinimized: false,
    isMaximized: false,
    zIndex: 108,
  },
  extraclass: {
    position: { x: 250, y: 150 },
    size: { width: 700, height: 500 },
    isVisible: false,
    isMinimized: false,
    isMaximized: false,
    zIndex: 109,
  },
  videoclass: {
    position: { x: 150, y: 100 },
    size: { width: 800, height: 550 },
    isVisible: false,
    isMinimized: false,
    isMaximized: false,
    zIndex: 110,
  },
  reflection: {
    position: { x: 300, y: 150 },
    size: { width: 600, height: 500 },
    isVisible: false,
    isMinimized: false,
    isMaximized: false,
    zIndex: 111,
  },
};

export const PANEL_MIN_SIZES: Record<ClassroomPanelId, PanelSize> = {
  video: { width: 400, height: 300 },
  transcription: { width: 300, height: 300 },
  nexo: { width: 350, height: 350 },
  flashcards: { width: 400, height: 350 },
  mindmap: { width: 500, height: 400 },
  audioclass: { width: 400, height: 400 },
  slidedeck: { width: 600, height: 450 },
  library: { width: 400, height: 400 },
  notes: { width: 300, height: 400 },
  extraclass: { width: 500, height: 400 },
  videoclass: { width: 600, height: 450 },
  reflection: { width: 500, height: 400 },
};

// =============================================================================
// Flashcard Difficulty Settings
// =============================================================================

export const FLASHCARD_DIFFICULTIES = [
  { value: 'easy', label: 'Facil', description: 'Conceitos basicos' },
  { value: 'medium', label: 'Medio', description: 'Conceitos intermediarios' },
  { value: 'hard', label: 'Dificil', description: 'Conceitos avancados' },
] as const;

export const FLASHCARD_COUNTS = [5, 10, 15, 20] as const;

// =============================================================================
// Audio Class Modes
// =============================================================================

export const AUDIOCLASS_MODES = [
  {
    value: 'deep_explanation',
    label: 'Explicacao Profunda',
    description: 'Dialogo detalhado entre dois hosts',
    icon: BookOpen,
  },
  {
    value: 'debate',
    label: 'Debate',
    description: 'Discussao com diferentes perspectivas',
    icon: Sparkles,
  },
  {
    value: 'summary',
    label: 'Resumo',
    description: 'Versao condensada do conteudo',
    icon: Trophy,
  },
] as const;

// =============================================================================
// Slide Deck Archetypes
// =============================================================================

export const SLIDEDECK_ARCHETYPES = [
  {
    value: 'deep_dive',
    label: 'Conceito Essencial',
    description: 'Exploracao profunda de um tema',
  },
  {
    value: 'how_to',
    label: 'Passo a Passo',
    description: 'Guia pratico com etapas',
  },
  {
    value: 'versus',
    label: 'Batalha Comparativa',
    description: 'Comparacao entre conceitos',
  },
  {
    value: 'case_study',
    label: 'Estudo de Caso',
    description: 'Analise de caso real',
  },
  {
    value: 'flash_quiz',
    label: 'Flash Quiz',
    description: 'Perguntas e respostas',
  },
] as const;

// =============================================================================
// Video Class Settings
// =============================================================================

export const VIDEO_FORMATS = [
  {
    value: 'brief',
    label: 'Breve (1-2 min)',
    description: 'Resumo rapido do conteudo',
  },
  {
    value: 'explainer',
    label: 'Explicativo (5-8 min)',
    description: 'Explicacao detalhada',
  },
] as const;

export const VISUAL_THEMES = [
  { value: 'corporate', label: 'Corporativo' },
  { value: 'educational', label: 'Educacional' },
  { value: 'anime', label: 'Anime' },
  { value: 'whiteboard', label: 'Quadro Branco' },
] as const;

// =============================================================================
// XP and Gamification
// =============================================================================

export const XP_REWARDS = {
  EPISODE_COMPLETE: 50,
  FLASHCARD_STUDY: 10,
  MINDMAP_GENERATE: 15,
  AUDIOCLASS_LISTEN: 20,
  REFLECTION_SUBMIT: 30,
  QUIZ_COMPLETE: 25,
  STREAK_BONUS: 10,
} as const;

export const LEVEL_THRESHOLDS = [
  0,     // Level 1
  100,   // Level 2
  250,   // Level 3
  500,   // Level 4
  1000,  // Level 5
  2000,  // Level 6
  3500,  // Level 7
  5500,  // Level 8
  8000,  // Level 9
  12000, // Level 10
] as const;

// =============================================================================
// ElevenLabs Voice Options
// =============================================================================

export interface VoiceOption {
  id: string;
  name: string;
  description: string;
}

export const VOICE_OPTIONS = {
  female: [
    { id: 'EXAVITQu4vr4xnSDxMaL', name: 'Sarah', description: 'Suave e acolhedora' },
    { id: 'cgSgspJ2msm6clMCkdW9', name: 'Jessica', description: 'Expressiva e animada' },
    { id: 'pFZP5JQG7iQjIQuC4Bku', name: 'Lily', description: 'Clara e articulada' },
  ] as VoiceOption[],
  male: [
    { id: 'cjVigY5qzO86Huf0OWal', name: 'Eric', description: 'Natural e conversacional' },
    { id: 'iP95p4xoKVk53GoZ742B', name: 'Chris', description: 'Descontrado e amigavel' },
    { id: 'nPczCjzI2devNBz1zQrb', name: 'Brian', description: 'Autoritativo e envolvente' },
  ] as VoiceOption[],
};

export const DEFAULT_MALE_VOICE = 'cjVigY5qzO86Huf0OWal'; // Eric
export const DEFAULT_FEMALE_VOICE = 'EXAVITQu4vr4xnSDxMaL'; // Sarah

// =============================================================================
// Audio Mode Labels
// =============================================================================

import type { AudioMode } from './types';

export const AUDIO_MODE_LABELS: Record<
  AudioMode,
  { label: string; description: string }
> = {
  deep_explanation: {
    label: 'Explicacao Profunda',
    description: 'Exploracao detalhada dos conceitos (5-8 min)',
  },
  debate: {
    label: 'Debate',
    description: 'Duas perspectivas discutindo o tema (5-8 min)',
  },
  summary: {
    label: 'Resumo',
    description: 'Recapitulacao rapida dos pontos-chave (2-3 min)',
  },
};

// =============================================================================
// Playback Rates
// =============================================================================

export const PLAYBACK_RATES = [0.5, 0.75, 1, 1.25, 1.5, 2] as const;

// =============================================================================
// Deck Archetypes (Detailed)
// =============================================================================

import type { DeckArchetype } from './types';

export interface DeckArchetypeInfo {
  id: DeckArchetype;
  emoji: string;
  name: string;
  description: string;
}

export const DECK_ARCHETYPES: readonly DeckArchetypeInfo[] = [
  {
    id: 'deep_dive',
    emoji: '🎯',
    name: 'Conceito Essencial',
    description: 'Explica um conceito em profundidade',
  },
  {
    id: 'how_to',
    emoji: '📋',
    name: 'Passo a Passo',
    description: 'Tutorial com etapas numeradas',
  },
  {
    id: 'versus',
    emoji: '⚔️',
    name: 'Batalha Comparativa',
    description: 'Compara duas ideias lado a lado',
  },
  {
    id: 'case_study',
    emoji: '📖',
    name: 'Estudo de Caso',
    description: 'Storytelling com licoes praticas',
  },
  {
    id: 'flash_quiz',
    emoji: '🧠',
    name: 'Flash Quiz',
    description: 'Teste de revisao com perguntas',
  },
] as const;

// =============================================================================
// Video Class Labels
// =============================================================================

import type { VideoFormat, VisualTheme } from './types';

export const FORMAT_LABELS: Record<
  VideoFormat,
  { label: string; description: string }
> = {
  brief: {
    label: 'Resumo Rapido',
    description: 'Video curto de 1-2 minutos com os pontos principais',
  },
  explainer: {
    label: 'Explicacao Detalhada',
    description: 'Video completo de 5-8 minutos com explicacao profunda',
  },
};

export const THEME_LABELS: Record<
  VisualTheme,
  { label: string; description: string }
> = {
  corporate: {
    label: 'Corporativo',
    description: 'Profissional, limpo, tons de azul e cinza',
  },
  educational: {
    label: 'Educacional',
    description: 'Amigavel, colorido, estilo infografico',
  },
  anime: {
    label: 'Anime',
    description: 'Vibrante, dinamico, inspirado em Studio Ghibli',
  },
  whiteboard: {
    label: 'Quadro Branco',
    description: 'Desenho a mao, estilo sketch, ilustracoes simples',
  },
};

// =============================================================================
// Storage Keys
// =============================================================================

export const ACADEMY_STORAGE_KEYS = {
  // Session management
  AGENTCORE_SESSION: 'faiston_academy_agentcore_session',
  COGNITO_TOKENS: 'faiston_academy_cognito_tokens',

  // Course classroom storage
  FLASHCARDS_PREFIX: 'faiston_academy_flashcards_',
  MINDMAP_PREFIX: 'faiston_academy_mindmap_',
  AUDIOCLASS_PREFIX: 'faiston_academy_audioclass_',
  AUDIOCLASS_SETTINGS_PREFIX: 'faiston_academy_audioclass_settings_',
  SLIDEDECK_PREFIX: 'faiston_academy_slidedeck_',
  SLIDEDECK_SETTINGS_PREFIX: 'faiston_academy_slidedeck_settings_',
  SLIDEDECK_HISTORY_PREFIX: 'faiston_academy_slidedeck_history_',
  VIDEOCLASS_PREFIX: 'faiston_academy_videoclass_',
  VIDEOCLASS_SETTINGS_PREFIX: 'faiston_academy_videoclass_settings_',
  EXTRACLASS_PREFIX: 'faiston_academy_extraclass_',
  EXTRACLASS_HISTORY_PREFIX: 'faiston_academy_extraclass_history_',
  EXTRACLASS_ACTIVE_PREFIX: 'faiston_academy_extraclass_active_',
  REFLECTION_PREFIX: 'faiston_academy_reflection_',
  YOUTUBE_RECOMMENDATIONS_PREFIX: 'faiston_academy_youtube_',
  NOTES_PREFIX: 'faiston_academy_notes_',
  PROGRESS_PREFIX: 'faiston_academy_progress_',
  LIBRARY_PREFIX: 'faiston_academy_library_',
  TRANSCRIPTION_PREFIX: 'faiston_academy_transcription_',

  // NEXO Tutor training storage
  TRAINING_PREFIX: 'faiston_academy_training_',

  // Live session storage
  LIVE_SESSION_PREFIX: 'faiston_academy_live_',
} as const;
