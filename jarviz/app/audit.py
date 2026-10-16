"""Registro de auditoría encadenado por hash (solo inserción; triggers en la BD lo impiden)."""
import hashlib
import json
import threading
from datetime import datetime, timezone

from .db import rows

GENESIS = "0" * 64
_lock = threading.Lock()


def _digest(prev: str, ts: str, actor: str, action: str, target: str, detail: str) -> str:
    return hashlib.sha256("|".join([prev, ts, actor, action, target or "", detail]).encode()).hexdigest()


def log(conn, actor: str, action: str, target: str | None = None, detail: dict | None = None) -> None:
    detail_s = json.dumps(detail or {}, ensure_ascii=False, sort_keys=True, default=str)
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with _lock:  # lectura del último hash + escritura sin carreras dentro del proceso
        last = conn.execute("SELECT hash FROM audit_log ORDER BY id DESC LIMIT 1").fetchone()
        prev = last["hash"] if last else GENESIS
        h = _digest(prev, ts, actor, action, target or "", detail_s)
        conn.execute(
            "INSERT INTO audit_log (ts, actor, action, target, detail_json, prev_hash, hash) VALUES (?,?,?,?,?,?,?)",
            (ts, actor, action, target, detail_s, prev, h),
        )


def verify(conn) -> dict:
    """Recalcula la cadena. Detecta ediciones o eliminaciones hechas por fuera de la aplicación."""
    prev = GENESIS
    n = 0
    for r in conn.execute("SELECT * FROM audit_log ORDER BY id"):
        expected = _digest(prev, r["ts"], r["actor"], r["action"], r["target"] or "", r["detail_json"])
        if r["prev_hash"] != prev or r["hash"] != expected:
            return {"ok": False, "broken_at_id": r["id"], "checked": n}
        prev = r["hash"]
        n += 1
    return {"ok": True, "checked": n}


def recent(conn, limit: int = 100) -> list[dict]:
    return rows(conn, "SELECT id, ts, actor, action, target, detail_json FROM audit_log ORDER BY id DESC LIMIT ?", (limit,))
