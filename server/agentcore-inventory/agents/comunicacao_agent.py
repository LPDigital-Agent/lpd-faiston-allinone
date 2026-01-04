# =============================================================================
# Comunicacao Agent - Faiston SGA Inventory
# =============================================================================
# Agent for notifications and technician communication.
#
# Features:
# - Send notifications for pending tasks
# - Remind technicians about pending reversals
# - Generate confirmation requests
# - Track communication history
# - Queue messages for delivery
#
# Module: Gestao de Ativos -> Gestao de Estoque
# Model: Gemini 3.0 Pro (MANDATORY per CLAUDE.md)
#
# Note: WhatsApp integration is planned for future sprints.
# Current implementation supports internal notifications and email.
# =============================================================================

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

from .base_agent import BaseInventoryAgent, ConfidenceScore
from .utils import (
    EntityPrefix,
    generate_id,
    now_iso,
    log_agent_action,
)


# =============================================================================
# Agent System Prompt
# =============================================================================

COMUNICACAO_AGENT_INSTRUCTION = """
Voce e o ComunicacaoAgent, agente de IA responsavel pela comunicacao
no sistema Faiston SGA (Sistema de Gestao de Ativos).

## Suas Responsabilidades

1. **Notificacoes**: Enviar alertas sobre tarefas pendentes
2. **Lembretes**: Lembrar tecnicos sobre reversas pendentes
3. **Confirmacoes**: Solicitar confirmacao de recebimento
4. **Escalacoes**: Notificar sobre prazos excedidos
5. **Historico**: Manter registro de comunicacoes

## Tipos de Comunicacao

### Notificacoes Internas (Sistema)
- Alertas de tarefas pendentes
- Confirmacao de operacoes
- Avisos de divergencias
- Lembrar sobre TTLs proximos de expirar

### Email
- Resumo diario de tarefas
- Alertas de alta prioridade
- Relatorios automaticos

### WhatsApp (Futuro)
- Confirmacao de recebimento
- Lembretes de reversa
- Respostas rapidas com botoes

## Regras de Comunicacao

### Prioridade de Envio
| Prioridade | Canal | Frequencia Max |
|------------|-------|----------------|
| URGENTE | Todos | Imediato |
| ALTA | Email + Sistema | 1/hora |
| MEDIA | Sistema | 1/dia |
| BAIXA | Sistema | Agregado diario |

### Horarios de Envio
- Notificacoes urgentes: 24/7
- Notificacoes normais: 8h-18h dias uteis
- Resumos: 8h dias uteis

### Nao Perturbe
- Respeitar configuracao de DND do usuario
- Agregar notificacoes em horario de DND
- Enviar agregado quando DND terminar

## Formato de Resposta

Responda SEMPRE em JSON estruturado:
```json
{
  "action": "send_notification|send_reminder|request_confirmation",
  "status": "sent|queued|failed",
  "message_id": "...",
  "channels": ["system", "email"],
  "scheduled_at": "..."
}
```

## Contexto

Voce gerencia a comunicacao entre o sistema e os usuarios.
Tecnicos precisam ser lembrados sobre reversas pendentes.
Gestores precisam saber sobre tarefas que requerem aprovacao.
Tudo deve ser registrado para auditoria.
"""


# =============================================================================
# Communication Types
# =============================================================================


class MessageChannel(Enum):
    """Available communication channels."""
    SYSTEM = "system"  # In-app notification
    EMAIL = "email"  # Email notification
    WHATSAPP = "whatsapp"  # WhatsApp (future)
    SMS = "sms"  # SMS (future)


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class MessageStatus(Enum):
    """Message delivery status."""
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


class MessageType(Enum):
    """Types of messages."""
    TASK_NOTIFICATION = "task_notification"
    REVERSAL_REMINDER = "reversal_reminder"
    RECEIPT_CONFIRMATION = "receipt_confirmation"
    APPROVAL_REQUEST = "approval_request"
    EXPIRATION_WARNING = "expiration_warning"
    DIVERGENCE_ALERT = "divergence_alert"
    DAILY_SUMMARY = "daily_summary"
    ESCALATION = "escalation"


