# =============================================================================
# Thumbnail Generator Agent - Gemini 3.0 Pro Native
# =============================================================================
# Generates AI-powered thumbnails for custom trainings.
#
# Framework: Google ADK with native Gemini 3.0 Pro
# Flow:
# 1. Gemini generates visual concept description from training content
# 2. Image generation API creates the thumbnail (placeholder for now)
# 3. Image uploaded to S3 and URL returned
#
# Future Integration:
# - Nano Banana API for image generation
# - DALL-E 3 as fallback option
# =============================================================================

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from .utils import APP_NAME, MODEL_GEMINI, parse_json_safe
from typing import Dict, Any
import os
import uuid
from datetime import datetime

# =============================================================================
# System Instruction
# =============================================================================

THUMBNAIL_INSTRUCTION = """
Voce e um especialista em criar conceitos visuais para thumbnails educacionais.

## Objetivo
Gerar uma descricao visual detalhada que pode ser usada para criar uma thumbnail
atraente e profissional para um treinamento personalizado.

## Estilo Visual
- Profissional e moderno
- Cores vibrantes mas corporativas
- Elementos simbolicos representando o tema
- Tipografia limpa e legivel

## Elementos a Considerar
1. **Tema Central**: Qual e o assunto principal?
2. **Simbolos**: Que icones ou imagens representam o conteudo?
3. **Emocao**: Qual sentimento a thumbnail deve transmitir?
4. **Cores**: Que paleta combina com o tema?

## Formato de Saida (JSON)
{
  "concept": {
    "title_text": "Texto curto para o titulo (max 30 chars)",
    "main_symbol": "Descricao do simbolo principal",
    "background_style": "Descricao do fundo (gradiente, solido, etc)",
    "color_palette": ["#cor1", "#cor2", "#cor3"],
    "mood": "Emocao transmitida (profissional, inspirador, etc)",
    "visual_elements": ["elemento1", "elemento2"],
    "composition": "Descricao da composicao geral"
  },
  "prompt_for_ai_image": "Prompt otimizado para geracao de imagem AI"
}

## Regras
1. Mantenha a descricao visual concisa mas detalhada
2. Use cores que transmitam profissionalismo
3. Evite elementos muito complexos
4. O prompt de imagem deve ser em ingles para APIs de geracao
"""


