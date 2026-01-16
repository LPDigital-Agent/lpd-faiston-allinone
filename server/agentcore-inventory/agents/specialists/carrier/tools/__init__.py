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
- save_posting_tool: Save posting to DynamoDB
- get_postings_tool: Query postings by status/user
- update_posting_status_tool: Update posting status with validation
- get_posting_by_tracking_tool: Lookup posting by tracking code
- get_posting_by_id_tool: Get posting by ID
- get_posting_by_order_code_tool: Get posting by order code
"""

from .quotes import get_quotes_tool
from .recommendation import recommend_carrier_tool
from .tracking import track_shipment_tool, liberate_shipment_tool
from .shipment import create_shipment_tool, get_label_tool
from .postings_db import (
    save_posting_tool,
    get_postings_tool,
    update_posting_status_tool,
    get_posting_by_tracking_tool,
    get_posting_by_id_tool,
    get_posting_by_order_code_tool,
    POSTING_STATUSES,
    VALID_STATUSES,
    VALID_STATUS_TRANSITIONS,
)

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
    # Postings (DynamoDB)
    "save_posting_tool",
    "get_postings_tool",
    "update_posting_status_tool",
    "get_posting_by_tracking_tool",
    "get_posting_by_id_tool",
    "get_posting_by_order_code_tool",
    # Constants
    "POSTING_STATUSES",
    "VALID_STATUSES",
    "VALID_STATUS_TRANSITIONS",
]
