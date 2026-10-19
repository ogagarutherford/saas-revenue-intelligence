-- Grain: one row per month per segment (plus 'All'), from the 13th month of data onward.
-- 12-month NRR/GRR: how much of the ARR held by customers 12 months ago is still there.
-- Monthly logo and revenue churn rates from the ARR bridge.

with snapshot as (
    select
        s.customer_id,
        s.month_start,
        s.mrr_eur,
        c.segment
    from {{ ref('int_customer_mrr_monthly') }} s
    inner join {{ ref('stg_customers') }} c on c.customer_id = s.customer_id
),

paired as (
    -- each customer active 12 months ago, with their MRR now
    select
        now_.month_start,
        then_.segment,
        then_.mrr_eur                                   as mrr_12m_ago,
        coalesce(now_.mrr_eur, 0)                       as mrr_now
    from snapshot then_
    inner join snapshot now_
        on  now_.customer_id = then_.customer_id
        and now_.month_start = {{ dbt.dateadd('month', 12, 'then_.month_start') }}
    where then_.mrr_eur > 0
),

segment_retention as (
    select
        month_start,
        segment,
        sum(mrr_12m_ago)                                            as starting_mrr,
        sum(mrr_now)                                                as retained_mrr,
        sum(case when mrr_now < mrr_12m_ago then mrr_now else mrr_12m_ago end) as retained_mrr_capped,
        count(*)                                                    as starting_customers,
        sum(case when mrr_now > 0 then 1 else 0 end)                as retained_customers
    from paired
    group by 1, 2
),

all_retention as (
    select
        month_start, 'All' as segment,
        sum(starting_mrr) as starting_mrr, sum(retained_mrr) as retained_mrr,
        sum(retained_mrr_capped) as retained_mrr_capped,
        sum(starting_customers) as starting_customers, sum(retained_customers) as retained_customers
    from segment_retention
    group by 1
),

retention as (
    select * from segment_retention
    union all
    select * from all_retention
),

bridge as (
    select * from {{ ref('mart_arr_bridge') }}
)

select
    cast(r.month_start as {{ dbt.type_string() }}) || '_' || r.segment as retention_id,
    r.month_start,
    r.segment,
    r.starting_customers,
    r.starting_mrr * 12                                             as starting_arr,
    r.retained_mrr / nullif(r.starting_mrr, 0)                      as nrr_12m,
    r.retained_mrr_capped / nullif(r.starting_mrr, 0)               as grr_12m,
    r.retained_customers * 1.0 / nullif(r.starting_customers, 0)    as logo_retention_12m,
    b.churned_customers * 1.0 / nullif(b.opening_customers, 0)      as monthly_logo_churn_rate,
    (b.churned_arr + b.contraction_arr) / nullif(b.opening_arr, 0)  as monthly_gross_revenue_churn_rate
from retention r
left join bridge b
    on b.month_start = r.month_start and b.segment = r.segment
