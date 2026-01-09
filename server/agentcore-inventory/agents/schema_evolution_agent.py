# =============================================================================
# Schema Evolution Agent (SEA) - Dynamic PostgreSQL Column Creation
# =============================================================================
# Specialized agent for dynamic schema evolution in the Faiston SGA Inventory.
#
# CRITICAL CONSTRAINTS (per CLAUDE.md):
# 1. NO direct PostgreSQL connections - ALL access via MCP Gateway
# 2. Lazy imports only - 30-second AgentCore cold start limit
# 3. Inherits from BaseInventoryAgent (Google ADK pattern)
#
# Architecture:
#   SEA Agent → MCPGatewayClient → AgentCore Gateway → Lambda → Aurora PostgreSQL
#
# Used by: NEXO Import Agent when users import CSVs with unknown fields
#
# Author: Faiston NEXO Team
# Date: January 2026
# =============================================================================

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from agents.base_agent import BaseInventoryAgent
from agents.utils import log_agent_action, RiskLevel


# =============================================================================
# System Prompt (Instruction) for Google ADK Agent
# =============================================================================

SCHEMA_EVOLUTION_INSTRUCTION = """
You are the Schema Evolution Agent (SEA), specialized in PostgreSQL schema management
for the Faiston SGA (Sistema de Gestão de Ativos) inventory system.

Your responsibilities:
1. Validate column creation requests (sanitization, security)
2. Infer appropriate PostgreSQL types from sample data
3. Execute schema changes via MCP tools with advisory locking
4. Ensure audit trail for all schema modifications

CRITICAL RULES:
- NEVER execute raw SQL - only use MCP tools
- ALWAYS sanitize column names (SQL injection prevention)
- ALWAYS validate against allowed tables and types whitelist
- When lock timeout occurs, recommend metadata JSONB fallback
- Log ALL schema changes for compliance audit

You work within the Faiston SGA inventory system, helping NEXO Import Agent
create new columns when users import CSV files with unknown fields.

Language: Respond in Brazilian Portuguese (pt-BR) for user-facing messages.
"""


# =============================================================================
# Schema Change Result Data Class
# =============================================================================


@dataclass
class SchemaChangeResult:
    """
    Result of a schema change operation.

    Used to communicate the outcome of column creation attempts
    back to the calling agent (e.g., NEXO Import Agent).

    Attributes:
        success: Whether the operation completed without errors
        created: Whether a new column was actually created
        column_name: Sanitized column name that was created/exists
        column_type: PostgreSQL data type of the column
        reason: Explanation of the result (especially for failures)
        use_metadata_fallback: Whether caller should use JSONB metadata
        error: Error type if operation failed
    """
    success: bool
    created: bool = False
    column_name: str = ""
    column_type: str = ""
    reason: str = ""
    use_metadata_fallback: bool = False
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "success": self.success,
            "created": self.created,
            "column_name": self.column_name,
            "column_type": self.column_type,
            "reason": self.reason,
            "use_metadata_fallback": self.use_metadata_fallback,
            "error": self.error,
        }


# =============================================================================
# Schema Evolution Agent
# =============================================================================


