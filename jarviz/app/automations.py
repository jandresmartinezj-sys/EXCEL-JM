"""Flujos de varios pasos con idempotencia, permisos y registro. Ver AUTOMATIONS.md."""
from datetime import date, timedelta

from . import audit, memory, tasks
from .analytics import (DEFAULT_GOALS, PLAN_PRICES, close_checklist, draft_proposal, kpis, money, norm,
                        obligations_overview, pipeline, receivables)
from .db import one

SEGMENT_HINTS = {
    "Emprendedor digital": ("tienda online", "ecommerce", "e-commerce", "digital", "instagram", "emprend"),
    "Persona natural": ("persona natural", "independiente", "renta personal"),
    "Agro / ganadero": ("ganad", "finca", "hacienda", "agro"),
    "Pyme comercio": ("comercial", "distribu", "ferret", "tienda", "almacen"),
    "Pyme servicios": ("servicio", "restaurante", "transporte", "taller", "consultor"),
}
PLAN_BY_SEGMENT = {"Persona natural": "Básico", "Emprendedor digital": "Básico", "Agro / ganadero": "Empresa",
                   "Pyme comercio": "Empresa", "Pyme servicios": "Empresa"}
DIAG_QUESTIONS = {
    "default": ["¿Qué régimen tienes (SIMPLE u ordinario)? ¿Facturas electrónicamente?",
                "¿Cuántos documentos y empleados manejas al mes?",
                "¿Sabes cuánto ganas realmente por mes?",
                "¿Has tenido sanciones o requerimientos de la DIAN?"],
    "Agro / ganadero": ["¿Declaras renta como persona natural? ¿Quién la prepara hoy?",
                        "¿Cómo facturas las ventas de ganado o cosecha?",
                        "¿Llevas costos por lote o finca?",
                        "¿Has tenido requerimientos de la DIAN o problemas de patrimonio?"],
}

REGISTRY = {
    "A_nuevo_prospecto": {"trigger": "Comando o API (POST /api/command)", "level": 3,
                          "idempotency": "nombre normalizado + contacto", "external": "envío de propuesta = aprobación nivel 4"},
    "B_cierre_contable": {"trigger": "Comando 'prepara el cierre de <cliente>'", "level": 3,
                          "idempotency": "cliente + periodo + paso", "external": "ninguna; requiere validación profesional"},
    "C_vigilancia_obligaciones": {"trigger": "Programador diario (cli run-scheduled) o API", "level": 3,
                                  "idempotency": "obligación + 'prep'", "external": "presentación = aprobación nivel 4"},
    "E_revision_semanal": {"trigger": "Comando o programador semanal", "level": 3,
                           "idempotency": "año-semana ISO", "external": "ninguna"},
}


def detect_segment(text: str) -> str | None:
    t = norm(text)
    for seg, keys in SEGMENT_HINTS.items():
        if any(k in t for k in keys):
            return seg
    return None


def flow_new_prospect(conn, actor: str, name: str, today: date, contact: str | None = None,
                      segment: str | None = None, channel: str | None = None) -> dict:
    name = name.strip(" .,:;")
    if len(name) < 3:
        raise ValueError("Necesito el nombre del prospecto (mínimo 3 caracteres).")
    segment = segment or detect_segment(name)
    key = f"{norm(name)}|{norm(contact or '')}"
    existing = one(conn, "SELECT * FROM prospects WHERE dedupe_key = ?", (key,))
    if existing:
        return {"duplicate": True, "prospect": existing, "message": f"{name} ya estaba registrado; no se duplicó."}
    plan = PLAN_BY_SEGMENT.get(segment, "Empresa")
    nxt = (today + timedelta(days=2)).isoformat()
    cur = conn.execute(
        """INSERT INTO prospects (created_at, name, segment, channel, contact, stage, plan, monthly_value, next_step, next_step_date, owner, dedupe_key)
           VALUES (?,?,?,?,?,'1 Prospecto',?,?,?,?,?,?)""",
        (today.isoformat(), name, segment, channel, contact, plan, PLAN_PRICES[plan],
         "Contactar y agendar diagnóstico", nxt, "titular", key))
    pid = cur.lastrowid
    audit.log(conn, actor, "prospect.create", f"prospect:{pid}", {"name": name, "segment": segment})
    proposal = draft_proposal(conn, name, plan, segment)
    task = tasks.create(conn, f"Contactar a {name} y agendar diagnóstico", actor, kind="comercial", agent="ventas",
                        due_date=nxt, idempotency_key=f"prospect:{pid}:contact")
    return {"duplicate": False, "prospect_id": pid, "segment": segment or "sin clasificar (completar)",
            "recommended_plan": plan, "diagnostic_questions": DIAG_QUESTIONS.get(segment, DIAG_QUESTIONS["default"]),
            "proposal_draft": proposal, "next_action": {"task_id": task["id"], "date": nxt},
            "approval_note": "La propuesta no se envía sin tu aprobación."}


