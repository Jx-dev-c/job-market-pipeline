from __future__ import annotations

from extract.raw_schema import FIELD_NAMES, RAW_JOB_SCHEMA_FIELDS, postgres_column_ddl


def test_field_names_match_schema_order():
    assert FIELD_NAMES == [name for name, _, _ in RAW_JOB_SCHEMA_FIELDS]
    assert FIELD_NAMES[0] == "source"
    assert FIELD_NAMES[-1] == "ingestion_date"


def test_postgres_ddl_types_and_nullability():
    ddl = postgres_column_ddl()
    assert '"source" TEXT NOT NULL' in ddl
    assert '"salary_min" DOUBLE PRECISION' in ddl
    assert '"posted_at" TIMESTAMPTZ' in ddl
    assert '"ingestion_date" DATE NOT NULL' in ddl
    # nullable columns must not be marked NOT NULL
    assert '"company" TEXT,' in ddl or ddl.strip().endswith('"company" TEXT')
