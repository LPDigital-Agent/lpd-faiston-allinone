# =============================================================================
# Sheet Analyzer Tool - Multi-Sheet XLSX Analysis
# =============================================================================
# Analyzes XLSX files with multiple sheets to understand structure,
# detect relationships, and suggest processing strategies.
#
# Philosophy: OBSERVE → THINK → ASK → LEARN → ACT
# This tool handles the OBSERVE phase by deeply analyzing file structure.
#
# SCHEMA-AWARE: Now uses SchemaColumnMatcher for dynamic column matching
# against PostgreSQL schema instead of hardcoded patterns.
#
# Module: Gestao de Ativos -> Gestao de Estoque -> Smart Import
# Author: Faiston NEXO Team
# Updated: January 2026 - Schema-aware matching
# =============================================================================

import io
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Types and Enums
# =============================================================================


class SheetPurpose(Enum):
    """Detected purpose of a sheet based on content analysis."""
    ITEMS = "items"                 # Main items/products list
    SERIALS = "serials"             # Serial numbers list
    METADATA = "metadata"           # File metadata/header info
    SUMMARY = "summary"             # Summary/totals sheet
    PROJECTS = "projects"           # Project assignments
    LOCATIONS = "locations"         # Location/warehouse data
    UNKNOWN = "unknown"             # Purpose not detected


class SheetRelationship(Enum):
    """Relationship type between sheets."""
    MASTER_DETAIL = "master_detail"     # Sheet1 is header, Sheet2 is details
    ONE_TO_MANY = "one_to_many"         # Sheet1 items have multiple Sheet2 records
    SEPARATE = "separate"               # Independent sheets
    DUPLICATE = "duplicate"             # Same data, different format
    COMPLEMENT = "complement"           # Sheets complement each other


@dataclass
class ColumnAnalysis:
    """Analysis of a single column."""
    name: str
    normalized_name: str
    sample_values: List[str]
    data_type: str              # "text", "number", "date", "mixed"
    unique_count: int
    null_count: int
    is_likely_key: bool         # Appears to be an ID/key column
    suggested_mapping: Optional[str] = None
    mapping_confidence: float = 0.0


@dataclass
class SheetAnalysis:
    """Analysis of a single sheet."""
    name: str
    row_count: int
    column_count: int
    columns: List[ColumnAnalysis]
    detected_purpose: SheetPurpose
    purpose_confidence: float
    has_headers: bool
    suggested_action: str       # "process", "skip", "merge_with"
    merge_target: Optional[str] = None  # If merge, which sheet
    notes: List[str] = field(default_factory=list)


@dataclass
class SheetRelationshipAnalysis:
    """Analysis of relationship between two sheets."""
    sheet1: str
    sheet2: str
    relationship_type: SheetRelationship
    confidence: float
    join_columns: List[Tuple[str, str]]  # (sheet1_col, sheet2_col)
    description: str


@dataclass
class WorkbookAnalysis:
    """Complete analysis of an XLSX workbook."""
    filename: str
    sheet_count: int
    total_rows: int
    sheets: List[SheetAnalysis]
    relationships: List[SheetRelationshipAnalysis]
    recommended_strategy: str
    questions_for_user: List[Dict[str, Any]]
    reasoning_trace: List[Dict[str, str]]


# =============================================================================
# Column Pattern Detection (OBSERVE phase)
# Schema-aware matching using SchemaColumnMatcher
# =============================================================================


# Global matcher instance (lazy initialized)
_schema_matcher = None


def _get_schema_matcher():
    """
    Get or create the SchemaColumnMatcher instance (lazy initialization).

    Uses lazy import to avoid cold start impact in AgentCore runtime.
    Falls back to pattern-only matching if schema is unavailable.
    """
    global _schema_matcher
    if _schema_matcher is None:
        try:
            from tools.schema_column_matcher import get_column_matcher
            _schema_matcher = get_column_matcher()
            logger.info("[SheetAnalyzer] Schema-aware matching enabled")
        except Exception as e:
            logger.warning(f"[SheetAnalyzer] Schema matcher unavailable: {e}")
            _schema_matcher = None
    return _schema_matcher


