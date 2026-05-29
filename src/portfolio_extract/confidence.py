from __future__ import annotations
from portfolio_extract.models import ConfidenceTier

def score_confidence(*, verified: bool, snippet_supports: bool,
                     known_alias: bool, reconciled: bool) -> tuple[ConfidenceTier, float]:
    base = 0.95 if verified else (0.70 if snippet_supports else 0.20)
    base += 0.05 if known_alias else -0.05
    if reconciled:
        base = min(base, 0.75)
    score = max(0.0, min(1.0, base))
    tier = (ConfidenceTier.HIGH if score >= 0.85
            else ConfidenceTier.MEDIUM if score >= 0.60 else ConfidenceTier.LOW)
    return tier, round(score, 3)
