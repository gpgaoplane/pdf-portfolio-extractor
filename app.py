import json

import pandas as pd
import streamlit as st
from portfolio_extract.evaluation import summarize_report
from portfolio_extract.models import MetricName
from portfolio_extract.repository import load_records_jsonl
from portfolio_extract.registry import load_companies_json
from portfolio_extract.view import (comparison_frame, overview_table, citation_for,
                                     saas_comparison, time_series)

st.set_page_config(page_title="Portfolio Metrics Explorer", layout="wide")


@st.cache_data
def _load():
    return load_records_jsonl("eval/demo_records.jsonl")


@st.cache_data
def _load_companies():
    return load_companies_json("eval/demo_companies.json")


@st.cache_data
def _load_eval_report():
    with open("eval/eval_report.json", encoding="utf-8") as f:
        return json.load(f)


records = _load()
frame = comparison_frame(records)
companies = _load_companies()

st.title("Portfolio Metrics Explorer")
st.caption("Comparable metrics extracted from portfolio-company PDF reports, with provenance.")

present_records = [r for r in records if r.value is not None and not r.restated]
table_verified = sum(1 for r in present_records if r.extraction_method.value == "table_cell")
auto_verified_pct = round(100 * table_verified / max(len(present_records), 1))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Reports", len({r.source_file for r in records}))
c2.metric("Metrics extracted", len(present_records))
c3.metric("Auto-verified", f"{auto_verified_pct}%")
c4.metric("Companies", frame["company"].nunique())

st.divider()
st.header("Portfolio overview")
st.dataframe(overview_table(frame), use_container_width=True)

st.divider()
st.header("Trace a number to its source")
st.caption("Pick a company, period, and metric to see the figure, where it came from, and the original wording.")

_METRIC_BY_VALUE = {m.value: m for m in MetricName}


def _period_int(p):
    year, quarter = p
    q = int(quarter[1]) if len(quarter) > 1 and quarter[1].isdigit() else 0
    return (year, q)


tc1, tc2, tc3 = st.columns(3)
companies = sorted(frame["company"].unique())
sel_company = tc1.selectbox("Company", companies)

cdf = frame[frame["company"] == sel_company]
periods = sorted({(int(y), str(q)) for y, q in zip(cdf["period_year"], cdf["period_quarter"])},
                 key=_period_int)
period_labels = {f"{y} {q}": (y, q) for y, q in periods}
sel_period_label = tc2.selectbox("Period", list(period_labels))
sel_period = period_labels[sel_period_label]

metric_values = [m.value for m in MetricName if m.value in set(frame["metric"])]
sel_metric_value = tc3.selectbox("Metric", metric_values,
                                 format_func=lambda v: v.replace("_", " ").title())
sel_metric = _METRIC_BY_VALUE[sel_metric_value]

st.write("")
citation = citation_for(records, sel_company, sel_period, sel_metric)
if citation is None:
    st.markdown(
        "<span style='color:#888'>No reported value for this cell "
        "(not applicable or not disclosed).</span>",
        unsafe_allow_html=True,
    )
else:
    _CONF_COLOR = {"HIGH": "#1a7f37", "MEDIUM": "#9a6700", "LOW": "#b35900"}
    sym = {"USD": "$", "GBP": "£", "EUR": "€"}.get(citation["currency"], "")
    val = citation["value"]
    headline = f"{sym}{val:g}" if val is not None else "—"

    st.markdown(f"### {headline}")
    st.markdown(
        f"Reported as **{citation['label_as_reported']}** "
        f"in {citation['company']}'s {citation['period']} report."
    )
    st.markdown(f"> {citation['snippet']}")
    st.caption(f"Source: {citation['source_file']} · p.{citation['source_page']}")

    conf = citation["confidence"]
    if conf:
        color = _CONF_COLOR.get(conf, "#555")
        st.markdown(
            f"<span style='background:{color};color:white;padding:2px 8px;"
            f"border-radius:10px;font-size:0.8em'>Confidence: {conf}</span>",
            unsafe_allow_html=True,
        )
    if citation["basis"]:
        st.caption(f"Basis: {citation['basis']}")
    if citation.get("restatement_note"):
        st.warning(f"{citation['restatement_note']} Originally reported: {citation['original_value']}.")

st.divider()
st.header("Insights")

st.subheader("How are the SaaS companies growing and retaining?")
st.caption("ARR ($M) and net revenue retention (%) for SaaS companies, latest reported period.")
saas = saas_comparison(frame, companies)
if saas.empty:
    st.info("No SaaS companies with ARR or retention in the current data.")
