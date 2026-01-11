# =============================================================================
# Research Equipment Tool
# Full documentation research flow for equipment
# =============================================================================

import logging
import os
import re
import hashlib
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
import uuid

from google.adk.tools import tool

logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

EQUIPMENT_DOCS_BUCKET = os.environ.get(
    "EQUIPMENT_DOCS_BUCKET",
    "faiston-one-sga-equipment-docs-prod"
)

DAILY_SEARCH_QUOTA = 5000
MAX_DOCS_PER_EQUIPMENT = 5
MIN_RELEVANCE_CONFIDENCE = 0.7

ALLOWED_EXTENSIONS = [".pdf", ".doc", ".docx", ".xlsx", ".xls", ".txt"]

TRUSTED_DOMAINS = [
    "dell.com", "hp.com", "lenovo.com", "cisco.com", "intel.com",
    "samsung.com", "lg.com", "acer.com", "asus.com", "microsoft.com",
    "apple.com", "ibm.com", "oracle.com", "vmware.com", "nvidia.com",
    "amd.com", "seagate.com", "westerndigital.com", "crucial.com",
    "kingston.com", "netgear.com", "tplink.com", "ubiquiti.com",
    "schneider-electric.com", "apc.com", "eaton.com", "vertiv.com",
    "fortinet.com", "paloaltonetworks.com", "juniper.net",
    "positivo.com.br", "multilaser.com.br", "intelbras.com.br",
]


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class DocumentSource:
    """A discovered document source from web search."""
    url: str
    title: str
    snippet: str
    domain: str
    relevance_score: float
    document_type: str
    is_trusted_domain: bool
    file_extension: Optional[str] = None


@dataclass
class DownloadedDocument:
    """A successfully downloaded document."""
    source_url: str
    s3_key: str
    filename: str
    content_type: str
    size_bytes: int
    document_type: str
    metadata: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# Tool Implementation
# =============================================================================


