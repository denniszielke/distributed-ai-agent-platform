"""In-memory SQLite database for objectives, plans, and tasks."""

from __future__ import annotations

import json
import logging
import sqlite3
from typing import Optional

from .models import (
    AgentPlan,
    Objective,
    Task,
    TaskStatus,
)

logger = logging.getLogger(__name__)


class SwarmDatabase:
    """Lightweight SQLite store for objectives, plans and tasks."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _create_tables(self) -> None:
        cur = self._conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS objectives (
                id TEXT PRIMARY KEY,
                input_text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                plan_id TEXT,
                result TEXT,
                created_at TEXT NOT NULL,
                last_updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS agent_plans (
                id TEXT PRIMARY KEY,
                objective_id TEXT NOT NULL,
                description TEXT NOT NULL,
                tasks_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL,
                FOREIGN KEY (objective_id) REFERENCES objectives(id)
            );

            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                payload TEXT,
                description TEXT,
                task_template TEXT NOT NULL DEFAULT '',
                task_type TEXT DEFAULT 'execute',
                tags TEXT DEFAULT '[]',
                priority INTEGER DEFAULT 50,
                target_agent_id TEXT,
                enabled INTEGER DEFAULT 1,
                last_run_at TEXT,
                result TEXT,
                status TEXT DEFAULT 'pending',
                created_by_agent_id TEXT,
                timezone TEXT DEFAULT 'UTC',
                created_at TEXT NOT NULL,
                last_updated_at TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Objectives CRUD
    # ------------------------------------------------------------------

    def insert_objective(self, obj: Objective) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """INSERT INTO objectives
               (id, input_text, status, plan_id, result, created_at, last_updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                obj.id,
                obj.input_text,
                obj.status.value,
                obj.plan_id,
                obj.result,
                obj.created_at,
                obj.last_updated_at,
            ),
        )
        self._conn.commit()

    def get_objective(self, objective_id: str) -> Optional[Objective]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM objectives WHERE id = ?", (objective_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return Objective(
            id=row["id"],
            input_text=row["input_text"],
            status=TaskStatus(row["status"]),
            plan_id=row["plan_id"],
            result=row["result"],
            created_at=row["created_at"],
            last_updated_at=row["last_updated_at"],
        )

    def list_objectives(self) -> list[Objective]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM objectives ORDER BY created_at DESC")
        return [
            Objective(
                id=r["id"],
                input_text=r["input_text"],
                status=TaskStatus(r["status"]),
                plan_id=r["plan_id"],
                result=r["result"],
                created_at=r["created_at"],
                last_updated_at=r["last_updated_at"],
            )
            for r in cur.fetchall()
        ]

    def update_objective(self, objective_id: str, **kwargs: object) -> None:
        allowed = {"status", "plan_id", "result", "last_updated_at"}
        parts: list[str] = []
        values: list[object] = []
        for k, v in kwargs.items():
            if k not in allowed:
                continue
            parts.append(f"{k} = ?")
            values.append(v.value if isinstance(v, TaskStatus) else v)
        if not parts:
            return
        values.append(objective_id)
        cur = self._conn.cursor()
        cur.execute(
            f"UPDATE objectives SET {', '.join(parts)} WHERE id = ?",
            values,
        )
        self._conn.commit()

    # ------------------------------------------------------------------
    # Agent Plans CRUD
    # ------------------------------------------------------------------

    def insert_plan(self, plan: AgentPlan) -> None:
        tasks_json = json.dumps([t.model_dump() for t in plan.tasks])
        cur = self._conn.cursor()
        cur.execute(
            """INSERT INTO agent_plans (id, objective_id, description, tasks_json, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (plan.id, plan.objective_id, plan.description, tasks_json, plan.created_at),
        )
        self._conn.commit()

    def get_plan(self, plan_id: str) -> Optional[AgentPlan]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM agent_plans WHERE id = ?", (plan_id,))
        row = cur.fetchone()
        if row is None:
            return None
        tasks = [Task(**t) for t in json.loads(row["tasks_json"])]
        return AgentPlan(
            id=row["id"],
            objective_id=row["objective_id"],
            description=row["description"],
            tasks=tasks,
            created_at=row["created_at"],
        )

    def get_plan_by_objective(self, objective_id: str) -> Optional[AgentPlan]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM agent_plans WHERE objective_id = ?", (objective_id,))
        row = cur.fetchone()
        if row is None:
            return None
        tasks = [Task(**t) for t in json.loads(row["tasks_json"])]
        return AgentPlan(
            id=row["id"],
            objective_id=row["objective_id"],
            description=row["description"],
            tasks=tasks,
            created_at=row["created_at"],
        )

    # ------------------------------------------------------------------
    # Tasks CRUD
    # ------------------------------------------------------------------

    def insert_task(self, task: Task) -> None:
        cur = self._conn.cursor()
        cur.execute(
            """INSERT INTO tasks
               (id, name, payload, description, task_template, task_type,
                tags, priority, target_agent_id, enabled, last_run_at,
                result, status, created_by_agent_id, timezone,
                created_at, last_updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                task.id,
                task.name,
                task.payload,
                task.description,
                task.task_template,
                task.task_type.value,
                json.dumps(task.tags),
                task.priority,
                task.target_agent_id,
                int(task.enabled),
                task.last_run_at,
                task.result,
                task.status.value,
                task.created_by_agent_id,
                task.timezone,
                task.created_at,
                task.last_updated_at,
            ),
        )
        self._conn.commit()

    def get_task(self, task_id: str) -> Optional[Task]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cur.fetchone()
        if row is None:
            return None
        return self._row_to_task(row)

    def list_tasks(self, objective_id: Optional[str] = None) -> list[Task]:
        cur = self._conn.cursor()
        if objective_id:
            # Tasks belonging to the plan for this objective
            cur.execute(
                """SELECT t.* FROM tasks t
                   JOIN agent_plans p ON p.objective_id = ?
                   WHERE t.id IN (
                       SELECT json_each.value->>'id'
                       FROM agent_plans, json_each(agent_plans.tasks_json)
                       WHERE agent_plans.objective_id = ?
                   )
                   ORDER BY t.priority DESC""",
                (objective_id, objective_id),
            )
        else:
            cur.execute("SELECT * FROM tasks ORDER BY created_at DESC")
        return [self._row_to_task(r) for r in cur.fetchall()]

    def update_task(self, task_id: str, **kwargs: object) -> None:
        allowed = {
            "status", "result", "last_run_at", "last_updated_at",
            "payload", "target_agent_id", "enabled",
        }
        parts: list[str] = []
        values: list[object] = []
        for k, v in kwargs.items():
            if k not in allowed:
                continue
            parts.append(f"{k} = ?")
            if isinstance(v, TaskStatus):
                values.append(v.value)
            elif isinstance(v, bool):
                values.append(int(v))
            else:
                values.append(v)
        if not parts:
            return
        values.append(task_id)
        cur = self._conn.cursor()
        cur.execute(
            f"UPDATE tasks SET {', '.join(parts)} WHERE id = ?",
            values,
        )
        self._conn.commit()

    def list_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM tasks WHERE status = ? ORDER BY priority DESC", (status.value,))
        return [self._row_to_task(r) for r in cur.fetchall()]

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            name=row["name"],
            payload=row["payload"],
            description=row["description"],
            task_template=row["task_template"],
            task_type=row["task_type"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            priority=row["priority"],
            target_agent_id=row["target_agent_id"],
            enabled=bool(row["enabled"]),
            last_run_at=row["last_run_at"],
            result=row["result"],
            status=TaskStatus(row["status"]),
            created_by_agent_id=row["created_by_agent_id"],
            timezone=row["timezone"],
            created_at=row["created_at"],
            last_updated_at=row["last_updated_at"],
        )

    def close(self) -> None:
        self._conn.close()
