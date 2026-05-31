# Portfolio Metrics — Glossary

Canonical metric vocabulary for the portfolio-company reporting extraction. Each company labels metrics its own way; this fixes the canonical term, what it means, which reported labels map to it, and which look-alike labels must NOT. It is a glossary of meaning, not a description of extraction mechanics.

Convention ("normalize-and-disclose"): comparability comes from mapping every company's label to one canonical metric while preserving the company's own label (`label_as_reported`) and the basis it was reported on. Compare on the normalized figure; stay honest by never hiding the basis. Currency is stored native, never converted at extraction.

## Language

**Revenue** (`revenue_quarterly`):
The company's total recognized revenue for the quarter, on its own reported basis. One comparable top-line figure across business models.
_Maps_: Recognized Revenue, Quarterly Revenue, Quarterly Revenue (recognized), Net Revenue, Platform Revenue (recognized), Gross Transaction Revenue (marketplace net fees), Total Recognized Revenue (composite total), Revenue.
_Map with care_: "Total Billings" — normally billings ≠ revenue (invoiced vs recognized), but NovaCloud footnotes it as ASC 606 recognized revenue. Map only when the source explicitly equates it to recognized revenue; keep the label and a note.
_Never_: GMV / Gross Transaction **Value**, Total Loan Book (balance-sheet asset), ACV / pipeline value, volume counts (shipments, emission records, candidate profiles). These are volume or balance, not revenue.
_Precedence_: when a component line and a total line coexist, the **total wins** as canonical (ApexFreight Total Recognized Revenue over transaction-only).
_Basis varies by sector_ (preserve in note): SaaS = recognized subscription/services; Marketplace = net transaction fees (the take, not GMV); Lending = interest income + fees.

**ARR** (`arr`):
Annual recurring revenue at period end, on the company's reported basis.
_Maps_: Annual Recurring Revenue, Contracted ARR, Contracted Annual Recurring Revenue, Subscription ARR, End-of-Period ARR, ARR (End of Period), ARR.
_Basis note_: "Contracted" (signed active contracts) vs run-rate (MRR×12) differ slightly; in this corpus every disclosed basis is contracted, none state explicit run-rate. Preserve the label.
_Never_ (separate derived metrics, out of core set): ARR Growth (YoY), Expansion ARR as % of Total, ARR from Existing Accounts, ARR per Full-Time Employee.
_Applicability_: `not_applicable` for lending and PURE marketplace; applicable to SaaS and to hybrid (marketplace plus recurring SaaS).

**Net Revenue Retention** (`net_revenue_retention`):
LTM revenue retained from the existing customer base including expansion (upsell/cross-sell), net of churn and contraction.
_Maps_: Net Revenue Retention, Net Dollar Retention, Net Pound Retention (NPR), NRR, NDR. NDR == NRR == NPR — the latter are currency relabels (NPR = GBP), footnote-confirmed.
_Do not conflate with_: Gross Revenue Retention (excludes expansion) or Logo Churn (count basis).
_Applicability_: `not_applicable` for lending and pure marketplace; applicable to SaaS and hybrid.

**Gross Revenue Retention** (`gross_revenue_retention`):
LTM revenue retained from the existing base EXCLUDING expansion — a floor metric, normally capped near 100%.
_Maps_: Gross Revenue Retention, GRR.
_Distinct from NRR_: TalentVault reports both in one table (GRR 91%, NRR 119%); the spread is the expansion contribution. Never merge.
_Applicability_: `not_applicable` for lending and pure marketplace; applicable to SaaS and hybrid.

**Logo Churn** (`logo_churn`):
Share of customer logos (accounts) lost over the period — a count basis, not revenue. Not 1 − NRR.
_Maps_: Logo Churn, Annual Logo Churn, Logo Churn Rate (LTM).
_Applicability_: `not_applicable` for lending and pure marketplace; applicable to SaaS and hybrid.

**Headcount** (`headcount`):
People employed at period end.
_Maps_: Total Headcount, Headcount, FTE. (FTE == headcount here: NovaCloud "FTE 142" == "Total Headcount 142".)
_Note_: sometimes disclosed only in prose, not a table (FleetLink "199 employees", "not tabled this quarter") — same metric, different extraction path.

**Cash Balance** (`cash_balance`):
Freely available operating cash at period end.
_Maps_: Cash Balance, Cash, Cash & Equivalents.
_Exclude_: restricted / segregated client float (not freely-available liquidity) — prefer the operating-cash figure; capture any restricted portion separately or flag.

**Net Burn** (`net_burn_monthly`):
Monthly net cash outflow.
_Maps_: Monthly Net Burn, Monthly Cash Burn, Net Burn (monthly); also "Quarterly Net Burn" where the value is actually monthly.
_Periodicity_: do NOT trust the period word in the label. Verify actual periodicity via runway = cash ÷ burn against the company's stated runway. Record the as-reported label.
_Note_: typically excludes non-cash stock-based compensation (footnoted).

**EBITDA** (`ebitda`):
Standard earnings before interest, tax, depreciation, amortization.
_Status_: not reported by any company in the dev set. The recognizer is retained — the held-out PDFs were not inspected (it may appear there), and absence is itself a reportable finding.

**Gross Margin** (`gross_margin`):
Revenue minus direct cost of delivery, as a percentage — a true gross margin for SaaS (customer-success/implementation scope debated) and Marketplace (post-carrier contribution basis).
_Lending is NOT a gross margin_: a lender's "Gross Margin" (interest income net of cost of funds) is a net-interest-spread / NIM construct — different numerator and denominator. It shares the field keyed to the company's self-label but carries `basis = net_interest_spread` and stands as its own series.
_Maps_: Gross Margin.
_Basis_ (machine-readable, gates comparison): `saas_cogs` / `marketplace_contribution` / `net_interest_spread`.
_Comparability_: within-company-over-time always valid; SaaS↔marketplace cross-sector valid with care; lending GM never aggregated or compared with the others — enforced by the basis enum, not a UI flag.

## Flagged ambiguities

- **Gross Margin** — extracted with a machine-readable `basis` enum; lending GM is a net-interest-spread construct (not a true gross margin) and is never compared cross-sector; SaaS↔marketplace comparable with care; within-company-over-time always valid.
- **Restatement vs rename** — store each source's as-reported value faithfully (Q1 PDF keeps 4.7M; the Q2 restatement of 4.6M is a separate record); reconcile at the view layer, preferring the latest restated value with an original + restatement flag. Distinct from a label rename across quarters, which alias resolution handles.
- **Currency** — not all USD (PeopleFlow = GBP, with EUR contracts). Detect and store native; never convert at extraction.
- **Revenue precedence & Total Billings** — see the Revenue entry.

## Example dialogue

Analyst: "NovaCloud's ARR is 34.2 — comparable to TalentVault's 22.4?"
Engineer: "Both map to `arr` at period end. NovaCloud labels it 'ARR (End of Period)', TalentVault 'Contracted ARR'. We keep both labels; the figure is comparable."
Analyst: "TalentVault shows retention of 91% and 119% — which is it?"
Engineer: "Two different metrics. 119% is Net Revenue Retention (includes expansion); 91% is Gross Revenue Retention (excludes it). Never merged — the 28-point gap is expansion."
Analyst: "PeopleFlow reports 'Net Pound Retention' — a different metric?"
Engineer: "Same metric, relabeled because they report in GBP. Maps to `net_revenue_retention`."
