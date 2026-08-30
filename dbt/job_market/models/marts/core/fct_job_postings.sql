{{ config(materialized='table') }}

-- Escopo dos marts: só vagas que casam com pelo menos uma skill do skills_keywords.csv.
-- As fontes são boards generalistas e ~75% do que entra não é vaga de tecnologia
-- (açougueiro, atendente de farmácia). A base completa continua em int_jobs_enriched;
-- o corte fica aqui porque é o grão que os marts analíticos consomem.
with jobs as (
    select * from {{ ref('int_jobs_enriched') }}
),

vagas_tech as (
    select distinct job_key from {{ ref('int_jobs_with_skills') }}
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
inner join vagas_tech on vagas_tech.job_key = jobs.job_key
left join companies on companies.company_name = jobs.company
