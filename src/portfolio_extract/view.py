from __future__ import annotations
import re
import pandas as pd
from portfolio_extract.models import MetricName, CanonicalUnit, METRIC_UNIT, Sector
from portfolio_extract.evaluation import _norm_quarter

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

_CURRENCY_SYMBOL = {"USD": "$", "GBP": "£", "EUR": "€"}

def _quarter_int(q) -> int:
    m = re.search(r"[Qq]\s*([1-4])", str(q))
    return int(m.group(1)) if m else 0

def _format_cell(value, currency, unit, reason) -> str:
    if reason == "not_applicable":
        return "n/a"
    if value is None or pd.isna(value):
        return "—"
    if unit == CanonicalUnit.PERCENT:
        return f"{value:g}%"
    if unit == CanonicalUnit.COUNT:
        return f"{int(value)}"
    return _CURRENCY_SYMBOL.get(currency, "") + f"{value:g}M"

def overview_table(frame):
    metric_order = [m.value for m in MetricName if m.value in set(frame["metric"])]
    rows = {}
    for company, g in frame.groupby("company"):
        latest = g.sort_values(["period_year", "period_quarter"],
                               key=lambda s: s.map(_quarter_int) if s.name == "period_quarter" else s).iloc[-1:]
        latest_key = (latest.iloc[0]["period_year"], latest.iloc[0]["period_quarter"])
        cur = g[(g["period_year"] == latest_key[0]) & (g["period_quarter"] == latest_key[1])]
        cells = {}
        for metric in metric_order:
            mrow = cur[cur["metric"] == metric]
            if mrow.empty:
                cells[metric] = "—"
                continue
            row = mrow.iloc[0]
            cells[metric] = _format_cell(row["value"], row["currency"],
                                         METRIC_UNIT[MetricName(metric)], row["absence_reason"])
        rows[company] = cells
    return pd.DataFrame.from_dict(rows, orient="index", columns=metric_order)

def saas_comparison(frame, companies):
    saas_names = [n for n, c in companies.items() if c.sector == Sector.SAAS]
    cols = [MetricName.ARR.value, MetricName.NET_REVENUE_RETENTION.value]
    rows = {}
    for company in saas_names:
        g = frame[frame["company"] == company]
        if g.empty:
            continue
        latest = g.sort_values(["period_year", "period_quarter"],
                               key=lambda s: s.map(_quarter_int) if s.name == "period_quarter" else s).iloc[-1:]
        latest_key = (latest.iloc[0]["period_year"], latest.iloc[0]["period_quarter"])
        cur = g[(g["period_year"] == latest_key[0]) & (g["period_quarter"] == latest_key[1])]
        cells = {}
        for metric in cols:
            mrow = cur[(cur["metric"] == metric) & (cur["absence_reason"] == "present")]
            cells[metric] = mrow.iloc[0]["value"] if not mrow.empty else float("nan")
        rows[company] = cells
    return pd.DataFrame.from_dict(rows, orient="index", columns=cols)

def citation_for(records, company, period, metric):
    year, qtoken = period[0], _norm_quarter(period[1])
    matches = [r for r in records if r.company == company and r.period_year == year
               and _norm_quarter(r.period_quarter) == qtoken and r.metric == metric]
    reported = next((r for r in matches if not r.restated), None)
    restated = next((r for r in matches if r.restated), None)
    rec = restated or reported
    if rec is None:
        return None
    out = {
        "company": rec.company, "period": f"{year} {qtoken}", "metric": metric.value,
        "value": rec.value, "currency": rec.currency.value, "label_as_reported": rec.label_as_reported,
        "snippet": rec.source_snippet, "source_file": rec.source_file, "source_page": rec.source_page,
        "confidence": rec.confidence_tier.value if rec.confidence_tier else None,
        "basis": rec.basis, "extraction_method": rec.extraction_method.value,
        "bbox": rec.bbox,
        "restated": rec.restated, "original_value": None,
    }
    if restated is not None and reported is not None:
        out["original_value"] = reported.value
        out["restatement_note"] = (f"Restated: the figure of {restated.value} supersedes the originally "
                                   f"reported {reported.value}.")
    return out

def time_series(frame, company, metric, companies=None, include_predecessor=False):
    names = [company]
    if include_predecessor and companies and company in companies:
        pred = companies[company].predecessor
        if pred:
            names.append(pred.name)
    sub = frame[(frame["company"].isin(names)) & (frame["metric"] == metric.value)]
    return sub.sort_values(["period_year", "period_quarter"])
