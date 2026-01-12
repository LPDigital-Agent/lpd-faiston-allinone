# =============================================================================
# Execute Import Tool
# =============================================================================
# Executes bulk import and creates inventory movements.
# =============================================================================

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime


from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

logger = logging.getLogger(__name__)

AGENT_ID = "import"
audit = AgentAuditEmitter(agent_id=AGENT_ID)


@trace_tool_call("sga_execute_import")
async def execute_import_tool(
    import_id: str,
    s3_key: str,
    column_mappings: List[Dict[str, Any]],
    pn_overrides: Optional[Dict[str, str]] = None,
    project_id: Optional[str] = None,
    destination_location_id: Optional[str] = None,
    operator_id: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute bulk import and create movements.

    Args:
        import_id: Unique import batch ID
        s3_key: S3 key of the import file
        column_mappings: Validated column mappings
        pn_overrides: Manual PN overrides for unmatched rows
        project_id: Target project ID
        destination_location_id: Target location ID
        operator_id: User executing the import
        session_id: Optional session ID for audit

    Returns:
        Import result with statistics
    """
    audit.working(
        message=f"Executando importação {import_id}...",
        session_id=session_id,
    )

    try:
        # Build mapping lookup
        mapping_lookup = {}
        for m in column_mappings:
            source = m.get("source_column")
            target = m.get("target_field")
            if source and target:
                mapping_lookup[source] = target

        # Get column references
        pn_column = next(
            (m["source_column"] for m in column_mappings
             if m.get("target_field") == "part_number"),
            None
        )
        qty_column = next(
            (m["source_column"] for m in column_mappings
             if m.get("target_field") == "quantity"),
            None
        )
        serial_column = next(
            (m["source_column"] for m in column_mappings
             if m.get("target_field") == "serial_number"),
            None
        )
        location_column = next(
            (m["source_column"] for m in column_mappings
             if m.get("target_field") == "location"),
            None
        )

        # Download and parse file
        from agents.import.tools.preview_import import _download_file, _parse_csv, _parse_excel

        file_content, file_type = await _download_file(s3_key)
        if not file_content:
            return {
                "success": False,
                "error": f"Arquivo não encontrado: {s3_key}",
            }

        if file_type in ["xlsx", "xls"]:
            headers, rows = await _parse_excel(file_content, file_type)
        else:
            headers, rows = await _parse_csv(file_content)

        # Get part numbers for matching
        db_parts = await _get_part_numbers_map()

        # Process each row
        now = _now_iso()
        created_movements = []
        skipped_rows = []
        errors = []

        total_items = 0
        total_quantity = 0

        for row_idx, row in enumerate(rows, start=1):
            try:
                # Get part number (from column or override)
                raw_pn = row.get(pn_column) if pn_column else None
                part_number = None

                # Check override first
                if pn_overrides and raw_pn and str(raw_pn) in pn_overrides:
                    part_number = pn_overrides[str(raw_pn)]
                elif raw_pn:
                    # Look up in database
                    pn_normalized = str(raw_pn).strip().upper()
                    part_number = db_parts.get(pn_normalized)

                if not part_number:
                    skipped_rows.append({
                        "row": row_idx,
                        "reason": "PN não encontrado",
                        "raw_pn": raw_pn,
                    })
                    continue

                # Get quantity
                quantity = 1
                if qty_column and row.get(qty_column):
                    try:
                        quantity = float(row[qty_column])
                    except (ValueError, TypeError):
                        quantity = 1

                if quantity == 0:
                    skipped_rows.append({
                        "row": row_idx,
                        "reason": "Quantidade zero",
                    })
                    continue

                # Get serial numbers
                serial_numbers = []
                if serial_column and row.get(serial_column):
                    raw_serial = str(row[serial_column])
                    # Split by common delimiters
                    for delim in [",", ";", "|", "\n"]:
                        if delim in raw_serial:
                            serial_numbers = [s.strip() for s in raw_serial.split(delim) if s.strip()]
                            break
                    else:
                        serial_numbers = [raw_serial.strip()] if raw_serial.strip() else []

                # Get location (from row or default)
                location_id = destination_location_id or "ESTOQUE_CENTRAL"
                if location_column and row.get(location_column):
                    location_id = str(row[location_column]).strip()

                # Determine movement type
                movement_type = "ENTRY" if quantity > 0 else "EXIT"

                # Create movement
                movement_id = _generate_id("MOV")
                movement_data = {
                    "movement_id": movement_id,
                    "movement_type": movement_type,
                    "part_number": part_number,
                    "quantity": abs(quantity),
                    "serial_numbers": serial_numbers,
                    "destination_location_id": location_id,
                    "project_id": project_id or "UNASSIGNED",
                    "import_id": import_id,
                    "import_row": row_idx,
                    "processed_by": operator_id or "system",
                    "created_at": now,
                }

                # Store movement
                await _store_movement(movement_data)
                created_movements.append(movement_id)

                # Update balance
                balance_delta = quantity if movement_type == "ENTRY" else -abs(quantity)
                await _update_balance(
                    part_number=part_number,
                    location_id=location_id,
                    project_id=project_id or "UNASSIGNED",
                    quantity_delta=balance_delta,
                )

                # Create assets for serialized items
                for serial in serial_numbers:
                    await _create_asset(
                        serial_number=serial,
                        part_number=part_number,
                        location_id=location_id,
                        project_id=project_id or "UNASSIGNED",
                        movement_id=movement_id,
                        import_id=import_id,
                    )

                total_items += 1
                total_quantity += abs(quantity)

                # Progress update every 100 rows
                if row_idx % 100 == 0:
                    audit.working(
                        message=f"Processando... {row_idx}/{len(rows)} linhas",
                        session_id=session_id,
                    )

            except Exception as e:
                errors.append({
                    "row": row_idx,
                    "error": str(e),
                })
                logger.error(f"[execute_import] Row {row_idx} error: {e}")

        # Calculate final statistics
        match_rate = len(created_movements) / len(rows) if rows else 0

        # Store import record
        import_record = {
            "import_id": import_id,
            "s3_key": s3_key,
            "filename": s3_key.split("/")[-1],
            "total_rows": len(rows),
            "rows_imported": len(created_movements),
            "rows_skipped": len(skipped_rows),
            "rows_error": len(errors),
            "total_quantity": total_quantity,
            "match_rate": match_rate,
            "column_mappings_used": column_mappings,
            "project_id": project_id,
            "destination_location_id": destination_location_id,
            "executed_by": operator_id,
            "executed_at": now,
        }
        await _store_import_record(import_record)

        audit.completed(
            message=f"Importação concluída: {len(created_movements)}/{len(rows)} linhas",
            session_id=session_id,
            details={
                "imported": len(created_movements),
                "skipped": len(skipped_rows),
                "errors": len(errors),
            },
        )

        return {
            "success": True,
            "import_id": import_id,
            "filename": import_record["filename"],
            "message": f"Importação concluída. {len(created_movements)} de {len(rows)} linhas processadas.",
            "rows_imported": len(created_movements),
            "rows_skipped": len(skipped_rows),
            "rows_error": len(errors),
            "total_quantity": total_quantity,
            "match_rate": match_rate,
            "column_mappings_used": column_mappings,
            "movement_ids": created_movements,
            "skipped_details": skipped_rows[:20],  # First 20 for review
            "error_details": errors[:20],
        }

    except Exception as e:
        logger.error(f"[execute_import] Error: {e}", exc_info=True)
        audit.error(
            message="Erro na importação",
            session_id=session_id,
            error=str(e),
        )
        return {
            "success": False,
            "import_id": import_id,
            "error": str(e),
        }


# =============================================================================
# Helper Functions
# =============================================================================

async def _get_part_numbers_map() -> Dict[str, str]:
    """Get part numbers as a lookup map (normalized → actual)."""
    try:
        from tools.db_client import DBClient
        db = DBClient()
        parts = await db.list_part_numbers()

        return {
            str(p.get("part_number", "")).strip().upper(): p.get("part_number")
            for p in parts
            if p.get("part_number")
        }
    except ImportError:
        logger.warning("[execute_import] DBClient not available")
        return {}
    except Exception as e:
        logger.error(f"[execute_import] DB error: {e}")
        return {}


async def _store_movement(movement_data: Dict[str, Any]) -> None:
    """Store movement record."""
    try:
        from tools.db_client import DBClient
        db = DBClient()
        await db.put_movement(movement_data)
    except ImportError:
        logger.warning("[execute_import] DBClient not available")


async def _update_balance(
    part_number: str,
    location_id: str,
    project_id: str,
    quantity_delta: float,
) -> None:
    """Update inventory balance."""
    try:
        from tools.db_client import DBClient
        db = DBClient()
        await db.update_balance(
            part_number=part_number,
            location_id=location_id,
            project_id=project_id,
            quantity_delta=quantity_delta,
            reserved_delta=0,
        )
    except ImportError:
        logger.warning("[execute_import] DBClient not available")


async def _create_asset(
    serial_number: str,
    part_number: str,
    location_id: str,
    project_id: str,
    movement_id: str,
    import_id: str,
) -> None:
    """Create asset record for serialized item."""
    try:
        from tools.db_client import DBClient
        db = DBClient()

        existing = await db.get_asset_by_serial(serial_number)
        now = _now_iso()

        if existing:
            await db.update_asset(
                asset_id=existing["asset_id"],
                updates={
                    "location_id": location_id,
                    "status": "IN_STOCK",
                    "last_movement_id": movement_id,
                    "updated_at": now,
                },
            )
        else:
            asset_id = _generate_id("AST")
            await db.put_asset({
                "asset_id": asset_id,
                "serial_number": serial_number,
                "part_number": part_number,
                "location_id": location_id,
                "project_id": project_id,
                "status": "IN_STOCK",
                "acquisition_type": "BULK_IMPORT",
                "acquisition_ref": import_id,
                "last_movement_id": movement_id,
                "created_at": now,
                "updated_at": now,
            })
    except ImportError:
        logger.warning("[execute_import] DBClient not available")


async def _store_import_record(import_record: Dict[str, Any]) -> None:
    """Store import batch record."""
    try:
        from tools.db_client import DBClient
        db = DBClient()
        await db.put_import_record(import_record)
    except ImportError:
        logger.warning("[execute_import] DBClient not available")


def _generate_id(prefix: str) -> str:
    """Generate unique ID with prefix."""
    import uuid
    return f"{prefix}_{uuid.uuid4().hex[:12].upper()}"


def _now_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.utcnow().isoformat() + "Z"