# Legacy COLUMN_PATTERNS kept as fallback when schema is unavailable
# These patterns are now also in schema_column_matcher.py BUILTIN_ALIASES
COLUMN_PATTERNS: Dict[str, List[str]] = {
    "part_number": [
        "pn", "codigo", "material", "part_number", "partnumber",
        "cod_material", "codigo_material", "item", "sku", "codigo_item",
        "equipamento", "equipment", "cod_equip"
    ],
    "description": [
        "desc", "descricao", "nome", "description", "nome_material",
        "desc_material", "produto", "product", "item_name"
    ],
    "quantity": [
        "qty", "quantidade", "qtd", "quant", "quantity", "qtde"
    ],
    "serial_number": [
        "serial", "sn", "serie", "serial_number", "numero_serie",
        "ns", "n_serie"
    ],
    "location_code": [
        "loc", "local", "deposito", "location", "warehouse",
        "armazem", "almoxarifado", "destino"
    ],
    "project_code": [
        "projeto", "project", "proj", "id_projeto", "cod_projeto",
        "project_id", "obra"
    ],
    "supplier_name": [
        "fornecedor", "supplier", "vendor", "fabricante", "manufacturer"
    ],
    "unit_value": [
        "custo", "cost", "preco", "valor", "unit_cost", "custo_unitario",
        "preco_unitario", "value"
    ],
    "ncm": [
        "ncm", "ncm_code", "codigo_ncm"
    ],
    "movement_date": [
        "data", "date", "dt", "data_entrada", "data_saida", "created_at"
    ],
    "status": [
        "status", "situacao", "estado", "state"
    ],
}


def normalize_column_name(name: str) -> str:
    """
    Normalize column name for pattern matching.

    Args:
        name: Original column name

    Returns:
        Normalized lowercase name without accents/special chars
    """
    if not name:
        return ""

    # Accent replacements
    replacements = {
        "á": "a", "à": "a", "ã": "a", "â": "a",
        "é": "e", "è": "e", "ê": "e",
        "í": "i", "ì": "i", "î": "i",
        "ó": "o", "ò": "o", "õ": "o", "ô": "o",
        "ú": "u", "ù": "u", "û": "u",
        "ç": "c", "ñ": "n",
    }

    result = str(name).lower().strip()
    for char, replacement in replacements.items():
        result = result.replace(char, replacement)

    # Keep only alphanumeric and underscore
    result = "".join(c if c.isalnum() or c == "_" else "_" for c in result)

    # Remove multiple underscores
    while "__" in result:
        result = result.replace("__", "_")

    return result.strip("_")


def detect_column_mapping(
    column_name: str,
    target_table: str = "pending_entry_items",
) -> Tuple[Optional[str], float]:
    """
    Detect which target field a column maps to using schema-aware matching.

    Algorithm (priority order):
    1. Use SchemaColumnMatcher (schema + aliases + fuzzy) if available
    2. Fallback to legacy COLUMN_PATTERNS if schema unavailable

    Args:
        column_name: Original column name
        target_table: Target PostgreSQL table (default: pending_entry_items)

    Returns:
        Tuple of (target_field or None, confidence)
    """
    # Try schema-aware matching first
    matcher = _get_schema_matcher()
    if matcher:
        target, confidence = matcher.match_column(column_name, target_table)
        if target:
            logger.debug(
                f"[SheetAnalyzer] Schema match: {column_name} → {target} ({confidence:.2f})"
            )
            return target, confidence

    # Fallback to legacy pattern matching
    normalized = normalize_column_name(column_name)

    for target_field, patterns in COLUMN_PATTERNS.items():
        # Exact match
        normalized_patterns = [normalize_column_name(p) for p in patterns]
        if normalized in normalized_patterns:
            return target_field, 0.95

        # Contains match
        for pattern in normalized_patterns:
            if pattern in normalized or normalized in pattern:
                return target_field, 0.75

    return None, 0.0


def detect_column_mapping_with_schema(
    column_name: str,
    target_table: str,
    schema_provider=None,
) -> Tuple[Optional[str], float]:
    """
    Schema-aware column mapping detection (explicit schema injection).

    Use this when you have a SchemaProvider instance and want to ensure
    schema awareness without relying on global state.

    Args:
        column_name: Original column name
        target_table: Target PostgreSQL table
        schema_provider: SchemaProvider instance (optional)

    Returns:
        Tuple of (target_field or None, confidence)
    """
    try:
        from tools.schema_column_matcher import SchemaColumnMatcher
        matcher = SchemaColumnMatcher(schema_provider)
        return matcher.match_column(column_name, target_table)
    except Exception as e:
        logger.warning(f"[SheetAnalyzer] Schema match failed: {e}")
        return detect_column_mapping(column_name, target_table)


