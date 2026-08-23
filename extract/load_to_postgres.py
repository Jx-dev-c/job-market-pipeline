from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

from extract.raw_schema import FIELD_NAMES, postgres_column_ddl

RAW_SCHEMA = "raw_job_market"


def _parse_row(raw: dict) -> tuple:
    posted_at = raw.get("posted_at")
    return (
        raw["source"],
        raw["external_id"],
        raw["title"],
        raw.get("company"),
        raw.get("location_raw"),
        raw.get("description"),
        raw["url"],
        datetime.fromisoformat(posted_at) if posted_at else None,
        raw.get("salary_min"),
        raw.get("salary_max"),
        raw.get("salary_currency"),
        raw.get("remote_flag_raw"),
        date.fromisoformat(raw["ingestion_date"]),
    )


def load_source_to_postgres(source: str, run_date: date, jsonl_path: Path, dsn: str) -> int:
    """Load one day's JSONL partition into Postgres.

    Replaces just that source+day's rows in a single transaction (DELETE then
    INSERT, plus the CREATE IF NOT EXISTS), so re-running the same day is idempotent.
    """
    import psycopg  # lazy import so a plain extraction run doesn't need the driver

    table = f"raw_{source}_jobs"
    rows = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(_parse_row(json.loads(line)))

    with psycopg.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{RAW_SCHEMA}"')
        cur.execute(f'CREATE TABLE IF NOT EXISTS "{RAW_SCHEMA}"."{table}" (\n    {postgres_column_ddl()}\n)')
        cur.execute(
            f'CREATE INDEX IF NOT EXISTS "{table}_ingestion_date_idx" ON "{RAW_SCHEMA}"."{table}" (ingestion_date)'
        )
        cur.execute(f'DELETE FROM "{RAW_SCHEMA}"."{table}" WHERE ingestion_date = %s', [run_date])
        if rows:
            columns = ", ".join(f'"{name}"' for name in FIELD_NAMES)
            placeholders = ", ".join(["%s"] * len(FIELD_NAMES))
            cur.executemany(
                f'INSERT INTO "{RAW_SCHEMA}"."{table}" ({columns}) VALUES ({placeholders})',
                rows,
            )
        # psycopg's context manager commits on clean exit and rolls back on error,
        # so the DDL, delete and insert land together or not at all.
    return len(rows)
