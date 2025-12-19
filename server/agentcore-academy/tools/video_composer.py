# =============================================================================
# Video Composer Tool - FFmpeg-based Video Generation
# =============================================================================
# Combines slide images and audio narration into a final MP4 video.
#
# Pipeline:
# 1. Receive list of slide images (PNG bytes) with durations
# 2. Receive audio narration (MP3 bytes) from ElevenLabs
# 3. Use FFmpeg to combine slides into video track
# 4. Overlay audio track
# 5. Output final MP4
#
# FFmpeg Strategy: Lambda Layer with static binary
# Layer ARN: Use public FFmpeg layer or custom layer
#
# Reference:
# - https://github.com/kkroening/ffmpeg-python
# - https://ffmpeg.org/documentation.html
# =============================================================================

import os
import tempfile
import subprocess
import uuid
from typing import List, Dict, Any, Optional, Tuple
from botocore.config import Config
import boto3

# =============================================================================
# Configuration
# =============================================================================

VIDEOS_BUCKET = os.getenv("VIDEOS_BUCKET", "hive-academy-videos-prod")
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")

# FFmpeg binary path (Lambda layer or local)
FFMPEG_PATH = os.getenv("FFMPEG_PATH", "/opt/bin/ffmpeg")
FFPROBE_PATH = os.getenv("FFPROBE_PATH", "/opt/bin/ffprobe")

# Fallback to system FFmpeg if Lambda layer not available
if not os.path.exists(FFMPEG_PATH):
    FFMPEG_PATH = "ffmpeg"
    FFPROBE_PATH = "ffprobe"

# S3 client config
S3_CONFIG = Config(
    signature_version="s3v4",
    s3={"addressing_style": "virtual"},
)

# Video settings
VIDEO_WIDTH = 1920
VIDEO_HEIGHT = 1080
VIDEO_FPS = 30
VIDEO_CODEC = "libx264"
VIDEO_PRESET = "medium"  # Balance between speed and quality
VIDEO_CRF = 23  # Quality (lower = better, 18-28 typical)
AUDIO_CODEC = "aac"
AUDIO_BITRATE = "192k"


# =============================================================================
# Utility Functions
# =============================================================================


