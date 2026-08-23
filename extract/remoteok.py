from __future__ import annotations

from datetime import date
from typing import Any

from extract.base import DEFAULT_TIMEOUT, BaseExtractor, parse_iso_datetime

BASE_URL = "https://remoteok.com/api"


class RemoteOKExtractor(BaseExtractor):
    source_name = "remoteok"
    # RemoteOK returns 403 for the default requests User-Agent, so set our own.
    user_agent = "job-market-pipeline/1.0 (portfolio project; contact via GitHub repo)"

    def fetch(self, run_date: date) -> list[dict[str, Any]]:
        response = self.session.get(BASE_URL, timeout=DEFAULT_TIMEOUT)
        response.raise_for_status()
        payload = response.json()
        # first element is always a legal/notice object, not a job
        return [item for item in payload if "id" in item and "legal" not in item]

    def normalize(self, raw_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        normalized = []
        for job in raw_records:
            normalized.append(
                {
                    "external_id": str(job.get("id")),
                    "title": job.get("position"),
                    "company": job.get("company"),
                    "location_raw": job.get("location"),
                    "description": job.get("description"),
                    "url": job.get("url"),
                    "posted_at": parse_iso_datetime(job.get("date")),
                    # RemoteOK sends 0 when salary isn't disclosed, so coerce it to None.
                    "salary_min": job.get("salary_min") or None,
                    "salary_max": job.get("salary_max") or None,
                    "salary_currency": None,
                    "remote_flag_raw": "true",  # everything on RemoteOK is remote
                }
            )
        return normalized
