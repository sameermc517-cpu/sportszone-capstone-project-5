# SportsZone — Capstone Application Source Code

SportsZone is a sports league management platform built as **three
independent Python/Flask microservices** plus **one web frontend**,
backed by **PostgreSQL**, covered by **unit tests (pytest)** and
**browser end-to-end tests (Selenium)**, analyzed by **SonarQube**, and
deployed through a full **Jenkins CI/CD pipeline**. It is the
application layer for the *Infrastructure Specialist – Cloud &
Application Operations* capstone project.

| Component       | Port | Responsibility                                    |
|------------------|------|----------------------------------------------------|
| team-service    | 5001 | CRUD for Teams (own PostgreSQL database)            |
| player-service  | 5002 | CRUD for Players; validates team_id via team-service |
| match-service   | 5003 | CRUD for Matches & live scores; validates both teams |
| web-frontend    | 5000 | Browser dashboard consuming all 3 APIs              |

Each backend service owns its own PostgreSQL database (database-per-service
pattern) and talks to the others only over HTTP — a genuine microservices
architecture, not a monolith split into folders.

## Repository layout

```
sportszone-capstone/
├── team-service/        app.py, requirements.txt, Dockerfile, pytest.ini, tests/
├── player-service/      app.py, requirements.txt, Dockerfile, pytest.ini, tests/
├── match-service/       app.py, requirements.txt, Dockerfile, pytest.ini, tests/
├── web-frontend/        app.py, requirements.txt, Dockerfile, templates/, static/
├── e2e-tests/           Selenium browser test suite (conftest.py, test_dashboard_workflow.py)
├── db-init/             init-multiple-dbs.sh — creates one Postgres DB per service
├── docker-compose.yml   local verification stack (all 4 services + PostgreSQL)
├── sonar-project.properties   SonarQube analysis configuration
├── Jenkinsfile          full CI/CD pipeline (test → SonarQube → build → deploy → Selenium → promote)
└── README.md
```

This repository is the **starting point** for the capstone project. The
step-by-step capstone guide (provided separately as a Word document,
*SportsZone_Capstone_Project_Guide.docx*) walks through every phase —
Linux, the SQL database, Docker, SonarQube, Terraform, Ansible,
Kubernetes, Selenium, and the full Jenkins pipeline — each with
verification steps and an explanation of what's expected.

## Local verification with Docker Compose

`docker-compose.yml` builds and runs all four services **and a real
PostgreSQL instance** together, with hostnames and `DATABASE_URL`s wired
up automatically. After bringing it up, open `http://localhost:5000/` in
a browser and confirm you can add a team, add a player against that
team, and schedule a match — this exercises all three backend services
and the database end-to-end.

## Running the unit tests

Each backend service has its own pytest suite using an isolated SQLite
database, so tests never touch a real Postgres instance:

```
cd team-service && pip install -r requirements.txt && pytest
cd player-service && pip install -r requirements.txt && pytest
cd match-service && pip install -r requirements.txt && pytest
```

Each run produces `coverage.xml` and `test-results.xml`, which is what
SonarQube and Jenkins both consume.

## Running the Selenium end-to-end tests

Point the suite at any running deployment (local Compose stack, or a
real Kubernetes/AWS URL) via `BASE_URL`:

```
cd e2e-tests && pip install -r requirements.txt
BASE_URL=http://localhost:5000 pytest -v
```

## API quick reference

**Team Service**
- `GET /api/teams`, `GET /api/teams/<id>`
- `POST /api/teams` — body: `{"name": "...", "sport": "...", "city": "...", "founded_year": 2024}`
- `PUT /api/teams/<id>`, `DELETE /api/teams/<id>`

**Player Service**
- `GET /api/players`, `GET /api/players?team_id=<id>`, `GET /api/players/<id>`
- `POST /api/players` — body: `{"name": "...", "team_id": 1, "position": "...", "jersey_no": 10}`
- `PUT /api/players/<id>`, `DELETE /api/players/<id>`

**Match Service**
- `GET /api/matches`, `GET /api/matches/<id>`
- `POST /api/matches` — body: `{"home_team_id": 1, "away_team_id": 2, "venue": "..."}`
- `PATCH /api/matches/<id>/score` — body: `{"home_score": 2, "away_score": 1}`
- `PUT /api/matches/<id>/status` — body: `{"status": "live"}`
- `DELETE /api/matches/<id>`

All services also expose `GET /health`, which reports database connectivity.

## License

Provided for training purposes as part of the Skill Horizon
Infrastructure Specialist curriculum.

Deployed by: Sameerbasha
Deployed by: Sameerbasha
Test merge
