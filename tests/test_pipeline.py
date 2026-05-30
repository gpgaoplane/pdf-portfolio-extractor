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

from types import SimpleNamespace
from portfolio_extract.pipeline import _match_level
from portfolio_extract.confidence import MatchLevel

def test_match_level_absent_when_value_is_none():
    # a metric the LLM returned but whose raw_text isn't numeric -> value None
    r = SimpleNamespace(value=None, raw_text="N/A", source_snippet="Headcount N/A")
    assert _match_level(r, None, "Headcount N/A") == MatchLevel.ABSENT