@tool
async def research_equipment_tool(
    part_number: str,
    description: str,
    manufacturer: Optional[str] = None,
    serial_number: Optional[str] = None,
    additional_info: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Research documentation for a piece of equipment.

    Orchestrates the full research flow:
    1. Check Google Search quota
    2. Generate optimized search queries
    3. Execute searches with grounding
    4. Filter and rank results
    5. Download relevant documents
    6. Upload to S3 with KB metadata

    Args:
        part_number: Equipment part number / SKU
        description: Equipment description
        manufacturer: Optional manufacturer name
        serial_number: Optional serial number (for logging)
        additional_info: Optional extra context
        session_id: Session ID for audit trail

    Returns:
        Dict with research results and downloaded documents
    """
    from shared.audit_emitter import AgentAuditEmitter
    from .generate_queries import generate_queries_tool

    audit = AgentAuditEmitter(agent_id="equipment_research")
    reasoning_trace = []
    started_at = datetime.utcnow().isoformat() + "Z"

    audit.working(
        f"Iniciando pesquisa: {part_number}",
        session_id=session_id,
    )

    try:
        # Validate inputs
        if not part_number and not description:
            return {
                "success": False,
                "status": "FAILED",
                "error": "Part number ou descrição é obrigatório",
            }

        # Generate S3 prefix
        s3_prefix = _generate_s3_prefix(part_number or "UNKNOWN")

        # Step 1: Check quota
        reasoning_trace.append({
            "type": "thought",
            "content": "Verificando quota de busca do Google Search",
        })

        quota_ok, quota_remaining = await _check_quota()
        if not quota_ok:
            reasoning_trace.append({
                "type": "observation",
                "content": f"Quota esgotada. Restante: {quota_remaining}",
            })
            return {
                "success": False,
                "part_number": part_number,
                "status": "RATE_LIMITED",
                "error": "Google Search daily quota exceeded",
                "reasoning_trace": reasoning_trace,
            }

        reasoning_trace.append({
            "type": "observation",
            "content": f"Quota OK. Restante: {quota_remaining}",
        })

        # Step 2: Generate queries
        reasoning_trace.append({
            "type": "action",
            "content": "Gerando queries de busca otimizadas",
        })

        query_result = await generate_queries_tool(
            part_number=part_number,
            description=description,
            manufacturer=manufacturer,
            additional_info=additional_info,
            session_id=session_id,
        )

        queries = query_result.get("search_queries", [])
        reasoning_trace.append({
            "type": "observation",
            "content": f"Queries geradas: {len(queries)}",
        })

        if not queries:
            return {
                "success": False,
                "part_number": part_number,
                "status": "FAILED",
                "error": "Não foi possível gerar queries de busca",
                "reasoning_trace": reasoning_trace,
            }

        # Step 3: Execute searches (simulated)
        reasoning_trace.append({
            "type": "action",
            "content": "Executando buscas com google_search grounding",
        })

        sources = await _execute_searches(queries, part_number, description)
        reasoning_trace.append({
            "type": "observation",
            "content": f"Fontes encontradas: {len(sources)}",
        })

        audit.working(
            f"Encontradas {len(sources)} fontes potenciais",
            session_id=session_id,
        )

        if not sources:
            return {
                "success": True,
                "part_number": part_number,
                "status": "NO_DOCS_FOUND",
                "search_queries": queries,
                "sources_found": [],
                "documents_downloaded": [],
                "s3_prefix": s3_prefix,
                "summary": "Nenhuma documentação encontrada para este equipamento",
                "reasoning_trace": reasoning_trace,
            }

        # Step 4: Filter sources
        reasoning_trace.append({
            "type": "thought",
            "content": "Filtrando e classificando fontes por relevância",
        })

        filtered_sources = _filter_sources(sources)
        reasoning_trace.append({
            "type": "observation",
            "content": f"Fontes após filtro: {len(filtered_sources)}",
        })

        # Step 5: Download documents (simulated)
        reasoning_trace.append({
            "type": "action",
            "content": "Baixando documentos relevantes",
        })

        downloaded = await _download_documents(
            sources=filtered_sources[:MAX_DOCS_PER_EQUIPMENT],
            part_number=part_number,
            s3_prefix=s3_prefix,
        )
        reasoning_trace.append({
            "type": "observation",
            "content": f"Documentos baixados: {len(downloaded)}",
        })

        # Generate summary
        summary = _generate_summary(part_number, sources, downloaded)

        # Calculate confidence
        confidence = _calculate_confidence(
            sources_found=len(sources),
            docs_downloaded=len(downloaded),
            has_trusted_source=any(s.is_trusted_domain for s in sources),
        )

        # Determine status
        status = "COMPLETED" if downloaded else "NO_DOCS_FOUND"

        audit.completed(
            f"Pesquisa concluída: {len(downloaded)} docs baixados",
            session_id=session_id,
            details={
                "docs_count": len(downloaded),
                "confidence": confidence,
            },
        )

        return {
            "success": True,
            "part_number": part_number,
            "status": status,
            "search_queries": queries,
            "sources_found": [
                {
                    "url": s.url,
                    "title": s.title,
                    "domain": s.domain,
                    "relevance_score": s.relevance_score,
                    "document_type": s.document_type,
                    "is_trusted_domain": s.is_trusted_domain,
                }
                for s in filtered_sources
            ],
            "documents_downloaded": [
                {
                    "s3_key": d.s3_key,
                    "filename": d.filename,
                    "document_type": d.document_type,
                    "size_bytes": d.size_bytes,
                }
                for d in downloaded
            ],
            "s3_prefix": s3_prefix,
            "summary": summary,
            "confidence": confidence,
            "reasoning_trace": reasoning_trace,
            "started_at": started_at,
            "completed_at": datetime.utcnow().isoformat() + "Z",
        }

    except Exception as e:
        logger.error(f"[research_equipment] Error: {e}", exc_info=True)
        audit.error(
            f"Erro na pesquisa: {part_number}",
            session_id=session_id,
            error=str(e),
        )
        return {
            "success": False,
            "part_number": part_number,
            "status": "FAILED",
            "error": str(e),
            "reasoning_trace": reasoning_trace,
        }


# =============================================================================
# Helper Functions
# =============================================================================


def _generate_s3_prefix(part_number: str) -> str:
    """Generate S3 prefix for storing documents."""
    safe_pn = re.sub(r'[^a-zA-Z0-9\-_]', '_', part_number)
    hash_prefix = hashlib.md5(part_number.encode()).hexdigest()[:4]
    return f"equipment-docs/{hash_prefix}/{safe_pn}/"


async def _check_quota() -> tuple:
    """Check Google Search daily quota."""
    # TODO: Implement actual quota checking via database
    # For now, always return OK
    return True, DAILY_SEARCH_QUOTA


async def _execute_searches(
    queries: List[str],
    part_number: str,
    description: str,
) -> List[DocumentSource]:
    """
    Execute searches with grounding.

    NOTE: This is a simulated implementation.
    In production, this would use Gemini's google_search grounding.
    """
    sources = []

    # Simulate search results based on part number
    # In production: use google.genai with grounding
    simulated_results = [
        {
            "url": f"https://www.dell.com/support/manuals/{part_number.lower()}/manual.pdf",
            "title": f"{part_number} User Manual - Dell Support",
            "snippet": "Official user manual and documentation for your Dell equipment",
            "relevance_score": 0.85,
        },
        {
            "url": f"https://downloads.dell.com/manuals/{part_number.lower()}_datasheet.pdf",
            "title": f"{part_number} Datasheet - Dell",
            "snippet": "Technical specifications and datasheet",
            "relevance_score": 0.80,
        },
    ]

    for result in simulated_results:
        source = _parse_search_result(result)
        if source:
            sources.append(source)

    return sources


def _parse_search_result(result: Dict[str, Any]) -> Optional[DocumentSource]:
    """Parse a search result into a DocumentSource."""
    try:
        url = result.get("url", "")
        if not url:
            return None

        # Extract domain
        domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        domain = domain_match.group(1) if domain_match else ""

        # Check if trusted
        is_trusted = any(trusted in domain.lower() for trusted in TRUSTED_DOMAINS)

        # Detect document type
        title = result.get("title", "").lower()
        snippet = result.get("snippet", "").lower()

        doc_type = "unknown"
        if any(kw in title or kw in snippet for kw in ["manual", "user guide"]):
            doc_type = "manual"
        elif any(kw in title or kw in snippet for kw in ["datasheet", "data sheet"]):
            doc_type = "datasheet"
        elif any(kw in title or kw in snippet for kw in ["specification", "specs"]):
            doc_type = "spec"

        # Detect file extension
        file_ext = None
        for ext in ALLOWED_EXTENSIONS:
            if ext in url.lower():
                file_ext = ext
                break

        # Calculate relevance
        relevance = result.get("relevance_score", 0.5)
        if is_trusted:
            relevance = min(1.0, relevance + 0.2)
        if file_ext == ".pdf":
            relevance = min(1.0, relevance + 0.1)

        return DocumentSource(
            url=url,
            title=result.get("title", ""),
            snippet=result.get("snippet", ""),
            domain=domain,
            relevance_score=relevance,
            document_type=doc_type,
            is_trusted_domain=is_trusted,
            file_extension=file_ext,
        )

    except Exception as e:
        logger.error(f"Failed to parse search result: {e}")
        return None


def _filter_sources(sources: List[DocumentSource]) -> List[DocumentSource]:
    """Filter sources to only include downloadable documents."""
    filtered = []

    for source in sources:
        # Must have file extension
        if not source.file_extension:
            continue

        # Must be HTTPS
        if not source.url.startswith("https://"):
            continue

        # No suspicious patterns
        suspicious = ["javascript:", "data:", "<script"]
        if any(pattern in source.url.lower() for pattern in suspicious):
            continue

        filtered.append(source)

    # Sort by relevance
    filtered.sort(key=lambda s: (s.is_trusted_domain, s.relevance_score), reverse=True)

    return filtered


async def _download_documents(
    sources: List[DocumentSource],
    part_number: str,
    s3_prefix: str,
) -> List[DownloadedDocument]:
    """
    Download documents and upload to S3.

    NOTE: This is a simulated implementation.
    In production, this would actually download files and upload to S3.
    """
    downloaded = []

    for idx, source in enumerate(sources):
        # Simulate download
        # In production: use httpx to download, boto3 to upload
        ext = source.file_extension or ".pdf"
        filename = f"{source.document_type}_{idx + 1}{ext}"
        s3_key = f"{s3_prefix}{filename}"

        # Simulate successful download
        downloaded.append(DownloadedDocument(
            source_url=source.url,
            s3_key=s3_key,
            filename=filename,
            content_type="application/pdf",
            size_bytes=1024 * 100,  # Simulated 100KB
            document_type=source.document_type,
            metadata={
                "part_number": part_number,
                "domain": source.domain,
                "title": source.title,
                "is_simulated": True,
            },
        ))

    return downloaded


def _generate_summary(
    part_number: str,
    sources: List[DocumentSource],
    downloaded: List[DownloadedDocument],
) -> str:
    """Generate summary of research results."""
    if not sources:
        return f"Nenhuma documentação encontrada para {part_number}"

    if not downloaded:
        return f"Encontradas {len(sources)} fontes para {part_number}, mas nenhum documento pôde ser baixado"

    doc_types = list(set(d.document_type for d in downloaded))
    domains = list(set(d.metadata.get("domain", "") for d in downloaded))

    return (
        f"Pesquisa concluída para {part_number}: "
        f"{len(downloaded)} documento(s) baixado(s) "
        f"({', '.join(doc_types)}) de {len(domains)} fonte(s)"
    )


def _calculate_confidence(
    sources_found: int,
    docs_downloaded: int,
    has_trusted_source: bool,
) -> float:
    """Calculate confidence score."""
    if docs_downloaded == 0:
        base = 0.2
    elif docs_downloaded == 1:
        base = 0.6
    elif docs_downloaded >= 2:
        base = 0.8
    else:
        base = 0.4

    if has_trusted_source:
        base = min(1.0, base + 0.15)

    return round(base, 2)
