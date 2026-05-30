from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from portfolio_extract.structural import extract_structure
from portfolio_extract.extract_llm import extract_with_llm, build_records_from_llm
from portfolio_extract.verify import verify_value, VerifyResult, MatchQuality
from portfolio_extract.confidence import score_confidence, MatchLevel
from portfolio_extract.models import ExtractionRecord, ExtractionMethod, AbsenceReason
from portfolio_extract.registry import resolve_identity, CompanyRecord, ReviewItem


@dataclass
class DocumentExtraction:
    records: list[ExtractionRecord]
    company: CompanyRecord
    review: list[ReviewItem]


def extract_pdf(pdf_path: Path | str) -> DocumentExtraction:
    pdf_path = Path(pdf_path)
    pages = extract_structure(pdf_path)
    all_cells = [c for p in pages for c in p.cells]
    hint_by_page = {p.number: p.unit_hint for p in pages}
    doc_hint = next((p.unit_hint for p in pages if p.unit_hint), None)
    text_by_page = {p.number: p.text for p in pages}

    out = extract_with_llm([p.text for p in pages])
    company, review = resolve_identity(pdf_path.name, out)
    records = build_records_from_llm(out, source_file=pdf_path.name,
                                     hint_by_page=hint_by_page, doc_hint=doc_hint)

    finalized: list[ExtractionRecord] = []
    for r in records:
        hint = hint_by_page.get(r.source_page) or doc_hint
        vr = (verify_value(r.value, r.canonical_unit, r.source_page, all_cells,
                           label=r.label_as_reported, unit_hint=hint)
              if r.value is not None else None)
        level = _match_level(r, vr, text_by_page.get(r.source_page, ""))
        tier, score = score_confidence(match_level=level, known_alias=True,  # known_alias: STUB (Plan 2c)
                                       reconciled=False)
        finalized.append(r.model_copy(update={
            "extraction_method": (ExtractionMethod.TABLE_CELL
                                  if level in (MatchLevel.EXACT_CELL, MatchLevel.ROUNDING_CELL)
                                  else r.extraction_method),
            "company": company.canonical_name,
            "bbox": vr.bbox if vr else None, "confidence_tier": tier, "confidence_score": score,
            "absence_reason": AbsenceReason.PRESENT if r.value is not None else AbsenceReason.EXPECTED_NOT_FOUND}))
    return DocumentExtraction(records=finalized, company=company, review=review)


def _match_level(r: ExtractionRecord, vr: VerifyResult | None, page_text: str) -> MatchLevel:
    if r.value is None:
        return MatchLevel.ABSENT
    if vr and vr.quality == MatchQuality.EXACT:
        return MatchLevel.EXACT_CELL
    if vr and vr.quality == MatchQuality.ROUNDING:
        return MatchLevel.ROUNDING_CELL
    raw = r.raw_text.strip()
    if raw and raw in r.source_snippet:
        return MatchLevel.PROSE_SNIPPET
    if raw and raw in page_text:
        return MatchLevel.SNIPPET_MISMATCH
    return MatchLevel.ABSENT
