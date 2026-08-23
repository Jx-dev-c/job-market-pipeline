from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime

from extract.adzuna import AdzunaExtractor
from extract.arbeitnow import ArbeitnowExtractor
from extract.base import BaseExtractor, ExtractionError
from extract.config import load_settings
from extract.load_gcs_to_bigquery import load_source_to_bigquery
from extract.load_to_gcs import upload_partition_to_gcs
from extract.load_to_postgres import load_source_to_postgres
from extract.remoteok import RemoteOKExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)


def build_extractor(source: str, settings) -> BaseExtractor:
    if source == "adzuna":
        return AdzunaExtractor(
            settings.raw_data_dir,
            app_id=settings.adzuna_app_id,
            app_key=settings.adzuna_app_key,
            country=settings.adzuna_country,
        )
    if source == "arbeitnow":
        return ArbeitnowExtractor(settings.raw_data_dir)
    if source == "remoteok":
        return RemoteOKExtractor(settings.raw_data_dir)
    raise ValueError(f"unknown source: {source}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract job postings from a single source into the raw layer.")
    parser.add_argument("--source", required=True, choices=["adzuna", "arbeitnow", "remoteok"])
    parser.add_argument("--date", default=None, help="Run date as YYYY-MM-DD (default: today, UTC)")
    parser.add_argument("--upload-gcs", action="store_true", help="Upload the partition file to GCS")
    parser.add_argument("--load-bq", action="store_true", help="Load the GCS partition into BigQuery (implies --upload-gcs)")
    parser.add_argument("--load-postgres", action="store_true", help="Load the partition into local Postgres")
    args = parser.parse_args()

    run_date = datetime.strptime(args.date, "%Y-%m-%d").date() if args.date else date.today()
    settings = load_settings()

    extractor = build_extractor(args.source, settings)
    try:
        local_path = extractor.run(run_date)
    except ExtractionError:
        logger.exception("%s: extraction failed", args.source)
        return 1

    if args.upload_gcs or args.load_bq:
        if not settings.gcs_raw_bucket:
            logger.error("GCS_RAW_BUCKET not set, cannot upload")
            return 1
        gcs_uri = upload_partition_to_gcs(local_path, args.source, run_date, settings.gcs_raw_bucket)
        logger.info("uploaded to %s", gcs_uri)

        if args.load_bq:
            if not settings.gcp_project_id:
                logger.error("GCP_PROJECT_ID not set, cannot load into BigQuery")
                return 1
            load_source_to_bigquery(args.source, run_date, gcs_uri, settings.gcp_project_id, settings.bq_raw_dataset)
            logger.info("%s: loaded partition %s into BigQuery", args.source, run_date.isoformat())

    if args.load_postgres:
        if not settings.postgres_dsn:
            logger.error("POSTGRES_DSN not set, cannot load into Postgres")
            return 1
        row_count = load_source_to_postgres(args.source, run_date, local_path, settings.postgres_dsn)
        logger.info("%s: loaded %d rows for partition %s into Postgres", args.source, row_count, run_date.isoformat())

    return 0


if __name__ == "__main__":
    sys.exit(main())
