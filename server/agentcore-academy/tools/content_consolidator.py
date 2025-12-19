# =============================================================================
# Content Consolidator Tool - Multi-Source Text Unification
# =============================================================================
# Consolidates text content from multiple sources into a unified training
# document ready for AI processing.
#
# Features:
# - Merges text from documents, URLs, and YouTube transcripts
# - Removes duplicates and normalizes formatting
# - Generates metadata and statistics
# - Chunks content for large training sets
#
# Usage:
#   consolidated = consolidate_content(sources=[
#       {"type": "document", "text": "...", "filename": "report.pdf"},
#       {"type": "url", "text": "...", "url": "https://..."},
#       {"type": "youtube", "text": "...", "video_id": "abc123"},
#   ])
# =============================================================================

import re
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime

# =============================================================================
# Configuration
# =============================================================================

# Maximum consolidated text length (500K characters)
MAX_CONSOLIDATED_LENGTH = 500_000

# Minimum content length per source (characters)
MIN_SOURCE_LENGTH = 50

# Chunk size for very large content (100K characters)
CHUNK_SIZE = 100_000


# =============================================================================
# Text Normalization
# =============================================================================


def normalize_whitespace(text: str) -> str:
    """
    Normalize whitespace in text.

    - Converts multiple spaces to single space
    - Converts multiple newlines to double newline (paragraph)
    - Strips leading/trailing whitespace

    Args:
        text: Text to normalize

    Returns:
        Normalized text
    """
    # Replace tabs with spaces
    text = text.replace("\t", " ")

    # Normalize multiple spaces
    text = re.sub(r" {2,}", " ", text)

    # Normalize multiple newlines (max 2)
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Strip leading/trailing whitespace from lines
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)

    return text.strip()


def remove_common_artifacts(text: str) -> str:
    """
    Remove common extraction artifacts.

    - Cookie consent notices
    - Navigation breadcrumbs
    - Share buttons text
    - Footer boilerplate

    Args:
        text: Text to clean

    Returns:
        Cleaned text
    """
    # Patterns to remove (case-insensitive)
    patterns = [
        r"aceitar\s+cookies?",
        r"politica\s+de\s+privacidade",
        r"termos\s+de\s+uso",
        r"compartilhar\s+no\s+(facebook|twitter|linkedin|whatsapp)",
        r"share\s+on\s+(facebook|twitter|linkedin)",
        r"copyright\s+\d{4}",
        r"todos\s+os\s+direitos\s+reservados",
        r"all\s+rights\s+reserved",
        r"subscribe\s+to\s+our\s+newsletter",
        r"inscreva-se\s+em\s+nossa\s+newsletter",
    ]

    for pattern in patterns:
        text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return text


def deduplicate_paragraphs(text: str) -> str:
    """
    Remove duplicate paragraphs from text.

    Args:
        text: Text with potential duplicates

    Returns:
        Deduplicated text
    """
    paragraphs = text.split("\n\n")
    seen = set()
    unique = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        # Create fingerprint (lowercase, no spaces)
        fingerprint = re.sub(r"\s+", "", para.lower())

        if fingerprint not in seen and len(para) >= MIN_SOURCE_LENGTH:
            seen.add(fingerprint)
            unique.append(para)

    return "\n\n".join(unique)


def clean_text(text: str) -> str:
    """
    Apply all text cleaning operations.

    Args:
        text: Raw text

    Returns:
        Cleaned text
    """
    text = normalize_whitespace(text)
    text = remove_common_artifacts(text)
    text = deduplicate_paragraphs(text)
    return text


# =============================================================================
# Source Processing
# =============================================================================


def format_document_source(source: Dict[str, Any]) -> str:
    """
    Format a document source for consolidation.

    Args:
        source: Document source dict with text, filename

    Returns:
        Formatted text with header
    """
    filename = source.get("filename", "documento")
    text = source.get("text", "")
    char_count = source.get("char_count", len(text))

    header = f"=== DOCUMENTO: {filename} ({char_count:,} caracteres) ==="

    return f"{header}\n\n{text}"


def format_url_source(source: Dict[str, Any]) -> str:
    """
    Format a URL source for consolidation.

    Args:
        source: URL source dict with text, url, title

    Returns:
        Formatted text with header
    """
    url = source.get("url", "URL desconhecida")
    title = source.get("title", "")
    text = source.get("text", "")
    char_count = source.get("char_count", len(text))

    if title:
        header = f"=== ARTIGO: {title} ==="
        subheader = f"Fonte: {url} ({char_count:,} caracteres)"
        return f"{header}\n{subheader}\n\n{text}"
    else:
        header = f"=== URL: {url} ({char_count:,} caracteres) ==="
        return f"{header}\n\n{text}"


