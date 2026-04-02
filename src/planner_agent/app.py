"""FastAPI application for the Planner Agent."""

from __future__ import annotations

import logging
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .planner import PlannerAgent
from .search_store import ExecutionPlanSearchStore

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

search_store = ExecutionPlanSearchStore()
planner = PlannerAgent(search_store=search_store)

app = FastAPI(title="Planner Agent", version="0.1.0")


class PlanRequest(BaseModel):
    objective_id: str
    objective_text: str
    registry_context: dict | None = None


class RecordRequest(BaseModel):
    id: str
    query: str
    description: str
    intent: str
    category: str | None = None
    complexity: str | None = None
    score: int | None = None


@app.post("/plan")
async def create_plan(req: PlanRequest) -> dict:
    """Create an execution plan for an objective."""
    plan = planner.create_plan(
        objective_id=req.objective_id,
        objective_text=req.objective_text,
        registry_context=req.registry_context,
    )
    return plan.model_dump()


@app.post("/record")
async def record_execution(req: RecordRequest) -> dict:
    """Record a completed execution plan in AI Search."""
    from src.swarm_controller.models import AgentExecutionPlan

    plan = AgentExecutionPlan(**req.model_dump())
    planner.record_execution(plan)
    return {"status": "recorded", "id": plan.id}


@app.post("/index/create")
async def create_index() -> dict:
    """Create or update the AI Search index."""
    search_store.create_index()
    return {"status": "index_created"}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "planner_agent"}


if __name__ == "__main__":
    uvicorn.run("src.planner_agent.app:app", host="0.0.0.0", port=8001, reload=True)
