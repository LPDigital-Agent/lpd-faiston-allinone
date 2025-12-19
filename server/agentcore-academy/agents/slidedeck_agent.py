# =============================================================================
# Slide Deck Generator v4 - Batch-Based Parallel Architecture
# =============================================================================
# Generates professional slide presentations with AI-rendered text and graphics.
#
# Architecture (2-Phase Generation - Design-First Pattern):
# 1. Design Architect (Gemini 3 Pro) - Creates detailed design specification
# 2. Visual Renderer (Gemini 3 Pro IMAGE) - Renders COMPLETE slide with text
#
# v4: Batch-Based Generation for AgentCore 120s Timeout:
# - PROBLEM: Full deck (8-15 slides) takes 3-5 minutes, exceeds 120s timeout
# - SOLUTION: Split generation into batches of 2 slides per invocation
# - Frontend orchestrates multiple parallel AgentCore calls
# - Each batch completes in ~50-70 seconds (safely under 120s limit)
# - Supports two modes:
#   1. "plan" - Extract concepts and return slide plan (fast, ~10s)
#   2. "generate_batch" - Generate specific slides by indices (2 slides, ~60s)
#
# NO PILLOW COMPOSITION - text is native to the generated image!
#
# Framework: Google ADK with Gemini (Text + Image)
# Storage: S3 bucket (hive-academy-slides-{env})
# =============================================================================

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google import genai
from io import BytesIO
import boto3
import json
import re
import os
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, List, Tuple
from .utils import APP_NAME, MODEL_GEMINI

# =============================================================================
# Constants
# =============================================================================

# =============================================================================
# v5: ARCHETYPE PROMPTS - 5 Pedagogical Styles
# =============================================================================
# Each archetype has a unique teaching strategy and visual structure.
# These prompts guide Gemini to generate slides with different approaches.
# =============================================================================

ARCHETYPE_PROMPTS = {
    "deep_dive": """
ESTILO: Conceito Essencial (Deep Dive)
OBJETIVO: Explicar UM conceito complexo em profundidade

INSTRUÇÕES:
- Identifique o conceito CENTRAL da transcrição
- Crie uma ANALOGIA do mundo real para explicá-lo
- Use frases de IMPACTO, não listas longas
- Foque em DEFINIÇÕES claras
- Máximo 5-6 slides focados no mesmo tema
- Cada slide deve aprofundar um aspecto do conceito
- Use visuais que ilustrem a analogia escolhida
""",

    "how_to": """
ESTILO: Passo a Passo (How-To / Tutorial)
OBJETIVO: Ensinar um processo, tutorial ou cronologia

INSTRUÇÕES:
- Quebre o conteúdo em 4-6 ETAPAS cronológicas ou lógicas
- Comece cada slide com um VERBO de ação (Instale, Configure, Execute)
- Use numeração clara (Passo 1, Passo 2...)
- Mostre a PROGRESSÃO visual entre etapas
- Inclua "Resultado Esperado" no penúltimo slide
- Use ícones de checklist, setas de progresso
- Visual: barras de progresso, numeração destacada
""",

    "versus": """
ESTILO: Batalha Comparativa (Versus Mode)
OBJETIVO: Comparar duas ideias, teorias, tecnologias ou abordagens

INSTRUÇÕES:
- Identifique as DUAS entidades principais para comparar
- Estruture como: Lado A vs Lado B
- Foque nas DIFERENÇAS e SEMELHANÇAS
- Use layout de duas colunas para contraste visual
- Cores distintas para cada lado (ex: azul vs laranja)
- Inclua slide de "Conclusão: Quando usar cada um"
- Use ícones de batalha: espadas, balanças, vs
""",

    "case_study": """
ESTILO: Estudo de Caso (Storytelling)
OBJETIVO: Analisar uma situação real para extrair lições práticas

INSTRUÇÕES:
- Encontre uma NARRATIVA dentro do conteúdo
- Estruture como Jornada: Contexto → Problema → Solução → Resultado
- Foque em CAUSA e CONSEQUÊNCIA
- Use citações ou dados reais quando disponíveis
- Visual: linha do tempo, ícones de pessoa/empresa
- Termine com "Lições Aprendidas" (3-4 pontos)
- Tom: narrativo, envolvente, como uma história
""",

    "flash_quiz": """
ESTILO: Flash Quiz (Gamification/Revisão Ativa)
OBJETIVO: Testar conhecimento do aluno com perguntas desafiadoras

INSTRUÇÕES:
- NÃO resuma o conteúdo, crie PERGUNTAS
- Crie 4-5 perguntas baseadas no conteúdo da transcrição
- Estrutura de cada slide: Pergunta grande → (pausa) → Resposta → Explicação curta
- Varie os tipos: múltipla escolha, verdadeiro/falso, complete a frase
- Use visual de quiz: interrogação grande, opções A/B/C/D
- Cores vibrantes: roxo, amarelo, verde para acerto
- Ótimo para revisão de final de aula
- Inclua slide final com "Quantas você acertou?"
""",
}