def get_audio_duration(audio_path: str) -> float:
    """
    Get duration of an audio file using ffprobe.

    Args:
        audio_path: Path to audio file

    Returns:
        Duration in seconds
    """
    try:
        result = subprocess.run(
            [
                FFPROBE_PATH,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return float(result.stdout.strip())
    except Exception as e:
        print(f"[VideoComposer] Error getting audio duration: {e}")
        return 0.0


def write_temp_file(content: bytes, suffix: str) -> str:
    """
    Write bytes to a temporary file.

    Args:
        content: File content as bytes
        suffix: File extension (e.g., ".png", ".mp3")

    Returns:
        Path to temporary file
    """
    fd, path = tempfile.mkstemp(suffix=suffix)
    try:
        os.write(fd, content)
    finally:
        os.close(fd)
    return path


def cleanup_temp_files(paths: List[str]) -> None:
    """
    Remove temporary files.

    Args:
        paths: List of file paths to remove
    """
    for path in paths:
        try:
            if os.path.exists(path):
                os.unlink(path)
        except Exception as e:
            print(f"[VideoComposer] Warning: Failed to cleanup {path}: {e}")


# =============================================================================
# Video Composition
# =============================================================================


def compose_video_from_slides(
    slides: List[Dict[str, Any]],
    audio_bytes: bytes,
    output_path: Optional[str] = None,
) -> str:
    """
    Compose a video from slide images and audio using FFmpeg.

    Each slide dict should have:
    - image: PNG bytes
    - duration_seconds: How long to show this slide

    If durations aren't provided, they're calculated proportionally
    based on total audio duration.

    Args:
        slides: List of slide dicts with 'image' and 'duration_seconds'
        audio_bytes: MP3 audio as bytes
        output_path: Optional output path (creates temp file if not provided)

    Returns:
        Path to output MP4 file
    """
    if not slides:
        raise ValueError("No slides provided")

    if not audio_bytes:
        raise ValueError("No audio provided")

    temp_files = []
    concat_file_path = None

    try:
        # Write audio to temp file
        audio_path = write_temp_file(audio_bytes, ".mp3")
        temp_files.append(audio_path)

        # Get audio duration
        audio_duration = get_audio_duration(audio_path)
        print(f"[VideoComposer] Audio duration: {audio_duration:.2f}s")

        if audio_duration <= 0:
            raise ValueError("Could not determine audio duration")

        # Calculate slide durations if not provided
        total_specified_duration = sum(
            s.get("duration_seconds", 0) for s in slides
        )

        if total_specified_duration <= 0:
            # Distribute audio duration evenly across slides
            per_slide_duration = audio_duration / len(slides)
            for slide in slides:
                slide["duration_seconds"] = per_slide_duration
            print(f"[VideoComposer] Auto-calculated {per_slide_duration:.2f}s per slide")
        else:
            # Scale durations to match audio length
            scale_factor = audio_duration / total_specified_duration
            for slide in slides:
                slide["duration_seconds"] = slide.get("duration_seconds", 5) * scale_factor

        # Write slide images to temp files
        slide_paths = []
        for i, slide in enumerate(slides):
            image_bytes = slide.get("image")
            if not image_bytes:
                raise ValueError(f"Slide {i} has no image data")

            slide_path = write_temp_file(image_bytes, f"_{i:03d}.png")
            slide_paths.append(slide_path)
            temp_files.append(slide_path)

        print(f"[VideoComposer] Wrote {len(slide_paths)} slide images")

        # Create FFmpeg concat demuxer file
        # Format: file 'path'\nduration X\n
        concat_content = ""
        for i, (slide_path, slide) in enumerate(zip(slide_paths, slides)):
            duration = slide["duration_seconds"]
            concat_content += f"file '{slide_path}'\n"
            concat_content += f"duration {duration}\n"

        # Last file needs to be listed again without duration for concat
        if slide_paths:
            concat_content += f"file '{slide_paths[-1]}'\n"

        concat_file_path = write_temp_file(concat_content.encode(), ".txt")
        temp_files.append(concat_file_path)

        # Output path
        if not output_path:
            output_path = write_temp_file(b"", ".mp4")
            # Remove empty file so FFmpeg can create it
            os.unlink(output_path)

        # Build FFmpeg command
        # This uses the concat demuxer to combine images with specified durations
        # then overlays the audio track
        ffmpeg_cmd = [
            FFMPEG_PATH,
            "-y",  # Overwrite output
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file_path,  # Input: slide images via concat
            "-i", audio_path,  # Input: audio
            "-vf", f"scale={VIDEO_WIDTH}:{VIDEO_HEIGHT}:force_original_aspect_ratio=decrease,pad={VIDEO_WIDTH}:{VIDEO_HEIGHT}:(ow-iw)/2:(oh-ih)/2,fps={VIDEO_FPS}",
            "-c:v", VIDEO_CODEC,
            "-preset", VIDEO_PRESET,
            "-crf", str(VIDEO_CRF),
            "-c:a", AUDIO_CODEC,
            "-b:a", AUDIO_BITRATE,
            "-shortest",  # End when shortest stream ends
            "-pix_fmt", "yuv420p",  # Compatibility
            "-movflags", "+faststart",  # Web optimization
            output_path,
        ]

        print(f"[VideoComposer] Running FFmpeg...")
        print(f"[VideoComposer] Command: {' '.join(ffmpeg_cmd[:10])}...")

        # Run FFmpeg
        result = subprocess.run(
            ffmpeg_cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )

        if result.returncode != 0:
            print(f"[VideoComposer] FFmpeg error: {result.stderr}")
            raise RuntimeError(f"FFmpeg failed: {result.stderr[:500]}")

        print(f"[VideoComposer] Video created: {output_path}")

        # Verify output
        if not os.path.exists(output_path):
            raise RuntimeError("FFmpeg did not create output file")

        output_size = os.path.getsize(output_path)
        print(f"[VideoComposer] Output size: {output_size / 1024 / 1024:.2f} MB")

        return output_path

    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg timed out after 5 minutes")

    finally:
        # Cleanup temp files (except output)
        cleanup_temp_files([f for f in temp_files if f != output_path])


def compose_video_simple(
    slide_images: List[bytes],
    audio_bytes: bytes,
    slide_durations: Optional[List[float]] = None,
) -> bytes:
    """
    Simplified video composition - returns MP4 bytes directly.

    Args:
        slide_images: List of PNG images as bytes
        audio_bytes: MP3 audio as bytes
        slide_durations: Optional list of durations per slide

    Returns:
        MP4 video as bytes
    """
    # Build slides list
    slides = []
    for i, image in enumerate(slide_images):
        duration = slide_durations[i] if slide_durations and i < len(slide_durations) else 0
        slides.append({
            "image": image,
            "duration_seconds": duration,
        })

    # Compose video
    output_path = compose_video_from_slides(slides, audio_bytes)

    try:
        # Read output file
        with open(output_path, "rb") as f:
            video_bytes = f.read()

        return video_bytes

    finally:
        # Cleanup output file
        cleanup_temp_files([output_path])


# =============================================================================
# S3 Upload
# =============================================================================


def upload_video_to_s3(
    video_bytes: bytes,
    episode_id: str,
    bucket: str = VIDEOS_BUCKET,
) -> str:
    """
    Upload video to S3 and return presigned URL.

    Args:
        video_bytes: MP4 video content
        episode_id: Episode identifier for organizing
        bucket: S3 bucket name

    Returns:
        Presigned URL for video access (1 hour expiration)
    """
    s3_client = boto3.client(
        "s3",
        region_name=AWS_REGION,
        config=S3_CONFIG,
    )

    file_key = f"generated/{episode_id}/{uuid.uuid4()}.mp4"

    print(f"[VideoComposer] Uploading to S3: {bucket}/{file_key}")

    s3_client.put_object(
        Bucket=bucket,
        Key=file_key,
        Body=video_bytes,
        ContentType="video/mp4",
    )

    # Generate presigned URL
    video_url = s3_client.generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": file_key},
        ExpiresIn=3600,  # 1 hour
    )

    url_host = video_url.split("/")[2] if "/" in video_url else "unknown"
    is_regional = f".{AWS_REGION}." in url_host
    print(f"[VideoComposer] S3 URL: {url_host} (regional={is_regional})")

    return video_url


# =============================================================================
# Main Composition Function
# =============================================================================


async def create_video_from_slides_and_audio(
    slides: List[Dict[str, Any]],
    audio_bytes: bytes,
    episode_id: str,
) -> Dict[str, Any]:
    """
    Complete pipeline: compose video and upload to S3.

    Each slide dict should have:
    - image: PNG bytes from slide_renderer
    - duration_seconds: How long to show this slide
    - type: Slide type (title, bullets, etc.) - for metadata

    Args:
        slides: List of slide dicts with image bytes
        audio_bytes: MP3 audio from ElevenLabs
        episode_id: Episode identifier

    Returns:
        Dict with video_url, duration_seconds, metadata
    """
    try:
        print(f"[VideoComposer] Starting composition for episode {episode_id}")
        print(f"[VideoComposer] Slides: {len(slides)}, Audio: {len(audio_bytes)} bytes")

        # Compose video
        video_bytes = compose_video_simple(
            slide_images=[s["image"] for s in slides],
            audio_bytes=audio_bytes,
            slide_durations=[s.get("duration_seconds", 0) for s in slides],
        )

        print(f"[VideoComposer] Video composed: {len(video_bytes)} bytes")

        # Upload to S3
        video_url = upload_video_to_s3(video_bytes, episode_id)

        # Calculate total duration
        total_duration = sum(s.get("duration_seconds", 0) for s in slides)

        return {
            "video_url": video_url,
            "duration_seconds": total_duration,
            "slide_count": len(slides),
            "video_size_bytes": len(video_bytes),
            "success": True,
        }

    except Exception as e:
        print(f"[VideoComposer] Error: {str(e)}")
        import traceback
        traceback.print_exc()

        return {
            "error": str(e),
            "success": False,
        }


# =============================================================================
# Test Function
# =============================================================================


def test_composition():
    """
    Test video composition with sample data.

    This creates a simple test video locally without S3 upload.
    """
    from slide_renderer import render_title_slide, render_bullets_slide

    print("[VideoComposer] Running test composition...")

    # Generate test slides
    slides = [
        {
            "image": render_title_slide("Test Video", "Subtitle here"),
            "duration_seconds": 3,
        },
        {
            "image": render_bullets_slide(
                "Key Points",
                ["First point", "Second point", "Third point"]
            ),
            "duration_seconds": 5,
        },
    ]

    # For testing, we'd need actual audio
    # This is just a structure test
    print(f"[VideoComposer] Test slides generated: {len(slides)}")
    print("[VideoComposer] Test requires audio file for full composition")

    return slides


if __name__ == "__main__":
    test_composition()
