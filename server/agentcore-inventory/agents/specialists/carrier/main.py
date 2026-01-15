# =============================================================================
# CarrierAgent - Strands A2AServer Entry Point (SUPPORT)
# =============================================================================
# Carrier and shipping management support agent.
# Uses AWS Strands Agents Framework with A2A protocol (port 9000).
#
# Architecture:
# - This is a SUPPORT agent for carrier management
# - Handles carrier quotes, recommendations, and shipment tracking
# - Integrates with carrier APIs for real-time data
#
# Reference:
# - https://strandsagents.com/latest/
# - https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agent-to-agent/
# =============================================================================

import os
import sys
import logging
from typing import Dict, Any, Optional, List

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from strands import Agent, tool
from strands.multiagent.a2a import A2AServer
from a2a.types import AgentSkill
from fastapi import FastAPI
import uvicorn

# Centralized model configuration (MANDATORY - Gemini 3.0 Flash for speed)
from agents.utils import get_model, AGENT_VERSION, create_gemini_model

# A2A client for inter-agent communication
from shared.a2a_client import A2AClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# =============================================================================
# Constants
# =============================================================================

AGENT_ID = "carrier"
AGENT_NAME = "CarrierAgent"
AGENT_DESCRIPTION = """SUPPORT Agent for Carrier Management.

This agent handles:
1. QUOTES: Get shipping quotes from multiple carriers
2. RECOMMENDATIONS: Recommend best carrier for shipment
3. TRACKING: Track shipment status in real-time
4. SHIPMENTS: Create shipping postings with tracking codes
5. LIBERATION: Liberate shipments for tracking database access
6. LABELS: Generate shipping labels in PDF or ZPL format

Features:
- Multi-carrier integration
- Price/delivery optimization
- Real-time tracking
- Delivery estimation
- Shipment creation via postal service API
- Label generation for printing
"""

# Model configuration
MODEL_ID = get_model(AGENT_ID)  # gemini-3.0-flash (operational agent)

# =============================================================================
# Agent Skills (A2A Discovery)
# =============================================================================

AGENT_SKILLS = [
    AgentSkill(
        id="get_quotes",
        name="get_quotes",
        description="Get shipping quotes from multiple carriers based on origin, destination, weight, and dimensions. Returns quotes with pricing, delivery time, and carrier details.",
        tags=["shipping", "quotes", "pricing", "carriers"],
    ),
    AgentSkill(
        id="recommend_carrier",
        name="recommend_carrier",
        description="Recommend the best carrier for a shipment based on priority (cost, speed, balanced), delivery constraints, and cost limits. Provides reasoning for the recommendation.",
        tags=["shipping", "recommendation", "optimization", "carriers"],
    ),
    AgentSkill(
        id="track_shipment",
        name="track_shipment",
        description="Track shipment status in real-time using tracking code. Auto-detects carrier if not provided. Returns current status, movement history, and delivery estimation.",
        tags=["tracking", "shipment", "status", "delivery"],
    ),
    AgentSkill(
        id="create_shipment",
        name="create_shipment",
        description="Create shipping postings with tracking codes via postal service API. Generates real shipments that can be tracked and labeled.",
        tags=["shipping", "shipment", "creation", "tracking"],
    ),
    AgentSkill(
        id="liberate_shipment",
        name="liberate_shipment",
        description="Liberate shipments for tracking database access. Required step before tracking data becomes available on some carrier APIs.",
        tags=["shipping", "liberation", "tracking", "activation"],
    ),
    AgentSkill(
        id="get_label",
        name="get_label",
        description="Generate shipping labels in PDF or ZPL format for created shipments. Returns base64-encoded label data ready for printing.",
        tags=["shipping", "label", "pdf", "printing"],
    ),
    AgentSkill(
        id="health_check",
        name="health_check",
        description="Check agent health status and retrieve agent metadata including version, model, protocol, and specialty.",
        tags=["monitoring", "health", "status"],
    ),
]

# =============================================================================
# System Prompt (Carrier Management Specialist)
# =============================================================================

