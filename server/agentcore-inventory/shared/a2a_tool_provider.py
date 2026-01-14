# =============================================================================
# A2A Tool Provider - Dynamic Agent Discovery (Phase 7.1)
# =============================================================================
# Implements Strands A2A Protocol for dynamic agent discovery and tool creation.
#
# This module replaces hardcoded ACTION_TO_SPECIALIST mappings with dynamic
# discovery via AgentCard protocol.
#
# Pattern: A2AClientToolProvider (from Strands documentation)
# Reference: https://strandsagents.com/latest/documentation/docs/user-guide/concepts/multi-agent/agent-to-agent/
#
# Architecture:
# 1. Discover agents at startup via AgentCard (/.well-known/agent-card.json)
# 2. Extract skills from each AgentCard
# 3. Create dynamic tools for each discovered skill
# 4. Generate dynamic system prompt from discovered capabilities
# =============================================================================

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from strands import tool

logger = logging.getLogger(__name__)


@dataclass
class DiscoveredSkill:
    """
    Represents a skill discovered from an AgentCard.

    Maps to A2A Protocol skill definition:
    - name: Unique skill identifier (e.g., "analyze_file")
    - description: Human-readable description for LLM routing
    - agent_id: Which agent provides this skill
    - input_schema: JSON Schema for skill parameters
    """

    name: str
    description: str
    agent_id: str
    input_schema: Dict[str, Any] = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)


@dataclass
class DiscoveredAgent:
    """
    Represents an agent discovered via A2A Protocol.

    Contains the AgentCard information plus resolved URL.
    """

    agent_id: str
    name: str
    description: str
    url: str
    version: str = "1.0.0"
    skills: List[DiscoveredSkill] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)


