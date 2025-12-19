# =============================================================================
# Faiston Academy Agents - DO NOT ADD IMPORTS HERE
# =============================================================================
# CRITICAL: This file MUST remain EMPTY to avoid cold start timeout.
#
# AgentCore has a 30-second cold start limit. Each Google ADK import
# takes ~5-6 seconds. If we import all agents here, we exceed the limit
# and get HTTP 424 errors.
#
# Agents are imported lazily in main.py inside their handler functions.
# =============================================================================
