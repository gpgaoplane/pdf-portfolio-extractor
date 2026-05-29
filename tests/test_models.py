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
