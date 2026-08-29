"""Cria as tabelas raw vazias no Postgres. Usado no CI pra o dbt build ter as
sources sem precisar rodar a extração de verdade (que bate em APIs externas)."""

from __future__ import annotations

import os

import psycopg

from extract.raw_schema import postgres_column_ddl

RAW_SCHEMA = "raw_job_market"
SOURCES = ["adzuna", "arbeitnow", "remoteok"]


def main() -> None:
    dsn = os.environ["POSTGRES_DSN"]
    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{RAW_SCHEMA}"')
        for source in SOURCES:
            table = f"raw_{source}_jobs"
            cur.execute(f'CREATE TABLE IF NOT EXISTS "{RAW_SCHEMA}"."{table}" (\n    {postgres_column_ddl()}\n)')
            print(f"ok {RAW_SCHEMA}.{table}")


if __name__ == "__main__":
    main()
