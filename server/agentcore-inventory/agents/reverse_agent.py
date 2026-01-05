# =============================================================================
# Reverse Agent - Faiston SGA Inventory
# =============================================================================
# Agent for handling reverse logistics (devoluções/reversas).
#
# Features:
# - Process return requests
# - Validate original movement (outbound reference)
# - Determine destination depot based on condition
# - Create RETURN movements
# - Handle BAD (defeituoso) items
#
# Module: Gestao de Ativos -> Gestao de Estoque
# Model: Gemini 3.0 Pro (MANDATORY per CLAUDE.md)
#
# Return Scenarios:
# 1. Devolução de Conserto - Equipment returns from "REMESSA PARA CONSERTO"
# 2. Devolução de Cliente - Client returns borrowed equipment
# 3. Equipamento BAD - Defective equipment to depot 03/03.01
# 4. Descarte - Unserviceable items to depot 04
# =============================================================================

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from enum import Enum

from .base_agent import BaseInventoryAgent, ConfidenceScore
from .utils import (
    EntityPrefix,
    MovementType,
    HILTaskType,
    HILTaskStatus,
    HILAssignedRole,
    RiskLevel,
    generate_id,
    now_iso,
    now_yyyymm,
    log_agent_action,
    parse_json_safe,
)


# =============================================================================
# Reverse Types
# =============================================================================

class ReverseReason(Enum):
    """Reason for return."""
    CONSERTO_RETORNO = "CONSERTO_RETORNO"  # Return from repair
    CLIENTE_DEVOLUCAO = "CLIENTE_DEVOLUCAO"  # Client return
    DEFEITUOSO = "DEFEITUOSO"  # Defective (BAD)
    FIM_LOCACAO = "FIM_LOCACAO"  # End of rental
    FIM_EMPRESTIMO = "FIM_EMPRESTIMO"  # End of loan
    DESCARTE = "DESCARTE"  # Discard (unrepairable)


class ItemCondition(Enum):
    """Condition of returned item."""
    FUNCIONAL = "FUNCIONAL"  # Working condition
    DEFEITUOSO = "DEFEITUOSO"  # Defective, needs repair
    INSERVIVEL = "INSERVIVEL"  # Beyond repair, discard


# Depot mapping based on owner and condition
DEPOT_MAPPING = {
    # Faiston equipment
    ("FAISTON", "FUNCIONAL"): "01",      # Recebimento
    ("FAISTON", "DEFEITUOSO"): "03",     # BAD Faiston
    ("FAISTON", "INSERVIVEL"): "04",     # Descarte
    # NTT equipment (third party)
    ("NTT", "FUNCIONAL"): "05",          # Itens de terceiros
    ("NTT", "DEFEITUOSO"): "03.01",      # BAD NTT
    ("NTT", "INSERVIVEL"): "04",         # Descarte
    # Other third parties
    ("TERCEIROS", "FUNCIONAL"): "06",    # Depósito de terceiros
    ("TERCEIROS", "DEFEITUOSO"): "03",   # BAD
    ("TERCEIROS", "INSERVIVEL"): "04",   # Descarte
}


# =============================================================================
# Agent System Prompt
# =============================================================================

