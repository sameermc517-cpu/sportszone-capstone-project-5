"""
SportsZone - Player Service
-----------------------------
Owns Players. Each player belongs to a Team, so this service calls the
Team Service over HTTP to validate a team_id before attaching a player
to it -- a realistic example of service-to-service communication.

Data layer: SQLAlchemy against PostgreSQL in production (DATABASE_URL),
falling back to local SQLite when no DATABASE_URL is set (unit tests,
quick local runs).

Endpoints
---------
GET    /health                -> service health check (includes DB check)
GET    /api/players           -> list all players (optional ?team_id=)
GET    /api/players/<id>      -> get a single player
POST   /api/players           -> create a player (validates team_id)
PUT    /api/players/<id>      -> update a player
DELETE /api/players/<id>      -> delete a player
"""

import os
import requests
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///players.db")
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

TEAM_SERVICE_URL = os.environ.get("TEAM_SERVICE_URL", "http://localhost:5001")
SERVICE_NAME = "player-service"
SERVICE_VERSION = "2.0.0"


class Player(db.Model):
    __tablename__ = "players"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    position = db.Column(db.String(60))
    jersey_no = db.Column(db.Integer)
    team_id = db.Column(db.Integer, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "position": self.position,
            "jersey_no": self.jersey_no,
            "team_id": self.team_id,
        }


with app.app_context():
    db.create_all()


def team_exists(team_id):
    """Ask the Team Service whether a given team_id is valid."""
    try:
        resp = requests.get(f"{TEAM_SERVICE_URL}/api/teams/{team_id}", timeout=3)
        return resp.status_code == 200
    except requests.exceptions.RequestException:
        # Fail safe (reject) rather than silently creating orphaned records.
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


@app.route("/api/players", methods=["GET"])
def list_players():
    team_id = request.args.get("team_id")
    query = Player.query
    if team_id:
        query = query.filter_by(team_id=team_id)
    players = query.order_by(Player.id).all()
    return jsonify([p.to_dict() for p in players])


@app.route("/api/players/<int:player_id>", methods=["GET"])
def get_player(player_id):
    player = Player.query.get(player_id)
    if player is None:
        return jsonify({"error": f"Player {player_id} not found"}), 404
    return jsonify(player.to_dict())


@app.route("/api/players", methods=["POST"])
def create_player():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    team_id = data.get("team_id")

    if not name or team_id is None:
        return jsonify({"error": "'name' and 'team_id' are required fields"}), 400

    if not team_exists(team_id):
        return jsonify({"error": f"team_id {team_id} does not exist in Team Service"}), 422

    player = Player(name=name, position=data.get("position"), jersey_no=data.get("jersey_no"), team_id=team_id)
    db.session.add(player)
    db.session.commit()
    return jsonify(player.to_dict()), 201


@app.route("/api/players/<int:player_id>", methods=["PUT"])
def update_player(player_id):
    player = Player.query.get(player_id)
    if player is None:
        return jsonify({"error": f"Player {player_id} not found"}), 404

    data = request.get_json(silent=True) or {}
    new_team_id = data.get("team_id", player.team_id)
    if new_team_id != player.team_id and not team_exists(new_team_id):
        return jsonify({"error": f"team_id {new_team_id} does not exist in Team Service"}), 422

    player.name = data.get("name", player.name)
    player.position = data.get("position", player.position)
    player.jersey_no = data.get("jersey_no", player.jersey_no)
    player.team_id = new_team_id
    db.session.commit()
    return jsonify(player.to_dict())


@app.route("/api/players/<int:player_id>", methods=["DELETE"])
def delete_player(player_id):
    player = Player.query.get(player_id)
    if player is None:
        return jsonify({"error": f"Player {player_id} not found"}), 404
    db.session.delete(player)
    db.session.commit()
    return jsonify({"message": f"Player {player_id} deleted"})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5002))
    app.run(host="0.0.0.0", port=port)
