"""
Unit tests for match-service. Team Service dependency is mocked.
"""

import os
import pytest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import app as app_module  # noqa: E402


@pytest.fixture
def client(monkeypatch):
    app_module.app.config["TESTING"] = True
    with app_module.app.app_context():
        app_module.db.drop_all()
        app_module.db.create_all()

    monkeypatch.setattr(app_module, "team_exists", lambda team_id: str(team_id) in ("1", "2"))

    with app_module.app.test_client() as client:
        yield client


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_create_match_valid_teams(client):
    resp = client.post("/api/matches", json={"home_team_id": 1, "away_team_id": 2, "venue": "Home Stadium"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["status"] == "scheduled"
    assert body["home_score"] == 0


def test_create_match_same_team_rejected(client):
    resp = client.post("/api/matches", json={"home_team_id": 1, "away_team_id": 1})
    assert resp.status_code == 400


def test_create_match_invalid_team_rejected(client):
    resp = client.post("/api/matches", json={"home_team_id": 1, "away_team_id": 999})
    assert resp.status_code == 422


def test_update_score(client):
    created = client.post("/api/matches", json={"home_team_id": 1, "away_team_id": 2}).get_json()
    resp = client.patch(f"/api/matches/{created['id']}/score", json={"home_score": 21, "away_score": 14})
    assert resp.status_code == 200
    assert resp.get_json()["home_score"] == 21


def test_update_status_invalid_value_rejected(client):
    created = client.post("/api/matches", json={"home_team_id": 1, "away_team_id": 2}).get_json()
    resp = client.put(f"/api/matches/{created['id']}/status", json={"status": "not-a-real-status"})
    assert resp.status_code == 400


def test_update_status_valid_value(client):
    created = client.post("/api/matches", json={"home_team_id": 1, "away_team_id": 2}).get_json()
    resp = client.put(f"/api/matches/{created['id']}/status", json={"status": "live"})
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "live"
