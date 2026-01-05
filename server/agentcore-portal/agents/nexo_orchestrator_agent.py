# =============================================================================
# NEXO Orchestrator Agent - Faiston Portal
# =============================================================================
# Central AI assistant for the Faiston NEXO intranet portal.
#
# Responsibilities:
# - General chat and assistance
# - News aggregation and summarization
# - A2A delegation to Academy and SGA agents
# - Daily summary generation
#
# Framework: Google ADK with Gemini 3.0 Pro (MANDATORY)
# =============================================================================

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone


# =============================================================================
# Agent Instruction (Persona)
# =============================================================================

NEXO_ORCHESTRATOR_INSTRUCTION = """
Voce e NEXO, o assistente de IA central do portal intranet Faiston.
Voce e amigavel, profissional e sempre pronto para ajudar.

## Suas Capacidades

1. **Noticias de Tecnologia**: Voce pode buscar e resumir noticias de tecnologia
   sobre Cloud (AWS, Azure, Google Cloud), Inteligencia Artificial, e tecnologia
   em geral. Use a tool `get_tech_news` para buscar noticias.

2. **Agenda (em breve)**: Futuramente voce podera verificar reunioes e
   compromissos do Outlook do usuario.

3. **Teams (em breve)**: Futuramente voce podera ver mensagens do Microsoft Teams.

4. **Academia Faiston**: Para perguntas sobre cursos, treinamentos, flashcards,
   mapas mentais ou aprendizado, voce deve delegar para o NEXO Academia.
   Use a tool `delegate_to_academy` para isso.

5. **Gestao de Estoque (SGA)**: Para perguntas sobre estoque, ativos, materiais,
   notas fiscais, entradas, saidas ou inventario, voce deve delegar para o NEXO
   Estoque. Use a tool `delegate_to_sga` para isso.

## Regras de Delegacao

- Perguntas sobre cursos, aulas, treinamentos, flashcards, mindmap, aprender,
  estudar -> delegate_to_academy
- Perguntas sobre estoque, ativo, material, entrada, saida, transferencia,
  inventario, NF-e, nota fiscal -> delegate_to_sga
- Perguntas sobre noticias, tecnologia, cloud, IA -> responder diretamente
- Perguntas gerais de assistencia -> responder diretamente

## Formato de Resposta

- Seja conciso e objetivo
- Use portugues brasileiro
- Use emojis com moderacao (1-2 por resposta)
- Para noticias, formate como lista com titulos e fontes
- Sempre seja util e proativo
"""


