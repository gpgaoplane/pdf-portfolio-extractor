from portfolio_extract.confidence import score_confidence, MatchLevel
from portfolio_extract.models import ConfidenceTier

def test_exact_cell_is_high():
    t, s = score_confidence(match_level=MatchLevel.EXACT_CELL, known_alias=True, reconciled=False)
    assert t == ConfidenceTier.HIGH and s >= 0.85

def test_rounding_cell_is_high():
    t, s = score_confidence(match_level=MatchLevel.ROUNDING_CELL, known_alias=True, reconciled=False)
    assert t == ConfidenceTier.HIGH and s == 0.90  # 0.85 + 0.05

def test_prose_snippet_is_medium():
    t, _ = score_confidence(match_level=MatchLevel.PROSE_SNIPPET, known_alias=True, reconciled=False)
    assert t == ConfidenceTier.MEDIUM

def test_snippet_mismatch_is_low():
    t, s = score_confidence(match_level=MatchLevel.SNIPPET_MISMATCH, known_alias=False, reconciled=False)
    assert t == ConfidenceTier.LOW and s == 0.45  # 0.50 - 0.05

def test_absent_is_low():
    t, s = score_confidence(match_level=MatchLevel.ABSENT, known_alias=False, reconciled=False)
    assert t == ConfidenceTier.LOW and s <= 0.20

def test_reconciled_capped():
    _, s = score_confidence(match_level=MatchLevel.EXACT_CELL, known_alias=True, reconciled=True)
    assert s <= 0.75
