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


def test_company_upsert_get_list(tmp_path):
    from portfolio_extract.repository import SqliteRepository
    from portfolio_extract.registry import CompanyRecord, Predecessor
    from portfolio_extract.models import Sector
    repo = SqliteRepository(tmp_path / "c.db"); repo.init_schema()
    repo.upsert_company(CompanyRecord(canonical_name="ApexFreight", sector=Sector.MARKETPLACE,
        aliases=["Apex Freight Solutions Inc."], predecessor=Predecessor(name="FleetLink")))
    got = repo.get_company("ApexFreight")
    assert got.sector == Sector.MARKETPLACE and got.predecessor.name == "FleetLink"
    repo.upsert_company(CompanyRecord(canonical_name="NovaCloud", sector=Sector.SAAS))
    assert {c.canonical_name for c in repo.list_companies()} == {"ApexFreight", "NovaCloud"}


def test_records_jsonl_roundtrip(tmp_path):
    from portfolio_extract.repository import export_records_jsonl, load_records_jsonl
    from portfolio_extract.models import (ExtractionRecord, MetricName, CanonicalUnit, Currency,
        ExtractionMethod, AbsenceReason, PeriodBasis)
    rec = ExtractionRecord(company="NovaCloud", period_year=2025, period_quarter="Q2",
        metric=MetricName.GROSS_MARGIN, value=78.0, canonical_unit=CanonicalUnit.PERCENT, currency=Currency.USD,
        raw_text="78%", label_as_reported="Gross Margin", source_file="NovaCloud_Q2_2025.pdf", source_page=1,
        source_snippet="Gross Margin 78%", extraction_method=ExtractionMethod.TABLE_CELL,
        absence_reason=AbsenceReason.PRESENT, period_basis=PeriodBasis.RATIO_LTM, basis="saas_cogs")
    p = tmp_path / "recs.jsonl"
    export_records_jsonl([rec], p)
    out = load_records_jsonl(p)
    assert len(out) == 1 and out[0].metric == MetricName.GROSS_MARGIN and out[0].basis == "saas_cogs"
