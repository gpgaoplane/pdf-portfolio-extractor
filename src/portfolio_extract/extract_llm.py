from __future__ import annotations
import os
from pydantic import BaseModel
import instructor
from openai import OpenAI
from portfolio_extract.models import (ExtractionRecord, MetricName, METRIC_UNIT, METRIC_PERIOD_BASIS,
    Currency, ExtractionMethod, ConfidenceTier, AbsenceReason)
from portfolio_extract.normalize import parse_number
from portfolio_extract.scale import to_canonical, ScaleContext

PROMPT_VERSION = "thin-slice-v1"

_CURRENCY_ALIASES = {
    "USD": Currency.USD, "$": Currency.USD, "US$": Currency.USD, "USD$": Currency.USD,
    "GBP": Currency.GBP, "£": Currency.GBP,
    "EUR": Currency.EUR, "€": Currency.EUR,
}

def _coerce_currency(raw: str | None) -> tuple[Currency, bool]:
    """Map an LLM-returned currency string to the Currency enum.
    Returns (currency, recognized); unrecognized strings fall back to USD with recognized=False
    so the caller can flag rather than silently default."""
    t = (raw or "").strip().upper()
    if t in _CURRENCY_ALIASES:
        return _CURRENCY_ALIASES[t], True
    return Currency.USD, False

class LLMMetric(BaseModel):
    metric: str
    raw_text: str
    label_as_reported: str
    source_page: int
    source_snippet: str

class LLMExtraction(BaseModel):
    company_name: str
    sector: str
    period_year: int
    period_quarter: str
    currency: str
    metrics: list[LLMMetric]

_SYSTEM = (
    "Extract universal-core metrics from a quarterly portfolio-company report: revenue_quarterly, "
    "gross_margin, headcount. Use canonical names. For each, give the value EXACTLY as printed "
    "(raw_text), the company's own label, the 1-indexed page, and the surrounding snippet. Map "
    "variants (FTE->headcount; Recognized/Quarterly/Net/Platform/Gross Transaction Revenue->"
    "revenue_quarterly). Never invent a value not in the text.")

_MODES = {"JSON": instructor.Mode.JSON, "TOOLS": instructor.Mode.TOOLS}

def make_client():
    # Structured-output mode is env-configurable so a provider that rejects JSON mode
    # (some DeepSeek/reasoning models) can switch to tool-calling without a code change.
    mode = _MODES.get(os.environ.get("LLM_MODE", "JSON").upper(), instructor.Mode.JSON)
    return instructor.from_openai(
        OpenAI(base_url=os.environ["LLM_BASE_URL"], api_key=os.environ["LLM_API_KEY"]),
        mode=mode)

def extract_with_llm(page_texts: list[str]) -> LLMExtraction:
    client = make_client()
    joined = "\n\n".join(f"[page {i}]\n{t}" for i, t in enumerate(page_texts, 1))
    kwargs = {}
    # DashScope hybrid-thinking models (Qwen3, DeepSeek) reject tool_choice=required while in
    # thinking mode, so structured extraction needs thinking off. Env-gated to stay provider-
    # agnostic: only sent when LLM_ENABLE_THINKING is explicitly false-y.
    if os.environ.get("LLM_ENABLE_THINKING", "").strip().lower() in ("false", "0", "no", "off"):
        kwargs["extra_body"] = {"enable_thinking": False}
    return client.chat.completions.create(
        model=os.environ.get("LLM_MODEL", "deepseek-v4-flash"), response_model=LLMExtraction,
        messages=[{"role": "system", "content": _SYSTEM}, {"role": "user", "content": joined}],
        **kwargs)

def build_records_from_llm(out: LLMExtraction, source_file: str,
                           hint_by_page: dict[int, str | None] | None = None,
                           doc_hint: str | None = None) -> list[ExtractionRecord]:
    records: list[ExtractionRecord] = []
    hint_by_page = hint_by_page or {}
    currency, currency_ok = _coerce_currency(out.currency)
    currency_note = None if currency_ok else f"unrecognized currency '{out.currency}'; defaulted to USD"
    for m in out.metrics:
        try:
            metric = MetricName(m.metric)
        except ValueError:
            continue
        hint = hint_by_page.get(m.source_page) or doc_hint
        value = to_canonical(parse_number(m.raw_text), METRIC_UNIT[metric], ScaleContext(hint))
        records.append(ExtractionRecord(
            company=out.company_name, period_year=out.period_year, period_quarter=out.period_quarter,
            metric=metric, value=value, canonical_unit=METRIC_UNIT[metric], currency=currency,
            raw_text=m.raw_text, label_as_reported=m.label_as_reported, source_file=source_file,
            source_page=m.source_page, source_snippet=m.source_snippet,
            extraction_method=ExtractionMethod.LLM_PROSE, confidence_tier=ConfidenceTier.LOW,
            confidence_score=0.0, absence_reason=AbsenceReason.PRESENT,
            period_basis=METRIC_PERIOD_BASIS[metric], prompt_version=PROMPT_VERSION, notes=currency_note))
    return records
