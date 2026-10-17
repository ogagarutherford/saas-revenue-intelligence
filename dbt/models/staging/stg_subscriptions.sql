with source as (
    select * from {{ source('raw', 'raw_subscriptions') }}
)

select
    subscription_id,
    customer_id,
    plan_id,
    cast(seats as integer)                      as seats,
    billing_cycle,
    cast(start_date as date)                    as start_date,
    cast(nullif(trim(end_date), '') as date)    as end_date,   -- null = still active
    cast(mrr_eur as decimal(12, 2))             as mrr_eur,    -- annual contracts already normalised to monthly
    change_reason,                                              -- why this version started: new / expansion / contraction
    nullif(trim(ended_reason), '')              as ended_reason -- churned / plan_change / null
from source
