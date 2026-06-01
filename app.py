import json
import os

import pandas as pd
import streamlit as st
from portfolio_extract.evaluation import summarize_report, _norm_quarter
from portfolio_extract.models import MetricName, METRIC_UNIT, CanonicalUnit
from portfolio_extract.repository import load_records_jsonl
from portfolio_extract.registry import load_companies_json
from portfolio_extract.view import (comparison_frame, overview_table, citation_for,
                                     saas_comparison, time_series, revenue_comparison, _quarter_int)
from portfolio_extract.structural import render_page_png

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


if "live_records" not in st.session_state:
    st.session_state.live_records = []
if "live_companies" not in st.session_state:
    st.session_state.live_companies = {}


def _cell_key(r):
    return (r.company, r.period_year, _norm_quarter(str(r.period_quarter)), r.metric)


live = st.session_state.live_records
_live_keys = {_cell_key(r) for r in live}
records = [r for r in _load() if _cell_key(r) not in _live_keys] + live
frame = comparison_frame(records)
companies = {**_load_companies(), **st.session_state.live_companies}

live_source_files = {r.source_file for r in live}
live_company_periods = {(r.company, r.period_year, str(r.period_quarter)) for r in live}

st.title("Portfolio Metrics Explorer")
st.caption("Comparable metrics extracted from portfolio-company PDF reports, with provenance.")

present_records = [r for r in records if r.value is not None and not r.restated]
table_verified = sum(1 for r in present_records if r.extraction_method.value == "table_cell")
auto_verified_pct = round(100 * table_verified / max(len(present_records), 1))

c1, c2, c3, c4 = st.columns(4)
c1.metric("Reports", len({r.source_file for r in records}))
c2.metric("Metrics extracted", len(present_records))
c3.metric("Table-sourced", f"{auto_verified_pct}%", help="Share of extracted values matched to a source-table cell. Distinct from the labelled-set accuracy in Trust & quality.")
c4.metric("Companies", frame["company"].nunique())

if live:
    periods_shown = sorted({f"{r.company} {r.period_year} {r.period_quarter}" for r in live})
    n_live_present = sum(1 for r in live if r.value is not None and not r.restated)
    st.info(
        f"Live this session: {', '.join(periods_shown)}. {n_live_present} metric values added "
        "to the matrix below. Source-verified (Layer 1); not checked against ground truth (Layer 2)."
    )
    if st.button("Clear live additions"):
        import shutil
        if st.session_state.get("upload_dir"):
            shutil.rmtree(st.session_state.upload_dir, ignore_errors=True)
        st.session_state.live_records = []
        st.session_state.live_companies = {}
        for k in ("last_extract", "live_pdf_paths", "upload_dir"):
            st.session_state.pop(k, None)
        st.rerun()

st.divider()
st.header("Portfolio overview")


def _latest_period(company):
    g = frame[frame["company"] == company]
    last = g.sort_values(
        ["period_year", "period_quarter"],
        key=lambda s: s.map(_quarter_int) if s.name == "period_quarter" else s,
    ).iloc[-1]
    return (company, last["period_year"], str(last["period_quarter"]))


def _live_at_latest(company):
    return _latest_period(company) in live_company_periods


def _mark_live_index(df):
    marked = {c for c in df.index if _live_at_latest(c)}
    return df.rename(index={c: f"{c} (live)" for c in marked}) if marked else df


_overview = _mark_live_index(overview_table(frame))
st.dataframe(_overview, use_container_width=True)
if any(_live_at_latest(c) for c in frame["company"].unique()):
    st.caption(
        "Companies tagged “(live)” were extracted this session; they carry source verification "
        "(Layer 1) but no ground-truth check (Layer 2)."
    )

st.divider()
st.header("Trace a number to its source")
st.caption("Pick a company, period, and metric to see the figure, where it came from, and the original wording.")

_METRIC_BY_VALUE = {m.value: m for m in MetricName}


