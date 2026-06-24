from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)

_RUBRIC = {
    "criteria": [
        {"key": "a", "name": "A", "description": "", "weight": 1, "order": 1}
    ]
}


def test_open_when_no_token(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "")
    r = client.put("/api/rubric", json=_RUBRIC)
    assert r.status_code == 200


def test_blocked_without_token(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "secret")
    r = client.put("/api/rubric", json=_RUBRIC)
    assert r.status_code == 401


def test_allowed_with_token(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "secret")
    r = client.put("/api/rubric", json=_RUBRIC, headers={"X-Admin-Token": "secret"})
    assert r.status_code == 200


def test_health_reports_auth_required(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "secret")
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["auth_required"] is True