def detect_data_type(values: List[Any]) -> str:
    """
    Detect the predominant data type in a list of values.

    Args:
        values: Sample values from column

    Returns:
        "text", "number", "date", or "mixed"
    """
    if not values:
        return "text"

    type_counts = {"text": 0, "number": 0, "date": 0, "empty": 0}

    for val in values:
        if val is None or str(val).strip() == "":
            type_counts["empty"] += 1
            continue

        str_val = str(val).strip()

        # Check if number
        try:
            float(str_val.replace(",", ".").replace(" ", ""))
            type_counts["number"] += 1
            continue
        except ValueError:
            pass

        # Check if date-like (simple patterns)
        if any(sep in str_val for sep in ["/", "-"]) and len(str_val) <= 20:
            if any(c.isdigit() for c in str_val):
                type_counts["date"] += 1
                continue

        type_counts["text"] += 1

    # Determine predominant type
    non_empty = sum(v for k, v in type_counts.items() if k != "empty")
    if non_empty == 0:
        return "text"

    for dtype, count in type_counts.items():
        if dtype != "empty" and count / non_empty > 0.7:
            return dtype

    return "mixed"


# =============================================================================
# Sheet Purpose Detection (THINK phase)
# =============================================================================


def detect_sheet_purpose(
    sheet_name: str,
    columns: List[ColumnAnalysis],
    row_count: int,
) -> Tuple[SheetPurpose, float]:
    """
    Detect the purpose of a sheet based on name and content.

    Args:
        sheet_name: Name of the sheet
        columns: Analyzed columns
        row_count: Number of data rows

    Returns:
        Tuple of (SheetPurpose, confidence)
    """
    name_lower = normalize_column_name(sheet_name)

    # Check sheet name patterns
    name_hints = {
        SheetPurpose.SERIALS: ["serial", "serie", "sn", "ns"],
        SheetPurpose.SUMMARY: ["resumo", "summary", "total", "consolidado"],
        SheetPurpose.METADATA: ["info", "cabecalho", "header", "meta"],
        SheetPurpose.PROJECTS: ["projeto", "project", "obra"],
        SheetPurpose.LOCATIONS: ["local", "location", "deposito", "armazem"],
        SheetPurpose.ITEMS: ["item", "material", "produto", "equipamento", "dados"],
    }

    for purpose, hints in name_hints.items():
        if any(h in name_lower for h in hints):
            return purpose, 0.85

    # Analyze columns to determine purpose
    column_fields = [c.suggested_mapping for c in columns if c.suggested_mapping]

    # Items sheet usually has part_number, quantity, description
    items_indicators = {"part_number", "quantity", "description"}
    if len(items_indicators & set(column_fields)) >= 2:
        return SheetPurpose.ITEMS, 0.90

    # Serials sheet has mostly serial columns
    has_serial = "serial" in column_fields
    few_columns = len(columns) <= 5
    if has_serial and few_columns:
        return SheetPurpose.SERIALS, 0.80

    # Summary sheet usually has few rows and aggregated data
    if row_count <= 10 and any("total" in normalize_column_name(c.name) for c in columns):
        return SheetPurpose.SUMMARY, 0.75

    # Default to ITEMS for sheets with many rows
    if row_count > 10:
        return SheetPurpose.ITEMS, 0.50

    return SheetPurpose.UNKNOWN, 0.30


# =============================================================================
# Relationship Detection (THINK phase)
# =============================================================================


def detect_sheet_relationships(
    sheets: List[SheetAnalysis],
) -> List[SheetRelationshipAnalysis]:
    """
    Detect relationships between sheets.

    Args:
        sheets: List of analyzed sheets

    Returns:
        List of relationship analyses
    """
    relationships = []

    for i, sheet1 in enumerate(sheets):
        for sheet2 in sheets[i + 1:]:
            relationship = _analyze_sheet_pair(sheet1, sheet2)
            if relationship:
                relationships.append(relationship)

    return relationships


