"""Cerebro central: interpreta la instrucción, delega a los agentes, aplica permisos y consolida.

Modo local (siempre disponible): enrutamiento por intención en español.
Modo IA (si hay ANTHROPIC_API_KEY): solo para instrucciones que el modo local no reconoce.
"""
import json
import re
from datetime import date

from . import alerts, analytics as an, audit, automations, llm, memory, policy, tasks
from .agents import AGENTS, summary as agents_summary
from .config import get_settings
from .db import one, rows

# (intención, patrón sobre texto normalizado, agentes). El orden importa: lo específico primero.
INTENTS = [
    ("help", r"\b(ayuda|que puedes hacer|que sabes hacer|tus agentes|capacidades)\b", ["ceo"]),
    ("external_action", r"\b(envia|enviar|envie|manda|mandar|presenta la declaracion|presentar la declaracion|paga|pagar|transfiere|transferir|firma|firmar|borra|borrar|elimina|eliminar)\b", ["ceo"]),
    ("new_prospect", r"\b(nuevo|registra|registrar|agrega|agregar|crea|crear)( un| una)? (prospecto|cliente potencial)\b", ["ventas"]),
    ("proposal", r"\bpropuesta\b", ["ventas"]),
    ("close", r"\bcierre( contable)?\b", ["contabilidad", "operaciones"]),
    ("save_memory", r"^(anota|nota|recuerda que|guarda que|toma nota)\b", ["ceo"]),
    ("create_task", r"\b(crea|crear|agrega|agregar|nueva)( una)? tarea\b|^recuerdame\b", ["operaciones"]),
    ("weekly_review", r"\b(revision|informe|reporte) semanal\b", ["ceo"]),
    ("priorities", r"\bprioriz|\bprioridades\b", ["ceo", "finanzas", "ventas", "tributario"]),
    ("status", r"\b(estado (general )?(del )?negocio|resumen (ejecutivo|general|del negocio)|como va(mos)?|como esta el negocio|estado general)\b",
     ["ceo", "finanzas", "ventas", "tributario", "control"]),
    ("opportunities", r"\boportunidad", ["mercado"]),
    ("churn", r"\b(abandono|fideliz|clientes en riesgo|retencion)\b", ["cliente"]),
    ("obligations", r"\b(obligacion|vencimiento|vence|calendario tributario|declaracion)", ["tributario"]),
    ("receivables", r"\b(cartera|cobrar|cobro|facturas?)\b", ["finanzas"]),
    ("profitability", r"\b(rentab|ingreso por hora|margen)", ["finanzas"]),
    ("pipeline", r"\b(pipeline|embudo|prospectos|comercial|ventas)\b", ["ventas"]),
    ("risks", r"\b(riesgo|control interno|auditoria|cumplimiento)\b", ["control"]),
    ("system", r"\b(estado del sistema|sistema|tecnologia)\b", ["tecnologia"]),
]

EXTERNAL_MAP = [
    (r"declaracion", "external.file_declaration"), (r"paga|pagar|transfiere|transferir", "external.payment"),
    (r"firma|firmar", "external.sign_document"), (r"borra|borrar|elimina|eliminar", "internal.delete_data"),
    (r"propuesta", "external.send_proposal"), (r".", "external.send_message"),
]


def classify(text: str) -> tuple[str, list[str]]:
    t = an.norm(text)
    t = re.sub(r"^(oye |hola )?jarvi[sz],? ", "", t)
    for intent, pat, agents in INTENTS:
        if re.search(pat, t):
            return intent, agents
    return "unknown", []


