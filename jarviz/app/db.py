"""Conexión SQLite y migraciones."""
import sqlite3
import threading
from pathlib import Path

from .config import get_settings

SCHEMA_VERSION = 1
_lock = threading.RLock()
_conn: sqlite3.Connection | None = None
_path: str | None = None


def connect(path: str | None = None) -> sqlite3.Connection:
    """Devuelve la conexión compartida (una por proceso; SQLite serializa escrituras)."""
    global _conn, _path
    path = path or get_settings().db_path
    with _lock:
        if _conn is not None and _path == path:
            return _conn
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL") if path != ":memory:" else None
        migrate(conn)
        _conn, _path = conn, path
        return conn


def reset(path: str) -> sqlite3.Connection:
    """Cierra la conexión actual y abre otra (pruebas)."""
    global _conn, _path
    with _lock:
        if _conn is not None:
            _conn.close()
        _conn, _path = None, None
    return connect(path)


def migrate(conn: sqlite3.Connection) -> None:
    sql = (Path(__file__).with_name("schema.sql")).read_text(encoding="utf-8")
    conn.executescript(sql)
    row = conn.execute("SELECT MAX(version) v FROM schema_version").fetchone()
    if (row["v"] or 0) < SCHEMA_VERSION:
        conn.execute("INSERT INTO schema_version VALUES (?, datetime('now'))", (SCHEMA_VERSION,))


def rows(conn, sql: str, params=()) -> list[dict]:
    return [dict(r) for r in conn.execute(sql, params).fetchall()]


def one(conn, sql: str, params=()) -> dict | None:
    r = conn.execute(sql, params).fetchone()
    return dict(r) if r else None
