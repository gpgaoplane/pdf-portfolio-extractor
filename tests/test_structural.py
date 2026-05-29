from portfolio_extract.structural import extract_structure, page_unit_hint

def test_extracts_text_and_cells(data_dir):
    pages = extract_structure(data_dir / "NovaCloud_Q2_2025.pdf")
    assert len(pages) >= 1
    assert "Recognized Revenue" in " ".join(p.text for p in pages)
    cells = [c for p in pages for c in p.cells]
    assert any(c.text and c.bbox for c in cells)

def test_unit_hint_detection():
    assert page_unit_hint("Metric (GBP unless noted)") == "GBP"
    assert page_unit_hint("All figures in thousands") == "in thousands"
    assert page_unit_hint("nothing here") is None
