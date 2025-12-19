# =============================================================================
# Flashcards Generator Agent - Gemini 3.0 Pro Native
# =============================================================================
# Generates educational flashcards from transcription content
# following Anki/SuperMemo best practices for spaced repetition.
#
# Framework: Google ADK with native Gemini 3.0 Pro (no LiteLLM wrapper)
# Output: JSON with question, answer, and tags
#
# Migration Note: Migrated from Claude Sonnet 4.5 (LiteLLM) to Gemini native.
# Gemini 3.0 Pro chosen for quality content generation.
# =============================================================================

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from .utils import APP_NAME, MODEL_GEMINI, parse_json_safe
from typing import Dict, Any

# =============================================================================
# System Instruction
# =============================================================================

FLASHCARDS_INSTRUCTION = """
Voce e um especialista em criacao de flashcards educacionais.

## Principios de Design (Anki/SuperMemo)
1. **Atomicidade**: Cada card testa UM conceito
2. **Clareza**: Perguntas sem ambiguidade
3. **Concisao**: Respostas diretas e memoraveis
4. **Contexto**: Fornecer contexto suficiente na pergunta

## Niveis de Dificuldade
- **Facil**: Fatos basicos, definicoes simples
- **Medio**: Aplicacao de conceitos, relacoes entre ideias
- **Dificil**: Analise critica, casos complexos

## Formato de Saida (JSON)
{
  "flashcards": [
    {
      "question": "Pergunta clara e especifica",
      "answer": "Resposta concisa e memoravel",
      "tags": ["tema1", "tema2"]
    }
  ]
}

## Regras
1. Extraia conceitos-chave da transcricao
2. Evite perguntas muito genericas
3. Inclua tags relevantes para organizacao
4. Varie os tipos de perguntas (o que, como, por que, quando)
5. Respostas devem ser factuais e verificaveis
"""


class FlashcardsAgent:
    """
    Flashcards Generator - Creates study cards from transcription.

    Follows spaced repetition best practices (Anki/SuperMemo)
    for effective learning.

    Uses Gemini 3.0 Pro for high quality content generation.
    """

    def __init__(self):
        """Initialize with Gemini 3.0 Pro native."""
        self.agent = Agent(
            model=MODEL_GEMINI,
            name="flashcards_agent",
            description="Agent that generates educational flashcards from lesson content.",
            instruction=FLASHCARDS_INSTRUCTION,
        )
        self.session_service = InMemorySessionService()
        print(f"FlashcardsAgent initialized with model: {MODEL_GEMINI}")

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

    async def generate(
        self,
        transcription: str,
        difficulty: str = "medium",
        count: int = 10,
        custom_prompt: str = "",
    ) -> Dict[str, Any]:
        """
        Generate flashcards from transcription.

        Args:
            transcription: Episode transcription text
            difficulty: easy, medium, or hard
            count: Number of flashcards to generate
            custom_prompt: Optional focus instructions

        Returns:
            Dict with flashcards array
        """
        # Build prompt
        prompt = f"""
Gere exatamente {count} flashcards no nivel de dificuldade "{difficulty}".

{f"Foco especial: {custom_prompt}" if custom_prompt else ""}

Transcricao da aula:
{transcription}

IMPORTANTE: Retorne APENAS o JSON valido, sem texto adicional.
Formato esperado:
{{
  "flashcards": [
    {{"question": "...", "answer": "...", "tags": ["..."]}}
  ]
}}
"""

        # Invoke agent
        response = await self.invoke(prompt, "system", "flashcards-gen")

        # Parse JSON response
        result = parse_json_safe(response)

        # Validate structure
        if "flashcards" not in result:
            result = {"flashcards": [], "error": "Invalid response structure"}

        # Normalize field names (backend uses question/answer, frontend expects front/back)
        for card in result.get("flashcards", []):
            if "question" in card and "front" not in card:
                card["front"] = card["question"]
            if "answer" in card and "back" not in card:
                card["back"] = card["answer"]
            if "tags" not in card:
                card["tags"] = []

        return result
