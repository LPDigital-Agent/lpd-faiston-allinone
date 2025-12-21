// =============================================================================
// Academy Types - Faiston Academy
// =============================================================================
// Type definitions for Faiston Academy module.
// Adapted from Hive Academy with NEXO AI (renamed from Sasha).
// =============================================================================

// =============================================================================
// Flashcards Types
// =============================================================================

export interface Flashcard {
  id: string;
  front?: string;
  back?: string;
  question?: string;
  answer?: string;
  tags?: string[];
  difficulty?: 'easy' | 'medium' | 'hard';
}

export interface FlashcardsRequest {
  transcription: string;
  difficulty?: 'easy' | 'medium' | 'hard';
  count?: number;
  custom_prompt?: string;
}

export interface FlashcardsResponse {
  flashcards: Flashcard[];
}

// =============================================================================
// MindMap Types
// =============================================================================

export interface MindMapNode {
  id: string;
  label: string;
  description?: string;
  timestamp?: number;
  children?: MindMapNode[];
}

export interface MindMapRequest {
  transcription: string;
  episode_title?: string;
}

export interface MindMapResponse {
  title: string;
  nodes: MindMapNode[];
  generatedAt: string;
  model?: string;
}

// =============================================================================
// NEXO AI Chat Types (renamed from Sasha)
// =============================================================================

export interface NexoChatRequest {
  question: string;
  transcription: string;
  episode_title?: string;
  conversation_history?: Array<{ role: string; content: string }>;
}

export interface NexoChatResponse {
  answer: string;
}

// =============================================================================
// Reflection Types
// =============================================================================

export interface ReflectionRequest {
  transcription: string;
  reflection: string;
}

export interface ProximoPasso {
  text: string;
  timestamp: number | null;
}

export interface ReflectionResponse {
  overall_score: number;
  coerencia: number;
  completude: number;
  precisao: number;
  pontos_fortes: string[];
  pontos_atencao: string[];
  proximos_passos: ProximoPasso[];
  xp_earned: number;
  model: string;
}

// =============================================================================
// Audio Class Types
// =============================================================================

export type AudioClassMode = 'deep_explanation' | 'debate' | 'summary';
export type AudioMode = AudioClassMode; // Alias for convenience

export interface AudioClassRequest {
  transcription: string;
  mode?: AudioClassMode;
  student_name?: string;
  custom_prompt?: string;
  episode_id?: string;
  male_voice_id?: string;
  female_voice_id?: string;
  male_voice_name?: string;
  female_voice_name?: string;
}

export interface AudioClassResponse {
  audio_base64?: string;
  audio_url?: string;
  duration_seconds: number;
  mode: string;
  student_name: string;
  male_voice_id?: string;
  female_voice_id?: string;
  male_voice_name?: string;
  female_voice_name?: string;
}

// =============================================================================
// YouTube Search Types
// =============================================================================

export interface YouTubeSearchRequest {
  transcription: string;
  episode_title?: string;
  category?: string;
}

export interface YouTubeVideo {
  videoId: string;
  title: string;
  channelTitle: string;
  thumbnailUrl: string;
  description: string;
  searchQuery: string;
}

export interface YouTubeSearchResponse {
  success: boolean;
  videos: YouTubeVideo[];
  queries?: string[];
  error?: string;
}

// =============================================================================
// Video Class Types
// =============================================================================

export type VideoFormat = 'brief' | 'explainer';
export type VisualTheme = 'corporate' | 'educational' | 'anime' | 'whiteboard';

export interface VideoVisualAsset {
  scene_id: number;
  type: 'text_slide' | 'generated';
  title: string;
  bullets: string[];
  theme: VisualTheme;
  placeholder?: boolean;
}

export interface VideoScene {
  id: number;
  type: 'intro' | 'content' | 'evidence' | 'conclusion';
  narration_text: string;
  visual_asset: {
    type: 'text_slide' | 'generated';
    title: string;
    bullets?: string[];
  };
  transition: 'fade' | 'slide_left' | 'slide_right' | 'zoom';
}

export interface VideoClassRequest {
  transcription: string;
  format: VideoFormat;
  visual_theme: VisualTheme;
  custom_prompt?: string;
  episode_id: string;
}

export interface VideoSlideWithUrl {
  id: number;
  type: string;
  title: string;
  duration_seconds: number;
  image_url: string | null;
}

export interface VideoClassResponse {
  video_url?: string;
  audio_url?: string;
  duration_seconds: number;
  project_title: string;
  slide_count?: number;
  format: VideoFormat;
  visual_theme: VisualTheme;
  slides?: VideoSlideWithUrl[];
  scenes?: VideoScene[];
  visuals?: VideoVisualAsset[];
  is_audio_only: boolean;
  phase: 'mvp' | 'phase2' | 'veo3' | 'slides_tts' | 'slides_tts_mvp';
  error?: string;
  model?: string;
  concepts?: {
    main_concept: string;
    key_points: string[];
    visual_suggestions?: string[];
  };
  roteiro?: {
    title: string;
    slides: Array<{
      id: number;
      type: string;
      title: string;
      duration_seconds: number;
    }>;
  };
}

// =============================================================================
// Slide Deck Types
// =============================================================================

export type DeckArchetype =
  | 'deep_dive'
  | 'how_to'
  | 'versus'
  | 'case_study'
  | 'flash_quiz';

