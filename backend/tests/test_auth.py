from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)

# DELETE on a non-existent submission exercises the admin gate (require_admin runs
# before the handler): blocked -> 401; allowed -> 404 (passes auth, then not found).
_PATH = "/api/submissions/999999"


def test_open_when_no_token(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "")
    r = client.delete(_PATH)
    assert r.status_code == 404  # open mode -> auth passes -> not found


def test_blocked_without_token(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "secret")
    r = client.delete(_PATH)
    assert r.status_code == 401


def test_allowed_with_token(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "secret")
    r = client.delete(_PATH, headers={"X-Admin-Token": "secret"})
    assert r.status_code == 404  # auth passes -> not found


def test_health_reports_auth_required(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "secret")
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["auth_required"] is True
