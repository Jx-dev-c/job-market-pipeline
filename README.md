# Job Market Data Pipeline

[![CI](https://github.com/Jx-dev-c/job-market-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/Jx-dev-c/job-market-pipeline/actions/workflows/ci.yml)

Pipeline de dados ponta a ponta sobre o mercado de vagas de tecnologia. Projeto de
portfólio pra Engenharia de Dados.

**~970 vagas por execução**, de 3 APIs públicas, ingeridas todo dia às 6h pelo Airflow,
transformadas em 15 modelos dbt com 57 testes de dados, e servidas num dashboard do
Metabase. Roda na AWS (S3 + Athena + Glue) dentro do free tier, em `us-east-2`, ou
inteiro em Postgres local (`--target dev`) sem custo nenhum.

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

Numa execução de 969 vagas (Adzuna 249, Arbeitnow 620, RemoteOK 100):

- **Excel aparece na frente de Python** (85 vagas contra 73). Isso diz menos sobre o
  mercado de tecnologia e mais sobre o viés da base: as fontes são boards generalistas e
  só 25% das vagas casam com alguma skill de tech. Restringindo às vagas de senioridade
  senior/staff, a ordem se inverte e Python passa Excel (41 contra 34).
- Depois de Python e SQL (52), o bloco mais pedido é de infraestrutura: AWS (37),
  Kubernetes (35) e Docker (29) aparecem à frente de linguagens como Java (24).
- **54% das vagas são presenciais**, 36% remotas e 10% híbridas. Vale ler junto com o
  viés das fontes: a RemoteOK é 100% remota por construção, então o presencial estaria
  ainda maior sem ela.

O primeiro item é o motivo de existir a seção abaixo: o número mais chamativo do
dashboard é, na verdade, um artefato da amostra.

## Como rodar

Setup, variáveis de ambiente e comandos em [`docs/desenvolvimento.md`](docs/desenvolvimento.md).

## Limitações conhecidas

- As fontes têm viés geográfico (Arbeitnow puxa pra Europa, RemoteOK pra remoto
  EUA/Europa). A cobertura pro Brasil ainda precisa ser validada melhor.
- A maior parte do que entra não é vaga de tecnologia. Numa amostra de 969 vagas, só
  246 (25%) casaram com alguma skill do `skills_keywords.csv`; o resto é açougueiro,
  atendente de farmácia, auxiliar de produção. As fontes são boards generalistas e os
  marts ainda não filtram por escopo, então os gráficos misturam os dois mundos. Próximo
  passo é filtrar os marts pelas vagas que casam com o `skills_keywords.csv`, mantendo a
  base completa na camada intermediate.
- Skill e senioridade saem de regex + um CSV de keywords, não de NLP. Na mesma amostra,
  metade das vagas fica sem senioridade identificável, ou 27% se olhar só as de
  tecnologia. A senioridade tenta o título primeiro e cai pra descrição quando o título
  não resolve; a descrição acerta 87% das vezes em que dispara, então `seniority_source`
  marca de onde veio o rótulo, pra quem quiser filtrar só o sinal de título.