def _speech_kpis(k: dict) -> list[str]:
    s = []
    mrr = k["mrr"]["value"]
    s.append(f"Ingreso recurrente {an.money(mrr)} al mes frente a una meta de {an.money(k['mrr']['goal'])}." if mrr is not None
             else "No hay clientes activos registrados, así que no puedo calcular el ingreso recurrente.")
    if k["obl_overdue"]["value"]:
        s.append(f"Atención: {k['obl_overdue']['value']} obligación(es) vencida(s) sin presentar.")
    if k["obl_urgent"]["value"]:
        s.append(f"{k['obl_urgent']['value']} obligación(es) vencen en los próximos 5 días.")
    if k["ar30_ratio"]["value"]:
        s.append(f"La cartera con más de 30 días equivale al {k['ar30_ratio']['value']:.0%} del ingreso mensual.")
    s.append(f"Pipeline abierto por {an.money(k['pipeline_value']['value'])} mensuales.")
    if k["stale_opps"]["value"]:
        s.append(f"{k['stale_opps']['value']} oportunidad(es) sin seguimiento vigente.")
    return s


class Orchestrator:
    def __init__(self, conn, user: dict, today: date | None = None):
        self.conn, self.user = conn, user
        self.today = today or date.today()
        self.actor = f"user:{user['username']}"
        self.settings = get_settings()

    # ------------------------------------------------------------ permisos
    def _check(self, action: str, agent: str) -> dict:
        return policy.decide(self.conn, action, AGENTS[agent]["max_autonomy"] if agent in AGENTS else 1, self.settings.max_autonomy)

    def _request_approval(self, task_id: int, action: str, payload: dict, reason: str) -> dict:
        cur = self.conn.execute(
            "INSERT INTO approvals (task_id, action, level, payload_json, reason, requested_by) VALUES (?,?,?,?,?,?)",
            (task_id, action, policy.ACTIONS.get(action, 4), json.dumps(payload, ensure_ascii=False), reason, self.actor))
        audit.log(self.conn, self.actor, "approval.request", f"approval:{cur.lastrowid}", {"action": action, "task": task_id})
        return {"approval_id": cur.lastrowid, "action": action, "reason": reason}

    # ------------------------------------------------------------ entrada principal
    def handle(self, text: str) -> dict:
        text = (text or "").strip()
        if not text:
            return {"status": "failed", "speech": "No recibí ninguna instrucción.", "detail": {}}
        if len(text) > 2000:
            text = text[:2000]
        intent, agents = classify(text)
        task = tasks.create(self.conn, f"Instrucción: {text[:80]}", self.actor, kind="command", agent="orquestador",
                            input_data={"text": text, "intent": intent, "agents": agents})
        tasks.transition(self.conn, task["id"], "running", "jarviz")
        self._remember("user", text)
        try:
            out = getattr(self, f"_i_{intent}")(text, task["id"])
            status = out.pop("_status", "completed")
            tasks.transition(self.conn, task["id"], status, "jarviz", result=out)
            out.update({"task_id": task["id"], "status": status, "intent": intent, "agents": agents})
        except Exception as e:  # la tarea queda en estado failed, con explicación y siguiente paso
            msg = str(e) or e.__class__.__name__
            tasks.transition(self.conn, task["id"], "failed", "jarviz", error=msg)
            out = {"task_id": task["id"], "status": "failed", "intent": intent, "agents": agents,
                   "speech": f"No pude completar la tarea: {msg}", "next_step": "Revisa el detalle en Tareas o reformula la instrucción.",
                   "detail": {}}
        self._remember("assistant", out.get("speech", ""))
        return out

    def _remember(self, role: str, content: str) -> None:
        self.conn.execute("INSERT INTO conversations (user_id, role, content) VALUES (?,?,?)", (self.user["id"], role, content[:4000]))

    # ------------------------------------------------------------ intenciones
    def _i_help(self, text, tid):
        active = [a for a in agents_summary() if a["status"] != "planificado"]
        planned = [a["name"] for a in agents_summary() if a["status"] == "planificado"]
        return {"speech": "Puedo darte el estado del negocio, prioridades de la semana, obligaciones, cartera, rentabilidad, "
                          "pipeline, oportunidades, riesgos, preparar propuestas y cierres, registrar prospectos, tareas y notas.",
                "detail": {"agentes_activos": [a["name"] for a in active], "agentes_planificados": planned,
                           "modo_ia": llm.available()}}

    def _i_status(self, text, tid):
        k = {x["id"]: x for x in an.kpis(self.conn, self.today)["kpis"]}
        risks = an.risk_review(self.conn, self.today)["findings"]
        speech = _speech_kpis(k)
        if risks:
            speech.append(f"Riesgo principal: {risks[0]['finding'].lower()}.")
        return {"speech": " ".join(speech), "detail": {"kpis": list(k.values()), "risks": risks,
                "demo_data": an.has_demo(self.conn)}, "sources": ["clients", "prospects", "invoices", "obligations", "time_entries"]}

    def _i_priorities(self, text, tid):
        r = automations.weekly_report(self.conn, self.today)
        return {"speech": "Prioridades: " + " ".join(r["priorities"][:4]), "detail": r, "sources": r["sources"]}

    def _i_weekly_review(self, text, tid):
        d = self._check("internal.save_memory", "ceo")
        r = automations.flow_weekly_review(self.conn, self.actor, self.today) if d["allowed"] else automations.weekly_report(self.conn, self.today)
        return {"speech": "Revisión semanal lista. " + " ".join(r["priorities"][:3]), "detail": r, "sources": r["sources"]}

    def _i_opportunities(self, text, tid):
        r = an.opportunities(self.conn, self.today)
        if not r["items"]:
            return {"speech": "Con los datos registrados no detecto oportunidades concretas. " + r["limits"], "detail": r}
        top = r["items"][:3]
        parts = [f"{i+1}. {o['type']}: {o['target']}" + (f", potencial {an.money(o['monthly_upside'])} al mes" if o["monthly_upside"] else "")
                 for i, o in enumerate(top)]
        return {"speech": "Oportunidades detectadas en tus datos: " + "; ".join(parts) + ". " + r["limits"], "detail": r}

    def _i_obligations(self, text, tid):
        ent = an.find_entity(self.conn, text)
        cid = ent["id"] if ent and ent["kind"] == "client" else None
        r = an.obligations_overview(self.conn, self.today, client_id=cid, horizon_days=30)
        if not r["items"]:
            return {"speech": "No hay obligaciones pendientes en los próximos 30 días según lo registrado.", "detail": r}
        over = [i for i in r["items"] if i["alert"] == "VENCIDA"]
        first = r["items"][0]
        s = f"Hay {len(r['items'])} obligación(es) en 30 días"
        s += f", {len(over)} vencida(s)" if over else ""
        s += f". La más próxima: {first['kind']} de {first['client']} el {first['due_date']}."
        return {"speech": s, "detail": r}

    def _i_receivables(self, text, tid):
        r = an.receivables(self.conn, self.today)
        b = r["buckets"]
        return {"speech": f"Cartera por cobrar {an.money(r['total'])}: al día {an.money(b['Al día'])}, más de 30 días {an.money(b['Más de 30'])}.",
                "detail": r}

    def _i_profitability(self, text, tid):
        r = an.profitability(self.conn, self.today)
        low = [i["name"] for i in r["items"] if i["state"] == "baja"]
        s = f"{len(r['items'])} cliente(s) activo(s). "
        s += ("Rentabilidad baja (menos de " + an.money(r["goal_rev_per_hour"]) + " por hora): " + ", ".join(low) + ".") if low else "Ninguno por debajo de la meta de ingreso por hora."
        return {"speech": s, "detail": r}

    def _i_pipeline(self, text, tid):
        r = an.pipeline(self.conn, self.today)
        stale = sum(1 for i in r["items"] if i["alert"] != "OK")
        return {"speech": f"{r['open']} oportunidad(es) abierta(s) por {an.money(r['value'])} mensuales; {stale} sin seguimiento vigente.", "detail": r}

    def _i_churn(self, text, tid):
        r = an.churn_risk(self.conn, self.today)
        if not r["items"]:
            return {"speech": "No detecto clientes en riesgo con los datos actuales.", "detail": r}
        return {"speech": "Clientes en riesgo: " + "; ".join(f"{i['client']} ({', '.join(i['reasons'])})" for i in r["items"][:3]) + ".", "detail": r}

    def _i_risks(self, text, tid):
        r = an.risk_review(self.conn, self.today)
        if not r["findings"]:
            return {"speech": "Sin hallazgos de riesgo en los datos registrados. Auditoría íntegra.", "detail": r}
        return {"speech": f"{len(r['findings'])} hallazgo(s). " + " ".join(f"{f['finding']}: {f['evidence']}." for f in r["findings"][:3]), "detail": r}

    def _i_system(self, text, tid):
        integ = audit.verify(self.conn)
        return {"speech": f"Sistema operativo. Modo IA {'activo' if llm.available() else 'desactivado (sin clave)'}; "
                          f"auditoría {'íntegra' if integ['ok'] else 'con inconsistencias'} ({integ['checked']} registros).",
                "detail": {"audit": integ, "llm": llm.available(), "agents": agents_summary()}}

    def _i_proposal(self, text, tid):
        ent = an.find_entity(self.conn, text)
        name, plan, segment = None, None, None
        if ent and ent["kind"] == "prospect":
            p = one(self.conn, "SELECT name, plan, segment FROM prospects WHERE id = ?", (ent["id"],))
            name, plan, segment = p["name"], p["plan"], p["segment"]
        elif ent:
            c = one(self.conn, "SELECT name, plan, segment FROM clients WHERE id = ?", (ent["id"],))
            name, plan, segment = c["name"], c["plan"], c["segment"]
        else:
            m = re.search(r"propuesta (?:comercial )?(?:para|a) (.+)$", text, re.I)
            name = m.group(1).strip(" .") if m else "prospecto sin nombre"
            segment = automations.detect_segment(text)
            plan = "Crecimiento" if re.search(r"tercerizar|outsourcing", an.norm(text)) else automations.PLAN_BY_SEGMENT.get(segment, "Empresa")
        r = an.draft_proposal(self.conn, name, plan, segment)
        return {"speech": f"Preparé un borrador de propuesta para {name}, plan {r['plan']} por {an.money(r['monthly_price'])} al mes. Queda para tu revisión; no se envía sin tu aprobación.",
                "detail": r}

    def _i_new_prospect(self, text, tid):
        d = self._check("internal.create_prospect", "ventas")
        m = re.search(r"(?:prospecto|cliente potencial)\s*(?:llamad[oa]|:)?\s*(.+)$", text, re.I)
        name = m.group(1) if m else ""
        contact = None
        cm = re.search(r"(?:tel[eé]fono|celular|contacto|correo)\s*:?\s*([\w@.+\- ]{5,})$", name, re.I)
        if cm:
            contact, name = cm.group(1).strip(), name[: cm.start()].strip(" ,")
        if not d["allowed"]:
            ap = self._request_approval(tid, "internal.create_prospect", {"name": name, "contact": contact}, d["reason"])
            return {"_status": "awaiting_approval", "speech": "Registrar prospectos supera la autonomía configurada; dejé la solicitud en Aprobaciones.", "detail": ap}
        r = automations.flow_new_prospect(self.conn, self.actor, name, self.today, contact=contact)
        if r["duplicate"]:
            return {"speech": r["message"], "detail": r}
        return {"speech": f"Registré a {name} como prospecto, segmento {r['segment']}, plan sugerido {r['recommended_plan']}. "
                          f"Creé la tarea de contacto para el {r['next_action']['date']} y un borrador de propuesta.", "detail": r}

    def _i_close(self, text, tid):
        ent = an.find_entity(self.conn, text)
        if not ent or ent["kind"] != "client":
            return {"_status": "failed", "speech": "¿De qué cliente? No encontré un cliente registrado con ese nombre.",
                    "detail": {"clientes": [c["name"] for c in rows(self.conn, "SELECT name FROM clients WHERE status='Activo'")]}}
        m = re.search(r"(20\d\d-\d\d)", text)
        prev = (self.today.replace(day=1) - __import__("datetime").timedelta(days=1))
        period = m.group(1) if m else prev.strftime("%Y-%m")
        d = self._check("internal.create_task", "contabilidad")
        if not d["allowed"]:
            ap = self._request_approval(tid, "internal.create_task", {"close": ent["name"], "period": period}, d["reason"])
            return {"_status": "awaiting_approval", "speech": "Crear las tareas del cierre requiere aprobación.", "detail": ap}
        r = automations.flow_close(self.conn, self.actor, ent["id"], period)
        miss = ", ".join(r["missing_documents"]) or "ninguno"
        return {"speech": f"Cierre {period} de {ent['name']}: {len(r['steps'])} pasos, {r['tasks_created']} tarea(s) nueva(s). "
                          f"Documentos faltantes: {miss}. Requiere tu validación profesional antes de cerrar.", "detail": r}

    def _i_create_task(self, text, tid):
        d = self._check("internal.create_task", "operaciones")
        title = re.sub(r"^(jarvi[sz],?\s*)?(crea|crear|agrega|agregar|nueva)( una)? tarea:?\s*|^recu[eé]rdame\s*", "", text, flags=re.I).strip()
        if len(title) < 3:
            raise ValueError("Necesito el texto de la tarea.")
        if not d["allowed"]:
            ap = self._request_approval(tid, "internal.create_task", {"title": title}, d["reason"])
            return {"_status": "awaiting_approval", "speech": "La tarea quedó pendiente de aprobación.", "detail": ap}
        m = re.search(r"(20\d\d-\d\d-\d\d)", title)
        t = tasks.create(self.conn, title, self.actor, kind="manual", agent="operaciones", due_date=m.group(1) if m else None)
        return {"speech": f"Tarea creada: {title}.", "detail": {"task": t}}

    def _i_save_memory(self, text, tid):
        content = re.sub(r"^(jarvi[sz],?\s*)?(anota|nota|recuerda que|guarda que|toma nota)( que)?:?\s*", "", text, flags=re.I)
        ent = an.find_entity(self.conn, content)
        if ent and ent["kind"] == "client":
            mid = memory.save(self.conn, "client", content, "dictado del usuario", self.actor, client_id=ent["id"])
        else:
            mid = memory.save(self.conn, "work", content, "dictado del usuario", self.actor)
        return {"speech": "Anotado." + (f" Lo asocié a {ent['name']}." if ent and ent["kind"] == "client" else ""), "detail": {"memory_id": mid}}

    def _i_external_action(self, text, tid):
        t = an.norm(text)
        action = next(a for p, a in EXTERNAL_MAP if re.search(p, t))
        d = self._check(action, "ceo")
        ap = self._request_approval(tid, action, {"instruction": text}, d["reason"])
        return {"_status": "awaiting_approval",
                "speech": "Esa acción es externa o irreversible: la dejé en tu bandeja de aprobaciones. No se ha ejecutado nada.",
                "detail": ap}

    def _i_unknown(self, text, tid):
        if llm.available():
            history = [{"role": r["role"], "content": r["content"]} for r in reversed(rows(
                self.conn, "SELECT role, content FROM conversations WHERE user_id = ? ORDER BY id DESC LIMIT 11 OFFSET 1", (self.user["id"],)))]
            while history and history[0]["role"] != "user":
                history.pop(0)
            r = llm.run(self.conn, text, history, self._tool, task_id=tid)
            return {"speech": r["answer"], "detail": {"mode": "ia", "tools_used": r["tools_used"]}}
        return {"_status": "completed", "speech": "No reconocí la instrucción. Puedes pedirme: estado del negocio, prioridades de la semana, "
                          "obligaciones, cartera, rentabilidad, pipeline, oportunidades, riesgos, una propuesta o un cierre.",
                "detail": {"mode": "local", "clarification_needed": True}}

    # ------------------------------------------------------------ herramientas para el modo IA
    def _tool(self, name: str, args: dict) -> dict:
        d = self.today
        if name == "get_kpis":
            return an.kpis(self.conn, d)
        if name == "get_obligations":
            return an.obligations_overview(self.conn, d, horizon_days=int(args.get("horizon_days", 30)))
        if name == "get_receivables":
            return an.receivables(self.conn, d)
        if name == "get_profitability":
            return an.profitability(self.conn, d)
        if name == "get_pipeline":
            return an.pipeline(self.conn, d)
        if name == "get_opportunities":
            return an.opportunities(self.conn, d)
        if name == "get_risks":
            return an.risk_review(self.conn, d)
        if name == "create_task":
            dec = self._check("internal.create_task", "operaciones")
            if not dec["allowed"]:
                return {"blocked": True, "reason": dec["reason"]}
            return tasks.create(self.conn, args["title"][:200], "jarviz:ia", agent="operaciones", due_date=args.get("due_date"))
        if name == "request_approval":
            if args.get("action") not in policy.ALWAYS_APPROVAL:
                return {"blocked": True, "reason": "Acción no permitida"}
            return self._request_approval(None, args["action"], {"description": args.get("description", "")[:500]}, "Solicitada por el modo IA")
        raise ValueError(f"Herramienta desconocida: {name}")


