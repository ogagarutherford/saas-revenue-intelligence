-- Grain: one row per customer per month where the customer had MRR this month or last.
-- The core analytical fact: every ARR, retention and cohort metric reconciles to this table.
select
    m.customer_month_id,
    m.customer_id,
    m.month_start,
    m.month_end,
    m.plan_id,
    c.segment,
    c.acquisition_channel,
    c.signup_month,
    m.previous_mrr_eur,
    m.mrr_eur,
    m.mrr_change_eur,
    m.movement_type
from {{ ref('int_mrr_movements') }} m
inner join {{ ref('stg_customers') }} c on c.customer_id = m.customer_id
