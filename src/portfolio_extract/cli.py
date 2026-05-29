from __future__ import annotations
import sys
from pathlib import Path
from portfolio_extract.pipeline import extract_pdf
from portfolio_extract.repository import SqliteRepository

def run(pdf_paths: list[str], db_path: Path | str = "out/portfolio.db") -> int:
    db_path = Path(db_path); db_path.parent.mkdir(parents=True, exist_ok=True)
    repo = SqliteRepository(db_path); repo.init_schema()
    total = 0
    for p in pdf_paths:
        records = extract_pdf(p); repo.save_many(records); total += len(records)
        print(f"{Path(p).name}: {len(records)} records")
    return total

def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("usage: portfolio-extract <pdf> [<pdf> ...]"); raise SystemExit(2)
    print(f"Total: {run(args)} records")

if __name__ == "__main__":
    main()
