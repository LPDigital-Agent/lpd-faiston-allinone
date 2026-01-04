# =============================================================================
# Intake Agent - Faiston SGA Inventory
# =============================================================================
# Agent for processing incoming materials via NF-e (Nota Fiscal Eletrônica).
#
# Features:
# - Upload and parse NF-e XML/PDF files
# - AI-assisted data extraction from PDFs
# - Automatic part number matching
# - Serial number detection
# - Entry creation with confidence scoring
# - HIL for new part numbers or low-confidence extractions
#
# Module: Gestao de Ativos -> Gestao de Estoque
# Model: Gemini 3.0 Pro (MANDATORY per CLAUDE.md)
#
# Human-in-the-Loop Matrix:
# - High confidence extraction (>80%): AUTONOMOUS with review
# - Low confidence extraction (<80%): HIL required
# - New part number detected: HIL required
# - High value item (>R$ 5000): HIL required
# =============================================================================

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

from .base_agent import BaseInventoryAgent, ConfidenceScore
from .utils import (
    EntityPrefix,
    MovementType,
    HILTaskType,
    HILTaskStatus,
    RiskLevel,
    generate_id,
    now_iso,
    now_yyyymm,
    log_agent_action,
    parse_json_safe,
    extract_json,
)


# =============================================================================
# Agent System Prompt
# =============================================================================

INTAKE_AGENT_INSTRUCTION = """
Voce e o IntakeAgent, agente de IA responsavel pela entrada de materiais
no sistema Faiston SGA (Sistema de Gestao de Ativos).

## Suas Responsabilidades

1. **Processar NF-e**: Ler e extrair dados de Notas Fiscais (XML ou PDF)
2. **Identificar Itens**: Mapear itens da NF para part numbers do cadastro
3. **Detectar Seriais**: Identificar numeros de serie nos itens
4. **Criar Entradas**: Registrar movimentacao de entrada no estoque
5. **Solicitar Aprovacao**: Quando necessario, criar tarefa HIL

## Regras de Negocio

### Processamento de NF-e
- XML e OBRIGATORIO para validacao fiscal
- PDF pode ser usado para informacoes complementares
- Chave de acesso (44 digitos) identifica a NF unicamente
- Data de emissao determina competencia

### Identificacao de Part Numbers
- Tentar match por codigo do fornecedor (cProd)
- Tentar match por descricao (xProd)
- Tentar match por NCM
- Se nao encontrar: criar tarefa HIL para cadastro

### Numeros de Serie
- Identificar seriais em descricao (SN:, SERIAL:, S/N, IMEI:)
- Quantidade de seriais deve bater com quantidade do item
- Seriais duplicados NAO sao permitidos

### Confidence Score
- > 90%: Entrada automatica, apenas revisao
- 80-90%: Entrada automatica com alerta
- < 80%: HIL obrigatorio
- Alto valor (> R$ 5000): HIL obrigatorio

## Formato de Resposta

Responda SEMPRE em JSON estruturado:
```json
{
  "action": "process_nf|validate_extraction|confirm_entry",
  "status": "success|pending_approval|error",
  "message": "Descricao da acao",
  "extraction": { ... },
  "confidence": { "overall": 0.95, "factors": [] }
}
```

## Contexto

Voce processa NF-e de fornecedores de equipamentos de TI e telecomunicacoes.
Os itens podem ser: switches, roteadores, access points, cabos, SFPs, etc.
Cada item pode ter numero de serie unico ou ser item de consumo (quantidade).
"""


# =============================================================================
# Entry Result Data Class
# =============================================================================


@dataclass
class EntryResult:
    """Result of an entry operation."""
    success: bool
    movement_id: Optional[str] = None
    nf_id: Optional[str] = None
    message: str = ""
    requires_hil: bool = False
    hil_task_id: Optional[str] = None
    confidence: Optional[ConfidenceScore] = None
    extraction: Optional[Dict[str, Any]] = None
    items_processed: int = 0
    items_pending: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "success": self.success,
            "message": self.message,
            "requires_hil": self.requires_hil,
            "items_processed": self.items_processed,
            "items_pending": self.items_pending,
        }
        if self.movement_id:
            result["movement_id"] = self.movement_id
        if self.nf_id:
            result["nf_id"] = self.nf_id
        if self.hil_task_id:
            result["hil_task_id"] = self.hil_task_id
        if self.confidence:
            result["confidence"] = self.confidence.to_dict()
        if self.extraction:
            result["extraction"] = self.extraction
        return result


