{{ config(materialized='table') }}

-- Full rebuild each run. int_jobs_deduped is one row per job, not per day, so the
-- join stays small no matter how much history piles up.
--
-- The keyword column is a regex, so one skill can cover its own aliases and the tools
-- that imply it: SQL matches the SQL-speaking databases (not MongoDB), JavaScript
-- matches js and, through it, node.js. skill_name is unique in the seed, so a job can
-- never pick up the same skill twice even when several alternatives hit.

-- Title and description together: Adzuna returns truncated snippets (470 chars on
-- average, 205 of 250 ending in an ellipsis), so a posting called "Software Developer
-- (Go | Java | Python)" carried none of its skills when only the description was read.
-- Adds nothing for Arbeitnow and RemoteOK, whose descriptions come through whole.
with jobs as (
    select
        job_key,
        lower(coalesce(title, '') || ' ' || coalesce(description, '')) as haystack
    from {{ ref('int_jobs_deduped') }}
),

skills as (
    select skill_name, keyword, category
    from {{ ref('skills_keywords') }}
)

select
    jobs.job_key,
    skills.skill_name,
    skills.category
from jobs
inner join skills
    on {{ regexp_like('jobs.haystack', word_boundary_pattern('lower(skills.keyword)')) }}