class NexoOrchestratorAgent:
    """
    Central NEXO orchestrator agent.

    Uses Google ADK with Gemini 3.0 Pro for intelligent query handling
    and A2A delegation.
    """

    def __init__(self):
        """Initialize orchestrator agent."""
        # Agent will be created lazily when needed
        self._agent = None
        self._runner = None

    def _get_agent(self):
        """Lazy-load the Google ADK agent."""
        if self._agent is None:
            from google import genai
            from google.adk import Agent, Runner
            from google.adk.tools import FunctionTool

            # Create tools for the agent
            tools = [
                FunctionTool(self._get_tech_news_tool),
                FunctionTool(self._delegate_to_academy_tool),
                FunctionTool(self._delegate_to_sga_tool),
            ]

            # Create agent with Gemini 3.0 Pro (MANDATORY)
            from agents.utils import MODEL_ID
            self._agent = Agent(
                model=MODEL_ID,
                name="nexo_portal",
                instruction=NEXO_ORCHESTRATOR_INSTRUCTION,
                tools=tools,
            )

            self._runner = Runner(
                agent=self._agent,
                app_name="faiston_portal"
            )

        return self._agent, self._runner

    async def chat(
        self,
        question: str,
        user_id: str,
        session_id: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        Handle a chat message from the user.

        Args:
            question: User's question or message
            user_id: User identifier
            session_id: Session identifier for context
            conversation_history: Optional previous messages

        Returns:
            Agent response
        """
        from agents.utils import classify_query_domain

        # First, classify the query domain
        domain = classify_query_domain(question)

        # For academy/inventory queries, delegate immediately
        if domain == "academy":
            return await self._delegate_to_academy(question, user_id, session_id)
        elif domain == "inventory":
            return await self._delegate_to_sga(question, user_id, session_id)

        # For portal queries, use the agent
        try:
            agent, runner = self._get_agent()

            # Build context with conversation history
            context = ""
            if conversation_history:
                context = "\n".join([
                    f"{msg['role']}: {msg['content']}"
                    for msg in conversation_history[-5:]  # Last 5 messages
                ])

            # Run the agent
            result = await runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=question,
                context=context if context else None
            )

            return {
                "success": True,
                "response": result.content if hasattr(result, 'content') else str(result),
                "domain": domain,
                "delegated": False
            }

        except Exception as e:
            # Fallback to simple response if agent fails
            return await self._fallback_response(question, str(e))

    async def get_daily_summary(
        self,
        user_id: str,
        include_news: bool = True,
        include_tips: bool = True
    ) -> Dict[str, Any]:
        """
        Generate a personalized daily summary.

        Args:
            user_id: User identifier
            include_news: Include news digest
            include_tips: Include productivity tips

        Returns:
            Daily summary with news, calendar (mock), and tips
        """
        summary = {
            "greeting": self._get_greeting(),
            "date": datetime.now(timezone.utc).strftime("%A, %d de %B de %Y"),
            "sections": []
        }

        # News digest
        if include_news:
            from agents.news_agent import get_news_digest
            news = await get_news_digest()
            if news.get("success"):
                summary["sections"].append({
                    "type": "news",
                    "title": "Principais Noticias de Tecnologia",
                    "data": news
                })

        # Calendar events (mock for now - MS Graph deferred)
        summary["sections"].append({
            "type": "calendar",
            "title": "Sua Agenda Hoje",
            "data": {
                "note": "Integracao com Outlook em breve",
                "events": []
            }
        })

        # Teams messages (mock for now - MS Graph deferred)
        summary["sections"].append({
            "type": "teams",
            "title": "Mensagens do Teams",
            "data": {
                "note": "Integracao com Teams em breve",
                "messages": []
            }
        })

        # Productivity tips
        if include_tips:
            summary["sections"].append({
                "type": "tips",
                "title": "Dica do Dia",
                "data": {
                    "tip": self._get_daily_tip()
                }
            })

        summary["generated_at"] = datetime.now(timezone.utc).isoformat()

        return {
            "success": True,
            "summary": summary
        }

    # =========================================================================
    # Tool Functions (for ADK Agent)
    # =========================================================================

    async def _get_tech_news_tool(
        self,
        categories: Optional[List[str]] = None,
        max_articles: int = 10
    ) -> Dict[str, Any]:
        """
        Tool: Get tech news from RSS feeds.

        Args:
            categories: News categories (cloud-aws, ai, brazil, etc.)
            max_articles: Maximum articles to return

        Returns:
            News articles
        """
        from agents.news_agent import get_tech_news
        return await get_tech_news(
            categories=categories,
            max_articles=max_articles
        )

    async def _delegate_to_academy_tool(
        self,
        question: str
    ) -> Dict[str, Any]:
        """
        Tool: Delegate learning questions to Academy agent.

        Args:
            question: User's learning-related question

        Returns:
            Academy agent response
        """
        return await self._delegate_to_academy(
            question=question,
            user_id="tool_invocation",
            session_id="tool_session"
        )

    async def _delegate_to_sga_tool(
        self,
        question: str
    ) -> Dict[str, Any]:
        """
        Tool: Delegate inventory questions to SGA agent.

        Args:
            question: User's inventory-related question

        Returns:
            SGA agent response
        """
        return await self._delegate_to_sga(
            question=question,
            user_id="tool_invocation",
            session_id="tool_session"
        )

    # =========================================================================
    # A2A Delegation Methods
    # =========================================================================

    async def _delegate_to_academy(
        self,
        question: str,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Delegate to Academy AgentCore."""
        try:
            from tools.a2a_client import delegate_to_academy
            result = await delegate_to_academy(
                question=question,
                user_id=user_id,
                session_id=session_id
            )
            return {
                "success": True,
                "response": result.get("response", result),
                "domain": "academy",
                "delegated": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Academy delegation failed: {str(e)}",
                "domain": "academy",
                "delegated": True
            }

    async def _delegate_to_sga(
        self,
        question: str,
        user_id: str,
        session_id: str
    ) -> Dict[str, Any]:
        """Delegate to SGA Inventory AgentCore."""
        try:
            from tools.a2a_client import delegate_to_sga
            result = await delegate_to_sga(
                question=question,
                user_id=user_id,
                session_id=session_id
            )
            return {
                "success": True,
                "response": result.get("response", result),
                "domain": "inventory",
                "delegated": True
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"SGA delegation failed: {str(e)}",
                "domain": "inventory",
                "delegated": True
            }

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _fallback_response(
        self,
        question: str,
        error: str
    ) -> Dict[str, Any]:
        """Generate a fallback response when agent fails."""
        return {
            "success": True,
            "response": (
                f"Desculpe, tive um problema tecnico ao processar sua pergunta. "
                f"Por favor, tente novamente ou reformule sua pergunta. "
                f"Se o problema persistir, entre em contato com o suporte."
            ),
            "domain": "portal",
            "delegated": False,
            "fallback": True,
            "error_details": error
        }

    def _get_greeting(self) -> str:
        """Get time-appropriate greeting."""
        hour = datetime.now().hour
        if 5 <= hour < 12:
            return "Bom dia"
        elif 12 <= hour < 18:
            return "Boa tarde"
        else:
            return "Boa noite"

    def _get_daily_tip(self) -> str:
        """Get a productivity tip."""
        tips = [
            "Comece o dia com as tarefas mais importantes.",
            "Faca pausas regulares para manter a produtividade.",
            "Use a tecnica Pomodoro: 25 minutos de foco, 5 de descanso.",
            "Mantenha sua area de trabalho organizada.",
            "Revise suas metas no inicio e fim do dia.",
            "Aproveite a Academia Faiston para aprender algo novo hoje!",
        ]
        import random
        return random.choice(tips)


# =============================================================================
# Module-level functions for direct invocation
# =============================================================================

async def nexo_chat(
    question: str,
    user_id: str,
    session_id: str,
    conversation_history: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Convenience function for chat invocation.

    Used by main.py handler.
    """
    agent = NexoOrchestratorAgent()
    return await agent.chat(
        question=question,
        user_id=user_id,
        session_id=session_id,
        conversation_history=conversation_history
    )


async def get_daily_summary(
    user_id: str,
    include_news: bool = True
) -> Dict[str, Any]:
    """
    Convenience function for daily summary.

    Used by main.py handler.
    """
    agent = NexoOrchestratorAgent()
    return await agent.get_daily_summary(
        user_id=user_id,
        include_news=include_news
    )
