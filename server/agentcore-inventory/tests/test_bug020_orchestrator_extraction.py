# =============================================================================
# BUG-020 Specific Integration Tests
# =============================================================================
# These tests specifically verify the fix for BUG-020:
# TypeError: can't access property "sheets", o.analysis is undefined
#
# Root Cause: Orchestrator's _invoke_swarm() was extracting from wrong path:
#   - WRONG: result.message (natural language text)
#   - CORRECT: result.results["file_analyst"].result (official Strands pattern)
#
# The fix imports _extract_tool_output_from_swarm_result from swarm.response_utils
# and uses it to properly extract structured data from Swarm results.
#
# Official Strands Documentation:
# https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/swarm/
# =============================================================================

import json
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock

from swarm.response_utils import (
    _extract_tool_output_from_swarm_result,
    _process_swarm_result,
)


class TestBug020OrchestratorExtraction:
    """
    Integration tests verifying BUG-020 fix in orchestrator context.

    The bug occurred because _invoke_swarm() tried to parse result.message
    (which contains LLM's conversational response) instead of using
    result.results["agent"].result (which contains the actual tool output).
    """

    def test_extracts_analysis_with_sheets_from_swarm(self):
        """
        BUG-020 CORE TEST: Must extract analysis.sheets from Swarm result.

        This test reproduces the exact scenario that caused the frontend error:
        - Frontend calls orchestrator with action: "nexo_analyze_file"
        - Orchestrator invokes Swarm which calls file_analyst agent
        - file_analyst runs unified_analyze_file tool and returns analysis
        - Orchestrator must extract analysis with sheets (NOT natural language)

        The fix uses _extract_tool_output_from_swarm_result() to get the
        structured response from result.results["file_analyst"].result
        """
        # Simulate the EXACT response structure from file_analyst agent
        mock_agent_result = Mock()
        mock_agent_result.result = {
            "success": True,
            "filename": "SOLICITAÇÕES DE EXPEDIÇÃO.csv",
            "detected_file_type": "csv",
            "analysis": {
                "sheet_count": 1,
                "total_rows": 150,
                "file_type": "csv",
                "recommended_strategy": "standard",
                "sheets": [
                    {
                        "name": "Sheet1",
                        "purpose": "items",
                        "row_count": 150,
                        "column_count": 10,
                        "columns": [
                            {"name": "NUMERO", "type": "string", "sample": ["001", "002"]},
                            {"name": "PART_NUMBER", "type": "string", "sample": ["C9200-24P"]},
                            {"name": "QUANTIDADE", "type": "integer", "sample": [1, 2]},
                            {"name": "SERIAL", "type": "string", "sample": ["TSP123456"]},
                        ],
                        "confidence": 0.92,
                    }
                ],
            },
            "column_mappings": [
                {
                    "file_column": "PART_NUMBER",
                    "target_field": "part_number",
                    "confidence": 0.95,
                    "reasoning": "Direct name match",
                },
                {
                    "file_column": "QUANTIDADE",
                    "target_field": "quantity",
                    "confidence": 0.90,
                    "reasoning": "Portuguese for quantity",
                },
            ],
            "overall_confidence": 0.92,
            "questions": [],
            "reasoning_trace": ["Analyzed file structure", "Mapped columns"],
        }

        # Simulate Swarm result structure (official Strands pattern)
        mock_swarm_result = Mock()
        mock_swarm_result.results = {"file_analyst": mock_agent_result}
        # The message contains LLM's conversational summary - NOT the tool output
        mock_swarm_result.message = "I have analyzed the CSV file and found 150 rows with inventory data."

        # Execute extraction using the fixed function
        extracted = _extract_tool_output_from_swarm_result(
            swarm_result=mock_swarm_result,
            agent_name="file_analyst",
            tool_name="unified_analyze_file",
        )

        # CRITICAL ASSERTIONS - These are what the frontend needs
        assert extracted is not None, "Must extract data from Swarm result"
        assert "analysis" in extracted, "Response must have 'analysis' key"
        assert "sheets" in extracted["analysis"], "analysis must have 'sheets' array"
        assert isinstance(extracted["analysis"]["sheets"], list), "sheets must be a list"
        assert len(extracted["analysis"]["sheets"]) > 0, "sheets must not be empty"

        # Verify sheet structure matches frontend TypeScript type
        sheet = extracted["analysis"]["sheets"][0]
        assert "name" in sheet, "Sheet must have 'name'"
        assert "row_count" in sheet, "Sheet must have 'row_count'"
        assert "columns" in sheet, "Sheet must have 'columns'"
        assert "confidence" in sheet, "Sheet must have 'confidence'"

        # Verify column mappings are present
        assert "column_mappings" in extracted, "Must have column_mappings"
        assert len(extracted["column_mappings"]) > 0, "Must have at least one mapping"

        # Verify we got the structured data, NOT the conversational message
        assert "I have analyzed" not in str(extracted), "Must NOT include LLM message"

    def test_does_not_use_message_when_results_available(self):
        """
        BUG-020 REGRESSION TEST: Must NOT fall back to result.message.

        The bug was caused by extracting from result.message which contains
        the LLM's natural language response, not the structured tool output.

        This test ensures we use result.results["agent"].result FIRST.
        """
        mock_agent_result = Mock()
        mock_agent_result.result = {
            "success": True,
            "analysis": {
                "sheets": [{"name": "CorrectSource", "row_count": 100}],
                "sheet_count": 1,
            },
        }

        mock_swarm_result = Mock()
        mock_swarm_result.results = {"file_analyst": mock_agent_result}
        # This message would cause the error if used - it has NO analysis.sheets
        mock_swarm_result.message = json.dumps({
            "success": True,
            "message": "File analyzed successfully"
            # NOTE: NO 'analysis' key here - this would cause the bug!
        })

        extracted = _extract_tool_output_from_swarm_result(
            swarm_result=mock_swarm_result,
            agent_name="file_analyst",
            tool_name="unified_analyze_file",
        )

        # Must use results, NOT message
        assert extracted is not None
        assert "analysis" in extracted
        assert extracted["analysis"]["sheets"][0]["name"] == "CorrectSource"

    def test_handles_toolresult_format_from_unified_analyze_file(self):
        """
        BUG-020 FORMAT TEST: Handle official Strands ToolResult format.

        The unified_analyze_file tool returns data in the official format:
        {"status": "success", "content": [{"json": {...}}]}

        The extraction must handle this nested structure.
        """
        mock_agent_result = Mock()
        mock_agent_result.result = {
            "status": "success",
            "content": [
                {
                    "json": {
                        "success": True,
                        "filename": "inventory.csv",
                        "analysis": {
                            "sheet_count": 1,
                            "total_rows": 50,
                            "sheets": [
                                {
                                    "name": "Data",
                                    "row_count": 50,
                                    "column_count": 5,
                                    "columns": [],
                                    "confidence": 0.88,
                                }
                            ],
                            "recommended_strategy": "auto_import",
                        },
                        "overall_confidence": 0.88,
                    }
                }
            ],
        }

        mock_swarm_result = Mock()
        mock_swarm_result.results = {"file_analyst": mock_agent_result}

        extracted = _extract_tool_output_from_swarm_result(
            swarm_result=mock_swarm_result,
            agent_name="file_analyst",
            tool_name="unified_analyze_file",
        )

        assert extracted is not None
        assert "analysis" in extracted
        assert "sheets" in extracted["analysis"]
        assert extracted["analysis"]["sheets"][0]["name"] == "Data"

    def test_orchestrator_response_includes_all_required_fields(self):
        """
        BUG-020 CONTRACT TEST: Response must include all fields frontend expects.

        The frontend TypeScript type NexoAnalyzeFileResponse expects:
        - success: boolean
        - session_id: string
        - round: number
        - analysis.sheets: array
        - column_mappings: array
        - overall_confidence: number
        """
        mock_agent_result = Mock()
        mock_agent_result.result = {
            "success": True,
            "analysis": {
                "sheets": [{"name": "Sheet1", "row_count": 100, "columns": [], "confidence": 0.9}],
                "sheet_count": 1,
                "total_rows": 100,
                "recommended_strategy": "standard",
            },
            "column_mappings": [
                {"file_column": "A", "target_field": "part_number", "confidence": 0.95, "reasoning": "Match"}
            ],
            "overall_confidence": 0.9,
            "questions": [],
        }

        mock_swarm_result = Mock()
        mock_swarm_result.results = {"file_analyst": mock_agent_result}

        session = {
            "session_id": "test-session-123",
            "round_count": 1,
            "context": {},
        }

        # Use _process_swarm_result which is what the orchestrator uses internally
        response = _process_swarm_result(mock_swarm_result, session, action="nexo_analyze_file")

        # Verify all required fields are present
        assert response["success"] is True, "Must have success: true"
        assert "analysis" in response, "Must have analysis"
        assert "sheets" in response["analysis"], "analysis must have sheets"
        assert isinstance(response["analysis"]["sheets"], list), "sheets must be list"
        # Note: session_id and round are added by _invoke_swarm, not _process_swarm_result


