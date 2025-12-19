# =============================================================================
# ElevenLabs TTS Tool - Text-to-Dialogue API
# =============================================================================
# Text-to-speech integration using ElevenLabs SDK with Text-to-Dialogue API
# for generating high-quality multi-speaker PT-BR audio.
#
# Migration: Upgraded from raw httpx to official ElevenLabs SDK
# API: Text-to-Dialogue (native multi-speaker support)
# Model: eleven_v3 (supports audio tags for emotional expression)
#
# Voice Selection:
# Users can choose from 3 female and 3 male voices.
# All voices work well with PT-BR via eleven_v3 model.
#
# Default Hosts:
# - Sarah (female): Soft, warm - curious host, asks questions
# - Eric (male): Smooth tenor - expert host, explains concepts
# =============================================================================

import os
from typing import Optional, Dict, List, Any
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# ElevenLabs SDK imports
from elevenlabs import ElevenLabs, DialogueInput
from elevenlabs import UnauthorizedError, NotFoundError, BadRequestError

# =============================================================================
# Configuration
# =============================================================================

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")

# =============================================================================
# Available Voices
# =============================================================================
# All voices are tested with PT-BR and eleven_v3 model

# Female Voices (curious host role)
VOICE_SARAH = "EXAVITQu4vr4xnSDxMaL"    # Sarah - Soft, warm (RECOMMENDED)
VOICE_JESSICA = "cgSgspJ2msm6clMCkdW9"  # Jessica - Expressive, lively
VOICE_LILY = "pFZP5JQG7iQjIQuC4Bku"     # Lily - Clear, articulate

# Male Voices (expert host role)
VOICE_ERIC = "cjVigY5qzO86Huf0OWal"     # Eric - Smooth tenor, conversational (RECOMMENDED)
VOICE_CHRIS = "iP95p4xoKVk53GoZ742B"    # Chris - Natural, down-to-earth
VOICE_BRIAN = "nPczCjzI2devNBz1zQrb"    # Brian - Resonant, authoritative narrator

# Default voices (Sarah + Eric are recommended)
DEFAULT_FEMALE_VOICE = VOICE_SARAH
DEFAULT_MALE_VOICE = VOICE_ERIC

# Voice catalog for UI selection
AVAILABLE_VOICES: Dict[str, List[Dict[str, str]]] = {
    "female": [
        {"id": VOICE_SARAH, "name": "Sarah", "description": "Suave e acolhedora"},
        {"id": VOICE_JESSICA, "name": "Jessica", "description": "Expressiva e animada"},
        {"id": VOICE_LILY, "name": "Lily", "description": "Clara e articulada"},
    ],
    "male": [
        {"id": VOICE_ERIC, "name": "Eric", "description": "Natural e conversacional"},
        {"id": VOICE_CHRIS, "name": "Chris", "description": "Descontraido e amigavel"},
        {"id": VOICE_BRIAN, "name": "Brian", "description": "Autoritativo e envolvente"},
    ],
}

# =============================================================================
# Model Configuration
# =============================================================================

# Eleven v3 - Latest model with audio tags support
# Supports: [laughs], [whispers], [sighs], [curious], [excited], etc.
MODEL_ID = "eleven_v3"

# Fallback model if v3 is unavailable
MODEL_ID_FALLBACK = "eleven_multilingual_v2"

# Output format: MP3 at 44.1kHz, 128kbps (high quality)
OUTPUT_FORMAT = "mp3_44100_128"

# Text limits
MAX_TEXT_LENGTH = 5000  # ElevenLabs limit per segment
MAX_TOTAL_LENGTH = 50000  # Total dialogue limit

# =============================================================================
# Text Validation
# =============================================================================


def validate_text(text: str) -> str:
    """
    Validate and clean text before TTS.

    Args:
        text: Text to validate

    Returns:
        Cleaned text

    Raises:
        ValueError: If text is empty or exceeds limits
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    cleaned = text.strip()

    if len(cleaned) > MAX_TEXT_LENGTH:
        raise ValueError(f"Text exceeds {MAX_TEXT_LENGTH} characters (got {len(cleaned)})")

    return cleaned


def validate_segments(segments: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Validate dialogue segments before TTS.

    Args:
        segments: List of {speaker, text} dicts

    Returns:
        Validated segments

    Raises:
        ValueError: If segments are invalid
    """
    if not segments:
        raise ValueError("No dialogue segments provided")

    total_length = 0
    validated = []

    for i, segment in enumerate(segments):
        if "text" not in segment or "speaker" not in segment:
            raise ValueError(f"Segment {i} missing 'text' or 'speaker' field")

        text = validate_text(segment["text"])
        total_length += len(text)

        if total_length > MAX_TOTAL_LENGTH:
            raise ValueError(f"Total dialogue exceeds {MAX_TOTAL_LENGTH} characters")

        validated.append({
            "speaker": segment["speaker"],
            "text": text,
        })

    return validated