def format_youtube_source(source: Dict[str, Any]) -> str:
    """
    Format a YouTube source for consolidation.

    Args:
        source: YouTube source dict with text, video_id, title

    Returns:
        Formatted text with header
    """
    video_id = source.get("video_id", "")
    title = source.get("title", "Video do YouTube")
    text = source.get("text", "")
    char_count = source.get("char_count", len(text))
    url = f"https://youtube.com/watch?v={video_id}" if video_id else ""

    header = f"=== VIDEO: {title} ==="
    if url:
        subheader = f"YouTube: {url} ({char_count:,} caracteres)"
        return f"{header}\n{subheader}\n\n{text}"
    else:
        return f"{header}\n({char_count:,} caracteres)\n\n{text}"


def format_source(source: Dict[str, Any]) -> Optional[str]:
    """
    Format any source type for consolidation.

    Args:
        source: Source dict with type and content

    Returns:
        Formatted text or None if invalid
    """
    source_type = source.get("type", "unknown")
    text = source.get("text", "")

    # Skip empty or too short sources
    if not text or len(text.strip()) < MIN_SOURCE_LENGTH:
        print(f"[Consolidator] Skipping short/empty source: {source_type}")
        return None

    if source_type == "document":
        return format_document_source(source)
    elif source_type == "url":
        return format_url_source(source)
    elif source_type == "youtube":
        return format_youtube_source(source)
    else:
        # Generic format
        return f"=== FONTE: {source_type} ===\n\n{text}"


# =============================================================================
# Main Consolidation Function
# =============================================================================


