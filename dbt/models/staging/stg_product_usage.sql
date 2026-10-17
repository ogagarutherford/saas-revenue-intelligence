with source as (
    select * from {{ source('raw', 'raw_product_usage') }}
)

select
    customer_id,
    cast(usage_month as date)               as usage_month,
    cast(seats_purchased as integer)        as seats_purchased,
    cast(active_users as integer)           as active_users,
    cast(sessions as integer)               as sessions,
    cast(reports_created as integer)        as reports_created,
    cast(integrations_enabled as integer)   as integrations_enabled,
    cast(support_tickets as integer)        as support_tickets
from source
