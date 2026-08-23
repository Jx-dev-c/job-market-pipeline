from __future__ import annotations

from datetime import date

from extract.raw_schema import RAW_JOB_SCHEMA_FIELDS


def load_source_to_bigquery(
    source: str,
    run_date: date,
    gcs_uri: str,
    project: str,
    raw_dataset: str,
) -> None:
    """Load one day's GCS partition into the raw dataset.

    Writes to a single BigQuery partition via the `$YYYYMMDD` decorator, so a re-run
    for the same day replaces rather than duplicates.
    """
    from google.cloud import bigquery  # lazy import so local-only runs skip the GCP deps

    client = bigquery.Client(project=project)
    schema = [bigquery.SchemaField(name, field_type, mode=mode) for name, field_type, mode in RAW_JOB_SCHEMA_FIELDS]
    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
        schema=schema,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        time_partitioning=bigquery.TimePartitioning(field="ingestion_date"),
    )
    table_id = f"{project}.{raw_dataset}.raw_{source}_jobs${run_date.strftime('%Y%m%d')}"
    load_job = client.load_table_from_uri(gcs_uri, table_id, job_config=job_config)
    load_job.result()
