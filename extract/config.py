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
    jooble_api_key: str | None
    gcp_project_id: str | None
    gcs_raw_bucket: str | None
    bq_raw_dataset: str
    postgres_dsn: str | None
    raw_data_dir: Path


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        adzuna_app_id=os.getenv("ADZUNA_APP_ID") or None,
        adzuna_app_key=os.getenv("ADZUNA_APP_KEY") or None,
        adzuna_country=os.getenv("ADZUNA_COUNTRY", "br"),
        jooble_api_key=os.getenv("JOOBLE_API_KEY") or None,
        gcp_project_id=os.getenv("GCP_PROJECT_ID") or None,
        gcs_raw_bucket=os.getenv("GCS_RAW_BUCKET") or None,
        bq_raw_dataset=os.getenv("BQ_RAW_DATASET", "raw_job_market"),
        postgres_dsn=os.getenv("POSTGRES_DSN") or None,
        raw_data_dir=Path(os.getenv("RAW_DATA_DIR", "/data/raw")),
    )
