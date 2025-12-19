# =============================================================================
# AWS Bedrock AgentCore Runtime Entrypoint - Faiston Academy
# =============================================================================
# Main entrypoint for Faiston Academy agents deployed to AgentCore Runtime.
# Uses BedrockAgentCoreApp decorator pattern for serverless deployment.
#
# Framework: Google ADK with native Gemini 3.0 Pro (no LiteLLM wrapper)
# Model: All agents use gemini-3-pro-preview exclusively
#
# Note: Adapted from Hive Academy for Faiston One platform.
# AI Assistant renamed from Sasha to NEXO.
#
# OPTIMIZATION: Lazy imports for faster cold start
# Agents are imported only when needed, reducing initialization time from ~30s to ~10s.
# This is critical for AgentCore Runtime's 30-second initialization limit.
#
# Based on:
# - https://github.com/awslabs/amazon-bedrock-agentcore-samples/tree/main/03-integrations/agentic-frameworks/adk
# - https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/using-any-agent-framework.html
# =============================================================================

# Note: GOOGLE_API_KEY is passed via --env at deploy time (not runtime SSM lookup)
# This follows the AWS official example pattern.

from bedrock_agentcore.runtime import BedrockAgentCoreApp
import asyncio
import json
import os

# LAZY IMPORTS: Agents are imported inside handler functions to reduce cold start time.
# Each agent imports Google ADK packages (~3-5s each), so importing all 5 at startup = ~15-25s.
# By lazy loading, we only pay the import cost for the agent actually being used.

# =============================================================================
# AgentCore Application
# =============================================================================

app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict, context) -> dict:
    """
    Main entrypoint for AgentCore Runtime.

    Routes requests to the appropriate agent based on the 'action' field.

    Args:
        payload: Request payload containing action and parameters
        context: AgentCore context with session_id, etc.

    Returns:
        Agent response as dict
    """
    action = payload.get("action", "nexo_chat")
    user_id = payload.get("user_id", "anonymous")
    session_id = getattr(context, "session_id", "default-session")

    # Route to appropriate agent
    try:
        if action == "nexo_chat":
            return asyncio.run(_nexo_chat(payload, user_id, session_id))

        elif action == "generate_flashcards":
            return asyncio.run(_generate_flashcards(payload))

        elif action == "generate_mindmap":
            return asyncio.run(_generate_mindmap(payload))

        elif action == "analyze_reflection":
            return asyncio.run(_analyze_reflection(payload))

        elif action == "generate_audio_class":
            return asyncio.run(_generate_audio_class(payload))

        elif action == "search_youtube":
            return asyncio.run(_search_youtube(payload, user_id, session_id))

        # Video Class action (synchronous - like AudioClass)
        elif action == "generate_video_class":
            return asyncio.run(_generate_video_class(payload, user_id))

        elif action == "generate_slidedeck":
            return asyncio.run(_generate_slidedeck(payload))

        # Slide Deck v4: Batch-based parallel generation (fits within 120s timeout)
        elif action == "slidedeck_plan":
            return asyncio.run(_slidedeck_plan(payload))

        elif action == "slidedeck_batch":
            return asyncio.run(_slidedeck_batch(payload))

        # Extra Class actions (HeyGen video generation)
        elif action == "validate_doubt":
            return asyncio.run(_validate_doubt(payload))

        elif action == "generate_extra_class":
            return asyncio.run(_generate_extra_class(payload))

        elif action == "check_extra_class_status":
            return asyncio.run(_check_extra_class_status(payload))

        elif action == "wait_extra_class_video":
            return asyncio.run(_wait_extra_class_video(payload))

        # =============================================================================
        # Custom Training Actions (NEXO Tutor)
        # =============================================================================
        elif action == "create_training":
            return asyncio.run(_create_training(payload, user_id))

        elif action == "get_training":
            return asyncio.run(_get_training(payload, user_id))

        elif action == "list_trainings":
            return asyncio.run(_list_trainings(payload, user_id))

        elif action == "delete_training":
            return asyncio.run(_delete_training(payload, user_id))

        elif action == "add_document_source":
            return asyncio.run(_add_document_source(payload, user_id))

        elif action == "add_url_source":
            return asyncio.run(_add_url_source(payload, user_id))

        elif action == "add_youtube_source":
            return asyncio.run(_add_youtube_source(payload, user_id))

        elif action == "process_document_source":
            return asyncio.run(_process_document_source(payload, user_id))

        elif action == "consolidate_training_content":
            return asyncio.run(_consolidate_training_content(payload, user_id))

        elif action == "generate_training_summary":
            return asyncio.run(_generate_training_summary(payload, user_id))

        elif action == "generate_thumbnail":
            return asyncio.run(_generate_thumbnail(payload, user_id))

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {"error": str(e), "action": action}


