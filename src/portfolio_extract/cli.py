from __future__ import annotations
import sys
from pathlib import Path
from portfolio_extract.pipeline import extract_pdf
from portfolio_extract.repository import SqliteRepository
from portfolio_extract.registry import Registry

def run(pdf_paths: list[str], db_path: Path | str = "out/portfolio.db") -> int:
    db_path = Path(db_path); db_path.parent.mkdir(parents=True, exist_ok=True)
    repo = SqliteRepository(db_path); repo.init_schema()
    registry = Registry()
    total = 0
    for p in pdf_paths:
        de = extract_pdf(p)
        repo.save_many(de.records); total += len(de.records)
        registry.add(de.company, de.review)
        print(f"{Path(p).name}: {len(de.records)} records")
    registry.finalize()
    for company in registry.companies():
        repo.upsert_company(company)
    if registry.review:
        with open(db_path.parent / "review_queue.jsonl", "w", encoding="utf-8") as f:
            for item in registry.review:
                f.write(item.model_dump_json() + "\n")
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
