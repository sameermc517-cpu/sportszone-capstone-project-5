"""
Unit tests for team-service.

Run with: pytest (from inside team-service/)
Uses an in-memory SQLite database so tests never touch a real Postgres
instance -- this is what Jenkins runs in the "Unit Tests" stage, and
what SonarQube's coverage report is generated from.
"""

import os
import pytest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import app as app_module  # noqa: E402


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.app_context():
        app_module.db.drop_all()
        app_module.db.create_all()
    with app_module.app.test_client() as client:
        yield client


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.get_json()["status"] == "healthy"


def test_create_and_list_team(client):
    resp = client.post("/api/teams", json={"name": "Falcons", "sport": "Football", "city": "Atlanta"})
    assert resp.status_code == 201
    body = resp.get_json()
    assert body["name"] == "Falcons"

    resp = client.get("/api/teams")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 1


def test_create_team_missing_fields(client):
    resp = client.post("/api/teams", json={"name": "Falcons"})
    assert resp.status_code == 400


def test_duplicate_team_name_rejected(client):
    client.post("/api/teams", json={"name": "Falcons", "sport": "Football"})
    resp = client.post("/api/teams", json={"name": "Falcons", "sport": "Football"})
    assert resp.status_code == 409


def test_get_missing_team_returns_404(client):
    resp = client.get("/api/teams/999")
    assert resp.status_code == 404


def test_update_team(client):
    created = client.post("/api/teams", json={"name": "Falcons", "sport": "Football"}).get_json()
    resp = client.put(f"/api/teams/{created['id']}", json={"city": "Atlanta"})
    assert resp.status_code == 200
    assert resp.get_json()["city"] == "Atlanta"


def test_delete_team(client):
    created = client.post("/api/teams", json={"name": "Falcons", "sport": "Football"}).get_json()
    resp = client.delete(f"/api/teams/{created['id']}")
    assert resp.status_code == 200
    assert client.get(f"/api/teams/{created['id']}").status_code == 404
