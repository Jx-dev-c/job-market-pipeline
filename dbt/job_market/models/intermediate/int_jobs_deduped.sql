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
    where ingestion_date > (select coalesce(max(last_seen), date '1900-01-01') from {{ this }})
    {% endif %}
),

ranked as (
    select
        *,
        row_number() over (partition by job_key order by ingestion_date desc) as rn
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
    {% if is_incremental() %}
    coalesce(existing.first_seen, l.ingestion_date) as first_seen
    {% else %}
    l.ingestion_date as first_seen
    {% endif %}
from latest_per_run l
{% if is_incremental() %}
left join {{ this }} existing on existing.job_key = l.job_key
{% endif %}
