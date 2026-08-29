from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.utils.task_group import TaskGroup
from airflow.utils.trigger_rule import TriggerRule

SOURCES = ["adzuna", "arbeitnow", "remoteok"]

DBT_PROJECT_DIR = "/opt/airflow/dbt/job_market"
DBT_BIN = "/opt/dbt-venv/bin/dbt"
EXTRACT_PYTHON = "/opt/extract-venv/bin/python"

# Produção roda na AWS (S3 + Athena). Para rodar o pipeline contra o Postgres local
# em vez da nuvem, sobrescreva no .env:
#   PIPELINE_EXTRACT_LOAD_FLAGS=--load-postgres
#   PIPELINE_DBT_TARGET=dev
EXTRACT_LOAD_FLAGS = os.environ.get("PIPELINE_EXTRACT_LOAD_FLAGS", "--upload-s3 --load-athena")
DBT_TARGET = os.environ.get("PIPELINE_DBT_TARGET", "prod")

default_args = {
    "owner": "job-market-pipeline",
    "retries": 2,
    "retry_delay": timedelta(minutes=5),
    # Dimensionado para as tasks de extração. As tasks de dbt sobrescrevem: o build
    # cresce com o histórico e 10 min viraria um teto arbitrário conforme os dados
    # acumulam.
    "execution_timeout": timedelta(minutes=10),
}

with DAG(
    dag_id="job_market_daily",
    description="Extrai vagas (Adzuna/Arbeitnow/RemoteOK), carrega no S3+Athena e roda o dbt build",
    default_args=default_args,
    schedule="0 6 * * *",
    start_date=datetime(2026, 8, 23),
    catchup=False,
    max_active_runs=1,
    tags=["job-market-pipeline"],
) as dag:
    extract_groups = []
    for source in SOURCES:
        with TaskGroup(group_id=source) as tg:
            # {{ ds }} é a data lógica, não wall-clock. Re-rodar a mesma data sempre
            # cai na mesma partição, então backfill continua idempotente.
            BashOperator(
                task_id=f"extract_and_load_{source}",
                bash_command=(
                    f"{EXTRACT_PYTHON} -m extract.run_extraction "
                    f"--source {source} --date {{{{ ds }}}} {EXTRACT_LOAD_FLAGS}"
                ),
                # BashOperator roda num dir temporário por default; sem cwd o pacote
                # `extract` não é importável.
                cwd="/opt/airflow",
            )
        extract_groups.append(tg)

    # Monitor, não portão: as sources têm warn_after/error_after em _sources.yml, mas
    # nada invocava `dbt source freshness`, então a config nunca era exercida. Roda em
    # paralelo ao build de propósito — uma fonte parada precisa acender a run em
    # vermelho, não impedir os marts de atualizarem com o que chegou.
    dbt_source_freshness = BashOperator(
        task_id="dbt_source_freshness",
        bash_command=f"{DBT_BIN} source freshness --project-dir {DBT_PROJECT_DIR} --target {DBT_TARGET}",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
        execution_timeout=timedelta(minutes=15),
        retries=0,
    )

    # As três fontes são independentes: se a RemoteOK morrer depois das retries, ainda
    # vale transformar o que Adzuna e Arbeitnow entregaram. Com all_success (default) um
    # único extract falho segurava o dbt e o dashboard não atualizava o dia inteiro.
    dbt_seed = BashOperator(
        task_id="dbt_seed",
        bash_command=f"{DBT_BIN} seed --project-dir {DBT_PROJECT_DIR} --target {DBT_TARGET}",
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
        execution_timeout=timedelta(minutes=15),
    )

    dbt_build = BashOperator(
        task_id="dbt_build",
        bash_command=f"{DBT_BIN} build --project-dir {DBT_PROJECT_DIR} --target {DBT_TARGET}",
        execution_timeout=timedelta(minutes=60),
    )

    extract_groups >> dbt_source_freshness
    extract_groups >> dbt_seed >> dbt_build
