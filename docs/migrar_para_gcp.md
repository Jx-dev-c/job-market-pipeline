# Trilha GCP (secundária)

Produção hoje roda na AWS (`docs/setup_aws.md`). A trilha GCP não foi descartada: o
adapter BigQuery segue instalado, virou o target `prod_gcp` (`dbt build --target prod_gcp`),
e o código GCP (`extract/load_to_gcs.py`, `extract/load_gcs_to_bigquery.py`, flags
`--upload-gcs --load-bq`) continua no repo. Este documento é o passo a passo pra reativar.

O plano original era GCP, mas o setup de billing travou por falta de limite de cartão.
O código que fala com GCP já está pronto, então reativar é configuração, não reescrita.

## Passo a passo

1. Resolver a conta de billing (cartão com limite, ou checar elegibilidade pro trial).
2. Provisionar os recursos seguindo `docs/setup_gcp.md` (projeto, billing, APIs,
   datasets, bucket, service account, key).
3. Preencher o `.env`:
   - `GCP_PROJECT_ID`
   - `GCS_RAW_BUCKET` (bucket do passo 5 do setup_gcp)
   - `GOOGLE_APPLICATION_CREDENTIALS` (default `/opt/airflow/keys/sa-key.json`, só
     garantir que o arquivo existe nesse path)
4. No `.env`, apontar o DAG pro GCP:
   `PIPELINE_EXTRACT_LOAD_FLAGS=--upload-gcs --load-bq` e `PIPELINE_DBT_TARGET=prod_gcp`.
5. `dbt build --target prod_gcp`. Os models não mudam, é pra isso que a regra de macros
   cross-database existe desde o começo.
6. Dashboard: reapontar o Metabase pro BigQuery, ou usar Looker Studio (tem link
   público compartilhável).

## O que não muda

`extract/load_to_gcs.py`, `extract/load_gcs_to_bigquery.py`, os extractors e o
`base.py` estão prontos desde a fase de extração, nada a alterar.

O Postgres local (`--target dev`) continua servindo pra iterar rápido sem custo, mesmo
com produção em outra nuvem.
