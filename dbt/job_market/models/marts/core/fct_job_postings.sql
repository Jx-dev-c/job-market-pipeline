{{ config(materialized='table') }}

with jobs as (
    select * from {{ ref('int_jobs_enriched') }}
),

companies as (
    select company_key, company_name from {{ ref('dim_company') }}
)

select
    jobs.job_key,
    companies.company_key,
    jobs.source,
    jobs.title,
    jobs.location_raw,
    jobs.url,
    jobs.posted_at,
    jobs.salary_min,
    jobs.salary_max,
    jobs.salary_currency,
    jobs.seniority_level,
    jobs.work_mode,
    jobs.first_seen,
    jobs.last_seen
from jobs
left join companies on companies.company_name = jobs.company
