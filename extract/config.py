from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    adzuna_app_id: str | None
    adzuna_app_key: str | None
    adzuna_country: str
    adzuna_category: str | None
    jooble_api_key: str | None
    gcp_project_id: str | None
    gcs_raw_bucket: str | None
    bq_raw_dataset: str
    postgres_dsn: str | None
    raw_data_dir: Path
    # AWS (S3 + Athena/Glue)
    s3_raw_bucket: str | None
    aws_region: str
    athena_database: str
    athena_workgroup: str
    athena_s3_staging_dir: str


def load_settings() -> Settings:
    load_dotenv()
    s3_raw_bucket = os.getenv("S3_RAW_BUCKET") or None
    athena_s3_staging_dir = os.getenv("ATHENA_S3_STAGING_DIR") or (
        f"s3://{s3_raw_bucket}/athena-results/" if s3_raw_bucket else ""
    )
    return Settings(
        adzuna_app_id=os.getenv("ADZUNA_APP_ID") or None,
        adzuna_app_key=os.getenv("ADZUNA_APP_KEY") or None,
        adzuna_country=os.getenv("ADZUNA_COUNTRY", "br"),
        # Sem categoria a busca varre o país inteiro (857k vagas no br) e só ~2% delas
        # casam com alguma skill de tecnologia. Vazio desliga o filtro.
        adzuna_category=os.getenv("ADZUNA_CATEGORY", "it-jobs") or None,
        jooble_api_key=os.getenv("JOOBLE_API_KEY") or None,
        gcp_project_id=os.getenv("GCP_PROJECT_ID") or None,
        gcs_raw_bucket=os.getenv("GCS_RAW_BUCKET") or None,
        bq_raw_dataset=os.getenv("BQ_RAW_DATASET", "raw_job_market"),
        postgres_dsn=os.getenv("POSTGRES_DSN") or None,
        raw_data_dir=Path(os.getenv("RAW_DATA_DIR", "/data/raw")),
        s3_raw_bucket=s3_raw_bucket,
        aws_region=os.getenv("AWS_DEFAULT_REGION", "us-east-2"),
        athena_database=os.getenv("GLUE_RAW_DATABASE", "raw_job_market"),
        athena_workgroup=os.getenv("ATHENA_WORKGROUP", "primary"),
        athena_s3_staging_dir=athena_s3_staging_dir,
    )
