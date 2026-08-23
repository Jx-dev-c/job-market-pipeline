from __future__ import annotations

from datetime import date
from pathlib import Path


def upload_partition_to_gcs(local_path: Path, source: str, run_date: date, bucket_name: str) -> str:
    """Upload the day's partition file to a fixed blob path.

    The path has no timestamp, so re-running a day overwrites instead of piling up
    duplicate files.
    """
    from google.cloud import storage  # lazy import so local-only runs skip the GCP deps

    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob_path = f"raw/{source}/dt={run_date.isoformat()}/{source}.jsonl"
    blob = bucket.blob(blob_path)
    blob.upload_from_filename(str(local_path))
    return f"gs://{bucket_name}/{blob_path}"
