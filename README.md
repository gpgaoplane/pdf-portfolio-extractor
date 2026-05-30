# Portfolio Metrics Extraction

Extracts a core set of reporting metrics from portfolio-company PDF packages into a single comparable table, with every number traceable back to the page and cell it came from.

## The problem

Portfolio companies each report in their own format and vocabulary. One calls it "Recognized Revenue", another "Quarterly Revenue", a marketplace calls its top line "Gross Transaction Revenue", a lender reports "interest income". Headcount shows up as "FTE", "Total Headcount", or "Headcount". Units shift between $M, $K, and raw counts, and some companies report in GBP. Pulling these into one comparable view by hand is slow and error-prone, and the numbers are hard to trust without tracing each one back to its source.

This prototype automates the first part of that work and keeps the trace.

## What it does

Point it at a folder of PDF reports. For each one it extracts the universal-core metrics, normalizes them into a comparable form, checks each value against the source, and stores it with full provenance. This first iteration covers the metrics every company reports:

- Revenue (quarterly, recognized)
- Gross Margin
- Headcount
- Reporting period

The canonical names and the label variants they map to are documented in `CONTEXT.md`. Metrics that only some companies report (ARR, retention, cash, burn) and the cross-company comparison view are the next iteration; see [Scope](#scope-and-limitations).

## How it works

The pipeline has four stages, each leaving a trail:

1. **Structural read.** `pdfplumber` pulls the text and table cells from each page, keeping each cell's bounding box.
2. **Extraction.** The page text goes to an LLM through [Instructor](https://python.useinstructor.com/), which returns each metric with its value as printed, the company's own label, the page, and the surrounding text. Any OpenAI-compatible endpoint works; the included example uses DeepSeek on Alibaba Cloud Model Studio.
3. **Normalize and verify.** Each value is resolved to a canonical unit based on the metric (so a bare "8400" in a thousands column becomes 8.4 in millions, while "142" stays a headcount), then cross-checked against the table cells. A value that matches a real cell is marked verified and carries that cell's bounding box.
4. **Score and store.** Each value gets a confidence tier and score from how it was found and verified, then is written to SQLite. Nothing is stored without its file, page, label, snippet, and confidence.

A value the model returns but cannot be matched in the source is flagged rather than trusted, which keeps hallucinated numbers out of the comparable view.

## Running it

Requires Python 3.11 or newer.

```bash
# install
python -m venv .venv
.venv/Scripts/pip install -e ".[dev]"      # Windows; use .venv/bin/pip on macOS/Linux

# configure the LLM endpoint
cp .env.example .env                         # then edit .env and set LLM_API_KEY
```

`.env.example` is set up for DeepSeek on Model Studio. Any OpenAI-compatible endpoint works: set `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`, and `LLM_MODE` (`TOOLS` for function-calling models, `JSON` otherwise). For DeepSeek's hybrid-thinking models, keep `LLM_ENABLE_THINKING=false` so structured output works.

```bash
# extract a folder of reports into a SQLite database
.venv/Scripts/portfolio-extract data/NovaCloud_Q2_2025.pdf data/MediSight_Q2_2025.pdf

# run the test suite (no API key needed; the LLM is mocked)
.venv/Scripts/pytest -q
```

Each run prints a per-file record count and writes to `out/portfolio.db`. The records are plain rows you can query:

```python
from portfolio_extract.repository import SqliteRepository
rows = SqliteRepository("out/portfolio.db").query(company="NovaCloud Analytics Inc.")
for r in rows:
    print(r.metric.value, r.value, r.canonical_unit.value, r.confidence_tier.value)
```

## What the output looks like

Running across two companies produces a comparable, traceable set:

| Company | Revenue ($M) | Gross Margin | Headcount |
|---|---|---|---|
| NovaCloud | 8.4 | 78% | 142 |
| MediSight | 6.8 | 77% | 121 |

Each cell behind these numbers carries the source file, page, the label as the company wrote it, the surrounding text, a confidence tier, and (where verified against a table) the bounding box on the page.

## Scope and limitations

This is a focused first iteration, built to prove the approach end to end rather than to cover everything:

- It extracts the universal-core metrics above. The where-applicable metrics (ARR, net and gross revenue retention, logo churn, cash, net burn, EBITDA), the per-company sector tag, restatement handling across quarters, company-identity tracking across rebrands, the full cross-company and cross-period comparison view, and a formal accuracy evaluation are the next iteration. The design already accounts for them.
- Extraction quality depends on the chosen LLM. Verification against the source catches values that do not match a real cell, but it confirms that a number appears on the page, not yet that it sits next to the right label.
- Unit and scale resolution is handled defensively. The sample reports mostly carry explicit unit suffixes, so the thousands-versus-millions path is exercised by tests more than by this corpus.
- Currency is detected and stored as reported, never silently converted. Cross-currency comparison is left to a later iteration.

## Layout

```
src/portfolio_extract/   extraction pipeline (structural, LLM, normalize, verify, score, store, CLI)
tests/                   test suite
data/                    sample portfolio-company PDF reports
CONTEXT.md               metric glossary: canonical names, label variants, what maps to what
```
