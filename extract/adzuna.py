from __future__ import annotations

from datetime import date
from typing import Any

from extract.base import DEFAULT_TIMEOUT, BaseExtractor, ExtractionError, parse_iso_datetime

BASE_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
RESULTS_PER_PAGE = 50
MAX_PAGES = 5  # cap to respect the free-tier daily request quota


class AdzunaExtractor(BaseExtractor):
    source_name = "adzuna"

    def __init__(self, raw_dir, app_id: str | None, app_key: str | None, country: str = "br"):
        super().__init__(raw_dir)
        if not app_id or not app_key:
            raise ExtractionError("adzuna: ADZUNA_APP_ID/ADZUNA_APP_KEY not set")
        self.app_id = app_id
        self.app_key = app_key
        self.country = country

    def fetch(self, run_date: date) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for page in range(1, MAX_PAGES + 1):
            url = BASE_URL.format(country=self.country, page=page)
            response = self.session.get(
                url,
                params={
                    "app_id": self.app_id,
                    "app_key": self.app_key,
                    "results_per_page": RESULTS_PER_PAGE,
                    "content-type": "application/json",
                },
                timeout=DEFAULT_TIMEOUT,
            )
            response.raise_for_status()
            page_results = response.json().get("results", [])
            if not page_results:
                break
            records.extend(page_results)
        return records

    def normalize(self, raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        for job in raw_records:
            normalized.append(
                {
                    "external_id": str(job.get("id")),
                    "title": job.get("title"),
                    "company": (job.get("company") or {}).get("display_name"),
                    "location_raw": (job.get("location") or {}).get("display_name"),
                    "description": job.get("description"),
                    "url": job.get("redirect_url"),
                    "posted_at": parse_iso_datetime(job.get("created")),
                    "salary_min": job.get("salary_min"),
                    "salary_max": job.get("salary_max"),
                    "salary_currency": None,
                    "remote_flag_raw": None,  # Adzuna doesn't expose an explicit remote flag
                }
            )
        return normalized