export interface Slide {
  id: string;
  title: string;
  image_url: string;
  speaker_notes?: string;
}

export interface SlideDeckData {
  deck_title: string;
  slides: Slide[];
  generatedAt: string;
  model?: string;
}

export interface SlideDeckRequest {
  transcription: string;
  episode_title?: string;
  episode_id?: string;
  archetype?: DeckArchetype;
}

export interface SlideDeckResponse extends SlideDeckData {
  error?: string;
}

export interface SlideConcept {
  index: number;
  title: string;
  content: string;
  key_points: string[];
  visual_hint: string;
}

export interface SlideBatch {
  batch_index: number;
  slide_type: 'cover' | 'content' | 'closing';
  slide_indices: number[];
  concept_indices?: number[];
  description: string;
}

export interface SlideDeckPlanResponse {
  deck_title: string;
  total_slides: number;
  content_slide_count: number;
  concepts: SlideConcept[];
  batches: SlideBatch[];
  version: string;
  generation_id?: string;
}

export interface BatchSlide extends Slide {
  index: number;
  slide_type: 'cover' | 'content' | 'closing';
}

export interface SlideBatchResponse {
  batch_type: string;
  slides: BatchSlide[];
  generatedAt: string;
}

export interface SlideDeckPlanRequest {
  transcription: string;
  episode_title?: string;
  archetype?: DeckArchetype;
}

export interface SlideBatchRequest {
  batch_type: 'cover' | 'content' | 'closing';
  episode_title: string;
  episode_id: string;
  concepts?: SlideConcept[];
  concept_indices?: number[];
  slide_indices: number[];
  style?: string;
  generation_id?: string;
}

// =============================================================================
// Extra Class Types (HeyGen)
// =============================================================================

export interface ExtraClassTimestamp {
  time: number;
  topic: string;
}

export interface ExtraClassRequest {
  transcription: string;
  episode_title?: string;
  episode_id?: string;
  avatar_id?: string;
  voice_id?: string;
  custom_prompt?: string;
}

export interface ExtraClassResponse {
  video_url?: string;
  video_id?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  duration_seconds?: number;
  error?: string;
}

// Doubt validation
export interface ValidateDoubtRequest {
  transcription: string;
  doubt: string;
}

export interface ValidateDoubtResponse {
  is_valid: boolean;
  message?: string;
  topics?: string[];
}

// Extra class generation
export interface GenerateExtraClassRequest {
  transcription: string;
  doubt: string;
  episode_id: string;
  student_name: string;
}

export interface GenerateExtraClassResponse {
  is_valid: boolean;
  message?: string;
  video_id?: string;
  script?: string;
  timestamps?: ExtraClassTimestamp[];
  topics?: string[];
  phase?: 'video_created' | 'video_error';
  error?: string;
}

// Status check
export interface CheckExtraClassStatusRequest {
  video_id: string;
}

export interface CheckExtraClassStatusResponse {
  status: 'waiting' | 'pending' | 'processing' | 'completed' | 'failed' | 'error';
  video_url?: string;
  thumbnail_url?: string;
  duration?: number;
  error?: string;
}

// =============================================================================
// Training Types (NEXO Tutor - Custom Trainings)
// =============================================================================

export interface Training {
  training_id: string;
  title: string;
  description?: string;
  thumbnail_url?: string;
  status: 'draft' | 'processing' | 'ready' | 'error';
  created_at: string;
  updated_at: string;
  source_count: number;
  user_id: string;
}

export interface TrainingSource {
  source_id: string;
  training_id: string;
  type: 'document' | 'url' | 'youtube';
  title: string;
  status: 'pending' | 'processing' | 'ready' | 'error';
  created_at: string;
}

export interface CreateTrainingRequest {
  title: string;
  description?: string;
}

export interface CreateTrainingResponse {
  training: Training;
}

export interface AddSourceRequest {
  training_id: string;
  type: 'document' | 'url' | 'youtube';
  content: string; // URL or base64 content
  title?: string;
}

export interface AddSourceResponse {
  source: TrainingSource;
}

// =============================================================================
// Course & Episode Types
// =============================================================================

export interface Episode {
  id: string;
  courseId: string;
  title: string;
  description?: string;
  duration: number;
  videoUrl: string;
  thumbnailUrl?: string;
  order: number;
  transcription?: string;
  status: 'locked' | 'available' | 'completed';
  progress?: number;
}

export interface Course {
  id: string;
  title: string;
  description: string;
  thumbnailUrl: string;
  category: string;
  instructor: {
    name: string;
    avatar?: string;
    bio?: string;
  };
  episodes: Episode[];
  totalDuration: number;
  episodeCount: number;
  enrolledCount?: number;
  rating?: number;
  status: 'not_started' | 'in_progress' | 'completed';
  progress?: number;
}

// =============================================================================
// Gamification Types
// =============================================================================

export interface UserStats {
  totalXp: number;
  level: number;
  streak: number;
  coursesCompleted: number;
  episodesWatched: number;
  flashcardsStudied: number;
  reflectionsSubmitted: number;
}

export interface Badge {
  id: string;
  name: string;
  description: string;
  iconUrl: string;
  earnedAt?: string;
  progress?: number;
  requirement: number;
}

export interface LeaderboardEntry {
  rank: number;
  userId: string;
  userName: string;
  userAvatar?: string;
  xp: number;
  level: number;
}
