# SaaS KPI Dictionary — Lumora

Single source of truth for every metric in this project. Each KPI states its
grain, formula and edge cases, so the dbt models, the churn model and the
dashboard all calculate it the same way.

**Conventions**
- Currency: EUR. Annual contracts are normalised to monthly (`annual price / 12`).
- MRR snapshots are taken on the **last calendar day of each month**.
- A customer is *active* in a month if they hold ≥1 subscription covering month-end.
- Assumed gross margin for LTV: **78%** (typical B2B SaaS; stated assumption, not data).

## Revenue

| KPI | Grain | Definition / formula | Notes |
|---|---|---|---|
| MRR | customer × month | Sum of `mrr_eur` of subscriptions active at month-end | Excludes one-off fees (none in data) |
| ARR | month | MRR × 12 | Run-rate, not recognised revenue |
| ARPA | month | MRR ÷ active customers | Split by segment; blended ARPA hides mix shift |
| New MRR | month | MRR of customers whose first-ever subscription month is this month | |
| Expansion MRR | month | Σ positive (MRRₜ − MRRₜ₋₁) for customers active in both months | Seats added or plan upgrade |
| Contraction MRR | month | Σ negative (MRRₜ − MRRₜ₋₁) for customers active in both months | Reported as a positive number |
| Churned MRR | month | MRRₜ₋₁ of customers active in t−1 and not active in t | |
| Net New MRR | month | New + Expansion − Contraction − Churned | Must reconcile: MRRₜ − MRRₜ₋₁ (dbt test) |
| New / Expansion / Contraction / Churned ARR | month | Corresponding MRR movement × 12 | |

## Retention

| KPI | Grain | Definition / formula | Notes |
|---|---|---|---|
| NRR (12-month) | month | MRRₜ of customers active at t−12 ÷ their MRR at t−12 | Includes expansion, excludes new logos |
| GRR (12-month) | month | Σ min(MRRₜ, MRRₜ₋₁₂) per customer ÷ Σ MRRₜ₋₁₂ | Capped at 100%; expansion cannot hide churn |
| Logo churn rate (monthly) | month | Customers churned in t ÷ customers active at end of t−1 | Annual contracts churn only at renewal → also report on renewal base |
| Gross revenue churn rate (monthly) | month | (Churned + Contraction MRR) ÷ MRRₜ₋₁ | |
| Cohort logo retention | signup cohort × months since signup | Active customers at month N ÷ cohort size | Cohorts by signup month; display by quarter |
| Cohort revenue retention | signup cohort × months since signup | Cohort MRR at month N ÷ cohort MRR at month 0 | Can exceed 100% |

## Unit economics

| KPI | Grain | Definition / formula | Notes |
|---|---|---|---|
| CAC | channel × period | (media + sales + tooling cost) ÷ new customers acquired | Blended and per channel; period ≥ quarter to smooth noise |
| LTV (simple) | segment | ARPA × gross margin ÷ monthly gross revenue churn rate | Sensitive to low churn → cap lifetime at 60 months |
| LTV (cohort) | cohort | Cumulative gross-margin revenue per acquired customer at month 24 | More conservative; preferred for decisions |
| LTV : CAC | channel / segment | LTV ÷ CAC | Rule of thumb ≥ 3 |
| CAC payback (months) | channel / segment | CAC ÷ (new-customer ARPA × gross margin) | Rule of thumb < 12 SMB, < 24 Enterprise |

## Product health & collections

| KPI | Grain | Definition / formula | Notes |
|---|---|---|---|
| Seat utilisation | customer × month | active_users ÷ seats_purchased | Leading churn indicator |
| Usage trend | customer × month | 3-month change in sessions per active user | Feature for churn model |
| Payment failure rate | month | Failed payments ÷ payments attempted | Involuntary-churn risk |
| Days to pay | invoice | payment_date − invoice_date | |

## Predictive

| Output | Definition |
|---|---|
| Churn label | Customer active at month t and not active at t+3 (90-day horizon) |
| Churn score | Model probability of the label, scored monthly for active customers |
