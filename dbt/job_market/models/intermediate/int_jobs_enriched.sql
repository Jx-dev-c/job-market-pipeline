{{ config(materialized='table') }}

-- Full rebuild each run, same as int_jobs_with_skills.
-- Seniority and work mode are regex keyword matches on the title/location/description.
-- Good enough for now; could move to something smarter if accuracy drops.

-- Title first, description only as a fallback. On the postings the title already
-- labels, the description agrees 216 times out of 248 (87%), so it's good enough to
-- break a tie but not to outrank the title. seniority_source says which one answered.
-- The DE/PT terms are here because Arbeitnow skews German and Adzuna Brazilian; they
-- were the biggest blocks of unlabelled postings with a clear signal in the title.
-- 'auxiliar'/'assistente' and 'director'/'vp' stay out on purpose: the first two are
-- job names and the last two a management ladder, neither is a seniority level.
{% set staff_pattern = "'(staff|principal|(tech|team|technical|engineering|squad|dev|development|data)[ -]lead|lead[ -](engineer|developer|architect|scientist)|head of)'" %}
{% set senior_pattern = "'(senior|sr|s[ée]nior)'" %}
{% set pleno_pattern = "'(pleno|mid[- ]level)'" %}
{% set junior_pattern = "'(junior|jr|j[uú]nior|intern|internship|est[aá]gio|estagi[aá]ri[oa]|aprendiz|trainee|werkstudent\\w*|working student|praktikum|praktikant\\w*|ausbildung|auszubildende\\w*|berufseinstieg)'" %}

with jobs as (
    select
        *,
        lower(title) as title_lower,
        lower(coalesce(description, '')) as description_lower,
        lower(coalesce(location_raw, '') || ' ' || coalesce(title, '') || ' ' || coalesce(description, '')) as remote_haystack
    from {{ ref('int_jobs_deduped') }}
),

classified as (
    select
        *,
        case
            when {{ regexp_like('title_lower', word_boundary_pattern(staff_pattern)) }} then 'staff'
            when {{ regexp_like('title_lower', word_boundary_pattern(senior_pattern)) }} then 'senior'
            when {{ regexp_like('title_lower', word_boundary_pattern(pleno_pattern)) }} then 'pleno'
            when {{ regexp_like('title_lower', word_boundary_pattern(junior_pattern)) }} then 'junior'
        end as seniority_from_title,
        case
            when {{ regexp_like('description_lower', word_boundary_pattern(staff_pattern)) }} then 'staff'
            when {{ regexp_like('description_lower', word_boundary_pattern(senior_pattern)) }} then 'senior'
            when {{ regexp_like('description_lower', word_boundary_pattern(pleno_pattern)) }} then 'pleno'
            when {{ regexp_like('description_lower', word_boundary_pattern(junior_pattern)) }} then 'junior'
        end as seniority_from_description
    from jobs
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
    coalesce(seniority_from_title, seniority_from_description, 'nao_identificado') as seniority_level,
    case
        when seniority_from_title is not null then 'titulo'
        when seniority_from_description is not null then 'descricao'
        else 'nenhuma'
    end as seniority_source,
    case
        when lower(coalesce(remote_flag_raw, '')) in ('true', '1') then 'remoto'
        when {{ regexp_like('remote_haystack', word_boundary_pattern("'(remote|remoto|home[- ]?office)'")) }} then 'remoto'
        when {{ regexp_like('remote_haystack', word_boundary_pattern("'(hybrid|h[ií]brido)'")) }} then 'hibrido'
        when location_raw is not null then 'presencial'
        else 'nao_identificado'
    end as work_mode
from classified