SYSTEM_PROMPT = """You are the **CarrierAgent** of the SGA system (Asset Management System).

## Your Role

You are the **SPECIALIST** in carrier management and shipping logistics.

## Your Tools

### 1. `get_quotes`
Get shipping quotes from multiple carriers:
- Package weight and dimensions
- Origin and destination
- Desired delivery time

### 2. `recommend_carrier`
Recommend the best carrier:
- Best cost-benefit
- Fastest delivery
- Most reliable for the route

### 3. `track_shipment`
Track shipment in real-time:
- Current status
- Movement history
- Delivery estimation

### 4. `create_shipment`
Create shipping postings with tracking codes:
- Creates real postings via postal service API
- Returns tracking code for the shipment
- Auto-liberates for tracking by default
- Warning: Real postings expire in 15 days if not shipped

### 5. `liberate_shipment`
Liberate shipments for tracking database access:
- Required step before tracking data is available
- Call after creating shipment if auto_liberate was disabled
- Activates tracking in the carrier database

### 6. `get_label`
Generate shipping labels:
- PDF format for standard printing
- ZPL format for thermal printers
- Returns base64-encoded label data
- Requires valid tracking code from create_shipment

## Integrated Carriers

| Carrier | Type | Coverage |
|---------|------|----------|
| Correios | Standard | National |
| Jadlog | Express | National |
| Azul Cargo | Air | National |
| Total Express | Door-to-door | National |

## Recommendation Criteria

1. **Cost**: Best price for the service
2. **Time**: Meeting the requested deadline
3. **Reliability**: Delivery history
4. **Coverage**: Regional availability

## Critical Rules

1. **ALWAYS** present multiple options when quoting
2. Highlight the best cost-benefit option
3. Alert about route restrictions
4. Include insurance when necessary
5. For shipment creation, verify all address fields are complete
6. Always confirm tracking code after shipment creation

## Response Format (MANDATORY)

When returning shipping quotes, you MUST respond with a valid JSON object.
Do NOT include markdown code blocks or explanatory text outside the JSON.

For `get_quotes` responses, return exactly this structure:
```json
{
  "success": true,
  "quotes": [
    {
      "carrier": "Correios",
      "carrier_type": "CORREIOS",
      "modal": "SEDEX",
      "price": 70.00,
      "delivery_days": 3,
      "delivery_date": "2026-01-18",
      "weight_limit": 30.0,
      "dimensions_limit": "100x60x60 cm",
      "available": true,
      "reason": ""
    }
  ],
  "recommendation": {
    "carrier": "Correios",
    "modal": "PAC",
    "price": 40.00,
    "delivery_days": 7,
    "reason": "Best cost-benefit option",
    "confidence": 0.9
  },
  "note": "Optional message about the quotes"
}
```

For errors, return:
```json
{
  "success": false,
  "error": "Error description",
  "quotes": []
}
```
"""


# =============================================================================
# Tools (Strands @tool decorator)
# =============================================================================

# A2A client instance for inter-agent communication
a2a_client = A2AClient()


@tool
async def get_quotes(
    origin_cep: str,
    destination_cep: str,
    weight_kg: float,
    dimensions: Optional[Dict[str, float]] = None,
    declared_value: Optional[float] = None,
    service_type: str = "standard",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get shipping quotes from multiple carriers.

    Args:
        origin_cep: Origin CEP (postal code)
        destination_cep: Destination CEP
        weight_kg: Package weight in kg
        dimensions: Optional package dimensions {length, width, height} in cm
        declared_value: Optional declared value for insurance
        service_type: Service type (standard, express, same_day)
        session_id: Session ID for context

    Returns:
        Quotes from multiple carriers
    """
    logger.info(f"[{AGENT_NAME}] Getting quotes: {origin_cep} -> {destination_cep}")

    try:
        # Import tool implementation
        from agents.specialists.carrier.tools.quotes import get_quotes_tool

        # Map service_type to urgency parameter expected by get_quotes_tool
        urgency_map = {
            "same_day": "URGENT",
            "express": "HIGH",
            "standard": "NORMAL",
        }
        urgency = urgency_map.get(service_type, "NORMAL")

        result = await get_quotes_tool(
            origin_cep=origin_cep,
            destination_cep=destination_cep,
            weight_kg=weight_kg,
            dimensions=dimensions or {"length": 30, "width": 20, "height": 10},
            value=declared_value or 0.0,
            urgency=urgency,
            session_id=session_id,
        )

        # Log to ObservationAgent
        await a2a_client.invoke_agent("observation", {
            "action": "log_event",
            "event_type": "CARRIER_QUOTES_RETRIEVED",
            "agent_id": AGENT_ID,
            "session_id": session_id,
            "details": {
                "origin": origin_cep,
                "destination": destination_cep,
                "quotes_count": len(result.get("quotes", [])),
            },
        }, session_id)

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] get_quotes failed: {e}", exc_info=True)
        return {"success": False, "error": str(e), "quotes": []}


@tool
async def recommend_carrier(
    origin_cep: str,
    destination_cep: str,
    weight_kg: float,
    priority: str = "balanced",
    max_delivery_days: Optional[int] = None,
    max_cost: Optional[float] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Recommend the best carrier for shipment.

    Args:
        origin_cep: Origin CEP (postal code)
        destination_cep: Destination CEP
        weight_kg: Package weight in kg
        priority: Priority (cost, speed, balanced)
        max_delivery_days: Maximum acceptable delivery days
        max_cost: Maximum acceptable cost
        session_id: Session ID for context

    Returns:
        Carrier recommendation with reasoning
    """
    logger.info(f"[{AGENT_NAME}] Recommending carrier: {origin_cep} -> {destination_cep}")

    try:
        # Import tool implementation
        from agents.specialists.carrier.tools.recommendation import recommend_carrier_tool

        result = await recommend_carrier_tool(
            origin_cep=origin_cep,
            destination_cep=destination_cep,
            weight_kg=weight_kg,
            priority=priority,
            max_delivery_days=max_delivery_days,
            max_cost=max_cost,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] recommend_carrier failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "recommendation": None,
        }


