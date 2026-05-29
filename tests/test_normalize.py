import pytest
from portfolio_extract.normalize import parse_number, ParsedNumber, UnitKind

@pytest.mark.parametrize("raw, magnitude, kind", [
    ("$8.4M", 8.4, UnitKind.MONEY_MILLIONS),
    ("8.6M", 8.6, UnitKind.MONEY_MILLIONS),
    ("$241k", 0.241, UnitKind.MONEY_MILLIONS),
    ("1.2bn", 1200.0, UnitKind.MONEY_MILLIONS),
    ("78%", 78.0, UnitKind.PERCENT),
    ("123%", 123.0, UnitKind.PERCENT),
    ("1,042", 1042.0, UnitKind.BARE),
    ("142", 142.0, UnitKind.BARE),
    ("8400", 8400.0, UnitKind.BARE),
    ("($0.55M)", -0.55, UnitKind.MONEY_MILLIONS),
    ("(0.21)", -0.21, UnitKind.BARE),
    ("8.4", 8.4, UnitKind.BARE),
])
def test_parse_number(raw, magnitude, kind):
    assert parse_number(raw) == ParsedNumber(magnitude=magnitude, kind=kind)

def test_unparseable_returns_none():
    assert parse_number("n/a") is None and parse_number("") is None
