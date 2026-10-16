import os
import sys
from datetime import date

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.pop("ANTHROPIC_API_KEY", None)  # las pruebas corren en modo local

from app import db, security  # noqa: E402
from app.seed import seed_demo  # noqa: E402

TODAY = date(2026, 10, 16)


@pytest.fixture()
def conn(tmp_path, monkeypatch):
    path = str(tmp_path / "t.db")
    monkeypatch.setenv("JARVIZ_DB_PATH", path)
    c = db.reset(path)
    yield c
    c.close()


@pytest.fixture()
def seeded(conn):
    seed_demo(conn, TODAY)
    return conn


@pytest.fixture()
def owner(conn):
    uid = security.create_user(conn, "dueno", "clave-segura-123", "owner")
    return {"id": uid, "username": "dueno", "role": "owner", "client_id": None}


@pytest.fixture()
def client_app(seeded, monkeypatch):
    from fastapi.testclient import TestClient

    from app import main
    monkeypatch.setattr(main, "today", lambda: TODAY)
    main.login_limiter.hits.clear()
    main.command_limiter.hits.clear()
    security.create_user(seeded, "dueno", "clave-segura-123", "owner")
    security.create_user(seeded, "auxiliar", "clave-segura-456", "staff")
    security.create_user(seeded, "cliente1", "clave-segura-789", "client", client_id=1)
    security.create_user(seeded, "cliente2", "clave-segura-000", "client", client_id=2)
    return TestClient(main.app)


def login(tc, user, pw):
    r = tc.post("/api/auth/login", json={"username": user, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}
