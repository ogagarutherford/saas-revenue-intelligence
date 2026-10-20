"""
Churn prediction for Lumora (synthetic B2B SaaS data).

Question: which active customers are likely to churn in the next 3 months, and which
behaviours signal it early enough for Customer Success to act?

- Input: LUMORA.MARTS.MART_CHURN_FEATURES (built in dbt; features use only data up to each snapshot)
- Split by time, not randomly: train on snapshots up to 2024-12, test on 2025 snapshots
- Baseline: logistic regression. Challenger: gradient boosting.
- Outputs: results/churn_model_metrics.json, docs/images/churn_drivers.png,
           and the latest scores written back to LUMORA.MARTS.CHURN_SCORES

Run from the repo root:  python python/churn_model.py
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from warehouse import read_sql, write_table

ROOT = Path(__file__).resolve().parents[1]
(ROOT / "results").mkdir(exist_ok=True)
(ROOT / "docs" / "images").mkdir(parents=True, exist_ok=True)

NUMERIC = ["tenure_months", "mrr_eur", "seats", "seat_utilisation", "sessions_per_active_user",
           "sessions_change_3m", "reports_created", "integrations_enabled",
           "support_tickets_3m", "failed_payments_3m", "contracted_last_3m"]
CATEGORICAL = ["segment", "acquisition_channel", "billing_cycle"]
FEATURES = NUMERIC + CATEGORICAL
TRAIN_END = pd.Timestamp("2024-12-01")

df = read_sql("select * from LUMORA.MARTS.MART_CHURN_FEATURES")
df["snapshot_month"] = pd.to_datetime(df["snapshot_month"])
for c in NUMERIC:
    df[c] = pd.to_numeric(df[c], errors="coerce").astype(float)

labelled = df[df["churned_next_3m"].notna()].copy()
labelled["churned_next_3m"] = labelled["churned_next_3m"].astype(int)
train = labelled[labelled["snapshot_month"] <= TRAIN_END]
test = labelled[labelled["snapshot_month"] > TRAIN_END]
latest = df[df["snapshot_month"] == df["snapshot_month"].max()].copy()

prep = ColumnTransformer([
    ("num", Pipeline([("impute", SimpleImputer(strategy="median")), ("scale", StandardScaler())]), NUMERIC),
    ("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAL),
])
models = {
    "logistic_regression": Pipeline([("prep", prep), ("clf", LogisticRegression(max_iter=1000, class_weight="balanced"))]),
    "gradient_boosting": Pipeline([("prep", prep), ("clf", HistGradientBoostingClassifier(max_iter=300, learning_rate=0.05, random_state=42))]),
}


def recall_at_top(y, p, share=0.10):
    """Share of all churners caught if Customer Success contacts the riskiest `share` of customers."""
    n = max(1, int(len(p) * share))
    top = np.argsort(-p)[:n]
    return float(y.iloc[top].sum() / max(1, y.sum()))


results = {"train_rows": int(len(train)), "test_rows": int(len(test)),
           "test_churn_rate": round(float(test["churned_next_3m"].mean()), 4), "models": {}}
for name, model in models.items():
    model.fit(train[FEATURES], train["churned_next_3m"])
    p = model.predict_proba(test[FEATURES])[:, 1]
    y = test["churned_next_3m"]
    results["models"][name] = {
        "roc_auc": round(roc_auc_score(y, p), 3),
        "pr_auc": round(average_precision_score(y, p), 3),
        "recall_at_top_10pct": round(recall_at_top(y, p, 0.10), 3),
        "recall_at_top_20pct": round(recall_at_top(y, p, 0.20), 3),
    }

best_name = max(results["models"], key=lambda k: results["models"][k]["pr_auc"])
best = models[best_name]
results["selected_model"] = best_name
print(json.dumps(results, indent=2))
(ROOT / "results" / "churn_model_metrics.json").write_text(json.dumps(results, indent=2))

# Drivers: permutation importance on the test period (model-agnostic, in original feature terms)
sample = test.sample(min(5000, len(test)), random_state=42)
imp = permutation_importance(best, sample[FEATURES], sample["churned_next_3m"],
                             scoring="average_precision", n_repeats=5, random_state=42)
drivers = pd.Series(imp.importances_mean, index=FEATURES).sort_values()
drivers = drivers[drivers > 0].tail(8)
fig, ax = plt.subplots(figsize=(8, 4.5))
drivers.plot.barh(ax=ax, color="#1F3864")
ax.set_title(f"What predicts churn in the next 3 months ({best_name.replace('_', ' ')})")
ax.set_xlabel("Drop in PR-AUC when the feature is shuffled")
plt.tight_layout()
plt.savefig(ROOT / "docs" / "images" / "churn_drivers.png", dpi=150)
print("Top drivers:", ", ".join(drivers.index[::-1][:5]))

# Score the latest month: who should Customer Success call?
latest["churn_risk"] = best.predict_proba(latest[FEATURES])[:, 1]
latest["risk_band"] = pd.cut(latest["churn_risk"], [-0.01, 0.10, 0.25, 1.0], labels=["low", "medium", "high"]).astype(str)
scores = latest[["customer_id", "snapshot_month", "segment", "mrr_eur", "churn_risk", "risk_band"]].copy()
scores["snapshot_month"] = scores["snapshot_month"].dt.strftime("%Y-%m-%d")
print(scores["risk_band"].value_counts().to_string())
print(f"MRR in high-risk band: EUR {scores.loc[scores.risk_band == 'high', 'mrr_eur'].sum():,.0f}")
write_table(scores, "CHURN_SCORES")