def _analyze_sheet_pair(
    sheet1: SheetAnalysis,
    sheet2: SheetAnalysis,
) -> Optional[SheetRelationshipAnalysis]:
    """Analyze relationship between two sheets."""
    # Find common column mappings
    sheet1_mappings = {c.suggested_mapping for c in sheet1.columns if c.suggested_mapping}
    sheet2_mappings = {c.suggested_mapping for c in sheet2.columns if c.suggested_mapping}
    common_mappings = sheet1_mappings & sheet2_mappings

    if not common_mappings:
        return SheetRelationshipAnalysis(
            sheet1=sheet1.name,
            sheet2=sheet2.name,
            relationship_type=SheetRelationship.SEPARATE,
            confidence=0.70,
            join_columns=[],
            description=f"Abas '{sheet1.name}' e '{sheet2.name}' parecem independentes",
        )

    # Check for master-detail pattern
    if sheet1.detected_purpose == SheetPurpose.ITEMS:
        if sheet2.detected_purpose == SheetPurpose.SERIALS:
            join_cols = _find_join_columns(sheet1, sheet2, common_mappings)
            return SheetRelationshipAnalysis(
                sheet1=sheet1.name,
                sheet2=sheet2.name,
                relationship_type=SheetRelationship.ONE_TO_MANY,
                confidence=0.85,
                join_columns=join_cols,
                description=f"'{sheet1.name}' contém itens, '{sheet2.name}' contém seriais relacionados",
            )

    # Check for complement pattern
    if sheet1.detected_purpose == sheet2.detected_purpose:
        return SheetRelationshipAnalysis(
            sheet1=sheet1.name,
            sheet2=sheet2.name,
            relationship_type=SheetRelationship.COMPLEMENT,
            confidence=0.60,
            join_columns=_find_join_columns(sheet1, sheet2, common_mappings),
            description=f"Abas '{sheet1.name}' e '{sheet2.name}' podem complementar dados",
        )

    return None


def _find_join_columns(
    sheet1: SheetAnalysis,
    sheet2: SheetAnalysis,
    common_mappings: set,
) -> List[Tuple[str, str]]:
    """Find columns that can be used to join two sheets."""
    join_cols = []

    for mapping in common_mappings:
        col1 = next((c for c in sheet1.columns if c.suggested_mapping == mapping), None)
        col2 = next((c for c in sheet2.columns if c.suggested_mapping == mapping), None)

        if col1 and col2:
            join_cols.append((col1.name, col2.name))

    return join_cols


# =============================================================================
# Question Generation (ASK phase)
# =============================================================================


def generate_questions(
    analysis: "WorkbookAnalysis",
) -> List[Dict[str, Any]]:
    """
    Generate clarification questions for the user based on analysis.

    Args:
        analysis: Complete workbook analysis

    Returns:
        List of question dictionaries
    """
    questions = []

    # Question about multiple sheets
    if analysis.sheet_count > 1:
        sheet_options = [
            {"value": "all", "label": "Processar todas as abas"},
            {"value": "first", "label": f"Apenas a primeira aba ({analysis.sheets[0].name})"},
            {"value": "select", "label": "Deixe-me escolher quais abas"},
        ]

        questions.append({
            "id": "sheet_selection",
            "question": f"Encontrei {analysis.sheet_count} abas neste arquivo. Como devo processar?",
            "context": _format_sheets_context(analysis.sheets),
            "options": sheet_options,
            "importance": "high",
            "topic": "sheet_selection",
        })

    # Question about unmapped columns
    for sheet in analysis.sheets:
        unmapped = [c for c in sheet.columns if not c.suggested_mapping]
        if len(unmapped) > 5:
            # Find columns that might be important
            potential_keys = [c for c in unmapped if c.is_likely_key]
            if potential_keys:
                questions.append({
                    "id": f"column_mapping_{sheet.name}",
                    "question": f"Na aba '{sheet.name}', a coluna '{potential_keys[0].name}' corresponde a qual campo?",
                    "context": f"Valores exemplo: {', '.join(potential_keys[0].sample_values[:3])}",
                    "options": [
                        {"value": "part_number", "label": "Part Number / Código"},
                        {"value": "serial", "label": "Número de Série"},
                        {"value": "project", "label": "Projeto"},
                        {"value": "ignore", "label": "Ignorar esta coluna"},
                    ],
                    "importance": "critical",
                    "topic": "column_mapping",
                    "column": potential_keys[0].name,
                })

    # Question about movement type (if not obvious)
    questions.append({
        "id": "movement_type",
        "question": "Este arquivo é para qual tipo de movimentação?",
        "context": "Preciso saber o tipo para processar corretamente",
        "options": [
            {"value": "entry", "label": "Entrada (Internalização)"},
            {"value": "exit", "label": "Saída (Expedição)"},
            {"value": "transfer", "label": "Transferência"},
            {"value": "reverse", "label": "Reversa (Devolução)"},
        ],
        "importance": "critical",
        "topic": "movement_type",
    })

    return questions


