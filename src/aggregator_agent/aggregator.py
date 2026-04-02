"""Aggregator Agent – receives agent execution results and produces final output.

The aggregator watches for task results, correlates them with the original
objective and plan, and determines whether the objective has been achieved.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from openai import AzureOpenAI

from src.swarm_controller.database import SwarmDatabase
from src.swarm_controller.models import (
    AgentExecutionPlan,
    AgentPlan,
    Objective,
    Task,
    TaskStatus,
)

load_dotenv()

logger = logging.getLogger(__name__)

AGGREGATOR_SYSTEM_PROMPT = """\
You are the Aggregator Agent for an agent swarm system. Your job is to:
1. Review the original objective
2. Review the execution plan with all planned tasks
3. Review the individual task results
4. Determine if the objective has been fully achieved
5. Create a comprehensive summary of the results

Return a JSON object with:
{
  "summary": "Comprehensive summary of results",
  "objective_achieved": true/false,
  "confidence_score": 1-100,
  "details": "Detailed analysis",
  "recommendations": "Any follow-up actions needed"
}
"""


class AggregatorAgent:
    """Aggregates results from agent task executions."""

    def __init__(self, db: Optional[SwarmDatabase] = None) -> None:
        self.db = db or SwarmDatabase()

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
            logger.warning("OpenAI not configured for aggregator agent")
            self._openai = None  # type: ignore[assignment]

    def aggregate(self, objective_id: str) -> dict:
        """Aggregate results for an objective and produce a final summary."""
        obj = self.db.get_objective(objective_id)
        if obj is None:
            return {"error": f"Objective {objective_id} not found"}

        plan = self.db.get_plan_by_objective(objective_id)
        if plan is None:
            return {"error": f"No plan found for objective {objective_id}"}

        # Collect task results
        task_results: list[dict] = []
        all_completed = True
        for task_def in plan.tasks:
            task = self.db.get_task(task_def.id)
            if task is None:
                all_completed = False
                task_results.append({"name": task_def.name, "status": "not_found", "result": None})
                continue
            if task.status != TaskStatus.COMPLETED:
                all_completed = False
            task_results.append({
                "name": task.name,
                "description": task.description,
                "status": task.status.value,
                "result": task.result,
            })

        if self._openai is None:
            # Fallback without LLM
            return {
                "summary": f"Aggregated {len(task_results)} task results",
                "objective_achieved": all_completed,
                "confidence_score": 80 if all_completed else 30,
                "task_results": task_results,
            }

        user_message = (
            f"## Original Objective\n{obj.input_text}\n\n"
            f"## Execution Plan\n{plan.description}\n\n"
            f"## Task Results\n{json.dumps(task_results, indent=2)}\n\n"
            f"Analyze the results and create a summary."
        )

        response = self._openai.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": AGGREGATOR_SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            response_format={"type": "json_object"},
            temperature=0.2,
        )

        result = json.loads(response.choices[0].message.content or "{}")
        result["task_results"] = task_results
        return result

    def build_execution_plan_record(self, objective_id: str, aggregation_result: dict) -> AgentExecutionPlan:
        """Build an AgentExecutionPlan for storage in the vector DB."""
        obj = self.db.get_objective(objective_id)
        plan = self.db.get_plan_by_objective(objective_id)

        return AgentExecutionPlan(
            query=obj.input_text if obj else "",
            description=plan.description if plan else "",
            intent=aggregation_result.get("summary", ""),
            category=aggregation_result.get("category"),
            complexity=aggregation_result.get("complexity"),
            score=aggregation_result.get("confidence_score"),
        )
