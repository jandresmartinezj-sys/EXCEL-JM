"""Importa el centro de control de Excel (plantillas/centro-de-control.xlsx) a JARVIZ.

Solo importa las columnas de entrada (no las calculadas). Idempotente por nombre/número.
Con demo=True marca los registros como demostración (la plantilla trae datos ficticios).
"""
from datetime import date, datetime

from openpyxl import load_workbook

from . import audit
from .db import one


def _d(v):
    if isinstance(v, datetime):
        return v.date().isoformat()
    if isinstance(v, date):
        return v.isoformat()
    return v or None


def import_excel(conn, path: str, demo: bool = False) -> dict:
    wb = load_workbook(path, data_only=False, read_only=True)
    flag = 1 if demo else 0
    n = {"clients": 0, "prospects": 0, "obligations": 0, "invoices": 0, "time_entries": 0, "skipped": 0}

    def cid(name):
        r = one(conn, "SELECT id FROM clients WHERE name = ?", (name,))
        return r["id"] if r else None

    for r in wb["Clientes"].iter_rows(min_row=2, values_only=True):
        name = r[0]
        if not name or cid(name):
            continue
        conn.execute("""INSERT INTO clients (name, nit, segment, plan, monthly_fee, start_date, status, risk, nps, is_demo)
                        VALUES (?,?,?,?,?,?,?,?,?,?)""",
                     (name, str(r[1] or ""), r[2], r[3], float(r[4] or 0), _d(r[5]), r[6] or "Activo", r[7] or "Bajo",
                      int(r[8]) if isinstance(r[8], (int, float)) else None, flag))
        n["clients"] += 1
    for r in wb["Pipeline"].iter_rows(min_row=2, values_only=True):
        if not r[1] or one(conn, "SELECT 1 x FROM prospects WHERE name = ?", (r[1],)):
            continue
        conn.execute("""INSERT INTO prospects (created_at, name, segment, channel, contact, stage, plan, next_step, next_step_date, lost_reason, is_demo)
                        VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                     (_d(r[0]) or date.today().isoformat(), r[1], r[2], r[3], r[4], r[5] or "1 Prospecto", r[6], r[8], _d(r[9]), r[11], flag))
        n["prospects"] += 1
    conn.execute("""UPDATE prospects SET monthly_value = CASE plan WHEN 'Básico' THEN 450000 WHEN 'Empresa' THEN 750000
                    WHEN 'Crecimiento' THEN 1100000 WHEN 'CFO fraccional' THEN 2200000 ELSE monthly_value END WHERE monthly_value = 0""")
    for r in wb["Obligaciones"].iter_rows(min_row=2, values_only=True):
        c = cid(r[0]) if r[0] else None
        if not c or not r[3]:
            n["skipped"] += 1 if r[0] else 0
            continue
        if one(conn, "SELECT 1 x FROM obligations WHERE client_id = ? AND kind = ? AND period IS ? AND due_date = ?", (c, r[1], r[2], _d(r[3]))):
            continue
        conn.execute("""INSERT INTO obligations (client_id, kind, period, due_date, status, owner, reference, source_note, is_demo)
                        VALUES (?,?,?,?,?,?,?,?,?)""", (c, r[1], r[2], _d(r[3]), r[4] or "Pendiente", r[5], r[8], "Importado del centro de control", flag))
        n["obligations"] += 1
    for r in wb["Facturacion"].iter_rows(min_row=2, values_only=True):
        c = cid(r[1]) if r[1] else None
        if not c or not r[0] or one(conn, "SELECT 1 x FROM invoices WHERE number = ?", (r[0],)):
            continue
        issue = _d(r[2])
        due = date.fromordinal(date.fromisoformat(issue).toordinal() + 4).isoformat()
        conn.execute("INSERT INTO invoices (number, client_id, issue_date, due_date, amount, paid, paid_date, is_demo) VALUES (?,?,?,?,?,?,?,?)",
                     (r[0], c, issue, due, float(r[4] or 0), float(r[5] or 0), _d(r[6]), flag))
        n["invoices"] += 1
    for r in wb["Horas"].iter_rows(min_row=2, values_only=True):
        c = cid(r[1]) if r[1] else None
        if not c or not r[0] or not r[3]:
            continue
        conn.execute("INSERT INTO time_entries (date, client_id, activity, hours, note, is_demo) VALUES (?,?,?,?,?,?)",
                     (_d(r[0]), c, r[2], float(r[3]), r[5], flag))
        n["time_entries"] += 1
    audit.log(conn, "system", "import.excel", None, {**n, "demo": demo, "file": path.split("/")[-1]})
    return n
