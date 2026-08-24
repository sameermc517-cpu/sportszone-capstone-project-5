"""
SportsZone - Team Service
--------------------------
Flask microservice owning all data and operations related to Teams.

Data layer: this service talks to a real SQL database through
SQLAlchemy. In production (Docker Compose / Kubernetes) DATABASE_URL
points at a PostgreSQL instance. For quick local/unit-test runs with no
database server available, DATABASE_URL defaults to a local SQLite
file so the service still starts -- SQLAlchemy hides the dialect
difference behind the same ORM calls.

Endpoints
---------
GET    /health              -> service health check (includes DB check)
GET    /api/teams           -> list all teams
GET    /api/teams/<id>      -> get a single team
POST   /api/teams           -> create a team
PUT    /api/teams/<id>      -> update a team
DELETE /api/teams/<id>      -> delete a team
"""

import os
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///teams.db")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

SERVICE_NAME = "team-service"
SERVICE_VERSION = "2.0.0"


class Team(db.Model):
    __tablename__ = "teams"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False, unique=True)
    city = db.Column(db.String(120))
    sport = db.Column(db.String(80), nullable=False)
    founded_year = db.Column(db.Integer)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "city": self.city,
            "sport": self.sport,
            "founded_year": self.founded_year,
        }


with app.app_context():
    db.create_all()


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


@app.route("/api/teams", methods=["GET"])
def list_teams():
    teams = Team.query.order_by(Team.id).all()
    return jsonify([t.to_dict() for t in teams])


@app.route("/api/teams/<int:team_id>", methods=["GET"])
def get_team(team_id):
    team = Team.query.get(team_id)
    if team is None:
        return jsonify({"error": f"Team {team_id} not found"}), 404
    return jsonify(team.to_dict())


@app.route("/api/teams", methods=["POST"])
def create_team():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    sport = data.get("sport")
    if not name or not sport:
        return jsonify({"error": "'name' and 'sport' are required fields"}), 400

    if Team.query.filter_by(name=name).first() is not None:
        return jsonify({"error": f"Team '{name}' already exists"}), 409

    team = Team(name=name, city=data.get("city"), sport=sport, founded_year=data.get("founded_year"))
    db.session.add(team)
    db.session.commit()
    return jsonify(team.to_dict()), 201


@app.route("/api/teams/<int:team_id>", methods=["PUT"])
def update_team(team_id):
    team = Team.query.get(team_id)
    if team is None:
        return jsonify({"error": f"Team {team_id} not found"}), 404

    data = request.get_json(silent=True) or {}
    team.name = data.get("name", team.name)
    team.city = data.get("city", team.city)
    team.sport = data.get("sport", team.sport)
    team.founded_year = data.get("founded_year", team.founded_year)
    db.session.commit()
    return jsonify(team.to_dict())


@app.route("/api/teams/<int:team_id>", methods=["DELETE"])
def delete_team(team_id):
    team = Team.query.get(team_id)
    if team is None:
        return jsonify({"error": f"Team {team_id} not found"}), 404
    db.session.delete(team)
    db.session.commit()
    return jsonify({"message": f"Team {team_id} deleted"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    app.run(host="0.0.0.0", port=port)
