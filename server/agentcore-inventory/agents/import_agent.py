# =============================================================================
# Import Agent - Faiston SGA Inventory
# =============================================================================
# Agent for bulk importing inventory data from CSV/Excel files.
#
# Features:
# - Parse CSV/Excel files with auto-column detection
# - AI-assisted part number matching for all rows
# - Validation and preview before import
# - Batch movement creation
# - Progress tracking for large imports
#
# Module: Gestao de Ativos -> Gestao de Estoque
# Model: Gemini 3.0 Pro (MANDATORY per CLAUDE.md)
#
# Human-in-the-Loop Matrix:
# - All PNs matched (>80% confidence): AUTONOMOUS import
# - Some PNs unmatched: HIL for PN mapping
# - High value total (>R$ 50000): HIL required
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
    HILAssignedRole,
    EntryStatus,
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

IMPORT_AGENT_INSTRUCTION = """
Voce e o ImportAgent, agente de IA responsavel pela importacao em massa
de dados de inventario no sistema Faiston SGA.

## Suas Responsabilidades

1. **Processar Arquivos**: Ler e validar CSV/Excel de importacao
2. **Mapear Colunas**: Identificar correspondencia entre colunas do arquivo e campos do sistema
3. **Encontrar Part Numbers**: Para cada linha, tentar match com PN cadastrado
4. **Validar Dados**: Verificar obrigatoriedade, formato, duplicatas
5. **Criar Movimentacoes**: Em lote, criar entradas de estoque

## Regras de Negocio

### Mapeamento de Colunas
- Colunas obrigatorias: part_number (ou descricao), quantity
- Colunas opcionais: serial, location, project, supplier_code, unit_cost, ncm
- Auto-detectar delimitador (virgula, ponto-e-virgula, tab)
- Suportar encoding UTF-8 e Latin-1

### Identificacao de Part Numbers
1. Tentar match por codigo do fornecedor (supplier_code)
2. Tentar match por descricao usando AI
3. Tentar match por NCM (categoria)
4. Se nao encontrar: marcar para revisao

### Validacao
- Quantidade deve ser numerica positiva
- Seriais nao podem duplicar (no arquivo ou no sistema)
- Location deve existir no cadastro
- Project deve existir no cadastro (ou deixar pendente)

### Confidence Score por Linha
- PN match exato (supplier_code): 95%
- PN match por descricao AI: 50-85%
- PN match por NCM: 60%
- Sem match: 0% (requer mapping manual)

### Confidence Score Geral
- 100% linhas matched: overall 95%
- 80%+ linhas matched: overall = % matched
- <80% linhas matched: HIL obrigatorio

## Formato de Resposta

Responda SEMPRE em JSON estruturado:
```json
{
  "action": "preview_import|validate_mapping|execute_import",
  "status": "success|pending_approval|error",
  "message": "Descricao da acao",
  "preview": { ... },
  "import_result": { ... },
  "confidence": { "overall": 0.95, "factors": [] }
}
```

## Contexto

Voce opera de forma autonoma quando a confianca e alta,
mas solicita Human-in-the-Loop quando necessario.
Sempre priorize a integridade dos dados sobre velocidade.
"""


# =============================================================================
# Import Agent Class
# =============================================================================

