# =============================================================================
# HeyGen Video Generation Tool
# =============================================================================
# Video generation integration using HeyGen API for creating personalized
# avatar-based educational videos.
#
# API Documentation: https://docs.heygen.com/reference/generate-video
#
# Features:
# - Create videos with custom Sasha avatar
# - Poll for video completion status
# - Brazilian Portuguese TTS voice
#
# Configuration:
# - HEYGEN_API_KEY: API key (from GitHub secrets)
# - SASHA_AVATAR_ID: Custom avatar ID for Sasha tutor
# =============================================================================

import os
import random
import time
import httpx
from typing import Dict, Any, Optional, List, Callable
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

# =============================================================================
# Configuration
# =============================================================================

HEYGEN_API_KEY = os.getenv("HEYGEN_API_KEY", "")

# HeyGen API endpoints
HEYGEN_BASE_URL = "https://api.heygen.com"
HEYGEN_VIDEO_GENERATE_URL = f"{HEYGEN_BASE_URL}/v2/video/generate"
HEYGEN_VIDEO_STATUS_URL = f"{HEYGEN_BASE_URL}/v1/video_status.get"

# V2 Avatar configurations - random selection for variety
# Curated list of professional female avatars for educational content
# Updated: December 2025
V2_AVATAR_IDS = [
    # Abigail
    "Abigail_standing_office_front",
    "Abigail_sitting_sofa_front",
    # Aiko
    "Aiko_public",
    # Amelia
    "Amelia_standing_business_training_front",
    "Amelia_sitting_business_training_front",
    "Amelia_sitting_business_training_side",
    # Anja
    "Anja_sitting_sofa_front",
    "Anja_standing_office_front",
    # Gala
    "Gala_sitting_office_front",
    "Gala_sitting_businesssofa_front",
    "Gala_standing_businesssofa_front_close",
    "Gala_standing_businesssofa_front",
    "Gala_sitting_sofa_front_close",
    "Gala_sitting_sofa_front",
    "Gala_sitting_casualsofawithipad_front",
    # UUID-based avatars
    "5be36aa9d66a485d9b103bc9efef45f2",
    "1820b20bc8f04366bb4e15d2edb52cdf",
    "bd0a0b1b6ffd4e64bb1e145ecf71c072",
    "02ec2f2552e845719740af795ddbfddf",
    "958d04cf00194866b28838d7e1242a79",
    # Anna
    "Anna_public_3_20240108",
    # Annelise
    "Annelise_public_2",
    "Annelise_public_1",
    "Annelise_public_4",
    # Annie
    "Annie_Desk_Sitting_Front_public",
    "Annie_Casual_Standing_Front_2_public",
    "Annie_Office_Standing_Front_public",
    # Aubrey
    "Aubrey_standing_night_scene_front",
    "Aubrey_sitting_sofa_front",
    # Bahar
    "Bahar_Casual_Sitting_Front_public",
    "Bahar_Suit_Front_public",
    "Bahar_Jacket_Casual_Front_public",
    # Blanka
    "Blanka_sitting_lounge_front",
    "Blanka_sitting_picnic_front",
    # Carlotta
    "Carlotta_Pink_Jumpsuit_Sitting_Front_public",
    "Carlotta_Half_Front_public",
    "Carlotta_Pink_Jumpsuit_Side_2_public",
    # Caroline
    "Caroline_Casual_Sitting_Front_public",
    "Caroline_Lobby_Sitting_Front_public",
    "Caroline_Sofa_Sitting_Front_public",
    "Caroline_Office_Sitting_Front_public",
]

# Legacy alias for backward compatibility
GALA_AVATAR_IDS = V2_AVATAR_IDS

# Default avatar (first one) and style
SASHA_AVATAR_ID = V2_AVATAR_IDS[0]  # Default fallback
SASHA_AVATAR_STYLE = "normal"

