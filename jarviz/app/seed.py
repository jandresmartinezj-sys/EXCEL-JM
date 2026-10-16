"""Datos de DEMOSTRACIÓN (is_demo = 1). El tablero los marca como tales. Bórralos con `cli purge-demo`."""
from datetime import date, timedelta

from . import audit


def seed_demo(conn, today: date | None = None) -> dict:
    d = today or date.today()
    m0 = d.replace(day=1)
    D = lambda n: (d + timedelta(days=n)).isoformat()  # noqa: E731
    cl = [("Restaurante La Ribera (demo)", "900100200", "Pyme servicios", "Empresa", 750_000, m0.isoformat(), "Activo", "Bajo", 9),
          ("Comercializadora Sinú SAS (demo)", "900300400", "Pyme comercio", "Crecimiento", 1_100_000, D(-100), "Activo", "Bajo", 10),
          ("Juan Pérez independiente (demo)", "1067000000", "Persona natural", "Básico", 450_000, D(-70), "Activo", "Medio", 7),
          ("Taller Mecánico Rápido (demo)", "901500600", "Pyme servicios", "Empresa", 750_000, D(-160), "Activo", "Alto", 5)]
    ids = []
    for c in cl:
        ids.append(conn.execute("""INSERT INTO clients (name, nit, segment, plan, monthly_fee, start_date, status, risk, nps, is_demo)
                                   VALUES (?,?,?,?,?,?,?,?,?,1)""", c).lastrowid)
    for p in [("Ferretería El Progreso (demo)", "Pyme comercio", "Referido", "5 Propuesta enviada", "Crecimiento", 1_100_000, "Llamar para resolver dudas", D(4)),
              ("Tienda Online Moda Sinú (demo)", "Emprendedor digital", "WhatsApp", "3 Diagnóstico agendado", "Básico", 450_000, "Reunión de diagnóstico", D(1)),
              ("Transportes del Caribe SAS (demo)", "Pyme servicios", "Alianza", "2 Contactado", "Empresa", 750_000, "Seguimiento", D(-6)),
              ("Hacienda Los Robles (demo)", "Agro / ganadero", "Red personal", "4 Diagnóstico entregado", "CFO fraccional", 2_200_000, "Presentar propuesta", D(5)),
              ("Distribuidora Andina (demo)", "Pyme comercio", "Google", "8 Perdido", "Empresa", 750_000, None, None)]:
        conn.execute("""INSERT INTO prospects (name, segment, channel, stage, plan, monthly_value, next_step, next_step_date, is_demo)
                        VALUES (?,?,?,?,?,?,?,?,1)""", p)
    conn.execute("INSERT INTO prospects (name, stage, plan, monthly_value, is_demo) VALUES ('Restaurante La Ribera (demo)','7 Ganado','Empresa',750000,1)")
    for o in [(ids[0], "Retención en la fuente", "mes anterior", D(3), "En preparación"),
              (ids[1], "IVA", "bimestre", D(10), "Pendiente"),
              (ids[1], "Retención en la fuente", "mes anterior", D(-2), "Presentada"),
              (ids[2], "Renta PN", "año gravable", D(40), "Pendiente"),
              (ids[3], "Nómina electrónica", "mes anterior", D(-1), "Pendiente")]:
        conn.execute("""INSERT INTO obligations (client_id, kind, period, due_date, status, owner, source_note, is_demo)
                        VALUES (?,?,?,?,?,'Titular','DEMO: fecha ficticia, no oficial',1)""", o)
    for i, (cid, amt, paid, issued) in enumerate([(ids[0], 750_000, 750_000, m0), (ids[1], 1_100_000, 1_100_000, m0),
                                                  (ids[2], 450_000, 0, m0), (ids[3], 750_000, 0, m0),
                                                  (ids[3], 750_000, 300_000, d - timedelta(days=45))], 1):
        conn.execute("""INSERT INTO invoices (number, client_id, issue_date, due_date, amount, paid, is_demo)
                        VALUES (?,?,?,?,?,?,1)""", (f"DEMO-{i:03d}", cid, issued.isoformat(), (issued + timedelta(days=4)).isoformat(), amt, paid))
    for cid, h, act in [(ids[0], 4, "Contabilidad"), (ids[0], 2, "Nómina"), (ids[1], 6, "Contabilidad"), (ids[1], 3, "Informe / reunión"),
                        (ids[2], 2, "Tributario"), (ids[3], 7, "Contabilidad"), (ids[3], 5, "Tributario")]:
        conn.execute("INSERT INTO time_entries (date, client_id, activity, hours, is_demo) VALUES (?,?,?,?,1)", (m0.isoformat(), cid, act, h))
    audit.log(conn, "system", "seed.demo", None, {"clients": len(ids)})
    return {"clients": len(ids)}


def purge_demo(conn) -> dict:
    n = {}
    demo_clients = "SELECT id FROM clients WHERE is_demo = 1"
    for t in ("time_entries", "invoices", "obligations"):
        n[t] = conn.execute(f"DELETE FROM {t} WHERE is_demo = 1 OR client_id IN ({demo_clients})").rowcount
    conn.execute(f"DELETE FROM documents WHERE client_id IN ({demo_clients})")
    conn.execute(f"UPDATE tasks SET client_id = NULL WHERE client_id IN ({demo_clients})")
    conn.execute(f"UPDATE alerts SET client_id = NULL WHERE client_id IN ({demo_clients})")
    conn.execute(f"DELETE FROM memory WHERE client_id IN ({demo_clients})")
    n["prospects"] = conn.execute("DELETE FROM prospects WHERE is_demo = 1").rowcount
    n["clients"] = conn.execute("DELETE FROM clients WHERE is_demo = 1").rowcount
    audit.log(conn, "system", "seed.purge_demo", None, n)
    return n
