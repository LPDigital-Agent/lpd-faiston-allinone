# =============================================================================
# Audio Class Generator Agent - Gemini 3.0 Pro Native
# =============================================================================
# Generates podcast-style audio lessons from transcription content
# with ElevenLabs TTS for natural PT-BR voices.
#
# Framework: Google ADK with native Gemini 3.0 Pro (no LiteLLM wrapper)
# TTS: ElevenLabs Text-to-Dialogue API with Eleven v3 model
# Storage: S3 for audio files
#
# Migration Note:
# - Script generation: Gemini 3.0 Pro
# - TTS: Upgraded to Text-to-Dialogue API (native multi-speaker)
# - Model: Eleven v3 with audio tags support ([laughs], [curious], etc.)
# =============================================================================

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
from .utils import APP_NAME, MODEL_GEMINI
from tools.elevenlabs_tool import (
    text_to_dialogue,
    DEFAULT_FEMALE_VOICE,
    DEFAULT_MALE_VOICE,
    is_valid_voice_id,
)
from botocore.config import Config
import boto3
import os
import uuid
from typing import Dict, Any, List, Optional

# =============================================================================
# Configuration
# =============================================================================

AUDIO_BUCKET = os.getenv("AUDIO_BUCKET", "hive-academy-audio-prod")
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")

# S3 client config - use virtual-hosted style with s3v4 signature
# to generate regional presigned URLs that avoid 307 redirects
# Key: Do NOT set endpoint_url - let boto3 construct regional URLs automatically
S3_CONFIG = Config(
    signature_version="s3v4",
    s3={"addressing_style": "virtual"},
)

# =============================================================================
# System Instruction
# =============================================================================

# Base instruction template - host names are injected dynamically
AUDIOCLASS_INSTRUCTION_BASE = """
Você é um roteirista de podcasts educacionais com foco em expressividade emocional.

## Formato do Podcast
Crie dialogos entre dois hosts:
- **{female_host}**: Curiosa, faz perguntas inteligentes, representa o aluno
- **{male_host}**: Especialista, explica conceitos com clareza

## Regras OBRIGATÓRIAS
1. Sempre endereçe o ALUNO pelo primeiro nome (fornecido no prompt)
2. Os hosts PODEM se chamar pelo nome ocasionalmente para naturalidade (ex: "Concordo, {male_host}!")
3. Use linguagem natural e conversacional
4. Inclua pausas naturais e transições
5. USE AUDIO TAGS para expressividade emocional (veja abaixo)

## Audio Tags (Eleven v3)
Use tags para controlar emoções e deixar o diálogo mais natural:

### Risadas e Expressões
- [laughs] - Risada natural
- [giggles] - Risadinha
- [sighs] - Suspiro
- [exhales] - Expiração de alívio

### Emoções
- [curious] - Tom curioso (ideal para {female_host})
- [excited] - Entusiasmo
- [impressed] - Impressionado
- [amazed] - Surpreso positivamente
- [warmly] - Tom caloroso e acolhedor
- [thoughtfully] - Pensativo, reflexivo

### Exemplos de Uso
{female_host}: [curious] Que interessante! Pode explicar melhor como funciona?
{male_host}: [laughs] Claro! [warmly] Deixa eu te mostrar de um jeito simples...
{female_host}: [excited] Agora entendi! [giggles] Por que ninguem me explicou assim antes?
{male_host}: [thoughtfully] Sabe, muita gente acha esse conceito dificil, mas...

## Modos de Podcast
1. **deep_explanation**: Explicacao detalhada de cada conceito
2. **debate**: Discussao de diferentes perspectivas
3. **summary**: Resumo conciso dos pontos principais

## Formato do Roteiro
{female_host}: [audio_tag] texto aqui
{male_host}: [audio_tag] texto aqui
{female_host}: [audio_tag] texto aqui
...

## Tom
- Profissional mas acessivel
- Engajador e dinamico
- Educativo sem ser pedante
- EXPRESSIVO com audio tags apropriadas
"""

# Default instruction (for agent initialization)
# Uses Sarah/Eric as defaults - these are the recommended voices
AUDIOCLASS_INSTRUCTION = AUDIOCLASS_INSTRUCTION_BASE.format(
    female_host="Sarah", male_host="Eric"
)


