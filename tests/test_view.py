from portfolio_extract.models import (ExtractionRecord, MetricName, CanonicalUnit, Currency,
    ExtractionMethod, ConfidenceTier, AbsenceReason, PeriodBasis)
def _r(company, value):
    return ExtractionRecord(company=company, period_year=2025, period_quarter="Q2",
        metric=MetricName.REVENUE_QUARTERLY, value=value, canonical_unit=CanonicalUnit.USD_MILLIONS,
        currency=Currency.USD, raw_text="x", label_as_reported="x", source_file="f.pdf",
        source_page=1, source_snippet="x", extraction_method=ExtractionMethod.TABLE_CELL,
        confidence_tier=ConfidenceTier.HIGH, confidence_score=0.95,
        absence_reason=AbsenceReason.PRESENT, period_basis=PeriodBasis.FLOW_QUARTERLY)

def test_metric_matrix_revenue_single_block():
    from portfolio_extract.view import comparison_frame, metric_matrix
    df = comparison_frame([_r("NovaCloud", 8.4), _r("LendBridge", 12.1)])
    groups = metric_matrix(df, MetricName.REVENUE_QUARTERLY)
    assert set(groups) == {"all"}            # revenue is comparable top-line, not basis-gated
    assert {"NovaCloud", "LendBridge"} <= set(groups["all"].index)

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

def test_overview_table_formats_cells():
    from portfolio_extract.view import comparison_frame, overview_table
    from portfolio_extract.models import (ExtractionRecord, MetricName, CanonicalUnit, Currency,
        ExtractionMethod, AbsenceReason, PeriodBasis)
    def r(metric, value, unit, reason, cur=Currency.USD):
        return ExtractionRecord(company="NovaCloud", period_year=2025, period_quarter="Q2", metric=metric,
            value=value, canonical_unit=unit, currency=cur, raw_text="x", label_as_reported="x",
            source_file="f.pdf", source_page=1, source_snippet="x", extraction_method=ExtractionMethod.TABLE_CELL,
            absence_reason=reason, period_basis=PeriodBasis.RATIO_LTM)
    recs = [
        r(MetricName.GROSS_MARGIN, 78.0, CanonicalUnit.PERCENT, AbsenceReason.PRESENT),
        r(MetricName.ARR, None, CanonicalUnit.USD_MILLIONS, AbsenceReason.NOT_APPLICABLE),
        r(MetricName.CASH_BALANCE, None, CanonicalUnit.USD_MILLIONS, AbsenceReason.NULL_IN_SOURCE),
        r(MetricName.HEADCOUNT, 142, CanonicalUnit.COUNT, AbsenceReason.PRESENT),
    ]
    tbl = overview_table(comparison_frame(recs))   # pandas DataFrame indexed by company
    row = tbl.loc["NovaCloud"]
    assert row["gross_margin"] == "78%"
    assert row["arr"] == "n/a"            # not_applicable
    assert row["cash_balance"] == "—"   # em dash for null/missing
    assert row["headcount"] == "142"

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

def test_saas_comparison_filters_by_sector():
    from portfolio_extract.view import comparison_frame, saas_comparison
    from portfolio_extract.registry import CompanyRecord
    from portfolio_extract.models import (ExtractionRecord, MetricName, CanonicalUnit, Currency,
        ExtractionMethod, AbsenceReason, PeriodBasis, Sector)
    def r(company, metric, value):
        unit = CanonicalUnit.USD_MILLIONS if metric == MetricName.ARR else CanonicalUnit.PERCENT
        return ExtractionRecord(company=company, period_year=2025, period_quarter="Q2", metric=metric, value=value,
            canonical_unit=unit, currency=Currency.USD, raw_text="x", label_as_reported="x", source_file="f.pdf",
            source_page=1, source_snippet="x", extraction_method=ExtractionMethod.TABLE_CELL,
            absence_reason=AbsenceReason.PRESENT, period_basis=PeriodBasis.POINT_IN_TIME_EOP)
    frame = comparison_frame([r("NovaCloud", MetricName.ARR, 34.2), r("NovaCloud", MetricName.NET_REVENUE_RETENTION, 123.0),
                              r("LendBridge", MetricName.ARR, 99.0)])  # LendBridge is Lending; must be excluded
    companies = {"NovaCloud": CompanyRecord(canonical_name="NovaCloud", sector=Sector.SAAS),
                 "LendBridge": CompanyRecord(canonical_name="LendBridge", sector=Sector.LENDING)}
    out = saas_comparison(frame, companies)   # pandas DataFrame indexed by company, columns arr/net_revenue_retention
    assert "NovaCloud" in out.index and "LendBridge" not in out.index
    assert out.loc["NovaCloud", "arr"] == 34.2 and out.loc["NovaCloud", "net_revenue_retention"] == 123.0