# Brazilian Portuguese TTS voice (HeyGen native voices)
# Verified via: curl https://api.heygen.com/v2/voices
PORTUGUESE_VOICES = [
    # Original voices
    "94ec497104a04c87904a8aa138d6e46c",  # Sofia Brazil (female)
    "0edbc867be6f48c5be8ff8b0fbca0802",  # Sofia Brazil - Friendly 😊 (female)
    "0d23c5b2f6004e909802a2e8bfcd52c2",  # Ana Carvalho (female)
    "4bd875d510f5461a9e228e1cbde2d545",  # Camila - Friendly (female)
    "e4dcfd51f07d4b93a0468a48a782b50e",  # Francisca - Cheerful (female)
    # Additional PT-BR voices (December 2025)
    "6d282a9f296746568da9d65586935dba",
    "6c0a95599317428a8151293305deceba",
    "ab40d65529a74f0e83528a1c2133a3b0",
    "2799eccbd72d48e0af3202a147d51146",
    "2f296fed147e4194aa07a425df87d7e7",
    "3f3e7753a09146048e0f65e9510d852f",
    "9f2ea3bb9ccb4f129d7685505df5fbc4",
]
SASHA_VOICE_ID = PORTUGUESE_VOICES[0]  # Sofia Brazil as default


def get_random_avatar_id() -> str:
    """
    Get a random Gala avatar ID for variety in videos.

    Returns:
        Random avatar ID from GALA_AVATAR_IDS
    """
    return random.choice(GALA_AVATAR_IDS)


def get_random_voice_id() -> str:
    """
    Get a random Portuguese voice ID for variety in videos.

    Returns:
        Random voice ID from PORTUGUESE_VOICES
    """
    return random.choice(PORTUGUESE_VOICES)

# Video settings
DEFAULT_VIDEO_WIDTH = 1280
DEFAULT_VIDEO_HEIGHT = 720
DEFAULT_BACKGROUND_COLOR = "#1E3A5F"  # Navy blue (matching Hive Academy theme)

# Timeouts
REQUEST_TIMEOUT = 60  # seconds


# =============================================================================
# HeyGen API Client
# =============================================================================


