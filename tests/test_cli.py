from portfolio_extract.cli import run

def test_cli_persists(tmp_path, monkeypatch, data_dir):
    from portfolio_extract.models import (ExtractionRecord, MetricName, CanonicalUnit, Currency,
        ExtractionMethod, ConfidenceTier, AbsenceReason, PeriodBasis)
    rec = ExtractionRecord(company="NovaCloud", period_year=2025, period_quarter="Q2",
        metric=MetricName.REVENUE_QUARTERLY, value=8.4, canonical_unit=CanonicalUnit.USD_MILLIONS,
        currency=Currency.USD, raw_text="$8.4M", label_as_reported="Recognized Revenue",
        source_file="NovaCloud_Q2_2025.pdf", source_page=1, source_snippet="x",
        extraction_method=ExtractionMethod.TABLE_CELL, confidence_tier=ConfidenceTier.HIGH,
        confidence_score=0.95, absence_reason=AbsenceReason.PRESENT, period_basis=PeriodBasis.FLOW_QUARTERLY)
    monkeypatch.setattr("portfolio_extract.cli.extract_pdf", lambda p: [rec])
    db = tmp_path / "out.db"
    assert run([str(data_dir / "NovaCloud_Q2_2025.pdf")], db_path=db) == 1 and db.exists()
