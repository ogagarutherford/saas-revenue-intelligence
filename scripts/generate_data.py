"""
Synthetic B2B SaaS dataset generator — "Lumora", a fictional European
B2B workflow-analytics SaaS company (2023-01 to 2025-12).

All data is SYNTHETIC. The generator encodes explicit, documented business
assumptions (see docs/data_assumptions.md) so that churn, expansion and CAC
behave realistically and contain learnable signal for a churn model.

Usage:  python scripts/generate_data.py           -> writes CSVs to data/raw/
"""
from pathlib import Path
import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)
OUT = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT.mkdir(parents=True, exist_ok=True)

MONTHS = pd.date_range("2023-01-01", "2025-12-01", freq="MS")
N_MONTHS = len(MONTHS)

# ---------------------------------------------------------------- dimensions
plans = pd.DataFrame({
    "plan_id": ["PLN_STARTER", "PLN_GROWTH", "PLN_PRO", "PLN_ENTERPRISE"],
    "plan_name": ["Starter", "Growth", "Pro", "Enterprise"],
    "plan_tier": [1, 2, 3, 4],
    "list_price_per_seat_eur": [15.0, 29.0, 49.0, 79.0],
    "annual_discount_pct": [0.10, 0.15, 0.15, 0.20],
})
PRICE = dict(zip(plans.plan_id, plans.list_price_per_seat_eur))
DISC = dict(zip(plans.plan_id, plans.annual_discount_pct))
TIER = dict(zip(plans.plan_id, plans.plan_tier))
PLAN_BY_TIER = {v: k for k, v in TIER.items()}

REGIONS = ["DACH", "UK&I", "Nordics", "Benelux", "Southern Europe"]
COUNTRIES = {"DACH": ["DE", "AT", "CH"], "UK&I": ["GB", "IE"],
             "Nordics": ["SE", "DK", "NO", "FI"], "Benelux": ["NL", "BE"],
             "Southern Europe": ["ES", "IT", "PT"]}
INDUSTRIES = ["E-commerce", "Logistics", "Fintech", "Manufacturing",
              "Professional Services", "Healthcare", "Media", "Retail"]

reps = []
rep_id = 1
for team, n in [("SMB", 4), ("Mid-Market", 5), ("Enterprise", 3)]:
    for _ in range(n):
        reps.append({"sales_rep_id": f"REP_{rep_id:03d}",
                     "rep_name": f"Rep {rep_id:03d}",
                     "sales_team": team,
                     "region": REGIONS[(rep_id - 1) % len(REGIONS)],
                     "hire_date": (pd.Timestamp("2021-06-01")
                                   + pd.Timedelta(days=int(rng.integers(0, 700)))).date()})
        rep_id += 1
sales_reps = pd.DataFrame(reps)

SEGMENTS = {  # share of new logos, seat range, monthly churn base, plan weights (tier1..4)
    "SMB":        dict(share=0.62, seats=(3, 12),   churn=0.034, plans=[.55, .35, .10, .00], annual=.25),
    "Mid-Market": dict(share=0.30, seats=(10, 50),  churn=0.016, plans=[.05, .45, .40, .10], annual=.60),
    "Enterprise": dict(share=0.08, seats=(50, 250), churn=0.007, plans=[.00, .05, .40, .55], annual=.90),
}
CHANNELS = {  # channel -> (segment weights SMB/MM/ENT, engagement shift, is_sales_led)
    "Organic":        ([.75, .22, .03], +0.15, False),
    "Paid Search":    ([.70, .27, .03], -0.05, False),
    "Paid Social":    ([.80, .18, .02], -0.20, False),
    "Partner":        ([.40, .45, .15], +0.10, True),
    "Outbound Sales": ([.20, .55, .25], 0.00, True),
    "Events":         ([.30, .50, .20], +0.05, True),
}
CH_NAMES = list(CHANNELS)
CH_MIX = np.array([.24, .22, .16, .10, .20, .08])

# ---------------------------------------------------------------- simulation
customers, subs, invoices, payments, usage = [], [], [], [], []
cust_n = sub_n = inv_n = pay_n = 0


def monthly_mrr(plan_id, seats, cycle):
    p = PRICE[plan_id] * seats
    return round(p * (1 - DISC[plan_id]) if cycle == "annual" else p, 2)


