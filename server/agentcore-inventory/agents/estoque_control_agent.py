# =============================================================================
# Estoque Control Agent - Faiston SGA Inventory
# =============================================================================
# Core agent for inventory movements (+/-). Handles:
# - Reservations for chamados/projetos
# - Expeditions (outgoing shipments)
# - Transfers between locations
# - Returns (reversas)
# - Balance queries
#
# Module: Gestao de Ativos -> Gestao de Estoque
# Model: Gemini 3.0 Pro (MANDATORY per CLAUDE.md)
#
# Human-in-the-Loop Matrix:
# - Reservation same project: AUTONOMOUS
# - Reservation cross-project: HIL
# - Transfer same project: AUTONOMOUS
# - Transfer to restricted location: HIL
# - Adjustment: ALWAYS HIL
# - Discard/Loss: ALWAYS HIL
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
)


# =============================================================================
# Agent System Prompt
# =============================================================================

ESTOQUE_CONTROL_INSTRUCTION = """
Voce e o EstoqueControlAgent, agente de IA responsavel pelo controle de estoque
do sistema Faiston SGA (Sistema de Gestao de Ativos).

## Suas Responsabilidades

1. **Reservas**: Criar e gerenciar reservas de ativos para chamados/projetos
2. **Expedicoes**: Processar saidas de material para clientes/tecnicos
3. **Transferencias**: Movimentar ativos entre locais de estoque
4. **Reversas**: Processar devolucoes de material
5. **Consultas**: Responder sobre saldos e localizacao de ativos

## Regras de Negocio

### Reservas
- Reserva BLOQUEIA o saldo disponivel
- Reserva tem TTL (expira automaticamente)
- Reserva pode ser para serial especifico ou quantidade generica
- Cross-project reserva REQUER APROVACAO HUMANA

### Movimentacoes
- Toda movimentacao gera evento IMUTAVEL
- Saldo e PROJECAO calculada dos eventos
- Transferencia para local RESTRITO requer APROVACAO
- AJUSTE e DESCARTE SEMPRE requerem APROVACAO

### Saldos
- saldo_total = entradas - saidas
- saldo_disponivel = saldo_total - reservado
- saldo_reservado = sum(reservas ativas)

## Formato de Resposta

Responda SEMPRE em JSON estruturado:
```json
{
  "action": "reservation|expedition|transfer|return|query",
  "status": "success|pending_approval|error",
  "message": "Descricao da acao executada",
  "data": { ... },
  "requires_hil": true|false,
  "confidence": { "overall": 0.95, "factors": [] }
}
```

## Contexto

Voce opera em um ambiente de gestao de estoque de equipamentos de TI e telecomunicacoes.
Os ativos sao controlados por numero de serie (serial) ou quantidade (para itens de consumo).
Cada ativo pertence a um projeto/cliente especifico.
"""


# =============================================================================
# Movement Result Data Class
# =============================================================================


@dataclass
class MovementResult:
    """Result of a movement operation."""
    success: bool
    movement_id: Optional[str] = None
    message: str = ""
    requires_hil: bool = False
    hil_task_id: Optional[str] = None
    confidence: Optional[ConfidenceScore] = None
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "success": self.success,
            "message": self.message,
            "requires_hil": self.requires_hil,
        }
        if self.movement_id:
            result["movement_id"] = self.movement_id
        if self.hil_task_id:
            result["hil_task_id"] = self.hil_task_id
        if self.confidence:
            result["confidence"] = self.confidence.to_dict()
        if self.data:
            result["data"] = self.data
        return result


# =============================================================================
# Estoque Control Agent
# =============================================================================


