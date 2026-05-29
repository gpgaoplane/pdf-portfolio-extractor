# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project context

Interview tech case study for Sagard (Forward Deployed Engineer). Spec lives in `Forward Deployed Engineer (FDE) - Tech Case Study.pdf` at the repo root — read it before making design decisions.

**Goal:** proof-of-concept that ingests a folder of portfolio-company PDF reporting packages and extracts a chosen subset of metrics into a comparable structure, with a small front-end for the demo.

**Deliverables expected by the case:**
- GitHub repo + README with run instructions
- Slide deck (business-focused: problem, prototype, roadmap)
- Live demo with a front-end displaying extracted metrics and 1–2 cross-company / cross-period insights

**Explicitly out of scope per the spec:** handling every edge case, every PDF perfectly, or every possible metric. The case is judging how ambiguity is navigated and how the solution is structured — not coverage.

**Time horizon:** No fixed deadline (user instruction, 2026-05-29 — the earlier ~5-day framing is deleted). Prioritize quality, proper architecture, a real eval methodology, and a polished demo over speed. Do not pace against any day count or raise timeline pressure. Foundation-first is the working style (see project memory). Still avoid gold-plating into needless production territory — lean POC that embodies the scalable pattern, with the production target articulated in the roadmap.

## Input data

24 PDFs in `data/`, naming pattern `{Company}_{Quarter}_{Year}.pdf` (e.g. `LendBridge_Q2_2025.pdf`). Some companies appear across multiple quarters (LendBridge, NovaCloud, MediSight, FleetLink, PeopleFlow) — useful for time-series insights. One `Portfolio_Snapshot_Q2_2025.pdf` is a different shape (portfolio-level rather than single-company).

The spec notes each company structures and labels reports differently — extraction logic must tolerate label variance (e.g. "Revenue" vs "Total Revenue" vs "Net Sales"), unit variance ($M vs $K vs raw), and missing metrics per report.

## Traceability requirement

The spec calls out: stakeholders need to *trust the numbers and trace them back to source documents*. Any extraction output should carry source provenance (file, page, ideally the surrounding text or bbox). This is a first-class requirement, not a nice-to-have.

## Layer hierarchy

Where each rule or piece of context lives:

1. **This `CLAUDE.md`** — project-wide framing and pointers. Auto-loaded.
2. **`.claude/rules/*.md`** — topical rule files. Loaded by topic; routed from the table below.
3. **`.claude/settings.json`** — mechanical permissions; the engine enforces these before any tool call.
4. **`docs/spec.md`** — living build spec, drafted during brainstorm; change-controlled (surface changes for approval before editing, never silently).
5. **Project memory** at `~/.claude/projects/D--Projects-interview-projects-pdf-extractor/memory/` — cross-session memory; accrues organically.

When a rule applies project-wide → CLAUDE.md or a rule file. When it's a spec-level fact about what's being built → `docs/spec.md`. When it must be guaranteed (not just remembered) → `settings.json` permissions. When it survives sessions → project memory.

## Routing table

| Concern | Location | Purpose |
|---|---|---|
| Mechanical enforcement (allow/deny) | `.claude/settings.json` | Engine-enforced permissions for shell commands |
| External-facing writing style | `.claude/rules/writing-style.md` | Style for slide deck, README, demo copy, commit messages |
| Skill routing during conversation | `.claude/rules/skill-routing.md` | When to proactively surface skills; failure modes to avoid |
| Domain-vocabulary alignment skill | `.claude/skills/grill-with-docs/` | One-question-at-a-time grilling for metric schema and ambiguity disambiguation |
| Domain glossary | `CONTEXT.md` (TBD, repo root) | Canonical terms — metric names, what each means, which labels to prefer over which. Created lazily by `grill-with-docs`. |
| Architecture decisions | `docs/adr/` (TBD) | Sparingly used; gated by hard-to-reverse + surprising + real-tradeoff |
| Case study brief | `Forward Deployed Engineer (FDE) - Tech Case Study.pdf` | The source spec the build is judged against |
| Source PDFs | `data/` | 24 portfolio-company reports to extract from |
| Living build spec | `docs/spec.md` | Chosen metrics, recognition heuristics, traceability schema, success criteria. Living, not frozen; changes surfaced for approval before editing. |
| Decisions log | `docs/DECISIONS.md` | Single chronological log of every decision: context, options, choice, rationale, tradeoffs. Maintained as decisions lock. |
| Session handoff | `docs/handoff/` | Per-session state captures (status, recon findings, pending decisions, resume instructions). |
| Research synthesis | `docs/research/` | Web research synthesis documents for load-bearing decisions (Q3 extraction approach, etc.). |
| Project memory | `~/.claude/projects/D--Projects-interview-projects-pdf-extractor/memory/` | Cross-session memory; accrues organically |

## Framework critique is required, not optional

This `CLAUDE.md`, the rule files, and any future `docs/spec.md` are tools, not a contract. If a rule contradicts what the project actually needs as the work progresses, name the mismatch, propose a better option, and wait for approval before working around it. Don't silently substitute. Disagreement done well beats agreement done politely.

How to apply:
- If a rule says X but the situation needs Y, surface the mismatch first.
- If something in `CLAUDE.md` is wrong or outdated, propose an edit rather than ignoring it.
- If a recurring gap shows up, name it as a candidate for a new rule file or a project-memory entry.

**Internal trigger sentence:** if you find yourself thinking "the rule says X but I'll do Y because it's better," that's the moment to surface, not bury. The substitution-without-flagging is the actual failure mode this section exists to prevent.

## Status

Brainstorm complete (2026-05-29). Foundation + design locked: `CLAUDE.md`, `.claude/` (settings, rules, grill-with-docs skill), `CONTEXT.md` (metric glossary), `docs/spec.md` (frozen build spec), `docs/DECISIONS.md` (D-001..D-018), `docs/research/` (extraction-approach + scalability syntheses), `docs/handoff/`. Next: implementation plan (writing-plans), then build. No code yet.

When code and structure exist, this section should describe:
- Language / runtime and how to install deps
- How to run the extraction pipeline against `data/`
- How to launch the front-end / demo
- How to run tests (and a single test)
- High-level architecture (ingestion → extraction → normalization → storage → UI → eval)
