# =============================================================================
# Extra Class Agent - Gemini 3.0 Pro Native
# =============================================================================
# Agent that validates student doubts against lesson content and generates
# personalized video lesson scripts for HeyGen avatar generation.
#
# Framework: Google ADK with native Gemini 3.0 Pro
# Integration: HeyGen API for avatar video generation
#
# Two-Phase Flow:
# 1. validate_doubt: Check if doubt relates to lesson transcription
# 2. generate_script: Create educational video script with timestamps
#
# Created: December 2025
# =============================================================================

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from .utils import APP_NAME, MODEL_GEMINI, parse_json_safe
from typing import Dict, Any, List
import re

# Import HeyGen tool for video generation (V2 API)
from tools.heygen_tool import (
    create_video,
    get_video_status,
    validate_script,
    estimate_video_duration,
    poll_until_complete_async,
)

# =============================================================================
# System Instructions
# =============================================================================

VALIDATION_INSTRUCTION = """
Você é um assistente especializado em análise educacional.

Sua tarefa é verificar se a dúvida do aluno está relacionada ao conteúdo da aula (transcrição fornecida).

## Critérios de Validação

Uma dúvida é VÁLIDA se:
1. Menciona conceitos, termos ou ideias presentes na transcrição
2. Pede esclarecimento sobre algo explicado na aula
3. Busca exemplos práticos de conceitos da aula
4. Quer entender melhor uma parte específica do conteúdo

Uma dúvida é INVÁLIDA se:
1. Não tem relação com nenhum tópico da transcrição
2. É sobre assuntos completamente diferentes da aula
3. É uma pergunta genérica sem conexão com o conteúdo
4. É spam ou não faz sentido

## Formato de Resposta (JSON)
{
    "is_valid": true/false,
    "message": "Mensagem explicativa para o aluno",
    "topics": ["tópico1", "tópico2"] // Lista de tópicos relacionados (se válido)
}

Se VÁLIDO: message deve ser encorajadora
Se INVÁLIDO: message deve ser gentil e sugerir reformular a pergunta

IMPORTANTE: Retorne APENAS o JSON, sem texto adicional.
"""

SCRIPT_INSTRUCTION = """
Você é Sasha, uma tutora de IA que cria aulas em vídeo personalizadas.

## Sua Personalidade
- Acolhedora e amigável
- Usa linguagem simples do dia a dia
- Dá exemplos práticos e relacionáveis
- Faz paralelos com situações cotidianas
- Referencia momentos específicos do vídeo original

## Estilo de Ensino
- Comece cumprimentando o aluno pelo nome
- Reconheça a dúvida específica dele
- Explique usando analogias do cotidiano
- Use exemplos práticos e concretos
- Faça referências ao vídeo original com timestamps
- Conclua com resumo e encorajamento

## Formato do Script
O script será narrado por um avatar de IA. Escreva de forma natural e conversacional.

### Estrutura:
1. **Abertura** (30 segundos)
   - Cumprimento personalizado
   - Reconhecimento da dúvida

2. **Desenvolvimento** (2-3 minutos)
   - Explicação do conceito
   - 2-3 exemplos práticos
   - Referências ao vídeo original

3. **Fechamento** (30 segundos)
   - Resumo dos pontos principais
   - Encorajamento para continuar

## Referências de Timestamp
Quando mencionar algo do vídeo original, use o formato:
"Como vimos no minuto X:XX do vídeo..."
"Lembra quando falamos sobre isso no minuto X:XX?"

## Duração
- Mínimo: 300 palavras (2 minutos)
- Máximo: 750 palavras (5 minutos)
- Ideal: 450-600 palavras (3-4 minutos)

## Formato de Resposta (JSON)
{
    "script": "O script completo para o avatar narrar...",
    "timestamps": [
        {"time": 125, "topic": "Conceito X"},
        {"time": 340, "topic": "Exemplo Y"}
    ],
    "estimated_duration": 180
}

timestamps: Lista de momentos do vídeo ORIGINAL que você referenciou
estimated_duration: Duração estimada em segundos

IMPORTANTE: Retorne APENAS o JSON, sem texto adicional.
"""


