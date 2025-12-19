# =============================================================================
# VideoClassAgent - Slides + TTS Video Generator
# =============================================================================
# Generates educational videos using programmatic slides and ElevenLabs TTS.
#
# Architecture:
# 1. Gemini extracts concepts and generates roteiro (script)
# 2. Pillow renders slides as PNG images
# 3. ElevenLabs generates single-voice narration
# 4. FFmpeg combines slides + audio into MP4
# 5. Upload to S3 and return presigned URL
#
# Benefits over Veo 3.1:
# - Cost: $0.01/video vs $6.00/video (600x cheaper)
# - Duration: 60+ seconds vs 8 seconds max
# - Quality: Consistent vs inconsistent
# - Control: Full control vs none
#
# Framework: Google Gemini API (direct, no ADK sessions)
# TTS: ElevenLabs single-voice (text_to_speech)
# Video: FFmpeg via Lambda Layer
# =============================================================================

from google import genai
from tools.slide_renderer import render_slide, GRADIENTS
from tools.elevenlabs_tool import text_to_speech, VOICE_SARAH, VOICE_ERIC
from .utils import MODEL_GEMINI, parse_json_safe
from botocore.config import Config
from typing import Dict, Any, List, Optional
import boto3
import base64
import uuid
import os

# =============================================================================
# Configuration
# =============================================================================

AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
VIDEOS_BUCKET = os.getenv("VIDEOS_BUCKET", "hive-academy-videos-prod")

# S3 client config - use virtual-hosted style with s3v4 signature
S3_CONFIG = Config(
    signature_version="s3v4",
    s3={"addressing_style": "virtual"},
)

# Default voice for narration (single voice, not dialogue)
DEFAULT_NARRATOR_VOICE = VOICE_SARAH  # Female narrator

# Target video duration
DEFAULT_DURATION_SECONDS = 60

# MVP mode: Return slides + audio separately for frontend composition
# This avoids FFmpeg dependency in AgentCore runtime
MVP_MODE = True

# =============================================================================
# Roteiro (Script) Prompt Template
# =============================================================================

ROTEIRO_GENERATION_PROMPT = """
Você é um especialista em criar roteiros educacionais para vídeos curtos.

## Tarefa
Crie um roteiro de vídeo educacional com base na transcrição fornecida.
O vídeo terá {duration} segundos de duração total.

## Estrutura do Roteiro
Crie entre 4 e 6 slides, cada um com:
- Um título claro e conciso
- Conteúdo visual (bullets, diagrama ou resumo)
- Texto de narração para áudio

## Tipos de Slide Disponíveis
1. **title**: Slide de título (título + subtítulo)
2. **bullets**: Slide com pontos-chave (título + 3-5 bullets)
3. **diagram**: Slide de fluxo/processo (título + elementos sequenciais)
4. **summary**: Slide de resumo (título + takeaways principais)

## Regras OBRIGATÓRIAS
1. Primeiro slide DEVE ser tipo "title" com o tema principal
2. Último slide DEVE ser tipo "summary" com os pontos principais
3. Slides intermediários podem ser "bullets" ou "diagram"
4. Narração deve ser natural, didática e em português brasileiro
5. Cada slide deve ter narração de 10-15 segundos (30-50 palavras)
6. Use linguagem acessível, evite jargões técnicos complexos
7. {custom_instructions}

## Transcrição da Aula
{transcription}

## Formato de Saída (JSON)
Retorne APENAS o JSON válido, sem texto adicional:
{{
  "title": "Título do Vídeo",
  "slides": [
    {{
      "id": 1,
      "type": "title",
      "title": "Título Principal",
      "subtitle": "Subtítulo opcional",
      "narration": "Texto da narração para este slide...",
      "duration_seconds": 8
    }},
    {{
      "id": 2,
      "type": "bullets",
      "title": "Conceitos Principais",
      "bullets": [
        "Primeiro ponto importante",
        "Segundo ponto importante",
        "Terceiro ponto importante"
      ],
      "narration": "Vamos explorar os conceitos principais...",
      "duration_seconds": 15
    }},
    {{
      "id": 3,
      "type": "diagram",
      "title": "Como Funciona",
      "elements": ["Entrada", "Processamento", "Saída"],
      "narration": "O processo funciona em três etapas...",
      "duration_seconds": 12
    }},
    {{
      "id": 4,
      "type": "summary",
      "title": "Resumo",
      "key_points": [
        "Primeiro takeaway",
        "Segundo takeaway",
        "Terceiro takeaway"
      ],
      "narration": "Recapitulando os pontos principais...",
      "duration_seconds": 10
    }}
  ],
  "total_duration_seconds": 45
}}
"""

