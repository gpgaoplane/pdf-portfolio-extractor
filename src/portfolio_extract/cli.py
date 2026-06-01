from __future__ import annotations
import sys
import json, os, time
from collections import Counter
from pathlib import Path
from portfolio_extract.pipeline import extract_pdf
from portfolio_extract.repository import SqliteRepository
from portfolio_extract.registry import Registry
from portfolio_extract.extract_llm import PROMPT_VERSION

def run(pdf_paths: list[str], db_path: Path | str = "out/portfolio.db") -> int:
    db_path = Path(db_path); db_path.parent.mkdir(parents=True, exist_ok=True)
    repo = SqliteRepository(db_path); repo.init_schema()
    registry = Registry()
    total = 0
    by_tier: Counter = Counter(); by_method: Counter = Counter()
    start = time.perf_counter()
    for p in pdf_paths:
        de = extract_pdf(p)
        repo.save_many(de.records); total += len(de.records)
        registry.add(de.company, de.review)
        for r in de.records:
            by_tier[r.confidence_tier.value if r.confidence_tier else "none"] += 1
            by_method[r.extraction_method.value] += 1
        print(f"{Path(p).name}: {len(de.records)} records")
    registry.finalize()
    for company in registry.companies():
        repo.upsert_company(company)
    if registry.review:
        with open(db_path.parent / "review_queue.jsonl", "w", encoding="utf-8") as f:
            for item in registry.review:
                f.write(item.model_dump_json() + "\n")
    manifest = {
        "provider": os.environ.get("LLM_BASE_URL"), "model": os.environ.get("LLM_MODEL"),
        "prompt_version": PROMPT_VERSION, "documents": len(pdf_paths), "records": total,
        "by_tier": dict(by_tier), "by_method": dict(by_method),
        "review_items": len(registry.review), "wall_clock_s": round(time.perf_counter() - start, 2),
    }
    (db_path.parent / "run_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return total

def main() -> None:
    from dotenv import load_dotenv
    load_dotenv()  # the one-command CLI loads provider config (LLM_*) from .env
    args = sys.argv[1:]
    if not args:
        print("usage: portfolio-extract <pdf> [<pdf> ...]"); raise SystemExit(2)
    print(f"Total: {run(args)} records")

if __name__ == "__main__":
    main()