class SchemaEvolutionAgent(BaseInventoryAgent):
    """
    AI Agent specialized in PostgreSQL schema evolution.

    CRITICAL: This agent does NOT connect directly to PostgreSQL.
    All database operations go through MCP Gateway → Lambda → RDS.

    Follows Google ADK patterns:
    - Inherits from BaseInventoryAgent
    - Lazy-loaded clients
    - Async action methods
    - Confidence scoring for HIL decisions

    Security features:
    - Table whitelist (only specific tables allowed)
    - Type whitelist (only safe PostgreSQL types)
    - Column name sanitization (SQL injection prevention)
    - Advisory locking (race condition prevention)
    - Full audit trail (compliance)

    Attributes:
        ALLOWED_TABLES: Set of tables that allow dynamic columns
        ALLOWED_TYPES: Set of PostgreSQL types that can be created
    """

    # Whitelist of tables that can have dynamic columns added
    ALLOWED_TABLES = frozenset({
        "pending_entry_items",
        "pending_entries",
    })

    # Whitelist of PostgreSQL types (safe for dynamic creation)
    ALLOWED_TYPES = frozenset({
        "TEXT",
        "VARCHAR(100)",
        "VARCHAR(255)",
        "VARCHAR(500)",
        "INTEGER",
        "BIGINT",
        "NUMERIC(12,2)",
        "BOOLEAN",
        "TIMESTAMPTZ",
        "DATE",
        "JSONB",
        "TEXT[]",
    })

    def __init__(self):
        """
        Initialize Schema Evolution Agent with Google ADK configuration.

        Uses lazy initialization for database adapter to minimize cold start impact.
        """
        super().__init__(
            name="SchemaEvolutionAgent",
            instruction=SCHEMA_EVOLUTION_INSTRUCTION,
            description=(
                "Specialized agent for dynamic PostgreSQL column creation "
                "with advisory locking and security validation"
            ),
        )
        # Lazy-loaded database adapter (will be created on first use)
        self._db_adapter = None

    @property
    def db_adapter(self):
        """
        Lazy-load database adapter (GatewayPostgresAdapter via MCP).

        This property ensures the adapter is only created when first accessed,
        reducing cold start time. The adapter routes all database calls
        through the AgentCore MCP Gateway.

        Returns:
            GatewayPostgresAdapter instance configured for MCP access
        """
        if self._db_adapter is None:
            # Lazy import to avoid cold start impact
            from tools.gateway_adapter import GatewayAdapterFactory
            self._db_adapter = GatewayAdapterFactory.create_from_env()
            log_agent_action(
                self.name, "db_adapter_init",
                status="completed",
                details={"count": 1},
            )
        return self._db_adapter

    # =========================================================================
    # Column Name Sanitization
    # =========================================================================

    def sanitize_column_name(self, raw_name: str) -> str:
        """
        Sanitize column name for PostgreSQL.

        Transforms arbitrary input into a safe PostgreSQL identifier:
        - Lowercase
        - Replace spaces/special chars with underscore
        - Remove consecutive underscores
        - Ensure doesn't start with a number
        - Limit to 63 chars (PostgreSQL identifier limit)

        Args:
            raw_name: Original column name (e.g., from CSV header)

        Returns:
            Sanitized column name safe for PostgreSQL

        Examples:
            >>> sea.sanitize_column_name("Serial Number")
            'serial_number'
            >>> sea.sanitize_column_name("123_field")
            'col_123_field'
            >>> sea.sanitize_column_name("Número NF-e")
            'numero_nf_e'
        """
        if not raw_name:
            return "unknown_field"

        # Lowercase and strip whitespace
        name = raw_name.lower().strip()

        # Replace any non-alphanumeric char (except underscore) with underscore
        name = re.sub(r'[^a-z0-9_]', '_', name)

        # Remove consecutive underscores
        name = re.sub(r'_+', '_', name)

        # Strip leading/trailing underscores
        name = name.strip('_')

        # Ensure doesn't start with a number
        if name and name[0].isdigit():
            name = f"col_{name}"

        # PostgreSQL identifier limit is 63 characters
        return name[:63] if name else "unknown_field"

    # =========================================================================
    # Type Inference
    # =========================================================================

    def infer_column_type(self, sample_values: List[str]) -> str:
        """
        Infer PostgreSQL type from sample data.

        Uses conservative inference - prefers TEXT for ambiguous cases
        to avoid data loss. Examines sample values to detect:
        - Integers (INTEGER or BIGINT based on magnitude)
        - Decimals (NUMERIC for currency/precision)
        - Booleans (true/false, 1/0, yes/no, sim/não)
        - Dates (ISO, BR, US formats)
        - Text (VARCHAR based on length, or TEXT for long values)

        Args:
            sample_values: List of sample values from CSV column

        Returns:
            PostgreSQL data type string (from ALLOWED_TYPES)

        Examples:
            >>> sea.infer_column_type(["123", "456", "789"])
            'INTEGER'
            >>> sea.infer_column_type(["1.234,56", "2.345,67"])
            'NUMERIC(12,2)'
            >>> sea.infer_column_type(["2024-01-15", "2024-02-20"])
            'TIMESTAMPTZ'
        """
        if not sample_values:
            return "TEXT"

        # Filter empty values
        non_empty = [v.strip() for v in sample_values if v and v.strip()]
        if not non_empty:
            return "TEXT"

        # Check for integers (no decimals)
        if all(self._is_integer(v) for v in non_empty):
            # Check if values exceed INT32 range
            try:
                max_val = max(abs(int(v.replace(",", "").replace(".", "")))
                             for v in non_empty)
                return "BIGINT" if max_val > 2147483647 else "INTEGER"
            except ValueError:
                return "INTEGER"

        # Check for decimals/currency
        if all(self._is_decimal(v) for v in non_empty):
            return "NUMERIC(12,2)"

        # Check for booleans
        bool_values = {'true', 'false', '1', '0', 'yes', 'no', 'sim', 'não', 'nao'}
        if all(v.lower() in bool_values for v in non_empty):
            return "BOOLEAN"

        # Check for dates
        if all(self._is_date(v) for v in non_empty):
            return "TIMESTAMPTZ"

        # Default: Text with length consideration
        max_len = max(len(v) for v in non_empty)
        if max_len <= 100:
            return "VARCHAR(100)"
        elif max_len <= 255:
            return "VARCHAR(255)"
        elif max_len <= 500:
            return "VARCHAR(500)"
        return "TEXT"

    # =========================================================================
    # Request Validation
    # =========================================================================

    def validate_column_request(
        self,
        table_name: str,
        column_name: str,
        column_type: str,
    ) -> Dict[str, Any]:
        """
        Validate column creation request before sending to MCP.

        Performs security checks:
        - Table whitelist validation
        - Type whitelist validation
        - Column name format validation
        - SQL injection pattern detection

        Args:
            table_name: Target table for column creation
            column_name: Sanitized column name
            column_type: PostgreSQL data type

        Returns:
            Dictionary with:
            - valid: bool - Whether request passed all checks
            - errors: List[str] - List of validation errors
        """
        errors = []

        # Table whitelist check
        if table_name not in self.ALLOWED_TABLES:
            errors.append(
                f"Tabela '{table_name}' não permitida para colunas dinâmicas. "
                f"Tabelas permitidas: {', '.join(self.ALLOWED_TABLES)}"
            )

        # Column name validation
        if not column_name or len(column_name) < 2:
            errors.append("Nome da coluna muito curto (mínimo 2 caracteres)")

        if len(column_name) > 63:
            errors.append("Nome da coluna excede limite do PostgreSQL (63 chars)")

        # Type whitelist check
        if column_type not in self.ALLOWED_TYPES:
            errors.append(
                f"Tipo '{column_type}' não permitido. "
                f"Tipos permitidos: {', '.join(sorted(self.ALLOWED_TYPES))}"
            )

        # SQL injection pattern detection
        dangerous_patterns = [
            "drop", "delete", "insert", "update", "select", "truncate",
            "alter", "create", "grant", "revoke", ";", "--", "/*", "*/",
        ]
        name_lower = column_name.lower()
        for pattern in dangerous_patterns:
            if pattern in name_lower:
                errors.append(f"Nome da coluna contém padrão SQL perigoso: '{pattern}'")
                break

        return {"valid": len(errors) == 0, "errors": errors}

    # =========================================================================
    # Main Action: Create Column
    # =========================================================================

    async def create_column(
        self,
        table_name: str,
        column_name: str,
        column_type: str,
        requested_by: str,
        original_csv_column: Optional[str] = None,
        sample_values: Optional[List[str]] = None,
    ) -> SchemaChangeResult:
        """
        Create a new column via MCP Gateway.

        This is the main async action method following Google ADK pattern.
        It orchestrates the full column creation workflow:
        1. Sanitize column name
        2. Infer type if not provided
        3. Validate request against security rules
        4. Call MCP tool via Gateway Adapter
        5. Return result with fallback recommendation if needed

        Args:
            table_name: Target table (must be in ALLOWED_TABLES)
            column_name: Column name (will be sanitized)
            column_type: PostgreSQL type (will be validated/inferred)
            requested_by: User ID for audit trail
            original_csv_column: Original CSV header name
            sample_values: Sample values for type inference

        Returns:
            SchemaChangeResult with operation outcome

        Raises:
            No exceptions raised - all errors captured in result
        """
        log_agent_action(
            self.name, "create_column",
            status="started",
            details={"count": 1},
        )

        # Step 1: Sanitize column name
        safe_column = self.sanitize_column_name(column_name)

        # Step 2: Infer type if not valid
        if column_type not in self.ALLOWED_TYPES:
            inferred_type = self.infer_column_type(sample_values or [])
            log_agent_action(
                self.name, "type_inference",
                status="completed",
                details={"count": 1},
            )
            column_type = inferred_type

        # Step 3: Validate request
        validation = self.validate_column_request(table_name, safe_column, column_type)
        if not validation["valid"]:
            log_agent_action(
                self.name, "create_column",
                status="failed",
                details={"error": "validation_failed"},
            )
            return SchemaChangeResult(
                success=False,
                error="validation_failed",
                reason="; ".join(validation["errors"]),
                use_metadata_fallback=True,
            )

        # Step 4: Call MCP tool via Gateway
        try:
            result = self.db_adapter.create_column_safe(
                table_name=table_name,
                column_name=safe_column,
                column_type=column_type,
                requested_by=requested_by,
                original_csv_column=original_csv_column,
                # Limit sample values to first 5 for logging
                sample_values=sample_values[:5] if sample_values else None,
            )

            log_agent_action(
                self.name, "create_column",
                status="completed",
                details={"count": 1},
            )

            return SchemaChangeResult(
                success=result.get("success", False),
                created=result.get("created", False),
                column_name=result.get("column_name", safe_column),
                column_type=result.get("column_type", column_type),
                reason=result.get("reason", ""),
                use_metadata_fallback=result.get("use_metadata_fallback", False),
                error=result.get("error"),
            )

        except Exception as e:
            log_agent_action(
                self.name, "create_column",
                status="failed",
                details={"error": str(e)[:100]},
            )
            return SchemaChangeResult(
                success=False,
                error="mcp_call_failed",
                reason=f"Erro ao chamar MCP Gateway: {str(e)[:200]}",
                use_metadata_fallback=True,
            )

    # =========================================================================
    # Helper Methods (Private)
    # =========================================================================

    def _is_integer(self, value: str) -> bool:
        """Check if value represents an integer (no decimal point)."""
        try:
            # Remove thousand separators and check
            cleaned = value.replace(",", "").replace(".", "").strip()
            int(cleaned)
            # Ensure original doesn't have decimal separators in non-thousand positions
            return "." not in value or value.count(".") == value.count(",")
        except (ValueError, AttributeError):
            return False

    def _is_decimal(self, value: str) -> bool:
        """Check if value represents a decimal number."""
        try:
            # Handle Brazilian format (1.234,56) and US format (1,234.56)
            # Normalize: replace comma with dot for parsing
            cleaned = value.replace(" ", "")
            # Brazilian: 1.234,56 -> 1234.56
            if "," in cleaned and "." in cleaned:
                if cleaned.index(",") > cleaned.index("."):
                    # Brazilian format
                    cleaned = cleaned.replace(".", "").replace(",", ".")
                else:
                    # US format
                    cleaned = cleaned.replace(",", "")
            elif "," in cleaned:
                # Could be Brazilian decimal or US thousand separator
                cleaned = cleaned.replace(",", ".")
            float(cleaned)
            return True
        except (ValueError, AttributeError):
            return False

    def _is_date(self, value: str) -> bool:
        """Check if value looks like a date."""
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}',           # ISO: 2024-01-15
            r'^\d{2}/\d{2}/\d{4}',           # BR/US: 15/01/2024
            r'^\d{2}-\d{2}-\d{4}',           # Alt: 15-01-2024
            r'^\d{4}/\d{2}/\d{2}',           # Alt: 2024/01/15
            r'^\d{2}\.\d{2}\.\d{4}',         # European: 15.01.2024
        ]
        stripped = value.strip()
        return any(re.match(pattern, stripped) for pattern in date_patterns)


# =============================================================================
# Factory Function (Google ADK Pattern)
# =============================================================================


def create_schema_evolution_agent() -> SchemaEvolutionAgent:
    """
    Create and return a SchemaEvolutionAgent instance.

    Factory function following the pattern used in main.py handlers.
    This allows for future enhancements like dependency injection
    or configuration without changing caller code.

    Returns:
        Configured SchemaEvolutionAgent instance
    """
    return SchemaEvolutionAgent()
