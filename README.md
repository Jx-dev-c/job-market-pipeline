# Job Market Data Pipeline

[![CI](https://github.com/Jx-dev-c/job-market-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/Jx-dev-c/job-market-pipeline/actions/workflows/ci.yml)

Pipeline de dados ponta a ponta sobre o mercado de vagas de tecnologia. Projeto de
portfólio pra Engenharia de Dados.

**~970 vagas por execução**, de 3 APIs públicas, ingeridas todo dia às 6h pelo Airflow,
transformadas em 15 modelos dbt com 57 testes de dados, e servidas num dashboard do
Metabase. As fontes são boards generalistas, então os marts recortam pras ~250 vagas que
casam com alguma skill de tecnologia; a base completa fica na camada intermediate. Roda
na AWS (S3 + Athena + Glue) dentro do free tier, em `us-east-2`, ou inteiro em Postgres
local (`--target dev`) sem custo nenhum.

Extração, carga, transformação, orquestração e dashboard já funcionam ponta a ponta.
Segue em evolução: o que ainda não está resolvido está em
[Limitações conhecidas](#limitações-conhecidas).

Setup da AWS: [`docs/setup_aws.md`](docs/setup_aws.md).
A versão GCP (BigQuery/GCS) ainda funciona como `--target prod_gcp`, ver
[`docs/migrar_para_gcp.md`](docs/migrar_para_gcp.md).

## Por que este projeto

Queria acompanhar tendências do mercado de vagas (skills mais pedidas, senioridade,
remoto vs presencial) enquanto procurava vaga, e ao mesmo tempo ter uma peça de
portfólio com o ciclo completo: ingestão, orquestração, transformação, modelagem e
visualização.

As fontes são só APIs públicas/oficiais (Adzuna, Arbeitnow, RemoteOK). Nada de scraping
ou login automatizado em LinkedIn/Glassdoor: isso viola os termos de uso dessas
plataformas.

## Arquitetura

```
APIs (Adzuna, Arbeitnow, RemoteOK)
  -> extract/ (Python, retry/backoff, validação com pydantic)
  -> S3 raw/bronze (particionado por ingestion_date)
  -> Glue Data Catalog (tabelas externas, partition projection)
  -> Airflow (orquestração diária)
  -> dbt (staging -> intermediate -> marts)
  -> Athena
  -> Metabase (lê os marts; local aponta pro Postgres, ver docs/setup_aws.md)
```

Detalhes e decisões em [`docs/architecture.md`](docs/architecture.md).

## Dashboard

![Dashboard no Metabase](docs/dashboard.png)

Skills mais pedidas, remoto vs presencial, senioridade e volume por fonte. Roda no
Metabase sobre os marts do dbt.

## O que os dados mostram

Numa execução de 970 vagas ingeridas (Adzuna 250, Arbeitnow 620, RemoteOK 100), das
quais 264 entram nos marts:

- **Excel aparece na frente de Python** (85 vagas contra 78). O motivo é o critério de
  escopo: `Excel` está no `skills_keywords.csv`, então vaga administrativa que pede Excel
  entra no recorte de "tecnologia". Restringindo às vagas senior/staff, a ordem se
  inverte e Python passa na frente (42 contra 34).
- Depois de Python e SQL (72), o pelotão seguinte mistura linguagem e infraestrutura em
  volume parecido: TypeScript (39), AWS (38), Kubernetes (36), JavaScript e Java (32
  cada).
- **45% das vagas são presenciais**, 43% remotas e 12% híbridas. Vale ler junto com o
  viés das fontes: a RemoteOK é 100% remota por construção, então o presencial estaria
  maior sem ela.
- 39% das vagas são senior e 20% junior, mas **28% seguem sem senioridade
  identificável** — o teto do que regex em título e descrição alcança.
- O aproveitamento por fonte segue desigual: 36% do que a Arbeitnow traz chega aos
  marts, contra 15% da RemoteOK e 9% da Adzuna. A RemoteOK devolve jardineiro,
  cozinheiro e registros de teste no meio das vagas de tech; a Adzuna entrega descrição
  truncada, então boa parte do sinal dela está só no título.

O primeiro item é o tipo de coisa que o dashboard sozinho não conta: o número mais
chamativo do gráfico é consequência de como "vaga de tecnologia" foi definido.

## Como rodar

Setup, variáveis de ambiente e comandos em [`docs/desenvolvimento.md`](docs/desenvolvimento.md).


