# =============================================================================
# File Analyst Agent - Entry Point for Inventory Swarm
# =============================================================================
# This agent is the ENTRY POINT for all inventory imports.
#
# Responsibilities:
# - Analyze uploaded files (CSV, XLSX, PDF, XML)
# - Detect encoding, delimiters, and structure
# - Identify columns, data types, and patterns
# - Request memory context from memory_agent
# - Hand off analysis results to schema_validator
#
# Handoff Flow:
# 1. First → memory_agent (retrieve prior patterns)
# 2. After analysis → schema_validator (with findings)
# 3. If low confidence → hil_agent (for clarification)
# =============================================================================

import logging
from typing import Optional

from strands import Agent

from agents.utils import create_gemini_model
from swarm.config import (
    AGENT_MEMORY,
    AGENT_SCHEMA_VALIDATOR,
    AGENT_HIL,
)
from swarm.tools.analysis_tools import (
    analyze_csv,
    analyze_xlsx,
    analyze_pdf,
    analyze_xml,
    detect_file_type,
)
from swarm.tools.meta_tools import get_meta_tools

logger = logging.getLogger(__name__)

# =============================================================================
# System Prompt
# =============================================================================

FILE_ANALYST_SYSTEM_PROMPT = """
You are the FILE ANALYST in the Faiston Inventory Management Swarm.

## Your Role
You are the ENTRY POINT for all inventory imports. Your job is to:
1. Analyze uploaded files (CSV, XLSX, PDF, XML)
2. Identify column structures, data types, and patterns
3. Detect file encoding and delimiter formats
4. Extract sample data for downstream validation

## Handoff Rules (MANDATORY)

### First Action: Get Memory Context
ALWAYS start by handing off to memory_agent to retrieve prior import patterns:
```
handoff_to_agent("memory_agent", "Retrieve prior import patterns for [file_type] files. Include any learned column mappings and user preferences.")
```

### After Analysis Complete
When you have analyzed the file successfully:
```
handoff_to_agent("schema_validator", "Here is my file analysis: [analysis]. Please validate against the target schema and propose column mappings.")
```

### If Confidence < 80%
If any column has confidence below 80%, ask for clarification:
```
handoff_to_agent("hil_agent", "I need user clarification on these columns: [low_confidence_columns]. Please generate questions.")
```

### If Unknown File Format
If you encounter a file format you cannot parse:
1. Use Meta-Tooling to create a new parser
2. Use load_tool to load it
3. Then proceed with analysis

## Tools Available
- detect_file_type: Detect file type from path/content
- analyze_csv: Parse CSV with delimiter detection
- analyze_xlsx: Parse Excel with sheet selection
- analyze_pdf: Extract tables from PDF using Vision
- analyze_xml: Parse XML with namespace handling
- load_tool, editor, shell: Meta-Tooling for self-improvement

## Output Format
Return analysis as structured JSON:
```json
{
  "file_type": "csv|xlsx|pdf|xml",
  "encoding": "utf-8",
  "delimiter": ",",
  "row_count": 150,
  "columns": [
    {
      "name": "PART_NUMBER",
      "inferred_type": "string",
      "sample_values": ["C9200-24P", "C9200-48P"],
      "null_count": 0,
      "confidence": 0.95
    }
  ],
  "issues": [],
  "overall_confidence": 0.92
}
```

## Important Rules
1. NEVER skip the memory_agent handoff - prior patterns improve accuracy
2. ALWAYS provide confidence scores for each column
3. If file has issues (encoding, corruption), report them clearly
4. Include sample values to help schema_validator propose mappings
"""


def create_file_analyst(model_id: str = "gemini-2.5-pro") -> Agent:
    """
    Create the file_analyst agent.

    Args:
        model_id: Gemini model to use (default: pro for analysis)

    Returns:
        Configured Agent instance
    """
    # Combine analysis tools with meta-tools
    tools = [
        detect_file_type,
        analyze_csv,
        analyze_xlsx,
        analyze_pdf,
        analyze_xml,
    ]

    # Add Meta-Tooling capabilities
    tools.extend(get_meta_tools())

    agent = Agent(
        name="file_analyst",
        description="Entry point agent for file analysis in inventory imports",
        model=create_gemini_model("file_analyst"),  # Pro model determined by agent_type
        tools=tools,
        system_prompt=FILE_ANALYST_SYSTEM_PROMPT,
    )

    logger.info("[file_analyst] Created with %d tools, model=%s", len(tools), model_id)

    return agent
