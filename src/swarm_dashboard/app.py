"""Swarm Dashboard – web UI for monitoring agent swarm operations."""

from __future__ import annotations

import logging
import os
from datetime import datetime

import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONTROLLER_URL = os.environ.get("SWARM_CONTROLLER_URL", "http://localhost:8000")
REGISTRY_URL = os.environ.get("SWARM_REGISTRY_URL", "http://localhost:8002")

app = FastAPI(title="Agent Swarm Dashboard", version="0.1.0")
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Main dashboard page."""
    objectives: list[dict] = []
    tasks: list[dict] = []
    registry: dict = {"agents": [], "mcp_servers": [], "skills": []}

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{CONTROLLER_URL}/objectives")
            if resp.status_code == 200:
                objectives = resp.json()
    except Exception:
        logger.warning("Could not reach swarm controller")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{CONTROLLER_URL}/tasks")
            if resp.status_code == 200:
                tasks = resp.json()
    except Exception:
        logger.warning("Could not reach swarm controller for tasks")

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{REGISTRY_URL}/context")
            if resp.status_code == 200:
                registry = resp.json()
    except Exception:
        logger.warning("Could not reach swarm registry")

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "objectives": objectives,
            "tasks": tasks,
            "registry": registry,
            "now": datetime.utcnow().isoformat(),
        },
    )


@app.get("/api/objectives")
async def api_objectives() -> list[dict]:
    """Proxy to controller objectives API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{CONTROLLER_URL}/objectives")
            return resp.json()
    except Exception:
        return []


@app.get("/api/tasks")
async def api_tasks() -> list[dict]:
    """Proxy to controller tasks API."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{CONTROLLER_URL}/tasks")
            return resp.json()
    except Exception:
        return []


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": "swarm_dashboard"}


if __name__ == "__main__":
    uvicorn.run("src.swarm_dashboard.app:app", host="0.0.0.0", port=8080, reload=True)