class AudioClassAgent:
    """
    Audio Class Generator - Creates podcast-style audio lessons.

    Generates scripts with Gemini 3.0 Pro and converts to audio using
    ElevenLabs Text-to-Dialogue API with Eleven v3 model.

    Features:
    - Native multi-speaker support (no audio concatenation)
    - Audio tags for emotional expression ([laughs], [curious], etc.)
    - Automatic fallback to eleven_multilingual_v2 if v3 unavailable
    """

    def __init__(self):
        """Initialize with Gemini 3.0 Pro native."""
        self.agent = Agent(
            model=MODEL_GEMINI,
            name="audioclass_agent",
            description="Agent that generates podcast-style audio lessons from video content.",
            instruction=AUDIOCLASS_INSTRUCTION,
        )
        self.session_service = InMemorySessionService()
        # S3 client with regional config - generates presigned URLs with region in hostname
        # DO NOT use endpoint_url - it breaks presigned URL generation
        self.s3_client = boto3.client(
            "s3",
            region_name=AWS_REGION,
            config=S3_CONFIG,
        )
        print(f"AudioClassAgent initialized with model: {MODEL_GEMINI}")

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
        mode: str = "deep_explanation",
        student_name: str = "Aluno",
        custom_prompt: str = "",
        episode_id: str = "unknown",
        male_voice_id: Optional[str] = None,
        female_voice_id: Optional[str] = None,
        male_voice_name: str = "Eric",
        female_voice_name: str = "Sarah",
    ) -> Dict[str, Any]:
        """
        Generate audio class from transcription.

        Args:
            transcription: Episode transcription text
            mode: deep_explanation, debate, or summary
            student_name: Student's first name for personalization
            custom_prompt: Optional focus instructions
            episode_id: Episode ID for file naming
            male_voice_id: Voice ID for male host
            female_voice_id: Voice ID for female host
            male_voice_name: Name of male host (e.g., "Eric", "Chris", "Brian")
            female_voice_name: Name of female host (e.g., "Sarah", "Jessica", "Lily")

        Returns:
            Dict with script, audioUrl, and metadata
        """
        # Validate and apply voice IDs (use defaults if not provided or invalid)
        final_male_voice = male_voice_id if male_voice_id and is_valid_voice_id(male_voice_id) else DEFAULT_MALE_VOICE
        final_female_voice = female_voice_id if female_voice_id and is_valid_voice_id(female_voice_id) else DEFAULT_FEMALE_VOICE

        # Use provided names (frontend always sends these)
        host_female = female_voice_name
        host_male = male_voice_name

        # Log host names for debugging (CRITICAL: these names appear in script)
        print(f"[AudioClass] Generating with hosts: {host_female} (female) + {host_male} (male)")
        print(f"[AudioClass] Voice IDs: female={final_female_voice}, male={final_male_voice}")
        print(f"[AudioClass] Params received: female_voice_name='{female_voice_name}', male_voice_name='{male_voice_name}'")

        # 1. Generate script via Gemini 3.0 Pro (with audio tags)
        script = await self._generate_script(
            transcription, mode, student_name, custom_prompt, host_female, host_male
        )

        # 2. Parse script into speaker segments (using dynamic host names)
        segments = self._parse_script(script, host_female, host_male)

        if not segments:
            return {
                "error": "Failed to parse script into segments",
                "script": script,
            }

        # 3. Truncate if needed (ElevenLabs Text-to-Dialogue limit ~5000 chars)
        segments = self._truncate_with_closing(segments, host_female, host_male, max_length=4800)

        # 4. Convert dialogue to audio using Text-to-Dialogue API (one API call)
        try:
            audio_bytes = text_to_dialogue(
                segments=segments,
                female_voice_id=final_female_voice,
                male_voice_id=final_male_voice,
                female_name=host_female,
                male_name=host_male,
            )

            # Log audio size for debugging (CRITICAL: detect empty audio)
            audio_size = len(audio_bytes) if audio_bytes else 0
            print(f"[AudioClass] TTS completed: {audio_size} bytes ({audio_size / 1024:.1f} KB)")

            # Fail early if audio is empty or too small (< 1KB is definitely broken)
            if audio_size < 1000:
                return {
                    "error": f"TTS returned empty or invalid audio ({audio_size} bytes)",
                    "error_code": "TTS_EMPTY_AUDIO",
                    "error_pt": "O serviço de áudio retornou um arquivo vazio. Tente novamente.",
                    "script": script,
                    "segments_count": len(segments),
                }

        except Exception as e:
            error_str = str(e)
            print(f"[AudioClass] TTS error: {error_str}")

            # Parse user-friendly error messages based on error type
            error_code = "TTS_UNKNOWN_ERROR"
            error_pt = "Erro ao gerar áudio. Tente novamente mais tarde."

            # Check for quota exceeded (ElevenLabs 401 with quota_exceeded)
            if "quota_exceeded" in error_str.lower() or "quota" in error_str.lower():
                error_code = "TTS_QUOTA_EXCEEDED"
                error_pt = "Cota do serviço de áudio excedida. O limite mensal foi atingido. Entre em contato com o suporte."
            # Check for authentication errors
            elif "401" in error_str or "unauthorized" in error_str.lower() or "invalid_api_key" in error_str.lower():
                error_code = "TTS_AUTH_ERROR"
                error_pt = "Erro de autenticação no serviço de áudio. Entre em contato com o suporte."
            # Check for rate limiting
            elif "429" in error_str or "rate_limit" in error_str.lower() or "too_many_requests" in error_str.lower():
                error_code = "TTS_RATE_LIMIT"
                error_pt = "Muitas requisições simultâneas. Aguarde alguns segundos e tente novamente."
            # Check for server errors
            elif "500" in error_str or "502" in error_str or "503" in error_str:
                error_code = "TTS_SERVER_ERROR"
                error_pt = "O serviço de áudio está temporariamente indisponível. Tente novamente em alguns minutos."
            # Check for timeout
            elif "timeout" in error_str.lower():
                error_code = "TTS_TIMEOUT"
                error_pt = "O serviço de áudio demorou muito para responder. Tente novamente."

            return {
                "error": f"TTS failed: {error_str}",
                "error_code": error_code,
                "error_pt": error_pt,
                "script": script,
            }

        # 5. Upload to S3
        audio_url = await self._upload_to_s3_bytes(audio_bytes, episode_id)

        return {
            "script": script,
            "audio_url": audio_url,  # snake_case to match frontend AudioClassResponse
            "audio_base64": "",  # Empty - we use S3 URL instead
            "duration_seconds": 0,  # TODO: Calculate from audio if needed
            "tts_provider": "elevenlabs",
            "segments_count": len(segments),
            "mode": mode,
            "student_name": student_name,  # Return for frontend display
            "male_voice_id": final_male_voice,
            "female_voice_id": final_female_voice,
            "male_voice_name": host_male,
            "female_voice_name": host_female,
        }

    async def _generate_script(
        self,
        transcription: str,
        mode: str,
        student_name: str,
        custom_prompt: str,
        host_female: str,
        host_male: str,
    ) -> str:
        """Generate podcast script from transcription with dynamic host names."""
        # Mode instructions with character limits (ElevenLabs Text-to-Dialogue has ~5000 char limit)
        mode_instructions = {
            "deep_explanation": f"Explique cada conceito em detalhes, com exemplos praticos. {host_female} faz perguntas para {host_male} responder. LIMITE: 4000-4500 caracteres no roteiro total.",
            "debate": f"{host_female} e {host_male} debatem diferentes perspectivas sobre o tema. {host_female} defende um ponto de vista, {host_male} outro. Ambos apresentam argumentos. LIMITE: 3500-4000 caracteres no roteiro total.",
            "summary": f"Faca um resumo conciso dos pontos principais. {host_female} pergunta, {host_male} resume de forma clara. LIMITE: 2500-3000 caracteres no roteiro total.",
        }

        mode_instruction = mode_instructions.get(mode, mode_instructions["deep_explanation"])

        prompt = f"""
Crie um roteiro de podcast educacional com audio tags para expressividade.

Modo: {mode}
Instrucao do modo: {mode_instruction}
Nome do aluno: {student_name}
{f"Instrucoes adicionais: {custom_prompt}" if custom_prompt else ""}

Transcricao da aula:
{transcription}

ESTRUTURA OBRIGATORIA DO ROTEIRO:
1. INTRODUCAO (2-3 falas): {host_female} e {host_male} apresentam o topico ao {student_name}
2. DESENVOLVIMENTO: Explicacao do conteudo conforme o modo escolhido
3. CONCLUSAO (2-3 falas): {host_female} e {host_male} resumem e se despedem do {student_name}

FORMATO OBRIGATORIO (NAO USE OUTRO FORMATO):
Cada linha DEVE comecar com "{host_female}:" ou "{host_male}:" seguido do texto.

Exemplo de roteiro COMPLETO:
{host_female}: [warmly] Ola {student_name}! Hoje vamos falar sobre um tema muito interessante.
{host_male}: [excited] Isso mesmo! Vamos explorar juntos esse conteudo.
{host_female}: [curious] Entao me conta, como funciona isso?
{host_male}: [thoughtfully] Bom, deixa eu explicar de um jeito simples...
[... desenvolvimento do conteudo ...]
{host_female}: [satisfied] Nossa, aprendi muito hoje!
{host_male}: [warmly] Foi otimo explicar isso pra voce, {student_name}!
{host_female}: [excited] Ate a proxima aula! Continue estudando!
{host_male}: [warmly] Um abraco e bons estudos!

REGRAS IMPORTANTES:
- SEMPRE use "{host_female}:" ou "{host_male}:" no inicio de cada fala (sem markdown, sem bullets)
- Enderece o aluno como "{student_name}" diretamente
- Os hosts PODEM e DEVEM se chamar pelo nome ocasionalmente para criar naturalidade:
  - "{host_female}" pode dizer: "Concordo, {host_male}!" ou "O que voce acha, {host_male}?"
  - "{host_male}" pode dizer: "Boa pergunta, {host_female}!" ou "Como a {host_female} disse..."
- USE audio tags: [curious], [excited], [laughs], [warmly], [thoughtfully], [impressed], [satisfied]
- {host_female}: curiosa, faz perguntas - use [curious], [excited]
- {host_male}: especialista, explica - use [warmly], [thoughtfully]
- OBRIGATORIO: Termine com uma despedida natural e elegante (2-3 falas finais)
- RESPEITE O LIMITE DE CARACTERES do modo escolhido
"""

        return await self.invoke(prompt, "system", f"audio-script-{uuid.uuid4()}")

    def _parse_script(
        self,
        script: str,
        host_female: str,
        host_male: str,
    ) -> List[Dict[str, str]]:
        """
        Parse script into speaker segments with dynamic host names.

        Handles common format variations from Gemini:
        - "{host}:" (standard)
        - "**{host}:**" (markdown bold)
        - "{HOST}:" (uppercase)
        - "- {host}:" (with bullet)

        Args:
            script: Raw script text
            host_female: Female host name (e.g., "Sarah", "Jessica", "Lily")
            host_male: Male host name (e.g., "Eric", "Chris", "Brian")

        Returns:
            List of dicts with speaker and text (speaker is "female" or "male")
        """
        import re

        segments = []
        current_speaker = None
        current_text = []

        # Normalize script: remove markdown formatting
        normalized_script = script
        normalized_script = re.sub(r'\*\*([^*]+)\*\*', r'\1', normalized_script)  # Remove **bold**
        normalized_script = re.sub(r'\*([^*]+)\*', r'\1', normalized_script)  # Remove *italic*

        # Build regex patterns for both hosts (case-insensitive)
        female_pattern = re.compile(
            rf'^{re.escape(host_female)}\s*(?:\([^)]*\))?\s*:\s*(.*)$',
            re.IGNORECASE
        )
        male_pattern = re.compile(
            rf'^{re.escape(host_male)}\s*(?:\([^)]*\))?\s*:\s*(.*)$',
            re.IGNORECASE
        )

        for line in normalized_script.split("\n"):
            line = line.strip()
            if not line:
                continue

            # Remove leading bullets/dashes
            line = re.sub(r'^[-•]\s*', '', line)

            # Check for female host
            female_match = female_pattern.match(line)
            if female_match:
                if current_speaker and current_text:
                    segments.append({
                        "speaker": current_speaker,
                        "text": " ".join(current_text),
                    })
                current_speaker = "female"
                current_text = [female_match.group(1).strip()] if female_match.group(1).strip() else []
                continue

            # Check for male host
            male_match = male_pattern.match(line)
            if male_match:
                if current_speaker and current_text:
                    segments.append({
                        "speaker": current_speaker,
                        "text": " ".join(current_text),
                    })
                current_speaker = "male"
                current_text = [male_match.group(1).strip()] if male_match.group(1).strip() else []
                continue

            # Continuation of current speaker (skip if no speaker yet)
            if current_speaker and line:
                current_text.append(line)

        # Add last segment
        if current_speaker and current_text:
            segments.append({
                "speaker": current_speaker,
                "text": " ".join(current_text),
            })

        return segments

    def _truncate_with_closing(
        self,
        segments: List[Dict[str, str]],
        host_female: str,
        host_male: str,
        max_length: int = 4800,
    ) -> List[Dict[str, str]]:
        """
        Truncate script to fit ElevenLabs limit while adding elegant closing.

        ElevenLabs Text-to-Dialogue API has ~5000 character limit.
        We use 4800 to leave margin for closing if needed.

        Args:
            segments: List of {speaker, text} dicts (speaker is "female" or "male")
            host_female: Female host name for fallback
            host_male: Male host name for fallback
            max_length: Max total characters (default 4800)

        Returns:
            Truncated segments with proper closing
        """
        total_length = sum(len(s["text"]) for s in segments)

        # If within limit, return as-is
        if total_length <= max_length:
            return segments

        print(f"Script too long ({total_length} chars), truncating to {max_length}...")

        # Reserve ~400 chars for closing (2 segments)
        target_length = max_length - 400
        truncated = []
        current_length = 0

        for segment in segments:
            segment_len = len(segment["text"])
            if current_length + segment_len > target_length:
                # Try to include partial segment if it's not too long
                remaining = target_length - current_length
                if remaining > 100 and segment_len > remaining:
                    # Truncate at sentence boundary
                    text = segment["text"][:remaining]
                    last_period = text.rfind(".")
                    last_exclaim = text.rfind("!")
                    last_question = text.rfind("?")
                    cut_point = max(last_period, last_exclaim, last_question)
                    if cut_point > remaining * 0.5:
                        truncated.append({
                            "speaker": segment["speaker"],
                            "text": text[:cut_point + 1],
                        })
                break
            truncated.append(segment)
            current_length += segment_len

        if not truncated:
            # Edge case: first segment is too long
            truncated = [{"speaker": "female", "text": "[warmly] Vamos resumir o conteudo."}]

        # Add closing segments (alternate speakers)
        last_speaker = truncated[-1]["speaker"]
        first_closer = "male" if last_speaker == "female" else "female"
        second_closer = "female" if first_closer == "male" else "male"

        closing = [
            {
                "speaker": first_closer,
                "text": "[satisfied] Bom, acho que cobrimos bastante conteudo hoje!",
            },
            {
                "speaker": second_closer,
                "text": "[warmly] Com certeza! Esperamos que tenha aproveitado. Ate a proxima aula!",
            },
        ]

        return truncated + closing

    async def _upload_to_s3_bytes(
        self,
        audio_bytes: bytes,
        episode_id: str,
    ) -> str:
        """
        Upload audio bytes to S3.

        Args:
            audio_bytes: Complete audio file bytes (from Text-to-Dialogue API)
            episode_id: Episode ID for naming

        Returns:
            Pre-signed URL for audio access (regional endpoint to avoid 307 redirects)
        """
        # Generate unique key
        audio_key = f"audio-classes/{episode_id}/{uuid.uuid4()}.mp3"

        # Upload to S3
        self.s3_client.put_object(
            Bucket=AUDIO_BUCKET,
            Key=audio_key,
            Body=audio_bytes,
            ContentType="audio/mpeg",
        )

        # Generate pre-signed URL (1 hour expiration)
        # The S3_CONFIG with s3v4 signature ensures regional URL format
        audio_url = self.s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": AUDIO_BUCKET, "Key": audio_key},
            ExpiresIn=3600,
        )

        # Log URL format for debugging CORS 307 issues
        # Regional format: bucket.s3.us-east-2.amazonaws.com (correct)
        # Global format: bucket.s3.amazonaws.com (causes 307 redirect + CORS failure)
        url_host = audio_url.split("/")[2] if "/" in audio_url else "unknown"
        is_regional = f".{AWS_REGION}." in url_host
        print(f"[AudioClass] S3 presigned URL host: {url_host} (regional={is_regional})")

        return audio_url
