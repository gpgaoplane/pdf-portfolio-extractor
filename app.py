import streamlit as st
from portfolio_extract.repository import load_records_jsonl
from portfolio_extract.view import comparison_frame, overview_table

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
