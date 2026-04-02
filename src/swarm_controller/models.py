"""Shared data models for the Agent Swarm Platform."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TaskStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    PLAN = "plan"
    EXECUTE = "execute"
    AGGREGATE = "aggregate"
    CODE_INTERPRETER = "code_interpreter"
    MCP_TOOL_CALL = "mcp_tool_call"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Task model – central unit of work inside the swarm
# ---------------------------------------------------------------------------

class Task(BaseModel):
    """Represents a single unit of work in the agent swarm."""

    id: str = Field(default_factory=_new_id)
    name: str
    payload: Optional[str] = None
    description: Optional[str] = None
    task_template: str = ""
    task_type: TaskType = TaskType.EXECUTE
    tags: list[str] = Field(default_factory=list)
    priority: int = 50
    target_agent_id: Optional[str] = None
    enabled: bool = True
    last_run_at: Optional[str] = None
    result: Optional[str] = None
    status: TaskStatus = TaskStatus.PENDING
    created_by_agent_id: Optional[str] = None
    timezone: str = "UTC"
    created_at: str = Field(default_factory=_utcnow)
    last_updated_at: str = Field(default_factory=_utcnow)


# ---------------------------------------------------------------------------
# Agent Execution Plan – stored in AI Search for vector retrieval
# ---------------------------------------------------------------------------

class AgentExecutionPlan(BaseModel):
    """Represents an agent execution plan with metadata for vector search."""

    id: str = Field(default_factory=_new_id)
    query: str  # input objective
    description: str  # execution plan with all involved agents and tasks
    intent: str  # detected intent of the objective
    category: Optional[str] = None
    complexity: Optional[str] = None
    score: Optional[int] = None  # 1-100 success score


# ---------------------------------------------------------------------------
# Objective – top-level request that enters the swarm
# ---------------------------------------------------------------------------

class Objective(BaseModel):
    """A high-level objective submitted to the swarm controller."""

    id: str = Field(default_factory=_new_id)
    input_text: str
    status: TaskStatus = TaskStatus.PENDING
    plan_id: Optional[str] = None
    result: Optional[str] = None
    created_at: str = Field(default_factory=_utcnow)
    last_updated_at: str = Field(default_factory=_utcnow)


# ---------------------------------------------------------------------------
# Agent Plan – the decomposed plan produced by the planner agent
# ---------------------------------------------------------------------------

class AgentPlan(BaseModel):
    """Plan produced by the planner agent for an objective."""

    id: str = Field(default_factory=_new_id)
    objective_id: str
    description: str
    tasks: list[Task] = Field(default_factory=list)
    created_at: str = Field(default_factory=_utcnow)


# ---------------------------------------------------------------------------
# Registry models
# ---------------------------------------------------------------------------

class MCPServerEntry(BaseModel):
    """An MCP server registered in the swarm registry."""

    id: str = Field(default_factory=_new_id)
    name: str
    url: str
    description: str
    tools: list[str] = Field(default_factory=list)
    enabled: bool = True


class AgentEntry(BaseModel):
    """An agent registered in the swarm registry."""

    id: str = Field(default_factory=_new_id)
    name: str
    description: str
    capabilities: list[str] = Field(default_factory=list)
    mcp_servers: list[str] = Field(default_factory=list)
    enabled: bool = True


class SkillEntry(BaseModel):
    """A skill registered in the swarm registry."""

    id: str = Field(default_factory=_new_id)
    name: str
    description: str
    skill_file: str  # path to the skill markdown
    tags: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Communication messages (Azure Storage Queue payloads)
# ---------------------------------------------------------------------------

class SwarmMessage(BaseModel):
    """Message exchanged via Azure Storage Queues."""

    id: str = Field(default_factory=_new_id)
    source_agent_id: str
    target_agent_id: str
    objective_id: str
    task_id: Optional[str] = None
    message_type: str  # "task_result", "task_request", "status_update"
    payload: str
    created_at: str = Field(default_factory=_utcnow)