# =============================================================================
# Message Result
# =============================================================================


@dataclass
class MessageResult:
    """Result of message operation."""
    success: bool
    message_id: Optional[str] = None
    status: str = "queued"
    channels: List[str] = None
    scheduled_at: Optional[str] = None
    error: Optional[str] = None

    def __post_init__(self):
        self.channels = self.channels or []

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "success": self.success,
            "status": self.status,
            "channels": self.channels,
        }
        if self.message_id:
            result["message_id"] = self.message_id
        if self.scheduled_at:
            result["scheduled_at"] = self.scheduled_at
        if self.error:
            result["error"] = self.error
        return result


# =============================================================================
# Comunicacao Agent
# =============================================================================


class ComunicacaoAgent(BaseInventoryAgent):
    """
    Agent for notifications and communication.

    Manages all outbound communication including notifications,
    reminders, and confirmation requests.
    """

    # Business hours for non-urgent messages
    BUSINESS_HOURS_START = 8
    BUSINESS_HOURS_END = 18

    # Reminder intervals (hours)
    REVERSAL_REMINDER_INTERVAL = 24
    TASK_REMINDER_INTERVAL = 4
    EXPIRATION_WARNING_HOURS = 24

    def __init__(self):
        """Initialize the Comunicacao Agent."""
        super().__init__(
            name="ComunicacaoAgent",
            instruction=COMUNICACAO_AGENT_INSTRUCTION,
            description="Comunicacao e notificacoes do sistema de estoque",
        )
        self._db_client = None

    @property
    def db(self):
        """Lazy-load DynamoDB client."""
        if self._db_client is None:
            from tools.dynamodb_client import SGADynamoDBClient
            self._db_client = SGADynamoDBClient()
        return self._db_client

    # =========================================================================
    # Notification Sending
    # =========================================================================

    async def send_notification(
        self,
        recipient_id: str,
        message_type: str,
        title: str,
        body: str,
        priority: str = MessagePriority.MEDIUM.value,
        channels: Optional[List[str]] = None,
        related_entity_type: Optional[str] = None,
        related_entity_id: Optional[str] = None,
        action_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MessageResult:
        """
        Send a notification to a user.

        Args:
            recipient_id: User ID to notify
            message_type: Type of message
            title: Notification title
            body: Notification body
            priority: Priority level
            channels: Channels to use (default based on priority)
            related_entity_type: Related entity type for deep linking
            related_entity_id: Related entity ID
            action_url: URL for action button
            metadata: Additional metadata

        Returns:
            MessageResult with delivery status
        """
        log_agent_action(
            self.name, "send_notification",
            entity_type="MESSAGE",
            status="started",
        )

        try:
            # Determine channels based on priority if not specified
            if not channels:
                channels = self._get_channels_for_priority(priority)

            now = now_iso()
            message_id = generate_id("MSG")

            # Check if should send now or queue
            should_queue = not self._is_business_hours() and priority not in [
                MessagePriority.URGENT.value,
                MessagePriority.HIGH.value,
            ]

            scheduled_at = None
            if should_queue:
                scheduled_at = self._get_next_business_hour()

            # Create message record
            message_item = {
                "PK": f"MESSAGE#{message_id}",
                "SK": "METADATA",
                "entity_type": "NOTIFICATION",
                "message_id": message_id,
                "message_type": message_type,
                "recipient_id": recipient_id,
                "title": title,
                "body": body,
                "priority": priority,
                "channels": channels,
                "status": MessageStatus.QUEUED.value if should_queue else MessageStatus.SENT.value,
                "scheduled_at": scheduled_at,
                "related_entity_type": related_entity_type,
                "related_entity_id": related_entity_id,
                "action_url": action_url,
                "metadata": metadata or {},
                "created_at": now,
                "sent_at": None if should_queue else now,
                # GSIs
                "GSI4_PK": f"RECIPIENT#{recipient_id}",
                "GSI4_SK": now,
            }

            self.db.put_item(message_item)

            # Send via each channel (if not queued)
            if not should_queue:
                for channel in channels:
                    await self._deliver_to_channel(
                        channel=channel,
                        recipient_id=recipient_id,
                        title=title,
                        body=body,
                        action_url=action_url,
                    )

            log_agent_action(
                self.name, "send_notification",
                entity_type="MESSAGE",
                entity_id=message_id,
                status="completed",
            )

            return MessageResult(
                success=True,
                message_id=message_id,
                status=MessageStatus.QUEUED.value if should_queue else MessageStatus.SENT.value,
                channels=channels,
                scheduled_at=scheduled_at,
            )

        except Exception as e:
            log_agent_action(
                self.name, "send_notification",
                entity_type="MESSAGE",
                status="failed",
            )
            return MessageResult(
                success=False,
                status=MessageStatus.FAILED.value,
                error=str(e),
            )

    def _get_channels_for_priority(self, priority: str) -> List[str]:
        """Get default channels based on priority."""
        if priority == MessagePriority.URGENT.value:
            return [MessageChannel.SYSTEM.value, MessageChannel.EMAIL.value]
        elif priority == MessagePriority.HIGH.value:
            return [MessageChannel.SYSTEM.value, MessageChannel.EMAIL.value]
        elif priority == MessagePriority.MEDIUM.value:
            return [MessageChannel.SYSTEM.value]
        else:
            return [MessageChannel.SYSTEM.value]

    def _is_business_hours(self) -> bool:
        """Check if current time is within business hours."""
        now = datetime.utcnow()
        hour = now.hour
        weekday = now.weekday()

        # Weekend
        if weekday >= 5:
            return False

        # Outside business hours
        if hour < self.BUSINESS_HOURS_START or hour >= self.BUSINESS_HOURS_END:
            return False

        return True

    def _get_next_business_hour(self) -> str:
        """Get next business hour timestamp."""
        now = datetime.utcnow()
        next_time = now

        # If weekend, move to Monday
        while next_time.weekday() >= 5:
            next_time += timedelta(days=1)

        # Set to business start
        next_time = next_time.replace(
            hour=self.BUSINESS_HOURS_START,
            minute=0,
            second=0,
            microsecond=0,
        )

        # If already past business hours, move to next day
        if now > next_time:
            next_time += timedelta(days=1)
            while next_time.weekday() >= 5:
                next_time += timedelta(days=1)

        return next_time.isoformat() + "Z"

    async def _deliver_to_channel(
        self,
        channel: str,
        recipient_id: str,
        title: str,
        body: str,
        action_url: Optional[str] = None,
    ) -> bool:
        """
        Deliver message to a specific channel.

        This is a placeholder - actual implementations would integrate
        with email services, WhatsApp API, etc.
        """
        if channel == MessageChannel.SYSTEM.value:
            # System notifications are stored in DB, delivered via frontend
            print(f"[SYSTEM] Notification for {recipient_id}: {title}")
            return True

        elif channel == MessageChannel.EMAIL.value:
            # Email integration placeholder
            print(f"[EMAIL] Would send to {recipient_id}: {title}")
            # In production: await send_email(recipient_id, title, body)
            return True

        elif channel == MessageChannel.WHATSAPP.value:
            # WhatsApp integration placeholder (future)
            print(f"[WHATSAPP] Would send to {recipient_id}: {title}")
            return False

        return False

    # =========================================================================
    # Specific Notification Types
    # =========================================================================

    async def send_reversal_reminder(
        self,
        technician_id: str,
        expedition_id: str,
        part_number: str,
        quantity: int,
        days_pending: int,
        recipient_name: str = "",
    ) -> MessageResult:
        """
        Send reminder about pending reversal.

        Args:
            technician_id: Technician user ID
            expedition_id: Original expedition movement ID
            part_number: Part number to return
            quantity: Quantity to return
            days_pending: Days since expedition
            recipient_name: Technician name for personalization

        Returns:
            MessageResult
        """
        title = f"Lembrete: Reversa pendente - {part_number}"
        body = f"""
Ola{f', {recipient_name}' if recipient_name else ''}!

Identificamos que existe material pendente de devolucao:

**Part Number**: {part_number}
**Quantidade**: {quantity}
**Dias Pendente**: {days_pending}
**Referencia**: {expedition_id}

Por favor, providencie a devolucao o mais breve possivel.

Em caso de duvidas, entre em contato com o setor de estoque.
        """.strip()

        # Increase priority based on days pending
        if days_pending > 14:
            priority = MessagePriority.HIGH.value
        elif days_pending > 7:
            priority = MessagePriority.MEDIUM.value
        else:
            priority = MessagePriority.LOW.value

        return await self.send_notification(
            recipient_id=technician_id,
            message_type=MessageType.REVERSAL_REMINDER.value,
            title=title,
            body=body,
            priority=priority,
            related_entity_type="MOVEMENT",
            related_entity_id=expedition_id,
            action_url=f"/estoque/movimentacoes/{expedition_id}",
            metadata={
                "part_number": part_number,
                "quantity": quantity,
                "days_pending": days_pending,
            },
        )

    async def send_approval_request(
        self,
        approver_id: str,
        task_id: str,
        task_type: str,
        summary: str,
        requested_by: str,
        priority: str = MessagePriority.HIGH.value,
    ) -> MessageResult:
        """
        Send approval request notification.

        Args:
            approver_id: User who should approve
            task_id: HIL task ID
            task_type: Type of approval
            summary: Brief summary
            requested_by: Who requested
            priority: Priority level

        Returns:
            MessageResult
        """
        title = f"Aprovacao Necessaria: {task_type}"
        body = f"""
Uma nova solicitacao de aprovacao requer sua atencao:

**Tipo**: {task_type}
**Resumo**: {summary}
**Solicitado por**: {requested_by}

Acesse o sistema para revisar e aprovar/rejeitar.
        """.strip()

        return await self.send_notification(
            recipient_id=approver_id,
            message_type=MessageType.APPROVAL_REQUEST.value,
            title=title,
            body=body,
            priority=priority,
            related_entity_type="HIL_TASK",
            related_entity_id=task_id,
            action_url=f"/estoque/tarefas/{task_id}",
            metadata={
                "task_type": task_type,
                "requested_by": requested_by,
            },
        )

    async def send_receipt_confirmation_request(
        self,
        recipient_id: str,
        movement_id: str,
        part_number: str,
        quantity: int,
        sender_name: str = "",
    ) -> MessageResult:
        """
        Request confirmation of receipt.

        Args:
            recipient_id: Who should confirm
            movement_id: Movement ID
            part_number: Part number received
            quantity: Quantity
            sender_name: Who sent

        Returns:
            MessageResult
        """
        title = f"Confirme Recebimento: {part_number}"
        body = f"""
Por favor, confirme o recebimento do seguinte material:

**Part Number**: {part_number}
**Quantidade**: {quantity}
{f'**Enviado por**: {sender_name}' if sender_name else ''}

Clique no link abaixo para confirmar ou reportar divergencia.
        """.strip()

        return await self.send_notification(
            recipient_id=recipient_id,
            message_type=MessageType.RECEIPT_CONFIRMATION.value,
            title=title,
            body=body,
            priority=MessagePriority.HIGH.value,
            related_entity_type="MOVEMENT",
            related_entity_id=movement_id,
            action_url=f"/estoque/confirmar-recebimento/{movement_id}",
            metadata={
                "part_number": part_number,
                "quantity": quantity,
            },
        )

    async def send_expiration_warning(
        self,
        recipient_id: str,
        entity_type: str,
        entity_id: str,
        entity_description: str,
        expires_at: str,
        hours_remaining: int,
    ) -> MessageResult:
        """
        Warn about upcoming expiration.

        Args:
            recipient_id: User to notify
            entity_type: Type of expiring entity
            entity_id: Entity ID
            entity_description: Description
            expires_at: Expiration timestamp
            hours_remaining: Hours until expiration

        Returns:
            MessageResult
        """
        title = f"Aviso: {entity_description} expira em {hours_remaining}h"
        body = f"""
O seguinte item esta proximo de expirar:

**Tipo**: {entity_type}
**Descricao**: {entity_description}
**Expira em**: {expires_at}
**Tempo restante**: {hours_remaining} horas

Tome acao antes da expiracao.
        """.strip()

        priority = MessagePriority.URGENT.value if hours_remaining < 4 else MessagePriority.HIGH.value

        return await self.send_notification(
            recipient_id=recipient_id,
            message_type=MessageType.EXPIRATION_WARNING.value,
            title=title,
            body=body,
            priority=priority,
            related_entity_type=entity_type,
            related_entity_id=entity_id,
            metadata={
                "expires_at": expires_at,
                "hours_remaining": hours_remaining,
            },
        )

    async def send_divergence_alert(
        self,
        recipient_id: str,
        campaign_id: str,
        part_number: str,
        location_id: str,
        system_qty: int,
        counted_qty: int,
    ) -> MessageResult:
        """
        Alert about inventory divergence.

        Args:
            recipient_id: Manager to notify
            campaign_id: Inventory campaign
            part_number: Part number with divergence
            location_id: Location
            system_qty: System quantity
            counted_qty: Counted quantity

        Returns:
            MessageResult
        """
        diff = counted_qty - system_qty
        diff_type = "SOBRA" if diff > 0 else "FALTA"

        title = f"Divergencia de Inventario: {diff_type} de {abs(diff)} unidades"
        body = f"""
Divergencia detectada durante contagem de inventario:

**Part Number**: {part_number}
**Local**: {location_id}
**Quantidade Sistema**: {system_qty}
**Quantidade Contada**: {counted_qty}
**Diferenca**: {diff:+d} ({diff_type})

Acesse a campanha para analisar e propor ajuste.
        """.strip()

        return await self.send_notification(
            recipient_id=recipient_id,
            message_type=MessageType.DIVERGENCE_ALERT.value,
            title=title,
            body=body,
            priority=MessagePriority.HIGH.value,
            related_entity_type="CAMPAIGN",
            related_entity_id=campaign_id,
            action_url=f"/estoque/inventario/{campaign_id}",
            metadata={
                "part_number": part_number,
                "location_id": location_id,
                "difference": diff,
            },
        )

    # =========================================================================
    # Batch Operations
    # =========================================================================

    async def process_pending_reminders(self) -> Dict[str, Any]:
        """
        Process all pending reminders.

        Called periodically to send reminders for:
        - Pending reversals
        - Expiring reservations
        - Pending approvals

        Returns:
            Summary of reminders sent
        """
        log_agent_action(
            self.name, "process_pending_reminders",
            entity_type="BATCH",
            status="started",
        )

        try:
            results = {
                "reversal_reminders": 0,
                "expiration_warnings": 0,
                "approval_reminders": 0,
                "total_sent": 0,
                "errors": [],
            }

            # Process reversal reminders
            # In production, query expeditions without returns
            # and send reminders based on days pending

            # Process expiration warnings
            # Query reservations/tasks near expiration
            # and send warnings

            log_agent_action(
                self.name, "process_pending_reminders",
                entity_type="BATCH",
                status="completed",
            )

            return {
                "success": True,
                "results": results,
            }

        except Exception as e:
            log_agent_action(
                self.name, "process_pending_reminders",
                entity_type="BATCH",
                status="failed",
            )
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # Message Queries
    # =========================================================================

    def get_user_notifications(
        self,
        user_id: str,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get notifications for a user.

        Args:
            user_id: User ID
            status: Optional status filter
            limit: Maximum notifications

        Returns:
            List of notifications
        """
        notifications = self.db.query_gsi(
            index_name="GSI4",
            pk=f"RECIPIENT#{user_id}",
            limit=limit,
        )

        if status:
            notifications = [n for n in notifications if n.get("status") == status]

        return notifications

    def mark_as_read(
        self,
        message_id: str,
        user_id: str,
    ) -> bool:
        """
        Mark a notification as read.

        Args:
            message_id: Message ID
            user_id: User marking as read

        Returns:
            Success status
        """
        try:
            now = now_iso()
            self.db.update_item(
                pk=f"MESSAGE#{message_id}",
                sk="METADATA",
                updates={
                    "status": MessageStatus.READ.value,
                    "read_at": now,
                    "read_by": user_id,
                },
            )
            return True
        except Exception:
            return False
