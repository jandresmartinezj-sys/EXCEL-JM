"""Autenticación, tokens, roles y límite de solicitudes."""
import hashlib
import hmac
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone

from .db import one

ROLES = ("owner", "staff", "client")


def hash_password(password: str) -> str:
    if len(password) < 10:
        raise ValueError("La contraseña debe tener al menos 10 caracteres.")
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"scrypt${salt.hex()}${dk.hex()}"


def check_password(password: str, stored: str) -> bool:
    try:
        _, salt_h, dk_h = stored.split("$")
        dk = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_h), n=2**14, r=8, p=1)
        return hmac.compare_digest(dk.hex(), dk_h)
    except Exception:
        return False


def _th(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(conn, user_id: int, kind: str, hours: int, label: str | None = None) -> str:
    token = secrets.token_urlsafe(32)
    exp = (datetime.now(timezone.utc) + timedelta(hours=hours)).isoformat()
    conn.execute("INSERT INTO tokens (token_hash, user_id, kind, label, expires_at) VALUES (?,?,?,?,?)",
                 (_th(token), user_id, kind, label, exp))
    return token


def resolve_token(conn, token: str) -> dict | None:
    if not token:
        return None
    r = one(conn, """SELECT u.id, u.username, u.role, u.client_id, t.kind, t.expires_at, t.revoked
                     FROM tokens t JOIN users u ON u.id = t.user_id WHERE t.token_hash = ?""", (_th(token),))
    if not r or r["revoked"] or r["expires_at"] < datetime.now(timezone.utc).isoformat():
        return None
    return r


def revoke_token(conn, token: str) -> None:
    conn.execute("UPDATE tokens SET revoked = 1 WHERE token_hash = ?", (_th(token),))


def create_user(conn, username: str, password: str, role: str, client_id: int | None = None) -> int:
    if role not in ROLES:
        raise ValueError("Rol inválido")
    cur = conn.execute("INSERT INTO users (username, pw_hash, role, client_id) VALUES (?,?,?,?)",
                       (username.strip().lower(), hash_password(password), role, client_id))
    return cur.lastrowid


class RateLimiter:
    """Ventana deslizante en memoria (suficiente para un único proceso)."""

    def __init__(self, limit: int, window_s: int):
        self.limit, self.window = limit, window_s
        self.hits: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True
