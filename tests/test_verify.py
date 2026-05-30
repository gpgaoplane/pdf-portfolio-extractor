from portfolio_extract.models import CanonicalUnit
from portfolio_extract.structural import Cell
from portfolio_extract.verify import verify_value

CELLS = [Cell("$8.4M", 1, (0, 0, 1, 1)), Cell("78%", 1, (0, 1, 1, 2)), Cell("142", 1, (0, 2, 1, 3))]

def test_exact_money_match():
    r = verify_value(8.4, CanonicalUnit.USD_MILLIONS, 1, CELLS)
    assert r.matched and r.bbox == (0, 0, 1, 1)

def test_percent_match():
    assert verify_value(78.0, CanonicalUnit.PERCENT, 1, CELLS).matched

def test_count_match():
    assert verify_value(142.0, CanonicalUnit.COUNT, 1, CELLS).matched

def test_negative_case_flags_mismatch():
    r = verify_value(9.9, CanonicalUnit.USD_MILLIONS, 1, CELLS)
    assert not r.matched and r.bbox is None

def test_scale_aware_bare_cell():
    cells = [Cell("8400", 1, (0, 0, 1, 1))]
    assert verify_value(8.4, CanonicalUnit.USD_MILLIONS, 1, cells, unit_hint="in thousands").matched


from portfolio_extract.verify import MatchQuality

# full-width row cells: label + value live in the SAME cell text.
# decoy is FIRST, so without label-awareness it would be matched instead.
SAME_CELL = [
    Cell("Pipeline Count 142 deals", 1, (9, 9, 10, 10)),  # first number 142 -> decoy
    Cell("Total Headcount 142", 1, (0, 0, 1, 1)),         # the real labelled cell
]

def test_label_aware_picks_the_labelled_cell():
    r = verify_value(142.0, CanonicalUnit.COUNT, 1, SAME_CELL, label="Total Headcount")
    assert r.matched and r.bbox == (0, 0, 1, 1)  # the headcount cell, not the earlier decoy

def test_falls_back_to_any_cell_when_label_absent():
    # label not present in any cell -> fall back to any-cell match (current behavior preserved)
    r = verify_value(142.0, CanonicalUnit.COUNT, 1, SAME_CELL, label="FTE")
    assert r.matched  # still verifies via fallback

def test_exact_vs_rounding_quality():
    cells = [Cell("Revenue (USD) $8.42M", 1, (0, 0, 1, 1))]
    assert verify_value(8.42, CanonicalUnit.USD_MILLIONS, 1, cells, label="Revenue").quality == MatchQuality.EXACT
    # 8.4 is within 1% of 8.42 -> rounding-tolerance, not exact
    assert verify_value(8.4, CanonicalUnit.USD_MILLIONS, 1, cells, label="Revenue").quality == MatchQuality.ROUNDING

def test_no_match_quality_none():
    cells = [Cell("Revenue $8.4M", 1, (0, 0, 1, 1))]
    assert verify_value(9.9, CanonicalUnit.USD_MILLIONS, 1, cells, label="Revenue").quality == MatchQuality.NONE
