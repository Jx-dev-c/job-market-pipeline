from __future__ import annotations

import abc
import json
import logging
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import requests
from pydantic import BaseModel, Field, ValidationError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 15

# Adzuna takes its credentials as query params, so requests puts them in the URL and
# every requests exception repeats that URL in its message. Redact before logging.
_SECRET_QUERY_PARAM = re.compile(r"([?&](?:app_id|app_key|api_key|key|token)=)[^&\s]+", re.IGNORECASE)


def redact_secrets(text: str) -> str:
    return _SECRET_QUERY_PARAM.sub(r"\1<redacted>", text)


class ExtractionError(RuntimeError):
    """Source couldn't produce a valid partition."""


class NormalizedJob(BaseModel):
    """Shape every extractor maps into before writing raw JSONL.

    Validated here (not only in dbt staging) so an API format change breaks the
    extraction instead of quietly poisoning the raw layer.
    """

    source: str
    external_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    company: str | None = None
    location_raw: str | None = None
    description: str | None = None
    url: str = Field(min_length=1)
    posted_at: datetime | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    salary_currency: str | None = None
    remote_flag_raw: str | None = None
    ingestion_date: date


class BaseExtractor(abc.ABC):
    source_name: str
    user_agent: str = "job-market-pipeline/1.0 (portfolio project)"
    min_expected_records: int = 1

    def __init__(self, raw_dir: Path):
        self.raw_dir = raw_dir
        self.session = self._build_session()

    def _build_session(self) -> requests.Session:
        session = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=1.5,
            status_forcelist=[429, 500, 502, 503, 504],
            respect_retry_after_header=True,
            allowed_methods=["GET", "POST"],
        )
        adapter = HTTPAdapter(max_retries=retry)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({"User-Agent": self.user_agent})
        return session

    @abc.abstractmethod
    def fetch(self, run_date: date) -> list[dict[str, Any]]:
        """Fetch raw records from the source API (source-native shape)."""

    @abc.abstractmethod
    def normalize(self, raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Map source-native records into NormalizedJob field names.

        No business logic here (skill extraction, seniority parsing). That's dbt's job.
        """

    def _validate(self, records: list[dict[str, Any]], run_date: date) -> list[dict[str, Any]]:
        valid: list[dict[str, Any]] = []
        seen_external_ids: set[str] = set()
        errors = 0
        duplicates = 0
        for record in records:
            # Arbeitnow (and possibly others) can return the same posting on two pages
            # when new jobs are inserted between page requests. Dedupe by external_id
            # here so every source is covered.
            external_id = record.get("external_id")
            if external_id in seen_external_ids:
                duplicates += 1
                continue
            seen_external_ids.add(external_id)
            record = {**record, "source": self.source_name, "ingestion_date": run_date}
            try:
                valid.append(NormalizedJob.model_validate(record).model_dump(mode="json"))
            except ValidationError as exc:
                errors += 1
                logger.warning("%s: skipping invalid record: %s", self.source_name, exc)
        if duplicates:
            logger.warning("%s: skipped %d duplicate external_id(s) within this fetch", self.source_name, duplicates)
        if errors:
            logger.warning("%s: %d/%d records failed validation", self.source_name, errors, len(records))
        return valid

    def write_raw(self, records: list[dict[str, Any]], run_date: date) -> Path:
        partition_dir = self.raw_dir / self.source_name / f"dt={run_date.isoformat()}"
        partition_dir.mkdir(parents=True, exist_ok=True)
        out_path = partition_dir / f"{self.source_name}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        return out_path

    def run(self, run_date: date) -> Path:
        try:
            raw = self.fetch(run_date)
        except requests.RequestException as exc:
            # `from None` on purpose: chaining would put the original exception (URL and
            # all) back in the traceback that run_extraction logs.
            raise ExtractionError(f"{self.source_name}: request failed: {redact_secrets(str(exc))}") from None
        normalized = self.normalize(raw)
        validated = self._validate(normalized, run_date)
        if len(validated) < self.min_expected_records:
            raise ExtractionError(
                f"{self.source_name}: only {len(validated)} valid record(s) for {run_date.isoformat()}, "
                f"expected at least {self.min_expected_records}, not writing the partition"
            )
        path = self.write_raw(validated, run_date)
        logger.info("%s: wrote %d records to %s", self.source_name, len(validated), path)
        return path


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))
