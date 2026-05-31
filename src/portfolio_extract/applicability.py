from __future__ import annotations
from typing import Optional
from portfolio_extract.models import (MetricName, Sector, ExtractionRecord, ExtractionMethod,
    AbsenceReason, METRIC_UNIT, METRIC_PERIOD_BASIS)

_RETENTION = {MetricName.ARR, MetricName.NET_REVENUE_RETENTION,
              MetricName.GROSS_REVENUE_RETENTION, MetricName.LOGO_CHURN}

SECTOR_NA: dict[Sector, set[MetricName]] = {
    Sector.LENDING: set(_RETENTION),
    Sector.MARKETPLACE: set(_RETENTION),
    Sector.SAAS: set(),
    Sector.HYBRID: set(),
    Sector.OTHER: set(),
}

_GM_BASIS = {Sector.SAAS: "saas_cogs", Sector.MARKETPLACE: "marketplace_contribution",
             Sector.HYBRID: "marketplace_contribution", Sector.LENDING: "net_interest_spread"}
_REV_BASIS = {Sector.SAAS: "saas_recognized", Sector.MARKETPLACE: "marketplace_net_fees",
              Sector.HYBRID: "marketplace_net_fees", Sector.LENDING: "lending_interest_income"}


def is_not_applicable(metric: MetricName, sector: Sector) -> bool:
    return metric in SECTOR_NA.get(sector, set())

def basis_for(metric: MetricName, sector: Sector) -> Optional[str]:
    if metric == MetricName.GROSS_MARGIN:
        return _GM_BASIS.get(sector)
    if metric == MetricName.REVENUE_QUARTERLY:
        return _REV_BASIS.get(sector)
    return None

def synthesize_absences(present: set[MetricName], sector: Sector, company: str,
                        period_year: int, period_quarter: str, source_file: str) -> list[ExtractionRecord]:
    out: list[ExtractionRecord] = []
    for metric in MetricName:
        if metric in present:
            continue
        reason = (AbsenceReason.NOT_APPLICABLE if is_not_applicable(metric, sector)
                  else AbsenceReason.NULL_IN_SOURCE)
        out.append(ExtractionRecord(
            company=company, period_year=period_year, period_quarter=period_quarter, metric=metric,
            value=None, canonical_unit=METRIC_UNIT[metric], raw_text="", label_as_reported="",
            source_file=source_file, source_page=0, source_snippet="",
            extraction_method=ExtractionMethod.LLM_PROSE, confidence_tier=None, confidence_score=None,
            absence_reason=reason, period_basis=METRIC_PERIOD_BASIS[metric]))
    return out