class EstoqueControlAgent(BaseInventoryAgent):
    """
    Core agent for inventory control operations.

    Handles all +/- movements in the inventory system with
    confidence scoring and HIL workflow support.
    """

    def __init__(self):
        """Initialize the Estoque Control Agent."""
        super().__init__(
            name="EstoqueControlAgent",
            instruction=ESTOQUE_CONTROL_INSTRUCTION,
            description="Controle de movimentacoes de estoque (reservas, expedicoes, transferencias)",
        )
        # Lazy-loaded clients
        self._db_client = None
        self._s3_client = None

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

    # =========================================================================
    # Reservation Operations
    # =========================================================================

    async def create_reservation(
        self,
        part_number: str,
        quantity: int,
        project_id: str,
        chamado_id: Optional[str] = None,
        serial_numbers: Optional[List[str]] = None,
        source_location_id: str = "ESTOQUE_CENTRAL",
        destination_location_id: Optional[str] = None,
        requested_by: str = "system",
        notes: Optional[str] = None,
        ttl_hours: int = 72,
    ) -> MovementResult:
        """
        Create a reservation for assets.

        Args:
            part_number: Part number to reserve
            quantity: Quantity to reserve
            project_id: Project/client this reservation is for
            chamado_id: Optional ticket/chamado ID
            serial_numbers: Optional specific serials to reserve
            source_location_id: Location to reserve from
            destination_location_id: Optional final destination
            requested_by: User who requested the reservation
            notes: Optional notes
            ttl_hours: TTL for reservation (default 72h)

        Returns:
            MovementResult with reservation details
        """
        log_agent_action(
            self.name, "create_reservation",
            entity_type="RESERVATION",
            status="started",
        )

        try:
            # 1. Check available balance
            balance = await self._get_balance(
                part_number=part_number,
                location_id=source_location_id,
                project_id=project_id,
            )

            if balance["available"] < quantity:
                return MovementResult(
                    success=False,
                    message=f"Saldo insuficiente. Disponivel: {balance['available']}, Solicitado: {quantity}",
                    data={"balance": balance},
                )

            # 2. Calculate confidence score
            risk_factors = []

            # Check if cross-project (different project owns the stock)
            is_cross_project = balance.get("owner_project_id") != project_id
            if is_cross_project:
                risk_factors.append("cross_project_reservation")

            # Check if high quantity
            if quantity > 10:
                risk_factors.append("high_quantity")

            confidence = self.calculate_confidence(
                extraction_quality=1.0,
                evidence_strength=0.9 if chamado_id else 0.7,
                historical_match=0.9,
                risk_factors=risk_factors,
                base_risk=RiskLevel.MEDIUM if is_cross_project else RiskLevel.LOW,
            )

            # 3. Check if HIL required
            requires_hil = self.should_require_hil(
                action_type="reservation",
                confidence=confidence,
            )

            # Cross-project always requires HIL
            if is_cross_project:
                requires_hil = True

            # 4. Generate reservation ID and create record
            reservation_id = generate_id("RES")
            now = now_iso()
            ttl_timestamp = int((datetime.utcnow().timestamp()) + (ttl_hours * 3600))

            reservation_item = {
                "PK": f"{EntityPrefix.RESERVATION}{reservation_id}",
                "SK": "METADATA",
                "entity_type": "RESERVATION",
                "reservation_id": reservation_id,
                "part_number": part_number,
                "quantity": quantity,
                "project_id": project_id,
                "chamado_id": chamado_id,
                "serial_numbers": serial_numbers or [],
                "source_location_id": source_location_id,
                "destination_location_id": destination_location_id,
                "status": "PENDING_APPROVAL" if requires_hil else "ACTIVE",
                "requested_by": requested_by,
                "notes": notes,
                "created_at": now,
                "ttl": ttl_timestamp,
                # GSIs
                "GSI4_PK": f"STATUS#{'PENDING_APPROVAL' if requires_hil else 'ACTIVE'}",
                "GSI4_SK": now,
                "GSI3_PK": f"{EntityPrefix.PROJECT}{project_id}",
                "GSI3_SK": f"RESERVATION#{now}",
            }

            # 5. If HIL required, create approval task
            hil_task_id = None
            if requires_hil:
                from tools.hil_workflow import HILWorkflowManager
                hil_manager = HILWorkflowManager()

                hil_task = await hil_manager.create_task(
                    task_type=HILTaskType.APPROVAL_TRANSFER,
                    title=f"Aprovar reserva cross-project: {part_number}",
                    description=self.format_hil_task_message(
                        action_type="reservation",
                        summary=f"Reserva de {quantity}x {part_number} para projeto {project_id}",
                        confidence=confidence,
                        details={
                            "part_number": part_number,
                            "quantity": quantity,
                            "project_id": project_id,
                            "source_project": balance.get("owner_project_id", "N/A"),
                            "chamado_id": chamado_id or "N/A",
                            "location": source_location_id,
                        },
                    ),
                    entity_type="RESERVATION",
                    entity_id=reservation_id,
                    requested_by=requested_by,
                    payload=reservation_item,
                )
                hil_task_id = hil_task.get("task_id")
                reservation_item["hil_task_id"] = hil_task_id

            # 6. Save reservation
            self.db.put_item(reservation_item)

            # 7. If not HIL, also update balance
            if not requires_hil:
                await self._update_reserved_balance(
                    part_number=part_number,
                    location_id=source_location_id,
                    project_id=project_id,
                    quantity_delta=quantity,
                )

            log_agent_action(
                self.name, "create_reservation",
                entity_type="RESERVATION",
                entity_id=reservation_id,
                status="completed",
            )

            return MovementResult(
                success=True,
                movement_id=reservation_id,
                message="Reserva criada com sucesso" if not requires_hil else "Reserva aguardando aprovacao",
                requires_hil=requires_hil,
                hil_task_id=hil_task_id,
                confidence=confidence,
                data={
                    "reservation_id": reservation_id,
                    "status": reservation_item["status"],
                    "ttl_hours": ttl_hours,
                },
            )

        except Exception as e:
            log_agent_action(
                self.name, "create_reservation",
                entity_type="RESERVATION",
                status="failed",
            )
            return MovementResult(
                success=False,
                message=f"Erro ao criar reserva: {str(e)}",
            )

    async def cancel_reservation(
        self,
        reservation_id: str,
        cancelled_by: str = "system",
        reason: Optional[str] = None,
    ) -> MovementResult:
        """
        Cancel an active reservation.

        Args:
            reservation_id: Reservation ID to cancel
            cancelled_by: User cancelling
            reason: Cancellation reason

        Returns:
            MovementResult
        """
        log_agent_action(
            self.name, "cancel_reservation",
            entity_type="RESERVATION",
            entity_id=reservation_id,
            status="started",
        )

        try:
            # Get reservation
            reservation = self.db.get_item(
                pk=f"{EntityPrefix.RESERVATION}{reservation_id}",
                sk="METADATA",
            )

            if not reservation:
                return MovementResult(
                    success=False,
                    message=f"Reserva {reservation_id} nao encontrada",
                )

            if reservation.get("status") not in ["ACTIVE", "PENDING_APPROVAL"]:
                return MovementResult(
                    success=False,
                    message=f"Reserva nao pode ser cancelada. Status: {reservation.get('status')}",
                )

            # Update status
            now = now_iso()
            self.db.update_item(
                pk=f"{EntityPrefix.RESERVATION}{reservation_id}",
                sk="METADATA",
                updates={
                    "status": "CANCELLED",
                    "cancelled_by": cancelled_by,
                    "cancelled_at": now,
                    "cancellation_reason": reason,
                    "GSI4_PK": "STATUS#CANCELLED",
                    "GSI4_SK": now,
                },
            )

            # Release reserved balance (if was active)
            if reservation.get("status") == "ACTIVE":
                await self._update_reserved_balance(
                    part_number=reservation["part_number"],
                    location_id=reservation["source_location_id"],
                    project_id=reservation["project_id"],
                    quantity_delta=-reservation["quantity"],
                )

            log_agent_action(
                self.name, "cancel_reservation",
                entity_type="RESERVATION",
                entity_id=reservation_id,
                status="completed",
            )

            return MovementResult(
                success=True,
                movement_id=reservation_id,
                message="Reserva cancelada com sucesso",
                data={
                    "reservation_id": reservation_id,
                    "previous_status": reservation.get("status"),
                    "cancelled_at": now,
                },
            )

        except Exception as e:
            log_agent_action(
                self.name, "cancel_reservation",
                entity_type="RESERVATION",
                entity_id=reservation_id,
                status="failed",
            )
            return MovementResult(
                success=False,
                message=f"Erro ao cancelar reserva: {str(e)}",
            )

    # =========================================================================
    # Expedition Operations
    # =========================================================================

    async def process_expedition(
        self,
        reservation_id: Optional[str] = None,
        part_number: Optional[str] = None,
        quantity: int = 1,
        serial_numbers: Optional[List[str]] = None,
        source_location_id: str = "ESTOQUE_CENTRAL",
        destination: str = "",
        project_id: Optional[str] = None,
        chamado_id: Optional[str] = None,
        recipient_name: str = "",
        recipient_contact: str = "",
        shipping_method: str = "HAND_DELIVERY",
        processed_by: str = "system",
        notes: Optional[str] = None,
        evidence_keys: Optional[List[str]] = None,
    ) -> MovementResult:
        """
        Process an expedition (outgoing shipment).

        Can be based on a reservation or ad-hoc.

        Args:
            reservation_id: Optional reservation to fulfill
            part_number: Part number (required if no reservation)
            quantity: Quantity to ship
            serial_numbers: Specific serials to ship
            source_location_id: Location shipping from
            destination: Destination address/description
            project_id: Project/client
            chamado_id: Ticket ID
            recipient_name: Who will receive
            recipient_contact: Contact info
            shipping_method: How it will be shipped
            processed_by: User processing
            notes: Additional notes
            evidence_keys: S3 keys for evidence documents

        Returns:
            MovementResult with expedition details
        """
        log_agent_action(
            self.name, "process_expedition",
            entity_type="MOVEMENT",
            status="started",
        )

        try:
            # 1. If reservation, load it
            reservation = None
            if reservation_id:
                reservation = self.db.get_item(
                    pk=f"{EntityPrefix.RESERVATION}{reservation_id}",
                    sk="METADATA",
                )
                if not reservation:
                    return MovementResult(
                        success=False,
                        message=f"Reserva {reservation_id} nao encontrada",
                    )
                if reservation.get("status") != "ACTIVE":
                    return MovementResult(
                        success=False,
                        message=f"Reserva nao esta ativa. Status: {reservation.get('status')}",
                    )

                # Use reservation data
                part_number = reservation["part_number"]
                quantity = reservation["quantity"]
                project_id = reservation["project_id"]
                serial_numbers = reservation.get("serial_numbers") or serial_numbers
                source_location_id = reservation["source_location_id"]
                chamado_id = reservation.get("chamado_id") or chamado_id

            # 2. Validate required fields
            if not part_number:
                return MovementResult(
                    success=False,
                    message="part_number e obrigatorio",
                )

            # 3. Check balance
            balance = await self._get_balance(
                part_number=part_number,
                location_id=source_location_id,
                project_id=project_id,
            )

            # Check available (for non-reservation) or total (for reservation)
            check_field = "available" if not reservation_id else "total"
            if balance[check_field] < quantity:
                return MovementResult(
                    success=False,
                    message=f"Saldo insuficiente. {check_field.title()}: {balance[check_field]}, Solicitado: {quantity}",
                    data={"balance": balance},
                )

            # 4. Calculate confidence
            risk_factors = []

            # High value or quantity
            if quantity > 5:
                risk_factors.append("high_quantity")

            # Missing evidence
            if not evidence_keys:
                risk_factors.append("no_evidence_attached")

            # Missing recipient
            if not recipient_name:
                risk_factors.append("missing_recipient")

            confidence = self.calculate_confidence(
                extraction_quality=1.0,
                evidence_strength=0.9 if evidence_keys else 0.6,
                historical_match=0.9 if reservation_id else 0.7,
                risk_factors=risk_factors,
                base_risk=RiskLevel.LOW,
            )

            # 5. Create movement record
            movement_id = generate_id("EXP")
            now = now_iso()

            movement_item = {
                "PK": f"{EntityPrefix.MOVEMENT}{movement_id}",
                "SK": "METADATA",
                "entity_type": "MOVEMENT",
                "movement_id": movement_id,
                "movement_type": MovementType.EXIT,
                "part_number": part_number,
                "quantity": -quantity,  # Negative for outgoing
                "serial_numbers": serial_numbers or [],
                "source_location_id": source_location_id,
                "destination": destination,
                "project_id": project_id,
                "chamado_id": chamado_id,
                "reservation_id": reservation_id,
                "recipient_name": recipient_name,
                "recipient_contact": recipient_contact,
                "shipping_method": shipping_method,
                "processed_by": processed_by,
                "notes": notes,
                "evidence_keys": evidence_keys or [],
                "created_at": now,
                # GSIs
                "GSI3_PK": f"{EntityPrefix.PROJECT}{project_id}" if project_id else "PROJECT#UNASSIGNED",
                "GSI3_SK": f"MOVEMENT#{now}",
                "GSI5_PK": f"DATE#{now_yyyymm()}",
                "GSI5_SK": f"EXIT#{now}",
            }

            # 6. Save movement
            self.db.put_item(movement_item)

            # 7. Update balances
            # Decrement total balance
            await self._update_balance(
                part_number=part_number,
                location_id=source_location_id,
                project_id=project_id,
                quantity_delta=-quantity,
            )

            # If from reservation, also decrement reserved
            if reservation_id:
                await self._update_reserved_balance(
                    part_number=part_number,
                    location_id=source_location_id,
                    project_id=project_id,
                    quantity_delta=-quantity,
                )

                # Mark reservation as fulfilled
                self.db.update_item(
                    pk=f"{EntityPrefix.RESERVATION}{reservation_id}",
                    sk="METADATA",
                    updates={
                        "status": "FULFILLED",
                        "fulfilled_at": now,
                        "fulfilled_by_movement": movement_id,
                        "GSI4_PK": "STATUS#FULFILLED",
                        "GSI4_SK": now,
                    },
                )

            # 8. Update asset status if serial numbers
            for serial in (serial_numbers or []):
                await self._update_asset_status(
                    serial_number=serial,
                    new_status="IN_TRANSIT",
                    location_id=None,  # No longer in stock
                    movement_id=movement_id,
                )

            log_agent_action(
                self.name, "process_expedition",
                entity_type="MOVEMENT",
                entity_id=movement_id,
                status="completed",
            )

            return MovementResult(
                success=True,
                movement_id=movement_id,
                message=f"Expedicao processada com sucesso. {quantity}x {part_number} enviado.",
                confidence=confidence,
                data={
                    "movement_id": movement_id,
                    "movement_type": MovementType.EXIT,
                    "quantity": quantity,
                    "destination": destination,
                    "shipping_method": shipping_method,
                    "reservation_fulfilled": reservation_id,
                },
            )

        except Exception as e:
            log_agent_action(
                self.name, "process_expedition",
                entity_type="MOVEMENT",
                status="failed",
            )
            return MovementResult(
                success=False,
                message=f"Erro ao processar expedicao: {str(e)}",
            )

    # =========================================================================
    # Transfer Operations
    # =========================================================================

    async def create_transfer(
        self,
        part_number: str,
        quantity: int,
        source_location_id: str,
        destination_location_id: str,
        project_id: str,
        serial_numbers: Optional[List[str]] = None,
        requested_by: str = "system",
        notes: Optional[str] = None,
    ) -> MovementResult:
        """
        Create a transfer between locations.

        Args:
            part_number: Part number to transfer
            quantity: Quantity to transfer
            source_location_id: Source location
            destination_location_id: Destination location
            project_id: Project context
            serial_numbers: Specific serials to transfer
            requested_by: User requesting
            notes: Additional notes

        Returns:
            MovementResult with transfer details
        """
        log_agent_action(
            self.name, "create_transfer",
            entity_type="MOVEMENT",
            status="started",
        )

        try:
            # 1. Check source balance
            source_balance = await self._get_balance(
                part_number=part_number,
                location_id=source_location_id,
                project_id=project_id,
            )

            if source_balance["available"] < quantity:
                return MovementResult(
                    success=False,
                    message=f"Saldo insuficiente na origem. Disponivel: {source_balance['available']}",
                    data={"source_balance": source_balance},
                )

            # 2. Check if destination is restricted
            dest_location = self.db.get_item(
                pk=f"{EntityPrefix.LOCATION}{destination_location_id}",
                sk="METADATA",
            )

            is_restricted = dest_location and dest_location.get("restricted", False)

            # 3. Calculate confidence
            risk_factors = []
            if is_restricted:
                risk_factors.append("restricted_destination")
            if quantity > 10:
                risk_factors.append("high_quantity")

            confidence = self.calculate_confidence(
                extraction_quality=1.0,
                evidence_strength=0.9,
                historical_match=0.85,
                risk_factors=risk_factors,
                base_risk=RiskLevel.MEDIUM if is_restricted else RiskLevel.LOW,
            )

            requires_hil = is_restricted or self.should_require_hil(
                action_type="transfer",
                confidence=confidence,
            )

            # 4. Create transfer movement
            movement_id = generate_id("TRF")
            now = now_iso()

            movement_item = {
                "PK": f"{EntityPrefix.MOVEMENT}{movement_id}",
                "SK": "METADATA",
                "entity_type": "MOVEMENT",
                "movement_id": movement_id,
                "movement_type": MovementType.TRANSFER,
                "part_number": part_number,
                "quantity": quantity,
                "serial_numbers": serial_numbers or [],
                "source_location_id": source_location_id,
                "destination_location_id": destination_location_id,
                "project_id": project_id,
                "status": "PENDING_APPROVAL" if requires_hil else "COMPLETED",
                "requested_by": requested_by,
                "notes": notes,
                "created_at": now,
                # GSIs
                "GSI3_PK": f"{EntityPrefix.PROJECT}{project_id}",
                "GSI3_SK": f"MOVEMENT#{now}",
                "GSI5_PK": f"DATE#{now_yyyymm()}",
                "GSI5_SK": f"TRANSFER#{now}",
            }

            # 5. If HIL required, create task
            hil_task_id = None
            if requires_hil:
                from tools.hil_workflow import HILWorkflowManager
                hil_manager = HILWorkflowManager()

                hil_task = await hil_manager.create_task(
                    task_type=HILTaskType.APPROVAL_TRANSFER,
                    title=f"Aprovar transferencia: {part_number}",
                    description=self.format_hil_task_message(
                        action_type="transfer",
                        summary=f"Transferencia de {quantity}x {part_number}",
                        confidence=confidence,
                        details={
                            "part_number": part_number,
                            "quantity": quantity,
                            "source": source_location_id,
                            "destination": destination_location_id,
                            "restricted": is_restricted,
                        },
                    ),
                    entity_type="MOVEMENT",
                    entity_id=movement_id,
                    requested_by=requested_by,
                    payload=movement_item,
                )
                hil_task_id = hil_task.get("task_id")
                movement_item["hil_task_id"] = hil_task_id

            # 6. Save movement
            self.db.put_item(movement_item)

            # 7. If not HIL, execute transfer
            if not requires_hil:
                await self._execute_transfer(
                    movement_id=movement_id,
                    part_number=part_number,
                    quantity=quantity,
                    serial_numbers=serial_numbers,
                    source_location_id=source_location_id,
                    destination_location_id=destination_location_id,
                    project_id=project_id,
                )

            log_agent_action(
                self.name, "create_transfer",
                entity_type="MOVEMENT",
                entity_id=movement_id,
                status="completed",
            )

            return MovementResult(
                success=True,
                movement_id=movement_id,
                message="Transferencia executada" if not requires_hil else "Transferencia aguardando aprovacao",
                requires_hil=requires_hil,
                hil_task_id=hil_task_id,
                confidence=confidence,
                data={
                    "movement_id": movement_id,
                    "movement_type": MovementType.TRANSFER,
                    "source": source_location_id,
                    "destination": destination_location_id,
                },
            )

        except Exception as e:
            log_agent_action(
                self.name, "create_transfer",
                entity_type="MOVEMENT",
                status="failed",
            )
            return MovementResult(
                success=False,
                message=f"Erro ao criar transferencia: {str(e)}",
            )

    async def _execute_transfer(
        self,
        movement_id: str,
        part_number: str,
        quantity: int,
        serial_numbers: Optional[List[str]],
        source_location_id: str,
        destination_location_id: str,
        project_id: str,
    ) -> None:
        """
        Execute the balance updates for a transfer.

        Internal method called after approval (or immediately if no HIL).
        """
        # Decrement source balance
        await self._update_balance(
            part_number=part_number,
            location_id=source_location_id,
            project_id=project_id,
            quantity_delta=-quantity,
        )

        # Increment destination balance
        await self._update_balance(
            part_number=part_number,
            location_id=destination_location_id,
            project_id=project_id,
            quantity_delta=quantity,
        )

        # Update asset locations if serial numbers
        for serial in (serial_numbers or []):
            await self._update_asset_status(
                serial_number=serial,
                new_status="IN_STOCK",
                location_id=destination_location_id,
                movement_id=movement_id,
            )

    # =========================================================================
    # Return (Reversa) Operations
    # =========================================================================

    async def process_return(
        self,
        part_number: str,
        quantity: int,
        serial_numbers: Optional[List[str]] = None,
        destination_location_id: str = "ESTOQUE_CENTRAL",
        project_id: str = "",
        chamado_id: Optional[str] = None,
        original_expedition_id: Optional[str] = None,
        return_reason: str = "",
        condition: str = "GOOD",  # GOOD, DAMAGED, DEFECTIVE
        processed_by: str = "system",
        notes: Optional[str] = None,
    ) -> MovementResult:
        """
        Process a return (reversa).

        Args:
            part_number: Part number being returned
            quantity: Quantity returned
            serial_numbers: Serial numbers returned
            destination_location_id: Where to receive
            project_id: Project context
            chamado_id: Related ticket
            original_expedition_id: Original outgoing movement
            return_reason: Why returned
            condition: Item condition
            processed_by: User processing
            notes: Additional notes

        Returns:
            MovementResult with return details
        """
        log_agent_action(
            self.name, "process_return",
            entity_type="MOVEMENT",
            status="started",
        )

        try:
            # 1. Calculate confidence
            risk_factors = []

            if condition != "GOOD":
                risk_factors.append(f"condition_{condition.lower()}")

            if not original_expedition_id:
                risk_factors.append("no_original_expedition")

            confidence = self.calculate_confidence(
                extraction_quality=1.0,
                evidence_strength=0.9 if original_expedition_id else 0.6,
                historical_match=0.85,
                risk_factors=risk_factors,
                base_risk=RiskLevel.LOW,
            )

            # 2. Create movement record
            movement_id = generate_id("RET")
            now = now_iso()

            movement_item = {
                "PK": f"{EntityPrefix.MOVEMENT}{movement_id}",
                "SK": "METADATA",
                "entity_type": "MOVEMENT",
                "movement_id": movement_id,
                "movement_type": MovementType.RETURN,
                "part_number": part_number,
                "quantity": quantity,  # Positive for incoming
                "serial_numbers": serial_numbers or [],
                "destination_location_id": destination_location_id,
                "project_id": project_id,
                "chamado_id": chamado_id,
                "original_expedition_id": original_expedition_id,
                "return_reason": return_reason,
                "condition": condition,
                "processed_by": processed_by,
                "notes": notes,
                "created_at": now,
                # GSIs
                "GSI3_PK": f"{EntityPrefix.PROJECT}{project_id}" if project_id else "PROJECT#UNASSIGNED",
                "GSI3_SK": f"MOVEMENT#{now}",
                "GSI5_PK": f"DATE#{now_yyyymm()}",
                "GSI5_SK": f"RETURN#{now}",
            }

            # 3. Save movement
            self.db.put_item(movement_item)

            # 4. Update balance
            await self._update_balance(
                part_number=part_number,
                location_id=destination_location_id,
                project_id=project_id,
                quantity_delta=quantity,
            )

            # 5. Update asset status if serial numbers
            status_map = {
                "GOOD": "IN_STOCK",
                "DAMAGED": "DAMAGED",
                "DEFECTIVE": "DEFECTIVE",
            }
            new_status = status_map.get(condition, "IN_STOCK")

            for serial in (serial_numbers or []):
                await self._update_asset_status(
                    serial_number=serial,
                    new_status=new_status,
                    location_id=destination_location_id,
                    movement_id=movement_id,
                )

            log_agent_action(
                self.name, "process_return",
                entity_type="MOVEMENT",
                entity_id=movement_id,
                status="completed",
            )

            return MovementResult(
                success=True,
                movement_id=movement_id,
                message=f"Reversa processada com sucesso. {quantity}x {part_number} recebido.",
                confidence=confidence,
                data={
                    "movement_id": movement_id,
                    "movement_type": MovementType.RETURN,
                    "quantity": quantity,
                    "condition": condition,
                    "destination": destination_location_id,
                },
            )

        except Exception as e:
            log_agent_action(
                self.name, "process_return",
                entity_type="MOVEMENT",
                status="failed",
            )
            return MovementResult(
                success=False,
                message=f"Erro ao processar reversa: {str(e)}",
            )

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def query_balance(
        self,
        part_number: str,
        location_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Query stock balance for a part number.

        Args:
            part_number: Part number to query
            location_id: Optional location filter
            project_id: Optional project filter

        Returns:
            Balance information
        """
        log_agent_action(
            self.name, "query_balance",
            entity_type="BALANCE",
            status="started",
        )

        try:
            balance = await self._get_balance(
                part_number=part_number,
                location_id=location_id,
                project_id=project_id,
            )

            log_agent_action(
                self.name, "query_balance",
                entity_type="BALANCE",
                status="completed",
            )

            return {
                "success": True,
                "balance": balance,
            }

        except Exception as e:
            log_agent_action(
                self.name, "query_balance",
                entity_type="BALANCE",
                status="failed",
            )
            return {
                "success": False,
                "error": str(e),
            }

    async def query_asset_location(
        self,
        serial_number: str,
    ) -> Dict[str, Any]:
        """
        Find where a specific serial number is located.

        Args:
            serial_number: Serial number to find

        Returns:
            Asset location and status
        """
        log_agent_action(
            self.name, "query_asset_location",
            entity_type="ASSET",
            status="started",
        )

        try:
            asset = self.db.get_asset_by_serial(serial_number)

            if not asset:
                return {
                    "success": False,
                    "message": f"Ativo com serial {serial_number} nao encontrado",
                }

            log_agent_action(
                self.name, "query_asset_location",
                entity_type="ASSET",
                entity_id=serial_number,
                status="completed",
            )

            return {
                "success": True,
                "serial_number": serial_number,
                "location_id": asset.get("location_id"),
                "status": asset.get("status"),
                "part_number": asset.get("part_number"),
                "project_id": asset.get("project_id"),
                "last_movement_id": asset.get("last_movement_id"),
                "last_updated": asset.get("updated_at"),
            }

        except Exception as e:
            log_agent_action(
                self.name, "query_asset_location",
                entity_type="ASSET",
                status="failed",
            )
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _get_balance(
        self,
        part_number: str,
        location_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get balance for a part number with optional filters.

        Returns calculated balance from projection or computed from movements.
        """
        # Build balance key
        balance_key = f"{part_number}"
        if location_id:
            balance_key += f"#{location_id}"
        if project_id:
            balance_key += f"#{project_id}"

        # Try to get from balance projection
        balance_item = self.db.get_balance(
            part_number=part_number,
            location_id=location_id or "ALL",
            project_id=project_id or "ALL",
        )

        if balance_item:
            return {
                "total": balance_item.get("quantity_total", 0),
                "reserved": balance_item.get("quantity_reserved", 0),
                "available": balance_item.get("quantity_available", 0),
                "part_number": part_number,
                "location_id": location_id,
                "project_id": project_id,
                "owner_project_id": balance_item.get("owner_project_id"),
                "last_updated": balance_item.get("updated_at"),
            }

        # Return zero balance if not found
        return {
            "total": 0,
            "reserved": 0,
            "available": 0,
            "part_number": part_number,
            "location_id": location_id,
            "project_id": project_id,
        }

    async def _update_balance(
        self,
        part_number: str,
        location_id: str,
        project_id: str,
        quantity_delta: int,
    ) -> None:
        """
        Update total balance atomically.
        """
        self.db.update_balance(
            part_number=part_number,
            location_id=location_id,
            project_id=project_id,
            quantity_delta=quantity_delta,
            reserved_delta=0,
        )

    async def _update_reserved_balance(
        self,
        part_number: str,
        location_id: str,
        project_id: str,
        quantity_delta: int,
    ) -> None:
        """
        Update reserved balance atomically.
        """
        self.db.update_balance(
            part_number=part_number,
            location_id=location_id,
            project_id=project_id,
            quantity_delta=0,
            reserved_delta=quantity_delta,
        )

    async def _update_asset_status(
        self,
        serial_number: str,
        new_status: str,
        location_id: Optional[str],
        movement_id: str,
    ) -> None:
        """
        Update asset status and location after movement.
        """
        now = now_iso()

        asset = self.db.get_asset_by_serial(serial_number)
        if not asset:
            return

        updates = {
            "status": new_status,
            "last_movement_id": movement_id,
            "updated_at": now,
            "GSI4_PK": f"STATUS#{new_status}",
            "GSI4_SK": now,
        }

        if location_id:
            updates["location_id"] = location_id
            updates["GSI2_PK"] = f"{EntityPrefix.LOCATION}{location_id}"
            updates["GSI2_SK"] = f"ASSET#{serial_number}"

        self.db.update_item(
            pk=asset["PK"],
            sk=asset["SK"],
            updates=updates,
        )


# =============================================================================
# Lazy Import for datetime
# =============================================================================
from datetime import datetime
