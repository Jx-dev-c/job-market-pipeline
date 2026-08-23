# Migrar para o GCP

O projeto roda local (Postgres + Metabase) porque o setup de billing do GCP travou por
falta de limite de cartão. O código que fala com GCP já está pronto, então migrar é
configuração, não reescrita.

## Passo a passo

1. Resolver a conta de billing (cartão com limite, ou checar elegibilidade pro trial).
2. Provisionar os recursos seguindo `docs/setup_gcp.md` (projeto, billing, APIs,
   datasets, bucket, service account, key).
3. Preencher o `.env`:
   - `GCP_PROJECT_ID`
   - `GCS_RAW_BUCKET` (bucket do passo 5 do setup_gcp)
   - `GOOGLE_APPLICATION_CREDENTIALS` (default `/opt/airflow/keys/sa-key.json`, só
     garantir que o arquivo existe nesse path)
4. Trocar o flag de load nas tasks do DAG: hoje chamam `--load-postgres`, trocar por
   `--upload-gcs --load-bq` (uma linha por task).
5. `dbt build --target prod`. Os models não mudam, é pra isso que a regra de macros
   cross-database existe desde o começo.
6. Dashboard: reapontar o Metabase pro BigQuery, ou usar Looker Studio (tem link
   público compartilhável).

## O que não muda

`extract/load_to_gcs.py`, `extract/load_gcs_to_bigquery.py`, os extractors e o
`base.py` já estão prontos, nada a alterar.

O Postgres local continua servindo pra iterar rápido sem custo antes de promover
pro `prod`.