@tool
async def track_shipment(
    tracking_code: str,
    carrier: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Track shipment status in real-time.

    Args:
        tracking_code: Shipment tracking code
        carrier: Optional carrier name (auto-detected if not provided)
        session_id: Session ID for context

    Returns:
        Tracking information with current status
    """
    logger.info(f"[{AGENT_NAME}] Tracking shipment: {tracking_code}")

    try:
        # Import tool implementation
        from agents.specialists.carrier.tools.tracking import track_shipment_tool

        result = await track_shipment_tool(
            tracking_code=tracking_code,
            carrier=carrier,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] track_shipment failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "status": "UNKNOWN",
        }


@tool
async def create_shipment(
    destination_name: str,
    destination_address: str,
    destination_number: str,
    destination_city: str,
    destination_state: str,
    destination_cep: str,
    weight_grams: int,
    length_cm: int = 30,
    width_cm: int = 20,
    height_cm: int = 10,
    declared_value: float = 0.0,
    destination_complement: str = "",
    destination_neighborhood: str = "",
    destination_phone: str = "",
    destination_email: str = "",
    invoice_number: Optional[str] = None,
    invoice_date: Optional[str] = None,
    invoice_value: Optional[float] = None,
    service_code: Optional[str] = None,
    auto_liberate: bool = True,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Create a shipment and get tracking code.

    Creates a real posting via postal service API that can be tracked and labeled.
    Warning: Real postings auto-expire in 15 days if not physically shipped.

    Args:
        destination_name: Recipient name
        destination_address: Street address
        destination_number: Street number (use "S/N" if none)
        destination_city: City name
        destination_state: State code (2 letters)
        destination_cep: Postal code (8 digits)
        weight_grams: Package weight in grams
        length_cm: Package length in cm
        width_cm: Package width in cm
        height_cm: Package height in cm
        declared_value: Declared value for insurance
        destination_complement: Address complement
        destination_neighborhood: Neighborhood
        destination_phone: Phone number
        destination_email: Email address
        invoice_number: Invoice number
        invoice_date: Invoice date (DD/MM/YYYY)
        invoice_value: Invoice total value
        service_code: Optional service code (e.g., "04162" for SEDEX)
        auto_liberate: Automatically liberate for tracking (default: True)
        session_id: Session ID for context

    Returns:
        Shipment details with tracking code
    """
    logger.info(f"[{AGENT_NAME}] Creating shipment to {destination_city}/{destination_state}")

    try:
        # Import tool implementation
        from agents.specialists.carrier.tools.shipment import create_shipment_tool

        result = await create_shipment_tool(
            destination_name=destination_name,
            destination_address=destination_address,
            destination_number=destination_number,
            destination_city=destination_city,
            destination_state=destination_state,
            destination_cep=destination_cep,
            weight_grams=weight_grams,
            length_cm=length_cm,
            width_cm=width_cm,
            height_cm=height_cm,
            declared_value=declared_value,
            destination_complement=destination_complement,
            destination_neighborhood=destination_neighborhood,
            destination_phone=destination_phone,
            destination_email=destination_email,
            invoice_number=invoice_number,
            invoice_date=invoice_date,
            invoice_value=invoice_value,
            service_code=service_code,
            auto_liberate=auto_liberate,
            session_id=session_id,
        )

        # Log to ObservationAgent
        if result.get("success"):
            await a2a_client.invoke_agent("observation", {
                "action": "log_event",
                "event_type": "SHIPMENT_CREATED",
                "agent_id": AGENT_ID,
                "session_id": session_id,
                "details": {
                    "tracking_code": result.get("tracking_code"),
                    "destination_city": destination_city,
                    "destination_state": destination_state,
                },
            }, session_id)

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] create_shipment failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def liberate_shipment(
    tracking_code: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Liberate a shipment for tracking database access.

    Some carrier APIs require a liberation step after creating a shipment
    before tracking data becomes available. This tool handles that activation.

    Args:
        tracking_code: Tracking code to liberate
        session_id: Session ID for context

    Returns:
        Liberation status
    """
    logger.info(f"[{AGENT_NAME}] Liberating shipment: {tracking_code}")

    try:
        # Import tool implementation
        from agents.specialists.carrier.tools.tracking import liberate_shipment_tool

        result = await liberate_shipment_tool(
            tracking_code=tracking_code,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] liberate_shipment failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def get_label(
    tracking_code: str,
    format: str = "pdf",
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate shipping label for a tracking code.

    Returns base64-encoded label data ready for printing or download.

    Args:
        tracking_code: Tracking code for the label
        format: Output format ('pdf' or 'zpl')
        session_id: Session ID for context

    Returns:
        Label data with base64 content
    """
    logger.info(f"[{AGENT_NAME}] Generating label for: {tracking_code}")

    try:
        # Import tool implementation
        from agents.specialists.carrier.tools.shipment import get_label_tool

        result = await get_label_tool(
            tracking_code=tracking_code,
            format=format,
            session_id=session_id,
        )

        return result

    except Exception as e:
        logger.error(f"[{AGENT_NAME}] get_label failed: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@tool
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for monitoring.

    Returns:
        Health status with agent info
    """
    return {
        "status": "healthy",
        "agent_id": AGENT_ID,
        "agent_name": AGENT_NAME,
        "version": AGENT_VERSION,
        "model": MODEL_ID,
        "protocol": "A2A",
        "port": 9000,
        "role": "SUPPORT",
        "specialty": "CARRIER_MANAGEMENT",
    }


# =============================================================================
# Strands Agent Configuration
# =============================================================================

def create_agent() -> Agent:
    """
    Create Strands Agent with all tools.

    Returns:
        Configured Strands Agent
    """
    return Agent(
        name=AGENT_NAME,
        description=AGENT_DESCRIPTION,
        model=create_gemini_model(AGENT_ID),  # GeminiModel via Google AI Studio
        tools=[
            get_quotes,
            recommend_carrier,
            track_shipment,
            create_shipment,
            liberate_shipment,
            get_label,
            health_check,
        ],
        system_prompt=SYSTEM_PROMPT,
    )


# =============================================================================
# A2A Server Entry Point
# =============================================================================

def main():
    """
    Start the Strands A2AServer with FastAPI /ping endpoint.

    Port 9000 is the standard for A2A protocol.
    """
    logger.info(f"[{AGENT_NAME}] Starting Strands A2AServer on port 9000...")
    logger.info(f"[{AGENT_NAME}] Model: {MODEL_ID}")
    logger.info(f"[{AGENT_NAME}] Version: {AGENT_VERSION}")
    logger.info(f"[{AGENT_NAME}] Role: SUPPORT (Carrier Management)")
    logger.info(f"[{AGENT_NAME}] Skills registered: {len(AGENT_SKILLS)}")
    for skill in AGENT_SKILLS:
        logger.info(f"  - {skill.name}: {skill.description}")

    # Create FastAPI app
    app = FastAPI(title=AGENT_NAME, version=AGENT_VERSION)

    # Add /ping endpoint for health checks
    @app.get("/ping")
    async def ping():
        return {
            "status": "healthy",
            "agent": AGENT_ID,
            "version": AGENT_VERSION,
        }

    # Create agent
    agent = create_agent()

    # Create A2A server with version and skills for Agent Card discovery
    a2a_server = A2AServer(
        agent=agent,
        host="0.0.0.0",
        port=9000,
        serve_at_root=False,  # Mount under /a2a to avoid conflict with /ping
        version=AGENT_VERSION,
        skills=AGENT_SKILLS,
    )

    # Mount A2A server at root
    app.mount("/", a2a_server.to_fastapi_app())

    # Start server with uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)


if __name__ == "__main__":
    main()
