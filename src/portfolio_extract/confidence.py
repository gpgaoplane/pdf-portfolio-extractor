from __future__ import annotations
from enum import Enum
from portfolio_extract.models import ConfidenceTier


class MatchLevel(str, Enum):
    EXACT_CELL = "exact_cell"
    ROUNDING_CELL = "rounding_cell"
    PROSE_SNIPPET = "prose_snippet"
    SNIPPET_MISMATCH = "snippet_mismatch"
    ABSENT = "absent"


_BASE = {
    MatchLevel.EXACT_CELL: 0.95,
    MatchLevel.ROUNDING_CELL: 0.85,
    MatchLevel.PROSE_SNIPPET: 0.70,
    MatchLevel.SNIPPET_MISMATCH: 0.50,
    MatchLevel.ABSENT: 0.20,
}


def score_confidence(*, match_level: MatchLevel, known_alias: bool,
                     reconciled: bool) -> tuple[ConfidenceTier, float]:
    base = _BASE[match_level]
    base += 0.05 if known_alias else -0.05
    if reconciled:
        base = min(base, 0.75)
    score = max(0.0, min(1.0, base))
    tier = (ConfidenceTier.HIGH if score >= 0.85
            else ConfidenceTier.MEDIUM if score >= 0.60 else ConfidenceTier.LOW)
    return tier, round(score, 3)
