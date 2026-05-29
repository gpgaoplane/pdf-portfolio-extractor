from __future__ import annotations
from portfolio_extract.models import ExtractionRecord, MetricName

def company_period_matrix(records: list[ExtractionRecord], metric: MetricName
                          ) -> dict[tuple[str, int, str], float | None]:
    """Minimal comparable view. Reconciliation, cross-basis gating, currency = Plan 2."""
    return {(r.company, r.period_year, r.period_quarter): r.value
            for r in records if r.metric == metric}
