-- Grain: one row per signup cohort (month) per month since signup.
-- Base for the cohort retention heatmap.

with snapshot as (
    select
        s.customer_id,
        s.month_start,
        s.mrr_eur,
        c.signup_month
    from {{ ref('int_customer_mrr_monthly') }} s
    inner join {{ ref('stg_customers') }} c on c.customer_id = s.customer_id
),

with_age as (
    select
        *,
        {{ dbt.datediff('signup_month', 'month_start', 'month') }} as months_since_signup
    from snapshot
),

cohort_base as (
    select signup_month, count(*) as cohort_customers, sum(mrr_eur) as cohort_starting_mrr
    from with_age
    where months_since_signup = 0
    group by 1
)

select
    cast(a.signup_month as {{ dbt.type_string() }}) || '_' || cast(a.months_since_signup as {{ dbt.type_string() }}) as cohort_cell_id,
    a.signup_month,
    a.months_since_signup,
    b.cohort_customers,
    sum(case when a.mrr_eur > 0 then 1 else 0 end)                          as active_customers,
    sum(case when a.mrr_eur > 0 then 1 else 0 end) * 1.0 / b.cohort_customers as logo_retention,
    sum(a.mrr_eur) / nullif(b.cohort_starting_mrr, 0)                       as revenue_retention
from with_age a
inner join cohort_base b on b.signup_month = a.signup_month
group by a.signup_month, a.months_since_signup, b.cohort_customers, b.cohort_starting_mrr
