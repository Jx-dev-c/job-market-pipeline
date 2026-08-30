from __future__ import annotations

from extract.adzuna import AdzunaExtractor
from extract.arbeitnow import ArbeitnowExtractor
from extract.remoteok import RemoteOKExtractor


def test_adzuna_normalize_maps_nested_fields(tmp_path):
    ex = AdzunaExtractor(tmp_path, app_id="x", app_key="y")
    raw = {
        "id": 12345,
        "title": "Data Engineer",
        "company": {"display_name": "ACME"},
        "location": {"display_name": "Sao Paulo"},
        "description": "...",
        "redirect_url": "https://adzuna/12345",
        "created": "2026-08-19T16:47:31Z",
        "salary_min": 8000.0,
        "salary_max": 12000.0,
    }
    (job,) = ex.normalize([raw])
    assert job["external_id"] == "12345"
    assert job["company"] == "ACME"
    assert job["location_raw"] == "Sao Paulo"
    assert job["url"] == "https://adzuna/12345"
    assert job["posted_at"].year == 2026
    assert job["salary_min"] == 8000.0
    assert job["remote_flag_raw"] is None


def test_adzuna_sends_category_only_when_set(tmp_path):
    enviados = {}

    def fake_get(url, params=None, timeout=None):
        enviados.update(params)

        class R:
            status_code = 200

            def raise_for_status(self):
                pass

            def json(self):
                return {"results": []}

        return R()

    com = AdzunaExtractor(tmp_path, app_id="x", app_key="y", category="it-jobs")
    com.session.get = fake_get
    com.fetch(None)
    assert enviados["category"] == "it-jobs"

    enviados.clear()
    sem = AdzunaExtractor(tmp_path, app_id="x", app_key="y")
    sem.session.get = fake_get
    sem.fetch(None)
    assert "category" not in enviados


def test_adzuna_normalize_tolerates_missing_company_and_location(tmp_path):
    ex = AdzunaExtractor(tmp_path, app_id="x", app_key="y")
    (job,) = ex.normalize([{"id": 1, "title": "X", "redirect_url": "u"}])
    assert job["company"] is None
    assert job["location_raw"] is None


def test_arbeitnow_normalize_converts_unix_timestamp_and_remote_flag(tmp_path):
    ex = ArbeitnowExtractor(tmp_path)
    raw = {
        "slug": "data-engineer-acme",
        "title": "Data Engineer",
        "company_name": "ACME",
        "location": "Berlin",
        "description": "...",
        "url": "https://arbeitnow/data-engineer-acme",
        "created_at": 1755620851,
        "remote": True,
    }
    (job,) = ex.normalize([raw])
    assert job["external_id"] == "data-engineer-acme"
    assert job["posted_at"].tzinfo is not None
    assert job["remote_flag_raw"] == "True"


def test_arbeitnow_normalize_handles_missing_created_at(tmp_path):
    ex = ArbeitnowExtractor(tmp_path)
    (job,) = ex.normalize([{"slug": "s", "title": "t", "url": "u", "remote": None}])
    assert job["posted_at"] is None
    assert job["remote_flag_raw"] is None


def test_remoteok_normalize_zero_salary_becomes_none(tmp_path):
    ex = RemoteOKExtractor(tmp_path)
    raw = {
        "id": 999,
        "position": "Backend Engineer",
        "company": "Remote Co",
        "location": "Worldwide",
        "description": "...",
        "url": "https://remoteok/999",
        "date": "2026-08-23T17:09:06+00:00",
        "salary_min": 0,
        "salary_max": 0,
    }
    (job,) = ex.normalize([raw])
    assert job["title"] == "Backend Engineer"
    assert job["salary_min"] is None
    assert job["salary_max"] is None
    assert job["remote_flag_raw"] == "true"


def test_remoteok_fetch_filters_legal_notice_object(tmp_path):
    ex = RemoteOKExtractor(tmp_path)
    payload = [
        {"legal": "notice", "id": 0},
        {"id": 1, "position": "Dev", "url": "u"},
    ]

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return payload

    ex.session.get = lambda *a, **k: _Resp()
    records = ex.fetch(run_date=None)
    assert [r["id"] for r in records] == [1]
