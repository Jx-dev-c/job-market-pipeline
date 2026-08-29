# Setup AWS (S3 + Athena + Glue)

Produção roda na AWS, dentro do free tier, região `us-east-2` (Ohio).
Warehouse é Athena, não Redshift: Athena não tem custo ocioso (paga por dado escaneado,
~$5/TB, e as runs escaneiam poucos MB). Redshift Serverless cobra capacidade-base por
hora mesmo parado.

## Componentes

| Papel | Serviço AWS | Como é criado |
|---|---|---|
| Raw/bronze (data lake) | **S3** | Bucket único; `extract/load_to_s3.py` sobe 1 arquivo JSONL por fonte/dia |
| Catálogo de metadados | **Glue Data Catalog** | `extract/load_s3_to_athena.py` cria o database + tabelas externas |
| Query engine / warehouse | **Athena** | Tabelas externas sobre o S3 + tabelas Iceberg escritas pelo dbt (`--target prod`) |
| Dashboard | **Metabase** (local, Docker) | Driver community de Athena em `metabase-plugins/` |
| Permissões | **IAM** | 1 usuário programático (`job-market-pipeline-ci`) com policy escopada |

## Layout no S3

```
s3://<bucket>/
  raw/<fonte>/ingestion_date=YYYY-MM-DD/<fonte>.jsonl   <- bronze, escrito pela extração
  athena-results/                                       <- output de query do Athena
  dbt/<schema>/<tabela>/                                <- tabelas materializadas pelo dbt
```

O caminho `ingestion_date=...` é Hive-style porque o Athena usa partition projection
nele. A partição do dia fica consultável assim que o arquivo cai no S3, sem
`MSCK REPAIR` nem `ALTER TABLE ADD PARTITION`.

## Passo a passo (console AWS)

Tudo na região **US East (Ohio) us-east-2**. Fixe a região no seletor do canto superior
direito antes de criar qualquer coisa.

### 1. Bucket S3

S3 → **Create bucket** → General purpose → nome global único (ex: `job-market-pipeline-jx-2026`)
→ Block all public access **marcado** → ACLs **disabled** → Create.

### 2. Policy IAM

IAM → Policies → Create policy → aba JSON → cola o conteúdo abaixo trocando `NOME_DO_BUCKET`
(2 ocorrências) → nome `job-market-pipeline-policy`.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "S3RawBucket",
      "Effect": "Allow",
      "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject","s3:ListBucket","s3:GetBucketLocation"],
      "Resource": ["arn:aws:s3:::NOME_DO_BUCKET","arn:aws:s3:::NOME_DO_BUCKET/*"]
    },
    {
      "Sid": "Athena",
      "Effect": "Allow",
      "Action": ["athena:StartQueryExecution","athena:GetQueryExecution","athena:GetQueryResults","athena:StopQueryExecution","athena:GetWorkGroup","athena:ListWorkGroups","athena:GetDataCatalog","athena:ListDataCatalogs","athena:GetDatabase","athena:GetTableMetadata","athena:ListDatabases","athena:ListTableMetadata"],
      "Resource": "*"
    },
    {
      "Sid": "GlueCatalog",
      "Effect": "Allow",
      "Action": ["glue:GetDatabase","glue:GetDatabases","glue:CreateDatabase","glue:GetTable","glue:GetTables","glue:CreateTable","glue:UpdateTable","glue:DeleteTable","glue:BatchDeleteTable","glue:GetTableVersion","glue:GetTableVersions","glue:DeleteTableVersion","glue:BatchDeleteTableVersion","glue:GetPartition","glue:GetPartitions","glue:BatchGetPartition","glue:CreatePartition","glue:BatchCreatePartition","glue:UpdatePartition","glue:DeletePartition","glue:BatchDeletePartition"],
      "Resource": "*"
    }
  ]
}
```

### 3. Usuário IAM + access key

IAM → Users → Create user → `job-market-pipeline-ci`, **sem** acesso ao console →
Attach policies directly → `job-market-pipeline-policy` → Create user.
Abre o usuário → Security credentials → Create access key → **Application running outside AWS**.

Copia o Access key ID e o Secret (**só aparece 1x**) para o `.env` local:

```
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=us-east-2
S3_RAW_BUCKET=<nome do bucket>
```

### 4. Trava de custo

Billing and Cost Management → Budgets → Create budget → template **Monthly cost budget**
= **$10**, alerta por e-mail. (Com créditos ativos o gasto real aparece coberto; o alerta
pega qualquer serviço caro ligado por engano.)

## Rodar o pipeline contra a AWS

```bash
docker compose build extract dbt airflow-webserver     # rebuild: pega boto3 + dbt-athena
docker compose up -d postgres                          # ainda necessário: metadata do Airflow

# extração + load manual de uma fonte:
docker compose run --rm extract --source adzuna --upload-s3 --load-athena

# dbt contra o Athena:
docker compose run --rm dbt build --target prod
```

Via Airflow: o DAG `job_market_daily` já usa `--upload-s3 --load-athena` e `--target prod`
por padrão (controlado por `PIPELINE_EXTRACT_LOAD_FLAGS` / `PIPELINE_DBT_TARGET` no `.env`).

## Dashboard: Metabase

`docker compose up -d metabase`, depois `http://localhost:3000`.

O Metabase aponta pro **Postgres local** (`job_market`, schema `job_market_marts`). Como
os models do dbt são idênticos nos targets `dev` e `prod`, os marts são os mesmos que
rodam no Athena. Rodar `dbt build --target dev` uma vez pra popular o Postgres.

Conectar o Metabase direto no Athena não é prático hoje: o único driver community
(`dacort/metabase-athena-driver`) parou em 2022 e não carrega em versões recentes do
Metabase. O diretório `metabase-plugins/` está montado no container caso apareça um
driver mantido, ou caso você fixe uma versão antiga do Metabase. A alternativa nativa
AWS seria o QuickSight (conecta no Athena sem driver), mas cobra por author depois do
trial.

## Custo esperado

- **S3**: 5 GB grátis/12 meses; depois ~$0.023/GB. Projeto = poucos MB.
- **Athena**: sem free tier, $5/TB escaneado. Runs diárias escaneiam MB → centavos/mês.
  Guarda-custo: no workgroup `primary` dá pra setar "per-query data usage limit" (ex: 1 GB).
- **Glue Data Catalog**: grátis até 1M objetos/requests. Não usar Glue Crawler nem
  Glue ETL job (esses custam $0.44/DPU-h). O catálogo é populado por DDL do
  `load_s3_to_athena.py` e pelo dbt.
- **Iceberg** (`int_jobs_deduped`): metadados no S3, sem custo além do storage.

## Dev local continua funcionando

`--target dev` (Postgres) continua funcionando pra iterar sem tocar na AWS:
`docker compose run --rm dbt build --target dev`. Ver `docs/desenvolvimento.md`.
