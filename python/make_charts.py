"""
Charts for the README: ARR bridge, NRR vs GRR by segment, cohort retention, unit economics.
Outputs PNGs to docs/images/. Run from the repo root:  python python/make_charts.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from warehouse import read_sql

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "images"
OUT.mkdir(parents=True, exist_ok=True)
NAVY, RED, GREEN, GREY = "#1F3864", "#C00000", "#548235", "#A6A6A6"

# 1. 2025 ARR bridge (waterfall)
b = read_sql("select * from LUMORA.MARTS.MART_ARR_BRIDGE where segment = 'All' order by month_start")
b["month_start"] = pd.to_datetime(b["month_start"])
for c in ["opening_arr", "new_arr", "reactivation_arr", "expansion_arr", "contraction_arr", "churned_arr", "closing_arr"]:
    b[c] = b[c].astype(float)
y = b[b["month_start"].dt.year == b["month_start"].dt.year.max()]
steps = [("Opening", y["opening_arr"].iloc[0]), ("New", y["new_arr"].sum() + y["reactivation_arr"].sum()),
         ("Expansion", y["expansion_arr"].sum()), ("Contraction", -y["contraction_arr"].sum()),
         ("Churn", -y["churned_arr"].sum()), ("Closing", y["closing_arr"].iloc[-1])]
fig, ax = plt.subplots(figsize=(8, 4.5))
running = 0
for i, (label, val) in enumerate(steps):
    if label in ("Opening", "Closing"):
        bottom, height, colour, text = 0, val, NAVY, f"{val / 1e6:.1f}"
        running = val
    else:
        bottom = running if val >= 0 else running + val
        height, colour, text = abs(val), (GREEN if val >= 0 else RED), f"{val / 1e6:+.1f}"
        running += val
    ax.bar(i, height / 1e6, bottom=bottom / 1e6, color=colour)
    ax.text(i, (bottom + height) / 1e6 + 0.6, text, ha="center", fontsize=9)
ax.set_xticks(range(len(steps)), [s[0] for s in steps])
ax.set_ylabel("ARR (EUR millions)")
ax.set_title(f"ARR bridge {int(y['month_start'].dt.year.max())}: growth is driven by new logos; churn offsets expansion")
plt.tight_layout(); plt.savefig(OUT / "arr_bridge.png", dpi=150); plt.close()

# 2. NRR vs GRR by segment (latest month)
r = read_sql("select * from LUMORA.MARTS.MART_RETENTION")
r["month_start"] = pd.to_datetime(r["month_start"])
r = r[r["month_start"] == r["month_start"].max()].set_index("segment").reindex(["SMB", "Mid-Market", "Enterprise", "All"])
x = np.arange(len(r)); w = 0.38
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.bar(x - w / 2, r["nrr_12m"].astype(float) * 100, w, label="NRR (12m)", color=NAVY)
ax.bar(x + w / 2, r["grr_12m"].astype(float) * 100, w, label="GRR (12m)", color=GREY)
ax.axhline(100, color="black", lw=0.8, ls="--")
for i, (n, g) in enumerate(zip(r["nrr_12m"].astype(float), r["grr_12m"].astype(float))):
    ax.text(i - w / 2, n * 100 + 1, f"{n:.0%}", ha="center", fontsize=9)
    ax.text(i + w / 2, g * 100 + 1, f"{g:.0%}", ha="center", fontsize=9)
ax.set_xticks(x, r.index); ax.set_ylim(0, 115); ax.set_ylabel("%")
ax.set_title("NRR vs GRR by segment: the leak is concentrated in SMB"); ax.legend()
plt.tight_layout(); plt.savefig(OUT / "nrr_vs_grr.png", dpi=150); plt.close()

# 3. Cohort logo retention heatmap (quarterly cohorts, first 12 months)
c = read_sql("select signup_month, months_since_signup, active_customers, cohort_customers from LUMORA.MARTS.MART_COHORT_RETENTION")
c["signup_month"] = pd.to_datetime(c["signup_month"])
c = c[c["months_since_signup"].astype(int) <= 12]
c["cohort"] = c["signup_month"].dt.to_period("Q").astype(str)
agg = c.groupby(["cohort", "months_since_signup"])[["active_customers", "cohort_customers"]].sum()
heat = (agg["active_customers"] / agg["cohort_customers"]).unstack()
fig, ax = plt.subplots(figsize=(9, 5))
im = ax.imshow(heat.values * 100, aspect="auto", cmap="Blues", vmin=50, vmax=100)
ax.set_yticks(range(len(heat)), heat.index); ax.set_xticks(range(heat.shape[1]), heat.columns.astype(int))
ax.set_xlabel("Months since signup"); ax.set_title("Logo retention by signup cohort (%)")
for i in range(heat.shape[0]):
    for j in range(heat.shape[1]):
        v = heat.values[i, j]
        if not np.isnan(v):
            ax.text(j, i, f"{v * 100:.0f}", ha="center", va="center", fontsize=6,
                    color="white" if v > 0.8 else "black")
plt.colorbar(im, ax=ax, shrink=0.8)
plt.tight_layout(); plt.savefig(OUT / "cohort_retention.png", dpi=150); plt.close()

# 4. Unit economics by channel (latest year)
u = read_sql("select * from LUMORA.MARTS.MART_UNIT_ECONOMICS")
u["year_start"] = pd.to_datetime(u["year_start"])
u = u[u["year_start"] == u["year_start"].max()].copy()
u["ltv_to_cac"] = u["ltv_to_cac"].astype(float); u["cac_eur"] = u["cac_eur"].astype(float)
u = u.sort_values("ltv_to_cac")
fig, ax = plt.subplots(figsize=(8, 4.5))
ax.barh(u["acquisition_channel"], u["ltv_to_cac"], color=[RED if v < u["ltv_to_cac"].median() else NAVY for v in u["ltv_to_cac"]])
for i, (v, cac) in enumerate(zip(u["ltv_to_cac"], u["cac_eur"])):
    ax.text(v + 0.3, i, f"{v:.1f}x  (CAC EUR {cac:,.0f})", va="center", fontsize=8)
ax.set_xlabel("LTV : CAC"); ax.set_title("Cheapest channels are not the most valuable (synthetic cost assumptions)")
plt.tight_layout(); plt.savefig(OUT / "unit_economics.png", dpi=150); plt.close()
print("Charts written to docs/images/: arr_bridge.png, nrr_vs_grr.png, cohort_retention.png, unit_economics.png")
