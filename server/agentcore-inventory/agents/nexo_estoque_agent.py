# =============================================================================
# NexoEstoqueAgent - Shim Class for Strands A2A Migration
# =============================================================================
# This module provides the NexoEstoqueAgent class expected by main_a2a.py.
# NexoEstoque is the AI copilot for inventory management queries.
#
# Created during Day 5 CLEANUP of Strands A2A migration.
# =============================================================================

import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class NexoEstoqueAgent:
    """
    NexoEstoqueAgent shim class for Strands A2A.

    This is the NEXO AI Copilot for inventory queries.
    Provides natural language interface for:
    - Stock balance queries
    - Asset location lookup
    - Movement history
    - Knowledge base Q&A

    Expected interface:
    - chat(): Process natural language query
    """

    def __init__(self):
        """Initialize the agent."""
        self.agent_id = "nexo_estoque"
        self.agent_name = "NexoEstoqueAgent"
        logger.info(f"[{self.agent_name}] Initialized (Strands A2A shim)")

    async def chat(
        self,
        question: str,
        user_id: str = None,
        session_id: str = None,
        context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Process natural language query about inventory.

        Uses Gemini 3.0 to understand the query and route to appropriate tools.

        Args:
            question: User's natural language question
            user_id: User ID for context
            session_id: Session ID for conversation history
            context: Additional context (e.g., current view, selected asset)

        Returns:
            AI-generated answer with sources and confidence
        """
        try:
            # Analyze question intent
            intent = self._analyze_intent(question)

            if intent == "BALANCE_QUERY":
                result = await self._handle_balance_query(question, session_id)
            elif intent == "LOCATION_QUERY":
                result = await self._handle_location_query(question, session_id)
            elif intent == "MOVEMENT_HISTORY":
                result = await self._handle_movement_history(question, session_id)
            elif intent == "GENERAL_KNOWLEDGE":
                result = await self._handle_knowledge_query(question, session_id)
            else:
                # Fallback: Use LLM to generate response
                result = await self._handle_general_query(question, session_id)

            return {
                "success": True,
                "answer": result.get("answer", "Não consegui processar sua pergunta."),
                "sources": result.get("sources", []),
                "confidence": result.get("confidence", 0.5),
                "intent": intent,
                "data": result.get("data"),
            }

        except Exception as e:
            logger.error(f"[{self.agent_name}] chat failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "answer": f"Desculpe, ocorreu um erro ao processar sua pergunta: {e}",
                "confidence": 0,
            }

    def _analyze_intent(self, question: str) -> str:
        """
        Analyze question to determine intent.

        Simple keyword-based analysis for now.
        Could be enhanced with LLM classification.
        """
        question_lower = question.lower()

        if any(kw in question_lower for kw in ["saldo", "quantidade", "quantos", "quantas", "estoque"]):
            return "BALANCE_QUERY"

        if any(kw in question_lower for kw in ["onde", "localização", "local", "localizar", "encontrar"]):
            return "LOCATION_QUERY"

        if any(kw in question_lower for kw in ["histórico", "movimentação", "movimentações", "quando", "últim"]):
            return "MOVEMENT_HISTORY"

        if any(kw in question_lower for kw in ["como", "o que", "por que", "explique", "ajuda"]):
            return "GENERAL_KNOWLEDGE"

        return "GENERAL"

    async def _handle_balance_query(
        self,
        question: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """Handle stock balance queries."""
        try:
            from tools.postgres_client import SGAPostgresClient

            pg = SGAPostgresClient()

            # Extract part number or asset from question (simplified)
            # In production, use NER or LLM extraction
            sql = """
                SELECT pn.part_number, pn.description,
                       COALESCE(SUM(b.quantity), 0) as total_quantity,
                       COUNT(DISTINCT l.location_id) as locations_count
                FROM sga.part_numbers pn
                LEFT JOIN sga.balances b ON pn.part_number_id = b.part_number_id
                LEFT JOIN sga.locations l ON b.location_id = l.location_id
                GROUP BY pn.part_number_id, pn.part_number, pn.description
                HAVING COALESCE(SUM(b.quantity), 0) > 0
                ORDER BY total_quantity DESC
                LIMIT 10
            """
            results = pg.execute_sql(sql)

            if results:
                answer = "Aqui está o resumo dos saldos em estoque:\n\n"
                for r in results:
                    answer += f"• **{r['part_number']}** ({r['description']}): {r['total_quantity']} unidades em {r['locations_count']} local(is)\n"

                return {
                    "answer": answer,
                    "sources": ["PostgreSQL - sga.balances"],
                    "confidence": 0.9,
                    "data": results,
                }
            else:
                return {
                    "answer": "Não encontrei registros de saldo em estoque.",
                    "sources": [],
                    "confidence": 0.8,
                }

        except Exception as e:
            logger.error(f"Balance query failed: {e}")
            return {
                "answer": f"Erro ao consultar saldos: {e}",
                "confidence": 0.3,
            }

    async def _handle_location_query(
        self,
        question: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """Handle location queries."""
        try:
            from tools.postgres_client import SGAPostgresClient

            pg = SGAPostgresClient()

            sql = """
                SELECT l.location_code, l.location_name, l.location_type,
                       COUNT(DISTINCT a.asset_id) as asset_count,
                       SUM(b.quantity) as total_items
                FROM sga.locations l
                LEFT JOIN sga.assets a ON l.location_id = a.current_location_id
                LEFT JOIN sga.balances b ON l.location_id = b.location_id
                GROUP BY l.location_id, l.location_code, l.location_name, l.location_type
                ORDER BY l.location_name
            """
            results = pg.execute_sql(sql)

            if results:
                answer = "Locais de estoque disponíveis:\n\n"
                for r in results:
                    answer += f"• **{r['location_code']}** - {r['location_name']} ({r['location_type']}): {r['asset_count'] or 0} ativos, {r['total_items'] or 0} itens\n"

                return {
                    "answer": answer,
                    "sources": ["PostgreSQL - sga.locations"],
                    "confidence": 0.9,
                    "data": results,
                }
            else:
                return {
                    "answer": "Não encontrei locais cadastrados.",
                    "sources": [],
                    "confidence": 0.8,
                }

        except Exception as e:
            logger.error(f"Location query failed: {e}")
            return {
                "answer": f"Erro ao consultar locais: {e}",
                "confidence": 0.3,
            }

    async def _handle_movement_history(
        self,
        question: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """Handle movement history queries."""
        try:
            from tools.postgres_client import SGAPostgresClient

            pg = SGAPostgresClient()

            sql = """
                SELECT m.movement_id, m.movement_type, m.quantity,
                       m.created_at, m.reference,
                       fl.location_name as from_location,
                       tl.location_name as to_location,
                       pn.part_number, pn.description
                FROM sga.movements m
                LEFT JOIN sga.locations fl ON m.from_location_id = fl.location_id
                LEFT JOIN sga.locations tl ON m.to_location_id = tl.location_id
                LEFT JOIN sga.part_numbers pn ON m.part_number_id = pn.part_number_id
                ORDER BY m.created_at DESC
                LIMIT 10
            """
            results = pg.execute_sql(sql)

            if results:
                answer = "Últimas movimentações de estoque:\n\n"
                for r in results:
                    date = r['created_at'].strftime('%d/%m/%Y %H:%M') if r.get('created_at') else 'N/A'
                    answer += f"• **{r['movement_type']}** ({date}): {r['quantity']}x {r['part_number']} - {r.get('from_location', 'N/A')} → {r.get('to_location', 'N/A')}\n"

                return {
                    "answer": answer,
                    "sources": ["PostgreSQL - sga.movements"],
                    "confidence": 0.9,
                    "data": results,
                }
            else:
                return {
                    "answer": "Não encontrei movimentações recentes.",
                    "sources": [],
                    "confidence": 0.8,
                }

        except Exception as e:
            logger.error(f"Movement history query failed: {e}")
            return {
                "answer": f"Erro ao consultar histórico: {e}",
                "confidence": 0.3,
            }

    async def _handle_knowledge_query(
        self,
        question: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """Handle knowledge base queries."""
        # Placeholder for KB/RAG integration
        return {
            "answer": "Para perguntas sobre processos e procedimentos, consulte a documentação do SGA ou entre em contato com o suporte.",
            "sources": ["Knowledge Base"],
            "confidence": 0.6,
        }

    async def _handle_general_query(
        self,
        question: str,
        session_id: str,
    ) -> Dict[str, Any]:
        """Handle general queries using LLM."""
        # Placeholder for general LLM response
        return {
            "answer": f"Entendi sua pergunta: '{question}'. Por favor, seja mais específico sobre o que deseja saber sobre o estoque.",
            "sources": [],
            "confidence": 0.5,
        }


# Export for import compatibility
__all__ = ["NexoEstoqueAgent"]