# =============================================================================
# Agent Handlers
# =============================================================================


async def _nexo_chat(payload: dict, user_id: str, session_id: str) -> dict:
    """
    Handle NEXO AI tutor chat requests.

    NEXO is a RAG-based tutoring agent that answers questions
    based on episode transcription content.
    """
    # Lazy import to reduce cold start time
    from agents.nexo_agent import NexoAgent
    agent = NexoAgent()

    question = payload.get("question", "")
    transcription = payload.get("transcription", "")
    history = payload.get("history", [])

    # Format history for context
    history_text = ""
    for msg in history[-10:]:  # Last 10 messages for context
        role = msg.get("role", "user")
        content = msg.get("content", "")
        history_text += f"{role.upper()}: {content}\n"

    # Build prompt with transcription context
    prompt = f"""
Transcricao da aula (use APENAS este conteudo para responder):
{transcription}

Historico da conversa:
{history_text}

Pergunta do aluno:
{question}

Responda de forma acolhedora, didatica e acessivel. NUNCA revele que suas respostas vem da transcricao.
"""

    # Invoke agent
    response = await agent.invoke(prompt, user_id, session_id)

    # Save to AgentCore Memory
    agent.save_to_memory(session_id, user_id, {"role": "user", "content": question})
    agent.save_to_memory(session_id, user_id, {"role": "assistant", "content": response})

    return {"answer": response}


async def _generate_flashcards(payload: dict) -> dict:
    """
    Handle flashcard generation requests.

    Generates study flashcards from transcription content
    following Anki/SuperMemo best practices.
    """
    # Lazy import to reduce cold start time
    from agents.flashcards_agent import FlashcardsAgent
    agent = FlashcardsAgent()

    return await agent.generate(
        transcription=payload.get("transcription", ""),
        difficulty=payload.get("difficulty", "medium"),
        count=payload.get("count", 10),
        custom_prompt=payload.get("custom_prompt", ""),
    )


async def _generate_mindmap(payload: dict) -> dict:
    """
    Handle mind map generation requests.

    Generates hierarchical mind map with timestamps
    for video navigation.
    """
    # Lazy import to reduce cold start time
    from agents.mindmap_agent import MindMapAgent
    agent = MindMapAgent()

    return await agent.generate(
        transcription=payload.get("transcription", ""),
        episode_title=payload.get("episode_title", "Aula"),
    )


async def _analyze_reflection(payload: dict) -> dict:
    """
    Handle reflection analysis requests.

    Analyzes student reflections and provides
    feedback with video timestamps for review.
    """
    # Lazy import to reduce cold start time
    from agents.reflection_agent import ReflectionAgent
    agent = ReflectionAgent()

    return await agent.analyze(
        transcription=payload.get("transcription", ""),
        reflection=payload.get("reflection", ""),
    )


