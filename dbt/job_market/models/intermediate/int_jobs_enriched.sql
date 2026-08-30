{{ config(materialized='table') }}

-- Full rebuild each run, same as int_jobs_with_skills.
-- Seniority and work mode are regex keyword matches on the title/location/description.
-- Good enough for now; could move to something smarter if accuracy drops.

-- Título primeiro, descrição só como fallback. Medido em 970 vagas reais (Arbeitnow +
-- RemoteOK, 2026-08-29) sobre as vagas em que o título já resolve a senioridade: a
-- descrição concorda em 216 dos 248 casos em que dispara — 87% de precisão. Precisa o
-- suficiente pra desempatar, não pra substituir o título; por isso a ordem do coalesce
-- e a coluna seniority_source.
--
-- Restringir a descrição aos termos estreitos (só staff|principal, sem os DE/PT) sobe a
-- precisão pra 92%, mas rotula 53 vagas a menos. Ficou a versão ampla: troca ~11 rótulos
-- errados a mais por ~42 certos a mais, e quem precisar de precisão filtra por
-- seniority_source = 'titulo'.
--
-- Os termos DE/PT existem porque a Arbeitnow puxa pra Alemanha e a Adzuna pro Brasil:
-- werkstudent/praktikum e estágio/aprendiz eram os maiores blocos de "nao_identificado"
-- que tinham sinal claro no título.
--
-- 'auxiliar' e 'assistente' ficaram DE FORA de propósito. São nomes de cargo, não marcas
-- de senioridade: casariam com 63 vagas, quase todas fora de tecnologia, e colocariam
-- "Assistente de Farmácia" no mesmo balde que dev júnior — justamente a métrica que o
-- dashboard existe pra medir. 'director'/'vp' também ficaram fora: é trilha de gestão,
-- não o topo da trilha técnica que 'staff' representa.
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
    -- De onde veio o rótulo. O dashboard pode filtrar por 'titulo' quando quiser só o
    -- sinal de alta precisão, e dá pra monitorar a cobertura de cada fonte ao longo do tempo.
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
