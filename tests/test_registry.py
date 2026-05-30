from types import SimpleNamespace
from portfolio_extract.registry import (resolve_identity, company_token_from_filename,
    map_sector, CompanyRecord, ReviewItem)
from portfolio_extract.models import Sector

def _out(company_name, sector="SaaS", predecessor_name=None, predecessor_effective_date=None):
    return SimpleNamespace(company_name=company_name, sector=sector,
                           predecessor_name=predecessor_name,
                           predecessor_effective_date=predecessor_effective_date)

def test_token_from_filename():
    assert company_token_from_filename("data/ApexFreight_Q2_2025.pdf") == "ApexFreight"
    assert company_token_from_filename("NovaCloud_Q2_2025.pdf") == "NovaCloud"

def test_map_sector_known_and_unknown():
    assert map_sector("SaaS") == (Sector.SAAS, True)
    assert map_sector("marketplace") == (Sector.MARKETPLACE, True)
    assert map_sector("Fintech") == (Sector.OTHER, False)

def test_resolve_identity_match_is_high():
    rec, review = resolve_identity("NovaCloud_Q2_2025.pdf", _out("NovaCloud Analytics Inc."))
    assert rec.canonical_name == "NovaCloud" and rec.identity_confidence == "HIGH"
    assert rec.sector == Sector.SAAS
    assert "NovaCloud Analytics Inc." in rec.aliases
    assert review == []

def test_resolve_identity_mismatch_flags_review():
    rec, review = resolve_identity("FooCorp_Q2_2025.pdf", _out("Bar Industries Ltd."))
    assert rec.identity_confidence == "LOW"
    assert any(r.kind == "identity_mismatch" for r in review)

def test_resolve_identity_unmapped_sector_flags_review():
    rec, review = resolve_identity("NovaCloud_Q2_2025.pdf", _out("NovaCloud", sector="Fintech"))
    assert rec.sector == Sector.OTHER
    assert any(r.kind == "sector_unmapped" for r in review)

def test_resolve_identity_captures_predecessor():
    rec, _ = resolve_identity("ApexFreight_Q2_2025.pdf",
        _out("Apex Freight Solutions Inc.", sector="Marketplace",
             predecessor_name="FleetLink Logistics Network", predecessor_effective_date="2025-04-01"))
    assert rec.predecessor and rec.predecessor.name == "FleetLink Logistics Network"
    assert rec.predecessor.effective_date == "2025-04-01"
