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

def _labeled_present(records, labels):
    """Yield (record, expected_value, metric) for each labeled-present cell with a matching record."""
    for _pdf, blk in labels.items():
        company, year = blk["company"], blk["period"]["year"]
        qtoken = _norm_quarter(blk["period"]["quarter"])
        for mname, lab in blk["metrics"].items():
            if lab.get("status") != "present":
                continue
            try:
                metric = MetricName(mname)
            except ValueError:
                continue
            recs = records_for(records, company, year, qtoken, metric)
            rec = recs[0] if recs else None
            if rec and rec.value is not None:
                yield rec, lab.get("value"), metric

def verification_ablation(records, labels) -> dict:
    mtx = {"verified": [0, 0], "unverified": [0, 0]}   # [correct, wrong]
    for rec, expected, metric in _labeled_present(records, labels):
        bucket = "verified" if rec.extraction_method == ExtractionMethod.TABLE_CELL else "unverified"
        mtx[bucket][0 if _is_correct(rec.value, expected, metric) else 1] += 1
    return mtx

def confidence_calibration(records, labels) -> dict:
    tiers = {"HIGH": [0, 0], "MEDIUM": [0, 0], "LOW": [0, 0]}   # [correct, wrong]
    for rec, expected, metric in _labeled_present(records, labels):
        if rec.confidence_tier is None:
            continue
        tiers[rec.confidence_tier.value][0 if _is_correct(rec.value, expected, metric) else 1] += 1
    return tiers

def time_series_flags(records, factor=5.0) -> list:
    by = {}
    for r in records:
        if r.restated or r.value is None or r.value == 0:
            continue
        by.setdefault((r.company, r.metric), []).append((r.period_year, _norm_quarter(r.period_quarter), r.value))
    flags = []
    for (company, metric), seq in by.items():
        seq.sort(key=lambda t: (t[0], t[1]))
        for (y0, q0, v0), (y1, q1, v1) in zip(seq, seq[1:]):
            ratio = max(abs(v0), abs(v1)) / max(min(abs(v0), abs(v1)), 1e-9)
            if ratio >= factor:
                flags.append((company, metric.value, f"{y0} {q0}->{y1} {q1}", round(ratio, 1)))
    return flags

def run_eval(db_path, labels_path) -> dict:
    from portfolio_extract.repository import SqliteRepository
    records = SqliteRepository(db_path).query()
    labels = load_labels(labels_path)
    return {"score": score(records, labels), "ablation": verification_ablation(records, labels),
            "calibration": confidence_calibration(records, labels), "time_series": time_series_flags(records)}

def main() -> None:
    import sys, json
    args = sys.argv[1:]
    db_path = args[0] if args else "out/portfolio.db"
    labels_path = args[1] if len(args) > 1 else "eval/labels.yaml"
    print(json.dumps(run_eval(db_path, labels_path), indent=2, default=str))
