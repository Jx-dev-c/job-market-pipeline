{{ config(materialized='table') }}

-- Full rebuild each run, same as int_jobs_with_skills.
-- Seniority and work mode are regex keyword matches on the title/location/description.
-- Good enough for now; could move to something smarter if accuracy drops.

with jobs as (
    select
        *,
        lower(title) as title_lower,
        lower(coalesce(location_raw, '') || ' ' || coalesce(title, '') || ' ' || coalesce(description, '')) as remote_haystack
    from {{ ref('int_jobs_deduped') }}
)

select
    job_key,
    source,
    external_id,
    title,
    company,
    location_raw,
    description,
    url,
    posted_at,
    salary_min,
    salary_max,
    salary_currency,
    first_seen,
    last_seen,
    case
        when {{ regexp_like('title_lower', word_boundary_pattern("'(staff|principal)'")) }} then 'staff'
        when {{ regexp_like('title_lower', word_boundary_pattern("'(senior|sr|s[ée]nior)'")) }} then 'senior'
        when {{ regexp_like('title_lower', word_boundary_pattern("'(pleno|mid[- ]level)'")) }} then 'pleno'
        when {{ regexp_like('title_lower', word_boundary_pattern("'(junior|jr|j[uú]nior|intern|est[aá]gio|trainee)'")) }} then 'junior'
        else 'nao_identificado'
    end as seniority_level,
    case
        when lower(coalesce(remote_flag_raw, '')) in ('true', '1') then 'remoto'
        when {{ regexp_like('remote_haystack', word_boundary_pattern("'(remote|remoto|home[- ]?office)'")) }} then 'remoto'
        when {{ regexp_like('remote_haystack', word_boundary_pattern("'(hybrid|h[ií]brido)'")) }} then 'hibrido'
        when location_raw is not null then 'presencial'
        else 'nao_identificado'
    end as work_mode
from jobs
