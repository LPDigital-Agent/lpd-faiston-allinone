// =============================================================================
// Academy AgentCore Service - Faiston Academy
// =============================================================================
// Purpose: Invoke AWS Bedrock AgentCore Runtime directly from the React SPA
// using JWT Bearer Token authentication.
//
// This service handles all AI features for Faiston Academy:
// - NEXO AI Chat (renamed from Sasha)
// - Flashcards generation
// - MindMap generation
// - Audio Class generation (ElevenLabs TTS)
// - Video Class generation
// - Slide Deck generation
// - Extra Class generation (HeyGen)
// - Reflection analysis
// - YouTube search
//
// Agent ARN: arn:aws:bedrock-agentcore:us-east-2:377311924364:runtime/faiston_academy_agents-ODNvP6HxCD
// =============================================================================

import { getAccessToken } from './authService';
import { ACADEMY_STORAGE_KEYS } from '@/lib/academy/constants';
import type {
  FlashcardsRequest,
  FlashcardsResponse,
  MindMapRequest,
  MindMapResponse,
  NexoChatRequest,
  NexoChatResponse,
  ReflectionRequest,
  ReflectionResponse,
  AudioClassRequest,
  AudioClassResponse,
  YouTubeSearchRequest,
  YouTubeSearchResponse,
  VideoClassRequest,
  VideoClassResponse,
  SlideDeckRequest,
  SlideDeckResponse,
  SlideDeckPlanRequest,
  SlideDeckPlanResponse,
  SlideBatchRequest,
  SlideBatchResponse,
  ExtraClassRequest,
  ExtraClassResponse,
  ValidateDoubtRequest,
  ValidateDoubtResponse,
  GenerateExtraClassRequest,
  GenerateExtraClassResponse,
  CheckExtraClassStatusRequest,
  CheckExtraClassStatusResponse,
} from '@/lib/academy/types';

// =============================================================================
// Configuration
// =============================================================================

const AGENTCORE_ENDPOINT =
  process.env.NEXT_PUBLIC_ACADEMY_AGENTCORE_ENDPOINT ||
  'https://bedrock-agentcore.us-east-2.amazonaws.com';

const AGENTCORE_ARN =
  process.env.NEXT_PUBLIC_ACADEMY_AGENTCORE_ARN ||
  'arn:aws:bedrock-agentcore:us-east-2:377311924364:runtime/faiston_academy_agents-ODNvP6HxCD';

// =============================================================================
// Types
// =============================================================================

export interface AgentCoreRequest {
  action: string;
  [key: string]: unknown;
}

export interface AgentCoreResponse<T = unknown> {
  data: T;
  sessionId: string;
}

export interface InvokeOptions {
  useSession?: boolean;
  signal?: AbortSignal;
}

// =============================================================================
// Retry Configuration
// =============================================================================

const RETRY_CONFIG = {
  maxRetries: 3,
  initialDelayMs: 3000,
  retryableStatuses: [502, 503, 504],
};

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// =============================================================================
// Session Management
// =============================================================================

function generateSessionId(): string {
  return `session-${crypto.randomUUID().replace(/-/g, '')}`;
}

export function getSessionId(): string {
  if (typeof window === 'undefined') return generateSessionId();

  try {
    let sessionId = sessionStorage.getItem(ACADEMY_STORAGE_KEYS.AGENTCORE_SESSION);
    if (!sessionId) {
      sessionId = generateSessionId();
      sessionStorage.setItem(ACADEMY_STORAGE_KEYS.AGENTCORE_SESSION, sessionId);
    }
    return sessionId;
  } catch {
    return generateSessionId();
  }
}

export function clearSession(): void {
  if (typeof window === 'undefined') return;

  try {
    sessionStorage.removeItem(ACADEMY_STORAGE_KEYS.AGENTCORE_SESSION);
  } catch {
    // sessionStorage not available
  }
}

// =============================================================================
// Core Invocation
// =============================================================================