def _format_sheets_context(sheets: List[SheetAnalysis]) -> str:
    """Format sheets info for question context."""
    lines = []
    for sheet in sheets:
        purpose_label = {
            SheetPurpose.ITEMS: "Itens",
            SheetPurpose.SERIALS: "Seriais",
            SheetPurpose.SUMMARY: "Resumo",
            SheetPurpose.METADATA: "Metadados",
            SheetPurpose.PROJECTS: "Projetos",
            SheetPurpose.LOCATIONS: "Locais",
            SheetPurpose.UNKNOWN: "Desconhecido",
        }.get(sheet.detected_purpose, "?")

        lines.append(f"• {sheet.name}: {sheet.row_count} linhas ({purpose_label})")

    return "\n".join(lines)


# =============================================================================
# Main Analysis Function (OBSERVE + THINK)
# =============================================================================


def analyze_workbook(
    content: bytes,
    filename: str,
    max_sample_rows: int = 20,
) -> WorkbookAnalysis:
    """
    Perform complete analysis of an XLSX workbook.

    This is the main entry point for the OBSERVE and THINK phases.

    Args:
        content: Raw file content as bytes
        filename: Original filename
        max_sample_rows: Maximum rows to sample per sheet

    Returns:
        Complete WorkbookAnalysis with recommendations
    """
    # Import openpyxl (lazy import to reduce cold start)
    try:
        from openpyxl import load_workbook
    except ImportError:
        raise ImportError(
            "openpyxl package required for Excel analysis. "
            "Add 'openpyxl>=3.1.0' to requirements.txt"
        )

    reasoning_trace = []

    # OBSERVE: Load workbook
    reasoning_trace.append({
        "type": "thought",
        "content": f"Vou analisar a estrutura do arquivo '{filename}'",
    })

    wb = load_workbook(io.BytesIO(content), read_only=True, data_only=True)

    reasoning_trace.append({
        "type": "observation",
        "content": f"Arquivo tem {len(wb.sheetnames)} aba(s): {', '.join(wb.sheetnames)}",
    })

    # OBSERVE: Analyze each sheet
    sheets_analysis = []
    total_rows = 0

    for sheet_name in wb.sheetnames:
        reasoning_trace.append({
            "type": "action",
            "content": f"Analisando aba '{sheet_name}'",
        })

        ws = wb[sheet_name]
        sheet_analysis = _analyze_sheet(ws, sheet_name, max_sample_rows)
        sheets_analysis.append(sheet_analysis)
        total_rows += sheet_analysis.row_count

        reasoning_trace.append({
            "type": "observation",
            "content": (
                f"Aba '{sheet_name}': {sheet_analysis.row_count} linhas, "
                f"{sheet_analysis.column_count} colunas, "
                f"propósito detectado: {sheet_analysis.detected_purpose.value}"
            ),
        })

    wb.close()

    # THINK: Detect relationships
    reasoning_trace.append({
        "type": "thought",
        "content": "Vou verificar se existe relação entre as abas",
    })

    relationships = detect_sheet_relationships(sheets_analysis)

    for rel in relationships:
        reasoning_trace.append({
            "type": "observation",
            "content": rel.description,
        })

    # THINK: Determine strategy
    reasoning_trace.append({
        "type": "thought",
        "content": "Decidindo a melhor estratégia de processamento",
    })

    strategy = _determine_processing_strategy(sheets_analysis, relationships)

    reasoning_trace.append({
        "type": "conclusion",
        "content": f"Estratégia recomendada: {strategy}",
    })

    # Build analysis
    analysis = WorkbookAnalysis(
        filename=filename,
        sheet_count=len(wb.sheetnames),
        total_rows=total_rows,
        sheets=sheets_analysis,
        relationships=relationships,
        recommended_strategy=strategy,
        questions_for_user=[],
        reasoning_trace=reasoning_trace,
    )

    # ASK: Generate questions
    analysis.questions_for_user = generate_questions(analysis)

    return analysis