async def _generate_audio_class(payload: dict) -> dict:
    """
    Handle audio class generation requests.

    Generates podcast-style audio lessons with
    ElevenLabs TTS using selected voice names as hosts.

    Users can select from 3 male and 3 female voices:
    - Female: Sarah, Jessica, Lily
    - Male: Eric, Chris, Brian
    """
    # Lazy import to reduce cold start time
    from agents.audioclass_agent import AudioClassAgent
    agent = AudioClassAgent()

    return await agent.generate(
        transcription=payload.get("transcription", ""),
        mode=payload.get("mode", "deep_explanation"),
        student_name=payload.get("student_name", "Aluno"),
        custom_prompt=payload.get("custom_prompt", ""),
        episode_id=payload.get("episode_id", "unknown"),
        male_voice_id=payload.get("male_voice_id"),
        female_voice_id=payload.get("female_voice_id"),
        male_voice_name=payload.get("male_voice_name", "Eric"),
        female_voice_name=payload.get("female_voice_name", "Sarah"),
    )


async def _search_youtube(payload: dict, user_id: str, session_id: str) -> dict:
    """
    Handle YouTube video search requests.

    Uses NEXO to generate search queries from transcription,
    then searches YouTube Data API v3 for real videos.

    This is an all-in-one endpoint that:
    1. Uses AI to generate relevant search queries
    2. Calls YouTube API directly (no Lambda proxy)
    3. Returns real video metadata (id, title, thumbnail, channel)
    """
    transcription = payload.get("transcription", "")
    episode_title = payload.get("episode_title", "Aula")
    category = payload.get("category", "Educacao")

    if not transcription:
        return {"success": False, "videos": [], "error": "Transcription required"}

    # Lazy imports to reduce cold start time
    from agents.nexo_agent import NexoAgent
    from tools.youtube_tool import search_multiple_videos

    # Step 1: Use NEXO to generate search queries
    agent = NexoAgent()

    # Chain-of-thought prompt for better query relevance
    # Forces AI to identify main topic BEFORE generating queries
    query_prompt = f"""
Voce e uma assistente especializada em gerar consultas de busca para YouTube educacional.

## PASSO 1: Identificacao do Tema Principal
Analise o titulo da aula e identifique o tema central:
- **Titulo da Aula:** "{episode_title}"
- **Categoria:** {category}

Antes de gerar consultas, declare:
TEMA PRINCIPAL: [extraia do titulo - ex: "Codigo de Conduta" = compliance, etica corporativa]
PALAVRAS-CHAVE: [2-3 termos centrais que DEVEM aparecer nas consultas]

## PASSO 2: O que IGNORAR na Transcricao
A transcricao contem dialogos e cenarios. IGNORE COMPLETAMENTE:
- Dialogos casuais (bom dia, cafe, conversas pessoais)
- Descricoes de cenario (cafeteria, escritorio, maquina de cafe)
- Nomes de personagens e interacoes pessoais
- Analogias e metaforas (carros, maquinas, objetos usados como exemplo)
- Mencoes tangenciais de tecnologias ou ferramentas

## PASSO 3: O que FOCAR
FOQUE APENAS em conceitos que correspondam ao TITULO da aula:
- Termos tecnicos da area ({category})
- Conceitos ensinados explicitamente relacionados ao titulo
- Problemas e solucoes do tema principal

## Transcricao (apenas para contexto, NAO para extrair topicos):
{transcription[:1500]}

## PASSO 4: Geracao de Consultas
Gere exatamente 4 consultas de busca seguindo estas REGRAS OBRIGATORIAS:

1. **Consultas 1 e 2:** DEVEM conter palavras do titulo "{episode_title}"
2. **Consultas 3 e 4:** Podem expandir para conceitos diretamente relacionados ao tema
3. Todas em portugues brasileiro
4. Use termos educativos: explicacao, tutorial, o que e, como funciona
5. Cada consulta com 3-6 palavras

## Exemplos por Categoria:

### Categoria "Corporativo" + Titulo "Codigo de Conduta":
TEMA: compliance, etica empresarial
CORRETO: ["codigo de conduta empresarial", "etica corporativa explicacao", "compliance o que e", "integridade no trabalho"]
ERRADO: ["como fazer cafe", "organizacao de escritorio", "gestao de cafeteria"]

### Categoria "Self-Improvement" + Titulo "5 Second Rule":
TEMA: produtividade, vencer procrastinacao
CORRETO: ["regra dos 5 segundos Mel Robbins", "como vencer procrastinacao", "motivacao para agir", "habitos de sucesso"]
ERRADO: ["como trocar marcha carro", "manual de carro", "dirigir carro manual"]

## Sua Resposta
Primeiro, identifique o tema:
TEMA PRINCIPAL: [seu texto aqui]
PALAVRAS-CHAVE: [seus termos aqui]

Depois, retorne APENAS o array JSON (sem explicacoes adicionais):
["consulta com palavra do titulo", "consulta com palavra do titulo", "consulta relacionada", "consulta relacionada"]
"""

    try:
        # Get search queries from NEXO
        response = await agent.invoke(query_prompt, user_id, session_id)

        # Parse JSON array from response
        import re
        json_match = re.search(r'\[[\s\S]*?\]', response)

        if not json_match:
            return {"success": False, "videos": [], "error": "AI did not return expected format"}

        queries = json.loads(json_match.group(0))

        if not isinstance(queries, list) or len(queries) == 0:
            return {"success": False, "videos": [], "error": "No search queries generated"}

        # Step 2: Search YouTube for real videos
        videos = search_multiple_videos(queries[:4])

        if not videos:
            return {"success": True, "videos": [], "queries": queries, "error": "No videos found"}

        return {
            "success": True,
            "videos": videos,
            "queries": queries,
        }

    except ValueError as e:
        # API key or quota issues
        return {"success": False, "videos": [], "error": str(e)}
    except Exception as e:
        print(f"[YouTube] Search error: {e}")
        return {"success": False, "videos": [], "error": f"Search failed: {str(e)}"}


