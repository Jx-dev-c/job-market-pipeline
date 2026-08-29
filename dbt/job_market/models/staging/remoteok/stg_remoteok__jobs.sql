with source as (
    select * from {{ source('raw_job_market', 'raw_remoteok_jobs') }}
)

select
    {{ dbt_utils.generate_surrogate_key(['source', 'external_id']) }} as job_key,
    source,
    external_id,
    title,
    company,
    location_raw,
    description,
    url,
    {{ parse_timestamp('posted_at') }} as posted_at,
    salary_min,
    salary_max,
    salary_currency,
    remote_flag_raw,
    cast(ingestion_date as date) as ingestion_date
from source
