# Arquitetura

Roda local: Postgres como warehouse, Airflow orquestrando, dbt transformando, Metabase
no dashboard. O plano é migrar pra GCP (BigQuery + GCS + Looker Studio) quando o billing
da nuvem for resolvido. A verificação de billing do GCP, mesmo pro trial, exige cartão
com limite, e isso travou. O passo a passo da migração está em `docs/migrar_para_gcp.md`,
e o código que fala com GCP (`load_to_gcs.py`, `load_gcs_to_bigquery.py`) já está pronto.

## Fluxo

```
APIs públicas (Adzuna, Arbeitnow, RemoteOK)
        |
        v
extract/  (Python: um módulo por fonte, BaseExtractor, retry/backoff, validação pydantic)
        |
        v
data/raw/<fonte>/dt=YYYY-MM-DD/<fonte>.jsonl      (bronze, arquivo local)
        |
        v
Postgres  schema raw_job_market, tabelas raw_<fonte>_jobs
        |
        v
dbt (staging -> intermediate -> marts)
        |
        v
Metabase

Airflow (LocalExecutor) orquestra: 3 extrações em paralelo -> dbt seed -> dbt build
```

## Camadas

- **Fontes**: Adzuna, Arbeitnow, RemoteOK. Só APIs públicas/oficiais.
- **Extração** (`extract/`): interface comum `BaseExtractor`, retry/backoff, validação
  do schema com pydantic no momento da extração, pra uma mudança de formato da API
  quebrar ali em vez de sujar o raw.
- **Raw/bronze**: `data/raw/.../<fonte>.jsonl`. Nome sem timestamp, então re-rodar o
  mesmo dia sobrescreve.
- **Warehouse local** (Postgres): schema `raw_job_market`, tabelas `raw_<fonte>_jobs`.
  Carga via `load_to_postgres.py`, DELETE + INSERT por partição numa transação.
- **Transformação** (dbt, target `dev`=postgres): staging, intermediate, marts
  (`core` e `analytics`). Os models não usam SQL nativo de um adapter, sempre uma macro
  cross-database, pra não travar a migração pro BigQuery depois.
- **Orquestração** (Airflow, Docker, LocalExecutor): DAG diário `job_market_daily`.
- **Dashboard**: Metabase (Docker local).

## Decisões

**Postgres local e não DuckDB.** O Airflow já precisa de um Postgres de metadata, então
reaproveitar é mais simples que trazer um paradigma novo. `dbt-postgres` é adapter
oficial.

**Arquivo local como bronze, não MinIO.** `load_to_gcs.py` já fala a API do GCS. Um
MinIO seria código descartável só pra simular S3.

**LocalExecutor e não Celery.** Volume pequeno (3 fontes, 1x/dia) não justifica
Celery/Redis.

**Modelos incrementais desde o começo.** Full-refresh diário cresce o custo/tempo de
processamento indefinidamente conforme o histórico acumula. Menos crítico no Postgres,
mas mantém a convenção pro BigQuery.

**Regex + CSV pra skills, não NLP.** Suficiente pro MVP e portável entre Postgres e
BigQuery sem duplicar SQL.