class ImportAgent(BaseInventoryAgent):
    """
    Agent for bulk importing inventory data from CSV/Excel files.

    Uses AI-powered part number matching to automatically map
    imported rows to existing part numbers in the system.

    Implements autonomous decisions with HIL escalation for
    uncertain matches or high-value imports.
    """

    def __init__(self):
        super().__init__(
            name="ImportAgent",
            instruction=IMPORT_AGENT_INSTRUCTION,
            description="Agent for bulk importing inventory data from CSV/Excel files",
        )

        # Lazy import to avoid cold start overhead
        self.csv_parser = None
        self.db = None

    def _ensure_tools(self):
        """Lazy-load tools to minimize cold start time."""
        if self.csv_parser is None:
            from ..tools.csv_parser import (
                parse_import_file,
                preview_to_dict,
                extract_all_rows,
            )
            self.csv_parser = {
                "parse": parse_import_file,
                "to_dict": preview_to_dict,
                "extract_all": extract_all_rows,
            }

        if self.db is None:
            from ..tools.dynamodb_client import SGADynamoDBClient
            self.db = SGADynamoDBClient()

    # =========================================================================
    # Public Actions
    # =========================================================================

    async def preview_import(
        self,
        file_content: bytes,
        filename: str,
        project_id: Optional[str] = None,
        destination_location_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Preview an import file before processing.

        Parses the file, detects column mappings, and attempts
        to match each row to existing part numbers.

        Args:
            file_content: Raw file bytes
            filename: Original filename (for type detection)
            project_id: Optional project to assign all items
            destination_location_id: Optional destination location

        Returns:
            Preview with column mappings, matched rows, and stats
        """
        self._ensure_tools()
        log_agent_action(self.name, "preview_import", {"filename": filename})

        try:
            # Parse file
            preview = self.csv_parser["parse"](file_content, filename, max_preview_rows=20)

            # Try to match part numbers for preview rows
            matched_rows = []
            unmatched_rows = []
            total_quantity = 0.0

            for row in preview.preview_rows:
                match_result = await self._match_row_to_pn(row.mapped_data)

                row_info = {
                    "row_number": row.row_number,
                    "mapped_data": row.mapped_data,
                    "validation_errors": row.validation_errors,
                    "pn_match": match_result.get("pn_match"),
                    "match_confidence": match_result.get("confidence", 0.0),
                    "match_method": match_result.get("method", "none"),
                }

                if match_result.get("pn_match"):
                    matched_rows.append(row_info)
                else:
                    unmatched_rows.append(row_info)

                # Sum quantity
                qty_str = row.mapped_data.get("quantity", "0")
                try:
                    total_quantity += float(qty_str.replace(",", "."))
                except ValueError:
                    pass

            # Calculate confidence
            match_rate = len(matched_rows) / max(len(preview.preview_rows), 1)
            confidence = self._calculate_import_confidence(
                match_rate=match_rate,
                total_rows=preview.total_rows,
                total_quantity=total_quantity,
            )

            # Generate import ID
            import_id = generate_id("IMP")

            return {
                "success": True,
                "import_id": import_id,
                "filename": filename,
                "file_type": preview.file_type.value,
                "total_rows": preview.total_rows,
                "column_mappings": [
                    {
                        "file_column": m.file_column,
                        "target_field": m.target_field,
                        "confidence": m.confidence,
                        "sample_values": m.sample_values,
                    }
                    for m in preview.column_mappings
                ],
                "unmapped_columns": preview.unmapped_columns,
                "matched_rows": matched_rows,
                "unmatched_rows": unmatched_rows,
                "stats": {
                    "preview_rows_shown": len(preview.preview_rows),
                    "matched_count": len(matched_rows),
                    "unmatched_count": len(unmatched_rows),
                    "match_rate": round(match_rate * 100, 1),
                    "total_quantity": total_quantity,
                },
                "confidence_score": confidence.to_dict(),
                "requires_review": confidence.requires_hil,
                "project_id": project_id,
                "destination_location_id": destination_location_id,
            }

        except Exception as e:
            log_agent_action(self.name, "preview_import_error", {"error": str(e)})
            return {
                "success": False,
                "error": str(e),
                "message": f"Erro ao processar arquivo: {e}",
            }

    async def execute_import(
        self,
        import_id: str,
        file_content: bytes,
        filename: str,
        column_mappings: List[Dict[str, str]],
        pn_overrides: Optional[Dict[int, str]] = None,
        project_id: Optional[str] = None,
        destination_location_id: Optional[str] = None,
        operator_id: str = "system",
    ) -> Dict[str, Any]:
        """
        Execute the import after preview/confirmation.

        Creates entry movements for all valid rows.

        Args:
            import_id: Import session ID
            file_content: Raw file bytes
            filename: Original filename
            column_mappings: Confirmed column mappings from preview
            pn_overrides: Manual PN assignments {row_number: pn_id}
            project_id: Project to assign all items
            destination_location_id: Destination location
            operator_id: User executing the import

        Returns:
            Import result with created movements
        """
        self._ensure_tools()
        log_agent_action(self.name, "execute_import", {
            "import_id": import_id,
            "filename": filename,
        })

        pn_overrides = pn_overrides or {}

        try:
            # Extract all rows
            all_rows = self.csv_parser["extract_all"](
                file_content, filename, column_mappings
            )

            created_movements = []
            failed_rows = []
            skipped_rows = []

            for i, row_data in enumerate(all_rows):
                row_number = i + 2  # 1-based + header

                try:
                    # Check for manual override
                    if row_number in pn_overrides:
                        pn_id = pn_overrides[row_number]
                        pn = self.db.get_item(f"{EntityPrefix.PART_NUMBER}{pn_id}")
                    else:
                        # Auto-match PN
                        match_result = await self._match_row_to_pn(row_data)
                        pn = match_result.get("pn_match")

                    if not pn:
                        skipped_rows.append({
                            "row_number": row_number,
                            "reason": "Part number nao encontrado",
                            "data": row_data,
                        })
                        continue

                    # Parse quantity
                    qty_str = row_data.get("quantity", "0")
                    try:
                        quantity = float(qty_str.replace(",", "."))
                    except ValueError:
                        failed_rows.append({
                            "row_number": row_number,
                            "reason": f"Quantidade invalida: {qty_str}",
                            "data": row_data,
                        })
                        continue

                    if quantity <= 0:
                        failed_rows.append({
                            "row_number": row_number,
                            "reason": "Quantidade deve ser maior que zero",
                            "data": row_data,
                        })
                        continue

                    # Create movement
                    movement = self._create_import_movement(
                        pn=pn,
                        quantity=quantity,
                        serial=row_data.get("serial"),
                        location_id=destination_location_id or row_data.get("location"),
                        project_id=project_id or row_data.get("project"),
                        unit_cost=row_data.get("unit_cost"),
                        import_id=import_id,
                        operator_id=operator_id,
                    )

                    created_movements.append({
                        "row_number": row_number,
                        "movement_id": movement["movement_id"],
                        "pn_id": pn["pn_id"],
                        "pn_number": pn.get("pn_number", ""),
                        "quantity": quantity,
                    })

                except Exception as row_error:
                    failed_rows.append({
                        "row_number": row_number,
                        "reason": str(row_error),
                        "data": row_data,
                    })

            # Calculate final stats
            total_rows = len(all_rows)
            success_rate = len(created_movements) / max(total_rows, 1)

            return {
                "success": True,
                "import_id": import_id,
                "total_rows": total_rows,
                "created_count": len(created_movements),
                "failed_count": len(failed_rows),
                "skipped_count": len(skipped_rows),
                "success_rate": round(success_rate * 100, 1),
                "created_movements": created_movements,
                "failed_rows": failed_rows,
                "skipped_rows": skipped_rows,
                "message": (
                    f"Importacao concluida: {len(created_movements)}/{total_rows} "
                    f"itens importados com sucesso"
                ),
            }

        except Exception as e:
            log_agent_action(self.name, "execute_import_error", {"error": str(e)})
            return {
                "success": False,
                "error": str(e),
                "message": f"Erro na importacao: {e}",
            }

    async def validate_pn_mapping(
        self,
        description: str,
        suggested_pn_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate a part number mapping suggestion.

        Used by operator to confirm or override AI suggestions.

        Args:
            description: Item description from file
            suggested_pn_id: Optional suggested PN to validate

        Returns:
            Validation result with alternative suggestions
        """
        self._ensure_tools()
        log_agent_action(self.name, "validate_pn_mapping", {"description": description})

        try:
            # Get suggested PN details
            suggested_pn = None
            if suggested_pn_id:
                suggested_pn = self.db.get_item(
                    f"{EntityPrefix.PART_NUMBER}{suggested_pn_id}"
                )

            # Search for alternatives using AI
            match_result = await self._match_row_to_pn({
                "description": description,
            })

            # Get more alternatives by keyword search
            keywords = self._extract_keywords(description)
            alternatives = self.db.search_pn_by_keywords(keywords, limit=5)

            return {
                "success": True,
                "description": description,
                "suggested_pn": suggested_pn,
                "ai_match": match_result.get("pn_match"),
                "ai_confidence": match_result.get("confidence", 0.0),
                "alternatives": alternatives,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # Private Helpers
    # =========================================================================

    async def _match_row_to_pn(
        self,
        row_data: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Try to match a row to an existing part number.

        Attempts multiple strategies in order of confidence.

        Args:
            row_data: Mapped row data

        Returns:
            Match result with pn_match, confidence, method
        """
        # 1. Try supplier code (highest confidence)
        supplier_code = row_data.get("supplier_code", "").strip()
        if supplier_code:
            pn = self.db.query_pn_by_supplier_code(supplier_code)
            if pn:
                return {
                    "pn_match": pn,
                    "confidence": 0.95,
                    "method": "supplier_code",
                }

        # 2. Try description match with AI
        description = row_data.get("description", "").strip()
        part_number_col = row_data.get("part_number", "").strip()

        # Combine description and part_number column for better matching
        search_text = f"{part_number_col} {description}".strip()

        if search_text:
            pn = await self._match_by_description(search_text)
            if pn:
                return {
                    "pn_match": pn["pn"],
                    "confidence": pn["confidence"],
                    "method": "description_ai",
                }

        # 3. Try NCM category (lowest confidence)
        ncm = row_data.get("ncm", "").strip()
        if ncm:
            matches = self.db.query_pn_by_ncm(ncm, limit=1)
            if matches:
                return {
                    "pn_match": matches[0],
                    "confidence": 0.60,
                    "method": "ncm",
                }

        return {
            "pn_match": None,
            "confidence": 0.0,
            "method": "none",
        }

    async def _match_by_description(
        self,
        description: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Match description using AI-powered ranking.

        Args:
            description: Item description to match

        Returns:
            Dict with pn and confidence, or None
        """
        keywords = self._extract_keywords(description)

        if not keywords:
            return None

        # Search for candidates
        candidates = self.db.search_pn_by_keywords(keywords, limit=10)

        if not candidates:
            return None

        # Use AI to rank candidates
        best_match = await self._rank_candidates_with_ai(description, candidates)

        return best_match

    def _extract_keywords(self, description: str) -> List[str]:
        """Extract meaningful keywords from description."""
        # Portuguese stopwords
        stopwords = {
            "de", "da", "do", "das", "dos", "em", "para", "com", "sem",
            "por", "que", "uma", "um", "e", "ou", "a", "o", "as", "os",
            "na", "no", "nas", "nos", "ao", "aos", "se", "nao", "sim",
        }

        # Tokenize and filter
        words = description.lower().split()
        keywords = [
            w for w in words
            if len(w) > 2 and w not in stopwords and w.isalnum()
        ]

        # Return unique keywords, max 5
        seen = set()
        unique = []
        for k in keywords:
            if k not in seen:
                seen.add(k)
                unique.append(k)
                if len(unique) >= 5:
                    break

        return unique

    async def _rank_candidates_with_ai(
        self,
        target_description: str,
        candidates: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Use Gemini AI to rank candidate part numbers.

        Args:
            target_description: Description to match
            candidates: List of candidate PNs from database

        Returns:
            Best match with confidence, or None
        """
        if not candidates:
            return None

        from google import genai
        from google.genai import types

        # Build prompt
        candidates_text = "\n".join([
            f"{i+1}. [{c.get('pn_id', '')}] {c.get('pn_number', '')} - {c.get('description', '')}"
            for i, c in enumerate(candidates)
        ])

        prompt = f"""Analise a descricao do item e encontre o melhor match entre os candidatos.

DESCRICAO DO ITEM:
{target_description}

CANDIDATOS:
{candidates_text}

Responda APENAS com JSON:
{{
  "best_match_index": <numero 1-based do melhor candidato ou 0 se nenhum match>,
  "match_score": <0.0 a 1.0 indicando confianca no match>,
  "reasoning": "<breve explicacao>"
}}
"""

        try:
            client = genai.Client()

            response = client.models.generate_content(
                model="gemini-3-pro-preview",
                contents=[types.Part.from_text(prompt)],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=256,
                ),
            )

            result = parse_json_safe(response.text)

            if result and result.get("best_match_index", 0) > 0:
                idx = result["best_match_index"] - 1

                if 0 <= idx < len(candidates):
                    # Cap confidence between 0.5 and 0.85 for AI matches
                    confidence = max(0.5, min(0.85, result.get("match_score", 0.7)))

                    return {
                        "pn": candidates[idx],
                        "confidence": confidence,
                        "reasoning": result.get("reasoning", ""),
                    }

        except Exception as e:
            log_agent_action(self.name, "_rank_candidates_with_ai_error", {"error": str(e)})

        return None

    def _calculate_import_confidence(
        self,
        match_rate: float,
        total_rows: int,
        total_quantity: float,
    ) -> ConfidenceScore:
        """
        Calculate overall import confidence.

        Args:
            match_rate: Percentage of rows with PN matches
            total_rows: Total number of rows
            total_quantity: Sum of all quantities

        Returns:
            ConfidenceScore for the import
        """
        factors = []

        # Base confidence from match rate
        overall = match_rate * 0.95

        if match_rate >= 0.9:
            factors.append("Alto match rate (>90%)")
        elif match_rate >= 0.7:
            factors.append(f"Match rate medio ({match_rate*100:.0f}%)")
        else:
            factors.append(f"Baixo match rate ({match_rate*100:.0f}%)")

        # Penalize large imports slightly
        if total_rows > 100:
            overall *= 0.95
            factors.append(f"Import grande ({total_rows} linhas)")

        # High value check
        risk_level = RiskLevel.LOW
        if total_quantity > 1000:
            risk_level = RiskLevel.MEDIUM
            factors.append(f"Volume alto ({total_quantity:.0f} unidades)")
        if total_quantity > 5000:
            risk_level = RiskLevel.HIGH
            factors.append("Volume muito alto - requer aprovacao")

        return ConfidenceScore(
            overall=overall,
            extraction_quality=match_rate,
            evidence_strength=0.9 if match_rate > 0.8 else 0.6,
            historical_match=0.8,
            risk_level=risk_level,
            factors=factors,
        )

    def _create_import_movement(
        self,
        pn: Dict[str, Any],
        quantity: float,
        serial: Optional[str],
        location_id: Optional[str],
        project_id: Optional[str],
        unit_cost: Optional[str],
        import_id: str,
        operator_id: str,
    ) -> Dict[str, Any]:
        """
        Create an entry movement for an imported row.

        Args:
            pn: Part number from database
            quantity: Quantity to add
            serial: Optional serial number
            location_id: Destination location
            project_id: Associated project
            unit_cost: Optional unit cost
            import_id: Parent import ID
            operator_id: User creating the movement

        Returns:
            Created movement record
        """
        movement_id = generate_id("MV")
        timestamp = now_iso()
        yyyymm = now_yyyymm()

        # Parse unit cost
        cost = 0.0
        if unit_cost:
            try:
                cost = float(str(unit_cost).replace(",", "."))
            except ValueError:
                pass

        movement = {
            "PK": f"{EntityPrefix.MOVEMENT}{movement_id}",
            "SK": timestamp,
            "GSI1PK": f"PN#{pn.get('pn_id', '')}",
            "GSI1SK": timestamp,
            "GSI2PK": f"YYYYMM#{yyyymm}",
            "GSI2SK": f"ENTRY#{timestamp}",
            "movement_id": movement_id,
            "movement_type": MovementType.ENTRY,
            "pn_id": pn.get("pn_id", ""),
            "pn_number": pn.get("pn_number", ""),
            "description": pn.get("description", ""),
            "quantity": int(quantity),
            "serial_number": serial or "",
            "location_id": location_id or "01",  # Default to depot 01
            "project_id": project_id or "",
            "unit_cost": cost,
            "total_cost": cost * quantity,
            "source": "IMPORT",
            "source_reference": import_id,
            "operator_id": operator_id,
            "status": "COMPLETED",
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        # Save to DynamoDB
        self.db.put_item(movement)

        # Update balance
        self._update_balance(
            pn_id=pn.get("pn_id", ""),
            location_id=location_id or "01",
            delta=int(quantity),
        )

        return movement

    def _update_balance(
        self,
        pn_id: str,
        location_id: str,
        delta: int,
    ) -> None:
        """
        Update inventory balance for a PN at a location.

        Args:
            pn_id: Part number ID
            location_id: Location ID
            delta: Quantity change (positive for entry)
        """
        balance_pk = f"{EntityPrefix.BALANCE}{pn_id}"
        balance_sk = f"LOC#{location_id}"

        # Try to update existing balance
        try:
            existing = self.db.get_item(balance_pk, balance_sk)

            if existing:
                new_qty = existing.get("quantity", 0) + delta
                self.db.update_item(
                    balance_pk,
                    balance_sk,
                    {
                        "quantity": new_qty,
                        "updated_at": now_iso(),
                    },
                )
            else:
                # Create new balance record
                self.db.put_item({
                    "PK": balance_pk,
                    "SK": balance_sk,
                    "GSI1PK": f"LOC#{location_id}",
                    "GSI1SK": f"PN#{pn_id}",
                    "pn_id": pn_id,
                    "location_id": location_id,
                    "quantity": delta,
                    "reserved_quantity": 0,
                    "created_at": now_iso(),
                    "updated_at": now_iso(),
                })

        except Exception as e:
            log_agent_action(self.name, "_update_balance_error", {"error": str(e)})


# =============================================================================
# Create Agent Instance
# =============================================================================

def create_import_agent() -> ImportAgent:
    """Create and return ImportAgent instance."""
    return ImportAgent()