for m_idx, month in enumerate(MONTHS):
    seasonal = 1.0 - 0.18 * (month.month in (7, 8, 12))      # summer/Dec slowdown
    n_new = rng.poisson(55 * (1.028 ** m_idx) * seasonal)
    for _ in range(n_new):
        cust_n += 1
        cid = f"CUST_{cust_n:05d}"
        channel = rng.choice(CH_NAMES, p=CH_MIX)
        seg_w, eng_shift, sales_led = CHANNELS[channel]
        segment = rng.choice(list(SEGMENTS), p=seg_w)
        cfg = SEGMENTS[segment]
        region = rng.choice(REGIONS, p=[.38, .20, .14, .14, .14])
        signup = month + pd.Timedelta(days=int(rng.integers(0, 28)))
        rep = None
        if sales_led or segment != "SMB":
            pool = sales_reps[sales_reps.sales_team == segment]
            rep = rng.choice(pool.sales_rep_id.values)
        customers.append({
            "customer_id": cid, "company_name": f"Company {cust_n:05d}",
            "country_code": rng.choice(COUNTRIES[region]), "region": region,
            "industry": rng.choice(INDUSTRIES), "segment": segment,
            "acquisition_channel": channel, "signup_date": signup.date(),
            "sales_rep_id": rep,
        })

        # latent engagement: drives usage AND churn (the learnable signal)
        engagement = rng.normal(0.0, 1.0) + eng_shift
        plan_id = PLAN_BY_TIER[int(rng.choice([1, 2, 3, 4], p=cfg["plans"]))]
        seats = int(rng.integers(*cfg["seats"]))
        cycle = "annual" if rng.random() < cfg["annual"] else "monthly"
        start = signup
        sub_n += 1
        sid = f"SUB_{sub_n:06d}"
        change = "new"
        churned = False

        for k in range(m_idx, N_MONTHS):
            cur = MONTHS[k]
            tenure = k - m_idx
            engagement += rng.normal(0, 0.18)                 # slow drift
            # --- monthly usage
            adoption = 1 / (1 + np.exp(-(engagement + 0.8)))
            active_users = int(np.clip(rng.binomial(seats, np.clip(adoption, .02, .98)), 0, seats))
            usage.append({
                "customer_id": cid, "usage_month": cur.date(), "seats_purchased": seats,
                "active_users": active_users,
                "sessions": int(rng.poisson(max(active_users, 0.3) * 14 * max(1 + .3 * engagement, .2))),
                "reports_created": int(rng.poisson(max(active_users, 0.2) * 3.5 * adoption)),
                "integrations_enabled": int(np.clip(round(1 + 2.5 * adoption + rng.normal(0, .7)), 0, 8)),
                "support_tickets": int(rng.poisson(0.4 + 1.2 * (1 - adoption) + 0.02 * seats ** .5)),
            })
            # --- billing for this month
            bill = (cycle == "monthly") or (tenure % 12 == 0)
            if bill:
                inv_n += 1
                amt = monthly_mrr(plan_id, seats, cycle) * (12 if cycle == "annual" else 1)
                inv_date = cur if k > m_idx else start
                invoices.append({
                    "invoice_id": f"INV_{inv_n:07d}", "customer_id": cid, "subscription_id": sid,
                    "invoice_date": pd.Timestamp(inv_date).date(),
                    "due_date": (pd.Timestamp(inv_date) + pd.Timedelta(days=14)).date(),
                    "billing_period_start": cur.date(),
                    "billing_period_end": (cur + pd.DateOffset(months=12 if cycle == "annual" else 1)
                                           - pd.Timedelta(days=1)).date(),
                    "amount_eur": round(amt, 2), "currency": "EUR",
                })
                fail_p = 0.02 + 0.05 * (engagement < -1)
                status = "failed" if rng.random() < fail_p else "succeeded"
                pay_n += 1
                payments.append({
                    "payment_id": f"PAY_{pay_n:07d}", "invoice_id": f"INV_{inv_n:07d}",
                    "payment_date": (pd.Timestamp(inv_date)
                                     + pd.Timedelta(days=int(rng.gamma(2, 4)))).date(),
                    "amount_eur": round(amt, 2) if status == "succeeded" else 0.0,
                    "payment_method": rng.choice(["card", "sepa_debit", "bank_transfer"],
                                                 p=[.45, .35, .20] if segment == "SMB" else [.10, .40, .50]),
                    "status": status,
                })
            if k == N_MONTHS - 1:
                break
            # --- churn decision (annual contracts only at renewal)
            can_churn = cycle == "monthly" or (tenure % 12 == 11)
            hazard = cfg["churn"] * np.exp(-0.75 * engagement) * (1.6 if tenure < 3 else 1.0)
            if cycle == "annual":
                hazard = 1 - (1 - hazard) ** 12                   # yearly-equivalent at renewal
            if can_churn and rng.random() < min(hazard, 0.9):
                end = MONTHS[k + 1] - pd.Timedelta(days=1)
                subs.append({"subscription_id": sid, "customer_id": cid, "plan_id": plan_id,
                             "seats": seats, "billing_cycle": cycle, "start_date": pd.Timestamp(start).date(),
                             "end_date": end.date(), "mrr_eur": monthly_mrr(plan_id, seats, cycle),
                             "change_reason": change, "ended_reason": "churned"})
                churned = True
                break
            # --- expansion / contraction / upgrade
            new_plan, new_seats = plan_id, seats
            r = rng.random()
            if r < 0.045 * (1 + max(engagement, 0)) and active_users >= 0.75 * seats:
                new_seats = int(seats * rng.uniform(1.05, 1.3)) + 1
            elif r < 0.058 + 0.01 * max(engagement, 0) and TIER[plan_id] < 4 and engagement > 0.3:
                new_plan = PLAN_BY_TIER[TIER[plan_id] + 1] if rng.random() < .5 else plan_id
            elif r > 0.985 and engagement < -0.5 and seats > 3:
                new_seats = max(3, int(seats * rng.uniform(0.6, 0.9)))
            if (new_plan, new_seats) != (plan_id, seats):
                end = MONTHS[k + 1] - pd.Timedelta(days=1)
                subs.append({"subscription_id": sid, "customer_id": cid, "plan_id": plan_id,
                             "seats": seats, "billing_cycle": cycle, "start_date": pd.Timestamp(start).date(),
                             "end_date": end.date(), "mrr_eur": monthly_mrr(plan_id, seats, cycle),
                             "change_reason": change, "ended_reason": "plan_change"})
                old_mrr = monthly_mrr(plan_id, seats, cycle)
                plan_id, seats = new_plan, new_seats
                change = "expansion" if monthly_mrr(plan_id, seats, cycle) > old_mrr else "contraction"
                sub_n += 1
                sid = f"SUB_{sub_n:06d}"
                start = MONTHS[k + 1]
        if not churned:
            subs.append({"subscription_id": sid, "customer_id": cid, "plan_id": plan_id,
                         "seats": seats, "billing_cycle": cycle, "start_date": pd.Timestamp(start).date(),
                         "end_date": None, "mrr_eur": monthly_mrr(plan_id, seats, cycle),
                         "change_reason": change, "ended_reason": None})

