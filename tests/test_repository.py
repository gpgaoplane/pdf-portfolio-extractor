from portfolio_extract.models import (ExtractionRecord, MetricName, CanonicalUnit, Currency,
    ExtractionMethod, ConfidenceTier, AbsenceReason, PeriodBasis)
from portfolio_extract.repository import SqliteRepository

def _rec(value):
    return ExtractionRecord(company="NovaCloud", period_year=2025, period_quarter="Q2",
        metric=MetricName.REVENUE_QUARTERLY, value=value, canonical_unit=CanonicalUnit.USD_MILLIONS,
        currency=Currency.USD, raw_text="$8.4M", label_as_reported="Recognized Revenue",
        source_file="NovaCloud_Q2_2025.pdf", source_page=1, source_snippet="...",
        extraction_method=ExtractionMethod.TABLE_CELL, confidence_tier=ConfidenceTier.HIGH,
        confidence_score=0.95, absence_reason=AbsenceReason.PRESENT, period_basis=PeriodBasis.FLOW_QUARTERLY)

def test_save_and_query_roundtrip(tmp_path):
    repo = SqliteRepository(tmp_path / "t.db"); repo.init_schema()
    repo.save_many([_rec(8.4)])
    rows = repo.query(company="NovaCloud")
    assert len(rows) == 1 and rows[0].value == 8.4
