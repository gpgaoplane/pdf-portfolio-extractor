from portfolio_extract.applicability import is_not_applicable, basis_for, synthesize_absences
from portfolio_extract.models import MetricName as M, Sector, AbsenceReason

def test_sector_gating():
    assert is_not_applicable(M.ARR, Sector.LENDING)
    assert is_not_applicable(M.LOGO_CHURN, Sector.MARKETPLACE)
    assert not is_not_applicable(M.ARR, Sector.HYBRID)
    assert not is_not_applicable(M.ARR, Sector.SAAS)
    assert not is_not_applicable(M.REVENUE_QUARTERLY, Sector.LENDING)

def test_basis_for():
    assert basis_for(M.GROSS_MARGIN, Sector.LENDING) == "net_interest_spread"
    assert basis_for(M.GROSS_MARGIN, Sector.SAAS) == "saas_cogs"
    assert basis_for(M.REVENUE_QUARTERLY, Sector.MARKETPLACE) == "marketplace_net_fees"
    assert basis_for(M.GROSS_MARGIN, Sector.HYBRID) == "marketplace_contribution"
    assert basis_for(M.HEADCOUNT, Sector.SAAS) is None

def test_synthesize_absences_fills_missing_with_reasons():
    present = {M.REVENUE_QUARTERLY, M.GROSS_MARGIN, M.HEADCOUNT}
    recs = synthesize_absences(present, Sector.LENDING, "LendBridge", 2025, "Q1", "LendBridge_Q1_2025.pdf")
    by = {r.metric: r for r in recs}
    assert M.REVENUE_QUARTERLY not in by
    assert by[M.ARR].absence_reason == AbsenceReason.NOT_APPLICABLE
    assert by[M.CASH_BALANCE].absence_reason == AbsenceReason.NULL_IN_SOURCE
    assert by[M.ARR].value is None and by[M.ARR].confidence_tier is None
