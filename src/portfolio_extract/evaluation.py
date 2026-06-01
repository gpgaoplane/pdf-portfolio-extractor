from __future__ import annotations
import re
from pathlib import Path
import yaml
from portfolio_extract.models import MetricName, CanonicalUnit, METRIC_UNIT, ExtractionMethod, AbsenceReason
from portfolio_extract.verify import TOLERANCE, _rel_diff

def load_labels(path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))

def _norm_quarter(q) -> str:
    m = re.search(r"[Qq]\s*([1-4])", str(q))
    return f"Q{m.group(1)}" if m else str(q).strip()

def _extractor_status(r) -> str:
    if r.value is not None:
        return "present"
    if r.absence_reason == AbsenceReason.NOT_APPLICABLE:
        return "not_applicable"
    return "null"

def _label_status(s) -> str:
    return {"present": "present", "null_in_source": "null", "not_applicable": "not_applicable"}.get(s, "null")

def _is_correct(value, expected, metric) -> bool:
    if value is None or expected is None:
        return False
    if METRIC_UNIT[metric] == CanonicalUnit.COUNT:
        return value == expected
    return _rel_diff(expected, value) <= TOLERANCE

def records_for(records, company, year, qtoken, metric):
    return [r for r in records if not r.restated and r.company == company
            and r.period_year == year and _norm_quarter(r.period_quarter) == qtoken and r.metric == metric]

def score(records, labels) -> dict:
    per_metric, warnings = {}, []
    omissions = hallucinations = status_ok = status_total = 0
    for _pdf, blk in labels.items():
        company, year = blk["company"], blk["period"]["year"]
        qtoken = _norm_quarter(blk["period"]["quarter"])
        for mname, lab in blk["metrics"].items():
            try:
                metric = MetricName(mname)
            except ValueError:
                continue
            recs = records_for(records, company, year, qtoken, metric)
            if len(recs) > 1:
                warnings.append(f"{company} {year} {qtoken} {mname}: {len(recs)} non-restated records")
            rec = recs[0] if recs else None
            lab_status = _label_status(lab.get("status"))
            ext_status = _extractor_status(rec) if rec else "null"
            status_total += 1
            status_ok += int(ext_status == lab_status)
            if lab_status == "present" and ext_status != "present":
                omissions += 1
            if lab_status in ("null", "not_applicable") and ext_status == "present":
                hallucinations += 1
            if lab_status == "present":
                pm = per_metric.setdefault(mname, [0, 0])
                pm[1] += 1
                if rec and ext_status == "present" and _is_correct(rec.value, lab.get("value"), metric):
                    pm[0] += 1
    return {"per_metric": per_metric, "omissions": omissions, "hallucinations": hallucinations,
            "status_agreement": [status_ok, status_total], "warnings": warnings}
