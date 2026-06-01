from portfolio_extract.models import (
    ExtractionRecord, MetricName, CanonicalUnit, Currency,
    ExtractionMethod, ConfidenceTier, AbsenceReason, PeriodBasis)

def test_record_roundtrips():
    r = ExtractionRecord(company="NovaCloud", period_year=2025, period_quarter="Q2",
        metric=MetricName.REVENUE_QUARTERLY, value=8.4, canonical_unit=CanonicalUnit.USD_MILLIONS,
        currency=Currency.USD, raw_text="$8.4M", label_as_reported="Recognized Revenue",
        source_file="NovaCloud_Q2_2025.pdf", source_page=1, source_snippet="Recognized Revenue $8.4M",
        extraction_method=ExtractionMethod.TABLE_CELL, confidence_tier=ConfidenceTier.HIGH,
        confidence_score=0.95, absence_reason=AbsenceReason.PRESENT, period_basis=PeriodBasis.FLOW_QUARTERLY)
    assert r.value == 8.4 and r.model_dump()["metric"] == "revenue_quarterly"

def test_absent_value_allowed_null():
    r = ExtractionRecord(company="LendBridge", period_year=2025, period_quarter="Q2",
        metric=MetricName.ARR, value=None, canonical_unit=CanonicalUnit.USD_MILLIONS,
        currency=Currency.USD, raw_text="", label_as_reported="", source_file="x.pdf",
        source_page=1, source_snippet="", extraction_method=ExtractionMethod.LLM_PROSE,
        confidence_tier=ConfidenceTier.LOW, confidence_score=0.2,
        absence_reason=AbsenceReason.NOT_APPLICABLE, period_basis=PeriodBasis.POINT_IN_TIME_EOP)
    assert r.value is None and r.absence_reason == AbsenceReason.NOT_APPLICABLE

def test_component_and_optional_confidence():
    from portfolio_extract.models import ExtractionRecord, Component, MetricName, CanonicalUnit, AbsenceReason, ExtractionMethod, PeriodBasis
    r = ExtractionRecord(company="X", period_year=2025, period_quarter="Q2",
        metric=MetricName.REVENUE_QUARTERLY, value=9.3, canonical_unit=CanonicalUnit.USD_MILLIONS,
        raw_text="9.3M", label_as_reported="Total Recognized Revenue", source_file="f.pdf",
        source_page=1, source_snippet="x", extraction_method=ExtractionMethod.LLM_PROSE,
        absence_reason=AbsenceReason.PRESENT, period_basis=PeriodBasis.FLOW_QUARTERLY,
        components=[Component(label="transaction", value=8.6, raw_text="8.6M"),
                    Component(label="SaaS tool fee", value=0.7, raw_text="0.7M")])
    assert r.confidence_tier is None and r.confidence_score is None
    assert r.components[0].value == 8.6

def test_restatement_model_and_restated_flag():
    from portfolio_extract.models import Restatement, ExtractionRecord, MetricName, CanonicalUnit, AbsenceReason, ExtractionMethod, PeriodBasis
    rs = Restatement(metric="revenue_quarterly", period_year=2025, period_quarter="Q1", raw_text="4.6M")
    assert rs.period_quarter == "Q1" and rs.note is None
    r = ExtractionRecord(company="PeopleFlow", period_year=2025, period_quarter="Q1",
        metric=MetricName.REVENUE_QUARTERLY, value=4.6, canonical_unit=CanonicalUnit.USD_MILLIONS,
        raw_text="4.6M", label_as_reported="restatement", source_file="PeopleFlow_Q2_2025.pdf",
        source_page=0, source_snippet="", extraction_method=ExtractionMethod.LLM_RECONCILED,
        absence_reason=AbsenceReason.PRESENT, period_basis=PeriodBasis.FLOW_QUARTERLY, restated=True)
    assert r.restated is True