def _analyze_sheet(
    ws,
    sheet_name: str,
    max_sample_rows: int,
) -> SheetAnalysis:
    """Analyze a single worksheet."""
    rows_iter = ws.iter_rows(values_only=True)

    # Get headers
    headers_row = next(rows_iter, None)
    if not headers_row:
        return SheetAnalysis(
            name=sheet_name,
            row_count=0,
            column_count=0,
            columns=[],
            detected_purpose=SheetPurpose.UNKNOWN,
            purpose_confidence=0.0,
            has_headers=False,
            suggested_action="skip",
            notes=["Aba vazia"],
        )

    headers = [str(h) if h else f"Column_{i}" for i, h in enumerate(headers_row)]

    # Sample rows for analysis
    sample_rows = []
    row_count = 0
    for row in rows_iter:
        row_count += 1
        if len(sample_rows) < max_sample_rows:
            sample_rows.append(row)

    # Analyze columns
    columns = []
    for col_idx, header in enumerate(headers):
        col_values = [row[col_idx] if col_idx < len(row) else None for row in sample_rows]

        # Detect mapping
        mapping, confidence = detect_column_mapping(header)

        # Detect data type
        data_type = detect_data_type(col_values)

        # Detect if likely key column
        unique_vals = set(str(v) for v in col_values if v)
        is_key = len(unique_vals) == len([v for v in col_values if v])

        columns.append(ColumnAnalysis(
            name=header,
            normalized_name=normalize_column_name(header),
            sample_values=[str(v) for v in col_values[:5] if v],
            data_type=data_type,
            unique_count=len(unique_vals),
            null_count=sum(1 for v in col_values if not v),
            is_likely_key=is_key and len(unique_vals) > 1,
            suggested_mapping=mapping,
            mapping_confidence=confidence,
        ))

    # Detect sheet purpose
    purpose, purpose_confidence = detect_sheet_purpose(sheet_name, columns, row_count)

    # Determine action
    if purpose == SheetPurpose.SUMMARY or purpose == SheetPurpose.METADATA:
        action = "skip"
    elif purpose == SheetPurpose.SERIALS:
        action = "merge_with"
    else:
        action = "process"

    return SheetAnalysis(
        name=sheet_name,
        row_count=row_count,
        column_count=len(headers),
        columns=columns,
        detected_purpose=purpose,
        purpose_confidence=purpose_confidence,
        has_headers=True,
        suggested_action=action,
        notes=[],
    )


def _determine_processing_strategy(
    sheets: List[SheetAnalysis],
    relationships: List[SheetRelationshipAnalysis],
) -> str:
    """Determine the best processing strategy for the workbook."""
    # Single sheet - straightforward
    if len(sheets) == 1:
        return "process_single"

    # All sheets are items - process all
    items_sheets = [s for s in sheets if s.detected_purpose == SheetPurpose.ITEMS]
    if len(items_sheets) == len(sheets):
        return "process_all_separate"

    # Has items + serials relationship
    has_serial_rel = any(
        r.relationship_type == SheetRelationship.ONE_TO_MANY
        for r in relationships
    )
    if has_serial_rel:
        return "merge_items_serials"

    # Has complement relationship
    has_complement = any(
        r.relationship_type == SheetRelationship.COMPLEMENT
        for r in relationships
    )
    if has_complement:
        return "merge_complement"

    # Default: process main sheet only
    return "process_main_only"


# =============================================================================
# Serialization for JSON Response
# =============================================================================


def analysis_to_dict(analysis: WorkbookAnalysis) -> Dict[str, Any]:
    """
    Convert WorkbookAnalysis to dictionary for JSON serialization.

    Args:
        analysis: WorkbookAnalysis object

    Returns:
        Dictionary representation
    """
    return {
        "filename": analysis.filename,
        "sheet_count": analysis.sheet_count,
        "total_rows": analysis.total_rows,
        "sheets": [
            {
                "name": s.name,
                "row_count": s.row_count,
                "column_count": s.column_count,
                "columns": [
                    {
                        "name": c.name,
                        "normalized_name": c.normalized_name,
                        "sample_values": c.sample_values,
                        "data_type": c.data_type,
                        "unique_count": c.unique_count,
                        "null_count": c.null_count,
                        "is_likely_key": c.is_likely_key,
                        "suggested_mapping": c.suggested_mapping,
                        "mapping_confidence": c.mapping_confidence,
                    }
                    for c in s.columns
                ],
                "purpose": s.detected_purpose.value,
                "confidence": s.purpose_confidence,
                "has_headers": s.has_headers,
                "suggested_action": s.suggested_action,
                "merge_target": s.merge_target,
                "notes": s.notes,
            }
            for s in analysis.sheets
        ],
        "relationships": [
            {
                "sheet1": r.sheet1,
                "sheet2": r.sheet2,
                "relationship_type": r.relationship_type.value,
                "confidence": r.confidence,
                "join_columns": r.join_columns,
                "description": r.description,
            }
            for r in analysis.relationships
        ],
        "recommended_strategy": analysis.recommended_strategy,
        "questions_for_user": analysis.questions_for_user,
        "reasoning_trace": analysis.reasoning_trace,
    }
