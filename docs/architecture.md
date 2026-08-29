# Arquitetura

Produção roda na AWS (S3 + Athena + Glue), dentro do free tier, em `us-east-2`. Dá pra
rodar tudo local em Postgres + Metabase também (`--target dev`), o que é útil pra iterar
rápido sem custo.

Antes da AWS o plano era GCP (BigQuery + GCS + Looker Studio). Isso travou porque a
verificação de billing do GCP, mesmo pro trial, exige cartão com limite. O código GCP
continua no repo e funciona como `--target prod_gcp` (ver `docs/migrar_para_gcp.md`).

## Fluxo

```
APIs públicas (Adzuna, Arbeitnow, RemoteOK)
        |
        v
extract/  (Python: um módulo por fonte, BaseExtractor, retry/backoff, validação pydantic)
        |
        +--> data/raw/<fonte>/dt=YYYY-MM-DD/<fonte>.jsonl        (bronze local)
        |
        v
S3  s3://<bucket>/raw/<fonte>/ingestion_date=YYYY-MM-DD/<fonte>.jsonl   (bronze na nuvem)
        |
        v
Glue Data Catalog   tabelas externas raw_<fonte>_jobs (partition projection em ingestion_date)
        |
        v
Athena  <-- dbt (staging -> intermediate -> marts)
        |       staging/int: views + 1 tabela Iceberg incremental (int_jobs_deduped)
        |       marts: tabelas Iceberg
        v
Metabase (local; lê os marts do Postgres, mesmos models via --target dev)

Airflow (local, LocalExecutor) orquestra: 3 extrações em paralelo -> dbt seed -> dbt build
```

## Camadas

- **Fontes**: Adzuna, Arbeitnow, RemoteOK. Só APIs públicas/oficiais.
- **Extração** (`extract/`): interface comum `BaseExtractor`, retry/backoff, validação
  do schema com pydantic no momento da extração, pra uma mudança de formato da API
  quebrar ali em vez de sujar o raw.
- **Raw/bronze**: `data/raw/.../<fonte>.jsonl` local e `s3://<bucket>/raw/...`. Nome sem
  timestamp, então re-rodar o mesmo dia sobrescreve.
- **Catálogo** (Glue): `raw_job_market.raw_<fonte>_jobs`, tabelas externas JSON com
  partition projection.
- **Warehouse / transformação** (Athena + dbt, target `prod`): staging, intermediate,
  marts (`core` e `analytics`). Os models não usam SQL nativo de um adapter, sempre uma
  macro cross-database (`regexp_like`, `word_boundary_pattern`, `parse_timestamp`), o
  que faz `--target dev` e `--target prod_gcp` rodarem sem editar model.
- **Orquestração** (Airflow, Docker, LocalExecutor): DAG diário `job_market_daily`.
- **Dashboard**: Metabase (Docker local) sobre o Postgres. Não existe driver de Athena
  mantido pro Metabase atual; como os marts são idênticos nos targets, o Postgres serve
  de fonte pro dashboard sem perder nada. Detalhe em `docs/setup_aws.md`.

## Decisões

**Athena e não Redshift.** Athena não tem custo ocioso: paga por dado escaneado (~$5/TB),
e as runs escaneiam poucos MB. Redshift Serverless cobra capacidade-base por hora mesmo
parado, o que consumiria o crédito à toa. `dbt-athena` é adapter mantido.

**Partition projection e não Glue Crawler.** Crawler custa por DPU-hora e roda em
schedule. Projection é config na tabela, custo zero, e a partição nova fica visível na
hora que o arquivo chega no S3.

**Iceberg em `int_jobs_deduped`, Hive não seria suficiente.** É o único model incremental
de verdade e precisa de `merge`, que o Athena não faz em tabela Hive. Os outros models
são view ou full-refresh, então acabaram todos em Iceberg por consistência (e porque o
Athena Hive não aceita `timestamp` com microssegundos, que é o que o Iceberg produz).

**Postgres local e não DuckDB.** O Airflow já precisa de um Postgres de metadata, então
reaproveitar é mais simples que trazer um paradigma novo. `dbt-postgres` é adapter
oficial.

**LocalExecutor e não Celery.** Volume pequeno (3 fontes, 1x/dia) não justifica
Celery/Redis.

**Modelos incrementais desde o começo.** Full-refresh diário cresce o custo/tempo de
processamento indefinidamente conforme o histórico acumula.

**Metabase e não QuickSight.** QuickSight cobra por author depois do trial. Metabase roda
local e de graça. Ele lê do Postgres em vez do Athena porque o driver community de Athena
não acompanha as versões novas do Metabase, mas os marts são os mesmos.

**Regex + CSV pra skills, não NLP.** Suficiente pro MVP e portável entre Postgres, Athena
e BigQuery sem duplicar SQL. Um caminho pra algo mais esperto fica em aberto se a
precisão cair.
