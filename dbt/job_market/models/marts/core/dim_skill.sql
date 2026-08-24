{{ config(materialized='table') }}

select distinct
    {{ dbt_utils.generate_surrogate_key(['skill_name']) }} as skill_key,
    skill_name,
    category
from {{ ref('skills_keywords') }}
