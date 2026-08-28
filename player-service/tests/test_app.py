"""
Unit tests for player-service.

The Team Service dependency is mocked (monkeypatched) so these are true
unit tests -- no network calls, no real team-service required. The
Selenium suite in /e2e-tests is what exercises the real inter-service
HTTP calls against a fully deployed environment.
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

    # Pretend team_id 1 exists and nothing else does, without any HTTP call.
    monkeypatch.setattr(app_module, "team_exists", lambda team_id: str(team_id) == "1")

    with app_module.app.test_client() as client:
        yield client


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_create_player_valid_team(client):
    resp = client.post("/api/players", json={"name": "John Doe", "team_id": 1, "position": "QB", "jersey_no": 7})
    assert resp.status_code == 201
    assert resp.get_json()["team_id"] == 1


def test_create_player_invalid_team_rejected(client):
    resp = client.post("/api/players", json={"name": "Ghost", "team_id": 999})
    assert resp.status_code == 422


def test_create_player_missing_fields(client):
    resp = client.post("/api/players", json={"name": "No Team"})
    assert resp.status_code == 400


def test_list_players_filtered_by_team(client):
    client.post("/api/players", json={"name": "Player A", "team_id": 1})
    resp = client.get("/api/players?team_id=1")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1


def test_delete_player(client):
    created = client.post("/api/players", json={"name": "Player A", "team_id": 1}).get_json()
    resp = client.delete(f"/api/players/{created['id']}")
    assert resp.status_code == 200
    assert client.get(f"/api/players/{created['id']}").status_code == 404
