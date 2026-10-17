-- One row per calendar month in the analysis window (vars in dbt_project.yml).
with spine as (
    {{ dbt_utils.date_spine(
        datepart="month",
        start_date="cast('" ~ var('start_month') ~ "' as date)",
        end_date="cast('" ~ var('end_month') ~ "' as date)"
    ) }}
)

select
    cast(date_month as date)                         as month_start,
    cast({{ dbt.last_day('date_month', 'month') }} as date) as month_end
from spine
