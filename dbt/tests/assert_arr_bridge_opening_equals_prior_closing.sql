-- Fails if any month's opening ARR differs from the previous month's closing ARR (same segment).
with ordered as (
    select
        segment,
        month_start,
        opening_arr,
        lag(closing_arr) over (partition by segment order by month_start) as prior_closing_arr
    from {{ ref('mart_arr_bridge') }}
)

select *
from ordered
where prior_closing_arr is not null
  and abs(opening_arr - prior_closing_arr) > 0.01