export async function invokeAgentCore<T = unknown>(
  request: AgentCoreRequest,
  options: InvokeOptions | boolean = true
): Promise<AgentCoreResponse<T>> {
  const opts: InvokeOptions = typeof options === 'boolean'
    ? { useSession: options }
    : options;
  const { useSession = true, signal } = opts;

  // Get JWT token from authService (same Cognito user pool used for login)
  const token = await getAccessToken();
  if (!token) {
    throw new Error('Nao autenticado. Por favor, faca login novamente.');
  }

  // Build URL
  const encodedArn = encodeURIComponent(AGENTCORE_ARN);
  const url = `${AGENTCORE_ENDPOINT}/runtimes/${encodedArn}/invocations?qualifier=DEFAULT`;

  // Get session ID
  const sessionId = useSession ? getSessionId() : generateSessionId();

  // Retry loop
  let lastError: Error | null = null;
  for (let attempt = 0; attempt <= RETRY_CONFIG.maxRetries; attempt++) {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
        'X-Amzn-Bedrock-AgentCore-Runtime-Session-Id': sessionId,
      },
      body: JSON.stringify(request),
      signal,
    });

    if (!response.ok) {
      const errorBody = await response.text();
      let errorMessage = `AgentCore error: ${response.status} ${response.statusText}`;

      try {
        const errorJson = JSON.parse(errorBody);
        errorMessage = errorJson.message || errorJson.Message || errorMessage;
      } catch {
        if (errorBody) {
          errorMessage = errorBody;
        }
      }

      if (response.status === 401) {
        throw new Error('Sessao expirada. Por favor, faca login novamente.');
      }
      if (response.status === 403) {
        throw new Error('Acesso negado. Verifique suas permissoes.');
      }

      if (RETRY_CONFIG.retryableStatuses.includes(response.status) && attempt < RETRY_CONFIG.maxRetries) {
        const delayMs = RETRY_CONFIG.initialDelayMs * Math.pow(2, attempt);
        console.warn(`[Academy AgentCore] Received ${response.status}, retrying in ${delayMs}ms...`);
        lastError = new Error(errorMessage);
        await sleep(delayMs);
        continue;
      }

      throw new Error(errorMessage);
    }

    // Parse response
    const contentType = response.headers.get('content-type') || '';

    if (contentType.includes('text/event-stream')) {
      const data = await parseSSEResponse<T>(response);
      return { data, sessionId };
    }

    if (contentType.includes('application/json')) {
      const data = (await response.json()) as T;
      return { data, sessionId };
    }

    const text = await response.text();
    try {
      const data = JSON.parse(text) as T;
      return { data, sessionId };
    } catch {
      return { data: text as unknown as T, sessionId };
    }
  }

  throw lastError || new Error('AgentCore request failed after all retries');
}

async function parseSSEResponse<T>(response: Response): Promise<T> {
  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('No response body for streaming');
  }

  const decoder = new TextDecoder();
  const chunks: string[] = [];

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value, { stream: true });
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6);
        if (data && data !== '[DONE]') {
          chunks.push(data);
        }
      }
    }
  }

  const fullResponse = chunks.join('');
  try {
    return JSON.parse(fullResponse) as T;
  } catch {
    return fullResponse as unknown as T;
  }
}

// =============================================================================
// NEXO AI Chat (renamed from Sasha)
// =============================================================================

export async function nexoChat(
  params: NexoChatRequest
): Promise<AgentCoreResponse<NexoChatResponse>> {
  return invokeAgentCore<NexoChatResponse>({
    action: 'nexo_chat',
    question: params.question,
    transcription: params.transcription,
    episode_title: params.episode_title || '',
    conversation_history: params.conversation_history || [],
  });
}

// =============================================================================
// Flashcards
// =============================================================================

export async function generateFlashcards(
  params: FlashcardsRequest
): Promise<AgentCoreResponse<FlashcardsResponse>> {
  return invokeAgentCore<FlashcardsResponse>({
    action: 'generate_flashcards',
    transcription: params.transcription,
    difficulty: params.difficulty || 'medium',
    num_cards: params.count || 10,
    custom_prompt: params.custom_prompt || '',
  });
}