def flow_close(conn, actor: str, client_id: int, period: str) -> dict:
    chk = close_checklist(conn, client_id, period)
    created = 0
    for i, s in enumerate(chk["steps"], 1):
        t = tasks.create(conn, f"[Cierre {period}] {s['step']}", actor, kind="cierre", agent="contabilidad",
                         client_id=client_id, idempotency_key=f"close:{client_id}:{period}:{i}")
        created += 0 if t.get("_duplicate") else 1
    chk["tasks_created"] = created
    chk["tasks_already_existed"] = len(chk["steps"]) - created
    return chk


def flow_obligation_watch(conn, actor: str, today: date) -> dict:
    created = []
    for o in obligations_overview(conn, today, horizon_days=15)["items"]:
        due = date.fromisoformat(o["due_date"])
        prep = max(today, due - timedelta(days=5)).isoformat()
        t = tasks.create(conn, f"Preparar {o['kind']} {o['period'] or ''} de {o['client']} (vence {o['due_date']})", actor,
                         kind="tributario", agent="tributario", client_id=o["client_id"], due_date=prep,
                         idempotency_key=f"obl:{o['id']}:prep")
        if not t.get("_duplicate"):
            created.append(t["id"])
    return {"tasks_created": len(created), "task_ids": created}


def flow_weekly_review(conn, actor: str, today: date) -> dict:
    y, w, _ = today.isocalendar()
    key = f"weekly:{y}-W{w:02d}"
    prior = one(conn, "SELECT id, content FROM memory WHERE scope = 'work' AND key = ? AND deleted_at IS NULL", (key,))
    report = weekly_report(conn, today)
    if prior:
        report["note"] = "La revisión de esta semana ya estaba registrada; se muestra actualizada sin duplicar."
    else:
        memory.save(conn, "work", report["text"], source="flujo E (revisión semanal)", actor=actor, key=key)
    return report


def weekly_report(conn, today: date) -> dict:
    k = {x["id"]: x for x in kpis(conn, today)["kpis"]}
    pl = pipeline(conn, today)
    ar = receivables(conn, today)
    obl = obligations_overview(conn, today, horizon_days=7)
    priorities = []
    if k["obl_overdue"]["value"]:
        priorities.append(f"1) Presentar {k['obl_overdue']['value']} obligación(es) vencida(s) hoy.")
    if obl["items"]:
        priorities.append(f"{len(priorities)+1}) Preparar {len(obl['items'])} obligación(es) que vencen en 7 días.")
    if ar["buckets"]["Más de 30"] or ar["buckets"]["16-30"]:
        priorities.append(f"{len(priorities)+1}) Cobrar {money(ar['buckets']['Más de 30'] + ar['buckets']['16-30'])} con más de 15 días de mora.")
    stale = [i for i in pl["items"] if i["alert"] != "OK"]
    if stale:
        priorities.append(f"{len(priorities)+1}) Dar seguimiento a {len(stale)} oportunidad(es) sin próximo paso vigente.")
    mrr = k["mrr"]["value"]
    if mrr is not None and mrr < DEFAULT_GOALS["mrr"]:
        gap = DEFAULT_GOALS["mrr"] - mrr
        priorities.append(f"{len(priorities)+1}) Brecha de MRR frente a la meta: {money(gap)}/mes ≈ {gap / 750_000:.0f} cliente(s) del plan Empresa.")
    if not priorities:
        priorities.append("Sin desviaciones críticas en los datos registrados.")
    text = "REVISIÓN SEMANAL " + today.isoformat() + "\n" + "\n".join(priorities)
    return {"as_of": today.isoformat(), "priorities": priorities, "text": text,
            "data": {"mrr": mrr, "pipeline_value": pl["value"], "receivables": ar["total"], "obligations_7d": len(obl["items"])},
            "sources": ["clients", "prospects", "invoices", "obligations"]}
