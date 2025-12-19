# =============================================================================
# Mind Map Generator Agent - Gemini 3.0 Pro Native
# =============================================================================
# Generates hierarchical mind maps from transcription content
# with video timestamps for navigation.
#
# Framework: Google ADK with native Gemini 3.0 Pro (no LiteLLM wrapper)
# Output: JSON tree with id, label, children, timestamp
#
# Migration Note: Claude Sonnet 4.5 was collapsing structures into 1 node.
# Gemini 3.0 Pro correctly generates 4-6 main topic nodes.
# =============================================================================

# Note: GOOGLE_API_KEY is passed via --env at deploy time (not runtime SSM lookup)
from .utils import APP_NAME, MODEL_GEMINI

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import asyncio
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Set, Optional

# =============================================================================
# System Instruction (Working Prompt from Legacy Agent)
# =============================================================================

MINDMAP_PROMPT_TEMPLATE = """Você é um especialista em criar mapas mentais educacionais ABRANGENTES e DETALHADOS.

## OBJETIVO PRINCIPAL
Criar um mapa mental COMPLETO que cubra TODO o conteúdo do vídeo DO INÍCIO AO FIM, permitindo ao usuário navegar pela aula inteira através do mapa.

## ⚠️ DURAÇÃO DO VÍDEO: {video_duration_seconds} SEGUNDOS ({video_duration_formatted})

## 📍 TIMESTAMPS DISPONÍVEIS NA TRANSCRIÇÃO:
{available_timestamps_list}

**REGRA CRÍTICA DE TIMESTAMPS**:
- Você DEVE escolher timestamps APENAS da lista acima
- NUNCA invente timestamps - use SOMENTE os valores listados
- Cada nó folha deve ter um timestamp DIFERENTE (não repita o mesmo timestamp)
- Distribua os timestamps uniformemente cobrindo TODO o vídeo: início, meio e fim
- O ÚLTIMO nó folha deve ter um timestamp próximo ao FINAL do vídeo

## ⚠️ ESTRUTURA - SEM LIMITES ARTIFICIAIS:
NÃO HÁ LIMITE MÁXIMO de nós. Crie QUANTOS nós forem necessários para cobrir TODO o conteúdo.

**Diretrizes mínimas (você pode criar MAIS):**
- Vídeos curtos (< 5 min): mínimo 4 conceitos principais
- Vídeos médios (5-10 min): mínimo 6 conceitos principais
- Vídeos longos (10-20 min): mínimo 8 conceitos principais
- Vídeos muito longos (20+ min): mínimo 12 conceitos principais

**IMPORTANTE**: Cada conceito principal deve ter 3-6 subconceitos com timestamps.

## REGRAS CRÍTICAS:

### 1. COBERTURA COMPLETA DO VÍDEO INTEIRO
- Cubra 100% do vídeo: desde 0:00 até o final ({video_duration_formatted})
- O primeiro nó deve ter timestamp no início (primeiros 30 segundos)
- O último nó deve ter timestamp no final (últimos 60 segundos)
- Extraia TODOS os conceitos importantes, não apenas alguns

### 2. ESTRUTURA HIERÁRQUICA CLARA
- **Conceitos principais**: Temas/seções amplas (ex: "Introdução", "Conceito X", "Conclusão")
- **Subconceitos**: Detalhes específicos dentro de cada tema
- **Folhas**: Pontos específicos COM timestamp para navegação direta

### 3. TIMESTAMPS - REGRA DE OURO
- CADA nó folha DEVE ter um timestamp da lista de disponíveis acima
- Timestamps são em SEGUNDOS TOTAIS (ex: 125 = 2min 5seg, 800 = 13min 20seg)
- PROIBIDO: timestamps duplicados, timestamps inventados
- Escolha o timestamp que melhor representa onde o conceito é explicado
- VERIFIQUE: seu último timestamp deve estar próximo de {video_duration_seconds}s

### 4. LABELS DESCRITIVOS
- **label**: Máximo 60 caracteres, título claro e informativo
- **description**: Opcional, 1-2 frases para conceitos complexos

### 5. IDs ÚNICOS
- Padrão hierárquico: "1", "1-1", "1-1-1", "1-1-2", etc.

### 6. EXEMPLO PARA VÍDEO DE 13 MINUTOS:
{{
  "title": "Título Principal da Aula",
  "nodes": [
    {{
      "id": "1",
      "label": "Introdução",
      "children": [
        {{"id": "1-1", "label": "Boas-vindas", "timestamp": 5}},
        {{"id": "1-2", "label": "Tema do episódio", "timestamp": 30}},
        {{"id": "1-3", "label": "Objetivos da aula", "timestamp": 55}}
      ]
    }},
    {{
      "id": "2",
      "label": "Conceito Principal A",
      "children": [
        {{"id": "2-1", "label": "Definição", "timestamp": 90}},
        {{"id": "2-2", "label": "Exemplo 1", "timestamp": 150}},
        {{"id": "2-3", "label": "Exemplo 2", "timestamp": 200}}
      ]
    }},
    {{
      "id": "3",
      "label": "Conceito Principal B",
      "children": [
        {{"id": "3-1", "label": "Teoria", "timestamp": 280}},
        {{"id": "3-2", "label": "Aplicação prática", "timestamp": 350}}
      ]
    }},
    {{
      "id": "4",
      "label": "Desenvolvimento",
      "children": [
        {{"id": "4-1", "label": "Casos de uso", "timestamp": 420}},
        {{"id": "4-2", "label": "Benefícios", "timestamp": 500}},
        {{"id": "4-3", "label": "Desafios", "timestamp": 560}}
      ]
    }},
    {{
      "id": "5",
      "label": "Conceito Principal C",
      "children": [
        {{"id": "5-1", "label": "Estratégias", "timestamp": 620}},
        {{"id": "5-2", "label": "Implementação", "timestamp": 680}}
      ]
    }},
    {{
      "id": "6",
      "label": "Conclusão",
      "children": [
        {{"id": "6-1", "label": "Resumo dos pontos", "timestamp": 720}},
        {{"id": "6-2", "label": "Próximos passos", "timestamp": 760}},
        {{"id": "6-3", "label": "Encerramento", "timestamp": 790}}
      ]
    }}
  ]
}}

Retorne APENAS um JSON válido com a estrutura acima. Certifique-se de cobrir TODO o vídeo até o final."""


