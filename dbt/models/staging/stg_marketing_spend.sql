with source as (
    select * from {{ source('raw', 'raw_marketing_spend') }}
),

typed as (
    select
        cast(spend_month as date)               as spend_month,
        channel,
        cast(media_spend_eur as decimal(12, 2)) as media_spend_eur,
        cast(sales_cost_eur as decimal(12, 2))  as sales_cost_eur,
        cast(tooling_cost_eur as decimal(12, 2)) as tooling_cost_eur
    from source
)

select
    *,
    media_spend_eur + sales_cost_eur + tooling_cost_eur as total_acquisition_cost_eur
from typed
