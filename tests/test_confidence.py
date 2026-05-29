from portfolio_extract.confidence import score_confidence
from portfolio_extract.models import ConfidenceTier

def test_verified_is_high():
    t, s = score_confidence(verified=True, snippet_supports=True, known_alias=True, reconciled=False)
    assert t == ConfidenceTier.HIGH and s >= 0.85

def test_prose_supported_is_medium():
    t, _ = score_confidence(verified=False, snippet_supports=True, known_alias=True, reconciled=False)
    assert t == ConfidenceTier.MEDIUM

def test_unsupported_is_low():
    t, s = score_confidence(verified=False, snippet_supports=False, known_alias=False, reconciled=False)
    assert t == ConfidenceTier.LOW and s <= 0.6

def test_reconciled_capped():
    _, s = score_confidence(verified=True, snippet_supports=True, known_alias=True, reconciled=True)
    assert s <= 0.75