# =============================================================================
# Intake Agent
# =============================================================================


class IntakeAgent(BaseInventoryAgent):
    """
    Agent for processing incoming materials via NF-e.

    Handles NF-e parsing, data extraction, part number matching,
    and entry creation with confidence scoring.
    """

    # High value threshold for HIL (R$)
    HIGH_VALUE_THRESHOLD = 5000.0

    # Minimum confidence for autonomous entry
    MIN_CONFIDENCE_AUTONOMOUS = 0.80

    def __init__(self):
        """Initialize the Intake Agent."""
        super().__init__(
            name="IntakeAgent",
            instruction=INTAKE_AGENT_INSTRUCTION,
            description="Processamento de entrada de materiais via NF-e",
        )
        # Lazy-loaded clients
        self._db_client = None
        self._s3_client = None
        self._nf_parser = None

    @property
    def db(self):
        """Lazy-load DynamoDB client."""
        if self._db_client is None:
            from tools.dynamodb_client import SGADynamoDBClient
            self._db_client = SGADynamoDBClient()
        return self._db_client

    @property
    def s3(self):
        """Lazy-load S3 client."""
        if self._s3_client is None:
            from tools.s3_client import SGAS3Client
            self._s3_client = SGAS3Client()
        return self._s3_client

    @property
    def nf_parser(self):
        """Lazy-load NF parser."""
        if self._nf_parser is None:
            from tools.nf_parser import NFParser
            self._nf_parser = NFParser()
        return self._nf_parser

    # =========================================================================
    # NF-e Processing
    # =========================================================================

    async def process_nf_upload(
        self,
        s3_key: str,
        file_type: str = "xml",
        project_id: str = "",
        destination_location_id: str = "ESTOQUE_CENTRAL",
        uploaded_by: str = "system",
    ) -> EntryResult:
        """
        Process an uploaded NF-e file (XML or PDF).

        Args:
            s3_key: S3 key of the uploaded file
            file_type: File type (xml or pdf)
            project_id: Project/client context
            destination_location_id: Where materials will go
            uploaded_by: User who uploaded

        Returns:
            EntryResult with extraction and status
        """
        log_agent_action(
            self.name, "process_nf_upload",
            entity_type="NF",
            status="started",
        )

        try:
            # 1. Download file from S3
            file_data = self.s3.download_file(s3_key)
            if not file_data:
                return EntryResult(
                    success=False,
                    message=f"Arquivo nao encontrado: {s3_key}",
                )

            # 2. Parse NF-e
            if file_type.lower() == "xml":
                extraction = self.nf_parser.parse_xml(
                    file_data.decode("utf-8")
                )
            else:
                # For PDF, use AI extraction
                extraction = await self._process_nf_pdf(file_data)

            if not extraction or extraction.get("confidence", 0) < 0.3:
                return EntryResult(
                    success=False,
                    message="Falha ao extrair dados da NF-e",
                    extraction=extraction,
                )

            # 3. Store extraction result in S3
            nf_id = extraction.get("chave_acesso", generate_id("NF"))
            self.s3.upload_nf_extraction(
                nf_id=nf_id,
                extraction=extraction,
            )

            # 4. Match items to part numbers
            matched_items, unmatched_items = await self._match_items_to_pn(
                extraction.get("items", [])
            )

            # 5. Calculate overall confidence
            confidence = self._calculate_extraction_confidence(
                extraction=extraction,
                matched_count=len(matched_items),
                total_count=len(extraction.get("items", [])),
            )

            # 6. Check if HIL required
            requires_hil = self._check_requires_hil(
                confidence=confidence,
                extraction=extraction,
                unmatched_items=unmatched_items,
            )

            # 7. Create pending entry record
            entry_id = generate_id("ENT")
            now = now_iso()

            entry_item = {
                "PK": f"{EntityPrefix.DOCUMENT}{entry_id}",
                "SK": "METADATA",
                "entity_type": "NF_ENTRY",
                "entry_id": entry_id,
                "nf_id": nf_id,
                "nf_numero": extraction.get("numero"),
                "nf_serie": extraction.get("serie"),
                "nf_chave": extraction.get("chave_acesso"),
                "emitente_cnpj": extraction.get("emitente", {}).get("cnpj"),
                "emitente_nome": extraction.get("emitente", {}).get("nome"),
                "destinatario_cnpj": extraction.get("destinatario", {}).get("cnpj"),
                "data_emissao": extraction.get("data_emissao"),
                "valor_total": extraction.get("valor_total"),
                "project_id": project_id,
                "destination_location_id": destination_location_id,
                "status": "PENDING_APPROVAL" if requires_hil else "PENDING_CONFIRMATION",
                "matched_items": matched_items,
                "unmatched_items": unmatched_items,
                "confidence_score": confidence.overall,
                "s3_xml_key": s3_key if file_type == "xml" else None,
                "s3_pdf_key": s3_key if file_type == "pdf" else None,
                "uploaded_by": uploaded_by,
                "created_at": now,
                # GSIs
                "GSI4_PK": f"STATUS#{'PENDING_APPROVAL' if requires_hil else 'PENDING_CONFIRMATION'}",
                "GSI4_SK": now,
                "GSI5_PK": f"DATE#{now_yyyymm()}",
                "GSI5_SK": f"ENTRY#{now}",
            }

            self.db.put_item(entry_item)

            # 8. Create HIL task if required
            hil_task_id = None
            if requires_hil:
                from tools.hil_workflow import HILWorkflowManager
                hil_manager = HILWorkflowManager()

                hil_task = await hil_manager.create_task(
                    task_type=HILTaskType.APPROVAL_ENTRY if unmatched_items else HILTaskType.REVIEW_ENTRY,
                    title=f"Revisar entrada NF-e: {extraction.get('numero', 'N/A')}",
                    description=self._format_entry_review_message(
                        extraction=extraction,
                        confidence=confidence,
                        matched_items=matched_items,
                        unmatched_items=unmatched_items,
                    ),
                    entity_type="NF_ENTRY",
                    entity_id=entry_id,
                    requested_by=uploaded_by,
                    payload=entry_item,
                    priority="HIGH" if unmatched_items else "MEDIUM",
                )
                hil_task_id = hil_task.get("task_id")

            log_agent_action(
                self.name, "process_nf_upload",
                entity_type="NF",
                entity_id=nf_id,
                status="completed",
            )

            return EntryResult(
                success=True,
                nf_id=nf_id,
                message="NF-e processada" + (
                    ", aguardando revisao" if requires_hil else ", pronta para confirmacao"
                ),
                requires_hil=requires_hil,
                hil_task_id=hil_task_id,
                confidence=confidence,
                extraction={
                    "nf_numero": extraction.get("numero"),
                    "emitente": extraction.get("emitente", {}).get("nome"),
                    "valor_total": extraction.get("valor_total"),
                    "total_items": len(extraction.get("items", [])),
                },
                items_processed=len(matched_items),
                items_pending=len(unmatched_items),
            )

        except Exception as e:
            log_agent_action(
                self.name, "process_nf_upload",
                entity_type="NF",
                status="failed",
            )
            return EntryResult(
                success=False,
                message=f"Erro ao processar NF-e: {str(e)}",
            )

    async def _process_nf_pdf(self, pdf_data: bytes) -> Dict[str, Any]:
        """
        Process NF-e PDF using AI extraction.

        Args:
            pdf_data: PDF file bytes

        Returns:
            Extraction dict
        """
        # Generate prompt for AI extraction
        prompt = self.nf_parser.get_pdf_extraction_prompt()

        # For PDF, we would use a vision model or OCR first
        # This is a simplified version - in production, use Gemini vision
        # or a dedicated OCR service

        log_agent_action(
            self.name, "_process_nf_pdf",
            status="started",
        )

        try:
            # Call the agent for PDF interpretation
            # Note: In production, this would send the PDF to a vision model
            response = await self.invoke(
                prompt=f"""
                Extraia os dados da NF-e do seguinte texto/imagem.
                {prompt}

                Formato de saida OBRIGATORIO: JSON conforme especificado.
                """,
                user_id="system",
                session_id=f"pdf_extraction_{generate_id('')}",
            )

            extraction = parse_json_safe(response)

            # Add source info
            extraction["source"] = "pdf_ai_extraction"
            extraction["confidence"] = extraction.get("confidence", 0.6)

            return extraction

        except Exception as e:
            log_agent_action(
                self.name, "_process_nf_pdf",
                status="failed",
            )
            return {
                "error": str(e),
                "confidence": 0.0,
                "source": "pdf_ai_extraction_failed",
            }

    async def _match_items_to_pn(
        self,
        nf_items: List[Dict[str, Any]],
    ) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Match NF-e items to existing part numbers.

        Args:
            nf_items: List of items from NF-e extraction

        Returns:
            Tuple of (matched_items, unmatched_items)
        """
        matched = []
        unmatched = []

        for item in nf_items:
            # Try different matching strategies
            pn_match = await self._find_part_number(item)

            if pn_match:
                matched.append({
                    **item,
                    "matched_pn": pn_match["part_number"],
                    "match_confidence": pn_match["confidence"],
                    "match_method": pn_match["method"],
                })
            else:
                unmatched.append({
                    **item,
                    "suggested_pn": self._suggest_part_number(item),
                })

        return matched, unmatched

    async def _find_part_number(
        self,
        item: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Find matching part number for an NF-e item.

        Tries multiple matching strategies:
        1. Exact match on supplier code (cProd)
        2. Fuzzy match on description (xProd)
        3. Match on NCM code

        Args:
            item: NF-e item dict

        Returns:
            Match info or None
        """
        # Strategy 1: Match by supplier code
        supplier_code = item.get("codigo")
        if supplier_code:
            pn = self._query_pn_by_supplier_code(supplier_code)
            if pn:
                return {
                    "part_number": pn["part_number"],
                    "confidence": 0.95,
                    "method": "supplier_code",
                }

        # Strategy 2: Match by description keywords
        description = item.get("descricao", "")
        if description:
            pn = await self._query_pn_by_description(description)
            if pn:
                return {
                    "part_number": pn["part_number"],
                    "confidence": pn.get("match_score", 0.7),
                    "method": "description_match",
                }

        # Strategy 3: Match by NCM
        ncm = item.get("ncm")
        if ncm:
            pn = self._query_pn_by_ncm(ncm)
            if pn:
                return {
                    "part_number": pn["part_number"],
                    "confidence": 0.6,
                    "method": "ncm_match",
                }

        return None

    def _query_pn_by_supplier_code(
        self,
        supplier_code: str,
    ) -> Optional[Dict[str, Any]]:
        """Query part number by supplier code."""
        # In production, this would query the database
        # For now, return None (no match)
        # The actual implementation would be:
        # return self.db.query_gsi(
        #     index_name="GSI1",  # Supplier code index
        #     pk=f"SUPPLIER_CODE#{supplier_code}",
        # )
        return None

    async def _query_pn_by_description(
        self,
        description: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Query part number by description using AI matching.

        Uses the agent to find best match from catalog.
        """
        # In production, this would:
        # 1. Query part numbers with similar keywords
        # 2. Use AI to rank matches
        # For now, return None
        return None

    def _query_pn_by_ncm(
        self,
        ncm: str,
    ) -> Optional[Dict[str, Any]]:
        """Query part number by NCM code."""
        # In production, this would query by NCM
        return None

    def _suggest_part_number(self, item: Dict[str, Any]) -> str:
        """
        Suggest a part number code for a new item.

        Based on description and category.
        """
        desc = item.get("descricao", "").upper()

        # Simple category-based suggestions
        if "SWITCH" in desc:
            return f"SW-{item.get('codigo', 'NEW')[:10]}"
        elif "ROUTER" in desc or "ROTEADOR" in desc:
            return f"RT-{item.get('codigo', 'NEW')[:10]}"
        elif "ACCESS POINT" in desc or "AP" in desc:
            return f"AP-{item.get('codigo', 'NEW')[:10]}"
        elif "CABO" in desc or "CABLE" in desc:
            return f"CBL-{item.get('codigo', 'NEW')[:10]}"
        elif "SFP" in desc:
            return f"SFP-{item.get('codigo', 'NEW')[:10]}"
        else:
            return f"MISC-{item.get('codigo', 'NEW')[:10]}"

    def _calculate_extraction_confidence(
        self,
        extraction: Dict[str, Any],
        matched_count: int,
        total_count: int,
    ) -> ConfidenceScore:
        """
        Calculate confidence score for NF-e extraction.

        Args:
            extraction: Extracted NF-e data
            matched_count: Number of items matched to PN
            total_count: Total items in NF-e

        Returns:
            ConfidenceScore
        """
        # Extraction quality from parser
        extraction_quality = extraction.get("confidence", 0.5)

        # Evidence strength (match ratio)
        match_ratio = matched_count / total_count if total_count > 0 else 0
        evidence_strength = match_ratio

        # Historical match (use default for now)
        historical_match = 0.8

        # Risk factors
        risk_factors = []

        if extraction_quality < 0.8:
            risk_factors.append("low_extraction_quality")

        if match_ratio < 0.5:
            risk_factors.append("many_unmatched_items")

        if extraction.get("valor_total", 0) > self.HIGH_VALUE_THRESHOLD:
            risk_factors.append("high_value_entry")

        if not extraction.get("chave_acesso"):
            risk_factors.append("missing_access_key")

        return self.calculate_confidence(
            extraction_quality=extraction_quality,
            evidence_strength=evidence_strength,
            historical_match=historical_match,
            risk_factors=risk_factors,
            base_risk=RiskLevel.MEDIUM,
        )

    def _check_requires_hil(
        self,
        confidence: ConfidenceScore,
        extraction: Dict[str, Any],
        unmatched_items: List[Dict[str, Any]],
    ) -> bool:
        """
        Check if HIL is required for this entry.

        Args:
            confidence: Calculated confidence
            extraction: NF-e extraction
            unmatched_items: Items without PN match

        Returns:
            True if HIL required
        """
        # Always HIL if there are unmatched items
        if unmatched_items:
            return True

        # HIL if confidence below threshold
        if confidence.overall < self.MIN_CONFIDENCE_AUTONOMOUS:
            return True

        # HIL for high value
        if extraction.get("valor_total", 0) > self.HIGH_VALUE_THRESHOLD:
            return True

        # HIL if confidence scoring requires it
        if confidence.requires_hil:
            return True

        return False

    def _format_entry_review_message(
        self,
        extraction: Dict[str, Any],
        confidence: ConfidenceScore,
        matched_items: List[Dict[str, Any]],
        unmatched_items: List[Dict[str, Any]],
    ) -> str:
        """
        Format message for HIL entry review task.
        """
        message = f"""
## Revisao de Entrada NF-e

### Dados da Nota
- **Numero**: {extraction.get('numero', 'N/A')} / Serie: {extraction.get('serie', 'N/A')}
- **Chave de Acesso**: {extraction.get('chave_acesso', 'N/A')}
- **Emitente**: {extraction.get('emitente', {}).get('nome', 'N/A')}
- **CNPJ Emitente**: {extraction.get('emitente', {}).get('cnpj', 'N/A')}
- **Data Emissao**: {extraction.get('data_emissao', 'N/A')}
- **Valor Total**: R$ {extraction.get('valor_total', 0):,.2f}

### Confianca da Extracao
- **Score Geral**: {confidence.overall:.0%}
- **Nivel de Risco**: {confidence.risk_level.upper()}
- **Fatores**: {', '.join(confidence.factors) if confidence.factors else 'Nenhum'}

### Itens Identificados ({len(matched_items)})
"""
        for item in matched_items[:5]:  # Show first 5
            message += f"- {item.get('descricao', 'N/A')[:50]} -> **{item.get('matched_pn')}** ({item.get('match_confidence', 0):.0%})\n"

        if len(matched_items) > 5:
            message += f"- ... e mais {len(matched_items) - 5} itens\n"

        if unmatched_items:
            message += f"""
### Itens NAO Identificados ({len(unmatched_items)}) - REQUER ACAO
"""
            for item in unmatched_items[:5]:
                message += f"- {item.get('descricao', 'N/A')[:50]} (Sugestao: **{item.get('suggested_pn')}**)\n"

            if len(unmatched_items) > 5:
                message += f"- ... e mais {len(unmatched_items) - 5} itens\n"

        message += """
### Acoes Disponiveis
- **Aprovar**: Confirmar entrada dos itens identificados
- **Rejeitar**: Cancelar esta entrada
- **Modificar**: Ajustar mapeamento de part numbers
"""
        return message

    # =========================================================================
    # Entry Confirmation
    # =========================================================================

    async def confirm_entry(
        self,
        entry_id: str,
        confirmed_by: str,
        item_mappings: Optional[Dict[str, str]] = None,
        notes: Optional[str] = None,
    ) -> EntryResult:
        """
        Confirm a pending entry and create movements.

        Args:
            entry_id: Entry ID to confirm
            confirmed_by: User confirming
            item_mappings: Optional manual PN mappings for unmatched items
            notes: Additional notes

        Returns:
            EntryResult with created movements
        """
        log_agent_action(
            self.name, "confirm_entry",
            entity_type="NF_ENTRY",
            entity_id=entry_id,
            status="started",
        )

        try:
            # 1. Get entry record
            entry = self.db.get_item(
                pk=f"{EntityPrefix.DOCUMENT}{entry_id}",
                sk="METADATA",
            )

            if not entry:
                return EntryResult(
                    success=False,
                    message=f"Entrada {entry_id} nao encontrada",
                )

            if entry.get("status") not in ["PENDING_CONFIRMATION", "PENDING_APPROVAL"]:
                return EntryResult(
                    success=False,
                    message=f"Entrada nao pode ser confirmada. Status: {entry.get('status')}",
                )

            # 2. Apply manual mappings if provided
            matched_items = entry.get("matched_items", [])
            unmatched_items = entry.get("unmatched_items", [])

            if item_mappings:
                for item in unmatched_items[:]:
                    item_key = item.get("codigo") or item.get("descricao", "")[:20]
                    if item_key in item_mappings:
                        item["matched_pn"] = item_mappings[item_key]
                        item["match_method"] = "manual"
                        item["match_confidence"] = 1.0
                        matched_items.append(item)
                        unmatched_items.remove(item)

            # 3. Check if still have unmatched items
            if unmatched_items:
                return EntryResult(
                    success=False,
                    message=f"Ainda existem {len(unmatched_items)} itens sem mapeamento",
                    items_pending=len(unmatched_items),
                )

            # 4. Create movement for each item
            now = now_iso()
            movement_ids = []
            total_items = 0

            for item in matched_items:
                movement_id = generate_id("ENT")

                # Create entry movement
                movement_item = {
                    "PK": f"{EntityPrefix.MOVEMENT}{movement_id}",
                    "SK": "METADATA",
                    "entity_type": "MOVEMENT",
                    "movement_id": movement_id,
                    "movement_type": MovementType.ENTRY,
                    "part_number": item["matched_pn"],
                    "quantity": item.get("quantidade", 1),
                    "serial_numbers": item.get("seriais", []),
                    "unit_value": item.get("valor_unitario", 0),
                    "total_value": item.get("valor_total", 0),
                    "destination_location_id": entry.get("destination_location_id", "ESTOQUE_CENTRAL"),
                    "project_id": entry.get("project_id", ""),
                    "nf_entry_id": entry_id,
                    "nf_numero": entry.get("nf_numero"),
                    "nf_item_codigo": item.get("codigo"),
                    "processed_by": confirmed_by,
                    "notes": notes,
                    "created_at": now,
                    # GSIs
                    "GSI3_PK": f"{EntityPrefix.PROJECT}{entry.get('project_id', 'UNASSIGNED')}",
                    "GSI3_SK": f"MOVEMENT#{now}",
                    "GSI5_PK": f"DATE#{now_yyyymm()}",
                    "GSI5_SK": f"ENTRY#{now}",
                }

                self.db.put_item(movement_item)
                movement_ids.append(movement_id)

                # Update balance
                self.db.update_balance(
                    part_number=item["matched_pn"],
                    location_id=entry.get("destination_location_id", "ESTOQUE_CENTRAL"),
                    project_id=entry.get("project_id", "UNASSIGNED"),
                    quantity_delta=item.get("quantidade", 1),
                    reserved_delta=0,
                )

                # Create/update assets if serial numbers
                for serial in item.get("seriais", []):
                    await self._create_or_update_asset(
                        serial_number=serial,
                        part_number=item["matched_pn"],
                        location_id=entry.get("destination_location_id", "ESTOQUE_CENTRAL"),
                        project_id=entry.get("project_id", ""),
                        movement_id=movement_id,
                        nf_entry_id=entry_id,
                    )

                total_items += item.get("quantidade", 1)

            # 5. Update entry status
            self.db.update_item(
                pk=f"{EntityPrefix.DOCUMENT}{entry_id}",
                sk="METADATA",
                updates={
                    "status": "COMPLETED",
                    "confirmed_at": now,
                    "confirmed_by": confirmed_by,
                    "confirmation_notes": notes,
                    "movement_ids": movement_ids,
                    "GSI4_PK": "STATUS#COMPLETED",
                    "GSI4_SK": now,
                },
            )

            # 6. Log to audit
            from tools.dynamodb_client import SGAAuditLogger
            audit = SGAAuditLogger()
            audit.log_action(
                action="NF_ENTRY_CONFIRMED",
                entity_type="NF_ENTRY",
                entity_id=entry_id,
                actor=confirmed_by,
                details={
                    "movements_created": len(movement_ids),
                    "total_items": total_items,
                },
            )

            log_agent_action(
                self.name, "confirm_entry",
                entity_type="NF_ENTRY",
                entity_id=entry_id,
                status="completed",
            )

            return EntryResult(
                success=True,
                nf_id=entry.get("nf_id"),
                message=f"Entrada confirmada. {total_items} itens processados em {len(movement_ids)} movimentacoes.",
                items_processed=total_items,
            )

        except Exception as e:
            log_agent_action(
                self.name, "confirm_entry",
                entity_type="NF_ENTRY",
                entity_id=entry_id,
                status="failed",
            )
            return EntryResult(
                success=False,
                message=f"Erro ao confirmar entrada: {str(e)}",
            )

    async def _create_or_update_asset(
        self,
        serial_number: str,
        part_number: str,
        location_id: str,
        project_id: str,
        movement_id: str,
        nf_entry_id: str,
    ) -> None:
        """
        Create or update asset record for serialized item.
        """
        now = now_iso()

        # Check if asset already exists
        existing = self.db.get_asset_by_serial(serial_number)

        if existing:
            # Update existing asset
            self.db.update_item(
                pk=existing["PK"],
                sk=existing["SK"],
                updates={
                    "location_id": location_id,
                    "status": "IN_STOCK",
                    "last_movement_id": movement_id,
                    "updated_at": now,
                    "GSI2_PK": f"{EntityPrefix.LOCATION}{location_id}",
                    "GSI2_SK": f"ASSET#{serial_number}",
                    "GSI4_PK": "STATUS#IN_STOCK",
                    "GSI4_SK": now,
                },
            )
        else:
            # Create new asset
            asset_id = generate_id("AST")
            asset_item = {
                "PK": f"{EntityPrefix.ASSET}{asset_id}",
                "SK": "METADATA",
                "entity_type": "ASSET",
                "asset_id": asset_id,
                "serial_number": serial_number,
                "part_number": part_number,
                "location_id": location_id,
                "project_id": project_id,
                "status": "IN_STOCK",
                "acquisition_type": "NF_ENTRY",
                "acquisition_ref": nf_entry_id,
                "last_movement_id": movement_id,
                "created_at": now,
                "updated_at": now,
                # GSIs
                "GSI1_PK": f"SERIAL#{serial_number}",
                "GSI1_SK": "METADATA",
                "GSI2_PK": f"{EntityPrefix.LOCATION}{location_id}",
                "GSI2_SK": f"ASSET#{serial_number}",
                "GSI3_PK": f"{EntityPrefix.PROJECT}{project_id}" if project_id else "PROJECT#UNASSIGNED",
                "GSI3_SK": f"ASSET#{now}",
                "GSI4_PK": "STATUS#IN_STOCK",
                "GSI4_SK": now,
            }
            self.db.put_item(asset_item)

    # =========================================================================
    # Presigned URL Generation
    # =========================================================================

    def get_upload_url(
        self,
        filename: str,
        content_type: str = "application/xml",
    ) -> Dict[str, Any]:
        """
        Generate presigned URL for NF-e upload.

        Args:
            filename: Original filename
            content_type: MIME type

        Returns:
            Dict with upload_url and key
        """
        # Generate temp path
        key = self.s3.get_temp_path(filename)

        return self.s3.generate_upload_url(
            key=key,
            content_type=content_type,
            expires_in=3600,
        )
