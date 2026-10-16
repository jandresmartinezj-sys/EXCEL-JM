import sqlite3

import pytest

from app import analytics as an, audit, memory, policy, tasks
from app.automations import flow_close, flow_new_prospect, flow_obligation_watch, flow_weekly_review
from app.orchestrator import Orchestrator, classify, decide_approval, run_scheduled
from tests.conftest import TODAY


def test_audit_is_append_only_and_chained(conn):
    audit.log(conn, "t", "a", None, {"x": 1})
    audit.log(conn, "t", "b", None, {"x": 2})
    assert audit.verify(conn)["ok"]
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("UPDATE audit_log SET actor = 'hacker' WHERE id = 1")
    with pytest.raises(sqlite3.DatabaseError):
        conn.execute("DELETE FROM audit_log")


def test_audit_detects_tampering(conn):
    audit.log(conn, "t", "a", None, {})
    audit.log(conn, "t", "b", None, {})
    conn.execute("DROP TRIGGER audit_no_update")  # simula manipulación directa de la BD
    conn.execute("UPDATE audit_log SET detail_json = '{\"x\": 9}' WHERE id = 1")
    r = audit.verify(conn)
    assert not r["ok"] and r["broken_at_id"] == 1


def test_task_state_machine(conn):
    t = tasks.create(conn, "x", "t")
    assert t["status"] == "pending"
    tasks.transition(conn, t["id"], "running", "t")
    tasks.transition(conn, t["id"], "failed", "t", error="boom")
    assert tasks.get(conn, t["id"])["error"] == "boom"
    with pytest.raises(ValueError):
        tasks.transition(conn, t["id"], "completed", "t")  # failed → completed no es válido


def test_idempotency_prevents_duplicates(conn):
    a = tasks.create(conn, "x", "t", idempotency_key="k1")
    b = tasks.create(conn, "x", "t", idempotency_key="k1")
    assert a["id"] == b["id"] and b.get("_duplicate")
    assert conn.execute("SELECT COUNT(*) FROM tasks").fetchone()[0] == 1


def test_policy_blocks_and_requires_approval(conn):
    assert policy.decide(conn, "read", 1, 3)["allowed"]
    d = policy.decide(conn, "external.send_message", 5, 5)
    assert not d["allowed"] and d["needs_approval"]  # nivel 4 siempre requiere aprobación
    d = policy.decide(conn, "internal.create_task", 3, 2)  # global 2 < nivel 3
    assert not d["allowed"] and d["needs_approval"]
    assert not policy.decide(conn, "inventada", 5, 5)["allowed"]


def test_memory_persists_and_isolates_clients(seeded):
    memory.save(seeded, "client", "Prefiere reuniones los lunes", "test", "t", client_id=1)
    memory.save(seeded, "work", "Meta Q4: 6 clientes", "test", "t")
    from app import db
    c2 = db.reset(db._path or "")  # nueva conexión = nueva sesión
    assert any("Meta Q4" in m["content"] for m in memory.recall(c2, ("work",)))
    assert memory.recall(c2, ("client",), client_id=2) == []
    assert len(memory.recall(c2, ("client",), client_id=1)) == 1


def test_kpis_use_real_data_and_flag_demo(seeded, conn):
    k = an.kpis(seeded, TODAY)
    assert k["demo_data"] is True
    kk = {x["id"]: x for x in k["kpis"]}
    assert kk["mrr"]["value"] == 3_050_000
    assert kk["obl_overdue"]["value"] == 1  # nómina electrónica vencida ayer (demo)
    assert kk["close_rate"]["value"] == 0.5
    assert all(x["definition"] and x["formula"] and x["source"] for x in k["kpis"])


def test_kpis_empty_db_report_not_available(conn):
    kk = {x["id"]: x for x in an.kpis(conn, TODAY)["kpis"]}
    assert kk["mrr"]["value"] is None and kk["mrr"]["missing"]
    assert an.kpis(conn, TODAY)["demo_data"] is False


