from __future__ import annotations
import re
from portfolio_extract.models import MetricName

METRIC_ALIASES: dict[MetricName, set[str]] = {
    MetricName.REVENUE_QUARTERLY: {"recognized revenue", "quarterly revenue", "net revenue",
        "platform revenue", "gross transaction revenue", "total recognized revenue"},
    MetricName.ARR: {"annual recurring revenue", "contracted arr", "subscription arr",
        "end-of-period arr", "arr"},
    MetricName.NET_REVENUE_RETENTION: {"net revenue retention", "net dollar retention",
        "net pound retention", "nrr", "ndr", "npr"},
    MetricName.GROSS_REVENUE_RETENTION: {"gross revenue retention", "grr"},
    MetricName.LOGO_CHURN: {"logo churn", "annual logo churn", "logo churn rate"},
    MetricName.HEADCOUNT: {"total headcount", "headcount", "fte"},
    MetricName.CASH_BALANCE: {"cash balance", "cash and equivalents", "cash & equivalents"},
    MetricName.NET_BURN_MONTHLY: {"monthly net burn", "monthly cash burn", "net burn"},
    MetricName.EBITDA: {"ebitda"},
    MetricName.GROSS_MARGIN: {"gross margin"},
}

def _norm(s: str) -> str:
    s = re.sub(r"\([^)]*\)", "", s.lower())        # strip parentheticals
    return re.sub(r"[^a-z0-9 ]", "", s).strip()

def is_known_alias(metric: MetricName, label: str) -> bool:
    n = _norm(label)
    if not n:
        return False
    return any(a in n or n in a for a in (_norm(x) for x in METRIC_ALIASES.get(metric, set())))
