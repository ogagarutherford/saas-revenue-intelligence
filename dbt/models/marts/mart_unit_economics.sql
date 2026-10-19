-- Grain: one row per acquisition channel per year.
-- CAC, ARPA of newly acquired customers, churn, LTV, LTV:CAC and payback.
-- Assumptions (vars): gross_margin, max_lifetime_months.

{% set gm = var('gross_margin') %}
{% set max_life = var('max_lifetime_months') %}

with spend as (
    select
        {{ dbt.date_trunc('year', 'spend_month') }} as year_start,
        channel as acquisition_channel,
        sum(total_acquisition_cost_eur) as acquisition_cost_eur
    from {{ ref('stg_marketing_spend') }}
    group by 1, 2
),

new_customers as (
    select
        {{ dbt.date_trunc('year', 'signup_month') }} as year_start,
        acquisition_channel,
        count(*)              as new_customers,
        avg(first_mrr_eur)    as new_customer_arpa_eur
    from {{ ref('dim_customer') }}
    group by 1, 2
),

churn as (
    -- average monthly gross revenue churn of each channel's customer base during the year
    select
        {{ dbt.date_trunc('year', 'month_start') }} as year_start,
        acquisition_channel,
        sum(case when movement_type in ('churn', 'contraction') then -mrr_change_eur else 0 end)
            / nullif(sum(previous_mrr_eur), 0) as monthly_revenue_churn_rate
    from {{ ref('fct_mrr_monthly') }}
    group by 1, 2
),

joined as (
    select
        n.year_start,
        n.acquisition_channel,
        n.new_customers,
        s.acquisition_cost_eur,
        s.acquisition_cost_eur / nullif(n.new_customers, 0)  as cac_eur,
        n.new_customer_arpa_eur,
        c.monthly_revenue_churn_rate,
        case
            when c.monthly_revenue_churn_rate is null or c.monthly_revenue_churn_rate <= 1.0 / {{ max_life }}
                then {{ max_life }}
            else 1.0 / c.monthly_revenue_churn_rate
        end as expected_lifetime_months
    from new_customers n
    left join spend s on s.year_start = n.year_start and s.acquisition_channel = n.acquisition_channel
    left join churn c on c.year_start = n.year_start and c.acquisition_channel = n.acquisition_channel
)

select
    cast(year_start as {{ dbt.type_string() }}) || '_' || acquisition_channel as unit_economics_id,
    *,
    new_customer_arpa_eur * {{ gm }} * expected_lifetime_months                       as ltv_eur,
    new_customer_arpa_eur * {{ gm }} * expected_lifetime_months / nullif(cac_eur, 0)  as ltv_to_cac,
    cac_eur / nullif(new_customer_arpa_eur * {{ gm }}, 0)                             as cac_payback_months
from joined
