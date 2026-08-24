"""
SportsZone - Web Frontend
----------------------------
A lightweight Flask application that acts as the single entry point a
user opens in their browser. It calls the three backend microservices
(Team, Player, Match) over HTTP and renders plain HTML pages. This is
what learners will point their browser at to verify the whole platform
is working end-to-end, at every stage of the capstone (local, Docker,
and Kubernetes/AWS).
"""

import os
import requests
from flask import Flask, render_template, request, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "sportszone-dev-secret")

TEAM_SERVICE_URL = os.environ.get("TEAM_SERVICE_URL", "http://localhost:5001")
PLAYER_SERVICE_URL = os.environ.get("PLAYER_SERVICE_URL", "http://localhost:5002")
MATCH_SERVICE_URL = os.environ.get("MATCH_SERVICE_URL", "http://localhost:5003")


def safe_get(url):
    """Call a backend service and degrade gracefully if it is unreachable
    -- useful while learners are still bringing services online one by one."""
    try:
        resp = requests.get(url, timeout=3)
        if resp.status_code == 200:
            return resp.json(), None
        return None, f"{url} returned HTTP {resp.status_code}"
    except requests.exceptions.RequestException as exc:
        return None, f"Could not reach {url} ({exc.__class__.__name__})"


@app.route("/")
def dashboard():
    teams, teams_err = safe_get(f"{TEAM_SERVICE_URL}/api/teams")
    players, players_err = safe_get(f"{PLAYER_SERVICE_URL}/api/players")
    matches, matches_err = safe_get(f"{MATCH_SERVICE_URL}/api/matches")

    team_lookup = {t["id"]: t["name"] for t in teams} if teams else {}

    return render_template(
        "index.html",
        teams=teams or [],
        players=players or [],
        matches=matches or [],
        team_lookup=team_lookup,
        errors=[e for e in (teams_err, players_err, matches_err) if e],
    )


@app.route("/teams/add", methods=["POST"])
def add_team():
    payload = {
        "name": request.form.get("name"),
        "city": request.form.get("city"),
        "sport": request.form.get("sport"),
        "founded_year": request.form.get("founded_year") or None,
    }
    try:
        resp = requests.post(f"{TEAM_SERVICE_URL}/api/teams", json=payload, timeout=3)
        if resp.status_code == 201:
            flash(f"Team '{payload['name']}' created.", "success")
        else:
            flash(f"Could not create team: {resp.json().get('error')}", "error")
    except requests.exceptions.RequestException as exc:
        flash(f"Team Service unreachable: {exc}", "error")
    return redirect(url_for("dashboard"))


@app.route("/players/add", methods=["POST"])
def add_player():
    payload = {
        "name": request.form.get("name"),
        "position": request.form.get("position"),
        "jersey_no": request.form.get("jersey_no") or None,
        "team_id": request.form.get("team_id"),
    }
    try:
        resp = requests.post(f"{PLAYER_SERVICE_URL}/api/players", json=payload, timeout=3)
        if resp.status_code == 201:
            flash(f"Player '{payload['name']}' added.", "success")
        else:
            flash(f"Could not add player: {resp.json().get('error')}", "error")
    except requests.exceptions.RequestException as exc:
        flash(f"Player Service unreachable: {exc}", "error")
    return redirect(url_for("dashboard"))


@app.route("/matches/add", methods=["POST"])
def add_match():
    payload = {
        "home_team_id": request.form.get("home_team_id"),
        "away_team_id": request.form.get("away_team_id"),
        "venue": request.form.get("venue"),
    }
    try:
        resp = requests.post(f"{MATCH_SERVICE_URL}/api/matches", json=payload, timeout=3)
        if resp.status_code == 201:
            flash("Match scheduled.", "success")
        else:
            flash(f"Could not schedule match: {resp.json().get('error')}", "error")
    except requests.exceptions.RequestException as exc:
        flash(f"Match Service unreachable: {exc}", "error")
    return redirect(url_for("dashboard"))


@app.route("/matches/<int:match_id>/score", methods=["POST"])
def update_score(match_id):
    payload = {
        "home_score": request.form.get("home_score"),
        "away_score": request.form.get("away_score"),
    }
    try:
        requests.patch(f"{MATCH_SERVICE_URL}/api/matches/{match_id}/score", json=payload, timeout=3)
        flash("Score updated.", "success")
    except requests.exceptions.RequestException as exc:
        flash(f"Match Service unreachable: {exc}", "error")
    return redirect(url_for("dashboard"))


@app.route("/health")
def health():
    return {"service": "web-frontend", "status": "healthy"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
