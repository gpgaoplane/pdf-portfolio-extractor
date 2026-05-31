import yaml
from pathlib import Path
from portfolio_extract.applicability import is_not_applicable
from portfolio_extract.models import MetricName, Sector

def test_labels_not_applicable_matches_rule():
    data = yaml.safe_load(Path("eval/labels.yaml").read_text(encoding="utf-8"))
    for pdf, blk in data.items():
        sector = Sector(blk["sector"])
        for mname, lab in blk["metrics"].items():
            if lab.get("status") == "not_applicable":
                assert is_not_applicable(MetricName(mname), sector), f"{pdf}:{mname} marked n/a but rule says applicable"