REVERSE_AGENT_INSTRUCTION = """
Voce e o ReverseAgent, agente de IA responsavel pela logistica reversa
no sistema Faiston SGA (Sistema de Gestao de Ativos).

## Suas Responsabilidades

1. **Processar Retornos**: Receber e validar devolucoes de equipamentos
2. **Validar Rastreabilidade**: Verificar movimento original de saida
3. **Avaliar Condicao**: Determinar estado do equipamento (funcional/defeituoso/inservivel)
4. **Definir Destino**: Escolher deposito correto baseado em dono e condicao
5. **Criar Movimentacao**: Registrar movimento RETURN no estoque

## Regras de Negocio

### Depositos de Destino
| Dono | Condicao | Deposito |
|------|----------|----------|
| Faiston | Funcional | 01 - Recebimento |
| Faiston | Defeituoso | 03 - BAD |
| Faiston | Inservivel | 04 - Descarte |
| NTT | Funcional | 05 - Terceiros |
| NTT | Defeituoso | 03.01 - BAD NTT |
| Outros | Funcional | 06 - Dep. Terceiros |

### Validacao de Rastreabilidade
- Todo retorno DEVE ter referencia a movimento de saida
- Serial number deve existir no sistema
- Projeto deve corresponder ao movimento original

### Aprovacoes Necessarias
- Retorno normal: Automatico
- Equipamento BAD: Notificar equipe tecnica
- Descarte: HIL obrigatorio com aprovacao

## Formato de Resposta

Responda SEMPRE em JSON estruturado:
```json
{
  "action": "process_return|validate_origin|evaluate_condition",
  "status": "success|pending_approval|error",
  "message": "Descricao da acao",
  "return_record": {...},
  "destination_depot": "01",
  "confidence": { "overall": 0.95, "factors": [] }
}
```
"""


# =============================================================================
# Reverse Agent Class
# =============================================================================

