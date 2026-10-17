with source as (
    select * from {{ source('raw', 'raw_plans') }}
)

select
    plan_id,
    plan_name,
    cast(plan_tier as integer)                  as plan_tier,
    cast(list_price_per_seat_eur as decimal(10, 2)) as list_price_per_seat_eur,
    cast(annual_discount_pct as decimal(5, 4))  as annual_discount_pct
from source
