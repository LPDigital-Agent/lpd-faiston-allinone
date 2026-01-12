# =============================================================================
# Campaign Management Tools
# =============================================================================

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid

from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

logger = logging.getLogger(__name__)
AGENT_ID = "reconciliacao"
audit = AgentAuditEmitter(agent_id=AGENT_ID)


# Campaign status values
class CampaignStatus:
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class CountStatus:
    PENDING = "PENDING"
    COUNTED = "COUNTED"
    VERIFIED = "VERIFIED"
    DIVERGENT = "DIVERGENT"


def generate_campaign_id() -> str:
    """Generate campaign ID."""
    return f"INV_{uuid.uuid4().hex[:12].upper()}"


@trace_tool_call("sga_start_campaign")
async def start_campaign_tool(
    name: str,
    description: str = "",
    location_ids: Optional[List[str]] = None,
    project_ids: Optional[List[str]] = None,
    part_numbers: Optional[List[str]] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    created_by: str = "system",
    require_double_count: bool = False,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
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
    """
    audit.working(message=f"Criando campanha: {name}", session_id=session_id)

    try:
        campaign_id = generate_campaign_id()
        now = datetime.utcnow().isoformat() + "Z"

        # Build scope based on filters
        scope = {
            "location_ids": location_ids or ["ALL"],
            "project_ids": project_ids or ["ALL"],
            "part_numbers": part_numbers or ["ALL"],
        }

        # Generate count items based on filters
        items_to_count = await _generate_count_items(
            location_ids=location_ids,
            project_ids=project_ids,
            part_numbers=part_numbers,
        )

        campaign_data = {
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
        }

        # Store campaign
        try:
            from tools.db_client import DBClient
            db = DBClient()
            await db.put_campaign(campaign_data)

            # Create count items
            for item in items_to_count:
                count_item = {
                    "campaign_id": campaign_id,
                    "part_number": item["part_number"],
                    "location_id": item["location_id"],
                    "project_id": item.get("project_id", ""),
                    "system_quantity": item["system_quantity"],
                    "system_serials": item.get("system_serials", []),
                    "status": CountStatus.PENDING,
                    "created_at": now,
                }
                await db.put_count_item(count_item)
        except ImportError:
            logger.warning("[start_campaign] DBClient not available")

        audit.completed(
            message=f"Campanha '{name}' criada com {len(items_to_count)} itens",
            session_id=session_id,
            details={"campaign_id": campaign_id, "total_items": len(items_to_count)},
        )

        return {
            "success": True,
            "campaign_id": campaign_id,
            "message": f"Campanha '{name}' criada com {len(items_to_count)} itens para contagem",
            "data": {
                "total_items": len(items_to_count),
                "status": CampaignStatus.ACTIVE,
                "scope": scope,
            },
        }

    except Exception as e:
        logger.error(f"[start_campaign] Error: {e}", exc_info=True)
        audit.error(message="Erro ao criar campanha", session_id=session_id, error=str(e))
        return {"success": False, "error": str(e)}


async def _generate_count_items(
    location_ids: Optional[List[str]],
    project_ids: Optional[List[str]],
    part_numbers: Optional[List[str]],
) -> List[Dict[str, Any]]:
    """Generate list of items to be counted based on filters."""
    items = []

    try:
        from tools.db_client import DBClient
        db = DBClient()

        # Query balances based on filters
        if location_ids:
            for loc_id in location_ids:
                balances = await db.get_balances_by_location(loc_id)
                for bal in balances:
                    if part_numbers and bal.get("part_number") not in part_numbers:
                        continue
                    if project_ids and bal.get("project_id") not in project_ids:
                        continue

                    # Get serials for this balance
                    serials = await db.get_serials_for_balance(
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
    except ImportError:
        logger.warning("[_generate_count_items] DBClient not available")

    return items


@trace_tool_call("sga_get_campaign")
async def get_campaign_tool(
    campaign_id: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get campaign details by ID."""
    try:
        from tools.db_client import DBClient
        db = DBClient()
        campaign = await db.get_campaign(campaign_id)

        if not campaign:
            return {"success": False, "error": "Campanha nao encontrada"}

        return {"success": True, "campaign": campaign}

    except ImportError:
        return {"success": False, "error": "DBClient not available"}
    except Exception as e:
        logger.error(f"[get_campaign] Error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@trace_tool_call("sga_get_campaign_items")
async def get_campaign_items_tool(
    campaign_id: str,
    status: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Get count items for a campaign."""
    try:
        from tools.db_client import DBClient
        db = DBClient()
        items = await db.get_campaign_items(campaign_id, status=status)

        return {
            "success": True,
            "items": items,
            "total": len(items),
        }

    except ImportError:
        return {"success": False, "error": "DBClient not available", "items": []}
    except Exception as e:
        logger.error(f"[get_campaign_items] Error: {e}", exc_info=True)
        return {"success": False, "error": str(e), "items": []}


@trace_tool_call("sga_complete_campaign")
async def complete_campaign_tool(
    campaign_id: str,
    completed_by: str = "system",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Mark a campaign as complete.

    Generates final report and statistics.
    """
    audit.working(message=f"Finalizando campanha: {campaign_id}", session_id=session_id)

    try:
        from tools.db_client import DBClient
        db = DBClient()

        # Get campaign
        campaign = await db.get_campaign(campaign_id)
        if not campaign:
            return {"success": False, "error": "Campanha nao encontrada"}

        # Get items
        items = await db.get_campaign_items(campaign_id)
        pending = [i for i in items if i.get("status") == CountStatus.PENDING]

        if pending:
            return {
                "success": False,
                "error": f"Ainda existem {len(pending)} itens pendentes de contagem",
                "pending_count": len(pending),
            }

        now = datetime.utcnow().isoformat() + "Z"

        # Calculate final statistics
        divergent = [i for i in items if i.get("status") == CountStatus.DIVERGENT]
        accuracy = (len(items) - len(divergent)) / len(items) if items else 0

        # Update campaign
        await db.update_campaign(campaign_id, {
            "status": CampaignStatus.COMPLETED,
            "completed_at": now,
            "completed_by": completed_by,
            "final_accuracy": accuracy,
        })

        audit.completed(
            message=f"Campanha finalizada com {accuracy:.1%} de acuracia",
            session_id=session_id,
            details={"accuracy": accuracy, "divergent_items": len(divergent)},
        )

        return {
            "success": True,
            "campaign_id": campaign_id,
            "message": f"Campanha finalizada com {accuracy:.1%} de acuracia",
            "data": {
                "total_items": len(items),
                "divergent_items": len(divergent),
                "accuracy": f"{accuracy:.1%}",
                "completed_at": now,
            },
        }

    except ImportError:
        return {"success": False, "error": "DBClient not available"}
    except Exception as e:
        logger.error(f"[complete_campaign] Error: {e}", exc_info=True)
        audit.error(message="Erro ao finalizar campanha", session_id=session_id, error=str(e))
        return {"success": False, "error": str(e)}
