{#
  Case-insensitive regex match, one implementation per adapter. Models call this
  instead of REGEXP_CONTAINS / regexp_like / ~* directly so the same model runs on
  dev (postgres), prod (athena) and prod_gcp (bigquery).
#}

{% macro regexp_like(column_expression, pattern) -%}
    {{ return(adapter.dispatch('regexp_like', 'job_market')(column_expression, pattern)) }}
{%- endmacro %}

{% macro default__regexp_like(column_expression, pattern) %}
    {{ column_expression }} ~* {{ pattern }}
{% endmacro %}

{% macro postgres__regexp_like(column_expression, pattern) %}
    {{ column_expression }} ~* {{ pattern }}
{% endmacro %}

{% macro bigquery__regexp_like(column_expression, pattern) %}
    REGEXP_CONTAINS({{ column_expression }}, {{ pattern }})
{% endmacro %}

{% macro athena__regexp_like(column_expression, pattern) %}
    regexp_like({{ column_expression }}, '(?i)' || {{ pattern }})
{% endmacro %}
