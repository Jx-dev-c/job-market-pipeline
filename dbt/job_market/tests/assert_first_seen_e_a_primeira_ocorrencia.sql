-- first_seen has to match the first time the job_key showed up in the raw history.
-- Regression guard: int_jobs_deduped used to take ingestion_date from the rn=1 row (the
-- most recent one), so every full-refresh collapsed first_seen into last_seen.
-- Only fails when first_seen is greater than the real minimum. If an S3 lifecycle rule
-- ever expires a raw partition, the incremental keeps a first_seen older than anything
-- still visible, and that's fine.

with primeira_ocorrencia as (
    select
        job_key,
        min(ingestion_date) as min_ingestion_date
    from {{ ref('int_jobs_unioned') }}
    group by job_key
)

select
    d.job_key,
    d.first_seen,
    p.min_ingestion_date
from {{ ref('int_jobs_deduped') }} d
inner join primeira_ocorrencia p on p.job_key = d.job_key
where d.first_seen > p.min_ingestion_date
