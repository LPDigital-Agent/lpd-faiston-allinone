# =============================================================================
# Reconciliacao Agent - Faiston SGA Inventory
# =============================================================================
# Agent for inventory reconciliation and counting campaigns.
#
# Features:
# - Start and manage inventory counting campaigns
# - Process count submissions from mobile devices
# - Detect divergences between system and physical counts
# - Propose adjustments (ALWAYS requires HIL)
# - Analyze patterns in divergences
#
# Module: Gestao de Ativos -> Gestao de Estoque
# Model: Gemini 3.0 Pro (MANDATORY per CLAUDE.md)
#
# Human-in-the-Loop Matrix:
# - Counting campaign start: AUTONOMOUS (operator can start)
# - Count submission: AUTONOMOUS
# - Divergence analysis: AUTONOMOUS
# - Adjustment proposal: ALWAYS HIL (manager approval required)
# =============================================================================

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
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
    now_yyyymmdd,
    log_agent_action,
    parse_json_safe,
)


# =============================================================================
# Agent System Prompt
# =============================================================================

RECONCILIACAO_AGENT_INSTRUCTION = """
Voce e o ReconciliacaoAgent, agente de IA responsavel pela reconciliacao
de inventario no sistema Faiston SGA (Sistema de Gestao de Ativos).

## Suas Responsabilidades

1. **Campanhas de Inventario**: Criar e gerenciar sessoes de contagem
2. **Processamento de Contagens**: Receber e validar contagens fisicas
3. **Deteccao de Divergencias**: Identificar diferencas entre sistema e fisico
4. **Proposta de Ajustes**: Sugerir acertos de estoque (sempre com aprovacao)
5. **Analise de Padroes**: Identificar tendencias e causas raiz

## Regras de Negocio

### Campanhas de Inventario
- Campanha agrupa multiplas sessoes de contagem
- Pode ser por local, projeto, part number ou combinacao
- Tem periodo de execucao definido
- Gera relatorio de divergencias ao final

### Contagem
- Operador escaneia/digita serial ou quantidade
- Sistema registra timestamp e operador
- Contagem dupla (duas pessoas) para itens de alto valor
- Foto/evidencia opcional para divergencias

### Divergencias
- POSITIVA: Fisico > Sistema (sobra)
- NEGATIVA: Fisico < Sistema (falta)
- Todas geram alerta automatico
- Grandes divergencias (>10%) requerem investigacao

### Ajustes
- NUNCA sao automaticos
- SEMPRE criam tarefa HIL para aprovacao
- Ajuste positivo: entrada de material
- Ajuste negativo: baixa por extravio/erro

## Formato de Resposta

Responda SEMPRE em JSON estruturado:
```json
{
  "action": "start_campaign|submit_count|analyze_divergences|propose_adjustment",
  "status": "success|pending_approval|error",
  "message": "Descricao da acao",
  "data": { ... }
}
```

## Contexto

Voce opera em um ambiente de gestao de estoque de equipamentos de TI.
Inventarios fisicos sao realizados periodicamente para garantir acuracia.
Divergencias podem indicar furto, erro de lancamento, ou falha de processo.
"""


# =============================================================================
# Campaign Status
# =============================================================================


class CampaignStatus:
    """Inventory campaign status values."""
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class CountStatus:
    """Individual count status values."""
    PENDING = "PENDING"
    COUNTED = "COUNTED"
    VERIFIED = "VERIFIED"
    DIVERGENT = "DIVERGENT"


class DivergenceType:
    """Divergence classification."""
    POSITIVE = "POSITIVE"  # Fisico > Sistema (sobra)
    NEGATIVE = "NEGATIVE"  # Fisico < Sistema (falta)
    SERIAL_MISMATCH = "SERIAL_MISMATCH"  # Serial diferente
    LOCATION_MISMATCH = "LOCATION_MISMATCH"  # Local diferente


# =============================================================================
# Result Data Classes
# =============================================================================


@dataclass
class CampaignResult:
    """Result of campaign operations."""
    success: bool
    campaign_id: Optional[str] = None
    message: str = ""
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "success": self.success,
            "message": self.message,
        }
        if self.campaign_id:
            result["campaign_id"] = self.campaign_id
        if self.data:
            result["data"] = self.data
        return result


