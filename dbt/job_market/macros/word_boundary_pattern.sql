{#
  Wraps a keyword in a word-boundary regex. Postgres uses \y; BigQuery and
  Athena (java regex) use \b. Checked on Postgres 16: \b matches nothing there.
  Kept in a macro so skills_keywords.csv stays a plain keyword list.
#}

{% macro word_boundary_pattern(keyword_expression) -%}
    {{ return(adapter.dispatch('word_boundary_pattern', 'job_market')(keyword_expression)) }}
{%- endmacro %}

{% macro default__word_boundary_pattern(keyword_expression) %}
    ('\y' || {{ keyword_expression }} || '\y')
{% endmacro %}

{% macro postgres__word_boundary_pattern(keyword_expression) %}
    ('\y' || {{ keyword_expression }} || '\y')
{% endmacro %}

{% macro bigquery__word_boundary_pattern(keyword_expression) %}
    (r'\b' || {{ keyword_expression }} || r'\b')
{% endmacro %}

{% macro athena__word_boundary_pattern(keyword_expression) %}
    ('\b' || {{ keyword_expression }} || '\b')
{% endmacro %}
