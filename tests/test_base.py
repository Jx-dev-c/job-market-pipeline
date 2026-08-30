from __future__ import annotations

import json
from datetime import date

import pytest
import requests
from pydantic import ValidationError

from extract.base import BaseExtractor, ExtractionError, NormalizedJob, parse_iso_datetime, redact_secrets

RUN_DATE = date(2026, 8, 20)


class FakeExtractor(BaseExtractor):
    source_name = "fake"

    def __init__(self, raw_dir, records):
        super().__init__(raw_dir)
        self._records = records

    def fetch(self, run_date):
        return self._records

    def normalize(self, raw_records):
        return list(raw_records)


def _job(**over):
    base = {"external_id": "1", "title": "Data Engineer", "url": "https://example.com/1"}
    base.update(over)
    return base


def test_parse_iso_datetime_handles_z_and_none():
    assert parse_iso_datetime(None) is None
    assert parse_iso_datetime("") is None
    parsed = parse_iso_datetime("2026-08-20T14:30:00Z")
    assert parsed is not None
    assert parsed.year == 2026 and parsed.hour == 14
    assert parsed.utcoffset() is not None  # became timezone-aware


def test_normalized_job_rejects_empty_required_fields():
    NormalizedJob.model_validate({**_job(), "source": "fake", "ingestion_date": RUN_DATE})
    for bad in ({"title": ""}, {"external_id": ""}, {"url": ""}):
        with pytest.raises(ValidationError):
            NormalizedJob.model_validate({**_job(**bad), "source": "fake", "ingestion_date": RUN_DATE})


def test_validate_dedupes_by_external_id(tmp_path):
    ex = FakeExtractor(tmp_path, [])
    out = ex._validate([_job(external_id="42"), _job(external_id="42", title="Other")], RUN_DATE)
    assert len(out) == 1
    assert out[0]["external_id"] == "42"


def test_validate_drops_invalid_and_stamps_source_and_date(tmp_path):
    ex = FakeExtractor(tmp_path, [])
    out = ex._validate([_job(external_id="1"), _job(external_id="2", title=None)], RUN_DATE)
    assert [r["external_id"] for r in out] == ["1"]
    assert out[0]["source"] == "fake"
    assert out[0]["ingestion_date"] == "2026-08-20"


def test_run_raises_when_below_min_expected(tmp_path):
    ex = FakeExtractor(tmp_path, [_job(title=None)])  # only record fails validation
    ex.min_expected_records = 1
    with pytest.raises(ExtractionError):
        ex.run(RUN_DATE)


def test_redact_secrets_hides_credentials_in_query_string():
    url = "https://api.adzuna.com/v1/api/jobs/br/search/1?app_id=abc123&app_key=s3cret&results_per_page=50"
    out = redact_secrets(url)
    assert "abc123" not in out
    assert "s3cret" not in out
    assert "results_per_page=50" in out


def test_run_does_not_leak_credentials_when_the_api_fails(tmp_path):
    class Failing(FakeExtractor):
        def fetch(self, run_date):
            raise requests.exceptions.RetryError(
                "too many 503 error responses for url: https://api.adzuna.com/search/1?app_key=s3cret"
            )

    ex = Failing(tmp_path, [])
    with pytest.raises(ExtractionError) as caught:
        ex.run(RUN_DATE)
    assert "s3cret" not in str(caught.value)
    # chain suppressed, otherwise the raw URL comes back via logger.exception
    assert caught.value.__cause__ is None
    assert caught.value.__suppress_context__


def test_run_writes_partition_file(tmp_path):
    ex = FakeExtractor(tmp_path, [_job(external_id="1"), _job(external_id="2")])
    out_path = ex.run(RUN_DATE)
    assert out_path == tmp_path / "fake" / "dt=2026-08-20" / "fake.jsonl"
    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert {json.loads(line)["external_id"] for line in lines} == {"1", "2"}
