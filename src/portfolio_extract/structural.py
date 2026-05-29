from __future__ import annotations
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import pdfplumber

@dataclass
class Cell:
    text: str; page: int; bbox: tuple[float, float, float, float] | None

@dataclass
class Page:
    number: int; text: str; unit_hint: Optional[str] = None
    cells: list[Cell] = field(default_factory=list)

def page_unit_hint(text: str) -> Optional[str]:
    low = text.lower()
    if "in thousands" in low or "($000" in low or "$000s" in low:
        return "in thousands"
    if "in millions" in low or re.search(r"\(\$?m\b", low) or "$m" in low:
        return "$M"
    if "gbp" in low:
        return "GBP"
    return None

def extract_structure(pdf_path: Path | str) -> list[Page]:
    pages: list[Page] = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            cells: list[Cell] = []
            for table in page.find_tables():
                for row in table.rows:
                    for cell_bbox in row.cells:
                        if cell_bbox is None:
                            continue
                        ctext = (page.within_bbox(cell_bbox).extract_text() or "").strip()
                        if ctext:
                            cells.append(Cell(text=ctext, page=i, bbox=tuple(cell_bbox)))
            pages.append(Page(number=i, text=text, unit_hint=page_unit_hint(text), cells=cells))
    return pages
