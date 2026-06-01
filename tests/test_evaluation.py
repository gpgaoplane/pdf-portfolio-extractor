from portfolio_extract.evaluation import score
from portfolio_extract.models import (ExtractionRecord, MetricName as M, CanonicalUnit, Currency,
    ExtractionMethod, ConfidenceTier, AbsenceReason, PeriodBasis)

def _rec(company, q, metric, value, unit, reason=AbsenceReason.PRESENT, method=ExtractionMethod.TABLE_CELL,
         tier=ConfidenceTier.HIGH, restated=False):
    return ExtractionRecord(company=company, period_year=2025, period_quarter=q, metric=metric, value=value,
        canonical_unit=unit, currency=Currency.USD, raw_text="x", label_as_reported="x", source_file="f.pdf",
        source_page=1, source_snippet="x", extraction_method=method, confidence_tier=tier,
        confidence_score=0.95 if tier else None, absence_reason=reason, period_basis=PeriodBasis.RATIO_LTM,
        restated=restated)

LABELS = {"NovaCloud_Q2_2025": {"company": "NovaCloud", "sector": "SaaS", "period": {"year": 2025, "quarter": "Q2"},
    "metrics": {
        "gross_margin": {"value": 78.0, "status": "present"},
        "headcount": {"value": 142, "status": "present"},
        "arr": {"value": 34.2, "status": "present"},
        "ebitda": {"status": "null_in_source"}}}}

def test_score_counts_correct_omission_hallucination():
    records = [
        _rec("NovaCloud", "Q2", M.GROSS_MARGIN, 78.0, CanonicalUnit.PERCENT),
        _rec("NovaCloud", "Q2", M.HEADCOUNT, 143, CanonicalUnit.COUNT),
        _rec("NovaCloud", "Q2", M.EBITDA, 5.0, CanonicalUnit.USD_MILLIONS),
    ]
    r = score(records, LABELS)
    assert r["per_metric"]["gross_margin"] == [1, 1]
    assert r["per_metric"]["headcount"] == [0, 1]
    assert r["omissions"] == 1
    assert r["hallucinations"] == 1

def test_score_ignores_restated_records():
    records = [_rec("NovaCloud", "Q2", M.GROSS_MARGIN, 99.0, CanonicalUnit.PERCENT, restated=True),
               _rec("NovaCloud", "Q2", M.GROSS_MARGIN, 78.0, CanonicalUnit.PERCENT)]
    r = score(records, {"x": {"company": "NovaCloud", "sector": "SaaS", "period": {"year": 2025, "quarter": "Q2"},
                              "metrics": {"gross_margin": {"value": 78.0, "status": "present"}}}})
    assert r["per_metric"]["gross_margin"] == [1, 1]

def test_verification_ablation_separates_verified():
    from portfolio_extract.evaluation import verification_ablation
    records = [
        _rec("NovaCloud", "Q2", M.GROSS_MARGIN, 78.0, CanonicalUnit.PERCENT, method=ExtractionMethod.TABLE_CELL),
        _rec("NovaCloud", "Q2", M.ARR, 99.0, CanonicalUnit.USD_MILLIONS, method=ExtractionMethod.LLM_PROSE),
    ]
    labels = {"x": {"company": "NovaCloud", "sector": "SaaS", "period": {"year": 2025, "quarter": "Q2"},
        "metrics": {"gross_margin": {"value": 78.0, "status": "present"}, "arr": {"value": 34.2, "status": "present"}}}}
    m = verification_ablation(records, labels)
    assert m["verified"] == [1, 0] and m["unverified"] == [0, 1]

def test_confidence_calibration_per_tier():
    from portfolio_extract.evaluation import confidence_calibration
    records = [_rec("NovaCloud", "Q2", M.GROSS_MARGIN, 78.0, CanonicalUnit.PERCENT, tier=ConfidenceTier.HIGH)]
    labels = {"x": {"company": "NovaCloud", "sector": "SaaS", "period": {"year": 2025, "quarter": "Q2"},
        "metrics": {"gross_margin": {"value": 78.0, "status": "present"}}}}
    c = confidence_calibration(records, labels)
    assert c["HIGH"] == [1, 0]

def test_time_series_flags_big_jump():
    from portfolio_extract.evaluation import time_series_flags
    records = [_rec("NovaCloud", "Q1", M.ARR, 3.4, CanonicalUnit.USD_MILLIONS),
               _rec("NovaCloud", "Q2", M.ARR, 34.0, CanonicalUnit.USD_MILLIONS)]
    flags = time_series_flags(records)
    assert any(f[0] == "NovaCloud" and f[1] == "arr" for f in flags)