def _period_int(p):
    year, quarter = p
    q = int(quarter[1]) if len(quarter) > 1 and quarter[1].isdigit() else 0
    return (year, q)


tc1, tc2, tc3 = st.columns(3)
company_names = sorted(frame["company"].unique())
sel_company = tc1.selectbox("Company", company_names)

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
    unit = METRIC_UNIT[sel_metric]
    if val is None:
        headline = "—"
    elif unit == CanonicalUnit.PERCENT:
        headline = f"{val:g}%"
    elif unit == CanonicalUnit.COUNT:
        headline = f"{int(val)}"
    else:
        headline = f"{sym}{val:g}M"

    st.markdown(f"<div style='font-size:2rem;font-weight:700;margin:0.2em 0'>{headline}</div>",
                unsafe_allow_html=True)
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
    if citation["source_file"] in live_source_files:
        st.markdown(
            "<span style='background:#8a5a00;color:white;padding:2px 8px;"
            "border-radius:10px;font-size:0.8em'>Live · Layer 2: unverified</span>",
            unsafe_allow_html=True,
        )
    if citation["basis"]:
        st.caption(f"Basis: {citation['basis']}")
    if citation.get("restatement_note"):
        st.warning(citation["restatement_note"])

    _uploaded_paths = st.session_state.get("live_pdf_paths", {})
    src_path = _uploaded_paths.get(citation["source_file"]) or os.path.join("data", citation["source_file"] or "")
    if citation["source_page"] and citation["source_file"] and os.path.exists(src_path):
        with st.expander("Verify in source"):
            try:
                png = render_page_png(src_path, citation["source_page"], citation.get("bbox"))
                cap = ("Highlighted cell is the matched value" if citation.get("bbox")
                       else "Prose value; see snippet above (no table cell to box).")
                st.image(png, caption=cap)
            except Exception as exc:
                st.caption(f"Could not render source page ({exc}).")

st.divider()
st.header("Insights")

st.subheader("Revenue across the portfolio")
st.caption(
    "Latest reported quarterly revenue for every company, across all business models. Native "
    "currency (mostly USD; PeopleFlow in GBP), not FX-converted. The revenue basis differs by "
    "model (SaaS recognized revenue, marketplace net fees, lending interest income); each figure "
    "traces to its source above."
)
_rev = revenue_comparison(frame)
if _rev.empty:
    st.info("No revenue values in the current data.")
else:
    _SYM = {"USD": "$", "GBP": "£", "EUR": "€"}

    def _rev_label(c):
        cur = _SYM.get(_rev.loc[c, "currency"], "")
        tag = f" {cur}" if cur and cur != "$" else ""
        return f"{c}{tag}{' (live)' if _live_at_latest(c) else ''}"

    _rev_plot = _rev[["revenue"]].copy()
    _rev_plot.index = [_rev_label(c) for c in _rev.index]
    st.bar_chart(_rev_plot.rename(columns={"revenue": "Revenue (M, native currency)"}))
    _top = _rev["revenue"].idxmax()
    st.markdown(
        f"{_top} reports the highest revenue this period at "
        f"{_SYM.get(_rev.loc[_top, 'currency'], '')}{_rev.loc[_top, 'revenue']:g}M. Revenue is the "
        "one top-line that compares across SaaS, marketplace, and lending, which is why it spans "
        "the whole portfolio while ARR and retention below stay SaaS-only."
    )

st.write("")
st.subheader("How are the SaaS companies growing and retaining?")
st.caption("ARR ($M) and net revenue retention (%) for SaaS companies, latest reported period.")
saas = saas_comparison(frame, companies)
if saas.empty:
    st.info("No SaaS companies with ARR or retention in the current data.")
