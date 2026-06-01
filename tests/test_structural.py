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

def test_render_page_png_returns_png_bytes(data_dir):
    from portfolio_extract.structural import render_page_png
    png = render_page_png(data_dir / "NovaCloud_Q2_2025.pdf", 1, bbox=(40, 80, 300, 100))
    assert isinstance(png, bytes) and png[:8] == b"\x89PNG\r\n\x1a\n"   # PNG magic
    png2 = render_page_png(data_dir / "NovaCloud_Q2_2025.pdf", 1, bbox=None)  # no box, still renders
    assert png2[:8] == b"\x89PNG\r\n\x1a\n"