# =============================================================================
# Slide Deck Handler
# =============================================================================


async def _generate_slidedeck(payload: dict) -> dict:
    """
    Handle slide deck generation requests (v3 - LEGACY, may timeout).

    WARNING: This is the legacy endpoint that generates all slides in one call.
    For large decks (8+ slides), this will exceed the 120s AgentCore timeout.

    Use slidedeck_plan + slidedeck_batch for production (v4 architecture).

    Returns slide deck with S3 image URLs for React rendering.
    """
    # Lazy import to reduce cold start time
    from agents.slidedeck_agent import SlideDeckAgent
    agent = SlideDeckAgent()

    return await agent.generate(
        transcription=payload.get("transcription", ""),
        episode_title=payload.get("episode_title", "Aula"),
        episode_id=payload.get("episode_id", "unknown"),
        custom_prompt=payload.get("custom_prompt", ""),
    )


async def _slidedeck_plan(payload: dict) -> dict:
    """
    Slide Deck v4/v5 - PHASE 1: Create slide plan (~10-15 seconds).

    This extracts concepts from the transcription and creates a generation plan.
    The frontend uses this plan to orchestrate parallel batch generation.

    v5: Now supports 5 pedagogical archetypes that guide slide style:
    - deep_dive: Explain ONE concept in depth
    - how_to: Step-by-step tutorial
    - versus: Compare two ideas side by side
    - case_study: Storytelling with practical lessons
    - flash_quiz: Review questions for testing knowledge

    Returns:
    - deck_title: Episode title
    - total_slides: Total number of slides
    - concepts: List of concepts for content slides
    - batches: Recommended batch assignments for parallel generation
    - archetype: The selected pedagogical style

    Timing: ~10-15 seconds (well under 120s limit)
    """
    # Lazy import to reduce cold start time
    from agents.slidedeck_agent import SlideDeckAgent
    agent = SlideDeckAgent()

    return await agent.plan(
        transcription=payload.get("transcription", ""),
        episode_title=payload.get("episode_title", "Aula"),
        archetype=payload.get("archetype", "deep_dive"),  # v5: Pedagogical style
    )


