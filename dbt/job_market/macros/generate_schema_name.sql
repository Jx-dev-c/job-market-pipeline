{#
  When a model sets +schema, use that name as-is on every target instead of
  prefixing it with the target schema (dbt's default, which would give
  job_market_staging_staging). Keeps schema names identical across dev/prod.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
