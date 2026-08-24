"""
SportsZone - Match Service
----------------------------
Owns Matches and live Scores between two teams. Validates both team ids
against the Team Service before a match can be created.

Data layer: SQLAlchemy against PostgreSQL in production (DATABASE_URL),
falling back to local SQLite when no DATABASE_URL is set.

Endpoints
---------
GET    /health                    -> service health check (includes DB check)
GET    /api/matches               -> list all matches
GET    /api/matches/<id>          -> get a single match
POST   /api/matches               -> schedule a match (validates both teams)
PATCH  /api/matches/<id>/score    -> update the live score
PUT    /api/matches/<id>/status   -> update match status (scheduled/live/completed)
DELETE /api/matches/<id>          -> delete a match
"""

import os
import requests
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///matches.db")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

TEAM_SERVICE_URL = os.environ.get("TEAM_SERVICE_URL", "http://localhost:5001")
SERVICE_NAME = "match-service"
SERVICE_VERSION = "2.0.0"
VALID_STATUSES = {"scheduled", "live", "completed"}


class Match(db.Model):
    __tablename__ = "matches"

    id = db.Column(db.Integer, primary_key=True)
    home_team_id = db.Column(db.Integer, nullable=False)
    away_team_id = db.Column(db.Integer, nullable=False)
    venue = db.Column(db.String(160))
    home_score = db.Column(db.Integer, default=0)
    away_score = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default="scheduled")

    def to_dict(self):
        return {
            "id": self.id,
            "home_team_id": self.home_team_id,
            "away_team_id": self.away_team_id,
            "venue": self.venue,
            "home_score": self.home_score,
            "away_score": self.away_score,
            "status": self.status,
        }


with app.app_context():
    db.create_all()


def team_exists(team_id):
    try:
        resp = requests.get(f"{TEAM_SERVICE_URL}/api/teams/{team_id}", timeout=3)
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        return False


@app.route("/health", methods=["GET"])
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        db_status = "connected"
    except Exception as exc:  # pragma: no cover
        db_status = f"unreachable ({exc.__class__.__name__})"
    return jsonify(
        {"service": SERVICE_NAME, "version": SERVICE_VERSION, "status": "healthy", "database": db_status}
    )


@app.route("/api/matches", methods=["GET"])
def list_matches():
    matches = Match.query.order_by(Match.id).all()
    return jsonify([m.to_dict() for m in matches])


@app.route("/api/matches/<int:match_id>", methods=["GET"])
def get_match(match_id):
    match = Match.query.get(match_id)
    if match is None:
        return jsonify({"error": f"Match {match_id} not found"}), 404
    return jsonify(match.to_dict())


@app.route("/api/matches", methods=["POST"])
def create_match():
    data = request.get_json(silent=True) or {}
    home_team_id = data.get("home_team_id")
    away_team_id = data.get("away_team_id")

    if home_team_id is None or away_team_id is None:
        return jsonify({"error": "'home_team_id' and 'away_team_id' are required"}), 400
    if home_team_id == away_team_id:
        return jsonify({"error": "A team cannot play itself"}), 400
    if not team_exists(home_team_id) or not team_exists(away_team_id):
        return jsonify({"error": "One or both team_ids do not exist in Team Service"}), 422

    match = Match(home_team_id=home_team_id, away_team_id=away_team_id, venue=data.get("venue"))
    db.session.add(match)
    db.session.commit()
    return jsonify(match.to_dict()), 201


@app.route("/api/matches/<int:match_id>/score", methods=["PATCH"])
def update_score(match_id):
    match = Match.query.get(match_id)
    if match is None:
        return jsonify({"error": f"Match {match_id} not found"}), 404

    data = request.get_json(silent=True) or {}
    match.home_score = data.get("home_score", match.home_score)
    match.away_score = data.get("away_score", match.away_score)
    db.session.commit()
    return jsonify(match.to_dict())


@app.route("/api/matches/<int:match_id>/status", methods=["PUT"])
def update_status(match_id):
    match = Match.query.get(match_id)
    if match is None:
        return jsonify({"error": f"Match {match_id} not found"}), 404

    data = request.get_json(silent=True) or {}
    status = data.get("status")
    if status not in VALID_STATUSES:
        return jsonify({"error": f"status must be one of {sorted(VALID_STATUSES)}"}), 400

    match.status = status
    db.session.commit()
    return jsonify(match.to_dict())


@app.route("/api/matches/<int:match_id>", methods=["DELETE"])
def delete_match(match_id):
    match = Match.query.get(match_id)
    if match is None:
        return jsonify({"error": f"Match {match_id} not found"}), 404
    db.session.delete(match)
    db.session.commit()
    return jsonify({"message": f"Match {match_id} deleted"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5003))
    app.run(host="0.0.0.0", port=port)
