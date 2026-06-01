from types import SimpleNamespace
from portfolio_extract.registry import (resolve_identity, company_token_from_filename,
    map_sector, CompanyRecord, ReviewItem, Registry, Predecessor)
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

def test_registry_merges_quarters_and_accretes_aliases():
    reg = Registry()
    reg.add(CompanyRecord(canonical_name="NovaCloud", sector=Sector.SAAS, aliases=["NovaCloud Analytics Inc."]), [])
    reg.add(CompanyRecord(canonical_name="NovaCloud", sector=Sector.SAAS, aliases=["NovaCloud Inc."]), [])
    reg.finalize()
    companies = {c.canonical_name: c for c in reg.companies()}
    assert len(companies) == 1
    assert set(companies["NovaCloud"].aliases) == {"NovaCloud Analytics Inc.", "NovaCloud Inc."}

def test_registry_flags_sector_disagreement():
    reg = Registry()
    reg.add(CompanyRecord(canonical_name="X", sector=Sector.SAAS), [])
    reg.add(CompanyRecord(canonical_name="X", sector=Sector.MARKETPLACE), [])
    reg.finalize()
    assert any(r.kind == "sector_disagreement" for r in reg.review)

def test_registry_resolves_predecessor_to_canonical_token():
    reg = Registry()
    reg.add(CompanyRecord(canonical_name="FleetLink", sector=Sector.MARKETPLACE), [])
    reg.add(CompanyRecord(canonical_name="ApexFreight", sector=Sector.MARKETPLACE,
        predecessor=Predecessor(name="FleetLink Logistics Network", effective_date="2025-04-01")), [])
    reg.finalize()
    apex = {c.canonical_name: c for c in reg.companies()}["ApexFreight"]
    assert apex.predecessor.name == "FleetLink"

def test_registry_flags_unresolved_predecessor():
    reg = Registry()
    reg.add(CompanyRecord(canonical_name="ApexFreight", sector=Sector.MARKETPLACE,
        predecessor=Predecessor(name="Unknown Holdings LLC")), [])
    reg.finalize()
    assert any(r.kind == "predecessor_unresolved" for r in reg.review)

def test_load_companies_json_roundtrip(tmp_path):
    import json
    from portfolio_extract.registry import CompanyRecord, Predecessor, load_companies_json
    from portfolio_extract.models import Sector
    data = [json.loads(CompanyRecord(canonical_name="ApexFreight", sector=Sector.HYBRID,
              predecessor=Predecessor(name="FleetLink")).model_dump_json()),
            json.loads(CompanyRecord(canonical_name="NovaCloud", sector=Sector.SAAS).model_dump_json())]
    p = tmp_path / "c.json"; p.write_text(json.dumps(data), encoding="utf-8")
    comps = load_companies_json(p)
    assert comps["ApexFreight"].sector == Sector.HYBRID and comps["ApexFreight"].predecessor.name == "FleetLink"
    assert comps["NovaCloud"].sector == Sector.SAAS
