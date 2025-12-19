# =============================================================================
# Reflection Analyzer Agent - Gemini 3.0 Pro Native
# =============================================================================
# Analyzes student reflections and provides feedback
# with video timestamps for targeted review.
#
# Framework: Google ADK with native Gemini 3.0 Pro (no LiteLLM wrapper)
# Output: JSON with scores and feedback
#
# Migration Note: Migrated from Claude Sonnet 4.5 (LiteLLM) to Gemini native.
# All agents use Gemini 3.0 Pro exclusively.
# =============================================================================

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from .utils import APP_NAME, MODEL_GEMINI, parse_json_safe
import re
from typing import Dict, Any, List

# =============================================================================
# System Instruction
# =============================================================================

REFLECTION_INSTRUCTION = """
Voce e um especialista em avaliacao de aprendizagem e feedback educacional.

## Sua Tarefa
Analisar a reflexao do aluno sobre a aula e fornecer feedback construtivo.

## Criterios de Avaliacao (0-100)
1. **Coerencia**: A reflexao faz sentido e tem logica interna
2. **Completude**: Cobre os pontos principais da aula
3. **Precisao**: As informacoes estao corretas

## Estrutura do Feedback
1. **Pontos Fortes**: O que o aluno fez bem
2. **Pontos de Atencao**: Areas para melhorar
3. **Proximos Passos**: Sugestoes com timestamps para revisao

## Formato de Saida (JSON)
{
  "scores": {
    "coerencia": 85,
    "completude": 70,
    "precisao": 90
  },
  "pontos_fortes": [
    "Demonstrou compreensao clara do conceito X",
    "Fez conexoes relevantes com Y"
  ],
  "pontos_atencao": [
    "Pode aprofundar o entendimento de Z"
  ],
  "proximos_passos": [
    {
      "text": "Revisar a explicacao sobre conceito X",
      "timestamp": 120
    }
  ]
}

## Regras
1. Seja encorajador mas honesto
2. Timestamps devem existir na transcricao (em segundos)
3. Conversao: HH:MM:SS = H*3600 + M*60 + S
4. Minimo 2 pontos fortes
5. Maximo 3 pontos de atencao
6. 2-4 proximos passos com timestamps
"""


class ReflectionAgent:
    """
    Reflection Analyzer - Evaluates student learning reflections.

    Provides feedback with scores, strengths, areas for improvement,
    and video timestamps for targeted review.

    Uses Gemini 3.0 Pro for high quality analysis.
    """

    def __init__(self):
        """Initialize with Gemini 3.0 Pro native."""
        self.agent = Agent(
            model=MODEL_GEMINI,
            name="reflection_agent",
            description="Agent that analyzes student reflections and provides constructive feedback.",
            instruction=REFLECTION_INSTRUCTION,
        )
        self.session_service = InMemorySessionService()
        print(f"ReflectionAgent initialized with model: {MODEL_GEMINI}")

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

    async def analyze(
        self,
        transcription: str,
        reflection: str,
    ) -> Dict[str, Any]:
        """
        Analyze student reflection against transcription.

        Args:
            transcription: Episode transcription text
            reflection: Student's reflection text

        Returns:
            Dict with scores, strengths, attention points, and next steps
        """
        # Extract valid timestamps
        valid_timestamps = self._extract_valid_timestamps(transcription)

        # Build prompt
        prompt = f"""
Analise a reflexao do aluno sobre esta aula.

Timestamps VALIDOS disponoveis (em segundos):
{valid_timestamps}

Use APENAS timestamps desta lista para proximos_passos.

Transcricao da aula:
{transcription}

Reflexao do aluno:
{reflection}

Retorne APENAS o JSON valido, sem texto adicional.
"""

        # Invoke agent
        response = await self.invoke(prompt, "system", "reflection-analysis")

        # Parse JSON response
        result = parse_json_safe(response)

        # Validate and ensure structure
        result = self._validate_structure(result, valid_timestamps)

        return result

    def _extract_valid_timestamps(self, transcription: str) -> List[int]:
        """Extract valid timestamps from transcription."""
        timestamps = set()

        # Pattern for HH:MM:SS.mmm or HH:MM:SS
        pattern = r"(\d{2}):(\d{2}):(\d{2})(?:\.(\d{3}))?"
        for match in re.finditer(pattern, transcription):
            h, m, s = match.groups()[:3]
            total_seconds = int(h) * 3600 + int(m) * 60 + int(s)
            timestamps.add(total_seconds)

        return sorted(timestamps)

    def _validate_structure(
        self,
        result: Dict[str, Any],
        valid_timestamps: List[int],
    ) -> Dict[str, Any]:
        """Validate and fix response structure."""
        # Ensure scores exist
        if "scores" not in result:
            result["scores"] = {
                "coerencia": 70,
                "completude": 70,
                "precisao": 70,
            }

        # Ensure scores are in range
        for key in ["coerencia", "completude", "precisao"]:
            if key in result["scores"]:
                result["scores"][key] = max(0, min(100, result["scores"][key]))

        # Ensure arrays exist
        if "pontos_fortes" not in result:
            result["pontos_fortes"] = ["Reflexao recebida"]
        if "pontos_atencao" not in result:
            result["pontos_atencao"] = []
        if "proximos_passos" not in result:
            result["proximos_passos"] = []

        # Validate timestamps in proximos_passos
        for step in result.get("proximos_passos", []):
            if isinstance(step, dict) and "timestamp" in step:
                timestamp = step["timestamp"]
                if timestamp is not None and valid_timestamps:
                    # Snap to nearest valid timestamp
                    nearest = min(
                        valid_timestamps,
                        key=lambda t: abs(t - timestamp),
                    )
                    step["timestamp"] = nearest

        return result
