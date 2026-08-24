{{ config(materialized='table') }}

select
    seniority_level,
    count(*) as job_postings_count
from {{ ref('fct_job_postings') }}
group by seniority_level
order by job_postings_count desc
