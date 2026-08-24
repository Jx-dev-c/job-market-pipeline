{{ config(materialized='table') }}

select
    work_mode,
    count(*) as job_postings_count
from {{ ref('fct_job_postings') }}
group by work_mode
order by job_postings_count desc
