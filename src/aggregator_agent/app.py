"""FastAPI application for the Aggregator Agent."""

from __future__ import annotations

import asyncio
import logging
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.swarm_controller.communication import (
    QUEUE_AGGREGATOR_INBOX,
    CommunicationLayer,
)
from src.swarm_controller.database import SwarmDatabase
from src.swarm_controller.models import SwarmMessage, TaskStatus

from .aggregator import AggregatorAgent

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SwarmDatabase(os.environ.get("SWARM_DB_PATH", ":memory:"))
comm = CommunicationLayer()
aggregator = AggregatorAgent(db=db)

app = FastAPI(title="Aggregator Agent", version="0.1.0")


class AggregateRequest(BaseModel):
    objective_id: str


@app.post("/aggregate")
async def aggregate(req: AggregateRequest) -> dict:
    """Trigger aggregation for an objective."""
    result = aggregator.aggregate(req.objective_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "aggregator_agent"}


async def poll_aggregator_queue(interval: float = 5.0) -> None:
    """Poll the aggregator inbox for task results."""
    logger.info("Aggregator polling started (interval=%.1fs)", interval)
    while True:
        try:
            messages = comm.receive_messages(QUEUE_AGGREGATOR_INBOX)
            for msg in messages:
                if msg.message_type == "task_result" and msg.task_id:
                    task = db.get_task(msg.task_id)
                    if task is None:
                        continue
                    # Check if all tasks for the objective are done
                    plan = db.get_plan_by_objective(msg.objective_id)
                    if plan is None:
                        continue
                    all_done = True
                    for t in plan.tasks:
                        fetched = db.get_task(t.id)
                        if not fetched or fetched.status not in (TaskStatus.COMPLETED, TaskStatus.FAILED):
                            all_done = False
                            break
                    if all_done:
                        result = aggregator.aggregate(msg.objective_id)
                        # Send completion back to controller
                        completion_msg = SwarmMessage(
                            source_agent_id="aggregator",
                            target_agent_id="controller",
                            objective_id=msg.objective_id,
                            message_type="aggregation_complete",
                            payload=result.get("summary", "Aggregation complete"),
                        )
                        comm.send_to_controller(completion_msg)
        except Exception:
            logger.exception("Error in aggregator poll loop")
        await asyncio.sleep(interval)


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(poll_aggregator_queue())


if __name__ == "__main__":
    uvicorn.run("src.aggregator_agent.app:app", host="0.0.0.0", port=8003, reload=True)