# ---------------------------------------------------------------- S&M costs (for CAC)
cust_df = pd.DataFrame(customers)
cust_df["signup_month"] = pd.to_datetime(cust_df.signup_date).dt.to_period("M").dt.to_timestamp()
new_by = cust_df.groupby(["signup_month", "acquisition_channel"]).size()
COST_PER_LOGO = {"Organic": 900, "Paid Search": 2600, "Paid Social": 2900,
                 "Partner": 3800, "Outbound Sales": 7500, "Events": 6200}
spend = []
for month in MONTHS:
    for ch in CH_NAMES:
        n = int(new_by.get((month, ch), 0))
        base = COST_PER_LOGO[ch] * max(n, 1) * rng.uniform(0.85, 1.2)
        spend.append({"spend_month": month.date(), "channel": ch,
                      "media_spend_eur": round(base * (0.0 if ch in ("Outbound Sales", "Events") else 0.8), 2),
                      "sales_cost_eur": round(base * (0.9 if ch in ("Outbound Sales", "Events") else 0.2), 2),
                      "tooling_cost_eur": round(base * 0.05, 2)})

# ---------------------------------------------------------------- write
tables = {
    "raw_customers": cust_df.drop(columns="signup_month"),
    "raw_plans": plans,
    "raw_sales_reps": sales_reps,
    "raw_subscriptions": pd.DataFrame(subs),
    "raw_invoices": pd.DataFrame(invoices),
    "raw_payments": pd.DataFrame(payments),
    "raw_product_usage": pd.DataFrame(usage),
    "raw_marketing_spend": pd.DataFrame(spend),
}
for name, df in tables.items():
    df.to_csv(OUT / f"{name}.csv", index=False)
    print(f"{name:22s} {len(df):>8,d} rows")