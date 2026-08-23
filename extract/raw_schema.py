"""Raw-layer schema, shared by every loader so they don't drift apart."""

from __future__ import annotations

# (field_name, logical_type, mode). mode is "REQUIRED" or "NULLABLE" (BigQuery's
# vocabulary); the Postgres loader maps REQUIRED to NOT NULL.
RAW_JOB_SCHEMA_FIELDS = [
    ("source", "STRING", "REQUIRED"),
    ("external_id", "STRING", "REQUIRED"),
    ("title", "STRING", "REQUIRED"),
    ("company", "STRING", "NULLABLE"),
    ("location_raw", "STRING", "NULLABLE"),
    ("description", "STRING", "NULLABLE"),
    ("url", "STRING", "REQUIRED"),
    ("posted_at", "TIMESTAMP", "NULLABLE"),
    ("salary_min", "FLOAT64", "NULLABLE"),
    ("salary_max", "FLOAT64", "NULLABLE"),
    ("salary_currency", "STRING", "NULLABLE"),
    ("remote_flag_raw", "STRING", "NULLABLE"),
    ("ingestion_date", "DATE", "REQUIRED"),
]

_LOGICAL_TO_POSTGRES = {
    "STRING": "TEXT",
    "TIMESTAMP": "TIMESTAMPTZ",
    "FLOAT64": "DOUBLE PRECISION",
    "DATE": "DATE",
}


def postgres_column_ddl() -> str:
    columns = []
    for name, logical_type, mode in RAW_JOB_SCHEMA_FIELDS:
        pg_type = _LOGICAL_TO_POSTGRES[logical_type]
        not_null = " NOT NULL" if mode == "REQUIRED" else ""
        columns.append(f'"{name}" {pg_type}{not_null}')
    return ",\n    ".join(columns)


FIELD_NAMES = [name for name, _, _ in RAW_JOB_SCHEMA_FIELDS]
