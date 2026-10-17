{{ config(materialized='table') }}

-- Grain: one row per customer per month-end, from the customer's signup month onward.
-- MRR = sum of subscriptions active on the last day of the month (0 after churn).

with months as (
    select * from {{ ref('int_month_spine') }}
),

customers as (
    select customer_id, signup_month from {{ ref('stg_customers') }}
),

subscriptions as (
    select subscription_id, customer_id, plan_id, mrr_eur, start_date, end_date
    from {{ ref('stg_subscriptions') }}
),

customer_months as (
    select
        c.customer_id,
        m.month_start,
        m.month_end
    from customers c
    inner join months m
        on m.month_start >= c.signup_month
),

monthly as (
    select
        cm.customer_id,
        cm.month_start,
        cm.month_end,
        coalesce(sum(s.mrr_eur), 0)     as mrr_eur,
        max(s.plan_id)                  as plan_id,
        count(s.subscription_id)        as active_subscriptions
    from customer_months cm
    left join subscriptions s
        on  s.customer_id = cm.customer_id
        and s.start_date <= cm.month_end
        and (s.end_date is null or s.end_date >= cm.month_end)
    group by 1, 2, 3
)

select
    customer_id || '_' || cast(month_start as {{ dbt.type_string() }}) as customer_month_id,
    *
from monthly