def get_headers() -> Dict[str, str]:
    """
    Get HTTP headers for HeyGen API requests.

    Returns:
        Headers dict with API key

    Raises:
        ValueError: If API key not configured
    """
    if not HEYGEN_API_KEY:
        raise ValueError("HEYGEN_API_KEY environment variable not set")

    return {
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# =============================================================================
# Video Generation
# =============================================================================


# Maximum avatar retry attempts
MAX_AVATAR_RETRIES = 5

# User-friendly error messages (Portuguese)
USER_FRIENDLY_ERRORS = {
    "avatar_not_found": "Ocorreu um problema técnico. Tentando novamente...",
    "voice_not_found": "Voz temporariamente indisponível. Tentando alternativa...",
    "quota_exceeded": "Limite de geração de vídeos atingido. Tente novamente mais tarde.",
    "rate_limit": "Muitas requisições. Aguarde um momento e tente novamente.",
    "timeout": "O servidor demorou para responder. Tente novamente.",
    "generic": "Erro ao gerar vídeo. Por favor, tente novamente.",
}


def _is_retryable_error(error_data: dict) -> bool:
    """
    Check if the error is retryable with a different avatar.

    Args:
        error_data: Error response from HeyGen API

    Returns:
        True if we should try another avatar
    """
    error_code = error_data.get("code", "")
    error_message = str(error_data.get("message", "")).lower()

    retryable_codes = ["avatar_not_found", "avatar_unavailable", "invalid_avatar"]
    retryable_messages = ["avatar", "not found", "no longer available", "unavailable"]

    if error_code in retryable_codes:
        return True

    for msg in retryable_messages:
        if msg in error_message:
            return True

    return False


def _sanitize_error_for_user(error_data: dict, status_code: int = 500) -> str:
    """
    Convert technical error to user-friendly message.

    Args:
        error_data: Error response from HeyGen API
        status_code: HTTP status code

    Returns:
        User-friendly error message in Portuguese
    """
    error_code = error_data.get("code", "")

    # Map known error codes to user-friendly messages
    if error_code in USER_FRIENDLY_ERRORS:
        return USER_FRIENDLY_ERRORS[error_code]

    # Check for rate limiting
    if status_code == 429 or "rate" in str(error_data).lower():
        return USER_FRIENDLY_ERRORS["rate_limit"]

    # Check for quota errors
    if "quota" in str(error_data).lower() or "limit" in str(error_data).lower():
        return USER_FRIENDLY_ERRORS["quota_exceeded"]

    # Generic error
    return USER_FRIENDLY_ERRORS["generic"]


def _create_video_single_attempt(
    script: str,
    title: str,
    avatar_id: str,
    avatar_style: str,
    voice_id: str,
    width: int,
    height: int,
    background_color: str,
) -> tuple[Optional[str], Optional[dict], Optional[int]]:
    """
    Single attempt to create video with specified avatar.

    Returns:
        Tuple of (video_id, error_data, status_code)
        - On success: (video_id, None, None)
        - On error: (None, error_data, status_code)
    """
    headers = get_headers()

    payload = {
        "title": title,
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id,
                    "avatar_style": avatar_style,
                },
                "voice": {
                    "type": "text",
                    "input_text": script,
                    "voice_id": voice_id,
                },
                "background": {
                    "type": "color",
                    "value": background_color,
                },
            }
        ],
        "dimension": {
            "width": width,
            "height": height,
        },
    }

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.post(
                HEYGEN_VIDEO_GENERATE_URL,
                headers=headers,
                json=payload,
            )

            data = response.json()

            # Success
            if response.status_code == 200 and "data" in data and "video_id" in data["data"]:
                return data["data"]["video_id"], None, None

            # Error response
            error_data = data.get("error", data)
            if isinstance(error_data, str):
                error_data = {"message": error_data}

            return None, error_data, response.status_code

    except httpx.TimeoutException:
        return None, {"code": "timeout", "message": "Request timeout"}, 408

    except Exception as e:
        return None, {"code": "unknown", "message": str(e)}, 500


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
    reraise=True,
)
def create_video(
    script: str,
    title: str,
    avatar_id: Optional[str] = None,  # None = random selection with fallback
    avatar_style: str = SASHA_AVATAR_STYLE,
    voice_id: str = SASHA_VOICE_ID,
    width: int = DEFAULT_VIDEO_WIDTH,
    height: int = DEFAULT_VIDEO_HEIGHT,
    background_color: str = DEFAULT_BACKGROUND_COLOR,
) -> str:
    """
    Create a video using HeyGen API with automatic avatar fallback.

    If the selected avatar fails (e.g., avatar_not_found), automatically
    tries other avatars from the pool before failing.

    Args:
        script: The text script for the avatar to speak
        title: Title for the video
        avatar_id: HeyGen avatar ID (None = random with fallback)
        avatar_style: Avatar style (normal, circle, etc.)
        voice_id: TTS voice ID (default: Brazilian Portuguese)
        width: Video width in pixels
        height: Video height in pixels
        background_color: Background color hex code

    Returns:
        video_id: Unique identifier for the video

    Raises:
        ValueError: If all avatars fail or non-retryable error occurs
    """
    if not HEYGEN_API_KEY:
        raise ValueError("HEYGEN_API_KEY environment variable not set")

    # Create a shuffled list of avatars to try
    available_avatars = V2_AVATAR_IDS.copy()
    random.shuffle(available_avatars)

    # If a specific avatar was requested, try it first
    if avatar_id is not None:
        if avatar_id in available_avatars:
            available_avatars.remove(avatar_id)
        available_avatars.insert(0, avatar_id)

    tried_avatars: list[str] = []
    last_error_data: Optional[dict] = None
    last_status_code: int = 500

    print(f"[HeyGen] Creating video: {title[:50]}...")
    print(f"[HeyGen] Script length: {len(script)} characters")

    for attempt, current_avatar in enumerate(available_avatars[:MAX_AVATAR_RETRIES]):
        tried_avatars.append(current_avatar)
        print(f"[HeyGen] Attempt {attempt + 1}/{MAX_AVATAR_RETRIES}: Trying avatar {current_avatar}")

        video_id, error_data, status_code = _create_video_single_attempt(
            script=script,
            title=title,
            avatar_id=current_avatar,
            avatar_style=avatar_style,
            voice_id=voice_id,
            width=width,
            height=height,
            background_color=background_color,
        )

        # Success!
        if video_id:
            print(f"[HeyGen] Video created successfully: {video_id}")
            if attempt > 0:
                print(f"[HeyGen] Success after {attempt + 1} attempts (failed avatars: {tried_avatars[:-1]})")
            return video_id

        # Store error for potential final failure
        last_error_data = error_data or {}
        last_status_code = status_code or 500

        # Log the error (technical details stay in logs, not UI)
        print(f"[HeyGen] Avatar {current_avatar} failed: {last_error_data}")

        # Check if this error is retryable with a different avatar
        if not _is_retryable_error(last_error_data):
            # Non-retryable error (quota, rate limit, etc.) - fail immediately
            user_message = _sanitize_error_for_user(last_error_data, last_status_code)
            print(f"[HeyGen] Non-retryable error, stopping: {user_message}")
            raise ValueError(user_message)

        # Continue to next avatar
        print(f"[HeyGen] Retryable error, trying next avatar...")

    # All avatars failed
    print(f"[HeyGen] All {len(tried_avatars)} avatars failed. Last error: {last_error_data}")
    user_message = _sanitize_error_for_user(last_error_data or {}, last_status_code)
    raise ValueError(user_message)