// =============================================================================
// MindMap
// =============================================================================

export async function generateMindMap(
  params: MindMapRequest
): Promise<AgentCoreResponse<MindMapResponse>> {
  return invokeAgentCore<MindMapResponse>({
    action: 'generate_mindmap',
    transcription: params.transcription,
    episode_title: params.episode_title || 'Aula',
  });
}

// =============================================================================
// Reflection
// =============================================================================

export async function analyzeReflection(
  params: ReflectionRequest
): Promise<AgentCoreResponse<ReflectionResponse>> {
  return invokeAgentCore<ReflectionResponse>({
    action: 'analyze_reflection',
    student_explanation: params.reflection,
    transcription: params.transcription,
    episode_title: '',
  });
}

// =============================================================================
// Audio Class
// =============================================================================

export async function generateAudioClass(
  params: AudioClassRequest,
  signal?: AbortSignal
): Promise<AgentCoreResponse<AudioClassResponse>> {
  return invokeAgentCore<AudioClassResponse>(
    {
      action: 'generate_audio_class',
      transcription: params.transcription,
      mode: params.mode || 'deep_explanation',
      student_name: params.student_name || 'Estudante',
      custom_prompt: params.custom_prompt || undefined,
      male_voice_id: params.male_voice_id,
      female_voice_id: params.female_voice_id,
      male_voice_name: params.male_voice_name,
      female_voice_name: params.female_voice_name,
    },
    { signal }
  );
}

// =============================================================================
// YouTube Search
// =============================================================================

export async function searchYouTube(
  params: YouTubeSearchRequest
): Promise<AgentCoreResponse<YouTubeSearchResponse>> {
  return invokeAgentCore<YouTubeSearchResponse>({
    action: 'search_youtube',
    transcription: params.transcription,
    episode_title: params.episode_title || 'Aula',
    category: params.category || 'Educacao',
  });
}

// =============================================================================
// Video Class
// =============================================================================

export async function generateVideoClass(
  params: VideoClassRequest,
  signal?: AbortSignal
): Promise<AgentCoreResponse<VideoClassResponse>> {
  return invokeAgentCore<VideoClassResponse>(
    {
      action: 'generate_video_class',
      transcription: params.transcription,
      format: params.format,
      visual_theme: params.visual_theme,
      custom_prompt: params.custom_prompt || '',
      episode_id: params.episode_id,
    },
    { signal }
  );
}

// =============================================================================
// Slide Deck
// =============================================================================

export async function generateSlideDeck(
  params: SlideDeckRequest
): Promise<AgentCoreResponse<SlideDeckResponse>> {
  return invokeAgentCore<SlideDeckResponse>({
    action: 'generate_slidedeck',
    transcription: params.transcription,
    episode_title: params.episode_title || 'Aula',
    episode_id: params.episode_id || 'unknown',
  });
}

export async function planSlideDeck(
  params: SlideDeckPlanRequest
): Promise<AgentCoreResponse<SlideDeckPlanResponse>> {
  return invokeAgentCore<SlideDeckPlanResponse>({
    action: 'slidedeck_plan',
    transcription: params.transcription,
    episode_title: params.episode_title || 'Aula',
    archetype: params.archetype || 'deep_dive',
  });
}

export async function generateSlideBatch(
  params: SlideBatchRequest,
  signal?: AbortSignal
): Promise<AgentCoreResponse<SlideBatchResponse>> {
  return invokeAgentCore<SlideBatchResponse>(
    {
      action: 'slidedeck_batch',
      batch_type: params.batch_type,
      episode_title: params.episode_title,
      episode_id: params.episode_id,
      concepts: params.concepts || [],
      concept_indices: params.concept_indices || [],
      slide_indices: params.slide_indices,
      style: params.style || 'corporate',
      generation_id: params.generation_id,
    },
    { signal }
  );
}

export interface GenerationProgress {
  phase: 'planning' | 'generating' | 'complete';
  current: number;
  total: number;
  message: string;
}