@dataclass
class Divergence:
    """Represents a divergence between system and physical count."""
    part_number: str
    location_id: str
    system_quantity: int
    counted_quantity: int
    divergence_type: str
    divergence_quantity: int
    serial_numbers_system: List[str] = field(default_factory=list)
    serial_numbers_counted: List[str] = field(default_factory=list)
    percentage: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "part_number": self.part_number,
            "location_id": self.location_id,
            "system_quantity": self.system_quantity,
            "counted_quantity": self.counted_quantity,
            "divergence_type": self.divergence_type,
            "divergence_quantity": self.divergence_quantity,
            "percentage": round(self.percentage, 2),
            "serial_numbers_system": self.serial_numbers_system,
            "serial_numbers_counted": self.serial_numbers_counted,
        }


# =============================================================================
# Reconciliacao Agent
# =============================================================================


class ReconciliacaoAgent(BaseInventoryAgent):
    """
    Agent for inventory reconciliation and counting.

    Manages counting campaigns, processes submissions,
    detects divergences, and proposes adjustments (with HIL).
    """

    # Threshold for significant divergence (percentage)
    SIGNIFICANT_DIVERGENCE_THRESHOLD = 0.10  # 10%

    def __init__(self):
        """Initialize the Reconciliacao Agent."""
        super().__init__(
            name="ReconciliacaoAgent",
            instruction=RECONCILIACAO_AGENT_INSTRUCTION,
            description="Reconciliacao de inventario e campanhas de contagem",
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
    # Campaign Management
    # =========================================================================

    async def start_campaign(
        self,
        name: str,
        description: str = "",
        location_ids: Optional[List[str]] = None,
        project_ids: Optional[List[str]] = None,
        part_numbers: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        created_by: str = "system",
        require_double_count: bool = False,
    ) -> CampaignResult:
        """
        Start a new inventory counting campaign.

        Args:
            name: Campaign name
            description: Campaign description
            location_ids: Locations to count (None = all)
            project_ids: Projects to include (None = all)
            part_numbers: Part numbers to count (None = all)
            start_date: Start date (ISO format)
            end_date: End date (ISO format)
            created_by: User creating campaign
            require_double_count: Require two counters for verification

        Returns:
            CampaignResult with campaign details
        """
        log_agent_action(
            self.name, "start_campaign",
            entity_type="CAMPAIGN",
            status="started",
        )

        try:
            campaign_id = generate_id("INV")
            now = now_iso()

            # Build scope based on filters
            scope = {
                "location_ids": location_ids or ["ALL"],
                "project_ids": project_ids or ["ALL"],
                "part_numbers": part_numbers or ["ALL"],
            }

            # Calculate items to count
            items_to_count = await self._generate_count_items(
                location_ids=location_ids,
                project_ids=project_ids,
                part_numbers=part_numbers,
            )

            campaign_item = {
                "PK": f"CAMPAIGN#{campaign_id}",
                "SK": "METADATA",
                "entity_type": "INVENTORY_CAMPAIGN",
                "campaign_id": campaign_id,
                "name": name,
                "description": description,
                "scope": scope,
                "status": CampaignStatus.ACTIVE,
                "start_date": start_date or now,
                "end_date": end_date,
                "require_double_count": require_double_count,
                "total_items": len(items_to_count),
                "counted_items": 0,
                "divergent_items": 0,
                "created_by": created_by,
                "created_at": now,
                # GSIs
                "GSI4_PK": f"STATUS#{CampaignStatus.ACTIVE}",
                "GSI4_SK": now,
            }

            # Save campaign
            self.db.put_item(campaign_item)

            # Create count items
            for item in items_to_count:
                count_item = {
                    "PK": f"CAMPAIGN#{campaign_id}",
                    "SK": f"COUNT#{item['part_number']}#{item['location_id']}",
                    "entity_type": "COUNT_ITEM",
                    "campaign_id": campaign_id,
                    "part_number": item["part_number"],
                    "location_id": item["location_id"],
                    "project_id": item.get("project_id", ""),
                    "system_quantity": item["system_quantity"],
                    "system_serials": item.get("system_serials", []),
                    "status": CountStatus.PENDING,
                    "counted_quantity": None,
                    "counted_serials": [],
                    "counted_by": None,
                    "counted_at": None,
                    "verified_by": None,
                    "verified_at": None,
                    "created_at": now,
                }
                self.db.put_item(count_item)

            log_agent_action(
                self.name, "start_campaign",
                entity_type="CAMPAIGN",
                entity_id=campaign_id,
                status="completed",
            )

            return CampaignResult(
                success=True,
                campaign_id=campaign_id,
                message=f"Campanha '{name}' criada com {len(items_to_count)} itens para contagem",
                data={
                    "total_items": len(items_to_count),
                    "status": CampaignStatus.ACTIVE,
                    "scope": scope,
                },
            )

        except Exception as e:
            log_agent_action(
                self.name, "start_campaign",
                entity_type="CAMPAIGN",
                status="failed",
            )
            return CampaignResult(
                success=False,
                message=f"Erro ao criar campanha: {str(e)}",
            )

    async def _generate_count_items(
        self,
        location_ids: Optional[List[str]],
        project_ids: Optional[List[str]],
        part_numbers: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """
        Generate list of items to be counted based on filters.

        Queries current balances and assets to create count targets.
        """
        items = []

        # Query balances based on filters
        if location_ids:
            for loc_id in location_ids:
                balances = self.db.query_gsi(
                    index_name="GSI2",
                    pk=f"{EntityPrefix.LOCATION}{loc_id}",
                    sk_prefix="BALANCE#",
                    limit=500,
                )
                for bal in balances:
                    if part_numbers and bal.get("part_number") not in part_numbers:
                        continue
                    if project_ids and bal.get("project_id") not in project_ids:
                        continue

                    # Get serials for this balance
                    serials = await self._get_serials_for_balance(
                        part_number=bal.get("part_number"),
                        location_id=loc_id,
                    )

                    items.append({
                        "part_number": bal.get("part_number"),
                        "location_id": loc_id,
                        "project_id": bal.get("project_id"),
                        "system_quantity": bal.get("quantity_total", 0),
                        "system_serials": serials,
                    })
        else:
            # Query all active balances
            # In production, this would be paginated
            pass

        return items

    async def _get_serials_for_balance(
        self,
        part_number: str,
        location_id: str,
    ) -> List[str]:
        """Get serial numbers for a balance position."""
        assets = self.db.get_assets_by_location(location_id, limit=500)
        serials = [
            a["serial_number"]
            for a in assets
            if a.get("part_number") == part_number
        ]
        return serials

    def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """Get campaign details."""
        return self.db.get_item(
            pk=f"CAMPAIGN#{campaign_id}",
            sk="METADATA",
        )

    def get_campaign_items(
        self,
        campaign_id: str,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get count items for a campaign."""
        items = self.db.query_pk(
            pk=f"CAMPAIGN#{campaign_id}",
            sk_prefix="COUNT#",
            limit=1000,
        )

        if status:
            items = [i for i in items if i.get("status") == status]

        return items

    # =========================================================================
    # Count Submission
    # =========================================================================

    async def submit_count(
        self,
        campaign_id: str,
        part_number: str,
        location_id: str,
        counted_quantity: int,
        counted_serials: Optional[List[str]] = None,
        counted_by: str = "system",
        evidence_keys: Optional[List[str]] = None,
        notes: Optional[str] = None,
    ) -> CampaignResult:
        """
        Submit a count result for a campaign item.

        Args:
            campaign_id: Campaign ID
            part_number: Part number counted
            location_id: Location counted
            counted_quantity: Physical count
            counted_serials: Serial numbers found
            counted_by: User who counted
            evidence_keys: S3 keys for photos
            notes: Additional notes

        Returns:
            CampaignResult with count status
        """
        log_agent_action(
            self.name, "submit_count",
            entity_type="COUNT",
            status="started",
        )

        try:
            # Get count item
            count_item = self.db.get_item(
                pk=f"CAMPAIGN#{campaign_id}",
                sk=f"COUNT#{part_number}#{location_id}",
            )

            if not count_item:
                return CampaignResult(
                    success=False,
                    message=f"Item de contagem nao encontrado: {part_number} @ {location_id}",
                )

            if count_item.get("status") not in [CountStatus.PENDING, CountStatus.COUNTED]:
                return CampaignResult(
                    success=False,
                    message=f"Item ja foi processado. Status: {count_item.get('status')}",
                )

            now = now_iso()

            # Check if campaign requires double count
            campaign = self.get_campaign(campaign_id)
            require_double = campaign and campaign.get("require_double_count", False)

            # Determine new status
            system_qty = count_item.get("system_quantity", 0)
            is_divergent = counted_quantity != system_qty

            if require_double and not count_item.get("counted_by"):
                # First count, needs verification
                new_status = CountStatus.COUNTED
            elif require_double and count_item.get("counted_by") == counted_by:
                # Same person trying to verify - not allowed
                return CampaignResult(
                    success=False,
                    message="Verificacao deve ser feita por pessoa diferente",
                )
            else:
                # Final count or no double-count required
                new_status = CountStatus.DIVERGENT if is_divergent else CountStatus.VERIFIED

            # Update count item
            updates = {
                "counted_quantity": counted_quantity,
                "counted_serials": counted_serials or [],
                "counted_by": counted_by,
                "counted_at": now,
                "status": new_status,
                "evidence_keys": evidence_keys or [],
                "notes": notes,
            }

            if new_status in [CountStatus.VERIFIED, CountStatus.DIVERGENT]:
                updates["verified_by"] = counted_by
                updates["verified_at"] = now

            self.db.update_item(
                pk=f"CAMPAIGN#{campaign_id}",
                sk=f"COUNT#{part_number}#{location_id}",
                updates=updates,
            )

            # Update campaign counters
            await self._update_campaign_counters(campaign_id)

            # If divergent, create divergence record
            if new_status == CountStatus.DIVERGENT:
                await self._create_divergence_record(
                    campaign_id=campaign_id,
                    count_item=count_item,
                    counted_quantity=counted_quantity,
                    counted_serials=counted_serials or [],
                )

            log_agent_action(
                self.name, "submit_count",
                entity_type="COUNT",
                status="completed",
            )

            return CampaignResult(
                success=True,
                campaign_id=campaign_id,
                message=f"Contagem registrada. Status: {new_status}",
                data={
                    "part_number": part_number,
                    "location_id": location_id,
                    "system_quantity": system_qty,
                    "counted_quantity": counted_quantity,
                    "status": new_status,
                    "is_divergent": is_divergent,
                },
            )

        except Exception as e:
            log_agent_action(
                self.name, "submit_count",
                entity_type="COUNT",
                status="failed",
            )
            return CampaignResult(
                success=False,
                message=f"Erro ao registrar contagem: {str(e)}",
            )

    async def _update_campaign_counters(self, campaign_id: str) -> None:
        """Update campaign progress counters."""
        items = self.get_campaign_items(campaign_id)

        counted = len([i for i in items if i.get("status") != CountStatus.PENDING])
        divergent = len([i for i in items if i.get("status") == CountStatus.DIVERGENT])

        self.db.update_item(
            pk=f"CAMPAIGN#{campaign_id}",
            sk="METADATA",
            updates={
                "counted_items": counted,
                "divergent_items": divergent,
                "status": CampaignStatus.IN_PROGRESS if counted > 0 else CampaignStatus.ACTIVE,
            },
        )

    async def _create_divergence_record(
        self,
        campaign_id: str,
        count_item: Dict[str, Any],
        counted_quantity: int,
        counted_serials: List[str],
    ) -> None:
        """Create a divergence record for analysis."""
        system_qty = count_item.get("system_quantity", 0)
        diff = counted_quantity - system_qty

        # Determine divergence type
        if diff > 0:
            div_type = DivergenceType.POSITIVE
        elif diff < 0:
            div_type = DivergenceType.NEGATIVE
        else:
            # Check for serial mismatches
            system_serials = set(count_item.get("system_serials", []))
            counted_set = set(counted_serials)
            if system_serials != counted_set:
                div_type = DivergenceType.SERIAL_MISMATCH
            else:
                return  # No actual divergence

        now = now_iso()
        div_id = generate_id("DIV")

        # Calculate percentage
        percentage = abs(diff) / system_qty if system_qty > 0 else 1.0

        div_item = {
            "PK": f"{EntityPrefix.DIVERGENCE}{div_id}",
            "SK": "METADATA",
            "entity_type": "DIVERGENCE",
            "divergence_id": div_id,
            "campaign_id": campaign_id,
            "part_number": count_item.get("part_number"),
            "location_id": count_item.get("location_id"),
            "project_id": count_item.get("project_id"),
            "divergence_type": div_type,
            "system_quantity": system_qty,
            "counted_quantity": counted_quantity,
            "divergence_quantity": abs(diff),
            "divergence_percentage": percentage,
            "system_serials": count_item.get("system_serials", []),
            "counted_serials": counted_serials,
            "status": "PENDING_ANALYSIS",
            "created_at": now,
            # GSIs
            "GSI4_PK": "STATUS#PENDING_ANALYSIS",
            "GSI4_SK": now,
        }

        self.db.put_item(div_item)

    # =========================================================================
    # Divergence Analysis
    # =========================================================================

    async def analyze_divergences(
        self,
        campaign_id: str,
    ) -> Dict[str, Any]:
        """
        Analyze divergences for a campaign.

        Provides summary statistics and patterns.

        Args:
            campaign_id: Campaign to analyze

        Returns:
            Analysis results with recommendations
        """
        log_agent_action(
            self.name, "analyze_divergences",
            entity_type="DIVERGENCE",
            status="started",
        )

        try:
            # Get campaign
            campaign = self.get_campaign(campaign_id)
            if not campaign:
                return {"success": False, "error": "Campaign not found"}

            # Get divergent items
            items = self.get_campaign_items(campaign_id, status=CountStatus.DIVERGENT)

            if not items:
                return {
                    "success": True,
                    "message": "Nenhuma divergencia encontrada",
                    "total_divergences": 0,
                }

            # Analyze patterns
            analysis = {
                "campaign_id": campaign_id,
                "campaign_name": campaign.get("name"),
                "total_items": campaign.get("total_items", 0),
                "counted_items": campaign.get("counted_items", 0),
                "divergent_items": len(items),
                "divergence_rate": len(items) / campaign.get("total_items", 1),
                "by_type": {
                    DivergenceType.POSITIVE: 0,
                    DivergenceType.NEGATIVE: 0,
                },
                "by_location": {},
                "by_part_number": {},
                "significant_divergences": [],
                "recommendations": [],
            }

            total_value_divergence = 0

            for item in items:
                system_qty = item.get("system_quantity", 0)
                counted_qty = item.get("counted_quantity", 0)
                diff = counted_qty - system_qty

                # Type analysis
                if diff > 0:
                    analysis["by_type"][DivergenceType.POSITIVE] += 1
                else:
                    analysis["by_type"][DivergenceType.NEGATIVE] += 1

                # Location analysis
                loc = item.get("location_id", "UNKNOWN")
                if loc not in analysis["by_location"]:
                    analysis["by_location"][loc] = {"count": 0, "total_diff": 0}
                analysis["by_location"][loc]["count"] += 1
                analysis["by_location"][loc]["total_diff"] += diff

                # Part number analysis
                pn = item.get("part_number", "UNKNOWN")
                if pn not in analysis["by_part_number"]:
                    analysis["by_part_number"][pn] = {"count": 0, "total_diff": 0}
                analysis["by_part_number"][pn]["count"] += 1
                analysis["by_part_number"][pn]["total_diff"] += diff

                # Significant divergences
                percentage = abs(diff) / system_qty if system_qty > 0 else 1.0
                if percentage >= self.SIGNIFICANT_DIVERGENCE_THRESHOLD:
                    analysis["significant_divergences"].append({
                        "part_number": pn,
                        "location_id": loc,
                        "system": system_qty,
                        "counted": counted_qty,
                        "difference": diff,
                        "percentage": f"{percentage:.1%}",
                    })

            # Generate recommendations
            if analysis["by_type"][DivergenceType.NEGATIVE] > analysis["by_type"][DivergenceType.POSITIVE]:
                analysis["recommendations"].append(
                    "Maioria das divergencias sao NEGATIVAS (falta). "
                    "Investigar possivel extravio ou erro de lancamento de saidas."
                )
            else:
                analysis["recommendations"].append(
                    "Maioria das divergencias sao POSITIVAS (sobra). "
                    "Investigar possivel erro de lancamento de entradas."
                )

            # Location patterns
            for loc, data in analysis["by_location"].items():
                if data["count"] > 3:
                    analysis["recommendations"].append(
                        f"Local '{loc}' tem {data['count']} divergencias. "
                        "Verificar processos de movimentacao neste local."
                    )

            log_agent_action(
                self.name, "analyze_divergences",
                entity_type="DIVERGENCE",
                status="completed",
            )

            return {
                "success": True,
                "analysis": analysis,
            }

        except Exception as e:
            log_agent_action(
                self.name, "analyze_divergences",
                entity_type="DIVERGENCE",
                status="failed",
            )
            return {"success": False, "error": str(e)}

    # =========================================================================
    # Adjustment Proposals
    # =========================================================================

    async def propose_adjustment(
        self,
        campaign_id: str,
        part_number: str,
        location_id: str,
        proposed_by: str = "system",
        adjustment_reason: str = "",
    ) -> CampaignResult:
        """
        Propose an inventory adjustment based on counting.

        ALWAYS creates HIL task - adjustments are NEVER automatic.

        Args:
            campaign_id: Campaign ID
            part_number: Part number to adjust
            location_id: Location to adjust
            proposed_by: User proposing
            adjustment_reason: Reason for adjustment

        Returns:
            CampaignResult with HIL task info
        """
        log_agent_action(
            self.name, "propose_adjustment",
            entity_type="ADJUSTMENT",
            status="started",
        )

        try:
            # Get count item
            count_item = self.db.get_item(
                pk=f"CAMPAIGN#{campaign_id}",
                sk=f"COUNT#{part_number}#{location_id}",
            )

            if not count_item:
                return CampaignResult(
                    success=False,
                    message="Item de contagem nao encontrado",
                )

            if count_item.get("status") != CountStatus.DIVERGENT:
                return CampaignResult(
                    success=False,
                    message="Item nao possui divergencia",
                )

            system_qty = count_item.get("system_quantity", 0)
            counted_qty = count_item.get("counted_quantity", 0)
            adjustment_qty = counted_qty - system_qty

            now = now_iso()
            movement_id = generate_id("ADJ")

            # Create pending adjustment movement
            movement_item = {
                "PK": f"{EntityPrefix.MOVEMENT}{movement_id}",
                "SK": "METADATA",
                "entity_type": "MOVEMENT",
                "movement_id": movement_id,
                "movement_type": MovementType.ADJUSTMENT,
                "part_number": part_number,
                "quantity": adjustment_qty,
                "location_id": location_id,
                "project_id": count_item.get("project_id", ""),
                "campaign_id": campaign_id,
                "status": "PENDING_APPROVAL",
                "adjustment_reason": adjustment_reason,
                "system_quantity_before": system_qty,
                "counted_quantity": counted_qty,
                "proposed_by": proposed_by,
                "created_at": now,
                # GSIs
                "GSI4_PK": "STATUS#PENDING_APPROVAL",
                "GSI4_SK": now,
            }

            self.db.put_item(movement_item)

            # Calculate confidence (always low for adjustments)
            confidence = self.calculate_confidence(
                extraction_quality=0.9,
                evidence_strength=0.8,
                historical_match=0.5,
                risk_factors=["adjustment", "inventory_count"],
                base_risk=RiskLevel.CRITICAL,
            )

            # Create HIL task (MANDATORY for adjustments)
            from tools.hil_workflow import HILWorkflowManager
            hil_manager = HILWorkflowManager()

            adj_type = "ENTRADA" if adjustment_qty > 0 else "BAIXA"
            hil_task = await hil_manager.create_task(
                task_type=HILTaskType.APPROVAL_ADJUSTMENT,
                title=f"Aprovar ajuste de inventario: {part_number}",
                description=self._format_adjustment_message(
                    part_number=part_number,
                    location_id=location_id,
                    system_qty=system_qty,
                    counted_qty=counted_qty,
                    adjustment_qty=adjustment_qty,
                    reason=adjustment_reason,
                    confidence=confidence,
                ),
                entity_type="MOVEMENT",
                entity_id=movement_id,
                requested_by=proposed_by,
                payload=movement_item,
                priority="HIGH",
            )

            # Update movement with task ID
            self.db.update_item(
                pk=f"{EntityPrefix.MOVEMENT}{movement_id}",
                sk="METADATA",
                updates={"hil_task_id": hil_task.get("task_id")},
            )

            log_agent_action(
                self.name, "propose_adjustment",
                entity_type="ADJUSTMENT",
                entity_id=movement_id,
                status="completed",
            )

            return CampaignResult(
                success=True,
                campaign_id=campaign_id,
                message=f"Proposta de ajuste criada. {adj_type} de {abs(adjustment_qty)} unidades.",
                data={
                    "movement_id": movement_id,
                    "hil_task_id": hil_task.get("task_id"),
                    "adjustment_type": adj_type,
                    "adjustment_quantity": adjustment_qty,
                    "requires_approval": True,
                },
            )

        except Exception as e:
            log_agent_action(
                self.name, "propose_adjustment",
                entity_type="ADJUSTMENT",
                status="failed",
            )
            return CampaignResult(
                success=False,
                message=f"Erro ao propor ajuste: {str(e)}",
            )

    def _format_adjustment_message(
        self,
        part_number: str,
        location_id: str,
        system_qty: int,
        counted_qty: int,
        adjustment_qty: int,
        reason: str,
        confidence: ConfidenceScore,
    ) -> str:
        """Format HIL message for adjustment approval."""
        adj_type = "ENTRADA" if adjustment_qty > 0 else "BAIXA"

        return f"""
## Solicitacao de Ajuste de Inventario

### Resumo
Ajuste de **{adj_type}** proposto com base em contagem fisica.

### Detalhes
| Campo | Valor |
|-------|-------|
| Part Number | {part_number} |
| Local | {location_id} |
| Quantidade Sistema | {system_qty} |
| Quantidade Contada | {counted_qty} |
| **Ajuste Proposto** | **{adjustment_qty:+d}** |

### Motivo
{reason or "Divergencia identificada em campanha de inventario"}

### Confianca da IA
- **Score Geral**: {confidence.overall:.0%}
- **Nivel de Risco**: **{confidence.risk_level.upper()}**
- **Fatores**: {', '.join(confidence.factors)}

### AVISO
Ajustes de inventario afetam diretamente o saldo contabil.
Certifique-se de que a contagem foi verificada antes de aprovar.

### Acoes Disponiveis
- **Aprovar**: Executar o ajuste conforme proposto
- **Rejeitar**: Cancelar o ajuste e manter saldo atual
- **Modificar**: Ajustar a quantidade antes de aprovar
"""

    # =========================================================================
    # Campaign Completion
    # =========================================================================

    async def complete_campaign(
        self,
        campaign_id: str,
        completed_by: str = "system",
    ) -> CampaignResult:
        """
        Mark a campaign as complete.

        Generates final report and statistics.

        Args:
            campaign_id: Campaign to complete
            completed_by: User completing

        Returns:
            CampaignResult with final statistics
        """
        log_agent_action(
            self.name, "complete_campaign",
            entity_type="CAMPAIGN",
            entity_id=campaign_id,
            status="started",
        )

        try:
            campaign = self.get_campaign(campaign_id)
            if not campaign:
                return CampaignResult(
                    success=False,
                    message="Campanha nao encontrada",
                )

            # Check if all items counted
            items = self.get_campaign_items(campaign_id)
            pending = [i for i in items if i.get("status") == CountStatus.PENDING]

            if pending:
                return CampaignResult(
                    success=False,
                    message=f"Ainda existem {len(pending)} itens pendentes de contagem",
                    data={"pending_count": len(pending)},
                )

            now = now_iso()

            # Calculate final statistics
            divergent = [i for i in items if i.get("status") == CountStatus.DIVERGENT]
            accuracy = (len(items) - len(divergent)) / len(items) if items else 0

            # Update campaign
            self.db.update_item(
                pk=f"CAMPAIGN#{campaign_id}",
                sk="METADATA",
                updates={
                    "status": CampaignStatus.COMPLETED,
                    "completed_at": now,
                    "completed_by": completed_by,
                    "final_accuracy": accuracy,
                    "GSI4_PK": f"STATUS#{CampaignStatus.COMPLETED}",
                    "GSI4_SK": now,
                },
            )

            # Log to audit
            from tools.dynamodb_client import SGAAuditLogger
            audit = SGAAuditLogger()
            audit.log_action(
                action="CAMPAIGN_COMPLETED",
                entity_type="CAMPAIGN",
                entity_id=campaign_id,
                actor=completed_by,
                details={
                    "total_items": len(items),
                    "divergent_items": len(divergent),
                    "accuracy": f"{accuracy:.1%}",
                },
            )

            log_agent_action(
                self.name, "complete_campaign",
                entity_type="CAMPAIGN",
                entity_id=campaign_id,
                status="completed",
            )

            return CampaignResult(
                success=True,
                campaign_id=campaign_id,
                message=f"Campanha finalizada com {accuracy:.1%} de acuracia",
                data={
                    "total_items": len(items),
                    "divergent_items": len(divergent),
                    "accuracy": f"{accuracy:.1%}",
                    "completed_at": now,
                },
            )

        except Exception as e:
            log_agent_action(
                self.name, "complete_campaign",
                entity_type="CAMPAIGN",
                status="failed",
            )
            return CampaignResult(
                success=False,
                message=f"Erro ao finalizar campanha: {str(e)}",
            )
