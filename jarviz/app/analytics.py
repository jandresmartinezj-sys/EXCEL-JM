"""Funciones de negocio sobre los datos reales de la BD (sin inventar cifras).

Cada resultado declara su fuente, su periodo y si contiene datos de demostración.
"""
import re
import unicodedata
from datetime import date, timedelta

from .db import one, rows

DEFAULT_GOALS = {
    "mrr": 15_000_000, "new_clients_month": 3, "close_rate": 0.30, "ar30_ratio": 0.05,
    "revenue_per_hour": 80_000, "max_concentration": 0.20, "capacity_hours": 140,
}
PLAN_PRICES = {"Básico": 450_000, "Empresa": 750_000, "Crecimiento": 1_100_000, "CFO fraccional": 2_200_000}
PLAN_SCOPE = {
    "Básico": "Contabilidad mensual, declaraciones tributarias y facturación electrónica.",
    "Empresa": "Básico + nómina electrónica, retenciones, información exógena e informe mensual.",
    "Crecimiento": "Empresa + flujo de caja, presupuesto, indicadores y reunión mensual de resultados.",
    "CFO fraccional": "Crecimiento + flujo de caja a 13 semanas, gestión de cartera e inventario, "
                      "análisis de precios y márgenes y acompañamiento en decisiones financieras.",
}
CLOSED_STAGES = ("7 Ganado", "8 Perdido")


