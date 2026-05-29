from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from portfolio_extract.models import CanonicalUnit
from portfolio_extract.structural import Cell
from portfolio_extract.normalize import parse_number
from portfolio_extract.scale import to_canonical, ScaleContext

TOLERANCE = 0.01  # 1% relative

@dataclass(frozen=True)
class VerifyResult:
    matched: bool
    bbox: Optional[tuple[float, float, float, float]] = None

def verify_value(value: float, metric_unit: CanonicalUnit, page: int, cells: list[Cell],
                 unit_hint: Optional[str] = None) -> VerifyResult:
    ctx = ScaleContext(unit_hint)
    for c in cells:
        if c.page != page:
            continue
        cell_val = to_canonical(parse_number(c.text), metric_unit, ctx)
        if cell_val is None:
            continue
        if abs(cell_val - value) / max(abs(cell_val), 1e-9) <= TOLERANCE:
            return VerifyResult(True, c.bbox)
    return VerifyResult(False, None)
