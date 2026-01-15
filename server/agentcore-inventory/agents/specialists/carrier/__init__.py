# =============================================================================
# CarrierAgent Module
# Shipping carrier selection and quotes
# =============================================================================

# Note: Import from main.py, not agent.py (which doesn't exist)
# Using alias for backward compatibility
from .main import create_agent as create_carrier_agent, AGENT_ID, AGENT_NAME

__all__ = ["create_carrier_agent", "AGENT_ID", "AGENT_NAME"]
