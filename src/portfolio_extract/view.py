from __future__ import annotations
import pandas as pd
from portfolio_extract.models import MetricName

def _reconcile(df):
    if df.empty:
        return df.assign(original_value=None, origin=None)
    out = []
    keys = ["company", "period_year", "period_quarter", "metric"]
    for _, g in df.groupby(keys, dropna=False):
        restated = g[g["restated"] == True]
        asrep = g[g["restated"] == False]
        if not restated.empty:
            row = restated.iloc[-1].to_dict()                 # on multiple restatements, last in frame order wins
            row["original_value"] = asrep.iloc[0]["value"] if not asrep.empty else None
            row["origin"] = "restated" if not asrep.empty else "restatement_only"
        else:
            row = asrep.iloc[0].to_dict()
            row["original_value"] = None
            row["origin"] = "reported"
        out.append(row)
    return pd.DataFrame(out)

_BASIS_GROUP = {"net_interest_spread": "lending", "saas_cogs": "saas_marketplace",
                "marketplace_contribution": "saas_marketplace"}
# Only gross margin gates by basis (lending GM is a net-interest-spread construct, not comparable
# with SaaS/marketplace GM). Revenue is the comparable top-line across business models; its basis
# is disclosure, not a comparison gate, so revenue is a single block.
_BASIS_VARIANCE = {MetricName.GROSS_MARGIN}

def _pivot(sub):
    return sub.pivot_table(index="company", columns=["period_year", "period_quarter"],
                           values="value", aggfunc="first")

def metric_matrix(frame, metric):
    sub = frame[frame["metric"] == metric.value]
    if metric in _BASIS_VARIANCE:
        return {grp: _pivot(g) for grp, g in
                sub.groupby(sub["basis"].map(lambda b: _BASIS_GROUP.get(b, "unknown")))}
    return {"all": _pivot(sub)}

def comparison_frame(records):
    rows = [{
        "company": r.company, "period_year": r.period_year, "period_quarter": r.period_quarter,
        "metric": r.metric.value, "value": r.value, "currency": r.currency.value, "basis": r.basis,
        "period_basis": r.period_basis.value, "absence_reason": r.absence_reason.value,
        "confidence_tier": r.confidence_tier.value if r.confidence_tier else None,
        "source_file": r.source_file, "restated": r.restated,
    } for r in records]
    return _reconcile(pd.DataFrame(rows))

def time_series(frame, company, metric, companies=None, include_predecessor=False):
    names = [company]
    if include_predecessor and companies and company in companies:
        pred = companies[company].predecessor
        if pred:
            names.append(pred.name)
    sub = frame[(frame["company"].isin(names)) & (frame["metric"] == metric.value)]
    return sub.sort_values(["period_year", "period_quarter"])
