# =============================================================================
# NEXO AI Tutor Agent - Gemini 3.0 Pro Native
# =============================================================================
# RAG-based tutoring agent that answers student questions
# based on episode transcription content.
#
# Framework: Google ADK with native Gemini 3.0 Pro (no LiteLLM wrapper)
# Memory: AgentCore Memory for conversation persistence (optional)
#
# Note: NEXO is the AI assistant for Faiston Academy (renamed from Sasha).
# All agents use Gemini 3.0 Pro exclusively.
# =============================================================================

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from .utils import APP_NAME, MODEL_GEMINI

# =============================================================================
# System Instruction
# =============================================================================

NEXO_INSTRUCTION = """
Voce e NEXO, um tutor de IA especialista em educacao corporativa e desenvolvimento profissional.

## Personalidade
- Acolhedor e amigavel
- Didatico e paciente
- Usa linguagem acessivel e clara
- Encoraja o aprendizado
- Objetivo e pratico

## Regras OBRIGATORIAS
1. Responda APENAS com base na transcricao fornecida
2. NUNCA revele que suas respostas vem da transcricao
3. Se a pergunta nao puder ser respondida com a transcricao, diga que precisa de mais contexto
4. Use exemplos praticos quando possivel
5. Mantenha respostas concisas mas completas

## Formato de Resposta
- Use markdown para formatacao
- Use listas quando apropriado
- Destaque termos importantes em **negrito**
- Mantenha paragrafos curtos

## Tom
- Profissional mas acessivel
- Encorajador e positivo
- Nunca condescendente
"""


class NexoAgent:
    """
    NEXO AI Tutor - RAG-based tutoring for Faiston Academy.

    Answers student questions based on episode transcription content
    with a friendly, educational tone.

    Uses Gemini 3.0 Pro for high quality responses.
    """

    def __init__(self):
        """Initialize NEXO with Gemini 3.0 Pro native."""
        self.agent = Agent(
            model=MODEL_GEMINI,
            name="nexo_agent",
            description="AI tutoring agent that answers questions based on lesson content.",
            instruction=NEXO_INSTRUCTION,
        )
        self.session_service = InMemorySessionService()
        print(f"NexoAgent initialized with model: {MODEL_GEMINI}")

    async def _setup_session_and_runner(self, user_id: str, session_id: str):
        """Set up session and runner for agent execution."""
        session = await self.session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )
        runner = Runner(
            agent=self.agent,
            app_name=APP_NAME,
            session_service=self.session_service,
        )
        return session, runner

    async def invoke(self, prompt: str, user_id: str, session_id: str) -> str:
        """
        Invoke the agent with a prompt and return the response.

        Args:
            prompt: User prompt/question
            user_id: Unique user identifier
            session_id: Unique session identifier

        Returns:
            Agent response as string
        """
        content = types.Content(
            role="user",
            parts=[types.Part(text=prompt)],
        )

        session, runner = await self._setup_session_and_runner(user_id, session_id)

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

    def save_to_memory(
        self,
        session_id: str,
        actor_id: str,
        content: dict,
    ) -> None:
        """
        Save an interaction to AgentCore Memory (STM).

        Note: This is a placeholder for AgentCore Memory integration.
        In the native Gemini implementation, we rely on InMemorySessionService
        for conversation context within a session.

        Args:
            session_id: Unique session identifier
            actor_id: Actor/user identifier
            content: Content to save (dict with role and content)
        """
        # AgentCore Memory integration is optional
        # The InMemorySessionService already maintains conversation context
        # This method is kept for API compatibility with main.py
        pass