def consolidate_content(
    sources: List[Dict[str, Any]],
    training_title: Optional[str] = None,
    training_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Consolidate multiple content sources into unified training content.

    Args:
        sources: List of source dicts, each with:
            - type: "document", "url", or "youtube"
            - text: Extracted text content
            - Additional metadata (filename, url, title, etc.)
        training_title: Optional training title for header
        training_id: Optional training ID for metadata

    Returns:
        Dict with:
        - consolidated_text: Unified text content
        - char_count: Total characters
        - source_count: Number of sources included
        - sources_summary: Brief summary of each source
        - chunks: List of text chunks (if content exceeds chunk size)
        - content_hash: SHA256 hash for deduplication
        - generated_at: Timestamp

    Raises:
        ValueError: If no valid sources provided
    """
    if not sources:
        raise ValueError("No sources provided for consolidation")

    # Process each source
    formatted_parts = []
    sources_summary = []

    for i, source in enumerate(sources):
        formatted = format_source(source)
        if formatted:
            # Clean the text
            cleaned = clean_text(formatted)
            formatted_parts.append(cleaned)

            # Create summary
            sources_summary.append({
                "index": i,
                "type": source.get("type", "unknown"),
                "name": source.get("filename") or source.get("title") or source.get("url", f"Fonte {i + 1}"),
                "char_count": len(source.get("text", "")),
            })

    if not formatted_parts:
        raise ValueError("No valid content found in any source")

    # Build consolidated content
    header_parts = []
    if training_title:
        header_parts.append(f"# {training_title}")
        header_parts.append("")

    header_parts.append(f"Este treinamento foi criado a partir de {len(formatted_parts)} fonte(s):")
    for summary in sources_summary:
        header_parts.append(f"  - {summary['name']} ({summary['char_count']:,} caracteres)")
    header_parts.append("")
    header_parts.append("=" * 60)
    header_parts.append("")

    header = "\n".join(header_parts)

    # Join all parts with clear separators
    body = "\n\n" + "\n\n".join(formatted_parts)

    # Final consolidation
    consolidated = header + body

    # Truncate if necessary
    if len(consolidated) > MAX_CONSOLIDATED_LENGTH:
        consolidated = consolidated[:MAX_CONSOLIDATED_LENGTH]
        consolidated += f"\n\n[Truncado: conteudo excedeu {MAX_CONSOLIDATED_LENGTH:,} caracteres]"
        print(f"[Consolidator] Warning: Content truncated at {MAX_CONSOLIDATED_LENGTH:,} chars")

    # Generate content hash
    content_hash = hashlib.sha256(consolidated.encode()).hexdigest()[:16]

    # Create chunks for very large content
    chunks = []
    if len(consolidated) > CHUNK_SIZE:
        for i in range(0, len(consolidated), CHUNK_SIZE):
            chunk = consolidated[i:i + CHUNK_SIZE]
            chunks.append({
                "index": i // CHUNK_SIZE,
                "start": i,
                "end": min(i + CHUNK_SIZE, len(consolidated)),
                "text": chunk,
            })

    result = {
        "consolidated_text": consolidated,
        "char_count": len(consolidated),
        "source_count": len(formatted_parts),
        "sources_summary": sources_summary,
        "content_hash": content_hash,
        "generated_at": datetime.utcnow().isoformat() + "Z",
    }

    if chunks:
        result["chunks"] = chunks
        result["chunk_count"] = len(chunks)

    if training_id:
        result["training_id"] = training_id

    print(f"[Consolidator] Consolidated {len(sources_summary)} sources → {len(consolidated):,} chars")

    return result


# =============================================================================
# Summary Generation
# =============================================================================


def generate_content_summary(
    consolidated_text: str,
    max_length: int = 500,
) -> str:
    """
    Generate a brief summary of consolidated content.

    This is a simple extractive summary that takes the first N characters
    of meaningful content. For AI-generated abstractive summaries,
    use the SashaAgent or a dedicated summarization agent.

    Args:
        consolidated_text: Full consolidated text
        max_length: Maximum summary length

    Returns:
        Brief content summary
    """
    # Skip header (first section before ===)
    parts = consolidated_text.split("===", 2)
    if len(parts) > 2:
        content = parts[2]
    else:
        content = consolidated_text

    # Clean and extract first meaningful paragraph
    content = normalize_whitespace(content)
    paragraphs = [p for p in content.split("\n\n") if len(p.strip()) > 50]

    if not paragraphs:
        return content[:max_length] + "..."

    # Take first paragraph(s) up to max_length
    summary = ""
    for para in paragraphs[:3]:
        if len(summary) + len(para) + 2 > max_length:
            break
        if summary:
            summary += "\n\n"
        summary += para

    if len(summary) > max_length:
        summary = summary[:max_length - 3] + "..."

    return summary


# =============================================================================
# Validation
# =============================================================================


def validate_sources(sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Validate and filter sources before consolidation.

    Args:
        sources: List of source dicts

    Returns:
        List of valid sources with validation status

    Raises:
        ValueError: If no valid sources
    """
    validated = []

    for i, source in enumerate(sources):
        result = {
            "index": i,
            "type": source.get("type", "unknown"),
            "valid": False,
            "error": None,
        }

        # Check required fields
        if "text" not in source:
            result["error"] = "Missing 'text' field"
        elif not source["text"] or not source["text"].strip():
            result["error"] = "Empty text content"
        elif len(source["text"].strip()) < MIN_SOURCE_LENGTH:
            result["error"] = f"Text too short (min {MIN_SOURCE_LENGTH} chars)"
        else:
            result["valid"] = True
            result["char_count"] = len(source["text"])

        validated.append(result)

    valid_count = sum(1 for v in validated if v["valid"])
    if valid_count == 0:
        raise ValueError("No valid sources provided")

    return validated


# =============================================================================
# Utility Functions
# =============================================================================


def estimate_consolidation_time(sources: List[Dict[str, Any]]) -> int:
    """
    Estimate time to consolidate sources (seconds).

    Args:
        sources: List of sources

    Returns:
        Estimated seconds
    """
    total_chars = sum(len(s.get("text", "")) for s in sources)
    # Rough estimate: 100K chars per second
    return max(1, total_chars // 100_000)


def get_content_statistics(consolidated_text: str) -> Dict[str, Any]:
    """
    Calculate statistics for consolidated content.

    Args:
        consolidated_text: Consolidated text

    Returns:
        Dict with word_count, paragraph_count, etc.
    """
    words = len(consolidated_text.split())
    paragraphs = len([p for p in consolidated_text.split("\n\n") if p.strip()])
    sentences = len(re.findall(r"[.!?]+", consolidated_text))
    lines = len(consolidated_text.split("\n"))

    return {
        "char_count": len(consolidated_text),
        "word_count": words,
        "paragraph_count": paragraphs,
        "sentence_count": sentences,
        "line_count": lines,
        "avg_words_per_paragraph": words // max(1, paragraphs),
    }