else:
    chart = saas.rename(columns={"arr": "ARR ($M)", "net_revenue_retention": "NRR (%)"})
    st.dataframe(chart, use_container_width=True)
    st.bar_chart(chart)
    leaders = saas["arr"].dropna()
    if not leaders.empty:
        top = leaders.idxmax()
        st.markdown(
            f"{top} leads on ARR at ${leaders.max():g}M; retention above 100% across these "
            f"companies means existing customers are expanding faster than they churn."
        )

st.write("")
st.subheader("How is a company tracking over time?")
st.caption("Pick a company and metric to see the trajectory across reported periods.")

ts_companies = sorted(frame["company"].unique())
_default_ts = ts_companies.index("ApexFreight") if "ApexFreight" in ts_companies else 0
ic1, ic2 = st.columns(2)
ts_company = ic1.selectbox("Company", ts_companies, index=_default_ts, key="ts_company")

ts_metric_values = [m.value for m in MetricName if m.value in set(frame["metric"])]
ts_metric_value = ic2.selectbox("Metric", ts_metric_values, key="ts_metric",
                                format_func=lambda v: v.replace("_", " ").title())
ts_metric = _METRIC_BY_VALUE[ts_metric_value]

ts = time_series(frame, ts_company, ts_metric, companies=companies, include_predecessor=True)
ts = ts[ts["absence_reason"] == "present"]
if ts.empty:
    st.info("No reported values for this company and metric.")
else:
    ts = ts.copy()
    ts["period"] = [f"{y} {q}" for y, q in zip(ts["period_year"], ts["period_quarter"])]
    st.line_chart(ts.set_index("period")["value"])
    pred = companies[ts_company].predecessor if ts_company in companies else None
    if pred and pred.name in set(ts["company"]):
        st.caption(f"Includes {pred.name} before the rename to {ts_company}.")

st.divider()
st.header("Trust & quality")

st.markdown(
    "Accuracy here is measured against a label set transcribed by hand from the source PDFs, "
    "independent of the extractor. Each labelled cell records the expected value and whether the "
    "metric is present, null, or not applicable in that report. The extractor's output is then "
    "compared cell by cell."
)

st.subheader("What this evaluation does and does not show")
st.markdown(
    "The corpus is clean and well formatted, so these numbers describe behaviour on tidy inputs "
    "rather than worst-case scrambled ones. The holdout is prior quarters of companies the "
    "extractor has already seen, so it tests generalization across time, not generalization to a "
    "brand-new company with an unfamiliar report layout. And because the error rate on this corpus "
    "is near zero, the results cannot demonstrate two mechanisms that do exist in the pipeline: "
    "source-table verification catching a wrong value, and the confidence tiers separating reliable "
    "extractions from shaky ones. Both would only show their worth on messier inputs."
)

st.subheader("Supporting evidence")
st.caption(
    "Two label sets. Dev is the set used while building the extractor; holdout is held-back prior "
    "quarters of the same companies. Denominators are shown so nothing hides behind a single percentage."
)

report = _load_eval_report()
_LABEL = {"dev": "Dev", "holdout": "Holdout"}

for split in ("dev", "holdout"):
    rep = report[split]
    s = summarize_report(rep)
    so, st_total = s["status_agreement"]

    st.markdown(f"#### {_LABEL[split]}")
    e1, e2, e3, e4 = st.columns(4)
    e1.metric("Present values correct", f"{s['present_correct']} of {s['present_total']}")
    e2.metric("Verified against source tables", f"{s['pct_verified']}%")
    e3.metric("Omissions / hallucinations", f"{s['omissions']} / {s['hallucinations']}")
    e4.metric("Status agreement", f"{so} of {st_total}")

    st.write("")
    pm = rep["score"]["per_metric"]
    pm_df = pd.DataFrame(
        [(m.replace("_", " ").title(), f"{c} of {n}") for m, (c, n) in pm.items()],
        columns=["Metric", "Correct of present"],
    )
    st.dataframe(pm_df, use_container_width=True, hide_index=True)

    cal = rep["calibration"]
    cal_df = pd.DataFrame(
        [(tier, c, w) for tier, (c, w) in cal.items()],
        columns=["Confidence tier", "Correct", "Wrong"],
    )
    with st.expander(f"Confidence calibration ({_LABEL[split]})"):
        st.dataframe(cal_df, use_container_width=True, hide_index=True)

    st.write("")
