# =============================================================================
# SAP Export Tools
# =============================================================================

import logging
from typing import Dict, Any, List, Optional

from google.adk.tools import tool
from shared.audit_emitter import AgentAuditEmitter
from shared.xray_tracer import trace_tool_call

logger = logging.getLogger(__name__)
AGENT_ID = "expedition"
audit = AgentAuditEmitter(agent_id=AGENT_ID)


# Nature of operation options for SAP NF
NATUREZA_OPERACAO = {
    "USO_CONSUMO": "REMESSA PARA USO E CONSUMO",
    "CONSERTO": "REMESSA PARA CONSERTO",
    "DEMONSTRACAO": "REMESSA PARA DEMONSTRACAO",
    "LOCACAO": "REMESSA EM LOCACAO",
    "EMPRESTIMO": "REMESSA EM EMPRESTIMO",
}


def generate_item_sap_data(
    pn: Dict[str, Any],
    serial: str,
    quantity: int,
    location_id: str,
    destination_client: str,
    nature: str,
    project_id: str,
    chamado_id: str,
) -> Dict[str, Any]:
    """
    Generate SAP-ready data for NF emission.

    Internal helper function.
    """
    natureza = NATUREZA_OPERACAO.get(nature, NATUREZA_OPERACAO["USO_CONSUMO"])

    return {
        "cliente": destination_client,
        "item_numero": pn.get("part_number", ""),
        "descricao": pn.get("description", ""),
        "serial_number": serial,
        "quantidade": quantity,
        "deposito": location_id,
        "utilizacao": "S-OUTRAS OPERACOES",
        "incoterms": "0",
        "transportadora": "",  # To be filled
        "natureza_operacao": natureza,
        "observacao": f"{project_id} - {chamado_id} - {serial}",
        "peso_liquido": 0.0,  # To be filled during separation
        "peso_bruto": 0.0,
        "embalagem": "",
    }


def format_sap_copyable(sap_data_list: List[Dict[str, Any]]) -> str:
    """Format SAP data for easy copy/paste."""
    lines = []

    for i, item in enumerate(sap_data_list, 1):
        lines.append(f"=== ITEM {i} ===")
        lines.append(f"Cliente: {item['cliente']}")
        lines.append(f"Item: {item['item_numero']} - {item.get('descricao', '')}")
        lines.append(f"Serial: {item['serial_number']}")
        lines.append(f"Quantidade: {item['quantidade']}")
        lines.append(f"Deposito: {item['deposito']}")
        lines.append(f"Utilizacao: {item['utilizacao']}")
        lines.append(f"Incoterms: {item['incoterms']}")
        lines.append(f"Natureza: {item['natureza_operacao']}")
        lines.append(f"Observacao: {item['observacao']}")
        lines.append("")

    return "\n".join(lines)


@tool
@trace_tool_call("sga_generate_sap_data")
async def generate_sap_data_tool(
    expedition_id: str,
    session_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Generate SAP-ready data for an expedition.

    Retrieves expedition details and formats data for NF emission.
    """
    audit.working(
        message=f"Gerando dados SAP para expedicao: {expedition_id}",
        session_id=session_id,
    )

    try:
        from tools.db_client import DBClient
        db = DBClient()

        # Get expedition
        expedition = await db.get_expedition(expedition_id)

        if not expedition:
            return {
                "success": False,
                "error": f"Expedicao nao encontrada: {expedition_id}",
            }

        # If SAP data already generated, return it
        if expedition.get("sap_data"):
            sap_data = expedition["sap_data"]
            copyable = format_sap_copyable(sap_data)

            audit.completed(
                message=f"Dados SAP recuperados: {len(sap_data)} itens",
                session_id=session_id,
            )

            return {
                "success": True,
                "expedition_id": expedition_id,
                "sap_data": sap_data,
                "sap_copyable": copyable,
            }

        # Generate SAP data for each item
        items = expedition.get("items", [])
        sap_data_list = []

        for item in items:
            pn = item.get("pn", {})
            sap_data = generate_item_sap_data(
                pn=pn,
                serial=item.get("serial", ""),
                quantity=item.get("quantity", 1),
                location_id=item.get("location_id", "01"),
                destination_client=expedition.get("destination_client", ""),
                nature=expedition.get("nature", "USO_CONSUMO"),
                project_id=expedition.get("project_id", ""),
                chamado_id=expedition.get("chamado_id", ""),
            )
            sap_data_list.append(sap_data)

        # Update expedition with SAP data
        await db.update_expedition(expedition_id, {"sap_data": sap_data_list})

        copyable = format_sap_copyable(sap_data_list)

        audit.completed(
            message=f"Dados SAP gerados: {len(sap_data_list)} itens",
            session_id=session_id,
        )

        return {
            "success": True,
            "expedition_id": expedition_id,
            "sap_data": sap_data_list,
            "sap_copyable": copyable,
        }

    except ImportError:
        return {"success": False, "error": "DBClient not available"}
    except Exception as e:
        logger.error(f"[generate_sap_data] Error: {e}", exc_info=True)
        audit.error(message="Erro ao gerar dados SAP", session_id=session_id, error=str(e))
        return {"success": False, "error": str(e)}
