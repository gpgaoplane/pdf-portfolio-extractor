from portfolio_extract.extract_llm import build_records_from_llm, LLMExtraction, LLMMetric
from portfolio_extract.models import MetricName

def test_build_records_maps_universal_core():
    out = LLMExtraction(company_name="NovaCloud Analytics Inc.", sector="SaaS",
        period_year=2025, period_quarter="Q2", currency="USD", metrics=[
            LLMMetric(metric="revenue_quarterly", raw_text="$8.4M",
                      label_as_reported="Recognized Revenue", source_page=1, source_snippet="Recognized Revenue $8.4M"),
            LLMMetric(metric="gross_margin", raw_text="78%", label_as_reported="Gross Margin",
                      source_page=1, source_snippet="Gross Margin 78%"),
            LLMMetric(metric="headcount", raw_text="142", label_as_reported="FTE",
                      source_page=1, source_snippet="FTE 142")])
    by = {r.metric: r for r in build_records_from_llm(out, source_file="NovaCloud_Q2_2025.pdf")}
    assert by[MetricName.REVENUE_QUARTERLY].value == 8.4
    assert by[MetricName.GROSS_MARGIN].value == 78.0
    assert by[MetricName.HEADCOUNT].value == 142.0
    assert by[MetricName.HEADCOUNT].label_as_reported == "FTE"
