# =============================================================================
# File Detector Tool - Smart File Type Detection
# =============================================================================
# Detects file type using multiple strategies:
# 1. Magic bytes (file signature) - Most reliable
# 2. MIME type from Content-Type header
# 3. File extension fallback
#
# Philosophy: Observe -> Think -> Learn -> Act
# The agent OBSERVES the raw bytes, THINKS about patterns,
# LEARNS from multiple detection strategies, and ACTS with confidence.
# =============================================================================

from typing import Literal

# Type definition for supported file types
FileType = Literal["xml", "pdf", "image", "csv", "xlsx", "txt", "unknown"]


def detect_file_type(
    filename: str,
    content_type: str = "",
    file_data: bytes = b"",
) -> FileType:
    """
    Detect file type using multiple strategies for maximum reliability.

    Strategy Priority:
    1. Magic bytes (file signature) - Most reliable, cannot be spoofed
    2. Content-Type MIME header - Second most reliable
    3. File extension - Fallback when bytes unavailable

    Args:
        filename: Original filename with extension
        content_type: MIME type from HTTP header (optional)
        file_data: Raw file bytes for magic byte detection (optional)

    Returns:
        FileType: One of 'xml', 'pdf', 'image', 'csv', 'xlsx', 'txt', 'unknown'
    """
    # ==========================================================================
    # Strategy 1: Magic Bytes Detection (Most Reliable)
    # ==========================================================================
    if file_data:
        detected = _detect_by_magic_bytes(file_data)
        if detected != "unknown":
            return detected

    # ==========================================================================
    # Strategy 2: MIME Type Detection
    # ==========================================================================
    if content_type:
        detected = _detect_by_mime_type(content_type)
        if detected != "unknown":
            return detected

    # ==========================================================================
    # Strategy 3: Extension Fallback
    # ==========================================================================
    return _detect_by_extension(filename)


def _detect_by_magic_bytes(file_data: bytes) -> FileType:
    """
    Detect file type by examining magic bytes (file signature).

    Magic bytes are the first few bytes of a file that identify its format.
    This is the most reliable method as it examines actual file content.
    """
    if len(file_data) < 2:
        return "unknown"

    # XML: Starts with '<?xml' (with optional BOM)
    # Handle UTF-8 BOM: EF BB BF
    if file_data[:3] == b"\xef\xbb\xbf":
        file_data = file_data[3:]  # Strip BOM

    if file_data[:5] == b"<?xml" or file_data[:6] == b"<?xml ":
        return "xml"

    # Also check for XML without declaration but with root element
    # Common in NF: <nfeProc or <NFe
    stripped = file_data.lstrip()
    if stripped[:1] == b"<" and b"nfe" in stripped[:100].lower():
        return "xml"

    # PDF: Starts with '%PDF'
    if file_data[:4] == b"%PDF":
        return "pdf"

    # PNG: 89 50 4E 47 0D 0A 1A 0A
    if file_data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image"

    # JPEG: FF D8 FF
    if file_data[:3] == b"\xff\xd8\xff":
        return "image"

    # GIF: 47 49 46 38 (GIF8)
    if file_data[:4] == b"GIF8":
        return "image"

    # XLSX/DOCX/ZIP: PK (ZIP signature) - 50 4B 03 04
    if file_data[:4] == b"PK\x03\x04":
        # Could be XLSX, DOCX, or other Office Open XML
        # Check for xl/ directory which indicates Excel
        if b"xl/" in file_data[:2000] or b"[Content_Types].xml" in file_data[:2000]:
            return "xlsx"
        # If can't determine, assume xlsx for now
        return "xlsx"

    # CSV: Plain text, check for comma/semicolon patterns
    # This is heuristic - CSV has no magic bytes
    if _looks_like_csv(file_data):
        return "csv"

    # TXT: Fallback for plain text
    if _is_plain_text(file_data):
        return "txt"

    return "unknown"


def _detect_by_mime_type(content_type: str) -> FileType:
    """
    Detect file type from MIME Content-Type header.
    """
    content_type = content_type.lower().split(";")[0].strip()

    mime_map = {
        # XML
        "application/xml": "xml",
        "text/xml": "xml",
        "application/xhtml+xml": "xml",
        # PDF
        "application/pdf": "pdf",
        # Images
        "image/jpeg": "image",
        "image/jpg": "image",
        "image/png": "image",
        "image/gif": "image",
        "image/webp": "image",
        # Spreadsheets
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": "xlsx",
        "application/vnd.ms-excel": "xlsx",
        # CSV
        "text/csv": "csv",
        "application/csv": "csv",
        # Text
        "text/plain": "txt",
    }

    return mime_map.get(content_type, "unknown")


def _detect_by_extension(filename: str) -> FileType:
    """
    Detect file type from file extension.
    This is the fallback method when bytes/MIME are unavailable.
    """
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    ext_map = {
        # XML
        "xml": "xml",
        # PDF
        "pdf": "pdf",
        # Images
        "jpg": "image",
        "jpeg": "image",
        "png": "image",
        "gif": "image",
        "webp": "image",
        # Spreadsheets
        "xlsx": "xlsx",
        "xls": "xlsx",
        # CSV
        "csv": "csv",
        # Text
        "txt": "txt",
        "text": "txt",
        "md": "txt",  # Markdown treated as text
    }

    return ext_map.get(ext, "unknown")


def _looks_like_csv(data: bytes) -> bool:
    """
    Heuristic check if data looks like CSV.
    CSV has no magic bytes, so we check for patterns.
    """
    try:
        # Try to decode as text
        text = data[:2000].decode("utf-8", errors="ignore")

        # Check for CSV-like patterns
        lines = text.split("\n")
        if len(lines) < 2:
            return False

        # Count delimiters in first few lines
        delimiters = [",", ";", "\t"]
        for delimiter in delimiters:
            counts = [line.count(delimiter) for line in lines[:5] if line.strip()]
            if len(counts) >= 2 and counts[0] > 0:
                # Check if delimiter count is consistent
                if all(c == counts[0] for c in counts):
                    return True

        return False
    except Exception:
        return False


def _is_plain_text(data: bytes) -> bool:
    """
    Check if data is likely plain text (not binary).
    """
    try:
        # Try to decode as UTF-8
        text = data[:1000].decode("utf-8", errors="strict")

        # Check for high ratio of printable characters
        printable = sum(1 for c in text if c.isprintable() or c.isspace())
        return printable / len(text) > 0.9 if text else False
    except Exception:
        return False


# =============================================================================
# Human-friendly labels for UI display
# =============================================================================

FILE_TYPE_LABELS = {
    "xml": "XML (Nota Fiscal)",
    "pdf": "PDF (Documento)",
    "image": "Imagem (JPG/PNG)",
    "csv": "CSV (Planilha)",
    "xlsx": "Excel (XLSX)",
    "txt": "Texto (TXT)",
    "unknown": "Formato desconhecido",
}


def get_file_type_label(file_type: FileType) -> str:
    """Get human-friendly label for file type."""
    return FILE_TYPE_LABELS.get(file_type, "Formato desconhecido")
