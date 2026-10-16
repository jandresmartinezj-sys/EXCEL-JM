"""Memoria empresarial por niveles con procedencia, retención y borrado lógico auditado."""
from datetime import datetime, timedelta, timezone

from . import audit
from .db import rows

SCOPES = ("work", "business", "client", "decision", "preference")
DEFAULT_RETENTION_DAYS = {"work": 180, "business": None, "client": None, "decision": None, "preference": None}


def save(conn, scope: str, content: str, source: str, actor: str, key: str | None = None,
         client_id: int | None = None, retention_days: int | None = -1) -> int:
    if scope not in SCOPES:
        raise ValueError("Ámbito de memoria inválido")
    if scope == "client" and client_id is None:
        raise ValueError("La memoria de cliente requiere client_id")
    days = DEFAULT_RETENTION_DAYS[scope] if retention_days == -1 else retention_days
    exp = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat() if days else None
    cur = conn.execute(
        "INSERT INTO memory (scope, client_id, key, content, source, created_by, expires_at) VALUES (?,?,?,?,?,?,?)",
        (scope, client_id, key, content.strip()[:4000], source, actor, exp))
    audit.log(conn, actor, "memory.save", f"memory:{cur.lastrowid}", {"scope": scope, "key": key, "source": source})
    return cur.lastrowid


def recall(conn, scopes=SCOPES, client_id: int | None = None, query: str | None = None, limit: int = 20) -> list[dict]:
    """Recupera memoria vigente. La memoria de un cliente solo se devuelve si se pide ese client_id."""
    now = datetime.now(timezone.utc).isoformat()
    sql = ["SELECT id, scope, client_id, key, content, source, created_at FROM memory",
           "WHERE deleted_at IS NULL AND (expires_at IS NULL OR expires_at > ?)"]
    params: list = [now]
    sql.append("AND scope IN (%s)" % ",".join("?" * len(scopes)))
    params += list(scopes)
    sql.append("AND (client_id IS NULL OR client_id = ?)")
    params.append(client_id if client_id is not None else -1)
    if query:
        sql.append("AND (content LIKE ? OR key LIKE ?)")
        params += [f"%{query}%", f"%{query}%"]
    sql.append("ORDER BY id DESC LIMIT ?")
    params.append(limit)
    return rows(conn, " ".join(sql), params)


def forget(conn, memory_id: int, actor: str) -> None:
    """Borrado lógico (el contenido se sobrescribe; queda la traza en auditoría)."""
    conn.execute("UPDATE memory SET deleted_at = datetime('now'), content = '[eliminado]' WHERE id = ?", (memory_id,))
    audit.log(conn, actor, "memory.forget", f"memory:{memory_id}", {})


def purge_expired_conversations(conn, days: int) -> int:
    cur = conn.execute("DELETE FROM conversations WHERE created_at < datetime('now', ?)", (f"-{int(days)} days",))
    return cur.rowcount
