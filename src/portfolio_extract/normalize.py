from __future__ import annotations
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional

class UnitKind(str, Enum):
    PERCENT = "percent"
    MONEY_MILLIONS = "money_millions"  # already scaled to $M (had a money symbol or k/m/bn suffix)
    BARE = "bare"                       # plain number; kind resolved by the target metric

@dataclass(frozen=True)
class ParsedNumber:
    magnitude: float
    kind: UnitKind

_SCALE = {"k": 1e-3, "m": 1.0, "bn": 1e3, "b": 1e3}  # multipliers into $M
_NUM_RE = re.compile(r"[-+]?\d[\d,]*\.?\d*")

def parse_number(raw: Optional[str]) -> Optional[ParsedNumber]:
    if not raw or not raw.strip():
        return None
    s = raw.strip()
    negative = s.startswith("(") and s.endswith(")")
    body = s.strip("()").strip()
    low = body.lower()
    m = _NUM_RE.search(body)
    if not m:
        return None
    magnitude = float(m.group(0).replace(",", ""))
    if negative:
        magnitude = -magnitude
    if "%" in body:
        return ParsedNumber(magnitude, UnitKind.PERCENT)
    scale = re.search(r"(bn|[kmb])\b", low)
    if scale:
        return ParsedNumber(round(magnitude * _SCALE[scale.group(1)], 6), UnitKind.MONEY_MILLIONS)
    if "$" in body or "£" in body or "€" in body:
        return ParsedNumber(round(magnitude / 1e6, 6), UnitKind.MONEY_MILLIONS)
    return ParsedNumber(magnitude, UnitKind.BARE)