# Phase 1: Design Architect (text generation for design spec)
MODEL_DESIGN = "gemini-3-pro-preview"

# Phase 2: Visual Renderer (image generation WITH text rendering)
# Using Gemini Image models (NOT Imagen - Imagen doesn't render text well)
# Docs: https://ai.google.dev/gemini-api/docs/image-generation
#
# gemini-3-pro-image-preview = "Nano Banana Pro" - state-of-the-art, advanced text rendering, 4K
# gemini-2.5-flash-image = "Nano Banana" - fast, efficient fallback
MODEL_RENDER_PRIMARY = "gemini-3-pro-image-preview"
MODEL_RENDER_FALLBACK = "gemini-2.5-flash-image"

# Slide dimensions (16:9 widescreen)
SLIDE_WIDTH = 1920
SLIDE_HEIGHT = 1080

# S3 bucket (created via terraform/main/s3_slides.tf)
S3_BUCKET = os.environ.get("SLIDES_BUCKET", "hive-academy-slides-prod")
S3_REGION = os.environ.get("AWS_REGION", "us-east-2")


class SlideDeckAgent:
    """
    Slide Deck Generator v3 - Two-Stage Design Pipeline

    For each slide:
    1. Design Architect creates detailed layout/color/typography spec
    2. Visual Renderer creates final PNG with ALL content (including text)

    NO Pillow composition - text is native to the image!

    This approach mirrors NotebookLM's quality by having the AI model
    render typography, icons, and layout as a single coherent image.
    """

    def __init__(self):
        """Initialize agents and services."""
        self.genai_client = genai.Client()
        self.s3 = boto3.client("s3", region_name=S3_REGION)
        print(f"SlideDeckAgent v3 initialized: {MODEL_DESIGN} (design) + {MODEL_RENDER_PRIMARY} (render)")

    async def _design_slide(self, slide_content: str, style: str = "corporate") -> str:
        """
        PHASE 1: Design Architect

        Creates detailed design specification for a single slide.
        The spec includes layout, colors, icons, and exact text content.

        Args:
            slide_content: The content/concepts for this slide
            style: Design style (corporate, creative, minimalist)

        Returns:
            Design specification string for the Visual Renderer
        """
        prompt = f'''Você é um designer de apresentações profissionais.
Crie uma especificação DETALHADA de design para um slide sobre:

CONTEÚDO:
{slide_content}

ESTILO: {style}

Forneça uma especificação visual completa em INGLÊS (para o renderizador de imagem):

## Slide Design Specification

**Layout Type**: [ex: "Three-column with rounded corner panels" ou "Two-column split" ou "Full-width with icon strip"]

**Title**:
- Text: "[título exato em português]"
- Position: top center
- Style: large bold, dark text on light background OR white text on dark

**Subtitle** (if applicable):
- Text: "[subtítulo em português]"
- Position: below title
- Style: smaller, muted color

**Main Content Sections**:

For each section/column, specify:
- **Section Header**: "[texto]" with [icon description]
- **Theme Color**: [specific color with hex, e.g., "slate grey #64748B"]
- **Subheader**: "[pergunta ou categoria]"
- **Bullet Points**:
  • [ponto 1 - texto EXATO em português]
  • [ponto 2 - texto EXATO em português]
  • [ponto 3 - texto EXATO em português]

**Color Palette**:
- Background: [color with hex]
- Section backgrounds: [colors with hex]
- Headers: [color]
- Body text: [color]
- Accents: [color]

**Visual Elements**:
- Icons: [describe simple icons for each concept]
- Borders: [rounded corners? shadows?]
- Separators: [lines, spacing]

**Typography**:
- Title: Bold sans-serif, ~48pt equivalent
- Headers: Semi-bold, ~24pt
- Body: Regular, ~18pt
- Use clean, modern sans-serif throughout

IMPORTANTE:
- Inclua TODO o texto exato que deve aparecer no slide (em português)
- Descreva ícones de forma clara (ex: "anchor icon", "lightbulb icon")
- Use cores que combinem harmoniosamente
- Pense em clareza e legibilidade
'''

        response = self.genai_client.models.generate_content(
            model=MODEL_DESIGN,
            contents=prompt,
        )

        return response.text

    async def _render_slide(self, design_spec: str, attempt: int = 1) -> bytes:
        """
        PHASE 2: Visual Renderer

        Renders the complete slide as PNG using the design spec.
        Text is rendered BY the model, not overlaid later!

        Args:
            design_spec: Design specification from Phase 1
            attempt: Current attempt number for fallback logic

        Returns:
            PNG image bytes of the complete slide
        """
        render_prompt = f'''Generate a professional presentation slide image.

DESIGN INSTRUCTIONS (follow these to create the visual, do NOT display this text):
{design_spec}

IMPORTANT - READ CAREFULLY:
- The text above are DESIGN INSTRUCTIONS - do NOT render them on the slide
- ONLY render the specific slide CONTENT text (titles, bullet points, subtitles mentioned)
- Do NOT show markdown, headers like "##", asterisks, or specification text
- Create a CLEAN, professional slide with ONLY the actual content

TECHNICAL REQUIREMENTS:
- 16:9 widescreen aspect ratio
- Clean, minimal, educational aesthetic
- Professional sans-serif typography
- High contrast for readability
- NO watermarks, NO AI signatures
- NO technical specification text visible

OUTPUT: A clean presentation slide image showing ONLY the content (title, subtitle, bullets) - NOT the design instructions.
'''

        # Try primary model first, then fallback
        # Docs: https://ai.google.dev/gemini-api/docs/image-generation
        models_to_try = [MODEL_RENDER_PRIMARY, MODEL_RENDER_FALLBACK]

        for model in models_to_try:
            try:
                print(f"[Slide Render] Trying {model}...")

                # Use generate_content with response_modalities for Gemini Image models
                # This is different from generate_images (Imagen API)
                response = self.genai_client.models.generate_content(
                    model=model,
                    contents=render_prompt,
                    config=types.GenerateContentConfig(
                        response_modalities=["IMAGE"],
                    ),
                )

                # Extract image from response.parts (official pattern)
                # Docs: response.parts contains text and/or inline_data
                for part in response.parts:
                    if hasattr(part, 'inline_data') and part.inline_data is not None:
                        # Get image bytes directly
                        if hasattr(part.inline_data, 'data'):
                            print(f"[Slide Render] {model} success!")
                            return part.inline_data.data
                        # Alternative: use as_image() if available
                        elif hasattr(part, 'as_image'):
                            from io import BytesIO
                            img = part.as_image()
                            buf = BytesIO()
                            img.save(buf, format='PNG')
                            print(f"[Slide Render] {model} success (via as_image)!")
                            return buf.getvalue()

                # Fallback: try candidates structure
                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, 'inline_data') and part.inline_data:
                            if hasattr(part.inline_data, 'data'):
                                print(f"[Slide Render] {model} success (via candidates)!")
                                return part.inline_data.data

            except Exception as e:
                print(f"[Slide Render] {model} failed: {e}")
                continue

        raise ValueError(f"Failed to render slide image after trying all models")

    async def _upload_to_s3(
        self,
        image_bytes: bytes,
        episode_id: str,
        slide_number: int,
        generation_id: str = None,
    ) -> str:
        """
        Upload slide image to S3 and return public URL.

        Args:
            image_bytes: PNG image bytes
            episode_id: Episode identifier for folder organization
            slide_number: Slide number (1-based)
            generation_id: Unique generation ID to prevent overwrite (v6)

        Returns:
            Public S3 URL for the image
        """
        # v6: Include generation_id in path to prevent overwrite between generations
        if generation_id:
            key = f"{episode_id}/{generation_id}/slide-{slide_number}.png"
        else:
            key = f"{episode_id}/slide-{slide_number}.png"

        self.s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=image_bytes,
            ContentType="image/png",
        )

        # Return public URL (bucket has public read policy)
        return f"https://{S3_BUCKET}.s3.{S3_REGION}.amazonaws.com/{key}"

    def _extract_slide_contents(self, concepts_text: str) -> List[str]:
        """
        Extract individual slide contents from concepts response.

        Args:
            concepts_text: Raw text with concepts separated by headers

        Returns:
            List of slide content strings
        """
        parts = []
        current = ""

        for line in concepts_text.split('\n'):
            # Detect new concept/section markers
            line_stripped = line.strip()
            if (line_stripped.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.')) or
                line_stripped.startswith(('#', '##', '###')) or
                line_stripped.lower().startswith(('conceito', 'slide', 'tópico', 'seção'))):
                if current.strip() and len(current.strip()) > 50:
                    parts.append(current.strip())
                current = line
            else:
                current += '\n' + line

        if current.strip() and len(current.strip()) > 50:
            parts.append(current.strip())

        # Filter only (no limit here - limit is applied in generate() based on transcription length)
        return [p for p in parts if len(p) > 50]

    def _parse_json_safe(self, response: str) -> Dict[str, Any]:
        """Safely parse JSON from response."""
        try:
            json_str = self._extract_json(response)
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            return {"error": f"Failed to parse JSON: {e}", "concepts": []}

    def _extract_json(self, response: str) -> str:
        """Extract JSON from response that may contain markdown blocks."""
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response)
        if json_match:
            return json_match.group(1).strip()
        json_match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", response)
        if json_match:
            return json_match.group(1).strip()
        return response.strip()

    def _calculate_slide_count(self, transcription_length: int) -> int:
        """
        Calculate optimal number of content slides based on transcription length.

        Heuristics (v3.2 - increased minimums):
        - Very short transcription (<3000 chars): 6 slides minimum
        - Short transcription (3000-8000 chars): 8 slides
        - Medium transcription (8000-15000 chars): 10 slides
        - Long transcription (15000-30000 chars): 12 slides
        - Very long transcription (>30000 chars): 13 slides (max)

        Note: This is for CONTENT slides only. Cover + closing are added separately.
        Maximum total slides = 15 (1 cover + 13 content + 1 closing)
        Minimum total slides = 8 (1 cover + 6 content + 1 closing)

        Args:
            transcription_length: Length of transcription in characters

        Returns:
            Number of content slides to generate (6-13)
        """
        if transcription_length < 3000:
            return 6  # Very short: 6 content + cover + closing = 8 total
        elif transcription_length < 8000:
            return 8  # Short: 8 content + cover + closing = 10 total
        elif transcription_length < 15000:
            return 10  # Medium: 10 content + cover + closing = 12 total
        elif transcription_length < 30000:
            return 12  # Long: 12 content + cover + closing = 14 total
        else:
            return 13  # Very long (60+ min): 13 content + cover + closing = 15 total

    async def _generate_cover_slide(self, episode_title: str, style: str) -> str:
        """
        Generate design spec for the cover/title slide.

        The cover slide is professional, impactful, and sets the tone for the presentation.
        This is an EDUCATIONAL presentation, NOT corporate.
        """
        cover_prompt = f'''Create a cover slide design specification.

SLIDE CONTENT (the actual text to display):
- Main Title: "{episode_title}"
- Subtitle: "Trilha de Aprendizagem"

VISUAL STYLE:
- Clean educational aesthetic (NOT corporate)
- Soft purple-to-blue gradient background
- Large centered title in dark purple
- Smaller subtitle below in muted color
- Optional: small educational icon (book, compass, lightbulb)
- Warm and inviting feel

Keep the specification brief and focused on the visual layout.
'''

        response = self.genai_client.models.generate_content(
            model=MODEL_DESIGN,
            contents=cover_prompt,
        )
        return response.text

    async def _generate_closing_slide(self, episode_title: str, style: str) -> str:
        """
        Generate design spec for the closing/thank you slide.

        The closing slide provides a warm conclusion to the educational presentation.
        This is for EDUCATION, not corporate - no presenter info or contact details.
        """
        closing_prompt = f'''Create a closing slide design specification.

SLIDE CONTENT (the actual text to display):
- Main Text: "Bons Estudos!"
- Secondary Text: "{episode_title}"
- Small Text: "Continue aprendendo!"

VISUAL STYLE:
- Warm educational aesthetic
- Soft purple-to-teal gradient background
- Large centered main text in dark purple
- Smaller secondary text below
- Optional: graduation cap or book icon
- Celebratory and encouraging feel
- NO contact info, NO corporate elements

Keep the specification brief and focused on the visual layout.
'''

        response = self.genai_client.models.generate_content(
            model=MODEL_DESIGN,
            contents=closing_prompt,
        )
        return response.text

    async def generate(
        self,
        transcription: str,
        episode_title: str = "Aula",
        episode_id: str = "unknown",
        custom_prompt: str = "",
        style: str = "corporate",
    ) -> Dict[str, Any]:
        """
        Generate slide deck using Two-Stage Design Pipeline.

        Structure:
        1. Cover slide (capa/abertura)
        2. Content slides (4-13 based on transcription length)
        3. Closing slide (encerramento/agradecimento)

        Total: 6-15 slides depending on content length.

        Args:
            transcription: Episode transcription text
            episode_title: Title of the episode
            episode_id: Unique episode identifier (for S3 organization)
            custom_prompt: Optional focus instructions
            style: Design style (corporate, creative, minimalist)

        Returns:
            Dict with deck_title, slides (with image_url), generatedAt, model
        """
        print(f"[SlideDeck v3] Starting two-stage generation for episode: {episode_id}")

        # Calculate optimal number of content slides based on transcription length
        content_slide_count = self._calculate_slide_count(len(transcription))
        total_slides = content_slide_count + 2  # +2 for cover and closing
        print(f"[SlideDeck v3] Transcription length: {len(transcription)} chars → {content_slide_count} content slides + cover + closing = {total_slides} total")

        slides = []
        slide_num = 0

        # ========== SLIDE 1: COVER SLIDE ==========
        slide_num += 1
        print(f"[SlideDeck v3] Slide {slide_num}/{total_slides} (COVER)")

        try:
            print(f"  [Phase 1] Designing cover slide...")
            cover_design = await self._generate_cover_slide(episode_title, style)

            print(f"  [Phase 2] Rendering cover slide...")
            cover_bytes = await self._render_slide(cover_design)

            print(f"  [Upload] Uploading cover slide...")
            cover_url = await self._upload_to_s3(cover_bytes, episode_id, slide_num)

            slides.append({
                "id": f"slide-{slide_num}",
                "title": "Capa",
                "image_url": cover_url,
                "slide_type": "cover",
            })
            print(f"  [Done] Cover slide complete")
        except Exception as e:
            print(f"  [Error] Cover slide failed: {e}")

        # ========== PHASE 0: Extract Key Concepts ==========
        concepts_prompt = f'''Analise esta transcrição e extraia {content_slide_count} conceitos principais para criar slides de apresentação.

Título da aula: {episode_title}
{f"Foco especial: {custom_prompt}" if custom_prompt else ""}

Transcrição:
{transcription[:15000]}

Para cada conceito, forneça em formato estruturado:
1. **Título**: Título curto e impactante (max 6 palavras)
2. **Conceito Principal**: Explicação clara do conceito
3. **Pontos-Chave**: 3-4 bullet points concisos
4. **Contexto Visual**: Que tipo de visual/ícones representariam este conceito

IMPORTANTE: Extraia exatamente {content_slide_count} conceitos distintos que cubram todo o conteúdo da aula.
Separe cada conceito claramente com numeração (1., 2., 3., etc.)
'''

        print(f"[SlideDeck v3] Phase 0: Extracting {content_slide_count} key concepts...")
        concepts_response = self.genai_client.models.generate_content(
            model=MODEL_DESIGN,
            contents=concepts_prompt,
        )
        concepts_text = concepts_response.text

        # Parse concepts into individual slide contents
        slide_contents = self._extract_slide_contents(concepts_text)

        if not slide_contents:
            # Fallback: split transcription into chunks
            print("[SlideDeck v3] Warning: No concepts extracted, using fallback")
            chunk_size = len(transcription) // content_slide_count
            slide_contents = []
            for i in range(content_slide_count):
                start = i * chunk_size
                end = start + chunk_size
                slide_contents.append(f"Parte {i+1}: {transcription[start:end][:1000]}")

        # Limit to requested count
        slide_contents = slide_contents[:content_slide_count]
        print(f"[SlideDeck v3] Extracted {len(slide_contents)} concepts for content slides")

        # ========== CONTENT SLIDES ==========
        for i, content in enumerate(slide_contents):
            slide_num += 1
            content_index = i + 1
            print(f"[SlideDeck v3] Slide {slide_num}/{total_slides} (Content {content_index}/{len(slide_contents)})")

            # PHASE 1: Design Architect
            print(f"  [Phase 1] Designing content slide {content_index}...")
            try:
                design_spec = await self._design_slide(content, style)
            except Exception as e:
                print(f"  [Phase 1] Design failed: {e}")
                design_spec = f"""
## Slide Design Specification

**Layout**: Single column with clean background

**Title**: "{episode_title} - Parte {content_index}"
**Position**: top center, large bold text

**Content**:
{content[:500]}

**Color Palette**:
- Background: white #FFFFFF
- Text: dark grey #1F2937
- Accent: blue #3B82F6

**Typography**: Clean sans-serif
"""

            # PHASE 2: Visual Renderer
            print(f"  [Phase 2] Rendering content slide {content_index}...")
            try:
                image_bytes = await self._render_slide(design_spec)
            except Exception as e:
                print(f"  [Phase 2] Render failed: {e}")
                continue

            # Upload to S3
            print(f"  [Upload] Uploading content slide {content_index}...")
            try:
                image_url = await self._upload_to_s3(
                    image_bytes=image_bytes,
                    episode_id=episode_id,
                    slide_number=slide_num,
                )
            except Exception as e:
                print(f"  [Upload] S3 upload failed: {e}")
                image_url = ""

            slides.append({
                "id": f"slide-{slide_num}",
                "title": f"Slide {content_index}",
                "image_url": image_url,
                "slide_type": "content",
            })
            print(f"  [Done] Content slide {content_index} complete")

        # ========== CLOSING SLIDE ==========
        slide_num += 1
        print(f"[SlideDeck v3] Slide {slide_num}/{total_slides} (CLOSING)")

        try:
            print(f"  [Phase 1] Designing closing slide...")
            closing_design = await self._generate_closing_slide(episode_title, style)

            print(f"  [Phase 2] Rendering closing slide...")
            closing_bytes = await self._render_slide(closing_design)

            print(f"  [Upload] Uploading closing slide...")
            closing_url = await self._upload_to_s3(closing_bytes, episode_id, slide_num)

            slides.append({
                "id": f"slide-{slide_num}",
                "title": "Obrigado",
                "image_url": closing_url,
                "slide_type": "closing",
            })
            print(f"  [Done] Closing slide complete")
        except Exception as e:
            print(f"  [Error] Closing slide failed: {e}")

        print(f"[SlideDeck v3] Generation complete: {len(slides)} slides")

        return {
            "deck_title": episode_title,
            "slides": slides,
            "generatedAt": datetime.utcnow().isoformat() + "Z",
            "model": f"{MODEL_DESIGN} (design) + {MODEL_RENDER_PRIMARY} (render)",
            "version": "v3.1-with-cover-closing",
            "slide_count": {
                "total": len(slides),
                "cover": 1,
                "content": len([s for s in slides if s.get("slide_type") == "content"]),
                "closing": 1,
            }
        }

    # =========================================================================
    # v4: BATCH-BASED GENERATION METHODS
    # =========================================================================
    # These methods support the parallel orchestration pattern where:
    # 1. Frontend calls plan() to get concept list (~10s)
    # 2. Frontend makes parallel calls to generate_batch() for each batch
    # 3. Each batch generates 2-3 slides (~80s, well under 120s limit)
    # 4. Frontend aggregates all batch results into final deck
    # =========================================================================

    async def plan(
        self,
        transcription: str,
        episode_title: str = "Aula",
        archetype: str = "deep_dive",
    ) -> Dict[str, Any]:
        """
        PHASE 1: Create slide plan with concepts (fast, ~10-15 seconds).

        This extracts key concepts from the transcription and creates a plan
        for the slide deck. The frontend uses this plan to orchestrate
        parallel batch generation.

        v5: Now supports 5 pedagogical archetypes that guide the slide style.

        Args:
            transcription: Episode transcription text
            episode_title: Title of the episode
            archetype: Pedagogical style (deep_dive, how_to, versus, case_study, flash_quiz)

        Returns:
            Dict with:
            - deck_title: Episode title
            - total_slides: Total number of slides to generate
            - concepts: List of slide concepts with content
            - batches: Recommended batch assignments (indices)
            - archetype: The selected archetype style
        """
        print(f"[SlideDeck v4] Planning slide deck for: {episode_title} (archetype: {archetype})")

        # Get archetype-specific instructions (v5)
        archetype_instructions = ARCHETYPE_PROMPTS.get(archetype, ARCHETYPE_PROMPTS["deep_dive"])

        # Calculate optimal number of content slides
        content_slide_count = self._calculate_slide_count(len(transcription))
        total_slides = content_slide_count + 2  # +2 for cover and closing
        print(f"[SlideDeck v4] Plan: {content_slide_count} content slides + cover + closing = {total_slides} total")

        # Extract concepts from transcription with archetype-specific guidance
        concepts_prompt = f'''Analise esta transcrição e extraia {content_slide_count} conceitos principais para criar slides de apresentação.

{archetype_instructions}

Título da aula: {episode_title}

Transcrição:
{transcription[:15000]}

IMPORTANTE: Retorne EXATAMENTE {content_slide_count} conceitos no formato JSON, seguindo o ESTILO indicado acima:

```json
{{
  "concepts": [
    {{
      "index": 1,
      "title": "Título curto (max 6 palavras)",
      "content": "Explicação clara do conceito em 2-3 frases",
      "key_points": ["ponto 1", "ponto 2", "ponto 3"],
      "visual_hint": "Descrição de elementos visuais/ícones"
    }}
  ]
}}
```

Extraia exatamente {content_slide_count} conceitos distintos que cubram todo o conteúdo da aula.
'''

        print(f"[SlideDeck v4] Extracting {content_slide_count} concepts...")
        concepts_response = self.genai_client.models.generate_content(
            model=MODEL_DESIGN,
            contents=concepts_prompt,
        )

        # Parse concepts
        concepts_data = self._parse_json_safe(concepts_response.text)
        concepts = concepts_data.get("concepts", [])

        # Fallback if JSON parsing failed
        if not concepts or len(concepts) < content_slide_count:
            print(f"[SlideDeck v4] JSON parsing yielded {len(concepts)} concepts, using text extraction")
            slide_contents = self._extract_slide_contents(concepts_response.text)
            concepts = [
                {
                    "index": i + 1,
                    "title": f"Conceito {i + 1}",
                    "content": content,
                    "key_points": [],
                    "visual_hint": ""
                }
                for i, content in enumerate(slide_contents[:content_slide_count])
            ]

        # Ensure we have exactly the right number
        concepts = concepts[:content_slide_count]

        # Create batch assignments (2 slides per batch for ~60s generation time)
        # Each slide takes ~25-35s (design + render), so 2 slides = ~60s safely under 120s
        # Batch structure: [cover], [content 1-2], [content 3-4], ..., [closing]
        SLIDES_PER_BATCH = 2
        batches = []

        # Batch 0: Cover slide only
        batches.append({
            "batch_index": 0,
            "slide_type": "cover",
            "slide_indices": [0],
            "description": "Slide de capa"
        })

        # Content batches
        content_indices = list(range(1, content_slide_count + 1))
        batch_index = 1
        for i in range(0, len(content_indices), SLIDES_PER_BATCH):
            batch_indices = content_indices[i:i + SLIDES_PER_BATCH]
            batches.append({
                "batch_index": batch_index,
                "slide_type": "content",
                "slide_indices": batch_indices,
                "concept_indices": [idx - 1 for idx in batch_indices],  # 0-based for concepts array
                "description": f"Slides de conteúdo {batch_indices[0]}-{batch_indices[-1]}"
            })
            batch_index += 1

        # Final batch: Closing slide
        batches.append({
            "batch_index": batch_index,
            "slide_type": "closing",
            "slide_indices": [total_slides - 1],
            "description": "Slide de encerramento"
        })

        # Generate unique ID for this deck generation (prevents S3 overwrite)
        generation_id = f"{int(datetime.now().timestamp() * 1000)}-{uuid.uuid4().hex[:8]}"

        print(f"[SlideDeck v4] Plan complete: {len(batches)} batches (archetype: {archetype}, gen_id: {generation_id})")

        return {
            "deck_title": episode_title,
            "total_slides": total_slides,
            "content_slide_count": content_slide_count,
            "concepts": concepts,
            "batches": batches,
            "archetype": archetype,  # v5: Return selected archetype
            "generation_id": generation_id,  # v6: Unique ID to prevent S3 overwrite
            "version": "v6-unique-generation-id",
        }

    async def generate_batch(
        self,
        batch_type: str,
        episode_title: str = "Aula",
        episode_id: str = "unknown",
        concepts: List[Dict[str, Any]] = None,
        concept_indices: List[int] = None,
        slide_indices: List[int] = None,
        style: str = "corporate",
        generation_id: str = None,
    ) -> Dict[str, Any]:
        """
        PHASE 2: Generate a batch of slides (1-2 slides, ~50-70 seconds).

        This generates a specific batch of slides as determined by the plan.
        Each batch is designed to complete safely under the 120s timeout.

        Args:
            batch_type: "cover", "content", or "closing"
            episode_title: Title of the episode
            episode_id: Unique episode identifier for S3
            concepts: List of all concepts from plan (for content batches)
            concept_indices: Which concepts to generate (0-based, for content batches)
            slide_indices: Which slide numbers to generate (for S3 naming)
            style: Design style
            generation_id: Unique ID from plan() to prevent S3 overwrite between generations

        Returns:
            Dict with slides array containing generated slides
        """
        # Use generation_id if provided, otherwise create fallback
        gen_id = generation_id or f"{int(datetime.now().timestamp() * 1000)}"
        print(f"[SlideDeck v4] Generating batch: {batch_type} (slides: {slide_indices}, gen_id: {gen_id})")

        slides = []

        if batch_type == "cover":
            # Generate cover slide
            print(f"  [Cover] Designing...")
            cover_design = await self._generate_cover_slide(episode_title, style)

            print(f"  [Cover] Rendering...")
            cover_bytes = await self._render_slide(cover_design)

            print(f"  [Cover] Uploading...")
            slide_num = slide_indices[0] + 1  # 1-based for S3
            cover_url = await self._upload_to_s3(cover_bytes, episode_id, slide_num, gen_id)

            slides.append({
                "id": f"slide-{slide_num}",
                "index": slide_indices[0],
                "title": "Capa",
                "image_url": cover_url,
                "slide_type": "cover",
            })
            print(f"  [Cover] Complete!")

        elif batch_type == "content":
            # Generate content slides from concepts
            if not concepts or concept_indices is None:
                raise ValueError("Content batch requires concepts and concept_indices")

            for i, concept_idx in enumerate(concept_indices):
                if concept_idx >= len(concepts):
                    print(f"  [Warning] Concept index {concept_idx} out of range, skipping")
                    continue

                concept = concepts[concept_idx]
                slide_idx = slide_indices[i] if i < len(slide_indices) else concept_idx + 1
                slide_num = slide_idx + 1  # 1-based for S3

                # Build content from concept
                content = f"""
Título: {concept.get('title', f'Conceito {concept_idx + 1}')}

{concept.get('content', '')}

Pontos-chave:
{chr(10).join('• ' + p for p in concept.get('key_points', []))}

Visual: {concept.get('visual_hint', '')}
"""

                print(f"  [Content {slide_num}] Designing...")
                try:
                    design_spec = await self._design_slide(content, style)
                except Exception as e:
                    print(f"  [Content {slide_num}] Design failed: {e}")
                    continue

                print(f"  [Content {slide_num}] Rendering...")
                try:
                    image_bytes = await self._render_slide(design_spec)
                except Exception as e:
                    print(f"  [Content {slide_num}] Render failed: {e}")
                    continue

                print(f"  [Content {slide_num}] Uploading...")
                try:
                    image_url = await self._upload_to_s3(image_bytes, episode_id, slide_num, gen_id)
                except Exception as e:
                    print(f"  [Content {slide_num}] Upload failed: {e}")
                    continue

                slides.append({
                    "id": f"slide-{slide_num}",
                    "index": slide_idx,
                    "title": concept.get('title', f'Slide {slide_num}'),
                    "image_url": image_url,
                    "slide_type": "content",
                })
                print(f"  [Content {slide_num}] Complete!")

        elif batch_type == "closing":
            # Generate closing slide
            print(f"  [Closing] Designing...")
            closing_design = await self._generate_closing_slide(episode_title, style)

            print(f"  [Closing] Rendering...")
            closing_bytes = await self._render_slide(closing_design)

            print(f"  [Closing] Uploading...")
            slide_num = slide_indices[0] + 1  # 1-based for S3
            closing_url = await self._upload_to_s3(closing_bytes, episode_id, slide_num, gen_id)

            slides.append({
                "id": f"slide-{slide_num}",
                "index": slide_indices[0],
                "title": "Encerramento",
                "image_url": closing_url,
                "slide_type": "closing",
            })
            print(f"  [Closing] Complete!")

        print(f"[SlideDeck v4] Batch complete: {len(slides)} slides generated")

        return {
            "batch_type": batch_type,
            "slides": slides,
            "generatedAt": datetime.utcnow().isoformat() + "Z",
        }
