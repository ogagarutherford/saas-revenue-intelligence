# Star Schema — LUMORA.MARTS

```mermaid
erDiagram
    DIM_DATE ||--o{ FACT_MRR_MONTHLY : "month_end_date"
    DIM_CUSTOMER ||--o{ FACT_MRR_MONTHLY : customer_key
    DIM_PLAN ||--o{ FACT_MRR_MONTHLY : plan_key
    DIM_CUSTOMER ||--o{ FACT_SUBSCRIPTIONS : customer_key
    DIM_PLAN ||--o{ FACT_SUBSCRIPTIONS : plan_key
    DIM_DATE ||--o{ FACT_SUBSCRIPTIONS : start_date_key
    DIM_CUSTOMER ||--o{ FACT_INVOICES : customer_key
    DIM_DATE ||--o{ FACT_INVOICES : invoice_date_key
    FACT_INVOICES ||--o{ FACT_PAYMENTS : invoice_id
    DIM_DATE ||--o{ FACT_PAYMENTS : payment_date_key
    DIM_CUSTOMER ||--o{ FACT_PRODUCT_USAGE : customer_key
    DIM_DATE ||--o{ FACT_PRODUCT_USAGE : usage_month_key
    DIM_SALES_REP ||--o{ DIM_CUSTOMER : sales_rep_key

    FACT_MRR_MONTHLY {
        date month_end_date
        string customer_key
        string plan_key
        number mrr_eur
        number prev_mrr_eur
        string movement_type "new|expansion|contraction|churn|flat"
        number movement_mrr_eur
    }
    FACT_SUBSCRIPTIONS {
        string subscription_id PK
        string customer_key
        string plan_key
        date start_date_key
        date end_date
        number seats
        string billing_cycle
        number mrr_eur
    }
    FACT_INVOICES {
        string invoice_id PK
        string customer_key
        date invoice_date_key
        number amount_eur
    }
    FACT_PAYMENTS {
        string payment_id PK
        string invoice_id
        date payment_date_key
        number amount_eur
        string status
    }
    FACT_PRODUCT_USAGE {
        string customer_key
        date usage_month_key
        number active_users
        number seats_purchased
        number sessions
        number reports_created
        number support_tickets
    }
    DIM_CUSTOMER {
        string customer_key PK
        string segment
        string region
        string industry
        string acquisition_channel
        date signup_date
        string sales_rep_key
    }
    DIM_PLAN {
        string plan_key PK
        string plan_name
        number plan_tier
        number list_price_per_seat_eur
    }
    DIM_SALES_REP {
        string sales_rep_key PK
        string sales_team
        string region
    }
    DIM_DATE {
        date date_key PK
        number year
        number quarter
        number month
        boolean is_month_end
    }
```

## Fact grains (state these in interviews)

| Fact | Grain | Why it exists |
|---|---|---|
| `fact_mrr_monthly` | one row per customer per month-end | **The core analytical fact.** Periodic snapshot that makes MRR movements, NRR/GRR and cohorts simple, fast SQL. Derived from subscriptions in the intermediate layer. |
| `fact_subscriptions` | one row per subscription version (a plan/seat change closes a row and opens a new one) | Type-2-style history of contracts; source for the snapshot |
| `fact_invoices` | one row per invoice | Billing view (annual contracts invoice 12 months upfront — differs from MRR) |
| `fact_payments` | one row per payment attempt | Collections, failure rate, involuntary churn |
| `fact_product_usage` | one row per customer per month | Product health, churn-model features |

**Design decisions**
- `dim_customer` is SCD Type 1 (current attributes). Segment does not change in this dataset; in production, segment changes would justify Type 2.
- Acquisition channel lives in `dim_customer` rather than a separate dimension: it is a fixed attribute of the customer, and a 6-row dimension adds joins without adding value.
- Snowflake keys are the natural IDs (e.g. `CUST_00001`); surrogate keys via `dbt_utils.generate_surrogate_key` are added in Day 2 marts.
