-- first_seen tem que bater com a primeira vez que o job_key apareceu no histórico
-- bruto. Regressão: int_jobs_deduped pegava ingestion_date da linha rn=1 (a mais
-- recente), então todo full-refresh colapsava first_seen em last_seen e o grão de
-- mart_tendencia_diaria virava "última vez vista" em vez de "vaga nova".
--
-- Só falha quando first_seen é MAIOR que o mínimo real: se a partição raw for
-- expirada por lifecycle no S3, first_seen preservado pelo incremental fica menor
-- que o mínimo ainda visível, e isso não é erro.

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
