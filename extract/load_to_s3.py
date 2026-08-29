from __future__ import annotations

from datetime import date
from pathlib import Path


def upload_partition_to_s3(local_path: Path, source: str, run_date: date, bucket: str, region: str) -> str:
    """Upload the day's partition file to S3.

    The key has no timestamp so a re-run overwrites the day. It's Hive-style
    (`ingestion_date=<date>`) so Athena partition projection picks up new days
    without any ADD PARTITION / MSCK REPAIR.
    """
    import boto3  # lazy import so local-only runs skip the AWS deps

    key = f"raw/{source}/ingestion_date={run_date.isoformat()}/{source}.jsonl"
    client = boto3.client("s3", region_name=region)
    client.upload_file(str(local_path), bucket, key)
    return f"s3://{bucket}/{key}"
