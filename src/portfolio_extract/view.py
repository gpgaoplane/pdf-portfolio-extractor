from __future__ import annotations
import pandas as pd
from portfolio_extract.models import ExtractionRecord, MetricName

def company_period_matrix(records: list[ExtractionRecord], metric: MetricName
                          ) -> dict[tuple[str, int, str], float | None]:
    """Minimal comparable view. Reconciliation, cross-basis gating, currency = Plan 2."""
    return {(r.company, r.period_year, r.period_quarter): r.value
            for r in records if r.metric == metric}

def _reconcile(df):
    return df

def comparison_frame(records, registry=None):
    rows = [{
        "company": r.company, "period_year": r.period_year, "period_quarter": r.period_quarter,
        "metric": r.metric.value, "value": r.value, "currency": r.currency.value, "basis": r.basis,
        "period_basis": r.period_basis.value, "absence_reason": r.absence_reason.value,
        "confidence_tier": r.confidence_tier.value if r.confidence_tier else None,
        "source_file": r.source_file, "restated": r.restated,
    } for r in records]
    return _reconcile(pd.DataFrame(rows))
