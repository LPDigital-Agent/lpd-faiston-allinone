# =============================================================================
# Faiston Academy Tools - DO NOT ADD IMPORTS HERE
# =============================================================================
# CRITICAL: This file MUST remain EMPTY to avoid cold start timeout.
#
# AgentCore has a 30-second cold start limit. Tools that depend on heavy
# libraries (boto3, elevenlabs, etc.) are imported lazily in agent code.
#
# Tools are imported where needed using lazy loading patterns:
#   from tools.elevenlabs_tool import text_to_dialogue
#   from tools.heygen_tool import create_video
# =============================================================================
