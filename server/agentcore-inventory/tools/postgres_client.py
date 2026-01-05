"""
PostgreSQL Client for SGA Inventory.

This client connects to Aurora PostgreSQL via RDS Proxy using IAM authentication.
Designed for use within AWS Lambda functions.

Architecture:
    Lambda -> RDS Proxy (IAM auth) -> Aurora PostgreSQL Serverless v2

Security:
    - IAM authentication (no password in code)
    - TLS encryption required
    - Connection pooling via RDS Proxy

Author: Faiston NEXO Team
Date: January 2026
"""

import logging
import os
from typing import Any, Dict, List, Optional
from datetime import datetime, date
import boto3

# Configure logging
logger = logging.getLogger(__name__)


class SGAPostgresClient:
    """
    PostgreSQL client for SGA inventory operations.

    Uses IAM authentication via RDS Proxy for secure, password-less connections.
    """

    def __init__(self):
        """Initialize the PostgreSQL client."""
        self._connection = None
        self._rds_client = boto3.client("rds")

        # Configuration from environment
        self._proxy_endpoint = os.environ.get("RDS_PROXY_ENDPOINT")
        self._database = os.environ.get("RDS_DATABASE_NAME", "sga_inventory")
        self._port = int(os.environ.get("RDS_PORT", "5432"))
        self._region = os.environ.get("AWS_REGION_NAME", "us-east-2")
        self._user = "sgaadmin"  # IAM auth uses username, no password

    def _get_connection(self):
        """
        Get or create a database connection using IAM authentication.

        Returns:
            psycopg connection object
        """
        if self._connection is not None and not self._connection.closed:
            return self._connection

        try:
            import psycopg
            from psycopg.rows import dict_row

            # Generate IAM auth token
            token = self._rds_client.generate_db_auth_token(
                DBHostname=self._proxy_endpoint,
                Port=self._port,
                DBUsername=self._user,
                Region=self._region
            )

            # Connect to RDS Proxy
            self._connection = psycopg.connect(
                host=self._proxy_endpoint,
                port=self._port,
                user=self._user,
                password=token,
                dbname=self._database,
                sslmode="require",
                row_factory=dict_row
            )

            logger.info("Connected to PostgreSQL via RDS Proxy")
            return self._connection

        except Exception as e:
            logger.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def _execute_query(
        self,
        query: str,
        params: Optional[tuple] = None,
        fetch_all: bool = True
    ) -> List[Dict]:
        """
        Execute a SQL query and return results.

        Args:
            query: SQL query string
            params: Query parameters (optional)
            fetch_all: If True, fetch all results; if False, return cursor

        Returns:
            List of dictionaries representing rows
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                if fetch_all:
                    return cur.fetchall()
                return []
        except Exception as e:
            conn.rollback()
            logger.error(f"Query execution failed: {e}")
            raise

    def _execute_write(self, query: str, params: Optional[tuple] = None) -> int:
        """
        Execute a write query (INSERT, UPDATE, DELETE).

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Number of affected rows
        """
        conn = self._get_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(query, params)
                conn.commit()
                return cur.rowcount
        except Exception as e:
            conn.rollback()
            logger.error(f"Write operation failed: {e}")
            raise

    # =========================================================================
    # Query Methods
    # =========================================================================

    def list_inventory(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List inventory with optional filters.

        Args:
            filters: Dictionary of filter conditions
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Dictionary with items and pagination info
        """
        filters = filters or {}

        # Build query using materialized view for performance
        query = """
            SELECT *
            FROM sga.mv_inventory_summary
            WHERE 1=1
        """
        params = []

        if "location_id" in filters:
            query += " AND location_code = %s"
            params.append(filters["location_id"])

        if "part_number" in filters:
            query += " AND part_number = %s"
            params.append(filters["part_number"])

        if "status" in filters:
            query += " AND stock_status = %s"
            params.append(filters["status"])

        # Get total count
        count_query = f"SELECT COUNT(*) as total FROM ({query}) AS subq"
        count_result = self._execute_query(count_query, tuple(params))
        total = count_result[0]["total"] if count_result else 0

        # Add pagination
        query += " ORDER BY part_number, location_code LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        items = self._execute_query(query, tuple(params))

        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + len(items)) < total
        }

    def get_balance(
        self,
        part_number: str,
        location_id: Optional[str] = None,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get stock balance for a part number.

        Args:
            part_number: Part number to query
            location_id: Optional location filter
            project_id: Optional project filter

        Returns:
            Balance information
        """
        query = """
            SELECT
                b.balance_id,
                pn.part_number,
                pn.description,
                l.location_code,
                l.location_name,
                p.project_code,
                p.project_name,
                b.quantity_total,
                b.quantity_reserved,
                b.quantity_available,
                b.last_movement_at,
                b.last_count_at
            FROM sga.balances b
            JOIN sga.part_numbers pn ON b.part_number_id = pn.part_number_id
            JOIN sga.locations l ON b.location_id = l.location_id
            LEFT JOIN sga.projects p ON b.project_id = p.project_id
            WHERE pn.part_number = %s
        """
        params = [part_number]

        if location_id:
            query += " AND l.location_code = %s"
            params.append(location_id)

        if project_id:
            query += " AND p.project_code = %s"
            params.append(project_id)

        results = self._execute_query(query, tuple(params))

        if not results:
            return {
                "found": False,
                "part_number": part_number,
                "message": "No balance found for this part number"
            }

        # Aggregate if multiple locations
        total_quantity = sum(r["quantity_total"] for r in results)
        total_reserved = sum(r["quantity_reserved"] for r in results)
        total_available = sum(r["quantity_available"] for r in results)

        return {
            "found": True,
            "part_number": part_number,
            "description": results[0]["description"],
            "summary": {
                "total_quantity": total_quantity,
                "total_reserved": total_reserved,
                "total_available": total_available
            },
            "by_location": results
        }

    def search_assets(
        self,
        query: str,
        search_type: str = "all",
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Search assets by serial, part number, or description.

        Args:
            query: Search term
            search_type: Type of search (serial, part_number, description, all)
            limit: Maximum results

        Returns:
            Search results
        """
        base_query = """
            SELECT
                a.asset_id,
                a.serial_number,
                pn.part_number,
                pn.description,
                l.location_code,
                l.location_name,
                p.project_code,
                a.status,
                a.condition,
                a.last_movement_at
            FROM sga.assets a
            JOIN sga.part_numbers pn ON a.part_number_id = pn.part_number_id
            LEFT JOIN sga.locations l ON a.location_id = l.location_id
            LEFT JOIN sga.projects p ON a.project_id = p.project_id
            WHERE a.is_active = TRUE
        """

        if search_type == "serial":
            base_query += " AND a.serial_number ILIKE %s"
            params = [f"%{query}%"]
        elif search_type == "part_number":
            base_query += " AND pn.part_number ILIKE %s"
            params = [f"%{query}%"]
        elif search_type == "description":
            base_query += " AND pn.search_vector @@ plainto_tsquery('portuguese', %s)"
            params = [query]
        else:  # all
            base_query += """
                AND (
                    a.serial_number ILIKE %s
                    OR pn.part_number ILIKE %s
                    OR pn.search_vector @@ plainto_tsquery('portuguese', %s)
                )
            """
            params = [f"%{query}%", f"%{query}%", query]

        base_query += " ORDER BY a.serial_number LIMIT %s"
        params.append(limit)

        results = self._execute_query(base_query, tuple(params))

        return {
            "query": query,
            "search_type": search_type,
            "count": len(results),
            "items": results
        }

    def get_asset_timeline(
        self,
        identifier: str,
        identifier_type: str = "serial_number",
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Get complete movement history of an asset.

        Args:
            identifier: Asset ID or serial number
            identifier_type: Type of identifier
            limit: Maximum events to return

        Returns:
            Asset info and timeline events
        """
        # First, get asset info
        if identifier_type == "asset_id":
            asset_query = """
                SELECT
                    a.asset_id,
                    a.serial_number,
                    pn.part_number,
                    pn.description,
                    l.location_code,
                    l.location_name,
                    p.project_code,
                    a.status,
                    a.condition,
                    a.purchase_date,
                    a.nf_number,
                    a.nf_date,
                    a.created_at
                FROM sga.assets a
                JOIN sga.part_numbers pn ON a.part_number_id = pn.part_number_id
                LEFT JOIN sga.locations l ON a.location_id = l.location_id
                LEFT JOIN sga.projects p ON a.project_id = p.project_id
                WHERE a.asset_id = %s::uuid
            """
        else:
            asset_query = """
                SELECT
                    a.asset_id,
                    a.serial_number,
                    pn.part_number,
                    pn.description,
                    l.location_code,
                    l.location_name,
                    p.project_code,
                    a.status,
                    a.condition,
                    a.purchase_date,
                    a.nf_number,
                    a.nf_date,
                    a.created_at
                FROM sga.assets a
                JOIN sga.part_numbers pn ON a.part_number_id = pn.part_number_id
                LEFT JOIN sga.locations l ON a.location_id = l.location_id
                LEFT JOIN sga.projects p ON a.project_id = p.project_id
                WHERE a.serial_number = %s
            """

        asset_result = self._execute_query(asset_query, (identifier,))

        if not asset_result:
            return {
                "found": False,
                "identifier": identifier,
                "message": "Asset not found"
            }

        asset = asset_result[0]

        # Get movement timeline
        timeline_query = """
            SELECT
                m.movement_id,
                m.movement_type,
                m.movement_date,
                m.quantity,
                sl.location_code as source_location,
                dl.location_code as destination_location,
                p.project_code,
                m.nf_number,
                m.reason,
                m.created_by
            FROM sga.movement_items mi
            JOIN sga.movements m ON mi.movement_id = m.movement_id
            LEFT JOIN sga.locations sl ON m.source_location_id = sl.location_id
            LEFT JOIN sga.locations dl ON m.destination_location_id = dl.location_id
            LEFT JOIN sga.projects p ON m.project_id = p.project_id
            WHERE mi.asset_id = %s::uuid
            ORDER BY m.movement_date DESC
            LIMIT %s
        """

        timeline = self._execute_query(
            timeline_query,
            (str(asset["asset_id"]), limit)
        )

        return {
            "found": True,
            "asset": asset,
            "timeline": timeline,
            "timeline_count": len(timeline)
        }

    def get_movements(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        List movements with filters.

        Args:
            filters: Filter conditions
            limit: Maximum results

        Returns:
            List of movements
        """
        filters = filters or {}

        query = """
            SELECT
                m.movement_id,
                m.movement_type,
                m.movement_date,
                pn.part_number,
                pn.description,
                m.quantity,
                sl.location_code as source_location,
                dl.location_code as destination_location,
                p.project_code,
                m.nf_number,
                m.nf_date,
                m.reason,
                m.created_by,
                m.created_at
            FROM sga.movements m
            JOIN sga.part_numbers pn ON m.part_number_id = pn.part_number_id
            LEFT JOIN sga.locations sl ON m.source_location_id = sl.location_id
            LEFT JOIN sga.locations dl ON m.destination_location_id = dl.location_id
            LEFT JOIN sga.projects p ON m.project_id = p.project_id
            WHERE 1=1
        """
        params = []

        if "start_date" in filters:
            query += " AND m.movement_date >= %s"
            params.append(filters["start_date"])

        if "end_date" in filters:
            query += " AND m.movement_date <= %s"
            params.append(filters["end_date"])

        if "movement_type" in filters:
            query += " AND m.movement_type = %s"
            params.append(filters["movement_type"])

        if "project_id" in filters:
            query += " AND p.project_code = %s"
            params.append(filters["project_id"])

        if "location_id" in filters:
            query += " AND (sl.location_code = %s OR dl.location_code = %s)"
            params.extend([filters["location_id"], filters["location_id"]])

        query += " ORDER BY m.movement_date DESC LIMIT %s"
        params.append(limit)

        results = self._execute_query(query, tuple(params))

        return {
            "count": len(results),
            "items": results
        }

    def get_pending_tasks(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        List pending approval tasks (from pending_entries table).

        Args:
            filters: Filter conditions
            limit: Maximum results

        Returns:
            List of pending tasks
        """
        filters = filters or {}

        query = """
            SELECT
                entry_id,
                source_type,
                nf_number,
                nf_date,
                supplier_name,
                total_value,
                total_items,
                status,
                ocr_confidence,
                created_at,
                created_by
            FROM sga.pending_entries
            WHERE status IN ('PENDING', 'PROCESSING')
        """
        params = []

        if "task_type" in filters:
            # Map task_type to source_type
            task_mapping = {
                "APPROVAL_ENTRY": ["NF_XML", "NF_PDF", "NF_IMAGE", "MANUAL"],
                "DOCUMENT_REVIEW": ["SAP_IMPORT", "BULK_IMPORT"],
            }
            source_types = task_mapping.get(filters["task_type"], [])
            if source_types:
                placeholders = ",".join(["%s"] * len(source_types))
                query += f" AND source_type IN ({placeholders})"
                params.extend(source_types)

        query += " ORDER BY created_at DESC LIMIT %s"
        params.append(limit)

        results = self._execute_query(query, tuple(params))

        return {
            "count": len(results),
            "items": results
        }

    def create_movement(
        self,
        movement_type: str,
        part_number: str,
        quantity: int,
        source_location_id: Optional[str] = None,
        destination_location_id: Optional[str] = None,
        project_id: Optional[str] = None,
        serial_numbers: Optional[List[str]] = None,
        nf_number: Optional[str] = None,
        nf_date: Optional[str] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new inventory movement.

        Args:
            movement_type: Type of movement
            part_number: Part number
            quantity: Quantity
            source_location_id: Source location code
            destination_location_id: Destination location code
            project_id: Project code
            serial_numbers: List of serial numbers
            nf_number: NF number
            nf_date: NF date
            reason: Reason for movement

        Returns:
            Created movement info
        """
        # Look up IDs from codes
        pn_query = "SELECT part_number_id FROM sga.part_numbers WHERE part_number = %s"
        pn_result = self._execute_query(pn_query, (part_number,))
        if not pn_result:
            return {"error": f"Part number not found: {part_number}"}
        part_number_id = pn_result[0]["part_number_id"]

        source_id = None
        if source_location_id:
            loc_query = "SELECT location_id FROM sga.locations WHERE location_code = %s"
            loc_result = self._execute_query(loc_query, (source_location_id,))
            if loc_result:
                source_id = loc_result[0]["location_id"]

        dest_id = None
        if destination_location_id:
            loc_query = "SELECT location_id FROM sga.locations WHERE location_code = %s"
            loc_result = self._execute_query(loc_query, (destination_location_id,))
            if loc_result:
                dest_id = loc_result[0]["location_id"]

        proj_id = None
        if project_id:
            proj_query = "SELECT project_id FROM sga.projects WHERE project_code = %s"
            proj_result = self._execute_query(proj_query, (project_id,))
            if proj_result:
                proj_id = proj_result[0]["project_id"]

        # Insert movement
        insert_query = """
            INSERT INTO sga.movements (
                movement_type,
                part_number_id,
                quantity,
                source_location_id,
                destination_location_id,
                project_id,
                nf_number,
                nf_date,
                reason,
                created_by
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING movement_id, movement_date
        """

        conn = self._get_connection()
        with conn.cursor() as cur:
            cur.execute(insert_query, (
                movement_type,
                str(part_number_id),
                quantity,
                str(source_id) if source_id else None,
                str(dest_id) if dest_id else None,
                str(proj_id) if proj_id else None,
                nf_number,
                nf_date,
                reason,
                "mcp_lambda"  # Created by MCP tool
            ))
            result = cur.fetchone()
            conn.commit()

        return {
            "success": True,
            "movement_id": str(result["movement_id"]),
            "movement_date": result["movement_date"].isoformat(),
            "message": f"Movement created: {movement_type} - {quantity} x {part_number}"
        }

    def reconcile_with_sap(
        self,
        sap_data: List[Dict[str, Any]],
        include_serials: bool = False
    ) -> Dict[str, Any]:
        """
        Compare SGA inventory with SAP export data.

        Args:
            sap_data: List of SAP items with part_number, quantity, location_code
            include_serials: Whether to include serial number comparison

        Returns:
            Reconciliation results with matches and discrepancies
        """
        results = {
            "total_sap_items": len(sap_data),
            "matches": [],
            "discrepancies": [],
            "sap_only": [],
            "sga_only": []
        }

        # Get all SGA balances
        sga_query = """
            SELECT
                pn.part_number,
                l.location_code,
                p.project_code,
                SUM(b.quantity_total) as sga_quantity
            FROM sga.balances b
            JOIN sga.part_numbers pn ON b.part_number_id = pn.part_number_id
            JOIN sga.locations l ON b.location_id = l.location_id
            LEFT JOIN sga.projects p ON b.project_id = p.project_id
            GROUP BY pn.part_number, l.location_code, p.project_code
        """
        sga_balances = self._execute_query(sga_query)

        # Create lookup for SGA data
        sga_lookup = {}
        for row in sga_balances:
            key = (row["part_number"], row.get("location_code"))
            sga_lookup[key] = row["sga_quantity"]

        # Compare each SAP item
        sap_keys_found = set()
        for sap_item in sap_data:
            key = (sap_item["part_number"], sap_item.get("location_code"))
            sap_keys_found.add(key)

            sap_qty = sap_item["quantity"]
            sga_qty = sga_lookup.get(key, 0)

            item_result = {
                "part_number": sap_item["part_number"],
                "location_code": sap_item.get("location_code"),
                "sap_quantity": sap_qty,
                "sga_quantity": sga_qty,
                "variance": sga_qty - sap_qty
            }

            if sap_qty == sga_qty:
                results["matches"].append(item_result)
            elif key not in sga_lookup:
                results["sap_only"].append(item_result)
            else:
                results["discrepancies"].append(item_result)

        # Find items in SGA but not in SAP
        for key, sga_qty in sga_lookup.items():
            if key not in sap_keys_found:
                results["sga_only"].append({
                    "part_number": key[0],
                    "location_code": key[1],
                    "sap_quantity": 0,
                    "sga_quantity": sga_qty,
                    "variance": sga_qty
                })

        results["summary"] = {
            "matches_count": len(results["matches"]),
            "discrepancies_count": len(results["discrepancies"]),
            "sap_only_count": len(results["sap_only"]),
            "sga_only_count": len(results["sga_only"]),
            "accuracy_percentage": round(
                len(results["matches"]) / len(sap_data) * 100, 2
            ) if sap_data else 100
        }

        return results
