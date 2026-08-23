#!/bin/bash
# Runs once on first container init, as the airflow superuser.
# Creates a second database and user (job_market) so the pipeline data isn't mixed
# in with Airflow's metadata DB.
set -euo pipefail

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER ${POSTGRES_JOB_MARKET_USER} WITH PASSWORD '${POSTGRES_JOB_MARKET_PASSWORD}';
    CREATE DATABASE ${POSTGRES_JOB_MARKET_DB} OWNER ${POSTGRES_JOB_MARKET_USER};
EOSQL
