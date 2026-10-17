with source as (
    select * from {{ source('raw', 'raw_sales_reps') }}
)

select
    sales_rep_id,
    rep_name,
    sales_team,
    region,
    cast(hire_date as date) as hire_date
from source