async def _slidedeck_batch(payload: dict) -> dict:
    """
    Slide Deck v4 - PHASE 2: Generate a batch of slides (~60-90 seconds).

    This generates 1-3 slides per batch. Each batch is designed to complete
    well under the 120s AgentCore timeout.

    The frontend makes parallel calls to this endpoint for each batch,
    then aggregates the results.

    Args:
        batch_type: "cover", "content", or "closing"
        episode_title: Title of the episode
        episode_id: Unique identifier for S3 organization
        concepts: Full concept list from plan (for content batches)
        concept_indices: Which concepts to generate (0-based)
        slide_indices: Which slide numbers to generate

    Returns:
        slides: Array of generated slides with image_url

    Timing: ~30s for cover/closing, ~60-90s for content (3 slides)
    """
    # Lazy import to reduce cold start time
    from agents.slidedeck_agent import SlideDeckAgent
    agent = SlideDeckAgent()

    return await agent.generate_batch(
        batch_type=payload.get("batch_type", "content"),
        episode_title=payload.get("episode_title", "Aula"),
        episode_id=payload.get("episode_id", "unknown"),
        concepts=payload.get("concepts", []),
        concept_indices=payload.get("concept_indices", []),
        slide_indices=payload.get("slide_indices", []),
        style=payload.get("style", "corporate"),
        generation_id=payload.get("generation_id"),  # v6: Prevent S3 path collision
    )


# =============================================================================
# Video Class Handler (Synchronous Pattern - like AudioClass)
# =============================================================================


async def _generate_video_class(payload: dict, user_id: str) -> dict:
    """
    Handle video class generation requests.

    Uses SYNCHRONOUS pattern (like AudioClassAgent):
    - Returns video_url directly (no task_id, no polling)
    - Well within AgentCore's 15-minute timeout
    - MVP returns audio + slide metadata (video composition in Phase 2)
    """
    # Lazy import to reduce cold start time
    from agents.video_agent import VideoClassAgent
    agent = VideoClassAgent()

    return await agent.generate(
        transcription=payload.get("transcription", ""),
        format=payload.get("format", "brief"),
        visual_theme=payload.get("visual_theme", "educational"),
        custom_prompt=payload.get("custom_prompt", ""),
        episode_id=payload.get("episode_id", ""),
        user_id=user_id,
    )


# =============================================================================
# Extra Class Handlers (HeyGen Video Generation)
# =============================================================================


async def _validate_doubt(payload: dict) -> dict:
    """
    Validate if student doubt relates to lesson content.

    Returns validation result with is_valid, message, and topics.
    This is Phase 1 of the Extra Class flow.
    """
    # Lazy import to reduce cold start time
    from agents.extraclass_agent import ExtraClassAgent
    agent = ExtraClassAgent()

    return await agent.validate_doubt(
        transcription=payload.get("transcription", ""),
        doubt=payload.get("doubt", ""),
    )


async def _generate_extra_class(payload: dict) -> dict:
    """
    Generate personalized video lesson for student's doubt.

    Full flow: validate doubt -> generate script -> create HeyGen video.
    Returns video_id for status polling.

    This is the main entry point for Extra Class feature.
    """
    # Lazy import to reduce cold start time
    from agents.extraclass_agent import ExtraClassAgent
    agent = ExtraClassAgent()

    return await agent.generate_video(
        transcription=payload.get("transcription", ""),
        doubt=payload.get("doubt", ""),
        episode_id=payload.get("episode_id", "unknown"),
        student_name=payload.get("student_name", "Aluno"),
    )


async def _check_extra_class_status(payload: dict) -> dict:
    """
    Check the status of a HeyGen video being generated.

    Poll this endpoint until status is 'completed' or 'failed'.
    Frontend should poll every 10 seconds.
    """
    # Lazy import to reduce cold start time
    from agents.extraclass_agent import ExtraClassAgent
    agent = ExtraClassAgent()

    return await agent.check_video_status(
        video_id=payload.get("video_id", ""),
    )