class TestBug020EdgeCases:
    """
    Edge case tests for BUG-020 to prevent regression.
    """

    def test_handles_empty_results_dict(self):
        """Should not crash when results dict is empty."""
        mock_swarm_result = Mock()
        mock_swarm_result.results = {}
        mock_swarm_result.entry_point = Mock()
        mock_swarm_result.entry_point.messages = []
        mock_swarm_result.message = None

        extracted = _extract_tool_output_from_swarm_result(
            mock_swarm_result, agent_name="file_analyst", tool_name="test"
        )

        assert extracted is None

    def test_handles_missing_agent_in_results(self):
        """Should handle case where specified agent is not in results."""
        mock_other_agent = Mock()
        mock_other_agent.result = {"some": "data"}

        mock_swarm_result = Mock()
        mock_swarm_result.results = {"other_agent": mock_other_agent}  # Different agent

        extracted = _extract_tool_output_from_swarm_result(
            mock_swarm_result, agent_name="file_analyst", tool_name="test"
        )

        # Should return None because file_analyst not found
        assert extracted is None

    def test_handles_agent_result_without_analysis(self):
        """Should handle agent result that doesn't have analysis key."""
        mock_agent_result = Mock()
        mock_agent_result.result = {
            "success": True,
            "message": "Processed successfully",
            # No 'analysis' key
        }

        mock_swarm_result = Mock()
        mock_swarm_result.results = {"file_analyst": mock_agent_result}

        extracted = _extract_tool_output_from_swarm_result(
            mock_swarm_result, agent_name="file_analyst", tool_name="test"
        )

        # Should return None because no analysis or success pattern
        # The function only returns dict with 'analysis' or 'success' keys
        assert extracted is not None  # Has 'success' key
        assert "analysis" not in extracted

    def test_handles_none_swarm_result(self):
        """Should handle None input gracefully."""
        extracted = _extract_tool_output_from_swarm_result(
            None, agent_name="file_analyst", tool_name="test"
        )
        assert extracted is None

    def test_iterates_all_agents_when_name_not_specified(self):
        """Should search all agents when agent_name is empty."""
        mock_agent_result = Mock()
        mock_agent_result.result = {
            "success": True,
            "analysis": {"sheets": [{"name": "Found"}]},
        }

        mock_swarm_result = Mock()
        mock_swarm_result.results = {"some_agent": mock_agent_result}

        extracted = _extract_tool_output_from_swarm_result(
            mock_swarm_result, agent_name="", tool_name="test"
        )

        assert extracted is not None
        assert extracted["analysis"]["sheets"][0]["name"] == "Found"

    def test_fallback_iterates_all_agents_when_name_not_found(self):
        """
        BUG-020 v3 FIX: When specified agent_name doesn't exist in results,
        extraction should still iterate all agents to find valid data.

        This is the CRITICAL test for the v3 fix. Before the fix, this test
        would FAIL because the `if not agent_name` guard prevented iteration
        when a specific agent_name was provided but not found in results.
        """
        mock_other_agent = Mock()
        mock_other_agent.result = {
            "success": True,
            "analysis": {"sheets": [{"name": "FoundViaFallback"}], "sheet_count": 1},
        }

        mock_swarm_result = Mock()
        # Note: Key is "other_agent", NOT "file_analyst"
        mock_swarm_result.results = {"other_agent": mock_other_agent}

        # Pass "file_analyst" which does NOT exist in results
        extracted = _extract_tool_output_from_swarm_result(
            mock_swarm_result, agent_name="file_analyst", tool_name="test"
        )

        # Should STILL find data via fallback iteration (BUG-020 v3 fix)
        assert extracted is not None, "Fallback iteration must find data in other agents"
        assert extracted["analysis"]["sheets"][0]["name"] == "FoundViaFallback"