# =============================================================================
# Video Status
# =============================================================================


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((httpx.ConnectError, httpx.TimeoutException)),
    reraise=True,
)
def get_video_status(video_id: str) -> Dict[str, Any]:
    """
    Get the status of a video being generated.

    Args:
        video_id: The video ID returned from create_video()

    Returns:
        Dict with status information:
        - status: "waiting" | "pending" | "processing" | "completed" | "failed"
        - video_url: URL to download video (when completed)
        - thumbnail_url: URL to video thumbnail (when completed)
        - duration: Video duration in seconds (when completed)
        - error: Error message (when failed)

    Raises:
        ValueError: If API key not configured
        httpx.HTTPStatusError: If API returns error status
    """
    headers = get_headers()

    try:
        with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
            response = client.get(
                HEYGEN_VIDEO_STATUS_URL,
                headers=headers,
                params={"video_id": video_id},
            )

            response.raise_for_status()

            data = response.json()

            # HeyGen returns: {"data": {"status": "...", "video_url": "...", ...}}
            if "data" not in data:
                raise ValueError("Invalid response from HeyGen API")

            video_data = data["data"]
            status = video_data.get("status", "unknown")

            result = {
                "status": status,
                "video_id": video_id,
            }

            # Add video URL when completed
            if status == "completed":
                result["video_url"] = video_data.get("video_url")
                result["thumbnail_url"] = video_data.get("thumbnail_url")
                result["duration"] = video_data.get("duration")
                print(f"[HeyGen] Video completed: {result['video_url']}")

            # Add error when failed
            elif status == "failed":
                result["error"] = video_data.get("error", "Video generation failed")
                print(f"[HeyGen] Video failed: {result['error']}")

            else:
                print(f"[HeyGen] Video status: {status}")

            return result

    except httpx.HTTPStatusError as e:
        try:
            error_data = e.response.json()
            error_msg = error_data.get("error", error_data.get("message", str(e)))
        except Exception:
            error_msg = str(e)

        print(f"[HeyGen] Status check error: {error_msg}")
        raise ValueError(f"HeyGen API error ({e.response.status_code}): {error_msg}")


# =============================================================================
# Utility Functions
# =============================================================================


def validate_script(script: str, min_length: int = 50, max_length: int = 5000) -> str:
    """
    Validate and clean video script.

    Args:
        script: Script text to validate
        min_length: Minimum script length
        max_length: Maximum script length

    Returns:
        Cleaned script

    Raises:
        ValueError: If script is invalid
    """
    if not script or not script.strip():
        raise ValueError("Script cannot be empty")

    cleaned = script.strip()

    if len(cleaned) < min_length:
        raise ValueError(f"Script too short (minimum {min_length} characters)")

    if len(cleaned) > max_length:
        raise ValueError(f"Script too long (maximum {max_length} characters)")

    return cleaned


def estimate_video_duration(script: str, words_per_minute: int = 150) -> float:
    """
    Estimate video duration based on script length.

    Args:
        script: Video script text
        words_per_minute: Speaking rate (default: 150 WPM)

    Returns:
        Estimated duration in seconds
    """
    word_count = len(script.split())
    minutes = word_count / words_per_minute
    return minutes * 60


def is_video_ready(status: str) -> bool:
    """
    Check if video status indicates completion.

    Args:
        status: Status string from get_video_status()

    Returns:
        True if video is ready to download
    """
    return status == "completed"


def is_video_processing(status: str) -> bool:
    """
    Check if video is still being processed.

    Args:
        status: Status string from get_video_status()

    Returns:
        True if video is still processing
    """
    return status in ("waiting", "pending", "processing")


def is_video_failed(status: str) -> bool:
    """
    Check if video generation failed.

    Args:
        status: Status string from get_video_status()

    Returns:
        True if video generation failed
    """
    return status == "failed"


