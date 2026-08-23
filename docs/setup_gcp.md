# Setup do GCP (trilha legada)

> Produção do pipeline hoje roda na AWS (`docs/setup_aws.md`). Este guia é a trilha GCP,
> mantida funcional como `--target prod_gcp`. Ver `docs/migrar_para_gcp.md` para quando
> e como reativar.

Estes passos são feitos uma vez, pelo Console Web do GCP (`console.cloud.google.com`).
Não precisa instalar `gcloud`; o pipeline usa os clients Python
(`google-cloud-bigquery`, `google-cloud-storage`).

## 1. Criar o projeto

- Console, criar novo projeto (ex. `job-market-pipeline`).
- Anotar o **Project ID** gerado (é único globalmente e diferente do nome digitado, ex.
  `job-market-pipeline-471023`).

## 2. Billing e controle de custo

- Ativar faturamento no projeto (obrigatório mesmo dentro do free tier).
- Criar um alerta de orçamento em Billing > Budgets & alerts (ex. $5). Esse alerta é só
  notificação por e-mail, não bloqueia gasto. O controle de custo de verdade vem de:
  - manter os recursos em **US multi-region** (fora disso já sai do free tier do
    BigQuery/GCS);
  - `maximum_bytes_billed` no profile do dbt, que trava cada query;
  - usar modelos incrementais em vez de full-refresh.

## 3. Ativar APIs

- BigQuery API (normalmente já ativa).
- Cloud Storage API.

## 4. Criar datasets no BigQuery

Todos em região `US` (multi-region). Outra região sai do free tier.

- `raw_job_market`
- `job_market_staging`, `job_market_intermediate`, `job_market_marts` (podem ser criados
  agora ou deixados pro dbt criar no primeiro run).

## 5. Criar bucket GCS

- Nome único globalmente (ex. `job-market-pipeline-raw-<project-id>`).
- Região: US multi-region.
- Lifecycle rule: expirar objetos depois de ~30 dias. O dado bruto também está no
  BigQuery, então isso só limita a janela de reprocessamento do raw.

## 6. Criar Service Account

`IAM & Admin > Service Accounts > Create Service Account`. Nome: `job-pipeline-sa`.

Papéis, com o menor escopo possível:
- `BigQuery Data Editor`, concedido **por dataset** (entrar em cada dataset do passo 4 >
  Permissions > Add Principal > e-mail da service account).
- `BigQuery Job User`, que só existe a nível de projeto, concedido no IAM do projeto.
- `Storage Object Admin`, concedido **no bucket** do passo 5, não no projeto.
- Nunca `Owner` ou `Editor` de projeto.

## 7. Gerar a chave da Service Account

- Service Account > Keys > Add Key > JSON.
- Baixar uma vez e salvar em `keys/sa-key.json` (a pasta está no `.gitignore`).

## 8. Configurar o profile do dbt

Com a key salva, o target `prod_gcp` em `dbt/profiles/profiles.yml` já aponta pra
`/opt/airflow/keys/sa-key.json`. Só preencher `project` com o Project ID.
`profiles.yml.example` tem os campos como referência.

## Se uma chave vazar

Revogar/rotacionar imediatamente no GCP (Service Account > Keys > deletar a chave
vazada > gerar outra). Remover do último commit não basta, o histórico do git continua
expondo a chave antiga até ela ser revogada na origem.
