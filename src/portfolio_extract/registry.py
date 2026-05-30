from __future__ import annotations
import re
from typing import Optional
from pydantic import BaseModel
from portfolio_extract.models import Sector


class Predecessor(BaseModel):
    name: str
    effective_date: Optional[str] = None


class CompanyRecord(BaseModel):
    canonical_name: str
    sector: Sector
    aliases: list[str] = []
    predecessor: Optional[Predecessor] = None
    identity_confidence: str = "HIGH"   # HIGH | LOW


class ReviewItem(BaseModel):
    kind: str   # identity_mismatch | sector_unmapped | predecessor_unresolved | sector_disagreement
    canonical_name: str
    detail: str


_SECTOR_MAP = {
    "saas": Sector.SAAS, "marketplace": Sector.MARKETPLACE,
    "lending": Sector.LENDING, "hybrid": Sector.HYBRID,
}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


def company_token_from_filename(filename: str) -> str:
    stem = re.split(r"[\\/]", filename)[-1]
    if stem.lower().endswith(".pdf"):
        stem = stem[:-4]
    return stem.split("_")[0]


def map_sector(raw: str) -> tuple[Sector, bool]:
    key = _norm(raw)
    return (_SECTOR_MAP.get(key, Sector.OTHER), key in _SECTOR_MAP)


def resolve_identity(filename: str, out) -> tuple[CompanyRecord, list[ReviewItem]]:
    token = company_token_from_filename(filename)
    review: list[ReviewItem] = []
    nt, nn = _norm(token), _norm(out.company_name)
    name_match = bool(nt) and (nt in nn or nn.startswith(nt))
    if not name_match:
        review.append(ReviewItem(kind="identity_mismatch", canonical_name=token,
            detail=f"filename token '{token}' not found in LLM company_name '{out.company_name}'"))
    sector, ok = map_sector(out.sector)
    if not ok:
        review.append(ReviewItem(kind="sector_unmapped", canonical_name=token,
            detail=f"LLM sector '{out.sector}' not recognized; defaulted to OTHER"))
    predecessor = None
    if getattr(out, "predecessor_name", None):
        predecessor = Predecessor(name=out.predecessor_name,
                                  effective_date=getattr(out, "predecessor_effective_date", None))
    aliases = [out.company_name] if nn and nn != nt else []
    rec = CompanyRecord(canonical_name=token, sector=sector, aliases=aliases,
                        predecessor=predecessor,
                        identity_confidence="HIGH" if name_match else "LOW")
    return rec, review
