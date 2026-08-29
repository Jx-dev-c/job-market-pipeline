{{ config(
    materialized='incremental',
    unique_key='job_key',
    incremental_strategy=('merge' if target.type == 'athena' else 'delete+insert'),
) }}

-- Only truly incremental model in the project. It reads the growing unioned raw
-- history; everything downstream reads this deduped, bounded table, so those can
-- full-refresh cheaply.
-- Strategy differs by target (Postgres: delete+insert; Athena: merge on an Iceberg
-- table, see +table_type in dbt_project.yml). The SQL below is the same for both.

with source as (
    select * from {{ ref('int_jobs_unioned') }}
    {% if is_incremental() %}
    -- >= e não >: reprocessar a mesma data precisa reler a partição inteira. Com >
    -- estrito, um segundo load no mesmo dia (extração parcial por rate limit, re-run
    -- manual) ficava invisível aqui. O merge por job_key torna o reprocesso seguro.
    where ingestion_date >= (select coalesce(max(last_seen), date '1900-01-01') from {{ this }})
    {% endif %}
),

ranked as (
    select
        *,
        row_number() over (partition by job_key order by ingestion_date desc) as rn,
        min(ingestion_date) over (partition by job_key) as first_seen_batch
    from source
),

latest_per_run as (
    select * from ranked where rn = 1
)

select
    l.job_key,
    l.source,
    l.external_id,
    l.title,
    l.company,
    l.location_raw,
    l.description,
    l.url,
    l.posted_at,
    l.salary_min,
    l.salary_max,
    l.salary_currency,
    l.remote_flag_raw,
    l.ingestion_date as last_seen,
    -- first_seen vem do min da janela, não da linha rn=1 (que é a mais recente).
    -- Usar l.ingestion_date aqui colapsava first_seen em last_seen a cada
    -- full-refresh e quebrava o grão de mart_tendencia_diaria.
    {% if is_incremental() %}
    coalesce(existing.first_seen, l.first_seen_batch) as first_seen
    {% else %}
    l.first_seen_batch as first_seen
    {% endif %}
from latest_per_run l
{% if is_incremental() %}
left join {{ this }} existing on existing.job_key = l.job_key
{% endif %}
