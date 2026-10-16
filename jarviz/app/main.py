"""API HTTP de JARVIZ + servidor de la aplicación web (PWA)."""
from datetime import date
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import __version__, alerts, analytics as an, audit, memory, policy, security, tasks
from .agents import summary as agents_summary
from .automations import REGISTRY as AUTOMATIONS
from .config import get_settings
from .db import connect, one, rows
from .orchestrator import Orchestrator, decide_approval, run_scheduled

WEB = Path(__file__).resolve().parent.parent / "web"
app = FastAPI(title="JARVIZ", version=__version__, docs_url="/api/docs", redoc_url=None)
_s = get_settings()
if _s.allowed_origins:
    app.add_middleware(CORSMiddleware, allow_origins=list(_s.allowed_origins), allow_methods=["GET", "POST"],
                       allow_headers=["Authorization", "Content-Type"])
login_limiter = security.RateLimiter(5, 60)
command_limiter = security.RateLimiter(30, 60)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Permissions-Policy"] = "microphone=(self), camera=(), geolocation=()"
    resp.headers["Content-Security-Policy"] = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
                                               "connect-src 'self'; manifest-src 'self'; worker-src 'self'")
    return resp


def db():
    return connect()


def current_user(authorization: str = Header(default=""), conn=Depends(db)) -> dict:
    token = authorization.removeprefix("Bearer ").strip()
    user = security.resolve_token(conn, token)
    if not user:
        raise HTTPException(401, "No autenticado")
    return user


def staff_user(user=Depends(current_user)) -> dict:
    if user["role"] not in ("owner", "staff"):
        raise HTTPException(403, "Solo el equipo de la firma")
    return user


def owner_user(user=Depends(current_user)) -> dict:
    if user["role"] != "owner":
        raise HTTPException(403, "Solo el propietario")
    return user


def today() -> date:
    return date.today()


# ------------------------------------------------------------------ autenticación
class Login(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=256)


@app.post("/api/auth/login")
def login(body: Login, request: Request, conn=Depends(db)):
    ip = request.client.host if request.client else "?"
    if not login_limiter.allow(f"{ip}:{body.username.lower()}"):
        raise HTTPException(429, "Demasiados intentos; espera un minuto.")
    u = one(conn, "SELECT * FROM users WHERE username = ?", (body.username.strip().lower(),))
    if not u or not security.check_password(body.password, u["pw_hash"]):
        audit.log(conn, f"anon:{ip}", "auth.login_failed", None, {"username": body.username[:64]})
        raise HTTPException(401, "Credenciales inválidas")
    token = security.issue_token(conn, u["id"], "session", get_settings().session_hours)
    audit.log(conn, f"user:{u['username']}", "auth.login", None, {})
    return {"token": token, "user": {"username": u["username"], "role": u["role"], "client_id": u["client_id"]}}


@app.post("/api/auth/logout")
def logout(authorization: str = Header(default=""), conn=Depends(db), user=Depends(current_user)):
    security.revoke_token(conn, authorization.removeprefix("Bearer ").strip())
    audit.log(conn, f"user:{user['username']}", "auth.logout", None, {})
    return {"ok": True}


class TokenReq(BaseModel):
    label: str = Field(min_length=2, max_length=60)
    days: int = Field(default=90, ge=1, le=365)


@app.post("/api/auth/personal-token")
def personal_token(body: TokenReq, conn=Depends(db), user=Depends(owner_user)):
    """Token para Atajos de iOS / Siri. Se muestra una sola vez; se puede revocar."""
    tok = security.issue_token(conn, user["id"], "personal", body.days * 24, body.label)
    audit.log(conn, f"user:{user['username']}", "auth.personal_token", None, {"label": body.label, "days": body.days})
    return {"token": tok, "warning": "Guárdalo en el Atajo; no se volverá a mostrar."}


@app.get("/api/me")
def me(user=Depends(current_user)):
    return {k: user[k] for k in ("username", "role", "client_id")}