class TestBug020FrontendContract:
    """
    Tests verifying the response matches frontend TypeScript types.

    Frontend type: NexoAnalyzeFileResponse in useSmartImportNexo.ts
    """

    def test_response_structure_matches_typescript_type(self):
        """
        Verify response structure matches:

        interface NexoAnalyzeFileResponse {
            success: boolean;
            session_id: string;
            round: number;
            import_session_id?: string;
            filename?: string;
            detected_file_type?: string;
            analysis: {
                sheet_count: number;
                total_rows: number;
                file_type: string;
                recommended_strategy: string;
                sheets: Array<{
                    name: string;
                    purpose?: string;
                    row_count: number;
                    column_count: number;
                    columns: Array<{...}>;
                    confidence: number;
                }>;
            };
            column_mappings: Array<{
                file_column: string;
                target_field: string;
                confidence: number;
                reasoning: string;
            }>;
            overall_confidence: number;
            questions: Array<{...}>;
            reasoning_trace?: string[];
        }
        """
        mock_agent_result = Mock()
        mock_agent_result.result = {
            "success": True,
            "import_session_id": "imp-123",
            "filename": "test.csv",
            "detected_file_type": "csv",
            "analysis": {
                "sheet_count": 1,
                "total_rows": 100,
                "file_type": "csv",
                "recommended_strategy": "auto_import",
                "sheets": [
                    {
                        "name": "Sheet1",
                        "purpose": "items",
                        "row_count": 100,
                        "column_count": 5,
                        "columns": [
                            {
                                "name": "PART_NUMBER",
                                "type": "string",
                                "sample": ["ABC-123"],
                            }
                        ],
                        "confidence": 0.92,
                    }
                ],
            },
            "column_mappings": [
                {
                    "file_column": "PART_NUMBER",
                    "target_field": "part_number",
                    "confidence": 0.95,
                    "reasoning": "Direct name match",
                }
            ],
            "overall_confidence": 0.92,
            "questions": [],
            "reasoning_trace": ["Step 1", "Step 2"],
        }

        mock_swarm_result = Mock()
        mock_swarm_result.results = {"file_analyst": mock_agent_result}

        extracted = _extract_tool_output_from_swarm_result(
            mock_swarm_result, agent_name="file_analyst", tool_name="unified_analyze_file"
        )

        # Verify structure matches TypeScript type
        assert isinstance(extracted["success"], bool)
        assert isinstance(extracted["analysis"], dict)
        assert isinstance(extracted["analysis"]["sheet_count"], int)
        assert isinstance(extracted["analysis"]["total_rows"], int)
        assert isinstance(extracted["analysis"]["sheets"], list)
        assert len(extracted["analysis"]["sheets"]) > 0

        sheet = extracted["analysis"]["sheets"][0]
        assert isinstance(sheet["name"], str)
        assert isinstance(sheet["row_count"], int)
        assert isinstance(sheet["columns"], list)
        assert isinstance(sheet["confidence"], (int, float))

        assert isinstance(extracted["column_mappings"], list)
        if extracted["column_mappings"]:
            mapping = extracted["column_mappings"][0]
            assert "file_column" in mapping
            assert "target_field" in mapping
            assert "confidence" in mapping
            assert "reasoning" in mapping

    def test_frontend_can_access_sheets_without_error(self):
        """
        BUG-020 REPRODUCTION TEST: Frontend code that caused the error.

        The frontend does: data.analysis.sheets.map(...)
        This test simulates that exact access pattern.
        """
        mock_agent_result = Mock()
        mock_agent_result.result = {
            "success": True,
            "analysis": {
                "sheets": [
                    {"name": "Sheet1", "row_count": 50},
                    {"name": "Sheet2", "row_count": 100},
                ],
                "sheet_count": 2,
            },
        }

        mock_swarm_result = Mock()
        mock_swarm_result.results = {"file_analyst": mock_agent_result}

        extracted = _extract_tool_output_from_swarm_result(
            mock_swarm_result, agent_name="file_analyst", tool_name="unified_analyze_file"
        )

        # Simulate frontend code: data.analysis.sheets.map(sheet => sheet.name)
        try:
            sheet_names = [sheet["name"] for sheet in extracted["analysis"]["sheets"]]
            assert sheet_names == ["Sheet1", "Sheet2"]
        except (TypeError, KeyError) as e:
            pytest.fail(f"Frontend access pattern failed: {e}")
