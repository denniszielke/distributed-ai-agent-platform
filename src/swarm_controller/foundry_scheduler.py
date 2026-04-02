"""Foundry Agent Scheduler – creates and executes agents via Microsoft Foundry SDK."""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import MCPTool, PromptAgentDefinition
from azure.identity import DefaultAzureCredential
from openai import AzureOpenAI

from .models import Task, TaskStatus

logger = logging.getLogger(__name__)


class FoundryAgentScheduler:
    """Schedule and run agents via Microsoft Foundry."""

    def __init__(
        self,
        project_endpoint: Optional[str] = None,
        model_deployment: Optional[str] = None,
    ) -> None:
        self._endpoint = project_endpoint or os.environ.get("AZURE_AI_PROJECT_ENDPOINT", "")
        self._model = model_deployment or os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4o")
        self._credential = DefaultAzureCredential()

        if self._endpoint:
            self._project_client = AIProjectClient(
                endpoint=self._endpoint,
                credential=self._credential,
            )
            self._openai_client = self._project_client.inference.get_azure_openai_client()
        else:
            logger.warning("AZURE_AI_PROJECT_ENDPOINT not set – Foundry scheduler disabled")
            self._project_client = None  # type: ignore[assignment]
            self._openai_client = None  # type: ignore[assignment]

    def schedule_task(self, task: Task, mcp_tools: Optional[list[dict]] = None) -> str:
        """Create a Foundry agent for the given task and execute it.

        Returns the agent response text.
        """
        if self._project_client is None:
            logger.warning("Foundry not configured – returning empty result")
            return ""

        tools = []
        if mcp_tools:
            for mcp in mcp_tools:
                tools.append(
                    MCPTool(
                        server_url=mcp["url"],
                        server_label=mcp.get("label", mcp.get("name", "tool")),
                        require_approval="never",
                        allowed_tools=mcp.get("tools", []),
                    )
                )

        instructions = task.task_template or (
            f"You are a worker agent. Execute the following task:\n\n"
            f"Task: {task.name}\n"
            f"Description: {task.description or ''}\n"
            f"Payload: {task.payload or ''}\n\n"
            f"Return a concise result."
        )

        agent = self._project_client.agents.create_version(
            agent_name=f"swarm-worker-{task.id[:8]}",
            definition=PromptAgentDefinition(
                model=self._model,
                instructions=instructions,
                temperature=0,
                tools=tools if tools else None,
            ),
        )
        logger.info("Created Foundry agent %s (v%s) for task %s", agent.name, agent.version, task.id)

        try:
            response = self._openai_client.responses.create(
                model=self._model,
                input=task.payload or task.description or task.name,
                extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
            )
            result_text = response.output_text if hasattr(response, "output_text") else str(response)
            return result_text
        finally:
            self._project_client.agents.delete_version(
                agent_name=agent.name,
                agent_version=agent.version,
            )
            logger.info("Deleted Foundry agent %s", agent.name)

    def schedule_code_interpreter_task(
        self,
        task: Task,
        connection_id: Optional[str] = None,
    ) -> str:
        """Run a task using the code interpreter session pool."""
        if self._project_client is None:
            return ""

        conn_id = connection_id or os.environ.get("AZURE_AI_CONNECTION_ID", "")

        tools = [
            MCPTool(
                server_url="https://localhost",
                server_label="python_tool",
                require_approval="never",
                allowed_tools=["launchShell", "runPythonCodeInRemoteEnvironment"],
                project_connection_id=conn_id,
            ),
        ]

        instructions = (
            "You are a helpful agent that can use a Python code interpreter. "
            "Use the `python_tool` MCP server for calculations or code execution. "
            "ALWAYS call the `launchShell` tool first before calling "
            "`runPythonCodeInRemoteEnvironment`.\n\n"
            f"Task: {task.name}\n"
            f"Description: {task.description or ''}\n"
            f"Payload: {task.payload or ''}"
        )

        agent = self._project_client.agents.create_version(
            agent_name=f"swarm-codeinterp-{task.id[:8]}",
            definition=PromptAgentDefinition(
                model=self._model,
                instructions=instructions,
                temperature=0,
                tools=tools,
            ),
        )
        logger.info("Created code-interpreter agent %s for task %s", agent.name, task.id)

        try:
            response = self._openai_client.responses.create(
                model=self._model,
                input=task.payload or task.description or task.name,
                extra_body={"agent_reference": {"name": agent.name, "type": "agent_reference"}},
            )
            return response.output_text if hasattr(response, "output_text") else str(response)
        finally:
            self._project_client.agents.delete_version(
                agent_name=agent.name,
                agent_version=agent.version,
            )
