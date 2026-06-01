from __future__ import annotations
import json
import re
from pathlib import Path
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


class Registry:
    def __init__(self) -> None:
        self._by_name: dict[str, CompanyRecord] = {}
        self.review: list[ReviewItem] = []

    def add(self, rec: CompanyRecord, doc_review: list[ReviewItem]) -> None:
        self.review.extend(doc_review)
        existing = self._by_name.get(rec.canonical_name)
        if existing is None:
            self._by_name[rec.canonical_name] = rec
            return
        for a in rec.aliases:
            if a not in existing.aliases:
                existing.aliases.append(a)
        if rec.predecessor and not existing.predecessor:
            existing.predecessor = rec.predecessor
        if rec.sector != existing.sector:
            self.review.append(ReviewItem(kind="sector_disagreement", canonical_name=rec.canonical_name,
                detail=f"sector differs across reports: {existing.sector.value} vs {rec.sector.value}"))
        if rec.identity_confidence == "LOW":
            existing.identity_confidence = "LOW"

    def finalize(self) -> None:
        norm_tokens = {_norm(t): t for t in self._by_name}
        for rec in self._by_name.values():
            if not rec.predecessor:
                continue
            np = _norm(rec.predecessor.name)
            match = next((canon for ntok, canon in norm_tokens.items()
                          if ntok and ntok != _norm(rec.canonical_name)
                          and (np.startswith(ntok) or ntok in np)), None)
            if match:
                rec.predecessor.name = match
            else:
                self.review.append(ReviewItem(kind="predecessor_unresolved", canonical_name=rec.canonical_name,
                    detail=f"predecessor '{rec.predecessor.name}' did not match a known company"))

    def companies(self) -> list[CompanyRecord]:
        return list(self._by_name.values())


def load_companies_json(path) -> dict[str, CompanyRecord]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    recs = [CompanyRecord.model_validate(d) for d in data]
    return {c.canonical_name: c for c in recs}