@pytest.mark.parametrize("text,intent", [
    ("JARVIZ, dame el estado general del negocio", "status"),
    ("identifica tres oportunidades de negocio", "opportunities"),
    ("prepara el cierre contable de Restaurante La Ribera", "close"),
    ("revisa los riesgos de cumplimiento de esta empresa", "risks"),
    ("¿qué debería priorizar esta semana para aumentar la rentabilidad?", "priorities"),
    ("prepara una propuesta para una empresa que necesita tercerizar su contabilidad", "proposal"),
    ("envía la propuesta a Ferretería El Progreso", "external_action"),
    ("registra un nuevo prospecto llamado Panadería La Espiga", "new_prospect"),
    ("¿qué obligaciones vencen esta semana?", "obligations"),
])
def test_intent_classification(text, intent):
    assert classify(text)[0] == intent


def test_orchestrator_delegates_and_consolidates(seeded, owner):
    r = Orchestrator(seeded, owner, TODAY).handle("JARVIZ, dame el estado general del negocio")
    assert r["status"] == "completed"
    assert set(r["agents"]) >= {"ceo", "finanzas", "tributario"}
    assert "3.050.000" in r["speech"]
    assert tasks.get(seeded, r["task_id"])["status"] == "completed"


def test_external_action_is_blocked_pending_approval(seeded, owner):
    r = Orchestrator(seeded, owner, TODAY).handle("envía la propuesta a Ferretería El Progreso")
    assert r["status"] == "awaiting_approval"
    ap = seeded.execute("SELECT * FROM approvals").fetchone()
    assert ap["action"] == "external.send_proposal" and ap["status"] == "pending"
    res = decide_approval(seeded, ap["id"], True, "user:dueno")
    assert res["executed"] is False and "manualmente" in res["note"]
    assert tasks.get(seeded, r["task_id"])["status"] == "completed"


def test_failed_task_has_identifiable_state(seeded, owner):
    r = Orchestrator(seeded, owner, TODAY).handle("crea una tarea")
    assert r["status"] == "failed" and r["next_step"]
    assert tasks.get(seeded, r["task_id"])["status"] == "failed"


def test_new_prospect_flow_is_idempotent(seeded):
    a = flow_new_prospect(seeded, "t", "Panadería La Espiga", TODAY, contact="300 1")
    b = flow_new_prospect(seeded, "t", "Panadería La Espiga", TODAY, contact="300 1")
    assert not a["duplicate"] and b["duplicate"]
    assert a["proposal_draft"]["status"] == "borrador"
    assert seeded.execute("SELECT COUNT(*) FROM prospects WHERE name='Panadería La Espiga'").fetchone()[0] == 1


def test_close_and_obligation_flows_do_not_duplicate(seeded):
    a = flow_close(seeded, "t", 1, "2026-09")
    b = flow_close(seeded, "t", 1, "2026-09")
    assert a["tasks_created"] == len(a["steps"]) and b["tasks_created"] == 0
    assert "extracto" in a["missing_documents"]
    w1 = flow_obligation_watch(seeded, "t", TODAY)
    w2 = flow_obligation_watch(seeded, "t", TODAY)
    assert w1["tasks_created"] >= 3 and w2["tasks_created"] == 0


def test_weekly_review_once_per_week(seeded):
    flow_weekly_review(seeded, "t", TODAY)
    r = flow_weekly_review(seeded, "t", TODAY)
    assert "ya estaba registrada" in r["note"]
    assert seeded.execute("SELECT COUNT(*) FROM memory WHERE key LIKE 'weekly:%'").fetchone()[0] == 1


def test_scheduled_alerts_deduplicate(seeded):
    a = run_scheduled(seeded, TODAY)
    b = run_scheduled(seeded, TODAY)
    assert a["alerts_new"] > 0 and b["alerts_new"] == 0


def test_low_autonomy_turns_internal_action_into_approval(seeded, owner):
    seeded.execute("INSERT INTO settings VALUES ('max_autonomy','2')")
    r = Orchestrator(seeded, owner, TODAY).handle("crea una tarea llamar al banco")
    assert r["status"] == "awaiting_approval"


def test_find_entity(seeded):
    e = an.find_entity(seeded, "prepara el cierre de la ribera")
    assert e and e["kind"] == "client" and "Ribera" in e["name"]
