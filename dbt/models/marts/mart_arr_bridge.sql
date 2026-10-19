-- Grain: one row per month per segment (plus an 'All' row per month).
-- Opening ARR + new + reactivation + expansion - contraction - churn = closing ARR.

with movements as (
    select * from {{ ref('fct_mrr_monthly') }}
),

by_segment as (
    select
        month_start,
        segment,
        sum(previous_mrr_eur) * 12                                                        as opening_arr,
        sum(case when movement_type = 'new'          then mrr_change_eur else 0 end) * 12 as new_arr,
        sum(case when movement_type = 'reactivation' then mrr_change_eur else 0 end) * 12 as reactivation_arr,
        sum(case when movement_type = 'expansion'    then mrr_change_eur else 0 end) * 12 as expansion_arr,
        -sum(case when movement_type = 'contraction' then mrr_change_eur else 0 end) * 12 as contraction_arr,
        -sum(case when movement_type = 'churn'       then mrr_change_eur else 0 end) * 12 as churned_arr,
        sum(mrr_eur) * 12                                                                 as closing_arr,
        sum(case when previous_mrr_eur > 0 then 1 else 0 end)                             as opening_customers,
        sum(case when movement_type = 'new' then 1 else 0 end)                            as new_customers,
        sum(case when movement_type = 'churn' then 1 else 0 end)                          as churned_customers,
        sum(case when mrr_eur > 0 then 1 else 0 end)                                      as closing_customers
    from movements
    group by 1, 2
),

all_segments as (
    select
        month_start,
        'All' as segment,
        sum(opening_arr) as opening_arr, sum(new_arr) as new_arr, sum(reactivation_arr) as reactivation_arr,
        sum(expansion_arr) as expansion_arr, sum(contraction_arr) as contraction_arr,
        sum(churned_arr) as churned_arr, sum(closing_arr) as closing_arr,
        sum(opening_customers) as opening_customers, sum(new_customers) as new_customers,
        sum(churned_customers) as churned_customers, sum(closing_customers) as closing_customers
    from by_segment
    group by 1
)

select
    cast(month_start as {{ dbt.type_string() }}) || '_' || segment as bridge_id,
    *,
    closing_arr - opening_arr as net_new_arr
from (
    select * from by_segment
    union all
    select * from all_segments
) unioned
