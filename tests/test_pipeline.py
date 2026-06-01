from portfolio_extract.pipeline import extract_pdf, DocumentExtraction
from portfolio_extract.extract_llm import LLMExtraction, LLMMetric
from portfolio_extract.models import MetricName, ConfidenceTier, Sector

def test_pipeline_assembles_records(monkeypatch, data_dir):
    fake = LLMExtraction(company_name="NovaCloud Analytics Inc.", sector="SaaS", period_year=2025,
        period_quarter="Q2", currency="USD", metrics=[
            LLMMetric(metric="gross_margin", raw_text="78%", label_as_reported="Gross Margin",
                      source_page=1, source_snippet="Gross Margin 78%")])
    monkeypatch.setattr("portfolio_extract.pipeline.extract_with_llm", lambda texts: fake)
    de = extract_pdf(data_dir / "NovaCloud_Q2_2025.pdf")
    assert isinstance(de, DocumentExtraction)
    assert de.company.canonical_name == "NovaCloud" and de.company.sector == Sector.SAAS
    gm = next(r for r in de.records if r.metric == MetricName.GROSS_MARGIN)
    assert gm.value == 78.0
    assert gm.company == "NovaCloud"
    assert gm.confidence_tier in {ConfidenceTier.HIGH, ConfidenceTier.MEDIUM}

from portfolio_extract.models import AbsenceReason

def test_pipeline_materializes_absence_and_basis(monkeypatch, data_dir):
    fake = LLMExtraction(company_name="LendBridge Capital Corp.", sector="Lending", period_year=2025,
        period_quarter="Q1", currency="USD", metrics=[
            LLMMetric(metric="gross_margin", raw_text="61%", label_as_reported="Gross Margin",
                      source_page=1, source_snippet="Gross Margin 61%")])
    monkeypatch.setattr("portfolio_extract.pipeline.extract_with_llm", lambda texts: fake)
    de = extract_pdf(data_dir / "LendBridge_Q1_2025.pdf")
    by = {r.metric: r for r in de.records}
    gm = by[MetricName.GROSS_MARGIN]
    assert gm.basis == "net_interest_spread" and gm.absence_reason == AbsenceReason.PRESENT
    assert by[MetricName.ARR].absence_reason == AbsenceReason.NOT_APPLICABLE   # lending gates ARR
    assert by[MetricName.ARR].confidence_tier is None                         # not low-confidence
    assert by[MetricName.CASH_BALANCE].absence_reason == AbsenceReason.NULL_IN_SOURCE

from types import SimpleNamespace
from portfolio_extract.pipeline import _match_level
from portfolio_extract.confidence import MatchLevel

def test_match_level_absent_when_value_is_none():
    # a metric the LLM returned but whose raw_text isn't numeric -> value None
    r = SimpleNamespace(value=None, raw_text="N/A", source_snippet="Headcount N/A")
    assert _match_level(r, None, "Headcount N/A") == MatchLevel.ABSENT

def test_pipeline_appends_restatement_record(monkeypatch, data_dir):
    from portfolio_extract.models import Restatement
    fake = LLMExtraction(company_name="PeopleFlow HR Systems Ltd.", sector="SaaS", period_year=2025,
        period_quarter="Q2", currency="GBP",
        restatements=[Restatement(metric="revenue_quarterly", period_year=2025, period_quarter="Q1", raw_text="4.6M")],
        metrics=[LLMMetric(metric="revenue_quarterly", raw_text="5.1M", label_as_reported="Quarterly Revenue",
                           source_page=1, source_snippet="Quarterly Revenue 5.1M")])
    monkeypatch.setattr("portfolio_extract.pipeline.extract_with_llm", lambda texts: fake)
    de = extract_pdf(data_dir / "PeopleFlow_Q2_2025.pdf")
    restated = [r for r in de.records if r.restated]
    assert len(restated) == 1
    assert restated[0].period_quarter == "Q1" and restated[0].value == 4.6
    assert restated[0].basis == "saas_recognized"
    cur = [r for r in de.records if r.metric.value == "revenue_quarterly" and not r.restated and r.period_quarter == "Q2"]
    assert len(cur) == 1

def test_pipeline_present_record_has_real_confidence_score(monkeypatch, data_dir):
    fake = LLMExtraction(company_name="NovaCloud Analytics Inc.", sector="SaaS", period_year=2025,
        period_quarter="Q2", currency="USD", metrics=[
            LLMMetric(metric="gross_margin", raw_text="78%", label_as_reported="Gross Margin",
                      source_page=1, source_snippet="Gross Margin 78%")])
    monkeypatch.setattr("portfolio_extract.pipeline.extract_with_llm", lambda texts: fake)
    de = extract_pdf(data_dir / "NovaCloud_Q2_2025.pdf")
    gm = next(r for r in de.records if r.metric == MetricName.GROSS_MARGIN)
    assert gm.confidence_score is not None and gm.confidence_score > 0.6
