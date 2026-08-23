# Job Market Data Pipeline

Pipeline de dados ponta a ponta sobre o mercado de vagas de tecnologia. Projeto de
portfólio pra Engenharia de Dados.

**Status:** em construção. Roda local (Postgres + Airflow + dbt). Extração, carga,
transformação e orquestração diária já rodam ponta a ponta. O plano é BigQuery + GCS +
Looker Studio quando o billing da nuvem for resolvido, ver
[`docs/migrar_para_gcp.md`](docs/migrar_para_gcp.md). Falta o dashboard.

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
  -> raw/bronze (arquivo local, particionado por data)
  -> Postgres raw (particionado por ingestion_date)
  -> Airflow (orquestração diária)
  -> dbt (staging -> intermediate -> marts)
  -> Metabase
```

Detalhes e decisões em [`docs/architecture.md`](docs/architecture.md).

## Como rodar

Setup, variáveis de ambiente e comandos em [`docs/desenvolvimento.md`](docs/desenvolvimento.md).

## Limitações conhecidas

- As fontes têm viés geográfico (Arbeitnow puxa pra Europa, RemoteOK pra remoto
  EUA/Europa). A cobertura pro Brasil ainda precisa ser validada melhor.
- Skill e senioridade saem de regex + um CSV de keywords, não de NLP. Uns 68% das
  vagas ficam sem senioridade identificável no título.
