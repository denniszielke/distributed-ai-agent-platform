"""MCP Server for Swarm Controller operations via FastMCP.

Exposes the swarm controller functionality as MCP tools and resources
that can be consumed by any agent runtime.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

import uvicorn
from dotenv import load_dotenv
from fastmcp import FastMCP

from src.swarm_controller.controller import SwarmController
from src.swarm_controller.database import SwarmDatabase
from src.swarm_controller.models import (
    AgentPlan,
    Objective,
    Task,
    TaskStatus,
    TaskType,
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SwarmDatabase(os.environ.get("SWARM_DB_PATH", ":memory:"))
controller = SwarmController(db=db)

mcp = FastMCP("AgentSwarmController")


# ---------------------------------------------------------------------------
# MCP Resources
# ---------------------------------------------------------------------------


@mcp.resource("config://version")
def get_version() -> dict:
    """Get the swarm controller version."""
    return {"version": "0.1.0", "features": ["planning", "execution", "aggregation"]}


@mcp.resource("resource://objectives/list")
async def list_objectives() -> list[dict]:
    """List all objectives in the swarm."""
    return [o.model_dump() for o in db.list_objectives()]


@mcp.resource("resource://objectives/{objective_id}/status")
async def get_objective_status(objective_id: str) -> dict:
    """Get the status of a specific objective."""
    return controller.get_status(objective_id)


@mcp.resource("resource://tasks/list")
async def list_tasks() -> list[dict]:
    """List all tasks in the swarm."""
    return [t.model_dump() for t in db.list_tasks()]


@mcp.resource("resource://tasks/{task_id}/details")
async def get_task_details(task_id: str) -> dict:
    """Get details of a specific task."""
    task = db.get_task(task_id)
    if task is None:
        return {"error": "Task not found"}
    return task.model_dump()


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def submit_objective(input_text: str) -> dict:
    """Submit a new objective to the agent swarm for planning and execution.

    Args:
        input_text: The high-level objective to achieve

    Returns:
        The created objective with its ID and initial status
    """
    logger.info("Tool called: submit_objective | input: %s", input_text[:80])
    obj = controller.submit_objective(input_text)
    return {"objective_id": obj.id, "status": obj.status.value}


@mcp.tool()
async def get_objective_result(objective_id: str) -> dict:
    """Get the current status and result of an objective.

    Args:
        objective_id: The ID of the objective to check

    Returns:
        Full status including plan, tasks and results
    """
    return controller.get_status(objective_id)


@mcp.tool()
async def create_task(
    name: str,
    description: str,
    task_type: str = "execute",
    payload: str = "",
    priority: int = 50,
    target_agent_id: str = "",
) -> dict:
    """Create and schedule a new task in the swarm.

    Args:
        name: Short descriptive name for the task
        description: Detailed task description
        task_type: Type of task (execute, code_interpreter, mcp_tool_call, custom)
        payload: Input data for the task
        priority: Priority 1-100 (higher = more important)
        target_agent_id: Specific agent to assign to

    Returns:
        The created task with its ID
    """
    task = Task(
        name=name,
        description=description,
        task_template=description,
        task_type=task_type,
        payload=payload if payload else None,
        priority=priority,
        target_agent_id=target_agent_id if target_agent_id else None,
        created_by_agent_id="mcp_client",
    )
    db.insert_task(task)
    logger.info("Tool called: create_task | name=%s, id=%s", name, task.id)
    return task.model_dump()


@mcp.tool()
async def list_pending_tasks() -> list[dict]:
    """List all tasks that are pending execution.

    Returns:
        List of pending tasks
    """
    tasks = db.list_tasks_by_status(TaskStatus.PENDING)
    return [t.model_dump() for t in tasks]


@mcp.tool()
async def update_task_result(task_id: str, result: str) -> dict:
    """Update a task with its execution result.

    Args:
        task_id: The ID of the task to update
        result: The result of the task execution

    Returns:
        Updated task status
    """
    controller.receive_task_result(task_id, result)
    task = db.get_task(task_id)
    if task is None:
        return {"error": "Task not found"}
    return {"task_id": task_id, "status": task.status.value}


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------


async def check_mcp_server(server: FastMCP) -> None:
    """Print available tools and resources on startup."""
    tools = await server.get_tools()
    resources = await server.get_resources()
    templates = await server.get_resource_templates()
    print(f"{len(tools)} Tool(s): {', '.join([t.name for t in tools.values()])}")
    print(f"{len(resources)} Resource(s): {', '.join([r.name for r in resources.values()])}")
    print(f"{len(templates)} Resource Template(s): {', '.join([t.name for t in templates.values()])}")


streamable_http_app = mcp.http_app(path="/mcp", transport="streamable-http")

if __name__ == "__main__":
    try:
        asyncio.run(check_mcp_server(mcp))
        uvicorn.run(streamable_http_app, host="0.0.0.0", port=8004)
    except KeyboardInterrupt:
        print("\nShutting down MCP server...")
