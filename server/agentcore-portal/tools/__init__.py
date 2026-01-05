# =============================================================================
# Faiston Portal Tools - DO NOT ADD IMPORTS HERE
# =============================================================================
# CRITICAL: This file MUST remain EMPTY to avoid cold start timeout.
#
# AgentCore has a 30-second cold start limit. Tools that depend on heavy
# libraries are imported lazily in agent code.
#
# Tools are imported where needed using lazy loading patterns:
#   from tools.rss_parser import fetch_and_parse_feed
#   from tools.a2a_client import invoke_academy_agent
# =============================================================================
