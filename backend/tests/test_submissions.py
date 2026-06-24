from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)
_URL = "https://github.com/octocat/Hello-World"


def test_empty_team_rejected(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "")
    r = client.post(
        "/api/submissions",
        json={"team_name": "  ", "project_name": "p", "github_url": _URL},
    )
    assert r.status_code == 400


def test_invalid_github_url_rejected(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "")
    r = client.post(
        "/api/submissions",
        json={"team_name": "t", "project_name": "p", "github_url": "not-a-url"},
    )
    assert r.status_code == 400


def test_invalid_stage_rejected(monkeypatch):
    monkeypatch.setattr(settings, "admin_token", "")
    r = client.post(
        "/api/submissions",
        json={"team_name": "t", "project_name": "p", "github_url": _URL, "stage": "weird"},
    )
    assert r.status_code == 400