class A2AToolProvider:
    """
    Dynamic A2A Tool Provider for Strands Orchestrator.

    This class implements the "A2AClientToolProvider" pattern from Strands:
    1. Discovers agents at startup via AgentCard
    2. Creates dynamic tools from discovered skills
    3. Generates system prompt from discovered capabilities

    Usage:
        provider = A2AToolProvider()
        await provider.discover_all_agents()

        # Use discovered tools with Strands Agent
        orchestrator = Agent(
            tools=provider.tools,
            system_prompt=provider.build_system_prompt(),
        )

    Benefits over hardcoded mappings:
    - Zero-touch updates: New agents auto-discovered
    - Self-documenting: System prompt reflects actual deployed skills
    - A2A Protocol compliant: Uses official AgentCard discovery
    - Decoupled: No code changes when specialist skills change
    """

    def __init__(self, a2a_client=None):
        """
        Initialize A2A Tool Provider.

        Args:
            a2a_client: Optional A2AClient instance. If None, creates new one.
        """
        self._a2a_client = a2a_client
        self._discovered_agents: Dict[str, DiscoveredAgent] = {}
        self._skill_to_agent: Dict[str, str] = {}
        self._tools: List[Callable] = []
        self._discovery_complete = False

    def _get_a2a_client(self):
        """Lazy load A2A client."""
        if self._a2a_client is None:
            from shared.a2a_client import A2AClient

            self._a2a_client = A2AClient(use_discovery=True)
        return self._a2a_client

    async def discover_all_agents(self) -> Dict[str, DiscoveredAgent]:
        """
        Discover all specialist agents via A2A Protocol.

        Fetches AgentCard from each known agent and extracts skills.

        Returns:
            Dict mapping agent_id to DiscoveredAgent
        """
        if self._discovery_complete:
            return self._discovered_agents

        # Import RUNTIME_IDS to know which agents to discover
        from shared.a2a_client import RUNTIME_IDS

        client = self._get_a2a_client()

        logger.info(f"[A2AToolProvider] Discovering {len(RUNTIME_IDS)} specialist agents...")

        # Discover agents in parallel
        discovery_tasks = []
        for agent_id in RUNTIME_IDS:
            discovery_tasks.append(self._discover_agent(client, agent_id))

        results = await asyncio.gather(*discovery_tasks, return_exceptions=True)

        # Process results
        discovered_count = 0
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"[A2AToolProvider] Discovery error: {result}")
            elif result:
                self._discovered_agents[result.agent_id] = result
                discovered_count += 1

                # Register skills
                for skill in result.skills:
                    self._skill_to_agent[skill.name] = result.agent_id

        logger.info(
            f"[A2AToolProvider] Discovered {discovered_count} agents, "
            f"{len(self._skill_to_agent)} total skills"
        )

        self._discovery_complete = True
        return self._discovered_agents

    async def _discover_agent(self, client, agent_id: str) -> Optional[DiscoveredAgent]:
        """
        Discover a single agent via AgentCard.

        Args:
            client: A2AClient instance
            agent_id: Agent identifier (e.g., "nexo_import")

        Returns:
            DiscoveredAgent or None if discovery failed
        """
        try:
            # Use existing discover_agent method from A2AClient
            card = await client.discover_agent(agent_id)

            if not card:
                logger.warning(f"[A2AToolProvider] No AgentCard for {agent_id}")
                return self._create_fallback_agent(agent_id)

            # Extract skills from AgentCard
            skills = []
            for skill_data in card.skills:
                skill = DiscoveredSkill(
                    name=skill_data.get("name", "unknown"),
                    description=skill_data.get("description", ""),
                    agent_id=agent_id,
                    input_schema=skill_data.get("inputSchema", {}),
                    examples=skill_data.get("examples", []),
                )
                skills.append(skill)

            return DiscoveredAgent(
                agent_id=agent_id,
                name=card.name,
                description=card.description,
                url=card.url,
                version=card.version,
                skills=skills,
                capabilities=card.capabilities,
            )

        except Exception as e:
            logger.warning(f"[A2AToolProvider] Failed to discover {agent_id}: {e}")
            return self._create_fallback_agent(agent_id)

    def _create_fallback_agent(self, agent_id: str) -> DiscoveredAgent:
        """
        Create fallback agent info when discovery fails.

        Uses hardcoded knowledge to provide basic routing capability.
        """
        # Fallback descriptions based on agent naming convention
        fallback_descriptions = {
            "estoque_control": "Inventory control: reservations, expeditions, transfers, balance queries",
            "intake": "Document intake: NF (Nota Fiscal) PDF/XML processing",
            "nexo_import": "Smart import: AI-powered file analysis and data import",
            "learning": "Memory: Prior knowledge retrieval and pattern learning",
            "validation": "Validation: Data and schema validation",
            "reconciliacao": "Reconciliation: Inventory counting and divergence analysis",
            "compliance": "Compliance: Policy validation and approval workflows",
            "carrier": "Carrier: Shipping quotes and carrier management",
            "expedition": "Expedition: Outbound logistics and SAP export",
            "reverse": "Reverse: Return processing and condition evaluation",
            "observation": "Observation: Audit logging and analysis",
            "schema_evolution": "Schema: Column type inference and schema changes",
            "equipment_research": "Research: Equipment documentation lookup",
            "data_import": "Import: Generic data import operations",
        }

        return DiscoveredAgent(
            agent_id=agent_id,
            name=f"faiston_sga_{agent_id}",
            description=fallback_descriptions.get(agent_id, f"Specialist agent: {agent_id}"),
            url="",  # Will use RUNTIME_IDS mapping
            version="1.0.0",
            skills=[],  # No discovered skills - rely on fallback routing
            capabilities=[],
        )

    def build_system_prompt(self) -> str:
        """
        Generate dynamic system prompt from discovered agents.

        This replaces the hardcoded SYSTEM_PROMPT in main.py with
        a dynamically generated version based on actual deployed capabilities.

        Returns:
            System prompt string for the orchestrator
        """
        if not self._discovered_agents:
            logger.warning("[A2AToolProvider] No agents discovered - using default prompt")
            return self._get_default_system_prompt()

        # Build agent table
        agents_table = "| Agent ID | Capabilities | Skills |\n|----------|-------------|--------|\n"

        for agent_id, agent in sorted(self._discovered_agents.items()):
            skills_list = ", ".join(s.name for s in agent.skills[:5])  # Limit to 5 skills
            if len(agent.skills) > 5:
                skills_list += f" (+{len(agent.skills) - 5} more)"

            agents_table += f"| {agent_id} | {agent.description[:50]} | {skills_list} |\n"

        # Build skill routing rules
        routing_rules = self._build_routing_rules()

        return f"""
## 🎯 You are Faiston Inventory Management Orchestrator

You are the central intelligence for the SGA (Sistema de Gestão de Ativos).
Your role is to:
1. UNDERSTAND the user's intent from their message
2. IDENTIFY which specialist agent should handle the request
3. INVOKE the appropriate specialist via the invoke_specialist tool
4. RETURN the specialist's response to the user

## 📋 Discovered Specialist Agents (Dynamic)

The following agents were discovered via A2A Protocol at startup:

{agents_table}

## 🔄 Routing Rules

{routing_rules}

## ⚠️ Response Format

Always return the specialist's response as-is in JSON format.
The response should include:
- success: boolean indicating operation result
- specialist_agent: which agent handled the request
- response: the actual data/result from the specialist
"""

    def _build_routing_rules(self) -> str:
        """Build routing rules from discovered skills."""
        rules = []

        # Group skills by agent
        for agent_id, agent in self._discovered_agents.items():
            if agent.skills:
                skill_names = [s.name for s in agent.skills]
                rules.append(f"- **{agent_id}**: {', '.join(skill_names)}")

        if not rules:
            return "Use agent_id based on the request type. Consult the agent table above."

        return "\n".join(rules)

    def _get_default_system_prompt(self) -> str:
        """Return fallback system prompt if discovery fails."""
        return """
## 🎯 You are Faiston Inventory Management Orchestrator

You route requests to specialist agents. Available agents:
- estoque_control: Inventory movements
- intake: Document processing
- nexo_import: Smart file import
- learning: Memory and patterns
- validation: Data validation
- reconciliacao: Inventory counting
- compliance: Approvals
- carrier: Shipping
- expedition: Outbound logistics
- reverse: Returns
- observation: Audit
- schema_evolution: Schema changes
- equipment_research: Equipment lookup
- data_import: Generic import

Use invoke_specialist tool with appropriate agent_id.
"""

    def create_invoke_tool(self) -> Callable:
        """
        Create the invoke_specialist tool with dynamic routing.

        Returns:
            Tool function that can be used with Strands Agent
        """
        provider = self  # Capture reference for closure

        @tool
        async def invoke_specialist(
            agent_id: str,
            action: str,
            payload: dict,
            session_id: str = None,
        ) -> dict:
            """
            Invoke a specialist agent via A2A Protocol (JSON-RPC 2.0).

            This tool routes requests to discovered specialist agents.
            Agent capabilities were discovered dynamically via AgentCard.

            Args:
                agent_id: Target specialist agent (discovered at startup)
                action: Action to perform on the specialist
                payload: Action-specific parameters
                session_id: Session ID for context continuity

            Returns:
                dict with success status and specialist response
            """
            import json

            client = provider._get_a2a_client()

            logger.info(f"[A2AToolProvider] Routing to {agent_id}, action={action}")

            # Build A2A payload
            a2a_payload = {"action": action, **payload}

            # Invoke specialist via A2A Protocol
            result = await client.invoke_agent(
                agent_id=agent_id,
                payload=a2a_payload,
                session_id=session_id or "default-session",
            )

            if not result.success:
                return {
                    "success": False,
                    "specialist_agent": agent_id,
                    "error": result.error or "A2A invocation failed",
                }

            # Parse response
            try:
                response_data = json.loads(result.response) if result.response else {}

                # Handle various response formats
                if "result" in response_data:
                    return {
                        "success": True,
                        "specialist_agent": agent_id,
                        "response": response_data["result"],
                    }

                if response_data.get("success") is not None:
                    return {
                        "success": response_data.get("success", True),
                        "specialist_agent": agent_id,
                        "response": response_data,
                    }

                if response_data:
                    return {
                        "success": True,
                        "specialist_agent": agent_id,
                        "response": response_data,
                    }

                return {
                    "success": False,
                    "specialist_agent": agent_id,
                    "error": "Empty response from specialist agent",
                }

            except json.JSONDecodeError:
                return {
                    "success": True,
                    "specialist_agent": agent_id,
                    "response": {"message": result.response},
                }

        return invoke_specialist

    def build_action_mapping(self) -> Dict[str, tuple]:
        """
        Build backward-compatible action mapping from discovered skills.

        This generates the ACTION_TO_SPECIALIST mapping dynamically
        based on discovered AgentCard skills.

        Returns:
            Dict mapping action names to (agent_id, action) tuples
        """
        mapping = {}

        for agent_id, agent in self._discovered_agents.items():
            for skill in agent.skills:
                # Map skill name directly
                mapping[skill.name] = (agent_id, skill.name)

                # Also create prefixed versions for backward compatibility
                # e.g., "nexo_analyze_file" -> ("nexo_import", "analyze_file")
                prefixed_name = f"{agent_id}_{skill.name}"
                mapping[prefixed_name] = (agent_id, skill.name)

        logger.info(f"[A2AToolProvider] Built action mapping with {len(mapping)} entries")
        return mapping

    @property
    def tools(self) -> List[Callable]:
        """
        Return tools for use with Strands Agent.

        Currently returns a single invoke_specialist tool.
        Future: Could return individual tools per skill.
        """
        if not self._tools:
            self._tools = [self.create_invoke_tool()]
        return self._tools

    @property
    def discovered_agents(self) -> Dict[str, DiscoveredAgent]:
        """Return discovered agents."""
        return self._discovered_agents

    @property
    def skill_to_agent(self) -> Dict[str, str]:
        """Return skill-to-agent mapping."""
        return self._skill_to_agent


# =============================================================================
# Convenience Functions
# =============================================================================


async def create_tool_provider() -> A2AToolProvider:
    """
    Factory function to create and initialize A2AToolProvider.

    Usage:
        provider = await create_tool_provider()
        orchestrator = Agent(
            tools=provider.tools,
            system_prompt=provider.build_system_prompt(),
        )
    """
    provider = A2AToolProvider()
    await provider.discover_all_agents()
    return provider


def create_tool_provider_sync() -> A2AToolProvider:
    """
    Synchronous factory function for A2AToolProvider.

    Runs async discovery in event loop.
    """
    provider = A2AToolProvider()
    asyncio.run(provider.discover_all_agents())
    return provider
