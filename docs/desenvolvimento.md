# Desenvolvimento

Setup, variáveis de ambiente e comandos do dia a dia.

## Setup

1. `cp .env.example .env` e preenche as variáveis (tabela abaixo). Pra AWS, seguir
   `docs/setup_aws.md`.
2. `docker compose build extract dbt airflow-init airflow-webserver airflow-scheduler`
3. `docker compose up -d`
4. Airflow em `http://localhost:8080` (`admin` / `admin`).
5. Disparar o DAG: `docker compose exec airflow-scheduler airflow dags trigger job_market_daily`

## Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | credenciais da API Adzuna |
| `JOOBLE_API_KEY` | API Jooble (opcional, ainda não usado) |
| `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` | usuário IAM `job-market-pipeline-ci` |
| `AWS_DEFAULT_REGION` | `us-east-2` |
| `S3_RAW_BUCKET` | bucket da camada raw |
| `GLUE_RAW_DATABASE` | database Glue das tabelas externas raw (default `raw_job_market`) |
| `ATHENA_WORKGROUP` | workgroup do Athena (default `primary`) |
| `ATHENA_S3_STAGING_DIR` / `ATHENA_S3_DATA_DIR` | output de query / dados do dbt (default derivado do bucket) |
| `PIPELINE_EXTRACT_LOAD_FLAGS` / `PIPELINE_DBT_TARGET` | alvo do DAG. Default AWS; pra local: `--load-postgres` e `dev` |
| `GCP_*` / `GCS_RAW_BUCKET` / `BQ_*_DATASET` | trilha GCP legada (`--target prod_gcp`) |
| `AIRFLOW_UID` | UID local, pra permissão dos volumes no Linux/WSL |
| `POSTGRES_*` | Postgres local: metadata do Airflow + warehouse do `--target dev` |
| `POSTGRES_DSN` | DSN usado pelo loader Postgres e pelo dbt `dev` |

## Extração + carga

```bash
docker compose up -d postgres
docker compose build extract

# produção (AWS)
docker compose run --rm extract --source adzuna    --upload-s3 --load-athena
docker compose run --rm extract --source arbeitnow --upload-s3 --load-athena
docker compose run --rm extract --source remoteok  --upload-s3 --load-athena

# local
docker compose run --rm extract --source adzuna --load-postgres

# GCP legado
docker compose run --rm extract --source adzuna --upload-gcs --load-bq
```

`--load-athena` só cria (idempotente) o database Glue e a tabela externa. A tabela usa
partition projection em `ingestion_date`, então a partição do dia aparece assim que o
arquivo chega no S3, sem `MSCK REPAIR`.

Rodando `docker run`/`docker build` avulso no Windows/Git Bash, prefixar com
`MSYS_NO_PATHCONV=1`, senão o path do bind mount `-v` é convertido errado e os arquivos
somem quando o container morre. No `docker compose` não precisa (os volumes vêm do YAML).

## dbt

```bash
docker compose build dbt
docker compose run --rm dbt deps

docker compose run --rm dbt build --target prod      # Athena
docker compose run --rm dbt build --target dev       # Postgres local
docker compose run --rm dbt build --target prod_gcp  # BigQuery

docker compose run --rm dbt source freshness --target prod
docker compose run --rm dbt docs generate
```

O profile é montado em `$HOME/.dbt` (o serviço roda como UID 50000, então `HOME` está
setado no compose). O projeto `dbt/job_market` também é volume, então `target/` e
`dbt_packages/` persistem e editar os `.sql` reflete sem rebuild. As credenciais AWS do
target `prod` vêm do `.env` via boto3, não do profile.

## Airflow

```bash
docker compose up -d
docker compose logs -f airflow-scheduler

docker compose exec airflow-scheduler airflow dags trigger job_market_daily
docker compose exec airflow-scheduler airflow dags list-runs -d job_market_daily
```

DAG `job_market_daily`: 3 extrações em paralelo, depois `dbt_seed` e `dbt_build`. Roda
em ~3 min. `extract/`, `dbt/job_market/` e `dbt/profiles/` são volumes nos containers
do Airflow, então editar o código reflete direto.

## Convenções

- Python com type hints, `ruff format` e `ruff check`.
- Cada fonte implementa `BaseExtractor` (`extract/base.py`). `extract/adzuna.py` serve
  de referência.
- dbt: um model por arquivo, sempre `ref()` / `source()`, prefixos `stg_` `int_` `fct_`
  `dim_` `mart_`, testes no `_schema.yml` ao lado do model.
- Três targets no profile `job_market`: `dev` (Postgres), `prod` (Athena), `prod_gcp`
  (BigQuery). Nunca usar SQL nativo de um adapter num model (`REGEXP_CONTAINS`, `~*`,
  `from_iso8601_timestamp`). Passar por uma macro `adapter.dispatch`. As que existem:
  `regexp_like`, `word_boundary_pattern`, `parse_timestamp`. Precisou de SQL específico
  de dialeto, estende a macro.
- Config incremental pode variar por target (ex. `int_jobs_deduped`), mas só no bloco
  `config()`, nunca no corpo do model.
- Raw no Athena é tabela externa JSON com partition projection
  (`extract/load_s3_to_athena.py`). Sem Glue Crawler (custo) e sem `MSCK REPAIR`.

## Adicionar uma nova fonte

1. `extract/<fonte>.py` implementando `BaseExtractor`.
2. `requests.Session` com retry/backoff e User-Agent próprio se a API exigir.
3. Adicionar a fonte às choices em `run_extraction.py`. A tabela `raw_<fonte>_jobs` sai
   automática do `RAW_JOB_SCHEMA_FIELDS`.
4. `stg_<fonte>__jobs.sql` em `dbt/job_market/models/staging/<fonte>/` (usar
   `parse_timestamp` no `posted_at`).
5. Incluir a staging nova em `int_jobs_unioned`.
6. Adicionar a fonte a `SOURCES` no DAG.
7. Documentar o viés geográfico da fonte no README.

## Segurança

- Nunca commitar `.env` real nem `keys/*.json`.
- IAM `job-market-pipeline-ci` com policy escopada (bucket do projeto + Athena + Glue),
  nunca `AdministratorAccess`.
- `pre-commit install` uma vez após clonar. O hook do `gitleaks` bloqueia segredo antes
  do commit.

## Notas de custo (AWS)

- O AWS Budget é só alerta por e-mail, não trava gasto. O controle de verdade vem do
  Athena escanear pouco dado (partição por `ingestion_date`) e de não usar Glue
  Crawler / ETL jobs.
- `int_jobs_deduped` é Iceberg. Os outros models são view ou tabela full-refresh, que
  são baratos porque leem do `int_jobs_deduped`, que já é pequeno.
