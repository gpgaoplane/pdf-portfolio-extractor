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

def test_unrecognized_currency_is_flagged_not_silent():
    out = LLMExtraction(company_name="X", sector="SaaS", period_year=2025,
        period_quarter="Q2", currency="BTC", metrics=[
            LLMMetric(metric="headcount", raw_text="142", label_as_reported="Headcount",
                      source_page=1, source_snippet="Headcount 142")])
    rec = build_records_from_llm(out, source_file="X_Q2_2025.pdf")[0]
    assert rec.currency == Currency.USD            # still defaults so the record is usable
    assert rec.notes and "BTC" in rec.notes        # but the problem is surfaced

def test_llm_extraction_predecessor_fields_default_none():
    out = LLMExtraction(company_name="X", sector="SaaS", period_year=2025,
                        period_quarter="Q2", currency="USD", metrics=[])
    assert out.predecessor_name is None and out.predecessor_effective_date is None

def test_llm_extraction_accepts_predecessor():
    out = LLMExtraction(company_name="Apex Freight Solutions Inc.", sector="Marketplace",
        period_year=2025, period_quarter="Q2", currency="USD",
        predecessor_name="FleetLink Logistics Network", predecessor_effective_date="2025-04-01",
        metrics=[])
    assert out.predecessor_name == "FleetLink Logistics Network"
    assert out.predecessor_effective_date == "2025-04-01"

def test_recognized_currency_sets_no_flag():
    out = LLMExtraction(company_name="X", sector="SaaS", period_year=2025,
        period_quarter="Q2", currency="GBP", metrics=[
            LLMMetric(metric="headcount", raw_text="142", label_as_reported="Headcount",
                      source_page=1, source_snippet="Headcount 142")])
    rec = build_records_from_llm(out, source_file="X_Q2_2025.pdf")[0]
    assert rec.currency == Currency.GBP and not rec.notes

def test_net_burn_stored_as_positive_magnitude():
    out = LLMExtraction(company_name="X", sector="SaaS", period_year=2025, period_quarter="Q2",
        currency="USD", metrics=[LLMMetric(metric="net_burn_monthly", raw_text="($0.75M)",
            label_as_reported="Monthly Net Burn", source_page=1, source_snippet="Monthly Net Burn ($0.75M)")])
    rec = build_records_from_llm(out, source_file="X.pdf")[0]
    assert rec.value == 0.75   # magnitude, not -0.75

def test_revenue_components_nested_on_total():
    from portfolio_extract.models import Component
    out = LLMExtraction(company_name="ApexFreight", sector="Marketplace", period_year=2025,
        period_quarter="Q2", currency="USD",
        revenue_components=[Component(label="transaction", value=8.6, raw_text="8.6M"),
                            Component(label="SaaS tool fee", value=0.7, raw_text="0.7M")],
        metrics=[LLMMetric(metric="revenue_quarterly", raw_text="9.3M",
            label_as_reported="Total Recognized Revenue", source_page=1, source_snippet="Total Recognized Revenue 9.3M")])
    rec = build_records_from_llm(out, source_file="ApexFreight_Q2_2025.pdf")[0]
    assert rec.value == 9.3 and len(rec.components) == 2 and rec.components[0].value == 8.6

def test_build_restatement_records_keyed_to_prior_period():
    from portfolio_extract.models import Restatement
    from portfolio_extract.extract_llm import build_restatement_records
    out = LLMExtraction(company_name="PeopleFlow HR Systems Ltd.", sector="SaaS", period_year=2025,
        period_quarter="Q2", currency="GBP",
        restatements=[Restatement(metric="revenue_quarterly", period_year=2025, period_quarter="Q1",
                                  raw_text="4.6M", note="restated from 4.7M")],
        metrics=[])
    recs = build_restatement_records(out, source_file="PeopleFlow_Q2_2025.pdf")
    assert len(recs) == 1
    r = recs[0]
    assert r.period_quarter == "Q1" and r.value == 4.6 and r.restated is True
    assert r.confidence_tier is None and r.currency.value == "GBP"
    assert r.source_file == "PeopleFlow_Q2_2025.pdf"

@pytest.mark.parametrize("raw, expected, recognized", [
    ("USD", Currency.USD, True), ("usd", Currency.USD, True),
    ("GBP ", Currency.GBP, True), (" gbp", Currency.GBP, True),
    ("£", Currency.GBP, True), ("$", Currency.USD, True), ("US$", Currency.USD, True),
    ("€", Currency.EUR, True), ("EUR", Currency.EUR, True),
    ("BTC", Currency.USD, False), ("", Currency.USD, False), (None, Currency.USD, False),
])
def test_coerce_currency(raw, expected, recognized):
    cur, ok = _coerce_currency(raw)
    assert cur == expected and ok == recognized
