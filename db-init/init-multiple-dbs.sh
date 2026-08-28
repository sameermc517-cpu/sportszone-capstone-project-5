#!/bin/bash
# Runs automatically the first time the postgres container starts
# (official postgres image convention: anything in
# /docker-entrypoint-initdb.d/ is executed on first init).
#
# SportsZone follows a database-per-service pattern: each microservice
# owns its own database inside the same Postgres instance, so a schema
# change in one service can never accidentally affect another service's
# tables. This script creates those three databases; each Flask service
# then creates its own tables inside its own database on startup via
# SQLAlchemy's create_all().

set -e

for db in sportszone_teams sportszone_players sportszone_matches; do
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE DATABASE ${db};
    GRANT ALL PRIVILEGES ON DATABASE ${db} TO ${POSTGRES_USER};
EOSQL
done
