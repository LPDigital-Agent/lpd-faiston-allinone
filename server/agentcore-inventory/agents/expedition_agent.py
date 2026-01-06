# =============================================================================
# Expedition Agent - Faiston SGA Inventory
# =============================================================================
# Agent for handling outbound shipments (expedição/saída).
#
# Features:
# - Process expedition requests from chamados/tickets
# - Verify stock availability
# - Suggest shipping modal
# - Generate SAP-ready data for NF
# - Handle separation and packaging workflow
#
# Module: Gestao de Ativos -> Gestao de Estoque
# Model: Gemini 3.0 Pro (MANDATORY per CLAUDE.md)
#
# Outbound Flow:
# 1. Chamado opened (request for equipment)
# 2. ExpeditionAgent verifies stock and project
# 3. Agent suggests shipping modal (via CarrierAgent)
# 4. Physical separation and packaging
# 5. Generate SAP-ready data for NF emission
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
    RiskLevel,
    generate_id,
    now_iso,
    now_yyyymm,
    log_agent_action,
    parse_json_safe,
    extract_json,
)


# =============================================================================
# SAP Export Formats
# =============================================================================

# Nature of operation options for SAP NF
NATUREZA_OPERACAO = {
    "USO_CONSUMO": "REMESSA PARA USO E CONSUMO",
    "CONSERTO": "REMESSA PARA CONSERTO",
    "DEMONSTRACAO": "REMESSA PARA DEMONSTRACAO",
    "LOCACAO": "REMESSA EM LOCACAO",
    "EMPRESTIMO": "REMESSA EM EMPRESTIMO",
}


# =============================================================================
# Agent System Prompt
# =============================================================================

EXPEDITION_AGENT_INSTRUCTION = """
Voce e o ExpeditionAgent, agente de IA responsavel pela expedicao de materiais
no sistema Faiston SGA (Sistema de Gestao de Ativos).

## Suas Responsabilidades

1. **Processar Chamados**: Receber e validar solicitacoes de expedicao
2. **Verificar Estoque**: Confirmar disponibilidade do item solicitado
3. **Sugerir Modal**: Recomendar melhor forma de envio
4. **Gerar Dados SAP**: Preparar informacoes para emissao de NF
5. **Controlar Separacao**: Acompanhar processo de separacao fisica

## Regras de Negocio

### Processamento de Chamados
- Chamado deve conter: ID, equipamento solicitado, destino, urgencia
- Validar projeto associado ao chamado
- Verificar se equipamento esta disponivel (nao reservado)

### Verificacao de Estoque
- Equipamento deve estar em deposito ativo (01, 05)
- Serial number deve existir e estar disponivel
- Quantidade solicitada deve estar disponivel

### Natureza da Operacao (SAP)
- USO E CONSUMO: Equipamento para uso do cliente
- CONSERTO: Equipamento para reparo
- DEMONSTRACAO: Equipamento para demonstracao temporaria
- LOCACAO: Equipamento em contrato de locacao
- EMPRESTIMO: Equipamento emprestado temporariamente

### Campos Obrigatorios para NF
- Cliente destino (CNPJ/razao social)
- Part Number + Serial
- Quantidade
- Utilizacao: "S-OUTRAS OPERACOES"
- Incoterms: 0 (obrigatorio)
- Transportadora
- Peso liquido/bruto
- Natureza da operacao
- Observacao: "PROJETO - CHAMADO - SERIAL"

## Formato de Resposta

Responda SEMPRE em JSON estruturado:
```json
{
  "action": "process_expedition|verify_stock|generate_sap_data",
  "status": "success|pending_approval|error",
  "message": "Descricao da acao",
  "sap_data": { ... },
  "confidence": { "overall": 0.95, "factors": [] }
}
```

## Contexto

Voce opera de forma autonoma quando a confianca e alta,
mas solicita Human-in-the-Loop para operacoes de alto valor
ou equipamentos restritos.
"""


# =============================================================================
# Expedition Data Classes
# =============================================================================

