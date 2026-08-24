{{ config(materialized='view') }}

{{ dbt_utils.union_relations(
    relations=[
        ref('stg_adzuna__jobs'),
        ref('stg_arbeitnow__jobs'),
        ref('stg_remoteok__jobs'),
    ]
) }}
