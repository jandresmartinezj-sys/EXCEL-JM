from tests.conftest import login


def test_requires_auth(client_app):
    assert client_app.get("/api/dashboard").status_code == 401
    assert client_app.post("/api/command", json={"text": "hola"}).status_code == 401


def test_bad_login_and_rate_limit(client_app):
    for _ in range(5):
        assert client_app.post("/api/auth/login", json={"username": "dueno", "password": "x"}).status_code == 401
    assert client_app.post("/api/auth/login", json={"username": "dueno", "password": "x"}).status_code == 429


def test_owner_command_and_dashboard(client_app):
    h = login(client_app, "dueno", "clave-segura-123")
    r = client_app.post("/api/command", json={"text": "dame el estado general del negocio"}, headers=h)
    assert r.status_code == 200 and r.json()["status"] == "completed"
    d = client_app.get("/api/dashboard", headers=h).json()
    assert d["demo_data"] is True and any(k["id"] == "mrr" for k in d["kpis"])


def test_client_portal_isolation(client_app):
    h1 = login(client_app, "cliente1", "clave-segura-789")
    p = client_app.get("/api/portal", headers=h1).json()
    assert "Ribera" in p["client"]["name"]
    assert all("DEMO" in i["number"] for i in p["invoices"]) and len(p["invoices"]) == 1
    # un cliente no puede usar el cerebro ni el tablero de la firma
    assert client_app.get("/api/dashboard", headers=h1).status_code == 403
    assert client_app.post("/api/command", json={"text": "cartera"}, headers=h1).status_code == 403
    h2 = login(client_app, "cliente2", "clave-segura-000")
    p2 = client_app.get("/api/portal", headers=h2).json()
    assert "Sinú" in p2["client"]["name"] and "Ribera" not in str(p2)


def test_staff_cannot_approve_or_change_autonomy(client_app):
    hs = login(client_app, "auxiliar", "clave-segura-456")
    r = client_app.post("/api/command", json={"text": "paga la factura del proveedor"}, headers=hs)
    assert r.json()["status"] == "awaiting_approval"
    ap = client_app.get("/api/approvals", headers=hs).json()[0]
    assert client_app.post(f"/api/approvals/{ap['id']}/decide", json={"approve": True}, headers=hs).status_code == 403
    assert client_app.post("/api/settings/autonomy", json={"level": 5}, headers=hs).status_code == 403
    assert client_app.get("/api/audit", headers=hs).status_code == 403


def test_owner_approves_and_audit_reconstructs(client_app):
    h = login(client_app, "dueno", "clave-segura-123")
    client_app.post("/api/command", json={"text": "envía un mensaje al cliente Taller"}, headers=h)
    ap = client_app.get("/api/approvals", headers=h).json()[0]
    r = client_app.post(f"/api/approvals/{ap['id']}/decide", json={"approve": False}, headers=h)
    assert r.json()["status"] == "rejected"
    a = client_app.get("/api/audit", headers=h).json()
    assert a["integrity"]["ok"]
    actions = [e["action"] for e in a["entries"]]
    assert "approval.request" in actions and "approval.rejected" in actions


def test_personal_token_for_shortcut(client_app):
    h = login(client_app, "dueno", "clave-segura-123")
    tok = client_app.post("/api/auth/personal-token", json={"label": "iPhone"}, headers=h).json()["token"]
    r = client_app.post("/api/shortcut", json={"text": "cómo va el negocio"}, headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200 and "Ingreso recurrente" in r.text


def test_logout_revokes(client_app):
    h = login(client_app, "dueno", "clave-segura-123")
    client_app.post("/api/auth/logout", headers=h)
    assert client_app.get("/api/me", headers=h).status_code == 401


def test_security_headers(client_app):
    r = client_app.get("/api/health")
    assert r.headers["X-Frame-Options"] == "DENY" and "default-src 'self'" in r.headers["Content-Security-Policy"]
