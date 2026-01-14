# =============================================================================
# Shipping Adapter Factory
# =============================================================================
"""
Factory for creating shipping adapters based on environment configuration.

Environment Variables:
- CARRIER_MODE: 'mock' or 'real' (default: 'mock' for safety)
- POSTAL_USUARIO: API username
- POSTAL_TOKEN: API password/token
- POSTAL_IDPERFIL: Profile ID

Usage:
    adapter = get_shipping_adapter()
    quotes = await adapter.get_quotes(...)
"""

import os
import logging
from typing import Optional

from .base import ShippingAdapter
from .mock import MockShippingAdapter
from .postal_service import PostalServiceAdapter

logger = logging.getLogger(__name__)

# Global adapter instance (singleton pattern)
_adapter_instance: Optional[ShippingAdapter] = None


def get_shipping_adapter(force_mode: Optional[str] = None) -> ShippingAdapter:
    """
    Get the configured shipping adapter.

    Args:
        force_mode: Override CARRIER_MODE env var ('mock' or 'real')

    Returns:
        ShippingAdapter instance (singleton)
    """
    global _adapter_instance

    # Determine mode
    mode = force_mode or os.getenv("CARRIER_MODE", "mock").lower()

    # Return existing instance if mode matches
    if _adapter_instance is not None:
        if mode == "mock" and _adapter_instance.is_mock:
            return _adapter_instance
        if mode == "real" and not _adapter_instance.is_mock:
            return _adapter_instance

    # Create new instance
    if mode == "real":
        logger.info("[AdapterFactory] Creating PostalServiceAdapter (real API)")
        _adapter_instance = PostalServiceAdapter()
    else:
        logger.info("[AdapterFactory] Creating MockShippingAdapter (mock mode)")
        _adapter_instance = MockShippingAdapter()

    return _adapter_instance


def reset_adapter():
    """Reset the adapter instance (useful for testing)."""
    global _adapter_instance
    _adapter_instance = None


def get_adapter_mode() -> str:
    """Get current adapter mode."""
    return os.getenv("CARRIER_MODE", "mock").lower()


def is_mock_mode() -> bool:
    """Check if running in mock mode."""
    return get_adapter_mode() == "mock"
