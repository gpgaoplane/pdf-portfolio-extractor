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