def decide_approval(conn, approval_id: int, approve: bool, actor: str) -> dict:
    """Solo el propietario decide. Las acciones externas no tienen integración: se marcan para ejecución manual."""
    ap = one(conn, "SELECT * FROM approvals WHERE id = ?", (approval_id,))
    if not ap:
        raise KeyError("Aprobación no existe")
    if ap["status"] != "pending":
        raise ValueError("La aprobación ya fue decidida")
    status = "approved" if approve else "rejected"
    conn.execute("UPDATE approvals SET status = ?, decided_by = ?, decided_at = datetime('now') WHERE id = ?", (status, actor, approval_id))
    audit.log(conn, actor, f"approval.{status}", f"approval:{approval_id}", {"action": ap["action"]})
    result = {"approval_id": approval_id, "status": status, "executed": False}
    payload = json.loads(ap["payload_json"])
    if approve and ap["action"] == "internal.create_task" and payload.get("title"):
        t = tasks.create(conn, payload["title"], actor, agent="operaciones")
        result.update(executed=True, task_id=t["id"])
    elif approve:
        result["note"] = "Aprobado. No hay integración externa configurada: ejecuta la acción manualmente y regístrala."
    if ap["task_id"]:
        t = tasks.get(conn, ap["task_id"])
        if t and t["status"] == "awaiting_approval":
            tasks.transition(conn, ap["task_id"], "completed" if approve else "cancelled", actor, result=result)
    return result


def run_scheduled(conn, today: date | None = None) -> dict:
    """Proceso programado (cron): alertas + vigilancia de obligaciones + retención de conversaciones."""
    today = today or date.today()
    a = alerts.run(conn, today)
    w = automations.flow_obligation_watch(conn, "jarviz:scheduler", today)
    purged = memory.purge_expired_conversations(conn, get_settings().conversation_retention_days)
    audit.log(conn, "jarviz:scheduler", "scheduled.run", None, {"alerts": a["new"], "tasks": w["tasks_created"], "purged": purged})
    return {"alerts_new": a["new"], "obligation_tasks": w["tasks_created"], "conversations_purged": purged}
