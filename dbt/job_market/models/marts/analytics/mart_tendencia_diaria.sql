{{ config(materialized='table') }}

-- Novas vagas por dia. Grão = first_seen (primeira vez que a vaga apareceu), não posted_at.
-- "Vagas ativas por dia" seria outra métrica, baseada em last_seen.

select
    first_seen as observed_date,
    source,
    count(*) as new_job_postings_count
from {{ ref('fct_job_postings') }}
group by first_seen, source
order by first_seen
