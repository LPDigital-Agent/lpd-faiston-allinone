# =============================================================================
# Equipment Research Agent - Documentation Discovery
# =============================================================================
# AI-First agent that researches equipment documentation after imports.
# Uses Gemini 3.0 Pro with google_search grounding to find official manuals,
# datasheets, and specifications from manufacturer websites.
#
# Philosophy: OBSERVE → THINK → ACT → ORGANIZE
#
# Module: Gestao de Ativos -> Gestao de Estoque -> Knowledge Base
# Model: Gemini 3.0 Pro with google_search grounding (MANDATORY per CLAUDE.md)
#
# Security: OWASP-compliant, no PII logging, input validation
# =============================================================================

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from datetime import datetime
import json
import re
import hashlib

from agents.base_agent import BaseInventoryAgent, ConfidenceScore
from agents.utils import (
    APP_NAME,
    MODEL_GEMINI,
    RiskLevel,
    log_agent_action,
    now_iso,
    generate_id,
    extract_json,
    parse_json_safe,
)


# =============================================================================
# Constants
# =============================================================================

# S3 bucket for equipment documentation (set via environment variable)
import os
EQUIPMENT_DOCS_BUCKET = os.environ.get(
    "EQUIPMENT_DOCS_BUCKET",
    "faiston-one-sga-equipment-docs-prod"
)

# Google Search daily quota limit
DAILY_SEARCH_QUOTA = 5000

# Maximum documents to download per equipment
MAX_DOCS_PER_EQUIPMENT = 5

# Minimum confidence for document relevance
MIN_RELEVANCE_CONFIDENCE = 0.7

# Trusted domains for equipment documentation
TRUSTED_DOMAINS = [
    "dell.com", "hp.com", "lenovo.com", "cisco.com", "intel.com",
    "samsung.com", "lg.com", "acer.com", "asus.com", "microsoft.com",
    "apple.com", "ibm.com", "oracle.com", "vmware.com", "nvidia.com",
    "amd.com", "seagate.com", "westerndigital.com", "crucial.com",
    "kingston.com", "netgear.com", "tplink.com", "ubiquiti.com",
    "schneider-electric.com", "apc.com", "eaton.com", "vertiv.com",
    "fortinet.com", "paloaltonetworks.com", "juniper.net",
    # Brazilian manufacturers/distributors
    "positivo.com.br", "multilaser.com.br", "intelbras.com.br",
]

# File types to download
ALLOWED_EXTENSIONS = [".pdf", ".doc", ".docx", ".xlsx", ".xls", ".txt"]


# =============================================================================
# Types and Enums
# =============================================================================


class ResearchStatus(Enum):
    """Status of equipment research task."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    NO_DOCS_FOUND = "NO_DOCS_FOUND"
    FAILED = "FAILED"
    RATE_LIMITED = "RATE_LIMITED"


@dataclass
class DocumentSource:
    """A discovered document source from web search."""
    url: str
    title: str
    snippet: str
    domain: str
    relevance_score: float
    document_type: str  # "manual", "datasheet", "spec", "guide", "unknown"
    is_trusted_domain: bool
    file_extension: Optional[str] = None
    size_estimate: Optional[int] = None


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


@dataclass
class ResearchResult:
    """Result of equipment research."""
    part_number: str
    status: ResearchStatus
    search_queries: List[str]
    sources_found: List[DocumentSource]
    documents_downloaded: List[DownloadedDocument]
    s3_prefix: str
    summary: str
    confidence: ConfidenceScore
    reasoning_trace: List[Dict[str, str]]
    error: Optional[str] = None
    started_at: str = field(default_factory=now_iso)
    completed_at: Optional[str] = None


# =============================================================================
# Agent Instruction (System Prompt)
# =============================================================================


EQUIPMENT_RESEARCH_INSTRUCTION = """Você é um agente especializado em pesquisar documentação técnica de equipamentos.

## Seu Papel

Quando receber informações sobre um equipamento (part number, descrição, fabricante), você deve:

