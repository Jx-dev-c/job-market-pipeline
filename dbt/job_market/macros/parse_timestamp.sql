{#
  Parse the raw posted_at (ISO-8601 string) into a timestamp.
  Postgres reads it straight from a timestamptz column. Athena reads it from a
  JSON string and needs from_iso8601_timestamp(); the timestamp(3) cast keeps it
  at millisecond precision, which is what the Hive/CTAS path downstream accepts.
#}

{% macro parse_timestamp(column_expression) -%}
    {{ return(adapter.dispatch('parse_timestamp', 'job_market')(column_expression)) }}
{%- endmacro %}

{% macro default__parse_timestamp(column_expression) %}
    cast({{ column_expression }} as timestamp)
{% endmacro %}

{% macro postgres__parse_timestamp(column_expression) %}
    {{ column_expression }}::timestamptz
{% endmacro %}

{% macro athena__parse_timestamp(column_expression) %}
    cast(from_iso8601_timestamp({{ column_expression }}) as timestamp(3))
{% endmacro %}
