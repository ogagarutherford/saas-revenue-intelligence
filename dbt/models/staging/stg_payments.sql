with source as (
    select * from {{ source('raw', 'raw_payments') }}
)

select
    payment_id,
    invoice_id,
    cast(payment_date as date)          as payment_date,
    cast(amount_eur as decimal(12, 2))  as amount_eur,
    payment_method,
    status
from source
