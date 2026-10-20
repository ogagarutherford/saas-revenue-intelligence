"""
12-month ARR forecast with three scenarios, from the dbt ARR bridge.

Assumptions come from the trailing 12 months and are printed, so they can be challenged:
monthly new ARR run-rate, and expansion / contraction / churn as a share of opening ARR.

Outputs: results/arr_forecast_scenarios.csv, docs/images/arr_forecast.png
Run from the repo root:  python python/arr_forecast.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from warehouse import read_sql

ROOT = Path(__file__).resolve().parents[1]
(ROOT / "results").mkdir(exist_ok=True)
(ROOT / "docs" / "images").mkdir(parents=True, exist_ok=True)

b = read_sql("""
    select month_start, opening_arr, new_arr, reactivation_arr, expansion_arr,
           contraction_arr, churned_arr, closing_arr
    from LUMORA.MARTS.MART_ARR_BRIDGE
    where segment = 'All'
    order by month_start
""")
b["month_start"] = pd.to_datetime(b["month_start"])
for c in b.columns[1:]:
    b[c] = b[c].astype(float)
t12 = b.tail(12)

new_run = (t12["new_arr"] + t12["reactivation_arr"]).mean()
exp_r = (t12["expansion_arr"] / t12["opening_arr"]).mean()
con_r = (t12["contraction_arr"] / t12["opening_arr"]).mean()
churn_r = (t12["churned_arr"] / t12["opening_arr"]).mean()
start = t12["closing_arr"].iloc[-1]
print(f"Starting ARR: EUR {start:,.0f}")
print(f"Assumptions (trailing 12m): new ARR EUR {new_run:,.0f}/month; expansion {exp_r:.2%}, "
      f"contraction {con_r:.2%}, churn {churn_r:.2%} of opening ARR per month")


def project(new_mult=1.0, exp_mult=1.0, churn_mult=1.0, months=12):
    arr, path = start, []
    for _ in range(months):
        arr = arr + new_run * new_mult + arr * (exp_r * exp_mult - con_r - churn_r * churn_mult)
        path.append(arr)
    return path


months = pd.date_range(b["month_start"].max() + pd.offsets.MonthBegin(1), periods=12, freq="MS")
fc = pd.DataFrame({
    "base": project(),
    "downside_churn_plus_20pct_new_minus_10pct": project(new_mult=0.9, churn_mult=1.2),
    "upside_expansion_plus_10pct_new_plus_10pct": project(new_mult=1.1, exp_mult=1.1),
    "retention_fix_churn_minus_25pct": project(churn_mult=0.75),
}, index=months).round(0)
fc.to_csv(ROOT / "results" / "arr_forecast_scenarios.csv", index_label="month_start")
print((fc.iloc[[2, 5, 11]] / 1e6).round(2).to_string())

fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(b["month_start"].tail(24), b["closing_arr"].tail(24) / 1e6, color="#1F3864", lw=2, label="Actual")
styles = {"base": ("#1F3864", "--"), "downside_churn_plus_20pct_new_minus_10pct": ("#C00000", ":"),
          "upside_expansion_plus_10pct_new_plus_10pct": ("#548235", ":"), "retention_fix_churn_minus_25pct": ("#BF8F00", "-.")}
for col, (colour, ls) in styles.items():
    ax.plot(fc.index, fc[col] / 1e6, color=colour, ls=ls, lw=1.8, label=col.replace("_", " "))
ax.set_title("ARR: last 24 months and 12-month scenarios")
ax.set_ylabel("ARR (EUR millions)")
ax.legend(fontsize=7, loc="upper left")
plt.tight_layout()
plt.savefig(ROOT / "docs" / "images" / "arr_forecast.png", dpi=150)
