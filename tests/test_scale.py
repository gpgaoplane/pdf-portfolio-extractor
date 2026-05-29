from portfolio_extract.models import CanonicalUnit
from portfolio_extract.normalize import parse_number
from portfolio_extract.scale import to_canonical, ScaleContext

def test_money_suffix_to_millions():
    assert to_canonical(parse_number("$8.4M"), CanonicalUnit.USD_MILLIONS, ScaleContext()) == 8.4

def test_bare_money_thousands_hint():
    assert to_canonical(parse_number("8400"), CanonicalUnit.USD_MILLIONS, ScaleContext("in thousands")) == 8.4

def test_bare_money_no_hint_defaults_millions():
    assert to_canonical(parse_number("8.4"), CanonicalUnit.USD_MILLIONS, ScaleContext()) == 8.4

def test_bare_as_count():
    assert to_canonical(parse_number("142"), CanonicalUnit.COUNT, ScaleContext()) == 142.0

def test_percent():
    assert to_canonical(parse_number("78%"), CanonicalUnit.PERCENT, ScaleContext()) == 78.0

def test_none_passthrough():
    assert to_canonical(None, CanonicalUnit.USD_MILLIONS, ScaleContext()) is None
