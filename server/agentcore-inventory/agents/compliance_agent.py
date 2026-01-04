# =============================================================================
# Compliance Agent - Faiston SGA Inventory
# =============================================================================
# Agent for policy validation and compliance workflows.
#
# Features:
# - Validate operations against business rules
# - Check approval requirements
# - Manage approval hierarchies
# - Audit compliance status
# - Flag policy violations
#
# Module: Gestao de Ativos -> Gestao de Estoque
# Model: Gemini 3.0 Pro (MANDATORY per CLAUDE.md)
#
# This agent acts as a gatekeeper, ensuring all inventory operations
# comply with established policies before execution.
# =============================================================================

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import json

from .base_agent import BaseInventoryAgent, ConfidenceScore
from .utils import (
    EntityPrefix,
    MovementType,
    HILTaskType,
    RiskLevel,
    generate_id,
    now_iso,
    log_agent_action,
)


# =============================================================================
# Agent System Prompt
# =============================================================================

COMPLIANCE_AGENT_INSTRUCTION = """
Voce e o ComplianceAgent, agente de IA responsavel pela validacao de
conformidade no sistema Faiston SGA (Sistema de Gestao de Ativos).

## Suas Responsabilidades

1. **Validar Operacoes**: Verificar se operacoes seguem politicas
2. **Verificar Aprovacoes**: Garantir que aprovacoes necessarias existem
3. **Auditar Conformidade**: Identificar violacoes de politicas
4. **Gerenciar Hierarquia**: Aplicar niveis de aprovacao corretamente
5. **Alertar Anomalias**: Detectar padroes suspeitos

## Politicas de Negocio

### Niveis de Aprovacao
| Operacao | Limite Autonomo | Aprovador |
|----------|-----------------|-----------|
| Reserva mesmo projeto | Ilimitado | Autonomo |
| Reserva cross-project | R$ 0 | Gerente Projeto |
| Transferencia normal | Ilimitado | Autonomo |
| Transferencia local restrito | R$ 0 | Gerente Estoque |
| Ajuste inventario | R$ 0 | Gerente Estoque |
| Descarte | R$ 0 | Diretor |
| Entrada alto valor | R$ 5.000 | Gerente Estoque |

### Restricoes de Local
- COFRE: Apenas Gerente Estoque pode autorizar
- QUARENTENA: Entrada livre, saida requer aprovacao
- DESCARTE: Apenas via workflow de baixa

### Restricoes de Horario
- Movimentacoes fora do horario comercial (8h-18h) geram alerta
- Movimentacoes em finais de semana geram alerta

### Restricoes de Volume
- Mais de 10 movimentacoes/hora por usuario gera alerta
- Movimentacao > 50 unidades de um item gera alerta

## Formato de Resposta

Responda SEMPRE em JSON estruturado:
```json
{
  "action": "validate|check_approval|audit|flag_violation",
  "status": "compliant|non_compliant|warning",
  "message": "Descricao",
  "violations": [],
  "required_approvals": [],
  "recommendations": []
}
```

## Contexto

Voce e o guardiao das politicas de estoque.
Nenhuma operacao critica deve passar sem sua validacao.
Em caso de duvida, sempre opte pela seguranca (solicitar aprovacao).
"""


# =============================================================================
# Compliance Result
# =============================================================================


@dataclass
class ComplianceResult:
    """Result of compliance check."""
    is_compliant: bool
    status: str  # "compliant", "non_compliant", "warning"
    message: str
    violations: List[str] = None
    required_approvals: List[Dict[str, Any]] = None
    recommendations: List[str] = None
    risk_level: str = RiskLevel.LOW

    def __post_init__(self):
        self.violations = self.violations or []
        self.required_approvals = self.required_approvals or []
        self.recommendations = self.recommendations or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_compliant": self.is_compliant,
            "status": self.status,
            "message": self.message,
            "violations": self.violations,
            "required_approvals": self.required_approvals,
            "recommendations": self.recommendations,
            "risk_level": self.risk_level,
        }


# =============================================================================
# Policy Definitions
# =============================================================================


class ApprovalRole:
    """Approval role hierarchy."""
    OPERATOR = "INVENTORY_OPERATOR"
    MANAGER = "INVENTORY_MANAGER"
    SUPERVISOR = "INVENTORY_SUPERVISOR"
    DIRECTOR = "DIRECTOR"