@dataclass
class ExpeditionRequest:
    """Request for expedition processing."""
    chamado_id: str
    project_id: str
    items: List[Dict[str, Any]]  # [{pn_id, serial, quantity}]
    destination_client: str
    destination_address: str
    urgency: str  # LOW, NORMAL, HIGH, URGENT
    nature: str  # USO_CONSUMO, CONSERTO, etc.
    notes: str = ""


@dataclass
class SAPExportData:
    """Data formatted for SAP NF emission."""
    cliente: str
    item_numero: str
    serial_number: str
    quantidade: int
    deposito: str
    utilizacao: str
    incoterms: str
    transportadora: str
    natureza_operacao: str
    observacao: str
    peso_liquido: float
    peso_bruto: float
    embalagem: str


# =============================================================================
# Expedition Agent Class
# =============================================================================

class ExpeditionAgent(BaseInventoryAgent):
    """
    Agent for handling outbound shipments.

    Processes expedition requests, verifies stock, suggests
    shipping modals, and generates SAP-ready data for NF.
    """

    def __init__(self):
        super().__init__(
            name="ExpeditionAgent",
            instruction=EXPEDITION_AGENT_INSTRUCTION,
            description="Agent for handling outbound shipments and NF data generation",
        )

        # Lazy import to avoid cold start overhead
        self.db = None

    def _ensure_tools(self):
        """Lazy-load tools to minimize cold start time."""
        if self.db is None:
            from ..tools.dynamodb_client import SGADynamoDBClient
            self.db = SGADynamoDBClient()

    # =========================================================================
    # Public Actions
    # =========================================================================

    async def process_expedition_request(
        self,
        chamado_id: str,
        project_id: str,
        items: List[Dict[str, Any]],
        destination_client: str,
        destination_address: str,
        urgency: str = "NORMAL",
        nature: str = "USO_CONSUMO",
        notes: str = "",
        operator_id: str = "system",
    ) -> Dict[str, Any]:
        """
        Process an expedition request from a chamado.

        Verifies stock, creates reservation, and prepares SAP data.

        Args:
            chamado_id: Ticket/chamado ID
            project_id: Associated project
            items: List of items to ship [{pn_id, serial, quantity}]
            destination_client: Client name/CNPJ
            destination_address: Delivery address
            urgency: Urgency level (LOW, NORMAL, HIGH, URGENT)
            nature: Nature of operation for SAP
            notes: Additional notes
            operator_id: User processing the expedition

        Returns:
            Expedition result with SAP-ready data
        """
        self._ensure_tools()
        log_agent_action(self.name, "process_expedition_request", {
            "chamado_id": chamado_id,
            "items_count": len(items),
        })

        try:
            # Validate project
            project = self.db.get_item(f"{EntityPrefix.PROJECT}{project_id}")
            if not project:
                return {
                    "success": False,
                    "error": f"Projeto nao encontrado: {project_id}",
                }

            # Generate expedition ID
            expedition_id = generate_id("EXP")
            timestamp = now_iso()

            # Process each item
            verified_items = []
            unavailable_items = []
            sap_data_list = []

            for item in items:
                pn_id = item.get("pn_id", "")
                serial = item.get("serial", "")
                quantity = item.get("quantity", 1)

                # Verify stock availability
                verification = await self._verify_stock_item(pn_id, serial, quantity)

                if verification["available"]:
                    verified_items.append({
                        **item,
                        "pn": verification["pn"],
                        "asset": verification.get("asset"),
                        "location_id": verification.get("location_id"),
                    })

                    # Generate SAP data for this item
                    sap_data = self._generate_sap_data(
                        pn=verification["pn"],
                        serial=serial,
                        quantity=quantity,
                        location_id=verification.get("location_id", "01"),
                        destination_client=destination_client,
                        nature=nature,
                        project_id=project_id,
                        chamado_id=chamado_id,
                    )
                    sap_data_list.append(sap_data)
                else:
                    unavailable_items.append({
                        **item,
                        "reason": verification.get("reason", "Nao disponivel"),
                    })

            # Calculate confidence
            availability_rate = len(verified_items) / max(len(items), 1)
            confidence = self._calculate_expedition_confidence(
                availability_rate=availability_rate,
                urgency=urgency,
                nature=nature,
            )

            # Create expedition record
            if verified_items:
                expedition = self._create_expedition_record(
                    expedition_id=expedition_id,
                    chamado_id=chamado_id,
                    project_id=project_id,
                    items=verified_items,
                    destination_client=destination_client,
                    destination_address=destination_address,
                    urgency=urgency,
                    nature=nature,
                    notes=notes,
                    operator_id=operator_id,
                    timestamp=timestamp,
                )

                # Create reservations for verified items
                for v_item in verified_items:
                    await self._create_expedition_reservation(
                        expedition_id=expedition_id,
                        pn_id=v_item["pn_id"],
                        serial=v_item.get("serial"),
                        quantity=v_item.get("quantity", 1),
                        location_id=v_item.get("location_id", "01"),
                        operator_id=operator_id,
                    )

            return {
                "success": True,
                "expedition_id": expedition_id,
                "chamado_id": chamado_id,
                "project_id": project_id,
                "verified_items": verified_items,
                "unavailable_items": unavailable_items,
                "sap_data": sap_data_list,
                "sap_copyable": self._format_sap_copyable(sap_data_list),
                "status": "PENDING_SEPARATION" if verified_items else "FAILED",
                "confidence_score": confidence.to_dict(),
                "requires_approval": confidence.requires_hil,
                "next_steps": [
                    "1. Separar itens fisicamente",
                    "2. Embalar equipamento",
                    "3. Copiar dados SAP para NF",
                    "4. Confirmar expedicao no sistema",
                ],
            }

        except Exception as e:
            log_agent_action(self.name, "process_expedition_error", {"error": str(e)})
            return {
                "success": False,
                "error": str(e),
                "message": f"Erro ao processar expedicao: {e}",
            }

    async def verify_stock(
        self,
        pn_id: str,
        serial: Optional[str] = None,
        quantity: int = 1,
    ) -> Dict[str, Any]:
        """
        Verify stock availability for an item.

        Args:
            pn_id: Part number ID
            serial: Optional serial number for serialized items
            quantity: Quantity needed

        Returns:
            Verification result with availability status
        """
        self._ensure_tools()
        log_agent_action(self.name, "verify_stock", {"pn_id": pn_id})

        return await self._verify_stock_item(pn_id, serial, quantity)

    async def confirm_separation(
        self,
        expedition_id: str,
        items_confirmed: List[Dict[str, Any]],
        package_info: Dict[str, Any],
        operator_id: str,
    ) -> Dict[str, Any]:
        """
        Confirm physical separation and packaging.

        Args:
            expedition_id: Expedition ID
            items_confirmed: List of confirmed items with serials
            package_info: Packaging details (weight, dimensions)
            operator_id: User confirming separation

        Returns:
            Confirmation result
        """
        self._ensure_tools()
        log_agent_action(self.name, "confirm_separation", {
            "expedition_id": expedition_id,
        })

        try:
            # Get expedition record
            expedition = self.db.get_item(
                f"{EntityPrefix.MOVEMENT}{expedition_id}",
            )

            if not expedition:
                return {
                    "success": False,
                    "error": f"Expedicao nao encontrada: {expedition_id}",
                }

            # Update expedition status
            self.db.update_item(
                f"{EntityPrefix.MOVEMENT}{expedition_id}",
                expedition.get("SK", now_iso()),
                {
                    "status": "SEPARATED",
                    "separation_confirmed_at": now_iso(),
                    "separation_confirmed_by": operator_id,
                    "package_info": package_info,
                    "items_confirmed": items_confirmed,
                    "updated_at": now_iso(),
                },
            )

            return {
                "success": True,
                "expedition_id": expedition_id,
                "status": "SEPARATED",
                "message": "Separacao confirmada. Pronto para emissao de NF.",
                "next_steps": [
                    "1. Emitir NF no SAP",
                    "2. Transmitir para SEFAZ",
                    "3. Imprimir DANFE",
                    "4. Despachar com transportadora",
                ],
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def complete_expedition(
        self,
        expedition_id: str,
        nf_number: str,
        nf_key: str,
        carrier: str,
        tracking_code: Optional[str] = None,
        operator_id: str = "system",
    ) -> Dict[str, Any]:
        """
        Complete the expedition after NF emission.

        Creates EXIT movements and updates stock.

        Args:
            expedition_id: Expedition ID
            nf_number: NF number
            nf_key: NF access key (44 digits)
            carrier: Carrier/transportadora name
            tracking_code: Optional tracking number
            operator_id: User completing

        Returns:
            Completion result with created movements
        """
        self._ensure_tools()
        log_agent_action(self.name, "complete_expedition", {
            "expedition_id": expedition_id,
            "nf_number": nf_number,
        })

        try:
            # Get expedition record
            expedition = self.db.get_item(
                f"{EntityPrefix.MOVEMENT}{expedition_id}",
            )

            if not expedition:
                return {
                    "success": False,
                    "error": f"Expedicao nao encontrada: {expedition_id}",
                }

            items = expedition.get("items_confirmed") or expedition.get("items", [])
            timestamp = now_iso()
            yyyymm = now_yyyymm()

            # Create EXIT movements for each item
            movements = []
            for item in items:
                movement_id = generate_id("MV")

                movement = {
                    "PK": f"{EntityPrefix.MOVEMENT}{movement_id}",
                    "SK": timestamp,
                    "GSI1PK": f"PN#{item.get('pn_id', '')}",
                    "GSI1SK": timestamp,
                    "GSI2PK": f"YYYYMM#{yyyymm}",
                    "GSI2SK": f"EXIT#{timestamp}",
                    "movement_id": movement_id,
                    "movement_type": MovementType.EXIT,
                    "pn_id": item.get("pn_id", ""),
                    "serial_number": item.get("serial", ""),
                    "quantity": -item.get("quantity", 1),  # Negative for exit
                    "source_location_id": item.get("location_id", "01"),
                    "destination": expedition.get("destination_client", ""),
                    "project_id": expedition.get("project_id", ""),
                    "expedition_id": expedition_id,
                    "nf_number": nf_number,
                    "nf_key": nf_key,
                    "carrier": carrier,
                    "tracking_code": tracking_code or "",
                    "operator_id": operator_id,
                    "status": "COMPLETED",
                    "created_at": timestamp,
                    "updated_at": timestamp,
                }

                self.db.put_item(movement)
                movements.append(movement_id)

                # Update balance
                self._update_balance(
                    pn_id=item.get("pn_id", ""),
                    location_id=item.get("location_id", "01"),
                    delta=-item.get("quantity", 1),
                )

            # Update expedition status
            self.db.update_item(
                f"{EntityPrefix.MOVEMENT}{expedition_id}",
                expedition.get("SK", now_iso()),
                {
                    "status": "COMPLETED",
                    "completed_at": timestamp,
                    "completed_by": operator_id,
                    "nf_number": nf_number,
                    "nf_key": nf_key,
                    "carrier": carrier,
                    "tracking_code": tracking_code or "",
                    "movements": movements,
                    "updated_at": timestamp,
                },
            )

            return {
                "success": True,
                "expedition_id": expedition_id,
                "status": "COMPLETED",
                "movements_created": movements,
                "nf_number": nf_number,
                "tracking_code": tracking_code,
                "message": f"Expedicao concluida com sucesso. NF {nf_number}.",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # Private Helpers
    # =========================================================================

    async def _verify_stock_item(
        self,
        pn_id: str,
        serial: Optional[str],
        quantity: int,
    ) -> Dict[str, Any]:
        """Verify stock availability for a single item."""
        # Get part number
        pn = self.db.get_item(f"{EntityPrefix.PART_NUMBER}{pn_id}")

        if not pn:
            return {
                "available": False,
                "reason": f"Part number nao encontrado: {pn_id}",
            }

        # For serialized items, check specific asset
        if pn.get("is_serialized") and serial:
            # Search for asset by serial
            assets = self.db.query_gsi(
                index_name="GSI4",
                pk=f"SERIAL#{serial}",
                limit=1,
            )

            if not assets:
                return {
                    "available": False,
                    "pn": pn,
                    "reason": f"Serial nao encontrado: {serial}",
                }

            asset = assets[0]

            # Check if available (not reserved, not in transit)
            if asset.get("status") in ["RESERVED", "IN_TRANSIT", "MAINTENANCE"]:
                return {
                    "available": False,
                    "pn": pn,
                    "asset": asset,
                    "reason": f"Equipamento com status: {asset.get('status')}",
                }

            return {
                "available": True,
                "pn": pn,
                "asset": asset,
                "location_id": asset.get("location_id", "01"),
            }

        # For non-serialized, check balance
        else:
            balance = self.db.get_item(
                f"{EntityPrefix.BALANCE}{pn_id}",
                "LOC#01",  # Default depot
            )

            available_qty = (balance.get("quantity", 0) -
                           balance.get("reserved_quantity", 0))

            if available_qty < quantity:
                return {
                    "available": False,
                    "pn": pn,
                    "reason": f"Quantidade insuficiente. Disponivel: {available_qty}",
                }

            return {
                "available": True,
                "pn": pn,
                "location_id": "01",
                "available_quantity": available_qty,
            }

    def _generate_sap_data(
        self,
        pn: Dict[str, Any],
        serial: str,
        quantity: int,
        location_id: str,
        destination_client: str,
        nature: str,
        project_id: str,
        chamado_id: str,
    ) -> Dict[str, Any]:
        """Generate SAP-ready data for NF emission."""
        natureza = NATUREZA_OPERACAO.get(nature, NATUREZA_OPERACAO["USO_CONSUMO"])

        return {
            "cliente": destination_client,
            "item_numero": pn.get("part_number", ""),
            "descricao": pn.get("description", ""),
            "serial_number": serial,
            "quantidade": quantity,
            "deposito": location_id,
            "utilizacao": "S-OUTRAS OPERACOES",
            "incoterms": "0",
            "transportadora": "",  # To be filled
            "natureza_operacao": natureza,
            "observacao": f"{project_id} - {chamado_id} - {serial}",
            "peso_liquido": 0.0,  # To be filled during separation
            "peso_bruto": 0.0,
            "embalagem": "",
        }

    def _format_sap_copyable(self, sap_data_list: List[Dict[str, Any]]) -> str:
        """Format SAP data for easy copy/paste."""
        lines = []

        for i, item in enumerate(sap_data_list, 1):
            lines.append(f"=== ITEM {i} ===")
            lines.append(f"Cliente: {item['cliente']}")
            lines.append(f"Item: {item['item_numero']} - {item['descricao']}")
            lines.append(f"Serial: {item['serial_number']}")
            lines.append(f"Quantidade: {item['quantidade']}")
            lines.append(f"Deposito: {item['deposito']}")
            lines.append(f"Utilizacao: {item['utilizacao']}")
            lines.append(f"Incoterms: {item['incoterms']}")
            lines.append(f"Natureza: {item['natureza_operacao']}")
            lines.append(f"Observacao: {item['observacao']}")
            lines.append("")

        return "\n".join(lines)

    def _create_expedition_record(
        self,
        expedition_id: str,
        chamado_id: str,
        project_id: str,
        items: List[Dict[str, Any]],
        destination_client: str,
        destination_address: str,
        urgency: str,
        nature: str,
        notes: str,
        operator_id: str,
        timestamp: str,
    ) -> Dict[str, Any]:
        """Create expedition record in DynamoDB."""
        yyyymm = now_yyyymm()

        expedition = {
            "PK": f"{EntityPrefix.MOVEMENT}{expedition_id}",
            "SK": timestamp,
            "GSI1PK": f"PROJECT#{project_id}",
            "GSI1SK": timestamp,
            "GSI2PK": f"YYYYMM#{yyyymm}",
            "GSI2SK": f"EXPEDITION#{timestamp}",
            "GSI3PK": f"CHAMADO#{chamado_id}",
            "GSI3SK": timestamp,
            "expedition_id": expedition_id,
            "movement_type": "EXPEDITION",
            "chamado_id": chamado_id,
            "project_id": project_id,
            "items": items,
            "destination_client": destination_client,
            "destination_address": destination_address,
            "urgency": urgency,
            "nature": nature,
            "notes": notes,
            "status": "PENDING_SEPARATION",
            "created_by": operator_id,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        self.db.put_item(expedition)
        return expedition

    async def _create_expedition_reservation(
        self,
        expedition_id: str,
        pn_id: str,
        serial: Optional[str],
        quantity: int,
        location_id: str,
        operator_id: str,
    ) -> None:
        """Create reservation for expedition item."""
        reservation_id = generate_id("RSV")
        timestamp = now_iso()

        reservation = {
            "PK": f"{EntityPrefix.RESERVATION}{reservation_id}",
            "SK": timestamp,
            "GSI1PK": f"PN#{pn_id}",
            "GSI1SK": f"RESERVATION#{timestamp}",
            "reservation_id": reservation_id,
            "pn_id": pn_id,
            "serial_number": serial or "",
            "quantity": quantity,
            "location_id": location_id,
            "expedition_id": expedition_id,
            "status": "ACTIVE",
            "created_by": operator_id,
            "created_at": timestamp,
            "expires_at": "",  # No expiration for expedition reservations
        }

        self.db.put_item(reservation)

        # Update balance reserved quantity
        self._update_reserved_quantity(pn_id, location_id, quantity)

    def _update_reserved_quantity(
        self,
        pn_id: str,
        location_id: str,
        delta: int,
    ) -> None:
        """Update reserved quantity in balance."""
        balance_pk = f"{EntityPrefix.BALANCE}{pn_id}"
        balance_sk = f"LOC#{location_id}"

        try:
            existing = self.db.get_item(balance_pk, balance_sk)

            if existing:
                new_reserved = existing.get("reserved_quantity", 0) + delta
                self.db.update_item(
                    balance_pk,
                    balance_sk,
                    {
                        "reserved_quantity": max(0, new_reserved),
                        "updated_at": now_iso(),
                    },
                )
        except Exception as e:
            log_agent_action(self.name, "_update_reserved_quantity_error", {"error": str(e)})

    def _update_balance(
        self,
        pn_id: str,
        location_id: str,
        delta: int,
    ) -> None:
        """Update inventory balance."""
        balance_pk = f"{EntityPrefix.BALANCE}{pn_id}"
        balance_sk = f"LOC#{location_id}"

        try:
            existing = self.db.get_item(balance_pk, balance_sk)

            if existing:
                new_qty = existing.get("quantity", 0) + delta
                # Also reduce reserved if it was a negative delta (exit)
                reserved = existing.get("reserved_quantity", 0)
                new_reserved = max(0, reserved + delta) if delta < 0 else reserved

                self.db.update_item(
                    balance_pk,
                    balance_sk,
                    {
                        "quantity": max(0, new_qty),
                        "reserved_quantity": new_reserved,
                        "updated_at": now_iso(),
                    },
                )
        except Exception as e:
            log_agent_action(self.name, "_update_balance_error", {"error": str(e)})

    def _calculate_expedition_confidence(
        self,
        availability_rate: float,
        urgency: str,
        nature: str,
    ) -> ConfidenceScore:
        """Calculate expedition confidence score."""
        factors = []

        # Base confidence from availability
        overall = availability_rate * 0.9

        if availability_rate >= 0.9:
            factors.append("Alto disponibilidade (>90%)")
        elif availability_rate >= 0.7:
            factors.append(f"Disponibilidade media ({availability_rate*100:.0f}%)")
        else:
            factors.append(f"Baixa disponibilidade ({availability_rate*100:.0f}%)")

        # Urgency factor
        risk_level = RiskLevel.LOW
        if urgency == "URGENT":
            risk_level = RiskLevel.HIGH
            factors.append("Urgencia alta - priorizar")
        elif urgency == "HIGH":
            risk_level = RiskLevel.MEDIUM
            factors.append("Urgencia media")

        # Nature factor
        if nature in ["CONSERTO", "DEMONSTRACAO"]:
            factors.append(f"Natureza: {nature} - retorno esperado")

        return ConfidenceScore(
            overall=overall,
            extraction_quality=availability_rate,
            evidence_strength=0.9,
            historical_match=0.85,
            risk_level=risk_level,
            factors=factors,
        )


# =============================================================================
# Create Agent Instance
# =============================================================================

def create_expedition_agent() -> ExpeditionAgent:
    """Create and return ExpeditionAgent instance."""
    return ExpeditionAgent()
