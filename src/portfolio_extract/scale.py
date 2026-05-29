from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional
from portfolio_extract.models import CanonicalUnit
from portfolio_extract.normalize import ParsedNumber, UnitKind

@dataclass(frozen=True)
class ScaleContext:
    unit_hint: Optional[str] = None  # from a column header / table caption / footnote

def _hint_multiplier(hint: Optional[str]) -> Optional[float]:
    if not hint:
        return None
    h = hint.lower()
    if "thousand" in h or re.search(r"\$?k\b", h):
        return 1e-3
    if "million" in h or re.search(r"\$?m\b", h):
        return 1.0
    if "billion" in h or re.search(r"\$?bn\b", h):
        return 1e3
    return None

def to_canonical(p: Optional[ParsedNumber], target_unit: CanonicalUnit,
                 ctx: ScaleContext) -> Optional[float]:
    """Resolve a parsed number to the metric's canonical unit."""
    if p is None:
        return None
    if target_unit == CanonicalUnit.PERCENT:
        return p.magnitude
    if target_unit == CanonicalUnit.COUNT:
        return p.magnitude
    if target_unit == CanonicalUnit.USD_MILLIONS:
        if p.kind == UnitKind.MONEY_MILLIONS:
            return p.magnitude
        if p.kind == UnitKind.BARE:
            mult = _hint_multiplier(ctx.unit_hint)
            return round(p.magnitude * mult, 6) if mult is not None else p.magnitude
        return p.magnitude
    return None