# =============================================================================
# VideoClassAgent Implementation
# =============================================================================


class VideoClassAgent:
    """
    Video Class Agent - Generates educational videos via Slides + TTS.

    Pipeline:
    1. Gemini generates roteiro (script) with slides and narration
    2. Pillow renders slides as PNG images
    3. ElevenLabs generates audio from narration text
    4. FFmpeg combines slides + audio into MP4
    5. Upload to S3 and return presigned URL

    Cost: ~$0.01 per 60-second video (vs $6.00 for Veo 3.1)
    """

    def __init__(self):
        """Initialize Gemini client for roteiro generation."""
        self.genai_client = genai.Client()
        print(f"VideoClassAgent initialized with model: {MODEL_GEMINI}")

    async def _generate_roteiro(
        self,
        transcription: str,
        duration_seconds: int = DEFAULT_DURATION_SECONDS,
        custom_prompt: str = "",
    ) -> Dict[str, Any]:
        """
        Generate roteiro (script) from transcription using Gemini.

        Args:
            transcription: Episode transcription text
            duration_seconds: Target video duration
            custom_prompt: Optional custom instructions

        Returns:
            Dict with title, slides array, total_duration_seconds
        """
        custom_instructions = f"Foco especial: {custom_prompt}" if custom_prompt else ""

        prompt = ROTEIRO_GENERATION_PROMPT.format(
            duration=duration_seconds,
            custom_instructions=custom_instructions,
            transcription=transcription[:8000],  # Limit transcription length
        )

        try:
            response = self.genai_client.models.generate_content(
                model=MODEL_GEMINI,
                contents=prompt,
            )

            response_text = response.text if response.text else ""
            print(f"[VideoClass] Roteiro response length: {len(response_text)}")

            return parse_json_safe(response_text)

        except Exception as e:
            print(f"[VideoClass] Roteiro generation error: {str(e)}")
            return {"error": str(e)}

    def _render_slides(
        self,
        slides: List[Dict[str, Any]],
        gradient: str = "dark_purple",
    ) -> List[bytes]:
        """
        Render slides to PNG images using Pillow.

        Args:
            slides: List of slide definitions from roteiro
            gradient: Gradient preset name

        Returns:
            List of PNG images as bytes
        """
        rendered = []

        for i, slide in enumerate(slides):
            try:
                # Normalize slide structure for renderer
                slide_type = slide.get("type", "bullets")

                # Map roteiro fields to renderer expectations
                if slide_type == "summary":
                    # Summary uses key_points, renderer expects key_points
                    pass
                elif slide_type == "diagram":
                    # Diagram uses elements
                    pass

                png_bytes = render_slide(slide, gradient)
                rendered.append(png_bytes)
                print(f"[VideoClass] Rendered slide {i + 1}: {slide_type}")

            except Exception as e:
                print(f"[VideoClass] Error rendering slide {i + 1}: {e}")
                # Create fallback slide
                fallback = {
                    "type": "bullets",
                    "title": slide.get("title", f"Slide {i + 1}"),
                    "bullets": ["Conteúdo não disponível"],
                }
                rendered.append(render_slide(fallback, gradient))

        return rendered

    def _generate_narration(
        self,
        slides: List[Dict[str, Any]],
        voice_id: str = DEFAULT_NARRATOR_VOICE,
    ) -> bytes:
        """
        Generate audio narration from slide scripts using ElevenLabs.

        Args:
            slides: List of slides with narration text
            voice_id: ElevenLabs voice ID

        Returns:
            MP3 audio as bytes
        """
        # Combine all narrations into one text
        # This is more cost-efficient than multiple API calls
        narrations = []

        for slide in slides:
            narration = slide.get("narration", "")
            if narration:
                narrations.append(narration)

        full_narration = " ... ".join(narrations)

        print(f"[VideoClass] Generating narration: {len(full_narration)} chars")

        try:
            audio_bytes = text_to_speech(
                text=full_narration,
                voice_id=voice_id,
            )
            print(f"[VideoClass] Narration generated: {len(audio_bytes)} bytes")
            return audio_bytes

        except Exception as e:
            print(f"[VideoClass] Narration error: {e}")
            raise

    def _upload_to_s3(
        self,
        content: bytes,
        episode_id: str,
        file_type: str = "audio",
        extension: str = "mp3",
    ) -> str:
        """
        Upload content to S3 and return presigned URL.

        Args:
            content: File content as bytes
            episode_id: Episode identifier for S3 path
            file_type: Type of file (audio, slide, video)
            extension: File extension

        Returns:
            Presigned URL for file access
        """
        s3_client = boto3.client(
            "s3",
            region_name=AWS_REGION,
            config=S3_CONFIG,
        )

        file_key = f"generated/{episode_id}/{file_type}_{uuid.uuid4()}.{extension}"

        content_types = {
            "mp3": "audio/mpeg",
            "png": "image/png",
            "mp4": "video/mp4",
        }

        s3_client.put_object(
            Bucket=VIDEOS_BUCKET,
            Key=file_key,
            Body=content,
            ContentType=content_types.get(extension, "application/octet-stream"),
        )

        # Generate presigned URL (1 hour expiration)
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": VIDEOS_BUCKET, "Key": file_key},
            ExpiresIn=3600,
        )

        print(f"[VideoClass] Uploaded {file_type} to S3: {file_key}")
        return url

    async def generate(
        self,
        transcription: str,
        format: str = "brief",
        visual_theme: str = "dark_purple",
        custom_prompt: str = "",
        episode_id: str = "",
        user_id: str = "anonymous",
        voice_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate educational video from transcription.

        MVP Pipeline (MVP_MODE=True):
        1. Gemini generates roteiro (script)
        2. Pillow renders slides as PNG
        3. ElevenLabs generates narration audio
        4. Upload slides + audio to S3
        5. Return URLs for frontend composition

        Full Pipeline (MVP_MODE=False, requires FFmpeg):
        1-3. Same as above
        4. FFmpeg composes slides + audio into MP4
        5. Upload video to S3

        Args:
            transcription: Episode transcription text
            format: Video format (brief=60s, explainer=120s)
            visual_theme: Gradient preset name
            custom_prompt: Optional focus instructions
            episode_id: Episode identifier for S3 path
            user_id: User identifier
            voice_id: Optional voice ID override

        Returns:
            Dict with video_url (or audio_url + slides), duration_seconds, metadata
        """
        print(f"[VideoClass] Starting Slides+TTS generation for episode {episode_id}")
        print(f"[VideoClass] MVP_MODE: {MVP_MODE}")

        try:
            # Determine target duration based on format
            duration_map = {
                "brief": 60,
                "explainer": 120,
            }
            target_duration = duration_map.get(format, 60)

            # Step 1: Generate roteiro
            print("[VideoClass] Step 1/4: Generating roteiro...")
            roteiro = await self._generate_roteiro(
                transcription=transcription,
                duration_seconds=target_duration,
                custom_prompt=custom_prompt,
            )

            if "error" in roteiro:
                return {
                    "error": f"Roteiro generation failed: {roteiro['error']}",
                    "phase": "slides_tts",
                }

            slides = roteiro.get("slides", [])
            if not slides:
                return {
                    "error": "Roteiro generated no slides",
                    "phase": "slides_tts",
                }

            project_title = roteiro.get("title", "Aula")
            print(f"[VideoClass] Roteiro: {len(slides)} slides, title: {project_title}")

            # Step 2: Render slides
            print("[VideoClass] Step 2/4: Rendering slides...")

            # Map visual_theme to gradient
            gradient = visual_theme if visual_theme in GRADIENTS else "dark_purple"
            slide_images = self._render_slides(slides, gradient)
            print(f"[VideoClass] Rendered {len(slide_images)} slide images")

            # Step 3: Generate narration
            print("[VideoClass] Step 3/4: Generating narration...")
            narrator_voice = voice_id or DEFAULT_NARRATOR_VOICE
            audio_bytes = self._generate_narration(slides, narrator_voice)

            # Calculate slide durations
            slide_durations = [s.get("duration_seconds", 10) for s in slides]
            total_duration = sum(slide_durations)

            # Step 4: Upload to S3 (MVP mode: slides + audio separately)
            print("[VideoClass] Step 4/4: Uploading to S3...")

            if MVP_MODE:
                # MVP: Upload audio and return slide data for frontend rendering
                audio_url = self._upload_to_s3(
                    audio_bytes, episode_id, "narration", "mp3"
                )

                # Upload slides as PNGs and get URLs
                slide_urls = []
                for i, slide_image in enumerate(slide_images):
                    slide_url = self._upload_to_s3(
                        slide_image, episode_id, f"slide_{i:02d}", "png"
                    )
                    slide_urls.append(slide_url)

                print(f"[VideoClass] Uploaded {len(slide_urls)} slides + audio")

                # Build slide metadata with URLs
                slides_with_urls = []
                for i, s in enumerate(slides):
                    slides_with_urls.append({
                        "id": s.get("id", i + 1),
                        "type": s.get("type"),
                        "title": s.get("title"),
                        "duration_seconds": s.get("duration_seconds", 10),
                        "image_url": slide_urls[i] if i < len(slide_urls) else None,
                    })

                return {
                    "audio_url": audio_url,
                    "duration_seconds": total_duration,
                    "project_title": project_title,
                    "slide_count": len(slides),
                    "format": format,
                    "visual_theme": visual_theme,
                    "is_audio_only": True,  # MVP returns slides + audio separately
                    "phase": "slides_tts_mvp",
                    "slides": slides_with_urls,
                }

            else:
                # Full mode: Compose video with FFmpeg (requires FFmpeg in runtime)
                from tools.video_composer import compose_video_simple, upload_video_to_s3

                print("[VideoClass] Composing video with FFmpeg...")
                video_bytes = compose_video_simple(
                    slide_images=slide_images,
                    audio_bytes=audio_bytes,
                    slide_durations=slide_durations,
                )
                print(f"[VideoClass] Video composed: {len(video_bytes)} bytes")

                video_url = upload_video_to_s3(video_bytes, episode_id)
                print(f"[VideoClass] Video URL: {video_url[:80]}...")

                return {
                    "video_url": video_url,
                    "duration_seconds": total_duration,
                    "project_title": project_title,
                    "slide_count": len(slides),
                    "format": format,
                    "visual_theme": visual_theme,
                    "is_audio_only": False,
                    "phase": "slides_tts",
                    "roteiro": {
                        "title": project_title,
                        "slides": [
                            {
                                "id": s.get("id", i + 1),
                                "type": s.get("type"),
                                "title": s.get("title"),
                                "duration_seconds": s.get("duration_seconds"),
                            }
                            for i, s in enumerate(slides)
                        ],
                    },
                }

        except Exception as e:
            print(f"[VideoClass] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "error": str(e),
                "phase": "slides_tts",
            }
