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

def test_build_records_uses_per_page_hint():
    # Bare "8400" on page 2, where page 2 is "in thousands" -> 8.4 (millions).
    out = LLMExtraction(company_name="X", sector="SaaS", period_year=2025,
        period_quarter="Q2", currency="USD", metrics=[
            LLMMetric(metric="revenue_quarterly", raw_text="8400",
                      label_as_reported="Revenue", source_page=2, source_snippet="Revenue 8400")])
    recs = build_records_from_llm(out, source_file="X_Q2_2025.pdf",
                                  hint_by_page={1: None, 2: "in thousands"})
    assert recs[0].value == 8.4

import pytest
from portfolio_extract.extract_llm import _coerce_currency
from portfolio_extract.models import Currency

@pytest.mark.parametrize("raw, expected", [
    ("USD", Currency.USD),
    ("usd", Currency.USD),
    ("GBP ", Currency.GBP),      # trailing space
    (" gbp", Currency.GBP),
    ("£", Currency.GBP),
    ("$", Currency.USD),
    ("US$", Currency.USD),
    ("€", Currency.EUR),
    ("EUR", Currency.EUR),
    ("BTC", Currency.USD),        # unknown -> default USD
    ("", Currency.USD),
    (None, Currency.USD),
])
def test_coerce_currency(raw, expected):
    assert _coerce_currency(raw) == expected
