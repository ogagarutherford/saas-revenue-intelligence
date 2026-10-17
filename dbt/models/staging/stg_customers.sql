with source as (
    select * from {{ source('raw', 'raw_customers') }}
),

renamed as (
    select
        customer_id,
        company_name,
        country_code,
        region,
        industry,
        segment,
        acquisition_channel,
        cast(signup_date as date)               as signup_date,
        nullif(trim(sales_rep_id), '')          as sales_rep_id
    from source
)

select
    *,
    {{ dbt.date_trunc('month', 'signup_date') }} as signup_month
from renamed
