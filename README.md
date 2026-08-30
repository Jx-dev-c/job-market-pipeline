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

Numa execução de 969 vagas ingeridas (Adzuna 249, Arbeitnow 620, RemoteOK 100), das
quais 246 entram nos marts:

- **Excel aparece na frente de Python** (85 vagas contra 73). O motivo é o critério de
  escopo: `Excel` está no `skills_keywords.csv`, então vaga administrativa que pede Excel
  entra no recorte de "tecnologia". Restringindo às vagas senior/staff, a ordem se
  inverte e Python passa Excel (41 contra 34).
- Depois de Python e SQL (52), o bloco mais pedido é de infraestrutura: AWS (37),
  Kubernetes (35) e Docker (29) aparecem à frente de linguagens como Java (24).
- **Presencial e remoto empatam em 44%** (109 cada), com 11% híbrido. Vale ler junto com
  o viés das fontes: a RemoteOK é 100% remota por construção, então o presencial estaria
  maior sem ela.
- 40% das vagas são senior e 22% junior, mas **27% seguem sem senioridade
  identificável** — o teto do que regex em título e descrição alcança.
- O aproveitamento por fonte é muito desigual: 36% do que a Arbeitnow traz chega aos
  marts, contra 15% da RemoteOK e **2,4% da Adzuna**. A Adzuna é buscada sem termo de
  busca, então puxa todas as vagas do Brasil e não só as de tecnologia; a RemoteOK
  devolve jardineiro, cozinheiro e registros de teste no meio das vagas de tech.

O primeiro item é o tipo de coisa que o dashboard sozinho não conta: o número mais
chamativo do gráfico é consequência de como "vaga de tecnologia" foi definido.

## Como rodar

Setup, variáveis de ambiente e comandos em [`docs/desenvolvimento.md`](docs/desenvolvimento.md).

## Limitações conhecidas

- As fontes têm viés geográfico (Arbeitnow puxa pra Europa, RemoteOK pra remoto
  EUA/Europa). A cobertura pro Brasil ainda precisa ser validada melhor.
- O recorte de "vaga de tecnologia" é frágil: é casar com qualquer keyword do
  `skills_keywords.csv`, que hoje tem 29 termos e trata apelido de forma inconsistente:
  `postgres(ql)?` e `node\.js` cobrem as variantes, mas `JS`, `K8s` e `TS` não casam com
  JavaScript, Kubernetes e TypeScript. Como `Excel` está na lista, vaga administrativa
  entra. Dos 969
  ingeridos, 246 passam; o resto (açougueiro, atendente de farmácia) fica só na camada
  intermediate. Um critério melhor exigiria classificar a vaga, não só procurar keyword.
- A ingestão não filtra por tecnologia na origem, ela traz tudo e o recorte acontece
  depois, no mart. A Adzuna aceita termo de busca (`what=`) e hoje não usa, o que
  explica os 2,4% de aproveitamento dela. Filtrar na origem economizaria storage e scan
  do Athena, além de melhorar a representatividade.
- Skill e senioridade saem de regex + um CSV de keywords, não de NLP. 27% das vagas nos
  marts ficam sem senioridade identificável. A senioridade tenta o título primeiro e cai
  pra descrição quando o título não resolve; a descrição acerta 87% das vezes em que
  dispara, então `seniority_source` marca de onde veio o rótulo, pra quem quiser filtrar
  só o sinal de título.
