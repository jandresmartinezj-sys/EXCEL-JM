"""Tareas con estados explícitos: pending → running → completed | failed | awaiting_approval | cancelled."""
import json

from . import audit
from .db import one, rows

VALID = {
    "pending": {"running", "cancelled", "awaiting_approval", "completed"},
    "running": {"completed", "failed", "awaiting_approval", "cancelled"},
    "awaiting_approval": {"running", "completed", "cancelled", "failed"},
    "failed": {"pending", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


def create(conn, title: str, actor: str, kind: str = "manual", agent: str | None = None,
           client_id: int | None = None, due_date: str | None = None, assignee: str | None = None,
           input_data: dict | None = None, idempotency_key: str | None = None) -> dict:
    """Crea una tarea. Con idempotency_key, una segunda llamada devuelve la existente (no duplica)."""
    if idempotency_key:
        existing = one(conn, "SELECT * FROM tasks WHERE idempotency_key = ?", (idempotency_key,))
        if existing:
            existing["_duplicate"] = True
            return existing
    cur = conn.execute(
        """INSERT INTO tasks (title, kind, agent, client_id, due_date, assignee, input_json, idempotency_key, created_by)
           VALUES (?,?,?,?,?,?,?,?,?)""",
        (title, kind, agent, client_id, due_date, assignee,
         json.dumps(input_data or {}, ensure_ascii=False), idempotency_key, actor))
    audit.log(conn, actor, "task.create", f"task:{cur.lastrowid}", {"title": title, "kind": kind, "agent": agent})
    return get(conn, cur.lastrowid)


def get(conn, task_id: int) -> dict | None:
    return one(conn, "SELECT * FROM tasks WHERE id = ?", (task_id,))


def transition(conn, task_id: int, status: str, actor: str, result: dict | None = None, error: str | None = None) -> dict:
    t = get(conn, task_id)
    if not t:
        raise KeyError(f"Tarea {task_id} no existe")
    if status not in VALID[t["status"]]:
        raise ValueError(f"Transición inválida {t['status']} → {status}")
    conn.execute(
        "UPDATE tasks SET status = ?, result_json = COALESCE(?, result_json), error = ?, updated_at = datetime('now') WHERE id = ?",
        (status, json.dumps(result, ensure_ascii=False, default=str) if result is not None else None, error, task_id))
    audit.log(conn, actor, f"task.{status}", f"task:{task_id}", {"error": error} if error else {})
    return get(conn, task_id)


def list_tasks(conn, status: str | None = None, limit: int = 100) -> list[dict]:
    if status:
        return rows(conn, "SELECT * FROM tasks WHERE status = ? ORDER BY id DESC LIMIT ?", (status, limit))
    return rows(conn, "SELECT * FROM tasks ORDER BY id DESC LIMIT ?", (limit,))
