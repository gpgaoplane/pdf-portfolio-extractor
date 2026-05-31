from portfolio_extract.aliases import is_known_alias
from portfolio_extract.models import MetricName

def test_known_alias_with_parenthetical_label():
    assert is_known_alias(MetricName.REVENUE_QUARTERLY, "Recognized Revenue (USD)")
    assert is_known_alias(MetricName.ARR, "Contracted ARR (end of period)")
    assert is_known_alias(MetricName.NET_REVENUE_RETENTION, "Net Dollar Retention (LTM)")
    assert is_known_alias(MetricName.HEADCOUNT, "FTE")

def test_novel_label_is_not_known():
    assert not is_known_alias(MetricName.REVENUE_QUARTERLY, "Bookings Pipeline ACV")
    assert not is_known_alias(MetricName.ARR, "")
