# =============================================================================
# Carrier Adapters Package
# =============================================================================
"""
Abstract adapter pattern for carrier integrations.

This package provides a vendor-agnostic interface for shipping operations:
- Quotes: Get shipping prices and delivery estimates
- Shipments: Create shipments and get tracking codes
- Tracking: Query shipment status
- Labels: Generate shipping labels

Architecture Decision (Option B Approved):
- Quotes: Correios Public API (no posting created)
- Shipments: PostalServiceAdapter (abstracts VIPP)
- Tracking: PostalServiceAdapter (abstracts VIPP)
"""

from .base import (
    ShippingAdapter,
    QuoteResult,
    ShipmentResult,
    TrackingResult,
    TrackingEvent,
)
from .factory import (
    get_shipping_adapter,
    reset_adapter,
    get_adapter_mode,
    is_mock_mode,
)
from .mock import MockShippingAdapter
from .postal_service import PostalServiceAdapter

__all__ = [
    # Base classes
    "ShippingAdapter",
    "QuoteResult",
    "ShipmentResult",
    "TrackingResult",
    "TrackingEvent",
    # Factory
    "get_shipping_adapter",
    "reset_adapter",
    "get_adapter_mode",
    "is_mock_mode",
    # Implementations
    "MockShippingAdapter",
    "PostalServiceAdapter",
]
