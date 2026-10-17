-- Grain: one row per customer per month where the customer had MRR this month or last month.
-- Classifies each month-over-month MRR change. Sum of mrr_change_eur per month
-- must equal the change in total MRR (tests/assert_mrr_movements_reconcile.sql).

with monthly as (
    select * from {{ ref('int_customer_mrr_monthly') }}
),

lagged as (
    select
        *,
        coalesce(lag(mrr_eur) over (partition by customer_id order by month_start), 0)
            as previous_mrr_eur,
        max(case when mrr_eur > 0 then 1 else 0 end) over (
            partition by customer_id order by month_start
            rows between unbounded preceding and 1 preceding
        ) as had_mrr_before
    from monthly
)

select
    customer_month_id,
    customer_id,
    month_start,
    month_end,
    plan_id,
    previous_mrr_eur,
    mrr_eur,
    mrr_eur - previous_mrr_eur as mrr_change_eur,
    case
        when previous_mrr_eur = 0 and mrr_eur > 0 and coalesce(had_mrr_before, 0) = 0 then 'new'
        when previous_mrr_eur = 0 and mrr_eur > 0                                    then 'reactivation'
        when previous_mrr_eur > 0 and mrr_eur = 0                                    then 'churn'
        when mrr_eur > previous_mrr_eur                                              then 'expansion'
        when mrr_eur < previous_mrr_eur                                              then 'contraction'
        else 'flat'
    end as movement_type
from lagged
where mrr_eur > 0 or previous_mrr_eur > 0
