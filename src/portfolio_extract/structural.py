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

def render_page_png(pdf_path, page_number: int, bbox=None, resolution: int = 110) -> bytes:
    import io
    with pdfplumber.open(pdf_path) as pdf:
        page = pdf.pages[page_number - 1]   # 1-indexed
        im = page.to_image(resolution=resolution)
        if bbox is not None:
            im.draw_rect(tuple(bbox), stroke="#0E6E6E", stroke_width=3, fill=None)
        buf = io.BytesIO(); im.save(buf, format="PNG")
        return buf.getvalue()
