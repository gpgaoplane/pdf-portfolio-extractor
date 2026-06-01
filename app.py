import streamlit as st
from portfolio_extract.models import MetricName
from portfolio_extract.repository import load_records_jsonl
from portfolio_extract.view import comparison_frame, overview_table, citation_for

st.set_page_config(page_title="Portfolio Metrics Explorer", layout="wide")


@st.cache_data
def _load():
    return load_records_jsonl("eval/demo_records.jsonl")


records = _load()
frame = comparison_frame(records)

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
