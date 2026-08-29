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
from extract.load_s3_to_athena import ensure_athena_raw_table
from extract.load_to_gcs import upload_partition_to_gcs
from extract.load_to_postgres import load_source_to_postgres
from extract.load_to_s3 import upload_partition_to_s3
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
    # AWS (produção)
    parser.add_argument("--upload-s3", action="store_true", help="Upload the partition file to S3")
    parser.add_argument(
        "--load-athena", action="store_true", help="Create the Athena external table if missing (implies --upload-s3)"
    )
    # GCP (legado, ver docs/migrar_para_gcp.md)
    parser.add_argument("--upload-gcs", action="store_true", help="Upload the partition file to GCS")
    parser.add_argument(
        "--load-bq", action="store_true", help="Load the GCS partition into BigQuery (implies --upload-gcs)"
    )
    # local
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

    if args.upload_s3 or args.load_athena:
        if not settings.s3_raw_bucket:
            logger.error("S3_RAW_BUCKET not set, cannot upload")
            return 1
        s3_uri = upload_partition_to_s3(local_path, args.source, run_date, settings.s3_raw_bucket, settings.aws_region)
        logger.info("uploaded to %s", s3_uri)

        if args.load_athena:
            ensure_athena_raw_table(
                args.source,
                settings.s3_raw_bucket,
                settings.aws_region,
                settings.athena_database,
                settings.athena_workgroup,
                settings.athena_s3_staging_dir,
            )
            logger.info("%s: Athena external table ready (partition %s)", args.source, run_date.isoformat())

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
