# Desenvolvimento

Setup, variáveis de ambiente e comandos do dia a dia.

## Setup

1. `cp .env.example .env` e preenche as variáveis (tabela abaixo).
2. `docker compose build`
3. `docker compose up -d`
4. Airflow em `http://localhost:8080` (`admin` / `admin`).
5. Disparar o DAG: `docker compose exec airflow-scheduler airflow dags trigger job_market_daily`

## Variáveis de ambiente

| Variável | Descrição |
|---|---|
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | credenciais da API Adzuna |
| `JOOBLE_API_KEY` | API Jooble (opcional, ainda não usado) |
| `GCP_PROJECT_ID` / `GCP_LOCATION` | projeto GCP e região (`US`), pra quando migrar |
| `GOOGLE_APPLICATION_CREDENTIALS` | path da service account key dentro do container |
| `GCS_RAW_BUCKET` / `BQ_*_DATASET` | bucket e datasets do BigQuery |
| `AIRFLOW_UID` | UID local, pra permissão dos volumes no Linux/WSL |
| `POSTGRES_*` | Postgres local: metadata do Airflow + warehouse do `--target dev` |
| `POSTGRES_DSN` | DSN usado pelo loader Postgres e pelo dbt `dev` |

## Extração + carga

```bash
docker compose up -d postgres
docker compose build extract

# local
docker compose run --rm extract --source adzuna    --load-postgres
docker compose run --rm extract --source arbeitnow --load-postgres
docker compose run --rm extract --source remoteok  --load-postgres

# quando migrar pro GCP (docs/migrar_para_gcp.md): --upload-gcs --load-bq
```

Rodando `docker run`/`docker build` avulso no Windows/Git Bash, prefixar com
`MSYS_NO_PATHCONV=1`, senão o path do bind mount `-v` é convertido errado e os arquivos
somem quando o container morre. No `docker compose` não precisa.

## dbt

```bash
docker compose build dbt
docker compose run --rm dbt deps

docker compose run --rm dbt build            # target dev (Postgres)
docker compose run --rm dbt build --target prod   # BigQuery (quando migrar)

docker compose run --rm dbt source freshness
docker compose run --rm dbt docs generate
```

O profile é montado em `$HOME/.dbt`. O projeto `dbt/job_market` também é volume, então
`target/` e `dbt_packages/` persistem e editar os `.sql` reflete sem rebuild.

## Airflow

```bash
docker compose up -d
docker compose logs -f airflow-scheduler

docker compose exec airflow-scheduler airflow dags trigger job_market_daily
```

DAG `job_market_daily`: 3 extrações em paralelo, depois `dbt_seed` e `dbt_build`.
`extract/`, `dbt/job_market/` e `dbt/profiles/` são volumes nos containers do Airflow,
então editar o código reflete direto.

## Convenções

- Python com type hints, `ruff format` e `ruff check`.
- Cada fonte implementa `BaseExtractor` (`extract/base.py`). `extract/adzuna.py` serve
  de referência.
- dbt: um model por arquivo, sempre `ref()` / `source()`, prefixos `stg_` `int_` `fct_`
  `dim_` `mart_`, testes no `_schema.yml` ao lado do model.
- Dois targets no profile: `dev` (Postgres) e `prod` (BigQuery). Nunca usar SQL nativo
  de um adapter num model (`REGEXP_CONTAINS`, `~*`). Passar por uma macro
  `adapter.dispatch` (`regexp_like`, `word_boundary_pattern`). É isso que faz
  `--target prod` rodar sem editar model quando migrar.

## Adicionar uma nova fonte

1. `extract/<fonte>.py` implementando `BaseExtractor`.
2. `requests.Session` com retry/backoff e User-Agent próprio se a API exigir.
3. Adicionar a fonte às choices em `run_extraction.py`.
4. `stg_<fonte>__jobs.sql` em `dbt/job_market/models/staging/<fonte>/`.
5. Incluir a staging nova em `int_jobs_unioned`.
6. Adicionar a fonte a `SOURCES` no DAG.
7. Documentar o viés geográfico da fonte no README.

## Segurança

- Nunca commitar `.env` real nem `keys/*.json`.
- `pre-commit install` uma vez após clonar. O hook do `gitleaks` bloqueia segredo antes
  do commit.
