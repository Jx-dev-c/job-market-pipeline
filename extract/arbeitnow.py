from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from extract.base import DEFAULT_TIMEOUT, BaseExtractor

BASE_URL = "https://www.arbeitnow.com/api/job-board-api"
MAX_PAGES = 5  # no auth/quota, but cap to keep a daily run bounded and fast


class ArbeitnowExtractor(BaseExtractor):
    source_name = "arbeitnow"

    def fetch(self, run_date: date) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        url: str | None = BASE_URL
        params = {}
        for _ in range(MAX_PAGES):
            if not url:
                break
            response = self.session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            response.raise_for_status()
            payload = response.json()
            page_results = payload.get("data", [])
            if not page_results:
                break
            records.extend(page_results)
            url = (payload.get("links") or {}).get("next")
            params = {}  # the "next" link already carries its own query string
        return records

    def normalize(self, raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        for job in raw_records:
            created_at = job.get("created_at")
            posted_at = (
                datetime.fromtimestamp(created_at, tz=timezone.utc) if isinstance(created_at, (int, float)) else None
            )
            normalized.append(
                {
                    "external_id": job.get("slug"),
                    "title": job.get("title"),
                    "company": job.get("company_name"),
                    "location_raw": job.get("location"),
                    "description": job.get("description"),
                    "url": job.get("url"),
                    "posted_at": posted_at,
                    "salary_min": None,
                    "salary_max": None,
                    "salary_currency": None,
                    "remote_flag_raw": str(job.get("remote")) if job.get("remote") is not None else None,
                }
            )
        return normalized