async def _wait_extra_class_video(payload: dict) -> dict:
    """
    Wait for HeyGen video completion with robust polling.

    This is a blocking endpoint that polls HeyGen until the video is ready.
    It uses progressive backoff (10s -> 30s intervals) and returns when:
    - Video is completed (status: "completed", video_url included)
    - Video failed (status: "failed", error included)
    - Timeout reached (status: "timeout", error included)

    Args:
        video_id: HeyGen video ID from generate_extra_class
        timeout_seconds: Maximum wait time (default: 600s / 10 min)

    Returns:
        Dict with:
        - status: "completed" | "failed" | "timeout" | "error"
        - video_url: URL when completed
        - thumbnail_url: Thumbnail when completed
        - duration: Video duration when completed
        - error: Error message if any
        - elapsed_seconds: Total time waited
        - poll_count: Number of status checks made

    Note: This is useful for fire-and-forget video generation where
    you want to wait for completion in a single request. For UI with
    progress updates, use check_extra_class_status with frontend polling.
    """
    # Lazy import to reduce cold start time
    from agents.extraclass_agent import ExtraClassAgent
    agent = ExtraClassAgent()

    video_id = payload.get("video_id", "")
    if not video_id:
        return {"status": "error", "error": "video_id is required"}

    timeout_seconds = payload.get("timeout_seconds", 600)

    return await agent.wait_for_video(
        video_id=video_id,
        timeout_seconds=timeout_seconds,
    )


# =============================================================================
# Custom Training Handlers (NEXO Tutor)
# =============================================================================


async def _create_training(payload: dict, user_id: str) -> dict:
    """
    Create a new custom training.

    This initializes a new training in DynamoDB with draft status.
    The user can then add sources before processing.
    """
    # Lazy import to reduce cold start time
    from agents.training_agent import TrainingAgent
    agent = TrainingAgent()

    return await agent.create_training(
        title=payload.get("title", "Novo Treinamento"),
        description=payload.get("description", ""),
        user_id=user_id,
        tenant_id=payload.get("tenant_id", "faiston-academy"),
        category=payload.get("category", "Geral"),
    )


async def _get_training(payload: dict, user_id: str) -> dict:
    """
    Get a training by ID.

    Returns full training data including sources and consolidated content.

    Note: user_id is NOT passed to get_training for READ operations.
    The unique training_id (UUID-based) provides sufficient security.
    This follows "anyone with the link can view" model.
    """
    # Lazy import to reduce cold start time
    from agents.training_agent import TrainingAgent
    agent = TrainingAgent()

    # Don't pass user_id for GET - training_id is the security boundary
    # This avoids "Access denied" when user_id doesn't match exactly
    return await agent.get_training(
        training_id=payload.get("training_id", ""),
        user_id=None,  # Skip ownership check for read operations
    )


async def _list_trainings(payload: dict, user_id: str) -> dict:
    """
    List trainings for a user.

    Returns paginated list ordered by creation date (newest first).
    """
    # Lazy import to reduce cold start time
    from agents.training_agent import TrainingAgent
    agent = TrainingAgent()

    return await agent.list_trainings(
        user_id=user_id,
        tenant_id=payload.get("tenant_id", "faiston-academy"),
        status=payload.get("status"),
        limit=payload.get("limit", 20),
        last_key=payload.get("last_key"),
    )


async def _delete_training(payload: dict, user_id: str) -> dict:
    """
    Delete a training.

    Removes training and all associated sources from DynamoDB.
    S3 files are cleaned up asynchronously.
    """
    # Lazy import to reduce cold start time
    from agents.training_agent import TrainingAgent
    agent = TrainingAgent()

    return await agent.delete_training(
        training_id=payload.get("training_id", ""),
        user_id=user_id,
    )


