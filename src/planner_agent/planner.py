"""Planner Agent – decomposes objectives into executable task plans.

The planner has access to:
- The swarm registry (available agents, MCP servers, tools, skills)
- Historical execution plans via AI Search vector DB
- An LLM for reasoning about task decomposition
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv
from openai import AzureOpenAI

from src.swarm_controller.models import (
    AgentExecutionPlan,
    AgentPlan,
    Task,
    TaskType,
)

from .search_store import ExecutionPlanSearchStore

load_dotenv()

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are the Planner Agent for an agent swarm system. Your job is to take a high-level
objective and decompose it into a concrete execution plan consisting of tasks that can
be executed by specialized worker agents.

You have access to:
1. A registry of available agents, MCP servers (with tools), and skills.
2. Historical execution plans for similar objectives (provided as context).

For each task you create, specify:
- name: short descriptive name
- description: detailed instructions for the worker agent
- task_template: the full prompt/instructions the agent should follow
- task_type: one of "execute", "code_interpreter", "mcp_tool_call", "custom"
- target_agent_id: which agent should handle this (from registry), or null for auto-assign
- tags: relevant tags
- priority: 1-100 (higher = more important)
- payload: any input data the agent needs

Return your plan as a JSON object with:
{
  "description": "Overall plan description",
  "tasks": [ ... array of task objects ... ]
}
"""


class PlannerAgent:
    """Decomposes objectives into agent execution plans."""

    def __init__(
        self,
        search_store: Optional[ExecutionPlanSearchStore] = None,
        registry_url: Optional[str] = None,
    ) -> None:
        self._search_store = search_store or ExecutionPlanSearchStore()
        self._registry_url = registry_url or os.environ.get(
            "SWARM_REGISTRY_URL", "http://localhost:8002"
        )

        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        key = os.environ.get("AZURE_OPENAI_API_KEY", "")
        self._model = os.environ.get("AZURE_OPENAI_COMPLETION_DEPLOYMENT_NAME", "gpt-4o")

        if endpoint and key:
            self._openai = AzureOpenAI(
                azure_endpoint=endpoint,
                api_key=key,
                api_version=os.environ.get("AZURE_OPENAI_VERSION", "2024-02-01"),
            )
        else:
            logger.warning("OpenAI not configured for planner agent")
            self._openai = None  # type: ignore[assignment]

    def create_plan(
        self,
        objective_id: str,
        objective_text: str,
        registry_context: Optional[dict] = None,
    ) -> AgentPlan:
        """Create an execution plan for the given objective."""

        # 1. Look up similar historical plans
        similar_plans = self._search_store.search_similar_plans(objective_text, top=3)

        # 2. Build context for the LLM
        context_parts: list[str] = []
        if similar_plans:
            context_parts.append("## Similar Historical Plans\n")
            for sp in similar_plans:
                context_parts.append(
                    f"- Intent: {sp['intent']}\n  Description: {sp['description']}\n"
                    f"  Score: {sp.get('score', 'N/A')}\n"
                )

        if registry_context:
            context_parts.append("\n## Available Registry Resources\n")
            if registry_context.get("agents"):
                context_parts.append("### Agents\n")
                for a in registry_context["agents"]:
                    context_parts.append(f"- {a['name']}: {a['description']}\n")
            if registry_context.get("mcp_servers"):
                context_parts.append("### MCP Servers\n")
                for m in registry_context["mcp_servers"]:
                    context_parts.append(
                        f"- {m['name']}: {m['description']} (tools: {', '.join(m.get('tools', []))})\n"
                    )
            if registry_context.get("skills"):
                context_parts.append("### Skills\n")
                for s in registry_context["skills"]:
                    context_parts.append(f"- {s['name']}: {s['description']}\n")

        context_str = "".join(context_parts) if context_parts else "No historical context available."

        # 3. Call LLM
        if self._openai is None:
            # Fallback: single task plan
            task = Task(
                name=f"Execute: {objective_text[:50]}",
                description=objective_text,
                task_template=objective_text,
                task_type=TaskType.EXECUTE,
                created_by_agent_id="planner",
            )
            return AgentPlan(
                objective_id=objective_id,
                description=f"Single-task plan for: {objective_text[:80]}",
                tasks=[task],
            )

        user_message = (
            f"## Objective\n{objective_text}\n\n"
            f"## Context\n{context_str}\n\n"
            f"Create an execution plan."
        )

        response = self._openai.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        plan_json = json.loads(response.choices[0].message.content or "{}")

        tasks: list[Task] = []
        for t in plan_json.get("tasks", []):
            tasks.append(
                Task(
                    name=t.get("name", "unnamed"),
                    description=t.get("description", ""),
                    task_template=t.get("task_template", t.get("description", "")),
                    task_type=t.get("task_type", "execute"),
                    target_agent_id=t.get("target_agent_id"),
                    tags=t.get("tags", []),
                    priority=t.get("priority", 50),
                    payload=t.get("payload"),
                    created_by_agent_id="planner",
                )
            )

        plan = AgentPlan(
            objective_id=objective_id,
            description=plan_json.get("description", ""),
            tasks=tasks,
        )
        logger.info("Created plan %s with %d tasks", plan.id, len(tasks))
        return plan

    def record_execution(self, plan: AgentExecutionPlan) -> None:
        """Store a completed execution plan in AI Search for future reference."""
        self._search_store.upsert_plan(plan.model_dump())