class RestrictedLocation:
    """Locations with special restrictions."""
    COFRE = "COFRE"
    QUARENTENA = "QUARENTENA"
    DESCARTE = "DESCARTE"


# =============================================================================
# Compliance Agent
# =============================================================================


class ComplianceAgent(BaseInventoryAgent):
    """
    Agent for policy validation and compliance checks.

    Acts as gatekeeper for all inventory operations,
    ensuring they comply with business rules.
    """

    # Value thresholds
    HIGH_VALUE_THRESHOLD = 5000.0  # R$
    BULK_QUANTITY_THRESHOLD = 50  # units

    # Time restrictions (24h format)
    BUSINESS_HOURS_START = 8
    BUSINESS_HOURS_END = 18

    # Rate limits
    MAX_MOVEMENTS_PER_HOUR = 10

    def __init__(self):
        """Initialize the Compliance Agent."""
        super().__init__(
            name="ComplianceAgent",
            instruction=COMPLIANCE_AGENT_INSTRUCTION,
            description="Validacao de conformidade e politicas de estoque",
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
    # Core Validation
    # =========================================================================

    async def validate_operation(
        self,
        operation_type: str,
        part_number: str,
        quantity: int,
        source_location: Optional[str] = None,
        destination_location: Optional[str] = None,
        source_project: Optional[str] = None,
        destination_project: Optional[str] = None,
        total_value: Optional[float] = None,
        user_id: str = "system",
    ) -> ComplianceResult:
        """
        Validate an operation against compliance policies.

        Args:
            operation_type: Type of operation (ENTRY, EXIT, TRANSFER, etc.)
            part_number: Part number involved
            quantity: Quantity to move
            source_location: Source location
            destination_location: Destination location
            source_project: Source project
            destination_project: Destination project
            total_value: Total value of operation
            user_id: User performing operation

        Returns:
            ComplianceResult with validation status
        """
        log_agent_action(
            self.name, "validate_operation",
            entity_type="COMPLIANCE",
            status="started",
        )

        violations = []
        required_approvals = []
        recommendations = []
        risk_level = RiskLevel.LOW

        try:
            # 1. Check restricted locations
            location_result = self._check_location_restrictions(
                operation_type=operation_type,
                source_location=source_location,
                destination_location=destination_location,
            )
            violations.extend(location_result.get("violations", []))
            required_approvals.extend(location_result.get("approvals", []))

            # 2. Check cross-project restrictions
            if source_project and destination_project:
                if source_project != destination_project:
                    required_approvals.append({
                        "role": ApprovalRole.MANAGER,
                        "reason": "Operacao cross-project requer aprovacao",
                        "type": "cross_project",
                    })
                    risk_level = RiskLevel.MEDIUM

            # 3. Check value thresholds
            if total_value and total_value >= self.HIGH_VALUE_THRESHOLD:
                required_approvals.append({
                    "role": ApprovalRole.MANAGER,
                    "reason": f"Valor alto (R$ {total_value:,.2f})",
                    "type": "high_value",
                })
                risk_level = RiskLevel.HIGH

            # 4. Check quantity thresholds
            if quantity >= self.BULK_QUANTITY_THRESHOLD:
                recommendations.append(
                    f"Quantidade elevada ({quantity} unidades). "
                    "Considere dividir em multiplas operacoes."
                )
                risk_level = max(risk_level, RiskLevel.MEDIUM)

            # 5. Check time restrictions
            time_result = self._check_time_restrictions()
            if time_result.get("warning"):
                recommendations.append(time_result["warning"])
                risk_level = max(risk_level, RiskLevel.MEDIUM)

            # 6. Check user rate limits
            rate_result = await self._check_user_rate_limit(user_id)
            if rate_result.get("exceeded"):
                violations.append(
                    f"Usuario excedeu limite de {self.MAX_MOVEMENTS_PER_HOUR} "
                    f"movimentacoes/hora"
                )
                required_approvals.append({
                    "role": ApprovalRole.SUPERVISOR,
                    "reason": "Limite de taxa excedido",
                    "type": "rate_limit",
                })
                risk_level = RiskLevel.HIGH

            # 7. Check operation-specific rules
            op_result = self._check_operation_rules(
                operation_type=operation_type,
                quantity=quantity,
                total_value=total_value,
            )
            violations.extend(op_result.get("violations", []))
            required_approvals.extend(op_result.get("approvals", []))

            # Determine final status
            if violations:
                status = "non_compliant"
                is_compliant = False
                message = f"Operacao NAO conforme: {len(violations)} violacao(es)"
            elif required_approvals:
                status = "warning"
                is_compliant = True  # Compliant but needs approval
                message = f"Operacao requer {len(required_approvals)} aprovacao(es)"
            else:
                status = "compliant"
                is_compliant = True
                message = "Operacao conforme com todas as politicas"

            log_agent_action(
                self.name, "validate_operation",
                entity_type="COMPLIANCE",
                status="completed",
            )

            return ComplianceResult(
                is_compliant=is_compliant,
                status=status,
                message=message,
                violations=violations,
                required_approvals=required_approvals,
                recommendations=recommendations,
                risk_level=risk_level,
            )

        except Exception as e:
            log_agent_action(
                self.name, "validate_operation",
                entity_type="COMPLIANCE",
                status="failed",
            )
            return ComplianceResult(
                is_compliant=False,
                status="non_compliant",
                message=f"Erro na validacao: {str(e)}",
                violations=[f"Erro interno: {str(e)}"],
                risk_level=RiskLevel.HIGH,
            )

    def _check_location_restrictions(
        self,
        operation_type: str,
        source_location: Optional[str],
        destination_location: Optional[str],
    ) -> Dict[str, List]:
        """Check location-based restrictions."""
        violations = []
        approvals = []

        # COFRE restrictions
        if source_location == RestrictedLocation.COFRE:
            approvals.append({
                "role": ApprovalRole.MANAGER,
                "reason": "Saida de local COFRE requer aprovacao",
                "type": "restricted_location",
            })

        if destination_location == RestrictedLocation.COFRE:
            approvals.append({
                "role": ApprovalRole.MANAGER,
                "reason": "Entrada em local COFRE requer aprovacao",
                "type": "restricted_location",
            })

        # QUARENTENA restrictions
        if source_location == RestrictedLocation.QUARENTENA:
            approvals.append({
                "role": ApprovalRole.MANAGER,
                "reason": "Saida de QUARENTENA requer aprovacao",
                "type": "quarantine_exit",
            })

        # DESCARTE restrictions
        if destination_location == RestrictedLocation.DESCARTE:
            if operation_type != MovementType.DISCARD:
                violations.append(
                    "Movimentacao para DESCARTE deve usar tipo DISCARD"
                )
            approvals.append({
                "role": ApprovalRole.DIRECTOR,
                "reason": "Descarte requer aprovacao de Diretor",
                "type": "discard",
            })

        return {"violations": violations, "approvals": approvals}

    def _check_time_restrictions(self) -> Dict[str, Any]:
        """Check time-based restrictions."""
        from datetime import datetime

        now = datetime.utcnow()
        hour = now.hour
        weekday = now.weekday()

        result = {"warning": None}

        # Weekend check
        if weekday >= 5:  # Saturday = 5, Sunday = 6
            result["warning"] = (
                "Movimentacao em final de semana. "
                "Operacao sera auditada."
            )
        # Outside business hours
        elif hour < self.BUSINESS_HOURS_START or hour >= self.BUSINESS_HOURS_END:
            result["warning"] = (
                f"Movimentacao fora do horario comercial ({self.BUSINESS_HOURS_START}h-{self.BUSINESS_HOURS_END}h). "
                "Operacao sera auditada."
            )

        return result

    async def _check_user_rate_limit(self, user_id: str) -> Dict[str, Any]:
        """Check if user has exceeded rate limits."""
        # In production, this would query recent movements by user
        # For now, return not exceeded
        return {"exceeded": False, "count": 0}

    def _check_operation_rules(
        self,
        operation_type: str,
        quantity: int,
        total_value: Optional[float],
    ) -> Dict[str, List]:
        """Check operation-specific rules."""
        violations = []
        approvals = []

        # Adjustments ALWAYS need approval
        if operation_type == MovementType.ADJUSTMENT:
            approvals.append({
                "role": ApprovalRole.MANAGER,
                "reason": "Ajustes de inventario SEMPRE requerem aprovacao",
                "type": "adjustment",
            })

        # Discards ALWAYS need director approval
        if operation_type == MovementType.DISCARD:
            approvals.append({
                "role": ApprovalRole.DIRECTOR,
                "reason": "Descartes SEMPRE requerem aprovacao de Diretor",
                "type": "discard",
            })

        # Loss declarations ALWAYS need approval
        if operation_type == MovementType.LOSS:
            approvals.append({
                "role": ApprovalRole.DIRECTOR,
                "reason": "Declaracoes de extravio SEMPRE requerem aprovacao",
                "type": "loss",
            })

        return {"violations": violations, "approvals": approvals}

    # =========================================================================
    # Approval Verification
    # =========================================================================

    async def check_approval_status(
        self,
        entity_type: str,
        entity_id: str,
        required_role: str,
    ) -> Dict[str, Any]:
        """
        Check if an entity has the required approval.

        Args:
            entity_type: Type of entity (MOVEMENT, RESERVATION, etc.)
            entity_id: Entity ID
            required_role: Role that needs to have approved

        Returns:
            Approval status
        """
        log_agent_action(
            self.name, "check_approval_status",
            entity_type=entity_type,
            entity_id=entity_id,
            status="started",
        )

        try:
            from tools.hil_workflow import HILWorkflowManager

            manager = HILWorkflowManager()
            tasks = manager.get_tasks_for_entity(entity_type, entity_id)

            # Find relevant approval task
            for task in tasks:
                if task.get("status") == "APPROVED":
                    # Check if approver has required role
                    # In production, this would verify against user roles
                    return {
                        "has_approval": True,
                        "approved_by": task.get("processed_by"),
                        "approved_at": task.get("processed_at"),
                        "task_id": task.get("task_id"),
                    }

            # Check for pending tasks
            pending = [t for t in tasks if t.get("status") == "PENDING"]
            if pending:
                return {
                    "has_approval": False,
                    "status": "pending",
                    "pending_task_id": pending[0].get("task_id"),
                    "message": "Aprovacao pendente",
                }

            return {
                "has_approval": False,
                "status": "not_requested",
                "message": "Nenhuma aprovacao solicitada",
            }

        except Exception as e:
            return {
                "has_approval": False,
                "status": "error",
                "message": str(e),
            }

    # =========================================================================
    # Compliance Audit
    # =========================================================================

    async def audit_compliance(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        location_id: Optional[str] = None,
        project_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run compliance audit on historical operations.

        Args:
            start_date: Start date for audit period
            end_date: End date for audit period
            location_id: Filter by location
            project_id: Filter by project

        Returns:
            Audit report with findings
        """
        log_agent_action(
            self.name, "audit_compliance",
            entity_type="AUDIT",
            status="started",
        )

        try:
            # In production, this would query historical movements
            # and check each against policies

            report = {
                "audit_period": {
                    "start": start_date or "N/A",
                    "end": end_date or "N/A",
                },
                "scope": {
                    "location_id": location_id or "ALL",
                    "project_id": project_id or "ALL",
                },
                "summary": {
                    "total_operations": 0,
                    "compliant": 0,
                    "non_compliant": 0,
                    "warnings": 0,
                },
                "findings": [],
                "recommendations": [],
            }

            # Query movements in period (simplified)
            # In production, paginate through all movements

            log_agent_action(
                self.name, "audit_compliance",
                entity_type="AUDIT",
                status="completed",
            )

            return {
                "success": True,
                "report": report,
            }

        except Exception as e:
            log_agent_action(
                self.name, "audit_compliance",
                entity_type="AUDIT",
                status="failed",
            )
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # Violation Flagging
    # =========================================================================

    async def flag_violation(
        self,
        entity_type: str,
        entity_id: str,
        violation_type: str,
        description: str,
        severity: str = "MEDIUM",
        flagged_by: str = "system",
    ) -> Dict[str, Any]:
        """
        Flag a compliance violation for review.

        Args:
            entity_type: Type of entity with violation
            entity_id: Entity ID
            violation_type: Type of violation
            description: Detailed description
            severity: LOW, MEDIUM, HIGH, CRITICAL
            flagged_by: User/system flagging

        Returns:
            Flag confirmation
        """
        log_agent_action(
            self.name, "flag_violation",
            entity_type=entity_type,
            entity_id=entity_id,
            status="started",
        )

        try:
            now = now_iso()
            flag_id = generate_id("FLAG")

            flag_item = {
                "PK": f"FLAG#{flag_id}",
                "SK": "METADATA",
                "entity_type": "COMPLIANCE_FLAG",
                "flag_id": flag_id,
                "related_entity_type": entity_type,
                "related_entity_id": entity_id,
                "violation_type": violation_type,
                "description": description,
                "severity": severity,
                "status": "OPEN",
                "flagged_by": flagged_by,
                "created_at": now,
                # GSIs
                "GSI4_PK": "STATUS#OPEN",
                "GSI4_SK": f"{severity}#{now}",
            }

            self.db.put_item(flag_item)

            # Log to audit
            from tools.dynamodb_client import SGAAuditLogger
            audit = SGAAuditLogger()
            audit.log_action(
                action="VIOLATION_FLAGGED",
                entity_type=entity_type,
                entity_id=entity_id,
                actor=flagged_by,
                details={
                    "flag_id": flag_id,
                    "violation_type": violation_type,
                    "severity": severity,
                },
            )

            # Create HIL task for severe violations
            if severity in ["HIGH", "CRITICAL"]:
                from tools.hil_workflow import HILWorkflowManager
                hil_manager = HILWorkflowManager()

                await hil_manager.create_task(
                    task_type=HILTaskType.ESCALATION,
                    title=f"Violacao de Compliance: {violation_type}",
                    description=f"""
## Violacao de Compliance Detectada

### Detalhes
- **Tipo**: {violation_type}
- **Severidade**: {severity}
- **Entidade**: {entity_type} #{entity_id}

### Descricao
{description}

### Acao Requerida
Investigar e tomar acoes corretivas.
                    """,
                    entity_type="COMPLIANCE_FLAG",
                    entity_id=flag_id,
                    requested_by=flagged_by,
                    priority="URGENT" if severity == "CRITICAL" else "HIGH",
                )

            log_agent_action(
                self.name, "flag_violation",
                entity_type=entity_type,
                entity_id=entity_id,
                status="completed",
            )

            return {
                "success": True,
                "flag_id": flag_id,
                "severity": severity,
                "message": f"Violacao registrada com severidade {severity}",
            }

        except Exception as e:
            log_agent_action(
                self.name, "flag_violation",
                entity_type=entity_type,
                entity_id=entity_id,
                status="failed",
            )
            return {
                "success": False,
                "error": str(e),
            }

    # =========================================================================
    # Policy Queries
    # =========================================================================

    def get_approval_requirements(
        self,
        operation_type: str,
    ) -> Dict[str, Any]:
        """
        Get approval requirements for an operation type.

        Args:
            operation_type: Type of operation

        Returns:
            Approval requirements
        """
        requirements = {
            MovementType.ENTRY: {
                "default": ApprovalRole.OPERATOR,
                "high_value": ApprovalRole.MANAGER,
                "threshold": self.HIGH_VALUE_THRESHOLD,
            },
            MovementType.EXIT: {
                "default": ApprovalRole.OPERATOR,
                "restricted_location": ApprovalRole.MANAGER,
            },
            MovementType.TRANSFER: {
                "default": ApprovalRole.OPERATOR,
                "cross_project": ApprovalRole.MANAGER,
                "restricted_location": ApprovalRole.MANAGER,
            },
            MovementType.ADJUSTMENT: {
                "default": ApprovalRole.MANAGER,
                "always_required": True,
            },
            MovementType.DISCARD: {
                "default": ApprovalRole.DIRECTOR,
                "always_required": True,
            },
            MovementType.LOSS: {
                "default": ApprovalRole.DIRECTOR,
                "always_required": True,
            },
            MovementType.RESERVATION: {
                "default": ApprovalRole.OPERATOR,
                "cross_project": ApprovalRole.MANAGER,
            },
        }

        return requirements.get(operation_type, {
            "default": ApprovalRole.OPERATOR,
        })
