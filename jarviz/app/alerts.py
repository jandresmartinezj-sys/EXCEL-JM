"""Alertas proactivas por reglas (se ejecutan por evento o programador). Deduplicadas por huella."""
from datetime import date

from . import audit
from .analytics import DEFAULT_GOALS, kpis, money
from .db import rows


def _upsert(conn, a: dict) -> bool:
    cur = conn.execute(
        """INSERT OR IGNORE INTO alerts (rule, fingerprint, severity, title, why, evidence, impact, confidence, action, decision, client_id)
           VALUES (:rule, :fingerprint, :severity, :title, :why, :evidence, :impact, :confidence, :action, :decision, :client_id)""",
        {"client_id": None, **a})
    return cur.rowcount == 1


def run(conn, today: date, actor: str = "jarviz:alerts") -> dict:
    t = today.isoformat()
    new = []

    for o in rows(conn, """SELECT o.id, o.kind, o.period, o.due_date, o.client_id, c.name,
                                  CAST(julianday(o.due_date) - julianday(?) AS INTEGER) d
                           FROM obligations o JOIN clients c ON c.id = o.client_id
                           WHERE o.status <> 'Presentada' AND o.due_date <= date(?, '+5 days')""", (t, t)):
        overdue = o["d"] < 0
        when = "VENCIDA" if overdue else f"vence en {o['d']} día(s)"
        a = {"rule": "obligation_due", "fingerprint": f"obl:{o['id']}:{'over' if overdue else 'soon'}",
             "severity": "alta", "client_id": o["client_id"],
             "title": f"{o['kind']} {o['period'] or ''} de {o['name']} {when}",
             "why": "Un incumplimiento genera sanciones e intereses para el cliente y riesgo profesional.",
             "evidence": f"Obligación #{o['id']} con vencimiento {o['due_date']} y estado distinto de Presentada.",
             "impact": "Sanción por extemporaneidad, intereses y pérdida de confianza.",
             "confidence": "alta (dato registrado; verificar la fecha contra el calendario oficial)",
             "action": "Preparar, enviar al cliente para aprobación y presentar.",
             "decision": "Aprobar la presentación cuando el borrador esté listo."}
        if _upsert(conn, a):
            new.append(a)

    for p in rows(conn, """SELECT id, name, stage, monthly_value, next_step_date FROM prospects
                           WHERE stage NOT IN ('7 Ganado','8 Perdido') AND (next_step_date IS NULL OR next_step_date < ?)""", (t,)):
        a = {"rule": "stale_opportunity", "fingerprint": f"opp:{p['id']}:{p['next_step_date']}", "severity": "media",
             "title": f"Oportunidad sin seguimiento: {p['name']}",
             "why": "Una oportunidad sin próximo paso se enfría y se pierde.",
             "evidence": f"Etapa {p['stage']}, próximo paso {p['next_step_date'] or 'sin fecha'}.",
             "impact": f"Ingreso potencial de {money(p['monthly_value'])}/mes.", "confidence": "alta",
             "action": "Contactar y registrar el próximo paso con fecha.", "decision": "¿Seguir o marcar como perdida?"}
        if _upsert(conn, a):
            new.append(a)

    for i in rows(conn, """SELECT i.id, i.number, c.name, i.client_id, i.amount - i.paid bal,
                                  CAST(julianday(?) - julianday(i.due_date) AS INTEGER) d
                           FROM invoices i JOIN clients c ON c.id = i.client_id
                           WHERE i.amount - i.paid > 0 AND i.due_date < date(?, '-15 days')""", (t, t)):
        a = {"rule": "receivable_late", "fingerprint": f"inv:{i['id']}:{'30' if i['d'] > 30 else '15'}",
             "severity": "alta" if i["d"] > 30 else "media", "client_id": i["client_id"],
             "title": f"Factura {i['number']} de {i['name']} con {i['d']} días de mora",
             "why": "La política de la firma suspende el servicio a los 15 días de atraso.",
             "evidence": f"Saldo {money(i['bal'])}.", "impact": "Caja de la firma y riesgo de incobrable.",
             "confidence": "alta", "action": "Gestionar el cobro; aplicar la suspensión según el contrato.",
             "decision": "¿Suspender el servicio o acordar un plan de pago?"}
        if _upsert(conn, a):
            new.append(a)

    k = {x["id"]: x for x in kpis(conn, today)["kpis"]}
    conc = k["concentration"]["value"]
    if conc and conc > DEFAULT_GOALS["max_concentration"]:
        a = {"rule": "concentration", "fingerprint": f"conc:{t[:7]}", "severity": "media",
             "title": f"Concentración de ingresos: el cliente mayor pesa {conc:.0%} del MRR",
             "why": "Perder ese cliente afectaría gravemente la caja.", "evidence": "Cálculo: max(monthly_fee)/MRR sobre clientes activos.",
             "impact": "Riesgo de liquidez.", "confidence": "alta",
             "action": "Priorizar la captación de clientes del mismo tamaño.", "decision": "Ajustar las metas comerciales del mes."}
        if _upsert(conn, a):
            new.append(a)

    for c in rows(conn, "SELECT id, name, risk FROM clients WHERE status = 'Activo' AND risk = 'Alto'"):
        a = {"rule": "client_risk", "fingerprint": f"risk:{c['id']}:{t[:7]}", "severity": "media", "client_id": c["id"],
             "title": f"Cliente en riesgo alto: {c['name']}", "why": "Riesgo de abandono o de incumplimiento.",
             "evidence": "Campo de riesgo marcado como Alto.", "impact": "Pérdida de ingreso recurrente.", "confidence": "media",
             "action": "Llamada del contador titular en 48 h.", "decision": "Definir un plan de retención."}
        if _upsert(conn, a):
            new.append(a)

    if new:  # solo deja traza cuando hay hallazgos nuevos (evita ruido en cada consulta del tablero)
        audit.log(conn, actor, "alerts.run", None, {"new": len(new)})
    return {"new": len(new), "alerts": new}


def open_alerts(conn, limit: int = 50) -> list[dict]:
    return rows(conn, """SELECT * FROM alerts WHERE status = 'open'
                         ORDER BY CASE severity WHEN 'alta' THEN 0 WHEN 'media' THEN 1 ELSE 2 END, id DESC LIMIT ?""", (limit,))