# =============================================================================
# ElevenLabs Client
# =============================================================================


def get_client() -> ElevenLabs:
    """
    Get configured ElevenLabs client.

    Returns:
        ElevenLabs client instance

    Raises:
        ValueError: If API key not configured
    """
    if not ELEVENLABS_API_KEY:
        raise ValueError("ELEVENLABS_API_KEY environment variable not set")

    return ElevenLabs(api_key=ELEVENLABS_API_KEY)


# =============================================================================
# Text-to-Dialogue API (RECOMMENDED)
# =============================================================================


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    reraise=True,
)
def text_to_dialogue(
    segments: List[Dict[str, str]],
    female_voice_id: str = DEFAULT_FEMALE_VOICE,
    male_voice_id: str = DEFAULT_MALE_VOICE,
    model_id: str = MODEL_ID,
    female_name: str = "Sarah",
    male_name: str = "Eric",
) -> bytes:
    """
    Convert dialogue segments to speech using Text-to-Dialogue API.

    This is the RECOMMENDED approach for multi-speaker content.
    Uses native multi-speaker support for seamless transitions.

    Args:
        segments: List of {speaker, text} dicts where speaker is "female", "male",
                  or a host name (e.g., "Sarah", "Eric")
        female_voice_id: Voice ID for female host
        male_voice_id: Voice ID for male host
        model_id: TTS model to use (default: eleven_v3)
        female_name: Name of female host (e.g., "Sarah", "Jessica", "Lily")
        male_name: Name of male host (e.g., "Eric", "Chris", "Brian")

    Returns:
        Audio bytes (MP3 format)

    Raises:
        ValueError: If API key not configured or segments invalid
        BadRequestError: If ElevenLabs rejects the request
        NotFoundError: If voice not found
        UnauthorizedError: If API key invalid
    """
    # Validate segments
    validated_segments = validate_segments(segments)

    # Log for debugging speaker mapping
    print(f"[ElevenLabs] text_to_dialogue called with female_name='{female_name}', male_name='{male_name}'")
    print(f"[ElevenLabs] Segment speakers: {[s['speaker'] for s in validated_segments]}")

    # Get client
    client = get_client()

    # Build dialogue inputs with flexible speaker mapping
    inputs = []
    for segment in validated_segments:
        speaker = segment["speaker"].lower()
        # Map speaker to voice: "female" or actual female name -> female voice
        # "male" or actual male name -> male voice
        if speaker in ("female", female_name.lower()):
            voice_id = female_voice_id
        else:
            voice_id = male_voice_id
        inputs.append(DialogueInput(
            text=segment["text"],
            voice_id=voice_id,
        ))

    try:
        # Use Text-to-Dialogue API (native multi-speaker)
        print(f"[ElevenLabs] Calling API with model_id={model_id}, format={OUTPUT_FORMAT}")
        print(f"[ElevenLabs] Total inputs: {len(inputs)}, total chars: {sum(len(i.text) for i in inputs)}")

        audio = client.text_to_dialogue.convert(
            inputs=inputs,
            model_id=model_id,
            output_format=OUTPUT_FORMAT,
        )

        # Convert generator/iterator to bytes
        # The SDK returns a streaming response that needs to be consumed
        if isinstance(audio, bytes):
            print(f"[ElevenLabs] Direct bytes: {len(audio)} bytes")
            return audio
        elif hasattr(audio, 'read'):
            # File-like object
            audio_bytes = audio.read()
            print(f"[ElevenLabs] File-like consumed: {len(audio_bytes)} bytes")
            return audio_bytes
        elif hasattr(audio, '__iter__'):
            # Generator/iterator - consume all chunks
            chunks = []
            for chunk in audio:
                if chunk:
                    chunks.append(chunk)
            audio_bytes = b''.join(chunks)
            print(f"[ElevenLabs] Generator consumed: {len(audio_bytes)} bytes from {len(chunks)} chunks")
            return audio_bytes
        else:
            # Unknown type - try to convert
            audio_bytes = bytes(audio) if audio else b''
            print(f"[ElevenLabs] Unknown type {type(audio)}, converted: {len(audio_bytes)} bytes")
            return audio_bytes

    except BadRequestError as e:
        # Log detailed error for debugging
        print(f"ElevenLabs BadRequestError: {e}")

        # Try fallback model if v3 fails
        if model_id == MODEL_ID:
            print(f"Retrying with fallback model: {MODEL_ID_FALLBACK}")
            return text_to_dialogue(
                segments=segments,
                female_voice_id=female_voice_id,
                male_voice_id=male_voice_id,
                model_id=MODEL_ID_FALLBACK,
            )
        raise ValueError(f"ElevenLabs rejected request: {e}")

    except NotFoundError as e:
        raise ValueError(f"Voice not found: {e}")

    except UnauthorizedError as e:
        raise ValueError(f"Invalid API key: {e}")


