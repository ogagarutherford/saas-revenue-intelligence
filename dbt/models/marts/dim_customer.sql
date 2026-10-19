-- One row per customer: fixed attributes plus first plan and first MRR.
with customers as (
    select * from {{ ref('stg_customers') }}
),

first_month as (
    select
        customer_id,
        plan_id  as first_plan_id,
        mrr_eur  as first_mrr_eur
    from {{ ref('int_mrr_movements') }}
    where movement_type = 'new'
)

select
    c.customer_id,
    c.company_name,
    c.country_code,
    c.region,
    c.industry,
    c.segment,
    c.acquisition_channel,
    c.signup_date,
    c.signup_month,
    c.sales_rep_id,
    f.first_plan_id,
    f.first_mrr_eur
from customers c
left join first_month f on f.customer_id = c.customer_id