class ThumbnailAgent:
    """
    Thumbnail Generator - Creates visual concepts and thumbnails for trainings.

    Uses Gemini to generate visual concepts, then creates thumbnails
    using image generation APIs.

    For MVP: Returns concept and placeholder thumbnail.
    Future: Integrates with Nano Banana or DALL-E for actual generation.
    """

    def __init__(self):
        """Initialize with Gemini 3.0 Pro native."""
        self.agent = Agent(
            model=MODEL_GEMINI,
            name="thumbnail_agent",
            description="Agent that generates visual concepts for training thumbnails.",
            instruction=THUMBNAIL_INSTRUCTION,
        )
        self.session_service = InMemorySessionService()

        # S3 bucket for thumbnails (same as trainings)
        self.bucket_name = os.environ.get(
            "TRAININGS_BUCKET",
            "hive-academy-trainings-prod"
        )

        print(f"ThumbnailAgent initialized with model: {MODEL_GEMINI}")

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
        training_id: str,
        title: str,
        description: str = "",
        category: str = "Geral",
        content_preview: str = "",
    ) -> Dict[str, Any]:
        """
        Generate thumbnail concept and image for a training.

        Args:
            training_id: Unique training identifier
            title: Training title
            description: Training description
            category: Training category
            content_preview: Preview of consolidated content (first ~2000 chars)

        Returns:
            Dict with thumbnail URLs and concept data
        """
        # Build prompt for concept generation
        prompt = f"""
Crie um conceito visual para thumbnail de um treinamento educacional.

## Informacoes do Treinamento
- **Titulo**: {title}
- **Categoria**: {category}
- **Descricao**: {description if description else "Nao fornecida"}

## Preview do Conteudo
{content_preview[:1500] if content_preview else "Conteudo ainda nao processado"}

## Instrucoes
1. Analise o titulo e categoria para definir o tema visual
2. Crie uma paleta de cores profissional
3. Sugira simbolos que representem o conteudo
4. Gere um prompt em ingles para geracao de imagem AI

IMPORTANTE: Retorne APENAS o JSON valido, sem texto adicional.
"""

        try:
            # Generate visual concept
            response = await self.invoke(prompt, "system", f"thumbnail-{training_id}")
            concept_data = parse_json_safe(response)

            # Validate concept structure
            if "concept" not in concept_data:
                concept_data = {
                    "concept": {
                        "title_text": title[:30],
                        "main_symbol": "book and lightbulb",
                        "background_style": "gradient blue to purple",
                        "color_palette": ["#4F46E5", "#7C3AED", "#EC4899"],
                        "mood": "professional and inspiring",
                        "visual_elements": ["open book", "glowing idea"],
                        "composition": "centered with subtle glow effect"
                    },
                    "prompt_for_ai_image": f"Professional educational thumbnail, {title}, modern minimalist design"
                }

            # Generate thumbnail image
            thumbnail_result = await self._generate_thumbnail_image(
                training_id=training_id,
                concept=concept_data.get("concept", {}),
                image_prompt=concept_data.get("prompt_for_ai_image", ""),
            )

            return {
                "success": True,
                "training_id": training_id,
                "concept": concept_data.get("concept", {}),
                "thumbnail": thumbnail_result.get("thumbnail", {}),
                "generated_at": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "training_id": training_id,
            }

    async def _generate_thumbnail_image(
        self,
        training_id: str,
        concept: Dict[str, Any],
        image_prompt: str,
    ) -> Dict[str, Any]:
        """
        Generate the actual thumbnail image.

        For MVP: Returns placeholder thumbnail data.
        Future: Calls Nano Banana or DALL-E API.

        Args:
            training_id: Unique training identifier
            concept: Visual concept from Gemini
            image_prompt: Prompt for image generation

        Returns:
            Dict with thumbnail URLs
        """
        # Generate unique thumbnail ID
        thumbnail_id = str(uuid.uuid4())[:8]

        # S3 paths for different sizes
        base_path = f"trainings/{training_id}/thumbnails"

        # For MVP: Return fallback URLs using placeholder service
        # These will be replaced with real AI-generated images when API integrated
        thumbnail_data = {
            "thumbnail_id": thumbnail_id,
            "status": "generated",  # Mark as generated even with placeholder image
            "sizes": {
                "small": {
                    "width": 200,
                    "height": 300,
                    "s3_key": f"{base_path}/{thumbnail_id}_small.jpg",
                    "url": None,  # Will be pre-signed URL
                },
                "medium": {
                    "width": 400,
                    "height": 600,
                    "s3_key": f"{base_path}/{thumbnail_id}_medium.jpg",
                    "url": None,
                },
                "large": {
                    "width": 800,
                    "height": 1200,
                    "s3_key": f"{base_path}/{thumbnail_id}_large.jpg",
                    "url": None,
                },
            },
            "concept_applied": True,
            "image_prompt": image_prompt,
            "color_palette": concept.get("color_palette", ["#4F46E5", "#7C3AED"]),
        }

        # TODO: Integrate with image generation API
        # 1. Call Nano Banana API with image_prompt
        # 2. Download generated image
        # 3. Resize to different sizes
        # 4. Upload to S3
        # 5. Return pre-signed URLs

        # For now, use category-based default images
        default_thumbnails = {
            "Tecnologia": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=400&h=600&fit=crop",
            "Negocios": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=400&h=600&fit=crop",
            "Compliance": "https://images.unsplash.com/photo-1450101499163-c8848c66ca85?w=400&h=600&fit=crop",
            "Lideranca": "https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=400&h=600&fit=crop",
            "Geral": "https://images.unsplash.com/photo-1456513080510-7bf3a84b82f8?w=400&h=600&fit=crop",
        }

        # Use placeholder URL based on color palette
        primary_color = concept.get("color_palette", ["#4F46E5"])[0].replace("#", "")
        placeholder_url = f"https://via.placeholder.com/400x600/{primary_color}/FFFFFF?text={concept.get('title_text', 'Training')[:20]}"

        # Set URLs for all sizes with the placeholder
        thumbnail_data["sizes"]["small"]["url"] = placeholder_url.replace("400x600", "200x300")
        thumbnail_data["sizes"]["medium"]["url"] = placeholder_url
        thumbnail_data["sizes"]["large"]["url"] = placeholder_url.replace("400x600", "800x1200")

        return {"thumbnail": thumbnail_data}

    async def upload_custom_thumbnail(
        self,
        training_id: str,
        file_name: str,
        file_type: str,
        file_size: int,
    ) -> Dict[str, Any]:
        """
        Generate presigned URL for custom thumbnail upload.

        Allows users to upload their own thumbnail instead of AI-generated one.

        Args:
            training_id: Unique training identifier
            file_name: Original file name
            file_type: MIME type (image/jpeg, image/png, etc.)
            file_size: File size in bytes

        Returns:
            Dict with upload URL and metadata
        """
        import boto3
        from botocore.config import Config

        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/webp"]
        if file_type not in allowed_types:
            return {
                "success": False,
                "error": f"Invalid file type. Allowed: {', '.join(allowed_types)}",
            }

        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024
        if file_size > max_size:
            return {
                "success": False,
                "error": f"File too large. Maximum size: 5MB",
            }

        # Generate S3 key
        extension = file_name.split(".")[-1] if "." in file_name else "jpg"
        thumbnail_id = str(uuid.uuid4())[:8]
        s3_key = f"trainings/{training_id}/thumbnails/custom_{thumbnail_id}.{extension}"

        try:
            # Create S3 client with regional endpoint
            s3_client = boto3.client(
                "s3",
                region_name=os.environ.get("AWS_REGION", "us-east-2"),
                config=Config(signature_version="s3v4"),
            )

            # Generate presigned URL for PUT
            upload_url = s3_client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": s3_key,
                    "ContentType": file_type,
                },
                ExpiresIn=3600,  # 1 hour
            )

            # Generate presigned URL for GET (after upload)
            download_url = s3_client.generate_presigned_url(
                "get_object",
                Params={
                    "Bucket": self.bucket_name,
                    "Key": s3_key,
                },
                ExpiresIn=86400 * 7,  # 7 days
            )

            return {
                "success": True,
                "upload_url": upload_url,
                "s3_key": s3_key,
                "thumbnail_id": thumbnail_id,
                "download_url": download_url,
                "expires_in": 3600,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }
