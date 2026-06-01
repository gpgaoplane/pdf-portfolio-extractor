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

def test_comparison_frame_long_format():
    from portfolio_extract.view import comparison_frame
    from portfolio_extract.models import (ExtractionRecord, MetricName, CanonicalUnit, Currency,
        ExtractionMethod, AbsenceReason, PeriodBasis)
    recs = [ExtractionRecord(company="NovaCloud", period_year=2025, period_quarter="Q2",
        metric=MetricName.GROSS_MARGIN, value=78.0, canonical_unit=CanonicalUnit.PERCENT, currency=Currency.USD,
        basis="saas_cogs", raw_text="78%", label_as_reported="Gross Margin", source_file="NovaCloud_Q2_2025.pdf",
        source_page=1, source_snippet="x", extraction_method=ExtractionMethod.TABLE_CELL,
        absence_reason=AbsenceReason.PRESENT, period_basis=PeriodBasis.RATIO_LTM)]
    df = comparison_frame(recs)
    assert list(df["company"]) == ["NovaCloud"]
    assert df.iloc[0]["basis"] == "saas_cogs" and df.iloc[0]["metric"] == "gross_margin"

def test_reconcile_prefers_restated_keeps_original():
    from portfolio_extract.view import comparison_frame
    from portfolio_extract.models import (ExtractionRecord, MetricName, CanonicalUnit, Currency,
        ExtractionMethod, AbsenceReason, PeriodBasis)
    def rev(value, restated, src):
        return ExtractionRecord(company="PeopleFlow", period_year=2025, period_quarter="Q1",
            metric=MetricName.REVENUE_QUARTERLY, value=value, canonical_unit=CanonicalUnit.USD_MILLIONS,
            currency=Currency.GBP, raw_text=f"{value}M", label_as_reported="Quarterly Revenue",
            source_file=src, source_page=1, source_snippet="x", extraction_method=ExtractionMethod.LLM_PROSE,
            absence_reason=AbsenceReason.PRESENT, period_basis=PeriodBasis.FLOW_QUARTERLY, restated=restated)
    df = comparison_frame([rev(4.7, False, "PeopleFlow_Q1_2025.pdf"), rev(4.6, True, "PeopleFlow_Q2_2025.pdf")])
    row = df[(df["company"] == "PeopleFlow") & (df["metric"] == "revenue_quarterly")]
    assert len(row) == 1
    assert row.iloc[0]["value"] == 4.6 and row.iloc[0]["original_value"] == 4.7
    assert row.iloc[0]["origin"] == "restated"

def test_metric_matrix_gates_lending_gm_separately():
    from portfolio_extract.view import comparison_frame, metric_matrix
    from portfolio_extract.models import (ExtractionRecord, MetricName, CanonicalUnit, Currency,
        ExtractionMethod, AbsenceReason, PeriodBasis)
    def gm(company, basis):
        return ExtractionRecord(company=company, period_year=2025, period_quarter="Q2",
            metric=MetricName.GROSS_MARGIN, value=60.0, canonical_unit=CanonicalUnit.PERCENT, currency=Currency.USD,
            basis=basis, raw_text="60%", label_as_reported="Gross Margin", source_file=f"{company}_Q2_2025.pdf",
            source_page=1, source_snippet="x", extraction_method=ExtractionMethod.TABLE_CELL,
            absence_reason=AbsenceReason.PRESENT, period_basis=PeriodBasis.RATIO_LTM)
    df = comparison_frame([gm("NovaCloud", "saas_cogs"), gm("LendBridge", "net_interest_spread")])
    groups = metric_matrix(df, MetricName.GROSS_MARGIN)
    assert set(groups) == {"saas_marketplace", "lending"}
    assert "LendBridge" in groups["lending"].index and "NovaCloud" in groups["saas_marketplace"].index

def test_time_series_stitches_predecessor():
    from portfolio_extract.view import comparison_frame, time_series
    from portfolio_extract.registry import CompanyRecord, Predecessor
    from portfolio_extract.models import (ExtractionRecord, MetricName, CanonicalUnit, Currency,
        ExtractionMethod, AbsenceReason, PeriodBasis, Sector)
    def rev(company, year, q, v):
        return ExtractionRecord(company=company, period_year=year, period_quarter=q,
            metric=MetricName.REVENUE_QUARTERLY, value=v, canonical_unit=CanonicalUnit.USD_MILLIONS,
            currency=Currency.USD, raw_text=f"{v}M", label_as_reported="Revenue", source_file="x.pdf",
            source_page=1, source_snippet="x", extraction_method=ExtractionMethod.LLM_PROSE,
            absence_reason=AbsenceReason.PRESENT, period_basis=PeriodBasis.FLOW_QUARTERLY)
    df = comparison_frame([rev("FleetLink", 2025, "Q1", 8.9), rev("ApexFreight", 2025, "Q2", 9.3)])
    companies = {"ApexFreight": CompanyRecord(canonical_name="ApexFreight", sector=Sector.HYBRID,
                                              predecessor=Predecessor(name="FleetLink"))}
    ts = time_series(df, "ApexFreight", MetricName.REVENUE_QUARTERLY, companies=companies, include_predecessor=True)
    assert set(ts["company"]) == {"ApexFreight", "FleetLink"}
    ts_solo = time_series(df, "ApexFreight", MetricName.REVENUE_QUARTERLY, companies=companies, include_predecessor=False)
    assert set(ts_solo["company"]) == {"ApexFreight"}
