from __future__ import annotations
from pathlib import Path
from portfolio_extract.structural import extract_structure
from portfolio_extract.extract_llm import extract_with_llm, build_records_from_llm
from portfolio_extract.verify import verify_value
from portfolio_extract.confidence import score_confidence
from portfolio_extract.models import ExtractionRecord, ExtractionMethod, AbsenceReason

def extract_pdf(pdf_path: Path | str) -> list[ExtractionRecord]:
    pdf_path = Path(pdf_path)
    pages = extract_structure(pdf_path)
    all_cells = [c for p in pages for c in p.cells]
    hint_by_page = {p.number: p.unit_hint for p in pages}
    doc_hint = next((p.unit_hint for p in pages if p.unit_hint), None)

    out = extract_with_llm([p.text for p in pages])
    records = build_records_from_llm(out, source_file=pdf_path.name, unit_hint=doc_hint)

    finalized: list[ExtractionRecord] = []
    for r in records:
        hint = hint_by_page.get(r.source_page, doc_hint)
        vr = (verify_value(r.value, r.canonical_unit, r.source_page, all_cells, unit_hint=hint)
              if r.value is not None else None)
        verified = bool(vr and vr.matched)
        snippet_supports = r.raw_text.strip() in r.source_snippet
        tier, score = score_confidence(verified=verified, snippet_supports=snippet_supports,
                                       known_alias=True, reconciled=False)  # known_alias: STUB (Plan 2)
        finalized.append(r.model_copy(update={
            "extraction_method": ExtractionMethod.TABLE_CELL if verified else r.extraction_method,
            "bbox": vr.bbox if vr else None, "confidence_tier": tier, "confidence_score": score,
            "absence_reason": AbsenceReason.PRESENT if r.value is not None else AbsenceReason.EXPECTED_NOT_FOUND}))
    return finalized
