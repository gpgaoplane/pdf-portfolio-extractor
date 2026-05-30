from __future__ import annotations
import sqlite3
from contextlib import closing
from pathlib import Path
from typing import Protocol
from portfolio_extract.models import ExtractionRecord
from portfolio_extract.registry import CompanyRecord

class Repository(Protocol):
    def init_schema(self) -> None: ...
    def save_many(self, records: list[ExtractionRecord]) -> None: ...
    def query(self, **filters) -> list[ExtractionRecord]: ...
    def upsert_company(self, rec) -> None: ...
    def get_company(self, canonical_name: str): ...
    def list_companies(self) -> list: ...

class SqliteRepository:
    def __init__(self, db_path: Path | str):
        self.db_path = str(db_path)

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path); c.row_factory = sqlite3.Row
        return c

    def init_schema(self) -> None:
        with closing(self._conn()) as c:
            c.execute("""CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT, period_year INTEGER,
                period_quarter TEXT, metric TEXT, source_file TEXT, payload TEXT)""")
            c.execute("""CREATE TABLE IF NOT EXISTS companies (
                canonical_name TEXT PRIMARY KEY, sector TEXT, payload TEXT)""")
            c.commit()

    def save_many(self, records: list[ExtractionRecord]) -> None:
        with closing(self._conn()) as c:
            c.executemany(
                "INSERT INTO records (company, period_year, period_quarter, metric, source_file, payload)"
                " VALUES (?,?,?,?,?,?)",
                [(r.company, r.period_year, r.period_quarter, r.metric.value, r.source_file,
                  r.model_dump_json()) for r in records])
            c.commit()

    def query(self, **filters) -> list[ExtractionRecord]:
        clause = " AND ".join(f"{k}=?" for k in filters) or "1=1"
        with closing(self._conn()) as c:
            rows = c.execute(f"SELECT payload FROM records WHERE {clause}",
                             tuple(filters.values())).fetchall()
        return [ExtractionRecord.model_validate_json(r["payload"]) for r in rows]

    def upsert_company(self, rec: CompanyRecord) -> None:
        with closing(self._conn()) as c:
            c.execute("INSERT OR REPLACE INTO companies (canonical_name, sector, payload) VALUES (?,?,?)",
                      (rec.canonical_name, rec.sector.value, rec.model_dump_json()))
            c.commit()

    def get_company(self, canonical_name: str) -> CompanyRecord | None:
        with closing(self._conn()) as c:
            row = c.execute("SELECT payload FROM companies WHERE canonical_name=?",
                            (canonical_name,)).fetchone()
        return CompanyRecord.model_validate_json(row["payload"]) if row else None

    def list_companies(self) -> list[CompanyRecord]:
        with closing(self._conn()) as c:
            rows = c.execute("SELECT payload FROM companies").fetchall()
        return [CompanyRecord.model_validate_json(r["payload"]) for r in rows]
