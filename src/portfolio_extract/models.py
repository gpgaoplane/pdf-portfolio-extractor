from __future__ import annotations
from enum import Enum
from typing import Optional
from pydantic import BaseModel


class MetricName(str, Enum):
    REVENUE_QUARTERLY = "revenue_quarterly"
    GROSS_MARGIN = "gross_margin"
    HEADCOUNT = "headcount"
    ARR = "arr"
    NET_REVENUE_RETENTION = "net_revenue_retention"
    GROSS_REVENUE_RETENTION = "gross_revenue_retention"
    LOGO_CHURN = "logo_churn"
    CASH_BALANCE = "cash_balance"
    NET_BURN_MONTHLY = "net_burn_monthly"
    EBITDA = "ebitda"


class CanonicalUnit(str, Enum):
    USD_MILLIONS = "usd_millions"
    PERCENT = "percent"
    COUNT = "count"


class Currency(str, Enum):
    USD = "USD"
    GBP = "GBP"
    EUR = "EUR"


class Sector(str, Enum):
    SAAS = "SaaS"
    MARKETPLACE = "Marketplace"
    LENDING = "Lending"
    HYBRID = "Hybrid"
    OTHER = "Other"


class ExtractionMethod(str, Enum):
    TABLE_CELL = "table_cell"
    LLM_PROSE = "llm_prose"
    LLM_RECONCILED = "llm_reconciled"


class ConfidenceTier(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class AbsenceReason(str, Enum):
    PRESENT = "present"
    NULL_IN_SOURCE = "null_in_source"
    NOT_APPLICABLE = "not_applicable"
    EXPECTED_NOT_FOUND = "expected_not_found"


class PeriodBasis(str, Enum):
    FLOW_QUARTERLY = "flow_quarterly"
    POINT_IN_TIME_EOP = "point_in_time_eop"
    RATIO_LTM = "ratio_ltm"
    FLOW_MONTHLY = "flow_monthly"


METRIC_UNIT: dict[MetricName, CanonicalUnit] = {
    MetricName.REVENUE_QUARTERLY: CanonicalUnit.USD_MILLIONS,
    MetricName.GROSS_MARGIN: CanonicalUnit.PERCENT,
    MetricName.HEADCOUNT: CanonicalUnit.COUNT,
    MetricName.ARR: CanonicalUnit.USD_MILLIONS,
    MetricName.NET_REVENUE_RETENTION: CanonicalUnit.PERCENT,
    MetricName.GROSS_REVENUE_RETENTION: CanonicalUnit.PERCENT,
    MetricName.LOGO_CHURN: CanonicalUnit.PERCENT,
    MetricName.CASH_BALANCE: CanonicalUnit.USD_MILLIONS,
    MetricName.NET_BURN_MONTHLY: CanonicalUnit.USD_MILLIONS,
    MetricName.EBITDA: CanonicalUnit.USD_MILLIONS,
}

METRIC_PERIOD_BASIS: dict[MetricName, PeriodBasis] = {
    MetricName.REVENUE_QUARTERLY: PeriodBasis.FLOW_QUARTERLY,
    MetricName.GROSS_MARGIN: PeriodBasis.RATIO_LTM,
    MetricName.HEADCOUNT: PeriodBasis.POINT_IN_TIME_EOP,
    MetricName.ARR: PeriodBasis.POINT_IN_TIME_EOP,
    MetricName.NET_REVENUE_RETENTION: PeriodBasis.RATIO_LTM,
    MetricName.GROSS_REVENUE_RETENTION: PeriodBasis.RATIO_LTM,
    MetricName.LOGO_CHURN: PeriodBasis.RATIO_LTM,
    MetricName.CASH_BALANCE: PeriodBasis.POINT_IN_TIME_EOP,
    MetricName.NET_BURN_MONTHLY: PeriodBasis.FLOW_MONTHLY,
    MetricName.EBITDA: PeriodBasis.FLOW_QUARTERLY,
}


class ExtractionRecord(BaseModel):
    company: str
    period_year: int
    period_quarter: str
    metric: MetricName
    value: Optional[float]
    canonical_unit: CanonicalUnit
    currency: Currency = Currency.USD
    basis: Optional[str] = None
    raw_text: str
    label_as_reported: str
    source_file: str
    source_page: int
    source_snippet: str
    bbox: Optional[tuple[float, float, float, float]] = None
    extraction_method: ExtractionMethod
    confidence_tier: ConfidenceTier
    confidence_score: float
    absence_reason: AbsenceReason
    period_basis: PeriodBasis
    extraction_timestamp: Optional[str] = None
    model_id: Optional[str] = None
    provider: Optional[str] = None
    prompt_version: Optional[str] = None
    source_doc_hash: Optional[str] = None
    notes: Optional[str] = None