def norm(text: str) -> str:
    t = unicodedata.normalize("NFD", text or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", t).strip()


def month_bounds(today: date) -> tuple[str, str]:
    start = today.replace(day=1)
    nxt = (start + timedelta(days=32)).replace(day=1)
    return start.isoformat(), nxt.isoformat()


def has_demo(conn) -> bool:
    for t in ("clients", "prospects", "obligations", "invoices", "time_entries"):
        if one(conn, f"SELECT 1 x FROM {t} WHERE is_demo = 1 LIMIT 1"):
            return True
    return False


def money(v: float | None) -> str:
    return "N/D" if v is None else "$" + f"{v:,.0f}".replace(",", ".")


# ---------------------------------------------------------------- búsqueda de entidades
STOP = {"de", "la", "el", "los", "las", "sas", "s", "a", "y", "del", "para", "cliente", "empresa", "ltda", "demo"}


def find_entity(conn, text: str) -> dict | None:
    """Busca un cliente o prospecto mencionado en el texto.

    Puntaje = palabras significativas coincidentes / min(palabras del nombre, 2).
    Si dos entidades distintas empatan con el mejor puntaje, devuelve None (pedir aclaración).
    """
    words = {w for w in norm(text).split() if w not in STOP and len(w) > 2}
    if not words:
        return None
    scored = []
    for kind, sql in (("client", "SELECT id, name FROM clients"), ("prospect", "SELECT id, name FROM prospects")):
        for r in rows(conn, sql):
            nw = {w for w in norm(r["name"]).split() if w not in STOP and len(w) > 2}
            if nw:
                score = min(1.0, len(words & nw) / min(len(nw), 2))
                if score >= 0.5:
                    scored.append((score, kind == "client", norm(r["name"]), {"kind": kind, "id": r["id"], "name": r["name"]}))
    if not scored:
        return None
    scored.sort(key=lambda x: (-x[0], not x[1]))
    top = scored[0]
    rivals = [s for s in scored[1:] if s[0] == top[0] and s[2] != top[2]]
    return None if rivals else top[3]


# ---------------------------------------------------------------- indicadores
def _kpi(id_, name, value, unit, definition, formula, source, owner, goal=None, better=None, missing=None):
    state = None
    if value is not None and goal is not None and better:
        if better == "higher":
            state = "verde" if value >= goal else ("amarillo" if value >= goal * 0.7 else "rojo")
        else:
            state = "verde" if value <= goal else ("amarillo" if value <= goal * 1.5 + 1e-9 else "rojo")
    return {"id": id_, "name": name, "value": value, "unit": unit, "definition": definition, "formula": formula,
            "source": source, "owner": owner, "goal": goal, "state": state, "available": value is not None,
            "missing": missing if value is None else None}


def kpis(conn, today: date, goals: dict | None = None) -> dict:
    g = {**DEFAULT_GOALS, **(goals or {})}
    m0, m1 = month_bounds(today)
    t = today.isoformat()
    active = rows(conn, "SELECT id, name, monthly_fee FROM clients WHERE status = 'Activo'")
    mrr = sum(c["monthly_fee"] for c in active) if active else None
    n_active = len(active)
    hours = one(conn, "SELECT SUM(hours) h FROM time_entries WHERE date >= ? AND date < ?", (m0, m1))["h"]
    ar = one(conn, "SELECT SUM(amount - paid) s FROM invoices WHERE amount - paid > 0")["s"]
    ar30 = one(conn, "SELECT SUM(amount - paid) s FROM invoices WHERE amount - paid > 0 AND due_date < date(?, '-30 days')", (t,))["s"] or 0
    n_inv = one(conn, "SELECT COUNT(*) n FROM invoices")["n"]
    new_c = one(conn, "SELECT COUNT(*) n FROM clients WHERE start_date >= ? AND start_date < ?", (m0, m1))["n"]
    open_p = rows(conn, "SELECT monthly_value, next_step_date FROM prospects WHERE stage NOT IN (?, ?)", CLOSED_STAGES)
    won = one(conn, "SELECT COUNT(*) n FROM prospects WHERE stage = '7 Ganado'")["n"]
    lost = one(conn, "SELECT COUNT(*) n FROM prospects WHERE stage = '8 Perdido'")["n"]
    stale = sum(1 for p in open_p if not p["next_step_date"] or p["next_step_date"] < t)
    obl_over = one(conn, "SELECT COUNT(*) n FROM obligations WHERE status <> 'Presentada' AND due_date < ?", (t,))["n"]
    obl_urg = one(conn, "SELECT COUNT(*) n FROM obligations WHERE status <> 'Presentada' AND due_date >= ? AND due_date <= date(?, '+5 days')", (t, t))["n"]
    n_obl = one(conn, "SELECT COUNT(*) n FROM obligations")["n"]
    nps_rows = [c["nps"] for c in rows(conn, "SELECT nps FROM clients WHERE status = 'Activo' AND nps IS NOT NULL")]
    tasks_over = one(conn, "SELECT COUNT(*) n FROM tasks WHERE status IN ('pending','running') AND due_date < ?", (t,))["n"]
    appr = one(conn, "SELECT COUNT(*) n FROM approvals WHERE status = 'pending'")["n"]
    llm = one(conn, "SELECT SUM(input_tokens) i, SUM(output_tokens) o, SUM(cache_read_tokens) c FROM llm_usage WHERE ts >= ?", (m0,))
    alerts_open = one(conn, "SELECT COUNT(*) n FROM alerts WHERE status = 'open'")["n"]

    conc = None
    if mrr:
        conc = max(c["monthly_fee"] for c in active) / mrr
    out = [
        _kpi("mrr", "Ingreso mensual recurrente (MRR)", mrr, "COP",
             "Suma de honorarios mensuales de clientes activos.", "Σ clients.monthly_fee (status=Activo)",
             "clients", "Finanzas", g["mrr"], "higher", "Registrar clientes activos con su valor mensual."),
        _kpi("active_clients", "Clientes activos", n_active, "n", "Clientes con estado Activo.",
             "COUNT(clients status=Activo)", "clients", "Dirección"),
        _kpi("ticket", "Ticket promedio", (mrr / n_active) if mrr and n_active else None, "COP",
             "Honorario mensual promedio por cliente activo.", "MRR / clientes activos", "clients", "Finanzas",
             missing="Requiere clientes activos."),
        _kpi("ar_total", "Cartera por cobrar", ar if n_inv else None, "COP", "Saldo pendiente de facturas emitidas.",
             "Σ (amount − paid) con saldo > 0", "invoices", "Finanzas", missing="Registrar facturas emitidas."),
        _kpi("ar30_ratio", "Cartera > 30 días / MRR", (ar30 / mrr) if (mrr and n_inv) else None, "%",
             "Saldo con más de 30 días de vencido sobre el MRR.", "Σ saldo(due_date < hoy−30) / MRR",
             "invoices, clients", "Finanzas", g["ar30_ratio"], "lower", "Requiere facturas y MRR."),
        _kpi("hours_month", "Horas registradas en el mes", hours, "h", "Horas de trabajo registradas en el mes.",
             "Σ time_entries.hours (mes)", "time_entries", "Operaciones", missing="Registrar horas por cliente."),
        _kpi("rev_per_hour", "Ingreso por hora", (mrr / hours) if (mrr and hours) else None, "COP/h",
             "Ingreso recurrente por hora trabajada en el mes.", "MRR / horas del mes", "clients, time_entries",
             "Finanzas", g["revenue_per_hour"], "higher", "Requiere MRR y horas registradas."),
        _kpi("capacity", "Uso de capacidad", (hours / g["capacity_hours"]) if hours else None, "%",
             "Horas del mes sobre la capacidad facturable.", "horas / capacidad mensual", "time_entries",
             "Operaciones", 0.8, "lower", "Registrar horas."),
        _kpi("concentration", "Concentración del cliente mayor", conc, "%",
             "Participación del cliente más grande en el MRR.", "max(monthly_fee) / MRR", "clients", "Dirección",
             g["max_concentration"], "lower", "Requiere clientes activos."),
        _kpi("new_clients", "Clientes nuevos en el mes", new_c, "n", "Clientes con fecha de inicio en el mes.",
             "COUNT(start_date en mes)", "clients", "Comercial", g["new_clients_month"], "higher"),
        _kpi("pipeline_value", "Valor mensual del pipeline abierto", sum(p["monthly_value"] for p in open_p), "COP",
             "Valor mensual de oportunidades abiertas.", "Σ prospects.monthly_value (etapas 1–6)", "prospects", "Comercial"),
        _kpi("close_rate", "Tasa de cierre", (won / (won + lost)) if (won + lost) else None, "%",
             "Ganadas sobre cerradas (ganadas + perdidas).", "ganados / (ganados + perdidos)", "prospects",
             "Comercial", g["close_rate"], "higher", "Se necesita al menos una oportunidad cerrada."),
        _kpi("stale_opps", "Oportunidades sin próximo paso vigente", stale, "n",
             "Oportunidades abiertas sin fecha o con fecha vencida.", "COUNT(abiertas con next_step_date vacía o < hoy)",
             "prospects", "Comercial", 0, "lower"),
        _kpi("obl_overdue", "Obligaciones vencidas sin presentar", obl_over if n_obl else None, "n",
             "Obligaciones con fecha pasada y estado distinto de Presentada.", "COUNT(due_date < hoy, status≠Presentada)",
             "obligations", "Tributario", 0, "lower", "Cargar el calendario de obligaciones por cliente."),
        _kpi("obl_urgent", "Obligaciones urgentes (≤ 5 días)", obl_urg if n_obl else None, "n",
             "Obligaciones que vencen en los próximos 5 días.", "COUNT(hoy ≤ due_date ≤ hoy+5)", "obligations",
             "Tributario", missing="Cargar obligaciones."),
        _kpi("nps", "NPS", (round((sum(1 for x in nps_rows if x >= 9) - sum(1 for x in nps_rows if x <= 6)) / len(nps_rows) * 100)
                           if nps_rows else None), "pts", "Promotores (9–10) menos detractores (0–6).",
             "(%promotores − %detractores) × 100", "clients.nps", "Servicio", 50, "higher",
             "Registrar la encuesta de satisfacción de clientes activos."),
        _kpi("tasks_overdue", "Tareas vencidas", tasks_over, "n", "Tareas abiertas con fecha límite pasada.",
             "COUNT(tasks abiertas con due_date < hoy)", "tasks", "Operaciones", 0, "lower"),
        _kpi("approvals_pending", "Aprobaciones pendientes", appr, "n", "Acciones esperando decisión humana.",
             "COUNT(approvals pending)", "approvals", "Dirección"),
        _kpi("alerts_open", "Alertas abiertas", alerts_open, "n", "Alertas proactivas sin atender.",
             "COUNT(alerts open)", "alerts", "Dirección"),
        _kpi("ai_tokens", "Uso de IA en el mes (tokens)", ((llm["i"] or 0) + (llm["o"] or 0)) if llm["i"] is not None else None,
             "tokens", "Tokens consumidos en llamadas al modelo en el mes.", "Σ input + output tokens (mes)",
             "llm_usage", "Tecnología", missing="Sin uso registrado (modo local o sin clave API)."),
    ]
    return {"as_of": t, "period": f"{m0} a {m1}", "demo_data": has_demo(conn), "kpis": out}


# ---------------------------------------------------------------- vistas por área
def obligations_overview(conn, today: date, client_id: int | None = None, horizon_days: int = 15) -> dict:
    t = today.isoformat()
    sql = """SELECT o.id, c.name client, o.client_id, o.kind, o.period, o.due_date, o.status, o.source_note,
                    CAST(julianday(o.due_date) - julianday(?) AS INTEGER) days_left
             FROM obligations o JOIN clients c ON c.id = o.client_id
             WHERE o.status <> 'Presentada' AND o.due_date <= date(?, ?)"""
    params = [t, t, f"+{horizon_days} days"]
    if client_id:
        sql += " AND o.client_id = ?"
        params.append(client_id)
    items = rows(conn, sql + " ORDER BY o.due_date", params)
    for i in items:
        i["alert"] = "VENCIDA" if i["days_left"] < 0 else ("URGENTE" if i["days_left"] <= 5 else "PRÓXIMA")
    return {"as_of": t, "horizon_days": horizon_days, "items": items,
            "note": "Las fechas provienen de lo cargado en la tabla de obligaciones; deben venir del calendario oficial vigente (DIAN / municipio)."}


def receivables(conn, today: date) -> dict:
    t = today.isoformat()
    items = rows(conn, """SELECT i.number, c.name client, i.issue_date, i.due_date, i.amount, i.paid,
                                 i.amount - i.paid balance, CAST(julianday(?) - julianday(i.due_date) AS INTEGER) days_late
                          FROM invoices i JOIN clients c ON c.id = i.client_id
                          WHERE i.amount - i.paid > 0 ORDER BY i.due_date""", (t,))
    buckets = {"Al día": 0.0, "1-15": 0.0, "16-30": 0.0, "Más de 30": 0.0}
    for i in items:
        d = i["days_late"]
        k = "Al día" if d <= 0 else ("1-15" if d <= 15 else ("16-30" if d <= 30 else "Más de 30"))
        i["bucket"] = k
        buckets[k] += i["balance"]
    return {"as_of": t, "total": sum(buckets.values()), "buckets": buckets, "items": items, "source": "invoices"}


def profitability(conn, today: date) -> dict:
    m0, m1 = month_bounds(today)
    items = rows(conn, """SELECT c.id, c.name, c.plan, c.monthly_fee,
                                 COALESCE((SELECT SUM(hours) FROM time_entries te WHERE te.client_id = c.id AND te.date >= ? AND te.date < ?), 0) hours
                          FROM clients c WHERE c.status = 'Activo' ORDER BY c.monthly_fee DESC""", (m0, m1))
    goal = DEFAULT_GOALS["revenue_per_hour"]
    for i in items:
        i["rev_per_hour"] = (i["monthly_fee"] / i["hours"]) if i["hours"] else None
        i["state"] = ("sin horas" if i["rev_per_hour"] is None else
                      "baja" if i["rev_per_hour"] < goal else "ajustada" if i["rev_per_hour"] < goal * 1.25 else "sana")
    return {"period": f"{m0} a {m1}", "goal_rev_per_hour": goal, "items": items,
            "formula": "honorario mensual / horas registradas en el mes", "source": "clients, time_entries"}


def pipeline(conn, today: date) -> dict:
    t = today.isoformat()
    items = rows(conn, """SELECT id, name, segment, channel, stage, plan, monthly_value, next_step, next_step_date
                          FROM prospects WHERE stage NOT IN (?, ?) ORDER BY stage DESC, monthly_value DESC""", CLOSED_STAGES)
    for i in items:
        i["alert"] = "SIN FECHA" if not i["next_step_date"] else ("VENCIDO" if i["next_step_date"] < t else "OK")
    by_stage: dict = {}
    for i in items:
        by_stage.setdefault(i["stage"], {"n": 0, "value": 0})
        by_stage[i["stage"]]["n"] += 1
        by_stage[i["stage"]]["value"] += i["monthly_value"]
    return {"as_of": t, "open": len(items), "value": sum(i["monthly_value"] for i in items), "by_stage": by_stage, "items": items}


def churn_risk(conn, today: date) -> dict:
    m0, m1 = month_bounds(today)
    t = today.isoformat()
    out = []
    for c in rows(conn, "SELECT id, name, risk, nps FROM clients WHERE status = 'Activo'"):
        reasons = []
        if c["risk"] == "Alto":
            reasons.append("riesgo marcado como Alto")
        if c["nps"] is not None and c["nps"] <= 6:
            reasons.append(f"satisfacción baja (NPS {c['nps']})")
        late = one(conn, "SELECT SUM(amount - paid) s FROM invoices WHERE client_id = ? AND amount - paid > 0 AND due_date < ?", (c["id"], t))["s"]
        if late:
            reasons.append(f"pagos atrasados por {money(late)}")
        h = one(conn, "SELECT SUM(hours) h FROM time_entries WHERE client_id = ? AND date >= ? AND date < ?", (c["id"], m0, m1))["h"]
        if not h:
            reasons.append("sin trabajo registrado este mes (posible falta de seguimiento)")
        if reasons:
            out.append({"client": c["name"], "client_id": c["id"], "reasons": reasons, "score": len(reasons)})
    return {"as_of": t, "items": sorted(out, key=lambda x: -x["score"])}


def opportunities(conn, today: date) -> dict:
    """Oportunidades derivadas SOLO de datos internos. No es investigación de mercado externa."""
    ops = []
    prof = {p["id"]: p for p in profitability(conn, today)["items"]}
    for c in rows(conn, "SELECT id, name, plan, monthly_fee, risk FROM clients WHERE status = 'Activo'"):
        p = prof.get(c["id"])
        if p and p["state"] == "baja" and c["plan"] in ("Básico", "Empresa"):
            nxt = "Empresa" if c["plan"] == "Básico" else "Crecimiento"
            gain = PLAN_PRICES[nxt] - c["monthly_fee"]
            ops.append({"type": "Subir de plan / reajustar alcance", "target": c["name"], "monthly_upside": gain,
                        "evidence": f"Ingreso por hora {money(p['rev_per_hour'])} < meta {money(DEFAULT_GOALS['revenue_per_hour'])} con {p['hours']:.1f} h en el mes.",
                        "confidence": "media", "next_action": f"Revisar el volumen real y proponer el plan {nxt} o cobrar el excedente."})
    for pr in rows(conn, "SELECT name, stage, plan, monthly_value FROM prospects WHERE stage IN ('4 Diagnóstico entregado','5 Propuesta enviada','6 Negociación') ORDER BY monthly_value DESC"):
        ops.append({"type": "Cierre de oportunidad avanzada", "target": pr["name"], "monthly_upside": pr["monthly_value"],
                    "evidence": f"Etapa {pr['stage']}, plan {pr['plan'] or 'sin definir'}.", "confidence": "media",
                    "next_action": "Agendar seguimiento de cierre y resolver objeciones."})
    seg = rows(conn, """SELECT segment, COUNT(*) n, SUM(monthly_fee) v FROM clients WHERE status='Activo' AND segment IS NOT NULL
                        GROUP BY segment ORDER BY v DESC LIMIT 1""")
    if seg and seg[0]["n"] >= 2:
        ops.append({"type": "Replicar el segmento que más factura", "target": seg[0]["segment"], "monthly_upside": None,
                    "evidence": f"{seg[0]['n']} clientes activos suman {money(seg[0]['v'])}/mes.", "confidence": "baja",
                    "next_action": "Pedir referidos en ese segmento y crear contenido específico."})
    ops.sort(key=lambda o: -(o["monthly_upside"] or 0))
    return {"as_of": today.isoformat(), "items": ops,
            "limits": "Basado solo en datos internos de JARVIZ. La investigación de mercado externa requiere el modo IA con búsqueda web y debe citar fuentes."}


def risk_review(conn, today: date) -> dict:
    from .audit import verify
    k = {x["id"]: x for x in kpis(conn, today)["kpis"]}
    findings = []

    def add(sev, what, evidence, rec):
        findings.append({"severity": sev, "finding": what, "evidence": evidence, "recommendation": rec})

    if k["obl_overdue"]["value"]:
        add("alta", "Obligaciones vencidas sin presentar", f"{k['obl_overdue']['value']} obligación(es)", "Presentar de inmediato y evaluar sanción/intereses; documentar causa.")
    if k["concentration"]["value"] and k["concentration"]["value"] > DEFAULT_GOALS["max_concentration"]:
        add("media", "Concentración de ingresos", f"Cliente mayor = {k['concentration']['value']:.0%} del MRR", "Priorizar captación para bajar del 20%.")
    if k["ar30_ratio"]["value"] and k["ar30_ratio"]["value"] > DEFAULT_GOALS["ar30_ratio"]:
        add("media", "Cartera vencida > 30 días", f"{k['ar30_ratio']['value']:.0%} del MRR", "Aplicar la política de suspensión a 15 días y gestionar el cobro.")
    if k["capacity"]["value"] and k["capacity"]["value"] > 0.8:
        add("media", "Capacidad por encima del 80%", f"{k['capacity']['value']:.0%}", "Evaluar la contratación de un auxiliar (ver 09-talento).")
    old_appr = one(conn, "SELECT COUNT(*) n FROM approvals WHERE status='pending' AND created_at < datetime('now','-2 days')")["n"]
    if old_appr:
        add("baja", "Aprobaciones sin decidir > 48 h", f"{old_appr}", "Revisar la bandeja de aprobaciones.")
    integ = verify(conn)
    if not integ["ok"]:
        add("alta", "Integridad del registro de auditoría comprometida", f"Cadena rota en el id {integ['broken_at_id']}", "Investigar el acceso directo a la base de datos; restaurar desde la copia de seguridad.")
    return {"as_of": today.isoformat(), "findings": findings, "audit_integrity": integ,
            "note": "Una anomalía no es un fraude confirmado: requiere verificación profesional."}


SOP_CLOSE = [
    ("Recibir soportes del mes (facturas, extractos, nómina)", ["facturas", "extracto", "nomina"]),
    ("Registrar y causar; generar documento soporte de compras a no obligados", []),
    ("Conciliar bancos al 100%", ["extracto"]),
    ("Transmitir nómina electrónica (antes del día 10)", ["nomina"]),
    ("Cruzar IVA generado vs. ventas gravadas", []),
    ("Cruzar retenciones practicadas vs. declaradas", []),
    ("Revisar terceros con saldos contrarios a su naturaleza", []),
    ("Revisión de calidad por segunda persona o reposo de 24 h", []),
    ("Informe mensual con semáforo y reunión con el cliente", []),
]


def close_checklist(conn, client_id: int, period: str) -> dict:
    docs = rows(conn, "SELECT title, kind FROM documents WHERE client_id = ? AND (period = ? OR period IS NULL)", (client_id, period))
    have = {norm(d["kind"] or d["title"]) for d in docs}
    steps, missing = [], set()
    for step, needed in SOP_CLOSE:
        miss = [n for n in needed if not any(n in h for h in have)]
        missing.update(miss)
        steps.append({"step": step, "missing_documents": miss})
    return {"client_id": client_id, "period": period, "documents_found": len(docs), "steps": steps,
            "missing_documents": sorted(missing), "requires": "Validación profesional del contador antes de cerrar.",
            "source": "SOP-02 (ecosistema/04-operaciones.md) + documentos registrados"}


def draft_proposal(conn, name: str, plan: str | None, segment: str | None) -> dict:
    plan = plan if plan in PLAN_PRICES else "Empresa"
    price = PLAN_PRICES[plan]
    text = f"""PROPUESTA DE SERVICIOS — BORRADOR PARA REVISIÓN
Para: {name}{f' · Segmento: {segment}' if segment else ''}

1. Situación: pendiente del diagnóstico financiero (plantilla diagnostico-financiero-pyme.xlsx). No se incluyen cifras del cliente porque no existen en JARVIZ.
2. Plan recomendado: {plan}. Incluye: {PLAN_SCOPE[plan]}
3. Cómo trabajaremos: semana 1 recepción de información y accesos; semanas 2–4 puesta al día; cada mes cierre, declaraciones a tiempo e informe con semáforo; mes 3 revisión de resultados.
4. Inversión: {money(price)} mensuales, pago anticipado del día 1 al 5. Valores antes de IVA si aplica. Precio de lista interno (hipótesis por validar).
5. Próximo paso: aceptación, primer pago y envío de información.
Condiciones sujetas a contrato y carta de encargo (legal/)."""
    return {"plan": plan, "monthly_price": price, "text": text, "status": "borrador",
            "warning": "No se envía al cliente sin aprobación (acción externa, nivel 4)."}
