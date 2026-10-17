-- Fails (returns rows) if, for any month, the sum of customer-level MRR movements
-- does not equal the month-over-month change in total MRR.

with movements as (
    select month_start, sum(mrr_change_eur) as net_movement
    from {{ ref('int_mrr_movements') }}
    group by 1
),

totals as (
    select month_start, sum(mrr_eur) as total_mrr
    from {{ ref('int_customer_mrr_monthly') }}
    group by 1
),

compared as (
    select
        t.month_start,
        t.total_mrr - coalesce(lag(t.total_mrr) over (order by t.month_start), 0) as actual_change,
        coalesce(m.net_movement, 0) as net_movement
    from totals t
    left join movements m on m.month_start = t.month_start
)

select *
from compared
where abs(actual_change - net_movement) > 0.01
