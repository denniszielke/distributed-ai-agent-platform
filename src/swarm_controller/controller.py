"""Agent Swarm Controller – the brain of the system.

Orchestrates agent interactions, manages task distribution, and coordinates
the planner and aggregator agents.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone

from dotenv import load_dotenv

from .communication import (
    QUEUE_AGGREGATOR_INBOX,
    QUEUE_CONTROLLER_INBOX,
    CommunicationLayer,
)
from .database import SwarmDatabase
from .foundry_scheduler import FoundryAgentScheduler
from .models import (
    AgentPlan,
    Objective,
    SwarmMessage,
    Task,
    TaskStatus,
    TaskType,
)

load_dotenv()

logger = logging.getLogger(__name__)


class SwarmController:
    """Central orchestrator for the agent swarm."""

    def __init__(
        self,
        db: SwarmDatabase | None = None,
        comm: CommunicationLayer | None = None,
        scheduler: FoundryAgentScheduler | None = None,
    ) -> None:
        self.db = db or SwarmDatabase()
        self.comm = comm or CommunicationLayer()
        self.scheduler = scheduler or FoundryAgentScheduler()

        # Ensure Azure Storage resources exist
        self.comm.ensure_queues()
        self.comm.ensure_blob_container()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit_objective(self, input_text: str) -> Objective:
        """Accept a new objective and kick off planning."""
        obj = Objective(input_text=input_text)
        self.db.insert_objective(obj)
        logger.info("New objective %s: %s", obj.id, input_text[:80])

        # Delegate to planner (step 1 → 2)
        self._request_plan(obj)
        return obj

    def receive_plan(self, objective_id: str, plan: AgentPlan) -> None:
        """Called by the planner agent once a plan is ready (step 2 → 3)."""
        self.db.insert_plan(plan)
        now = datetime.now(timezone.utc).isoformat()
        self.db.update_objective(
            objective_id,
            plan_id=plan.id,
            status=TaskStatus.SCHEDULED,
            last_updated_at=now,
        )

        # Persist individual tasks and schedule them
        for task in plan.tasks:
            self.db.insert_task(task)

        self._schedule_tasks(plan)

    def receive_task_result(self, task_id: str, result: str) -> None:
        """Record a completed task result and forward to aggregator."""
        now = datetime.now(timezone.utc).isoformat()
        self.db.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            result=result,
            last_run_at=now,
            last_updated_at=now,
        )
        task = self.db.get_task(task_id)
        if task is None:
            return

        # Send result to aggregator queue (step 3 → 4)
        msg = SwarmMessage(
            source_agent_id=task.target_agent_id or "controller",
            target_agent_id="aggregator",
            objective_id="",  # will be resolved by aggregator via task
            task_id=task_id,
            message_type="task_result",
            payload=result,
        )
        self.comm.send_to_aggregator(msg)

    def receive_aggregation_result(self, objective_id: str, result: str) -> None:
        """Called by aggregator when the final result is ready (step 4 done)."""
        now = datetime.now(timezone.utc).isoformat()
        self.db.update_objective(
            objective_id,
            status=TaskStatus.COMPLETED,
            result=result,
            last_updated_at=now,
        )
        logger.info("Objective %s completed", objective_id)

    def get_status(self, objective_id: str) -> dict:
        """Return current status for an objective."""
        obj = self.db.get_objective(objective_id)
        if obj is None:
            return {"error": "not found"}
        plan = self.db.get_plan_by_objective(objective_id)
        tasks = [self.db.get_task(t.id) for t in (plan.tasks if plan else [])]
        return {
            "objective": obj.model_dump(),
            "plan": plan.model_dump() if plan else None,
            "tasks": [t.model_dump() for t in tasks if t],
        }

    # ------------------------------------------------------------------
    # Polling loop
    # ------------------------------------------------------------------

    async def poll_loop(self, interval: float = 5.0) -> None:
        """Poll the controller inbox for messages."""
        logger.info("Starting controller poll loop (interval=%.1fs)", interval)
        while True:
            try:
                messages = self.comm.receive_messages(QUEUE_CONTROLLER_INBOX)
                for msg in messages:
                    self._handle_message(msg)
            except Exception:
                logger.exception("Error in poll loop")
            await asyncio.sleep(interval)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _request_plan(self, obj: Objective) -> None:
        """Send objective to the planner agent via queue."""
        msg = SwarmMessage(
            source_agent_id="controller",
            target_agent_id="planner",
            objective_id=obj.id,
            message_type="task_request",
            payload=obj.input_text,
        )
        self.comm.send_message("swarm-controller-inbox", msg)
        logger.info("Requested plan for objective %s", obj.id)

    def _schedule_tasks(self, plan: AgentPlan) -> None:
        """Schedule each task via the Foundry agent scheduler."""
        for task in plan.tasks:
            now = datetime.now(timezone.utc).isoformat()
            self.db.update_task(task.id, status=TaskStatus.SCHEDULED, last_updated_at=now)

            try:
                if task.task_type == TaskType.CODE_INTERPRETER:
                    result = self.scheduler.schedule_code_interpreter_task(task)
                else:
                    result = self.scheduler.schedule_task(task)

                self.receive_task_result(task.id, result)
            except Exception:
                logger.exception("Failed to schedule task %s", task.id)
                self.db.update_task(
                    task.id,
                    status=TaskStatus.FAILED,
                    result="Scheduling error",
                    last_updated_at=now,
                )

    def _handle_message(self, msg: SwarmMessage) -> None:
        """Route an incoming message."""
        if msg.message_type == "task_result":
            if msg.task_id:
                self.receive_task_result(msg.task_id, msg.payload)
        elif msg.message_type == "plan_ready":
            plan_data = json.loads(msg.payload)
            plan = AgentPlan(**plan_data)
            self.receive_plan(msg.objective_id, plan)
        elif msg.message_type == "aggregation_complete":
            self.receive_aggregation_result(msg.objective_id, msg.payload)
        else:
            logger.warning("Unknown message type: %s", msg.message_type)
