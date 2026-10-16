"""Prueba el bucle del modo IA con un cliente simulado (sin red ni clave)."""
import types

import pytest

from app import llm
from app.orchestrator import Orchestrator
from tests.conftest import TODAY


class FakeBlock(types.SimpleNamespace):
    pass


def _resp(stop, content):
    return types.SimpleNamespace(stop_reason=stop, content=content, model="claude-opus-5-5",
                                 usage=types.SimpleNamespace(input_tokens=100, output_tokens=20, cache_read_input_tokens=50))


class FakeClient:
    """Primera respuesta: pide get_kpis y request_approval; segunda: texto final."""

    def __init__(self):
        self.calls = []
        self.beta = types.SimpleNamespace(messages=types.SimpleNamespace(create=self._create))

    def _create(self, **kw):
        self.calls.append(kw)
        if len(self.calls) == 1:
            return _resp("tool_use", [FakeBlock(type="tool_use", id="t1", name="get_kpis", input={}),
                                      FakeBlock(type="tool_use", id="t2", name="request_approval",
                                                input={"action": "external.send_message", "description": "Escribir al cliente"})])
        return _resp("end_turn", [FakeBlock(type="text", text="Listo: dejé la solicitud en aprobaciones.")])


@pytest.fixture()
def fake(monkeypatch):
    import anthropic
    fc = FakeClient()
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: fc)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    return fc


def test_llm_loop_uses_tools_records_usage_and_gates_external(seeded, owner, fake):
    r = Orchestrator(seeded, owner, TODAY).handle("escríbele un saludo a mis clientes y revisa los números")
    assert r["status"] == "completed" and r["detail"]["mode"] == "ia"
    assert r["detail"]["tools_used"] == ["get_kpis", "request_approval"]
    # el resultado de la herramienta se devolvió en un único mensaje de usuario con ambos tool_result
    second = fake.calls[1]["messages"][-1]
    assert second["role"] == "user" and [b["tool_use_id"] for b in second["content"]] == ["t1", "t2"]
    assert fake.calls[0]["model"] == "claude-opus-5-5"
    ap = seeded.execute("SELECT action, status FROM approvals").fetchone()
    assert ap["action"] == "external.send_message" and ap["status"] == "pending"  # nada se ejecutó
    u = seeded.execute("SELECT SUM(input_tokens), SUM(cache_read_tokens) FROM llm_usage").fetchone()
    assert u[0] == 200 and u[1] == 100


def test_llm_refusal_marks_task_failed(seeded, owner, monkeypatch):
    import anthropic
    fc = FakeClient()
    fc._create = lambda **kw: _resp("refusal", [])
    fc.beta = types.SimpleNamespace(messages=types.SimpleNamespace(create=fc._create))
    monkeypatch.setattr(anthropic, "Anthropic", lambda *a, **k: fc)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    r = Orchestrator(seeded, owner, TODAY).handle("algo que el modo local no reconoce")
    assert r["status"] == "failed" and "declinó" in r["speech"]


def test_llm_not_used_without_key(seeded, owner, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert not llm.available()
    r = Orchestrator(seeded, owner, TODAY).handle("algo que el modo local no reconoce")
    assert r["detail"]["clarification_needed"]
