"""FastAPI application for the Swarm Controller."""

from __future__ import annotations

import asyncio
import logging
import os

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .controller import SwarmController
from .database import SwarmDatabase
from .models import Objective

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = SwarmDatabase(os.environ.get("SWARM_DB_PATH", ":memory:"))
controller = SwarmController(db=db)

app = FastAPI(title="Agent Swarm Controller", version="0.1.0")


class SubmitRequest(BaseModel):
    input_text: str


class SubmitResponse(BaseModel):
    objective_id: str
    status: str


@app.post("/objectives", response_model=SubmitResponse)
async def submit_objective(req: SubmitRequest) -> SubmitResponse:
    """Submit a new objective to the swarm."""
    obj = controller.submit_objective(req.input_text)
    return SubmitResponse(objective_id=obj.id, status=obj.status.value)


@app.get("/objectives/{objective_id}")
async def get_objective_status(objective_id: str) -> dict:
    """Get status of an objective including plan and tasks."""
    result = controller.get_status(objective_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail="Objective not found")
    return result


@app.get("/objectives")
async def list_objectives() -> list[dict]:
    """List all objectives."""
    return [o.model_dump() for o in db.list_objectives()]


@app.get("/tasks")
async def list_tasks() -> list[dict]:
    """List all tasks."""
    return [t.model_dump() for t in db.list_tasks()]


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "swarm_controller"}


@app.on_event("startup")
async def startup() -> None:
    asyncio.create_task(controller.poll_loop())


if __name__ == "__main__":
    uvicorn.run("src.swarm_controller.app:app", host="0.0.0.0", port=8000, reload=True)