def test_citation_for_returns_provenance():
    from portfolio_extract.view import citation_for
    from portfolio_extract.models import (ExtractionRecord, MetricName, CanonicalUnit, Currency,
        ExtractionMethod, ConfidenceTier, AbsenceReason, PeriodBasis)
    rec = ExtractionRecord(company="NovaCloud", period_year=2025, period_quarter="Q2",
        metric=MetricName.GROSS_MARGIN, value=78.0, canonical_unit=CanonicalUnit.PERCENT, currency=Currency.USD,
        basis="saas_cogs", raw_text="78%", label_as_reported="Gross Margin", source_file="NovaCloud_Q2_2025.pdf",
        source_page=1, source_snippet="Gross Margin 78%", extraction_method=ExtractionMethod.TABLE_CELL,
        confidence_tier=ConfidenceTier.HIGH, confidence_score=1.0, absence_reason=AbsenceReason.PRESENT,
        period_basis=PeriodBasis.RATIO_LTM, bbox=(40.0, 80.0, 300.0, 100.0))
    c = citation_for([rec], "NovaCloud", (2025, "Q2"), MetricName.GROSS_MARGIN)
    assert c is not None
    assert c["source_file"] == "NovaCloud_Q2_2025.pdf" and c["source_page"] == 1
    assert c["label_as_reported"] == "Gross Margin" and c["snippet"] == "Gross Margin 78%"
    assert c["confidence"] == "HIGH" and c["basis"] == "saas_cogs" and c["value"] == 78.0
    assert "bbox" in c and c["bbox"] == (40.0, 80.0, 300.0, 100.0)

def test_citation_for_missing_returns_none():
    from portfolio_extract.view import citation_for
    from portfolio_extract.models import MetricName
    assert citation_for([], "X", (2025, "Q2"), MetricName.ARR) is None

def test_citation_for_restated_supersedes_keeps_original():
    from portfolio_extract.view import citation_for
    from portfolio_extract.models import (ExtractionRecord, MetricName, CanonicalUnit, Currency,
        ExtractionMethod, AbsenceReason, PeriodBasis)
    def rev(value, restated, src):
        return ExtractionRecord(company="PeopleFlow", period_year=2025, period_quarter="Q1",
            metric=MetricName.REVENUE_QUARTERLY, value=value, canonical_unit=CanonicalUnit.USD_MILLIONS,
            currency=Currency.GBP, raw_text=f"{value}M", label_as_reported="Quarterly Revenue",
            source_file=src, source_page=2, source_snippet=f"Revenue {value}M",
            extraction_method=ExtractionMethod.LLM_PROSE, absence_reason=AbsenceReason.PRESENT,
            period_basis=PeriodBasis.FLOW_QUARTERLY, restated=restated)
    recs = [rev(4.7, False, "PeopleFlow_Q1_2025.pdf"), rev(4.6, True, "PeopleFlow_Q2_2025.pdf")]
    c = citation_for(recs, "PeopleFlow", (2025, "Q1"), MetricName.REVENUE_QUARTERLY)
    assert c["value"] == 4.6 and c["restated"] is True
    assert c["original_value"] == 4.7
    assert c["source_file"] == "PeopleFlow_Q2_2025.pdf"
    assert "restatement_note" in c