else:
    saas_m = _mark_live_index(saas)
    chart = saas_m.rename(columns={"arr": "ARR ($M)", "net_revenue_retention": "NRR (%)"})
    st.dataframe(chart, use_container_width=True)
    # ARR ($M) and NRR (%) are on different scales; chart them separately so neither flattens the other.
    ac, nc = st.columns(2)
    ac.caption("ARR ($M)")
    ac.bar_chart(saas_m[["arr"]].dropna(how="all").rename(columns={"arr": "ARR ($M)"}))
    nc.caption("Net revenue retention (%)")
    nc.bar_chart(saas_m[["net_revenue_retention"]].dropna(how="all").rename(columns={"net_revenue_retention": "NRR (%)"}))
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


st.divider()
st.header("Live extraction")
st.caption(
    "Run the real pipeline on a report. Needs an LLM key in .env; otherwise the prebuilt "
    "results above stand."
)
try:
    from pathlib import Path

    from dotenv import load_dotenv

    pdfs = sorted(p.name for p in Path("data").glob("*.pdf"))
    default_idx = pdfs.index("NovaCloud_Q2_2025.pdf") if "NovaCloud_Q2_2025.pdf" in pdfs else 0
    choice = st.selectbox("Report", pdfs, index=default_idx)
    uploaded = st.file_uploader("...or upload a PDF", type="pdf")
    if st.button("Extract"):
        load_dotenv()
        if not (os.environ.get("LLM_BASE_URL") and os.environ.get("LLM_API_KEY")):
            st.info(
                "Configure .env with an LLM key (LLM_BASE_URL, LLM_API_KEY) to run live. "
                "The prebuilt results above are unaffected."
            )
        else:
            import tempfile

            from portfolio_extract.pipeline import extract_pdf

            if uploaded is not None:
                # Keep the original filename: company identity is parsed from it, and the file
                # must stay on disk so "Verify in source" can render its page later this session.
                if "upload_dir" not in st.session_state:
                    st.session_state.upload_dir = tempfile.mkdtemp(prefix="pfx_uploads_")
                target = os.path.join(st.session_state.upload_dir, uploaded.name)
                with open(target, "wb") as f:
                    f.write(uploaded.getvalue())
            else:
                target = f"data/{choice}"
            with st.spinner("Extracting (live LLM call)..."):
                try:
                    de = extract_pdf(target)
                except Exception as e:
                    st.error(
                        f"Live extraction failed ({type(e).__name__}: {e}). "
                        "The prebuilt results above are unaffected."
                    )
                    de = None
            if de is not None:
                new_keys = {_cell_key(r) for r in de.records}
                st.session_state.live_records = [
                    r for r in st.session_state.live_records
                    if _cell_key(r) not in new_keys
                ] + list(de.records)
                st.session_state.live_companies[de.company.canonical_name] = de.company
                if uploaded is not None:
                    st.session_state.setdefault("live_pdf_paths", {})[uploaded.name] = target
                st.session_state.last_extract = {
                    "company": de.company.canonical_name,
                    "sector": de.company.sector.value,
                    "n_present": sum(1 for r in de.records
                                     if r.value is not None and not r.restated),
                    "rows": [
                        {
                            "metric": r.metric.value,
                            "value": r.value,
                            "label": r.label_as_reported,
                            "page": r.source_page,
                            "confidence": r.confidence_tier.value if r.confidence_tier else None,
                            "status": r.absence_reason.value,
                        }
                        for r in de.records
                        if not r.restated
                    ],
                    "review": [i.kind for i in de.review],
                }
                st.rerun()

    last_extract = st.session_state.get("last_extract")
    if last_extract:
        st.success(
            f"Joined the matrix above: {last_extract['company']} "
            f"({last_extract['sector']}), {last_extract['n_present']} metric values. "
            "Source-verified (Layer 1); ground-truth unverified (Layer 2)."
        )
        st.dataframe(pd.DataFrame(last_extract["rows"]), use_container_width=True)
        if last_extract["review"]:
            st.caption("Review-queue items: " + "; ".join(last_extract["review"]))
except Exception as e:
    st.warning(
        f"Live-extraction panel unavailable ({type(e).__name__}). "
        "The rest of the dashboard is unaffected."
    )
