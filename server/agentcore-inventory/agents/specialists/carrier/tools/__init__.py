# =============================================================================
# CarrierAgent Tools
# =============================================================================
"""
Tools for carrier operations:
- get_quotes_tool: Get shipping quotes (Correios Public API)
- recommend_carrier_tool: AI-based carrier recommendation
- track_shipment_tool: Track shipment status
- liberate_shipment_tool: Liberate for tracking
- create_shipment_tool: Create actual shipment
- get_label_tool: Generate shipping label
"""

from .quotes import get_quotes_tool
from .recommendation import recommend_carrier_tool
from .tracking import track_shipment_tool, liberate_shipment_tool
from .shipment import create_shipment_tool, get_label_tool

__all__ = [
    # Quotes
    "get_quotes_tool",
    # Recommendation
    "recommend_carrier_tool",
    # Tracking
    "track_shipment_tool",
    "liberate_shipment_tool",
    # Shipment
    "create_shipment_tool",
    "get_label_tool",
]