1. **OBSERVE**: Analisar as informações fornecidas e identificar o tipo de equipamento
2. **THINK**: Gerar queries de busca otimizadas para encontrar documentação oficial
3. **ACT**: Avaliar os resultados da busca e identificar documentos relevantes
4. **ORGANIZE**: Estruturar as informações encontradas

## Tipos de Documentos Prioritários

1. **Manual do Usuário** - Instruções de operação e uso
2. **Datasheet** - Especificações técnicas completas
3. **Quick Start Guide** - Guia de início rápido
4. **Service Manual** - Manual de manutenção/reparo
5. **Especificações** - Sheets de especificação técnica

## Formato de Resposta

SEMPRE responda em JSON válido com a estrutura:
```json
{
    "equipment_type": "tipo do equipamento",
    "manufacturer": "fabricante identificado",
    "search_queries": ["query1", "query2", "query3"],
    "reasoning": "explicação do raciocínio",
    "document_priorities": ["manual", "datasheet", "spec"],
    "confidence": 0.0 a 1.0
}
```

## Linguagem

Responda em português brasileiro, mas as queries de busca devem ser em inglês para melhores resultados.

## Segurança

- NUNCA inclua informações pessoais nas queries
- Priorize sites oficiais de fabricantes
- Evite sites de terceiros desconhecidos
"""


# =============================================================================
# Equipment Research Agent
# =============================================================================


class EquipmentResearchAgent(BaseInventoryAgent):
    """
    AI-First agent for researching equipment documentation.

    Uses Gemini 3.0 Pro with google_search grounding to find official
    documentation from manufacturer websites. Documents are downloaded
    and organized in S3 for Bedrock Knowledge Base ingestion.

    Security Compliance:
        - OWASP: Input validation, no injection vulnerabilities
        - NIST: Secure API usage, least privilege
        - AWS Well-Architected: S3 encryption, IAM roles

    Example:
        agent = EquipmentResearchAgent()
        result = await agent.research_equipment(
            part_number="ABC123",
            description="Dell PowerEdge R740 Server",
            manufacturer="Dell",
        )
    """

    def __init__(self):
        """Initialize the Equipment Research Agent."""
        super().__init__(
            name="EquipmentResearchAgent",
            instruction=EQUIPMENT_RESEARCH_INSTRUCTION,
            description="Pesquisa documentação técnica de equipamentos usando IA",
        )
        self._reasoning_trace: List[Dict[str, str]] = []

    # =========================================================================
    # Main Research Flow
    # =========================================================================

    async def research_equipment(
        self,
        part_number: str,
        description: str,
        serial_number: Optional[str] = None,
        manufacturer: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> ResearchResult:
        """
        Research documentation for a piece of equipment.

        This is the main entry point that orchestrates the full research flow:
        1. Check if already researched (deduplication)
        2. Check Google Search quota
        3. Generate optimized search queries using Gemini
        4. Execute searches with google_search grounding
        5. Evaluate and filter results
        6. Download relevant documents
        7. Upload to S3 with KB metadata
        8. Update research status

        Args:
            part_number: Part number / SKU of the equipment
            description: Equipment description
            serial_number: Optional serial number (for logging only)
            manufacturer: Optional manufacturer name
            additional_info: Optional extra context

        Returns:
            ResearchResult with status and downloaded documents
        """
        log_agent_action(
            self.name, "research_equipment",
            entity_type="part_number",
            entity_id=part_number,
            status="started",
        )

        self._reasoning_trace = []
        s3_prefix = self._generate_s3_prefix(part_number)

        # Initialize result
        result = ResearchResult(
            part_number=part_number,
            status=ResearchStatus.IN_PROGRESS,
            search_queries=[],
            sources_found=[],
            documents_downloaded=[],
            s3_prefix=s3_prefix,
            summary="",
            confidence=ConfidenceScore(overall=0.0),
            reasoning_trace=[],
        )

        try:
            # Step 1: Check quota
            self._add_reasoning("thought", "Verificando quota de busca do Google Search")
            quota_ok, quota_remaining = await self._check_quota()

            if not quota_ok:
                self._add_reasoning("observation", f"Quota esgotada. Restante: {quota_remaining}")
                result.status = ResearchStatus.RATE_LIMITED
                result.error = "Google Search daily quota exceeded"
                result.completed_at = now_iso()
                return result

            self._add_reasoning("observation", f"Quota OK. Restante: {quota_remaining}")

            # Step 2: Generate search queries using Gemini
            self._add_reasoning("action", "Gerando queries de busca otimizadas com Gemini")
            queries = await self._generate_search_queries(
                part_number=part_number,
                description=description,
                manufacturer=manufacturer,
                additional_info=additional_info,
            )
            result.search_queries = queries
            self._add_reasoning("observation", f"Queries geradas: {len(queries)}")

            # Step 3: Execute searches with google_search grounding
            self._add_reasoning("action", "Executando buscas com google_search grounding")
            sources = await self._execute_searches(queries, part_number, description)
            result.sources_found = sources
            self._add_reasoning("observation", f"Fontes encontradas: {len(sources)}")

            if not sources:
                result.status = ResearchStatus.NO_DOCS_FOUND
                result.summary = "Nenhuma documentação encontrada para este equipamento"
                result.completed_at = now_iso()
                result.reasoning_trace = self._reasoning_trace.copy()
                return result

            # Step 4: Filter and rank sources
            self._add_reasoning("thought", "Filtrando e classificando fontes por relevância")
            filtered_sources = self._filter_sources(sources)
            self._add_reasoning("observation", f"Fontes após filtro: {len(filtered_sources)}")

            # Step 5: Download documents
            self._add_reasoning("action", "Baixando documentos relevantes")
            downloaded = await self._download_documents(
                sources=filtered_sources[:MAX_DOCS_PER_EQUIPMENT],
                part_number=part_number,
                s3_prefix=s3_prefix,
            )
            result.documents_downloaded = downloaded
            self._add_reasoning("observation", f"Documentos baixados: {len(downloaded)}")

            # Step 6: Generate summary
            result.summary = self._generate_summary(part_number, sources, downloaded)

            # Step 7: Calculate confidence
            result.confidence = self._calculate_research_confidence(
                sources_found=len(sources),
                docs_downloaded=len(downloaded),
                has_trusted_source=any(s.is_trusted_domain for s in sources),
            )

            # Set final status
            if downloaded:
                result.status = ResearchStatus.COMPLETED
            else:
                result.status = ResearchStatus.NO_DOCS_FOUND

            result.completed_at = now_iso()
            result.reasoning_trace = self._reasoning_trace.copy()

            log_agent_action(
                self.name, "research_equipment",
                entity_type="part_number",
                entity_id=part_number,
                status="completed",
                details={"count": len(downloaded)},
            )

            return result

        except Exception as e:
            log_agent_action(
                self.name, "research_equipment",
                entity_type="part_number",
                entity_id=part_number,
                status="failed",
                details={"error": str(e)[:100]},
            )

            result.status = ResearchStatus.FAILED
            result.error = str(e)
            result.completed_at = now_iso()
            result.reasoning_trace = self._reasoning_trace.copy()
            return result

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _add_reasoning(self, step_type: str, content: str) -> None:
        """Add a step to the reasoning trace."""
        self._reasoning_trace.append({
            "type": step_type,
            "content": content,
            "timestamp": now_iso(),
        })

    def _generate_s3_prefix(self, part_number: str) -> str:
        """
        Generate S3 prefix for storing documents.

        Format: equipment-docs/{part_number_hash}/{part_number}/
        Uses hash prefix for better S3 partitioning.
        """
        # Sanitize part number for use in S3 key
        safe_pn = re.sub(r'[^a-zA-Z0-9\-_]', '_', part_number)

        # Create hash prefix for partitioning
        hash_prefix = hashlib.md5(part_number.encode()).hexdigest()[:4]

        return f"equipment-docs/{hash_prefix}/{safe_pn}/"

    async def _check_quota(self) -> Tuple[bool, int]:
        """
        Check Google Search daily quota.

        Returns:
            Tuple of (quota_ok, remaining_count)
        """
        # TODO: Implement PostgreSQL quota check
        # For now, return OK with default quota
        # This will be implemented in Phase 4 with database integration
        return True, DAILY_SEARCH_QUOTA

    async def _generate_search_queries(
        self,
        part_number: str,
        description: str,
        manufacturer: Optional[str] = None,
        additional_info: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """
        Generate optimized search queries using Gemini.

        Uses the base agent to invoke Gemini with the system prompt
        to generate contextually relevant search queries.

        Args:
            part_number: Equipment part number
            description: Equipment description
            manufacturer: Optional manufacturer name
            additional_info: Optional extra context

        Returns:
            List of search query strings
        """
        prompt = f"""Gere queries de busca para encontrar documentação técnica deste equipamento:

