{{ config(materialized='table') }}

with jobs as (
    select company
    from {{ ref('int_jobs_enriched') }}
    where company is not null
)

select
    {{ dbt_utils.generate_surrogate_key(['company']) }} as company_key,
    company as company_name,
    count(*) as job_postings_count
from jobs
group by company