# ------------------------------------------------------------------ cerebro central
class Command(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


def _run_command(text, conn, user):
    if not command_limiter.allow(user["username"]):
        raise HTTPException(429, "Demasiadas instrucciones por minuto.")
    return Orchestrator(conn, user, today()).handle(text)


@app.post("/api/command")
def command(body: Command, conn=Depends(db), user=Depends(staff_user)):
    return _run_command(body.text, conn, user)


@app.post("/api/shortcut", response_class=PlainTextResponse)
def shortcut(body: Command, conn=Depends(db), user=Depends(staff_user)):
    """Respuesta en texto plano para 'Leer texto' en Atajos de iOS."""
    return _run_command(body.text, conn, user).get("speech", "")


@app.get("/api/conversation")
def conversation(conn=Depends(db), user=Depends(staff_user)):
    return rows(conn, "SELECT role, content, created_at FROM conversations WHERE user_id = ? ORDER BY id DESC LIMIT 50", (user["id"],))[::-1]


@app.delete("/api/conversation")
def clear_conversation(conn=Depends(db), user=Depends(staff_user)):
    n = conn.execute("DELETE FROM conversations WHERE user_id = ?", (user["id"],)).rowcount
    audit.log(conn, f"user:{user['username']}", "conversation.clear", None, {"deleted": n})
    return {"deleted": n}


# ------------------------------------------------------------------ centro de mando
@app.get("/api/dashboard")
def dashboard(conn=Depends(db), user=Depends(staff_user)):
    alerts.run(conn, today())  # idempotente: deduplica por huella
    k = an.kpis(conn, today())
    return {**k, "alerts": alerts.open_alerts(conn, 10), "llm_mode": get_settings().anthropic_key_present}


@app.get("/api/obligations")
def obligations(days: int = 30, conn=Depends(db), user=Depends(staff_user)):
    return an.obligations_overview(conn, today(), horizon_days=max(1, min(days, 365)))


@app.get("/api/receivables")
def receivables_ep(conn=Depends(db), user=Depends(staff_user)):
    return an.receivables(conn, today())


@app.get("/api/pipeline")
def pipeline_ep(conn=Depends(db), user=Depends(staff_user)):
    return an.pipeline(conn, today())


@app.get("/api/clients")
def clients(conn=Depends(db), user=Depends(staff_user)):
    return an.profitability(conn, today())["items"]


@app.get("/api/agents")
def agents(user=Depends(staff_user)):
    return agents_summary()


@app.get("/api/automations")
def automations_ep(user=Depends(staff_user)):
    return AUTOMATIONS


@app.get("/api/alerts")
def alerts_ep(conn=Depends(db), user=Depends(staff_user)):
    return alerts.open_alerts(conn)


@app.post("/api/alerts/{alert_id}/ack")
def alert_ack(alert_id: int, conn=Depends(db), user=Depends(staff_user)):
    conn.execute("UPDATE alerts SET status = 'ack' WHERE id = ?", (alert_id,))
    audit.log(conn, f"user:{user['username']}", "alert.ack", f"alert:{alert_id}", {})
    return {"ok": True}


@app.post("/api/scheduled/run")
def scheduled(conn=Depends(db), user=Depends(owner_user)):
    return run_scheduled(conn, today())


# ------------------------------------------------------------------ tareas y aprobaciones
@app.get("/api/tasks")
def tasks_ep(status: str | None = None, conn=Depends(db), user=Depends(staff_user)):
    if status and status not in tasks.VALID:
        raise HTTPException(400, "Estado inválido")
    return tasks.list_tasks(conn, status)


class TaskStatus(BaseModel):
    status: str


@app.post("/api/tasks/{task_id}/status")
def task_status(task_id: int, body: TaskStatus, conn=Depends(db), user=Depends(staff_user)):
    if body.status not in ("completed", "cancelled", "pending"):
        raise HTTPException(400, "Solo se permite completar, cancelar o reabrir")
    try:
        t = tasks.get(conn, task_id)
        if not t:
            raise HTTPException(404, "No existe")
        if body.status == "completed" and t["status"] == "pending":
            tasks.transition(conn, task_id, "running", f"user:{user['username']}")
        return tasks.transition(conn, task_id, body.status, f"user:{user['username']}")
    except ValueError as e:
        raise HTTPException(409, str(e))


@app.get("/api/approvals")
def approvals(conn=Depends(db), user=Depends(staff_user)):
    return rows(conn, "SELECT * FROM approvals ORDER BY CASE status WHEN 'pending' THEN 0 ELSE 1 END, id DESC LIMIT 100")


class Decision(BaseModel):
    approve: bool


@app.post("/api/approvals/{approval_id}/decide")
def decide(approval_id: int, body: Decision, conn=Depends(db), user=Depends(owner_user)):
    try:
        return decide_approval(conn, approval_id, body.approve, f"user:{user['username']}")
    except KeyError:
        raise HTTPException(404, "No existe")
    except ValueError as e:
        raise HTTPException(409, str(e))


# ------------------------------------------------------------------ memoria, configuración y auditoría
@app.get("/api/memory")
def memory_ep(scope: str | None = None, q: str | None = None, conn=Depends(db), user=Depends(staff_user)):
    scopes = (scope,) if scope in memory.SCOPES else ("work", "business", "decision", "preference")
    return memory.recall(conn, scopes, query=q, limit=100)


@app.delete("/api/memory/{memory_id}")
def memory_forget(memory_id: int, conn=Depends(db), user=Depends(owner_user)):
    memory.forget(conn, memory_id, f"user:{user['username']}")
    return {"ok": True}


class AutonomyReq(BaseModel):
    level: int = Field(ge=1, le=5)


@app.get("/api/settings")
def settings_get(conn=Depends(db), user=Depends(staff_user)):
    return {"max_autonomy": policy.global_autonomy(conn, get_settings().max_autonomy), "actions": policy.ACTIONS,
            "always_approval": sorted(policy.ALWAYS_APPROVAL), "llm_mode": get_settings().anthropic_key_present,
            "model": get_settings().model, "conversation_retention_days": get_settings().conversation_retention_days}


@app.post("/api/settings/autonomy")
def settings_autonomy(body: AutonomyReq, conn=Depends(db), user=Depends(owner_user)):
    conn.execute("INSERT INTO settings (key, value) VALUES ('max_autonomy', ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (str(body.level),))
    audit.log(conn, f"user:{user['username']}", "settings.autonomy", None, {"level": body.level})
    return {"max_autonomy": body.level}


@app.get("/api/audit")
def audit_ep(conn=Depends(db), user=Depends(owner_user)):
    return {"integrity": audit.verify(conn), "entries": audit.recent(conn, 200)}


# ------------------------------------------------------------------ portal de clientes (solo su información)
@app.get("/api/portal")
def portal(conn=Depends(db), user=Depends(current_user)):
    if user["role"] != "client":
        raise HTTPException(403, "Portal exclusivo para clientes")
    cid = user["client_id"]
    return {
        "client": one(conn, "SELECT name, plan, status FROM clients WHERE id = ?", (cid,)),
        "obligations": rows(conn, "SELECT kind, period, due_date, status FROM obligations WHERE client_id = ? ORDER BY due_date", (cid,)),
        "invoices": rows(conn, "SELECT number, issue_date, due_date, amount, paid FROM invoices WHERE client_id = ? ORDER BY issue_date DESC", (cid,)),
        "documents": rows(conn, "SELECT title, kind, period, created_at FROM documents WHERE client_id = ? ORDER BY id DESC", (cid,)),
    }


@app.get("/api/health")
def health():
    return {"ok": True, "version": __version__}


# ------------------------------------------------------------------ aplicación web
@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/sw.js")
def sw():
    return FileResponse(WEB / "sw.js", media_type="application/javascript", headers={"Service-Worker-Allowed": "/"})


app.mount("/static", StaticFiles(directory=WEB), name="static")
