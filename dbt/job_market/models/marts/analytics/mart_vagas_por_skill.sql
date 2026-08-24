{{ config(materialized='table') }}

select
    d.skill_name,
    d.category,
    count(*) as job_postings_count
from {{ ref('fct_job_skills') }} f
inner join {{ ref('dim_skill') }} d on d.skill_key = f.skill_key
group by d.skill_name, d.category
order by job_postings_count desc
