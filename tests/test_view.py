from portfolio_extract.models import (ExtractionRecord, MetricName, CanonicalUnit, Currency,
    ExtractionMethod, ConfidenceTier, AbsenceReason, PeriodBasis)
from portfolio_extract.view import company_period_matrix

def _r(company, value):
    return ExtractionRecord(company=company, period_year=2025, period_quarter="Q2",
        metric=MetricName.REVENUE_QUARTERLY, value=value, canonical_unit=CanonicalUnit.USD_MILLIONS,
        currency=Currency.USD, raw_text="x", label_as_reported="x", source_file="f.pdf",
        source_page=1, source_snippet="x", extraction_method=ExtractionMethod.TABLE_CELL,
        confidence_tier=ConfidenceTier.HIGH, confidence_score=0.95,
        absence_reason=AbsenceReason.PRESENT, period_basis=PeriodBasis.FLOW_QUARTERLY)

def test_matrix_groups_by_company_period():
    m = company_period_matrix([_r("NovaCloud", 8.4), _r("MediSight", 6.8)], MetricName.REVENUE_QUARTERLY)
    assert m[("NovaCloud", 2025, "Q2")] == 8.4 and m[("MediSight", 2025, "Q2")] == 6.8