class ExtraClassAgent:
    """
    Extra Class Agent - Generates personalized video lessons.

    Validates student doubts against lesson content and generates
    educational video scripts for HeyGen avatar rendering.

    Uses Gemini 3.0 Pro for validation and script generation.
    """

    def __init__(self):
        """Initialize with Gemini 3.0 Pro native."""
        # Validation agent
        self.validation_agent = Agent(
            model=MODEL_GEMINI,
            name="extraclass_validation",
            description="Validates if student doubt relates to lesson content.",
            instruction=VALIDATION_INSTRUCTION,
        )

        # Script generation agent
        self.script_agent = Agent(
            model=MODEL_GEMINI,
            name="extraclass_script",
            description="Generates personalized video lesson scripts.",
            instruction=SCRIPT_INSTRUCTION,
        )

        self.session_service = InMemorySessionService()
        print(f"ExtraClassAgent initialized with model: {MODEL_GEMINI}")

    async def _setup_session_and_runner(self, agent: Agent, user_id: str, session_id: str):
        """Set up session and runner for agent execution."""
        session = await self.session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        runner = Runner(
            agent=agent,
            app_name=APP_NAME,
            session_service=self.session_service,
        )
        return session, runner

    async def _invoke_agent(
        self, agent: Agent, prompt: str, user_id: str, session_id: str
    ) -> str:
        """
        Invoke an agent with a prompt and return the response.

        Args:
            agent: The agent to invoke
            prompt: User prompt
            user_id: Unique user identifier
            session_id: Unique session identifier

        Returns:
            Agent response as string
        """
        content = types.Content(
            role="user",
            parts=[types.Part(text=prompt)],
        )

        session, runner = await self._setup_session_and_runner(agent, user_id, session_id)

        events = runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        )

        async for event in events:
            if event.is_final_response():
                if event.content and event.content.parts:
                    return event.content.parts[0].text

        return ""

    async def validate_doubt(
        self,
        transcription: str,
        doubt: str,
    ) -> Dict[str, Any]:
        """
        Validate if student doubt relates to lesson content.

        Args:
            transcription: Episode transcription text
            doubt: Student's doubt/question

        Returns:
            Dict with:
            - is_valid: bool
            - message: str (feedback for student)
            - topics: List[str] (related topics if valid)
        """
        if not doubt or len(doubt.strip()) < 10:
            return {
                "is_valid": False,
                "message": "Por favor, descreva sua dúvida com mais detalhes (mínimo 10 caracteres).",
                "topics": [],
            }

        if not transcription:
            return {
                "is_valid": False,
                "message": "Não foi possível validar sua dúvida. Transcrição não disponível.",
                "topics": [],
            }

        prompt = f"""
Analise se a dúvida do aluno está relacionada ao conteúdo da aula.

## Transcrição da Aula (primeiros 3000 caracteres):
{transcription[:3000]}

## Dúvida do Aluno:
{doubt}

Avalie e retorne o JSON com is_valid, message e topics.
"""

        response = await self._invoke_agent(
            self.validation_agent,
            prompt,
            "system",
            "validation",
        )

        result = parse_json_safe(response)

        # Ensure required fields
        if "is_valid" not in result:
            result["is_valid"] = False
        if "message" not in result:
            result["message"] = "Não foi possível validar sua dúvida. Tente novamente."
        if "topics" not in result:
            result["topics"] = []

        return result

    async def generate_script(
        self,
        transcription: str,
        doubt: str,
        topics: List[str],
        student_name: str = "Aluno",
    ) -> Dict[str, Any]:
        """
        Generate video script for student's doubt.

        Args:
            transcription: Episode transcription text
            doubt: Student's doubt/question
            topics: Related topics from validation
            student_name: Student's name for personalization

        Returns:
            Dict with:
            - script: str (video script)
            - timestamps: List[Dict] (references to original video)
            - estimated_duration: int (seconds)
        """
        topics_text = ", ".join(topics) if topics else "o conteúdo da aula"

        prompt = f"""
Crie um roteiro de vídeo personalizado para ajudar o aluno a entender melhor.

## Informações
- **Nome do Aluno:** {student_name}
- **Dúvida:** {doubt}
- **Tópicos Relacionados:** {topics_text}

## Transcrição da Aula (com timestamps):
{transcription[:4000]}

## Instruções
1. Cumprimente {student_name} de forma acolhedora
2. Reconheça a dúvida específica sobre: {doubt[:100]}
3. Explique os conceitos usando linguagem simples
4. Use exemplos do dia a dia
5. Faça referências ao vídeo original com timestamps reais
6. Encerre com resumo e encorajamento

Retorne o JSON com script, timestamps e estimated_duration.
"""

        response = await self._invoke_agent(
            self.script_agent,
            prompt,
            "system",
            "script-gen",
        )

        result = parse_json_safe(response)

        # Ensure required fields and validate script
        if "script" not in result or not result["script"]:
            result["script"] = self._generate_fallback_script(doubt, student_name)

        if "timestamps" not in result:
            result["timestamps"] = []

        if "estimated_duration" not in result:
            result["estimated_duration"] = int(estimate_video_duration(result["script"]))

        return result

    async def generate_video(
        self,
        transcription: str,
        doubt: str,
        episode_id: str,
        student_name: str = "Aluno",
    ) -> Dict[str, Any]:
        """
        Full flow: Validate doubt, generate script, create video.

        This is the main entry point for the Extra Class feature.

        Args:
            transcription: Episode transcription text
            doubt: Student's doubt/question
            episode_id: Episode identifier
            student_name: Student's name

        Returns:
            Dict with:
            - phase: str (current phase)
            - is_valid: bool
            - message: str (if invalid)
            - video_id: str (if valid)
            - script: str (generated script)
            - timestamps: List[Dict]
            - estimated_duration: int
        """
        # Phase 1: Validate doubt
        validation = await self.validate_doubt(transcription, doubt)

        if not validation.get("is_valid", False):
            return {
                "phase": "validation",
                "is_valid": False,
                "message": validation.get("message", "Dúvida não relacionada ao conteúdo."),
                "topics": [],
            }

        # Phase 2: Generate script
        topics = validation.get("topics", [])
        script_result = await self.generate_script(
            transcription=transcription,
            doubt=doubt,
            topics=topics,
            student_name=student_name,
        )

        script = script_result.get("script", "")

        # Validate script length
        # min_length=1500 chars ≈ 250-300 words ≈ 2 minutes of video
        # This aligns with prompt instruction "Mínimo: 300 palavras (2 minutos)"
        try:
            validated_script = validate_script(script, min_length=1500, max_length=5000)
        except ValueError as e:
            return {
                "phase": "script",
                "is_valid": True,
                "error": str(e),
                "topics": topics,
            }

        # Phase 3: Create video with HeyGen
        try:
            video_title = f"Aula Extra - {doubt[:50]}..."
            video_id = create_video(
                script=validated_script,
                title=video_title,
            )

            return {
                "phase": "video_created",
                "is_valid": True,
                "video_id": video_id,
                "script": validated_script,
                "timestamps": script_result.get("timestamps", []),
                "estimated_duration": script_result.get("estimated_duration", 180),
                "topics": topics,
            }

        except ValueError as e:
            return {
                "phase": "video_error",
                "is_valid": True,
                "error": str(e),
                "script": validated_script,
                "timestamps": script_result.get("timestamps", []),
                "topics": topics,
            }

    async def check_video_status(self, video_id: str) -> Dict[str, Any]:
        """
        Check the status of a video being generated.

        Args:
            video_id: HeyGen video ID

        Returns:
            Dict with status information from HeyGen API
        """
        try:
            return get_video_status(video_id)
        except ValueError as e:
            return {
                "status": "error",
                "error": str(e),
                "video_id": video_id,
            }

    async def wait_for_video(
        self,
        video_id: str,
        timeout_seconds: int = 600,
    ) -> Dict[str, Any]:
        """
        Wait for video completion with robust polling.

        This method provides a complete flow for waiting on HeyGen video
        generation with:
        - Configurable timeout (default: 10 minutes)
        - Progressive polling intervals (10s -> 30s max)
        - Automatic retry on transient failures
        - Detailed status tracking

        Args:
            video_id: HeyGen video ID from create_video or generate_video
            timeout_seconds: Maximum time to wait (default: 600s / 10 min)

        Returns:
            Dict with:
            - status: "completed" | "failed" | "timeout" | "error"
            - video_url: URL when completed
            - thumbnail_url: Thumbnail URL when completed
            - duration: Video duration when completed
            - error: Error message if any
            - elapsed_seconds: Total time waited
            - poll_count: Number of status checks made
        """
        try:
            return await poll_until_complete_async(
                video_id=video_id,
                timeout_seconds=timeout_seconds,
                poll_interval_seconds=10,
            )
        except Exception as e:
            return {
                "status": "error",
                "video_id": video_id,
                "error": str(e),
            }

    def _generate_fallback_script(self, doubt: str, student_name: str) -> str:
        """
        Generate a fallback script if AI generation fails.

        Args:
            doubt: Student's doubt
            student_name: Student's name

        Returns:
            Basic script text
        """
        return f"""
Olá, {student_name}! Aqui é a Sasha, sua tutora de IA.

Recebi sua dúvida sobre: {doubt[:200]}

Vou te ajudar a entender melhor esse conceito.

Primeiro, vamos pensar em uma situação do dia a dia que pode nos ajudar a entender. Imagine que você está organizando sua casa. Cada conceito que aprendemos é como uma gaveta - precisamos saber onde colocar cada coisa para encontrar facilmente depois.

Da mesma forma, o que você está perguntando se relaciona com como organizamos e entendemos as informações que recebemos.

O importante é que você está fazendo perguntas - isso mostra que você está engajado e querendo aprender de verdade!

Continue assim, e qualquer outra dúvida, estou aqui para ajudar.

Até a próxima!
"""