# =============================================================================
# Text-to-Speech API (Single Speaker - Legacy)
# =============================================================================


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    reraise=True,
)
def text_to_speech(
    text: str,
    voice_id: str = DEFAULT_FEMALE_VOICE,
    model_id: str = MODEL_ID,
    is_female: bool = True,
) -> bytes:
    """
    Convert text to speech using single-speaker TTS API.

    DEPRECATED: Use text_to_dialogue() for multi-speaker content.
    This function is kept for backward compatibility.

    Args:
        text: Text to convert to speech
        voice_id: ElevenLabs voice ID
        model_id: TTS model to use
        is_female: Unused (kept for backward compatibility)

    Returns:
        Audio bytes (MP3 format)

    Raises:
        ValueError: If API key not configured or text invalid
        BadRequestError: If ElevenLabs rejects the request
    """
    # Validate text
    validated_text = validate_text(text)

    # Get client
    client = get_client()

    try:
        audio = client.text_to_speech.convert(
            text=validated_text,
            voice_id=voice_id,
            model_id=model_id,
            output_format=OUTPUT_FORMAT,
        )

        # Convert generator to bytes if needed
        if hasattr(audio, '__iter__') and not isinstance(audio, bytes):
            return b''.join(audio)
        return audio

    except BadRequestError as e:
        print(f"ElevenLabs BadRequestError: {e}")

        # Try fallback model
        if model_id == MODEL_ID:
            print(f"Retrying with fallback model: {MODEL_ID_FALLBACK}")
            return text_to_speech(
                text=text,
                voice_id=voice_id,
                model_id=MODEL_ID_FALLBACK,
                is_female=is_female,
            )
        raise ValueError(f"ElevenLabs rejected request: {e}")

    except NotFoundError as e:
        raise ValueError(f"Voice not found: {e}")

    except UnauthorizedError as e:
        raise ValueError(f"Invalid API key: {e}")


# =============================================================================
# Utility Functions
# =============================================================================


def get_available_voices() -> Dict[str, List[Dict[str, str]]]:
    """
    Return catalog of available voices for UI selection.

    Returns:
        Dict with 'female' and 'male' lists of voice options
    """
    return AVAILABLE_VOICES


def get_default_voices() -> Dict[str, str]:
    """
    Return default voice IDs (Sarah for female, Eric for male).

    Returns:
        Dict with 'female' and 'male' default voice IDs
    """
    return {
        "female": DEFAULT_FEMALE_VOICE,
        "male": DEFAULT_MALE_VOICE,
    }


def is_valid_voice_id(voice_id: str) -> bool:
    """
    Check if a voice ID is valid (exists in available voices).

    Args:
        voice_id: Voice ID to validate

    Returns:
        True if valid, False otherwise
    """
    all_voice_ids = [v["id"] for v in AVAILABLE_VOICES["female"]] + \
                    [v["id"] for v in AVAILABLE_VOICES["male"]]
    return voice_id in all_voice_ids


# =============================================================================
# Audio Tags Reference (Eleven v3)
# =============================================================================
#
# Eleven v3 supports audio tags for emotional expression:
#
# Laughter:
#   [laughs], [laughs harder], [giggling], [wheezing]
#
# Whispers/Breaths:
#   [whispers], [sighs], [exhales], [snorts]
#
# Emotions:
#   [curious], [excited], [sarcastic], [crying], [mischievously]
#   [impressed], [amazed], [delighted], [warmly], [dramatically]
#
# Sound Effects:
#   [applause], [clapping], [gunshot], [explosion]
#
# Performance:
#   [sings], [woo]
#
# Example usage in script:
#   Sarah: [curious] Que interessante! Pode explicar melhor?
#   Eric: [laughs] Claro! [warmly] Deixa eu te mostrar...
#
# Note: Tag effectiveness depends on voice characteristics.
# Use "Creative" or "Natural" stability for best emotional expression.
# =============================================================================