class ReverseAgent(BaseInventoryAgent):
    """
    Agent for handling reverse logistics.

    Processes returns, validates traceability, determines
    destination depot based on owner and condition.
    """

    def __init__(self):
        super().__init__(
            name="ReverseAgent",
            instruction=REVERSE_AGENT_INSTRUCTION,
            description="Agent for reverse logistics and returns",
        )

        # Lazy import
        self.db = None

    def _ensure_tools(self):
        """Lazy-load tools."""
        if self.db is None:
            from ..tools.dynamodb_client import SGADynamoDBClient
            self.db = SGADynamoDBClient()

    # =========================================================================
    # Public Actions
    # =========================================================================

    async def process_return(
        self,
        serial_number: str,
        reason: str,
        condition: str,
        origin_reference: Optional[str] = None,
        project_id: Optional[str] = None,
        notes: str = "",
        operator_id: str = "system",
    ) -> Dict[str, Any]:
        """
        Process a return request.

        Args:
            serial_number: Serial number of returning item
            reason: Return reason (CONSERTO_RETORNO, CLIENTE_DEVOLUCAO, etc.)
            condition: Item condition (FUNCIONAL, DEFEITUOSO, INSERVIVEL)
            origin_reference: Reference to original exit movement
            project_id: Associated project
            notes: Additional notes
            operator_id: User processing return

        Returns:
            Return result with destination depot
        """
        self._ensure_tools()
        log_agent_action(self.name, "process_return", {
            "serial": serial_number,
            "reason": reason,
            "condition": condition,
        })

        try:
            # 1. Find asset by serial
            asset = await self._find_asset_by_serial(serial_number)

            if not asset:
                return {
                    "success": False,
                    "error": f"Equipamento nao encontrado: {serial_number}",
                }

            # 2. Validate origin movement if reference provided
            origin_movement = None
            if origin_reference:
                origin_movement = self.db.get_item(
                    f"{EntityPrefix.MOVEMENT}{origin_reference}",
                )

            # 3. Determine owner (Faiston, NTT, etc.)
            owner = self._determine_owner(asset, project_id)

            # 4. Determine destination depot
            destination_depot = self._determine_depot(owner, condition)

            # 5. Calculate confidence
            confidence = self._calculate_return_confidence(
                asset=asset,
                origin_movement=origin_movement,
                condition=condition,
            )

            # 6. Create return movement
            return_id = generate_id("RET")
            timestamp = now_iso()
            yyyymm = now_yyyymm()

            pn_id = asset.get("pn_id", "")

            return_record = {
                "PK": f"{EntityPrefix.MOVEMENT}{return_id}",
                "SK": timestamp,
                "GSI1PK": f"PN#{pn_id}",
                "GSI1SK": timestamp,
                "GSI2PK": f"YYYYMM#{yyyymm}",
                "GSI2SK": f"RETURN#{timestamp}",
                "GSI4PK": f"SERIAL#{serial_number}",
                "GSI4SK": timestamp,
                "return_id": return_id,
                "movement_type": MovementType.RETURN,
                "serial_number": serial_number,
                "pn_id": pn_id,
                "pn_number": asset.get("pn_number", ""),
                "quantity": 1,
                "destination_location_id": destination_depot,
                "origin_reference": origin_reference or "",
                "project_id": project_id or asset.get("project_id", ""),
                "reason": reason,
                "condition": condition,
                "owner": owner,
                "notes": notes,
                "status": "PENDING_INSPECTION" if condition != "FUNCIONAL" else "COMPLETED",
                "created_by": operator_id,
                "created_at": timestamp,
                "updated_at": timestamp,
            }

            self.db.put_item(return_record)

            # 7. Update asset location
            self._update_asset_location(
                asset=asset,
                new_location=destination_depot,
                condition=condition,
            )

            # 8. Update balance
            self._update_balance(pn_id, destination_depot, 1)

            # 9. Create HIL task if needed
            hil_task_id = None
            if condition == "INSERVIVEL":
                hil_task_id = await self._create_discard_approval_task(
                    return_id=return_id,
                    asset=asset,
                    reason=reason,
                    operator_id=operator_id,
                )
            elif condition == "DEFEITUOSO":
                # Notify technical team (async, no approval needed)
                await self._notify_technical_team(
                    return_id=return_id,
                    asset=asset,
                    condition=condition,
                )

            return {
                "success": True,
                "return_id": return_id,
                "serial_number": serial_number,
                "destination_depot": destination_depot,
                "depot_name": self._get_depot_name(destination_depot),
                "condition": condition,
                "owner": owner,
                "status": return_record["status"],
                "confidence_score": confidence.to_dict(),
                "requires_approval": condition == "INSERVIVEL",
                "hil_task_id": hil_task_id,
                "next_steps": self._get_next_steps(condition),
            }

        except Exception as e:
            log_agent_action(self.name, "process_return_error", {"error": str(e)})
            return {
                "success": False,
                "error": str(e),
            }

    async def validate_origin(
        self,
        serial_number: str,
    ) -> Dict[str, Any]:
        """
        Validate traceability for a return.

        Finds original exit movement for the serial.

        Args:
            serial_number: Serial number to trace

        Returns:
            Origin movement information if found
        """
        self._ensure_tools()
        log_agent_action(self.name, "validate_origin", {"serial": serial_number})

        try:
            # Find movements for this serial
            movements = self.db.query_gsi(
                index_name="GSI4",
                pk=f"SERIAL#{serial_number}",
                limit=10,
            )

            # Find last EXIT movement
            exit_movements = [
                m for m in movements
                if m.get("movement_type") in ["EXIT", "EXPEDITION"]
            ]

            if not exit_movements:
                return {
                    "success": True,
                    "found": False,
                    "message": "Nenhum movimento de saida encontrado para este serial",
                }

            # Get most recent
            latest = sorted(exit_movements, key=lambda m: m.get("created_at", ""))[-1]

            return {
                "success": True,
                "found": True,
                "origin_movement": {
                    "movement_id": latest.get("movement_id", latest.get("expedition_id", "")),
                    "movement_type": latest.get("movement_type", ""),
                    "project_id": latest.get("project_id", ""),
                    "destination": latest.get("destination", latest.get("destination_client", "")),
                    "nf_number": latest.get("nf_number", ""),
                    "created_at": latest.get("created_at", ""),
                },
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def evaluate_condition(
        self,
        serial_number: str,
        inspection_notes: str,
        test_results: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate and update item condition after inspection.

        Args:
            serial_number: Serial number
            inspection_notes: Notes from physical inspection
            test_results: Optional test results

        Returns:
            Condition evaluation with AI recommendation
        """
        self._ensure_tools()
        log_agent_action(self.name, "evaluate_condition", {"serial": serial_number})

        try:
            # Get asset
            asset = await self._find_asset_by_serial(serial_number)

            if not asset:
                return {
                    "success": False,
                    "error": f"Equipamento nao encontrado: {serial_number}",
                }

            # Use AI to evaluate condition based on notes
            condition = await self._ai_evaluate_condition(
                asset=asset,
                notes=inspection_notes,
                test_results=test_results,
            )

            return {
                "success": True,
                "serial_number": serial_number,
                "recommended_condition": condition["condition"],
                "confidence": condition["confidence"],
                "reasoning": condition["reasoning"],
                "recommended_depot": self._determine_depot(
                    self._determine_owner(asset, None),
                    condition["condition"],
                ),
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # Private Helpers
    # =========================================================================

    async def _find_asset_by_serial(
        self,
        serial_number: str,
    ) -> Optional[Dict[str, Any]]:
        """Find asset by serial number."""
        assets = self.db.query_gsi(
            index_name="GSI4",
            pk=f"SERIAL#{serial_number}",
            sk_prefix="ASSET#",
            limit=1,
        )
        return assets[0] if assets else None

    def _determine_owner(
        self,
        asset: Dict[str, Any],
        project_id: Optional[str],
    ) -> str:
        """Determine equipment owner."""
        # Check project for owner info
        if project_id:
            project = self.db.get_item(f"{EntityPrefix.PROJECT}{project_id}")
            if project:
                client = project.get("client", "").upper()
                if "NTT" in client:
                    return "NTT"
                elif client and client != "FAISTON":
                    return "TERCEIROS"

        # Check asset metadata
        owner = asset.get("owner", "").upper()
        if "NTT" in owner:
            return "NTT"
        elif owner and owner not in ["FAISTON", ""]:
            return "TERCEIROS"

        return "FAISTON"

    def _determine_depot(self, owner: str, condition: str) -> str:
        """Determine destination depot."""
        key = (owner, condition)
        return DEPOT_MAPPING.get(key, "01")

    def _get_depot_name(self, depot_code: str) -> str:
        """Get depot display name."""
        names = {
            "01": "Recebimento",
            "03": "BAD (Defeituosos Faiston)",
            "03.01": "BAD NTT",
            "04": "Descarte",
            "05": "Itens de Terceiros",
            "06": "Depósito de Terceiros",
        }
        return names.get(depot_code, f"Depósito {depot_code}")

    def _get_next_steps(self, condition: str) -> List[str]:
        """Get next steps based on condition."""
        if condition == "FUNCIONAL":
            return [
                "1. Equipamento disponível para uso",
                "2. Atualizar cadastro se necessário",
            ]
        elif condition == "DEFEITUOSO":
            return [
                "1. Aguardar análise técnica",
                "2. Avaliar viabilidade de reparo",
                "3. Após reparo, atualizar condição para FUNCIONAL",
            ]
        else:  # INSERVIVEL
            return [
                "1. Aguardar aprovação de descarte",
                "2. Após aprovação, realizar baixa patrimonial",
                "3. Destinar equipamento conforme política ambiental",
            ]

    def _update_asset_location(
        self,
        asset: Dict[str, Any],
        new_location: str,
        condition: str,
    ) -> None:
        """Update asset location and status."""
        status = "AVAILABLE"
        if condition == "DEFEITUOSO":
            status = "MAINTENANCE"
        elif condition == "INSERVIVEL":
            status = "PENDING_DISCARD"

        self.db.update_item(
            asset["PK"],
            asset["SK"],
            {
                "location_id": new_location,
                "status": status,
                "condition": condition,
                "updated_at": now_iso(),
            },
        )

    def _update_balance(
        self,
        pn_id: str,
        location_id: str,
        delta: int,
    ) -> None:
        """Update balance at destination."""
        balance_pk = f"{EntityPrefix.BALANCE}{pn_id}"
        balance_sk = f"LOC#{location_id}"

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

    async def _create_discard_approval_task(
        self,
        return_id: str,
        asset: Dict[str, Any],
        reason: str,
        operator_id: str,
    ) -> str:
        """Create HIL task for discard approval."""
        from ..tools.hil_workflow import HILWorkflowManager

        hil = HILWorkflowManager()

        task_id = await hil.create_task(
            task_type=HILTaskType.APPROVAL_DISCARD,
            title=f"Aprovação de Descarte - {asset.get('serial_number', '')}",
            description=f"Equipamento inservível aguardando aprovação de descarte.\n\nMotivo: {reason}",
            entity_type="RETURN",
            entity_id=return_id,
            assigned_role=HILAssignedRole.OPERATIONS_MANAGER,
            created_by=operator_id,
            metadata={
                "serial_number": asset.get("serial_number", ""),
                "pn_number": asset.get("pn_number", ""),
                "reason": reason,
            },
        )

        return task_id

    async def _notify_technical_team(
        self,
        return_id: str,
        asset: Dict[str, Any],
        condition: str,
    ) -> None:
        """Notify technical team about defective equipment."""
        # Log notification (actual notification via ComunicacaoAgent)
        log_agent_action(self.name, "notify_technical_team", {
            "return_id": return_id,
            "serial": asset.get("serial_number", ""),
            "condition": condition,
        })

    async def _ai_evaluate_condition(
        self,
        asset: Dict[str, Any],
        notes: str,
        test_results: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Use AI to evaluate condition."""
        from google import genai
        from google.genai import types

        prompt = f"""Avalie a condicao do equipamento baseado nas informacoes:

EQUIPAMENTO:
- PN: {asset.get('pn_number', '')}
- Descricao: {asset.get('description', '')}
- Historico: {asset.get('maintenance_history', 'Nenhum')}

NOTAS DE INSPECAO:
{notes}

RESULTADOS DE TESTES:
{test_results or 'Nenhum teste realizado'}

Responda em JSON:
{{
  "condition": "FUNCIONAL" ou "DEFEITUOSO" ou "INSERVIVEL",
  "confidence": 0.0 a 1.0,
  "reasoning": "Justificativa breve"
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
            return result or {
                "condition": "DEFEITUOSO",
                "confidence": 0.5,
                "reasoning": "Avaliacao padrao - inspecao manual recomendada",
            }

        except Exception as e:
            log_agent_action(self.name, "_ai_evaluate_error", {"error": str(e)})
            return {
                "condition": "DEFEITUOSO",
                "confidence": 0.3,
                "reasoning": f"Erro na avaliacao AI: {e}",
            }

    def _calculate_return_confidence(
        self,
        asset: Dict[str, Any],
        origin_movement: Optional[Dict[str, Any]],
        condition: str,
    ) -> ConfidenceScore:
        """Calculate confidence for return processing."""
        factors = []
        overall = 0.9

        # Asset found
        if asset:
            factors.append("Equipamento encontrado no sistema")
        else:
            overall *= 0.5
            factors.append("Equipamento NAO encontrado")

        # Origin traceability
        if origin_movement:
            factors.append("Rastreabilidade confirmada")
        else:
            overall *= 0.8
            factors.append("Sem referencia de movimento de saida")

        # Condition
        risk_level = RiskLevel.LOW
        if condition == "FUNCIONAL":
            factors.append("Condicao FUNCIONAL - retorno padrao")
        elif condition == "DEFEITUOSO":
            risk_level = RiskLevel.MEDIUM
            factors.append("Condicao DEFEITUOSO - requer analise")
        else:
            risk_level = RiskLevel.HIGH
            factors.append("Condicao INSERVIVEL - requer aprovacao")

        return ConfidenceScore(
            overall=overall,
            extraction_quality=0.9 if asset else 0.5,
            evidence_strength=0.9 if origin_movement else 0.6,
            historical_match=0.85,
            risk_level=risk_level,
            factors=factors,
        )


# =============================================================================
# Create Agent Instance
# =============================================================================

def create_reverse_agent() -> ReverseAgent:
    """Create and return ReverseAgent instance."""
    return ReverseAgent()
