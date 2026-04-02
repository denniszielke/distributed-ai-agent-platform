"""Swarm Registry – central registry for MCP servers, tools, skills, and agents."""

from __future__ import annotations

import json
import logging
from typing import Optional

from src.swarm_controller.models import AgentEntry, MCPServerEntry, SkillEntry

logger = logging.getLogger(__name__)


class SwarmRegistry:
    """In-memory registry of available MCP servers, agents, and skills."""

    def __init__(self) -> None:
        self._mcp_servers: dict[str, MCPServerEntry] = {}
        self._agents: dict[str, AgentEntry] = {}
        self._skills: dict[str, SkillEntry] = {}

    # ------------------------------------------------------------------
    # MCP Servers
    # ------------------------------------------------------------------

    def register_mcp_server(self, server: MCPServerEntry) -> None:
        self._mcp_servers[server.id] = server
        logger.info("Registered MCP server: %s (%s)", server.name, server.id)

    def unregister_mcp_server(self, server_id: str) -> bool:
        return self._mcp_servers.pop(server_id, None) is not None

    def get_mcp_server(self, server_id: str) -> Optional[MCPServerEntry]:
        return self._mcp_servers.get(server_id)

    def list_mcp_servers(self) -> list[MCPServerEntry]:
        return list(self._mcp_servers.values())

    def find_mcp_servers_by_tool(self, tool_name: str) -> list[MCPServerEntry]:
        return [s for s in self._mcp_servers.values() if tool_name in s.tools and s.enabled]

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------

    def register_agent(self, agent: AgentEntry) -> None:
        self._agents[agent.id] = agent
        logger.info("Registered agent: %s (%s)", agent.name, agent.id)

    def unregister_agent(self, agent_id: str) -> bool:
        return self._agents.pop(agent_id, None) is not None

    def get_agent(self, agent_id: str) -> Optional[AgentEntry]:
        return self._agents.get(agent_id)

    def list_agents(self) -> list[AgentEntry]:
        return list(self._agents.values())

    def find_agents_by_capability(self, capability: str) -> list[AgentEntry]:
        return [
            a
            for a in self._agents.values()
            if capability.lower() in [c.lower() for c in a.capabilities] and a.enabled
        ]

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------

    def register_skill(self, skill: SkillEntry) -> None:
        self._skills[skill.id] = skill
        logger.info("Registered skill: %s (%s)", skill.name, skill.id)

    def unregister_skill(self, skill_id: str) -> bool:
        return self._skills.pop(skill_id, None) is not None

    def get_skill(self, skill_id: str) -> Optional[SkillEntry]:
        return self._skills.get(skill_id)

    def list_skills(self) -> list[SkillEntry]:
        return list(self._skills.values())

    # ------------------------------------------------------------------
    # Full context (for planner)
    # ------------------------------------------------------------------

    def get_registry_context(self) -> dict:
        """Return full registry context for the planner agent."""
        return {
            "agents": [a.model_dump() for a in self._agents.values() if a.enabled],
            "mcp_servers": [s.model_dump() for s in self._mcp_servers.values() if s.enabled],
            "skills": [s.model_dump() for s in self._skills.values()],
        }