async def _add_document_source(payload: dict, user_id: str) -> dict:
    """
    Add a document source to a training.

    Returns a presigned URL for the frontend to upload the document.
    The document will be processed after upload using process_document_source.
    """
    # Lazy import to reduce cold start time
    from agents.training_agent import TrainingAgent
    agent = TrainingAgent()

    return await agent.add_document_source(
        training_id=payload.get("training_id", ""),
        user_id=user_id,
        file_name=payload.get("file_name", ""),
        file_type=payload.get("file_type", "application/pdf"),
        file_size=payload.get("file_size", 0),
    )


async def _add_url_source(payload: dict, user_id: str) -> dict:
    """
    Add a URL source to a training.

    The URL is scraped immediately and content is extracted.
    Supports articles, documentation, and blog posts.
    """
    # Lazy import to reduce cold start time
    from agents.training_agent import TrainingAgent
    agent = TrainingAgent()

    return await agent.add_url_source(
        training_id=payload.get("training_id", ""),
        user_id=user_id,
        url=payload.get("url", ""),
    )


async def _add_youtube_source(payload: dict, user_id: str) -> dict:
    """
    Add a YouTube source to a training.

    Adds the video for transcript extraction during processing.
    """
    # Lazy import to reduce cold start time
    from agents.training_agent import TrainingAgent
    agent = TrainingAgent()

    return await agent.add_youtube_source(
        training_id=payload.get("training_id", ""),
        user_id=user_id,
        youtube_url=payload.get("youtube_url", ""),
    )


async def _process_document_source(payload: dict, user_id: str) -> dict:
    """
    Process an uploaded document source.

    Called after the frontend uploads the document to S3.
    Extracts text content from PDF, DOCX, or TXT files.
    """
    # Lazy import to reduce cold start time
    from agents.training_agent import TrainingAgent
    agent = TrainingAgent()

    training_id = payload.get("training_id", "")
    source_id = payload.get("source_id", "")

    if not training_id or not source_id:
        return {"success": False, "error": "training_id and source_id are required"}

    # Use the agent's built-in method
    return await agent.process_document_source(
        training_id=training_id,
        source_id=source_id,
    )


async def _consolidate_training_content(payload: dict, user_id: str) -> dict:
    """
    Consolidate all sources into unified training content.

    Merges text from all processed sources into a single document.
    This becomes the transcription for AI features.
    """
    # Lazy import to reduce cold start time
    from agents.training_agent import TrainingAgent
    agent = TrainingAgent()

    # Note: user_id=None skips ownership check for read operations
    return await agent.consolidate_content(
        training_id=payload.get("training_id", ""),
        user_id=None,
    )


async def _generate_training_summary(payload: dict, user_id: str) -> dict:
    """
    Generate AI summary for a training.

    Uses NEXO AI to create a concise overview of the training content.
    """
    # Lazy import to reduce cold start time
    from agents.training_agent import TrainingAgent
    agent = TrainingAgent()

    # Note: user_id=None skips ownership check for read operations
    return await agent.generate_summary(
        training_id=payload.get("training_id", ""),
        user_id=None,
    )


async def _generate_thumbnail(payload: dict, user_id: str) -> dict:
    """
    Generate AI thumbnail for a training.

    Uses ThumbnailAgent to create a visual representation of the training.
    """
    # Lazy import to reduce cold start time
    from agents.thumbnail_agent import ThumbnailAgent
    agent = ThumbnailAgent()

    training_id = payload.get("training_id", "")

    # Get training data first
    from agents.training_agent import TrainingAgent
    training_agent = TrainingAgent()

    # Note: user_id=None skips ownership check for read operations
    # The unique training_id (UUID) provides sufficient security
    training_result = await training_agent.get_training(training_id, user_id=None)
    if not training_result.get("success"):
        return training_result

    training = training_result.get("training", {})

    return await agent.generate(
        training_id=training_id,
        title=training.get("title", ""),
        description=training.get("description", ""),
        category=training.get("category", "Geral"),
        content_preview=training.get("consolidated_content", "")[:2000],
    )


# =============================================================================
# Run Application
# =============================================================================

if __name__ == "__main__":
    app.run()
