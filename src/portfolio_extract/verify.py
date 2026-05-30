from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional
from portfolio_extract.models import CanonicalUnit
from portfolio_extract.structural import Cell
from portfolio_extract.normalize import parse_number
from portfolio_extract.scale import to_canonical, ScaleContext

TOLERANCE = 0.01   # 1% relative — rounding-tolerance band
EXACT_EPS = 1e-6   # below this relative diff, treat as an exact match


class MatchQuality(str, Enum):
    EXACT = "exact"
    ROUNDING = "rounding"
    NONE = "none"


@dataclass(frozen=True)
class VerifyResult:
    quality: MatchQuality
    bbox: Optional[tuple[float, float, float, float]] = None

    @property
    def matched(self) -> bool:
        return self.quality != MatchQuality.NONE


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def _label_matches(cell_text: str, label: str) -> bool:
    # cells are full-width row strings; the (shorter) label is a substring of the cell text
    a, b = _norm(cell_text), _norm(label)
    return bool(a and b and b in a)


def _rel_diff(a: float, b: float) -> float:
    return abs(a - b) / max(abs(a), 1e-9)


def _scan(cells: list[Cell], value: float, metric_unit: CanonicalUnit,
          ctx: ScaleContext) -> VerifyResult:
    best: Optional[VerifyResult] = None
    for c in cells:
        cell_val = to_canonical(parse_number(c.text), metric_unit, ctx)
        if cell_val is None:
            continue
        d = _rel_diff(cell_val, value)
        if d <= EXACT_EPS:
            return VerifyResult(MatchQuality.EXACT, c.bbox)
        if d <= TOLERANCE and best is None:
            best = VerifyResult(MatchQuality.ROUNDING, c.bbox)
    return best or VerifyResult(MatchQuality.NONE, None)


def verify_value(value: float, metric_unit: CanonicalUnit, page: int, cells: list[Cell],
                 label: Optional[str] = None, unit_hint: Optional[str] = None) -> VerifyResult:
    ctx = ScaleContext(unit_hint)
    page_cells = [c for c in cells if c.page == page]

    # Label-aware: prefer cells whose text contains the label.
    if label:
        labelled = [c for c in page_cells if _label_matches(c.text, label)]
        res = _scan(labelled, value, metric_unit, ctx)
        if res.matched:
            return res
    # Fallback: any cell on the page (prose value, or label phrasing not found in a cell).
    return _scan(page_cells, value, metric_unit, ctx)
