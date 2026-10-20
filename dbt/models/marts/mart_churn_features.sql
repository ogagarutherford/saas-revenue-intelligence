-- Grain: one row per active customer per snapshot month.
-- Features use only information available at the snapshot month (no leakage).
-- Label: churned_next_3m = 1 if the customer's MRR drops to 0 in any of the next 3 months.
-- The latest 3 months have no label yet (null): those rows are what the model scores.

with snapshot as (
    select * from {{ ref('int_customer_mrr_monthly') }}
),

customers as (
    select customer_id, segment, acquisition_channel, signup_month
    from {{ ref('stg_customers') }}
),

subs as (
    select customer_id, billing_cycle, seats, start_date, end_date
    from {{ ref('stg_subscriptions') }}
),

usage as (
    select * from {{ ref('stg_product_usage') }}
),

failed_payments as (
    select
        i.customer_id,
        {{ dbt.date_trunc('month', 'p.payment_date') }} as payment_month,
        count(*) as failed_payments
    from {{ ref('stg_payments') }} p
    inner join {{ ref('stg_invoices') }} i on i.invoice_id = p.invoice_id
    where p.status = 'failed'
    group by 1, 2
),

last_month as (
    select max(month_start) as last_month_start from snapshot
),

base as (
    select
        s.customer_id,
        s.month_start                                                      as snapshot_month,
        s.mrr_eur,
        c.segment,
        c.acquisition_channel,
        {{ dbt.datediff('c.signup_month', 's.month_start', 'month') }}     as tenure_months,
        sub.billing_cycle,
        sub.seats,
        u.active_users,
        u.sessions,
        u.reports_created,
        u.integrations_enabled,
        u.support_tickets
    from snapshot s
    inner join customers c on c.customer_id = s.customer_id
    left join subs sub
        on  sub.customer_id = s.customer_id
        and sub.start_date <= s.month_end
        and (sub.end_date is null or sub.end_date >= s.month_end)
    left join usage u
        on u.customer_id = s.customer_id and u.usage_month = s.month_start
    where s.mrr_eur > 0
),

with_history as (
    select
        b.*,
        b.active_users * 1.0 / nullif(b.seats, 0)                          as seat_utilisation,
        b.sessions * 1.0 / nullif(b.active_users, 0)                       as sessions_per_active_user,
        lag(b.sessions, 3) over (partition by b.customer_id order by b.snapshot_month) as sessions_3m_ago,
        sum(b.support_tickets) over (
            partition by b.customer_id order by b.snapshot_month
            rows between 2 preceding and current row)                      as support_tickets_3m,
        lag(b.mrr_eur, 3) over (partition by b.customer_id order by b.snapshot_month) as mrr_3m_ago
    from base b
),

payments_3m as (
    select
        h.customer_id,
        h.snapshot_month,
        coalesce(sum(f.failed_payments), 0) as failed_payments_3m
    from with_history h
    left join failed_payments f
        on  f.customer_id = h.customer_id
        and f.payment_month <= h.snapshot_month
        and f.payment_month >  {{ dbt.dateadd('month', -3, 'h.snapshot_month') }}
    group by 1, 2
),

with_payments as (
    select h.*, pm.failed_payments_3m
    from with_history h
    inner join payments_3m pm
        on pm.customer_id = h.customer_id and pm.snapshot_month = h.snapshot_month
),

future as (
    -- did MRR hit 0 in any of the next 3 months?
    select
        s.customer_id,
        s.month_start as snapshot_month,
        max(case when f.mrr_eur = 0 then 1 else 0 end) as churned_next_3m
    from snapshot s
    inner join snapshot f
        on  f.customer_id = s.customer_id
        and f.month_start >  s.month_start
        and f.month_start <= {{ dbt.dateadd('month', 3, 's.month_start') }}
    group by 1, 2
)

select
    p.customer_id || '_' || cast(p.snapshot_month as {{ dbt.type_string() }}) as churn_feature_id,
    p.customer_id,
    p.snapshot_month,
    p.segment,
    p.acquisition_channel,
    p.billing_cycle,
    p.tenure_months,
    p.mrr_eur,
    p.seats,
    p.seat_utilisation,
    p.sessions_per_active_user,
    (p.sessions - p.sessions_3m_ago) * 1.0 / nullif(p.sessions_3m_ago, 0)  as sessions_change_3m,
    p.reports_created,
    p.integrations_enabled,
    p.support_tickets_3m,
    p.failed_payments_3m,
    case when p.mrr_3m_ago is not null and p.mrr_eur < p.mrr_3m_ago then 1 else 0 end as contracted_last_3m,
    case
        when p.snapshot_month > {{ dbt.dateadd('month', -3, 'lm.last_month_start') }} then null
        else coalesce(fu.churned_next_3m, 0)
    end as churned_next_3m
from with_payments p
cross join last_month lm
left join future fu
    on fu.customer_id = p.customer_id and fu.snapshot_month = p.snapshot_month
