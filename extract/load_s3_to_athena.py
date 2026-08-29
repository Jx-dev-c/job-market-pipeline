from __future__ import annotations

import time

from extract.raw_schema import RAW_JOB_SCHEMA_FIELDS

# ingestion_date is the partition key (value comes from the S3 path), so it's not a
# table column here. Everything else maps 1:1 from the JSONL.
_PARTITION_FIELD = "ingestion_date"

_LOGICAL_TO_ATHENA = {
    "STRING": "string",
    # posted_at stays a string; the JSON SerDe doesn't parse ISO-8601 timestamps
    # cleanly, so staging casts it (parse_timestamp macro).
    "TIMESTAMP": "string",
    "FLOAT64": "double",
    "DATE": "date",
}


def _athena_columns() -> str:
    cols = []
    for name, logical_type, _mode in RAW_JOB_SCHEMA_FIELDS:
        if name == _PARTITION_FIELD:
            continue
        cols.append(f"`{name}` {_LOGICAL_TO_ATHENA[logical_type]}")
    return ",\n    ".join(cols)


def _run_query(client, sql: str, database: str, workgroup: str, output_location: str) -> None:
    resp = client.start_query_execution(
        QueryString=sql,
        QueryExecutionContext={"Database": database},
        WorkGroup=workgroup,
        ResultConfiguration={"OutputLocation": output_location},
    )
    query_id = resp["QueryExecutionId"]
    while True:
        status = client.get_query_execution(QueryExecutionId=query_id)["QueryExecution"]["Status"]
        state = status["State"]
        if state in ("SUCCEEDED", "FAILED", "CANCELLED"):
            break
        time.sleep(1)
    if state != "SUCCEEDED":
        reason = status.get("StateChangeReason", "unknown")
        raise RuntimeError(f"Athena query {state}: {reason}\nSQL:\n{sql}")


def ensure_athena_raw_table(
    source: str,
    bucket: str,
    region: str,
    database: str,
    workgroup: str,
    s3_staging_dir: str,
) -> None:
    """Create the Glue database and external table for one source if they don't exist.

    The table uses partition projection on ingestion_date, so a new day's file is
    queryable as soon as it's in S3 (no ADD PARTITION). Both statements are
    IF NOT EXISTS and DDL doesn't scan data, so it's cheap to run every time.
    """
    import boto3  # lazy import so a plain extraction run doesn't need the AWS deps

    client = boto3.client("athena", region_name=region)
    table = f"raw_{source}_jobs"
    location = f"s3://{bucket}/raw/{source}/"

    _run_query(client, f"CREATE DATABASE IF NOT EXISTS `{database}`", "default", workgroup, s3_staging_dir)

    create_sql = f"""
CREATE EXTERNAL TABLE IF NOT EXISTS `{database}`.`{table}` (
    {_athena_columns()}
)
PARTITIONED BY (`{_PARTITION_FIELD}` date)
ROW FORMAT SERDE 'org.openx.data.jsonserde.JsonSerDe'
WITH SERDEPROPERTIES ('ignore.malformed.json' = 'true')
LOCATION '{location}'
TBLPROPERTIES (
    'projection.enabled' = 'true',
    'projection.{_PARTITION_FIELD}.type' = 'date',
    'projection.{_PARTITION_FIELD}.format' = 'yyyy-MM-dd',
    'projection.{_PARTITION_FIELD}.range' = '2026-01-01,NOW',
    'projection.{_PARTITION_FIELD}.interval' = '1',
    'projection.{_PARTITION_FIELD}.interval.unit' = 'DAYS',
    'storage.location.template' = '{location}{_PARTITION_FIELD}=${{{_PARTITION_FIELD}}}/'
)
""".strip()
    _run_query(client, create_sql, database, workgroup, s3_staging_dir)
