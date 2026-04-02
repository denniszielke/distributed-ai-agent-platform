"""FastAPI application for the Swarm Registry."""

from __future__ import annotations

import logging
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException

from src.swarm_controller.models import AgentEntry, MCPServerEntry, SkillEntry

from .registry import SwarmRegistry

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

registry = SwarmRegistry()
app = FastAPI(title="Swarm Registry", version="0.1.0")


# ------------------------------------------------------------------
# MCP Servers
# ------------------------------------------------------------------


@app.post("/mcp-servers")
async def register_mcp_server(server: MCPServerEntry) -> dict:
    registry.register_mcp_server(server)
    return {"status": "registered", "id": server.id}


@app.get("/mcp-servers")
async def list_mcp_servers() -> list[dict]:
    return [s.model_dump() for s in registry.list_mcp_servers()]


@app.get("/mcp-servers/{server_id}")
async def get_mcp_server(server_id: str) -> dict:
    server = registry.get_mcp_server(server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="MCP server not found")
    return server.model_dump()


@app.delete("/mcp-servers/{server_id}")
async def unregister_mcp_server(server_id: str) -> dict:
    if registry.unregister_mcp_server(server_id):
        return {"status": "unregistered"}
    raise HTTPException(status_code=404, detail="MCP server not found")


# ------------------------------------------------------------------
# Agents
# ------------------------------------------------------------------


@app.post("/agents")
async def register_agent(agent: AgentEntry) -> dict:
    registry.register_agent(agent)
    return {"status": "registered", "id": agent.id}


@app.get("/agents")
async def list_agents() -> list[dict]:
    return [a.model_dump() for a in registry.list_agents()]


@app.get("/agents/{agent_id}")
async def get_agent(agent_id: str) -> dict:
    agent = registry.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent.model_dump()


@app.delete("/agents/{agent_id}")
async def unregister_agent(agent_id: str) -> dict:
    if registry.unregister_agent(agent_id):
        return {"status": "unregistered"}
    raise HTTPException(status_code=404, detail="Agent not found")


# ------------------------------------------------------------------
# Skills
# ------------------------------------------------------------------


@app.post("/skills")
async def register_skill(skill: SkillEntry) -> dict:
    registry.register_skill(skill)
    return {"status": "registered", "id": skill.id}


@app.get("/skills")
async def list_skills() -> list[dict]:
    return [s.model_dump() for s in registry.list_skills()]


@app.get("/skills/{skill_id}")
async def get_skill(skill_id: str) -> dict:
    skill = registry.get_skill(skill_id)
    if skill is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill.model_dump()


@app.delete("/skills/{skill_id}")
async def unregister_skill(skill_id: str) -> dict:
    if registry.unregister_skill(skill_id):
        return {"status": "unregistered"}
    raise HTTPException(status_code=404, detail="Skill not found")


# ------------------------------------------------------------------
# Context (for planner)
# ------------------------------------------------------------------


@app.get("/context")
async def get_context() -> dict:
    """Full registry context for the planner agent."""
    return registry.get_registry_context()


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "swarm_registry"}


if __name__ == "__main__":
    uvicorn.run("src.swarm_registry.app:app", host="0.0.0.0", port=8002, reload=True)
