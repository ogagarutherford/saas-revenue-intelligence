with source as (
    select * from {{ source('raw', 'raw_invoices') }}
)

select
    invoice_id,
    customer_id,
    subscription_id,
    cast(invoice_date as date)          as invoice_date,
    cast(due_date as date)              as due_date,
    cast(billing_period_start as date)  as billing_period_start,
    cast(billing_period_end as date)    as billing_period_end,
    cast(amount_eur as decimal(12, 2))  as amount_eur,
    currency
from source