# =============================================================================
# Async Polling
# =============================================================================


def poll_until_complete(
    video_id: str,
    timeout_seconds: int = 600,  # 10 minutes max
    poll_interval_seconds: int = 10,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """
    Poll video status until completion, failure, or timeout.

    This function provides robust polling with:
    - Configurable timeout (default: 10 minutes)
    - Progressive polling intervals
    - Optional progress callback for real-time updates
    - Automatic retry on transient failures

    Args:
        video_id: HeyGen video ID from create_video()
        timeout_seconds: Maximum time to wait (default: 600s / 10 min)
        poll_interval_seconds: Initial polling interval (increases over time)
        on_progress: Optional callback function(status_dict) for progress updates

    Returns:
        Dict with final status:
        - status: "completed" | "failed" | "timeout"
        - video_url: URL when completed
        - thumbnail_url: Thumbnail URL when completed
        - duration: Video duration when completed
        - error: Error message when failed or timeout
        - elapsed_seconds: Total time waited
        - poll_count: Number of status checks made

    Example:
        >>> result = poll_until_complete("video123", timeout_seconds=300)
        >>> if result["status"] == "completed":
        ...     print(f"Video ready: {result['video_url']}")
    """
    start_time = time.time()
    poll_count = 0
    current_interval = poll_interval_seconds

    print(f"[HeyGen] Starting poll for video {video_id} (timeout: {timeout_seconds}s)")

    while True:
        elapsed = time.time() - start_time
        poll_count += 1

        # Check timeout
        if elapsed >= timeout_seconds:
            result = {
                "status": "timeout",
                "video_id": video_id,
                "error": f"Polling timed out after {timeout_seconds} seconds",
                "elapsed_seconds": int(elapsed),
                "poll_count": poll_count,
            }
            print(f"[HeyGen] Poll timeout: {timeout_seconds}s exceeded")
            return result

        # Get status
        try:
            status_result = get_video_status(video_id)
            status = status_result.get("status", "unknown")

            # Add metadata
            status_result["elapsed_seconds"] = int(elapsed)
            status_result["poll_count"] = poll_count

            # Call progress callback if provided
            if on_progress:
                try:
                    on_progress(status_result)
                except Exception as e:
                    print(f"[HeyGen] Progress callback error: {e}")

            # Check if done
            if is_video_ready(status):
                print(f"[HeyGen] Video completed after {int(elapsed)}s ({poll_count} polls)")
                return status_result

            if is_video_failed(status):
                print(f"[HeyGen] Video failed after {int(elapsed)}s: {status_result.get('error')}")
                return status_result

            # Still processing - log and continue
            print(f"[HeyGen] Poll #{poll_count}: {status} (elapsed: {int(elapsed)}s)")

        except ValueError as e:
            # API error - log but continue polling
            print(f"[HeyGen] Poll #{poll_count} error: {e}")
            # Continue polling unless we've hit too many consecutive errors

        except Exception as e:
            # Unexpected error - log and continue
            print(f"[HeyGen] Poll #{poll_count} unexpected error: {e}")

        # Wait before next poll
        # Progressive backoff: increase interval by 50% each time, max 30s
        time.sleep(current_interval)
        current_interval = min(current_interval * 1.5, 30)


async def poll_until_complete_async(
    video_id: str,
    timeout_seconds: int = 600,
    poll_interval_seconds: int = 10,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """
    Async version of poll_until_complete for use in async contexts.

    Same functionality as poll_until_complete but uses asyncio.sleep
    instead of time.sleep for non-blocking operation.

    Args:
        video_id: HeyGen video ID from create_video()
        timeout_seconds: Maximum time to wait (default: 600s / 10 min)
        poll_interval_seconds: Initial polling interval
        on_progress: Optional async callback for progress updates

    Returns:
        Dict with final status (same as poll_until_complete)
    """
    import asyncio

    start_time = time.time()
    poll_count = 0
    current_interval = poll_interval_seconds

    print(f"[HeyGen] Starting async poll for video {video_id} (timeout: {timeout_seconds}s)")

    while True:
        elapsed = time.time() - start_time
        poll_count += 1

        # Check timeout
        if elapsed >= timeout_seconds:
            result = {
                "status": "timeout",
                "video_id": video_id,
                "error": f"Polling timed out after {timeout_seconds} seconds",
                "elapsed_seconds": int(elapsed),
                "poll_count": poll_count,
            }
            print(f"[HeyGen] Async poll timeout: {timeout_seconds}s exceeded")
            return result

        # Get status (sync call, but quick)
        try:
            status_result = get_video_status(video_id)
            status = status_result.get("status", "unknown")

            # Add metadata
            status_result["elapsed_seconds"] = int(elapsed)
            status_result["poll_count"] = poll_count

            # Call progress callback if provided
            if on_progress:
                try:
                    if asyncio.iscoroutinefunction(on_progress):
                        await on_progress(status_result)
                    else:
                        on_progress(status_result)
                except Exception as e:
                    print(f"[HeyGen] Progress callback error: {e}")

            # Check if done
            if is_video_ready(status):
                print(f"[HeyGen] Video completed after {int(elapsed)}s ({poll_count} polls)")
                return status_result

            if is_video_failed(status):
                print(f"[HeyGen] Video failed after {int(elapsed)}s: {status_result.get('error')}")
                return status_result

            # Still processing - log and continue
            print(f"[HeyGen] Async poll #{poll_count}: {status} (elapsed: {int(elapsed)}s)")

        except ValueError as e:
            print(f"[HeyGen] Async poll #{poll_count} error: {e}")

        except Exception as e:
            print(f"[HeyGen] Async poll #{poll_count} unexpected error: {e}")

        # Wait before next poll (non-blocking)
        await asyncio.sleep(current_interval)
        current_interval = min(current_interval * 1.5, 30)


def create_video_and_wait(
    script: str,
    title: str,
    avatar_id: Optional[str] = None,
    avatar_style: str = SASHA_AVATAR_STYLE,
    voice_id: str = SASHA_VOICE_ID,
    width: int = DEFAULT_VIDEO_WIDTH,
    height: int = DEFAULT_VIDEO_HEIGHT,
    background_color: str = DEFAULT_BACKGROUND_COLOR,
    timeout_seconds: int = 600,
    on_progress: Optional[Callable[[Dict[str, Any]], None]] = None,
) -> Dict[str, Any]:
    """
    Create a video and wait for completion in one call.

    This is a convenience function that combines create_video() and
    poll_until_complete() for simple use cases.

    Args:
        script: The text script for the avatar to speak
        title: Title for the video
        avatar_id: HeyGen avatar ID (None = random Gala avatar)
        avatar_style: Avatar style (normal, circle, etc.)
        voice_id: TTS voice ID (default: Brazilian Portuguese Sofia)
        width: Video width in pixels
        height: Video height in pixels
        background_color: Background color hex code
        timeout_seconds: Maximum time to wait for completion
        on_progress: Optional callback for progress updates

    Returns:
        Dict with:
        - status: "completed" | "failed" | "timeout" | "error"
        - video_id: The created video ID
        - video_url: URL when completed
        - error: Error message if any

    Example:
        >>> result = create_video_and_wait(
        ...     script="Olá! Bem-vindo à aula...",
        ...     title="Introdução ao Curso",
        ...     timeout_seconds=300,
        ... )
        >>> if result["status"] == "completed":
        ...     print(f"Video URL: {result['video_url']}")
    """
    try:
        # Create the video
        video_id = create_video(
            script=script,
            title=title,
            avatar_id=avatar_id,
            avatar_style=avatar_style,
            voice_id=voice_id,
            width=width,
            height=height,
            background_color=background_color,
        )

        # Poll until complete
        result = poll_until_complete(
            video_id=video_id,
            timeout_seconds=timeout_seconds,
            on_progress=on_progress,
        )

        return result

    except ValueError as e:
        return {
            "status": "error",
            "error": str(e),
        }


# =============================================================================
# Configuration Check
# =============================================================================


def check_configuration() -> Dict[str, Any]:
    """
    Check HeyGen configuration status.

    Returns:
        Dict with configuration status
    """
    return {
        "api_key_configured": bool(HEYGEN_API_KEY),
        "avatar_ids": GALA_AVATAR_IDS,
        "avatar_count": len(GALA_AVATAR_IDS),
        "voice_id": SASHA_VOICE_ID,
        "portuguese_voices": len(PORTUGUESE_VOICES),
        "default_dimensions": f"{DEFAULT_VIDEO_WIDTH}x{DEFAULT_VIDEO_HEIGHT}",
        "api_endpoint": HEYGEN_VIDEO_GENERATE_URL,
    }