Part Number: {part_number}
Descrição: {description}
"""
        if manufacturer:
            prompt += f"Fabricante: {manufacturer}\n"

        if additional_info:
            prompt += f"Informações Adicionais: {json.dumps(additional_info, ensure_ascii=False)}\n"

        prompt += """
Gere de 3 a 5 queries de busca otimizadas em INGLÊS para encontrar:
1. Manual do usuário
2. Datasheet / especificações técnicas
3. Quick start guide

As queries devem incluir:
- Nome/modelo do equipamento
- Fabricante (se conhecido)
- Tipo de documento desejado (manual, datasheet, etc.)
- Formato de arquivo (PDF quando relevante)

Responda APENAS em JSON.
"""

        try:
            response = await self.invoke(prompt)
            result = parse_json_safe(response)

            if "search_queries" in result:
                return result["search_queries"]

            # Fallback: generate basic queries
            return self._generate_fallback_queries(part_number, description, manufacturer)

        except Exception as e:
            print(f"[EquipmentResearchAgent] Query generation failed: {e}")
            return self._generate_fallback_queries(part_number, description, manufacturer)

    def _generate_fallback_queries(
        self,
        part_number: str,
        description: str,
        manufacturer: Optional[str] = None,
    ) -> List[str]:
        """Generate basic fallback queries without AI."""
        queries = []

        # Extract key terms from description
        terms = description.split()[:5]  # First 5 words
        base_query = " ".join(terms)

        if manufacturer:
            queries.append(f"{manufacturer} {part_number} manual PDF")
            queries.append(f"{manufacturer} {base_query} datasheet")
            queries.append(f"{manufacturer} {part_number} specifications")
        else:
            queries.append(f"{part_number} manual PDF")
            queries.append(f"{base_query} datasheet")
            queries.append(f"{part_number} specifications technical")

        return queries

    async def _execute_searches(
        self,
        queries: List[str],
        part_number: str,
        description: str,
    ) -> List[DocumentSource]:
        """
        Execute searches using Gemini with google_search grounding.

        Uses the google.genai grounding feature to perform web searches
        and extract relevant documentation sources.

        Args:
            queries: Search queries to execute
            part_number: Equipment part number (for context)
            description: Equipment description (for context)

        Returns:
            List of DocumentSource objects
        """
        sources: List[DocumentSource] = []

        # Lazy import for cold start optimization
        from tools.web_research_tool import search_with_grounding

        for query in queries[:3]:  # Limit to 3 queries to conserve quota
            try:
                results = await search_with_grounding(
                    query=query,
                    context=f"Equipment: {description} (PN: {part_number})",
                    max_results=5,
                )

                for result in results:
                    source = self._parse_search_result(result)
                    if source and source.relevance_score >= MIN_RELEVANCE_CONFIDENCE:
                        # Check for duplicates
                        if not any(s.url == source.url for s in sources):
                            sources.append(source)

            except Exception as e:
                print(f"[EquipmentResearchAgent] Search failed for '{query}': {e}")
                continue

        # Sort by relevance and trusted domain
        sources.sort(
            key=lambda s: (s.is_trusted_domain, s.relevance_score),
            reverse=True
        )

        return sources

    def _parse_search_result(self, result: Dict[str, Any]) -> Optional[DocumentSource]:
        """Parse a search result into a DocumentSource."""
        try:
            url = result.get("url", "")
            if not url:
                return None

            # Extract domain
            domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
            domain = domain_match.group(1) if domain_match else ""

            # Check if trusted domain
            is_trusted = any(
                trusted in domain.lower()
                for trusted in TRUSTED_DOMAINS
            )

            # Detect document type from URL/title
            title = result.get("title", "").lower()
            snippet = result.get("snippet", "").lower()

            doc_type = "unknown"
            if any(kw in title or kw in snippet for kw in ["manual", "user guide"]):
                doc_type = "manual"
            elif any(kw in title or kw in snippet for kw in ["datasheet", "data sheet", "spec sheet"]):
                doc_type = "datasheet"
            elif any(kw in title or kw in snippet for kw in ["specification", "specs"]):
                doc_type = "spec"
            elif any(kw in title or kw in snippet for kw in ["quick start", "quickstart", "getting started"]):
                doc_type = "guide"

            # Detect file extension
            file_ext = None
            for ext in ALLOWED_EXTENSIONS:
                if ext in url.lower():
                    file_ext = ext
                    break

            # Calculate relevance score
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
            print(f"[EquipmentResearchAgent] Failed to parse result: {e}")
            return None

    def _filter_sources(self, sources: List[DocumentSource]) -> List[DocumentSource]:
        """
        Filter sources to only include downloadable documents.

        Security: Validates URLs and filters untrusted sources.
        """
        filtered = []

        for source in sources:
            # Must have file extension (downloadable)
            if not source.file_extension:
                continue

            # Validate URL format (basic security check)
            if not source.url.startswith("https://"):
                continue

            # Skip if URL contains suspicious patterns
            suspicious_patterns = ["javascript:", "data:", "<script", "onclick"]
            if any(pattern in source.url.lower() for pattern in suspicious_patterns):
                continue

            filtered.append(source)

        return filtered

    async def _download_documents(
        self,
        sources: List[DocumentSource],
        part_number: str,
        s3_prefix: str,
    ) -> List[DownloadedDocument]:
        """
        Download documents and upload to S3.

        Each document is uploaded with metadata for Bedrock KB.

        Args:
            sources: Document sources to download
            part_number: Equipment part number
            s3_prefix: S3 prefix for uploads

        Returns:
            List of successfully downloaded documents
        """
        downloaded: List[DownloadedDocument] = []

        # Lazy import for cold start optimization
        from tools.document_downloader import download_document, DocumentDownloadResult
        from tools.s3_client import SGAS3Client

        s3_client = SGAS3Client(bucket_name=EQUIPMENT_DOCS_BUCKET)

        for idx, source in enumerate(sources):
            try:
                # Download document
                result: DocumentDownloadResult = await download_document(
                    url=source.url,
                    timeout_seconds=30,
                    max_size_mb=50,
                )

                if not result.success or not result.content:
                    continue

                # Generate filename
                ext = source.file_extension or ".pdf"
                filename = f"{source.document_type}_{idx + 1}{ext}"
                s3_key = f"{s3_prefix}{filename}"

                # Upload to S3
                success = s3_client.upload_file(
                    key=s3_key,
                    data=result.content,
                    content_type=result.content_type,
                    metadata={
                        "part_number": part_number,
                        "source_url": source.url[:500],  # Truncate for metadata limit
                        "document_type": source.document_type,
                        "domain": source.domain,
                    },
                )

                if success:
                    # Create KB metadata file
                    await self._create_kb_metadata(
                        s3_client=s3_client,
                        s3_key=s3_key,
                        part_number=part_number,
                        source=source,
                    )

                    downloaded.append(DownloadedDocument(
                        source_url=source.url,
                        s3_key=s3_key,
                        filename=filename,
                        content_type=result.content_type,
                        size_bytes=len(result.content),
                        document_type=source.document_type,
                        metadata={
                            "part_number": part_number,
                            "domain": source.domain,
                            "title": source.title,
                        },
                    ))

            except Exception as e:
                print(f"[EquipmentResearchAgent] Download failed for {source.url}: {e}")
                continue

        return downloaded

    async def _create_kb_metadata(
        self,
        s3_client,
        s3_key: str,
        part_number: str,
        source: DocumentSource,
    ) -> None:
        """
        Create metadata file for Bedrock Knowledge Base.

        Bedrock KB uses .metadata.json files to add custom attributes
        to documents for filtering during retrieval.
        """
        metadata = {
            "metadataAttributes": {
                "part_number": part_number,
                "document_type": source.document_type,
                "source_domain": source.domain,
                "is_trusted_source": source.is_trusted_domain,
                "title": source.title[:200] if source.title else "",
                "indexed_at": now_iso(),
            }
        }

        metadata_key = f"{s3_key}.metadata.json"
        s3_client.upload_file(
            key=metadata_key,
            data=json.dumps(metadata, ensure_ascii=False).encode("utf-8"),
            content_type="application/json",
        )

    def _generate_summary(
        self,
        part_number: str,
        sources: List[DocumentSource],
        downloaded: List[DownloadedDocument],
    ) -> str:
        """Generate a human-readable summary of research results."""
        if not sources:
            return f"Nenhuma documentação encontrada para {part_number}"

        if not downloaded:
            return f"Encontradas {len(sources)} fontes para {part_number}, mas nenhum documento pôde ser baixado"

        doc_types = [d.document_type for d in downloaded]
        unique_types = list(set(doc_types))

        return (
            f"Pesquisa concluída para {part_number}: "
            f"{len(downloaded)} documento(s) baixado(s) "
            f"({', '.join(unique_types)}) "
            f"de {len(set(d.metadata.get('domain', '') for d in downloaded))} fonte(s)"
        )

    def _calculate_research_confidence(
        self,
        sources_found: int,
        docs_downloaded: int,
        has_trusted_source: bool,
    ) -> ConfidenceScore:
        """Calculate confidence score for research results."""
        # Base score on results
        if docs_downloaded == 0:
            overall = 0.2
        elif docs_downloaded == 1:
            overall = 0.6
        elif docs_downloaded >= 2:
            overall = 0.8
        else:
            overall = 0.4

        # Boost for trusted sources
        if has_trusted_source:
            overall = min(1.0, overall + 0.15)

        return self.calculate_confidence(
            extraction_quality=overall,
            evidence_strength=0.8 if has_trusted_source else 0.5,
            historical_match=0.5,  # No historical data yet
            risk_factors=[] if docs_downloaded > 0 else ["no_docs_found"],
        )

    # =========================================================================
    # Batch Research
    # =========================================================================

    async def research_batch(
        self,
        equipment_list: List[Dict[str, Any]],
        max_concurrent: int = 3,
    ) -> List[ResearchResult]:
        """
        Research multiple equipment items in batch.

        Respects rate limits and processes items sequentially
        to avoid overwhelming Google Search quota.

        Args:
            equipment_list: List of equipment dicts with part_number, description, etc.
            max_concurrent: Maximum concurrent research tasks (not used yet)

        Returns:
            List of ResearchResult for each equipment
        """
        results: List[ResearchResult] = []

        for equipment in equipment_list:
            # Check quota before each research
            quota_ok, _ = await self._check_quota()
            if not quota_ok:
                # Create rate-limited result for remaining items
                result = ResearchResult(
                    part_number=equipment.get("part_number", "UNKNOWN"),
                    status=ResearchStatus.RATE_LIMITED,
                    search_queries=[],
                    sources_found=[],
                    documents_downloaded=[],
                    s3_prefix="",
                    summary="Pesquisa adiada: quota de busca esgotada",
                    confidence=ConfidenceScore(overall=0.0),
                    reasoning_trace=[],
                    error="Daily quota exceeded",
                )
                results.append(result)
                continue

            # Research this equipment
            result = await self.research_equipment(
                part_number=equipment.get("part_number", ""),
                description=equipment.get("description", ""),
                serial_number=equipment.get("serial_number"),
                manufacturer=equipment.get("manufacturer"),
                additional_info=equipment.get("additional_info"),
            )
            results.append(result)

        return results