export async function generateSlideDeckV4(
  params: SlideDeckRequest,
  onProgress?: (progress: GenerationProgress) => void
): Promise<SlideDeckResponse> {
  const episodeId = params.episode_id || 'unknown';
  const episodeTitle = params.episode_title || 'Aula';

  // PHASE 1: Create plan
  onProgress?.({
    phase: 'planning',
    current: 0,
    total: 1,
    message: 'Analisando conteudo...',
  });

  const { data: plan } = await planSlideDeck({
    transcription: params.transcription,
    episode_title: episodeTitle,
    archetype: params.archetype,
  });

  if (!plan || !plan.batches || !Array.isArray(plan.batches)) {
    throw new Error(
      (plan as { error?: string })?.error ||
        'Falha ao criar plano de slides. Por favor, tente novamente.'
    );
  }

  const totalBatches = plan.batches.length;
  onProgress?.({
    phase: 'generating',
    current: 0,
    total: totalBatches,
    message: `Gerando ${plan.total_slides} slides em ${totalBatches} lotes...`,
  });

  // PHASE 2: Generate batches in parallel
  const generationId = plan.generation_id;
  let completedBatches = 0;

  const batchPromises = plan.batches.map(async (batch) => {
    const result = await generateSlideBatch({
      batch_type: batch.slide_type,
      episode_title: episodeTitle,
      episode_id: episodeId,
      concepts: plan.concepts,
      concept_indices: batch.concept_indices,
      slide_indices: batch.slide_indices,
      style: 'corporate',
      generation_id: generationId,
    });

    completedBatches++;
    onProgress?.({
      phase: 'generating',
      current: completedBatches,
      total: totalBatches,
      message: `Lote ${completedBatches}/${totalBatches} concluido`,
    });

    return result;
  });

  const batchResults = await Promise.all(batchPromises);

  // PHASE 3: Aggregate results
  const allSlides = batchResults
    .flatMap(r => r.data.slides)
    .sort((a, b) => a.index - b.index)
    .map(slide => ({
      id: slide.id,
      title: slide.title,
      image_url: slide.image_url,
      speaker_notes: slide.speaker_notes,
    }));

  onProgress?.({
    phase: 'complete',
    current: totalBatches,
    total: totalBatches,
    message: 'Slide deck concluido!',
  });

  return {
    deck_title: plan.deck_title,
    slides: allSlides,
    generatedAt: new Date().toISOString(),
    model: 'gemini-3-pro + imagen-3',
  };
}

// =============================================================================
// Extra Class (HeyGen)
// =============================================================================

/**
 * Validate if a student's doubt relates to the transcription content.
 */
export async function validateDoubt(
  params: ValidateDoubtRequest
): Promise<AgentCoreResponse<ValidateDoubtResponse>> {
  return invokeAgentCore<ValidateDoubtResponse>({
    action: 'validate_doubt',
    transcription: params.transcription,
    doubt: params.doubt,
  });
}

/**
 * Generate personalized extra class video with HeyGen.
 */
export async function generateExtraClass(
  params: GenerateExtraClassRequest,
  signal?: AbortSignal
): Promise<AgentCoreResponse<GenerateExtraClassResponse>> {
  return invokeAgentCore<GenerateExtraClassResponse>(
    {
      action: 'generate_extra_class',
      transcription: params.transcription,
      doubt: params.doubt,
      episode_id: params.episode_id,
      student_name: params.student_name,
    },
    { signal }
  );
}

/**
 * Check the status of a HeyGen video generation.
 */
export async function checkExtraClassStatus(
  params: CheckExtraClassStatusRequest
): Promise<AgentCoreResponse<CheckExtraClassStatusResponse>> {
  return invokeAgentCore<CheckExtraClassStatusResponse>({
    action: 'check_extra_class_status',
    video_id: params.video_id,
  });
}

// =============================================================================
// Configuration Helpers
// =============================================================================

export function getAgentCoreConfig() {
  return {
    endpoint: AGENTCORE_ENDPOINT,
    arn: AGENTCORE_ARN,
    configured: Boolean(AGENTCORE_ARN),
  };
}