class MindMapAgent:
    """
    Mind Map Generator using Gemini 3.0 Pro directly (no LiteLLM).

    Uses native Google ADK Agent with Gemini 3.0 Pro model.
    This model correctly generates 4-6 main topic nodes (Claude was collapsing).
    """

    def __init__(self):
        """Initialize with Gemini 3.0 Pro native."""
        self.agent = Agent(
            model=MODEL_GEMINI,
            name="mindmap_agent",
            description="Agent to generate hierarchical mind maps from video transcriptions.",
            instruction="I create detailed, navigable mind maps from video lesson transcriptions.",
        )
        self.session_service = InMemorySessionService()
        print(f"MindMapAgent initialized with model: {MODEL_GEMINI}")

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

    async def generate(self, transcription: str, episode_title: str = "Aula") -> Dict[str, Any]:
        """
        Generate mind map from transcription.

        Args:
            transcription: Episode transcription text
            episode_title: Title for the root node

        Returns:
            Dict with title, nodes array, generatedAt, and model
        """
        # Step 1: Extract ALL valid timestamps from transcription
        valid_timestamps = self._extract_valid_timestamps(transcription)
        duration_seconds = max(valid_timestamps) + 10 if valid_timestamps else 600
        duration_formatted = self._format_duration(duration_seconds)

        # Format available timestamps for prompt (show as "Xs (M:SS)")
        # No artificial limit - pass all timestamps to ensure full video coverage
        timestamps_formatted = []
        for ts in valid_timestamps:
            formatted = self._format_duration(ts)
            timestamps_formatted.append(f"{ts}s ({formatted})")
        available_timestamps_str = ", ".join(timestamps_formatted)

        # Step 2: Build prompt with available timestamps
        system_prompt = MINDMAP_PROMPT_TEMPLATE.format(
            video_duration_seconds=duration_seconds,
            video_duration_formatted=duration_formatted,
            available_timestamps_list=available_timestamps_str
        )

        user_prompt = f"""Transcrição da aula "{episode_title}":

{transcription}

---

Gere um mapa mental baseado nesta transcrição.
- Use SOMENTE timestamps da lista de disponíveis: {available_timestamps_str}
- Distribua os conceitos do início ao fim do vídeo
- Não repita o mesmo timestamp em nós diferentes"""

        # Step 3: Invoke Gemini
        full_prompt = f"{system_prompt}\n\n{user_prompt}"
        response = await self.invoke(full_prompt, "system", "mindmap-gen")

        # Parse JSON response
        result = self._parse_json_safe(response)

        # Validate structure
        if "nodes" not in result:
            if isinstance(result, list):
                result = {"nodes": result}
            else:
                result = {"nodes": [], "error": "Invalid response structure"}

        # Step 4: Post-process - snap timestamps to valid ones
        self._snap_to_valid_timestamps(result.get("nodes", []), valid_timestamps)

        # Validate and log metrics
        nodes = result.get("nodes", [])
        total_nodes = self._count_nodes(nodes)
        # Minimum 4 main topics and 20 total nodes for good coverage
        is_valid = len(nodes) >= 4 and total_nodes >= 20

        print(f"MindMap generated: {len(nodes)} main topics, {total_nodes} total nodes, valid={is_valid}")

        # Return with metadata
        return {
            "title": result.get("title", episode_title),
            "nodes": nodes,
            "generatedAt": datetime.utcnow().isoformat() + "Z",
            "model": MODEL_GEMINI,
            "_meta": {
                "main_topics": len(nodes),
                "total_nodes": total_nodes,
                "structure_valid": is_valid,
            }
        }

    def _extract_valid_timestamps(self, transcription: str) -> List[int]:
        """
        Extract all valid timestamps from transcription.

        Supports formats:
        - HH:MM:SS.mmm (e.g., 00:05:15.000)
        - HH:MM:SS (e.g., 00:05:15)
        - MM:SS (e.g., 05:15)

        Returns:
            Sorted list of timestamps in seconds
        """
        timestamps_set: Set[int] = set()

        # Try HH:MM:SS.mmm format first (most precise)
        timestamps_full = re.findall(r'(\d{2}):(\d{2}):(\d{2})\.?\d*', transcription)
        for h, m, s in timestamps_full:
            total = int(h) * 3600 + int(m) * 60 + int(s)
            timestamps_set.add(total)

        # Also try MM:SS format (common in shorter videos)
        if not timestamps_set:
            timestamps_short = re.findall(r'(\d{2}):(\d{2})', transcription)
            for m, s in timestamps_short:
                # Skip if this looks like HH:MM (hours:minutes)
                if int(m) < 60 and int(s) < 60:
                    total = int(m) * 60 + int(s)
                    timestamps_set.add(total)

        # If no timestamps found, generate synthetic ones (every 30s for 10 min)
        if not timestamps_set:
            return list(range(0, 600, 30))

        return sorted(timestamps_set)

    def _format_duration(self, seconds: int) -> str:
        """Format duration in MM:SS format."""
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"

    def _snap_to_valid_timestamps(
        self,
        nodes: List[Dict[str, Any]],
        valid_timestamps: List[int],
        used_timestamps: Optional[Set[int]] = None,
    ) -> None:
        """
        Recursively snap node timestamps to valid values and ensure uniqueness.

        Args:
            nodes: List of nodes to process
            valid_timestamps: List of valid timestamp values
            used_timestamps: Set of already used timestamps (for uniqueness)
        """
        if used_timestamps is None:
            used_timestamps = set()

        for node in nodes:
            # Process children first (depth-first)
            children = node.get("children", [])
            if children:
                self._snap_to_valid_timestamps(children, valid_timestamps, used_timestamps)

            # Snap this node's timestamp if it has one
            timestamp = node.get("timestamp")
            if timestamp is not None and valid_timestamps:
                if isinstance(timestamp, (int, float)):
                    original = int(timestamp)
                    nearest = self._find_nearest_unused(original, valid_timestamps, used_timestamps)
                    if nearest is not None:
                        node["timestamp"] = nearest
                        used_timestamps.add(nearest)
                    else:
                        node["timestamp"] = None

    def _find_nearest_unused(
        self,
        target: int,
        valid_timestamps: List[int],
        used: Set[int],
    ) -> Optional[int]:
        """
        Find the nearest unused timestamp to the target.

        Args:
            target: Target timestamp value
            valid_timestamps: List of valid timestamps
            used: Set of already used timestamps

        Returns:
            Nearest unused timestamp or None if all used
        """
        available = [t for t in valid_timestamps if t not in used]
        if not available:
            return None

        return min(available, key=lambda t: abs(t - target))

    def _count_nodes(self, nodes: List[Dict[str, Any]]) -> int:
        """Count total nodes in the tree recursively."""
        count = len(nodes)
        for node in nodes:
            children = node.get("children", [])
            if children:
                count += self._count_nodes(children)
        return count

    def _parse_json_safe(self, response: str) -> Dict[str, Any]:
        """
        Safely parse JSON from response with fallback.

        Args:
            response: Raw response text

        Returns:
            Parsed JSON dict or error dict
        """
        try:
            json_str = self._extract_json(response)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse JSON: {e}", "raw_response": response}

    def _extract_json(self, response: str) -> str:
        """
        Extract JSON from a response that may contain markdown code blocks.

        Args:
            response: Raw response text

        Returns:
            Extracted JSON string
        """
        # Try to find JSON in markdown code block
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
        if json_match:
            return json_match.group(1).strip()

        # Try to find raw JSON object or array
        json_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", response)
        if json_match:
            return json_match.group(1).strip()

        # Return as-is if no JSON found
        return response.strip()
