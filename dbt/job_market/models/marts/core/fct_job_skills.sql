{{ config(materialized='table') }}

with bridge as (
    select job_key, skill_name
    from {{ ref('int_jobs_with_skills') }}
),

skills as (
    select skill_key, skill_name from {{ ref('dim_skill') }}
)

select
    bridge.job_key,
    skills.skill_key
from bridge
inner join skills on skills.skill_name = bridge.skill_name
