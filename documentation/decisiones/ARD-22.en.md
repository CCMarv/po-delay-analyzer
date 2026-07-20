# F4 Interface Rework Spec: Key Information by Person and Executable Checklist

* **Status:** 🔵 **DRAFT** (closed by the team — executed and verified by G7)
* **Technical Context:** Phase 4 — final rework of `04_app` (Streamlit); G6 unit of the closing orchestration, direct input from G7 (execution)
* **References:** Issue #130 (feedback post-redesign); [ADR-09](ARD-09.en.md) (`../user_personas.en.md`);
  [ARD-17](ARD-17.en.md) (visual language, unchanged); [ARD-21](ARD-21.en.md) (tier-1/tier-2 contract, source of the exposed fields); [ADR-10](ARD-10.en.md) (hybrid severity — not modified); Issue #197 (drill-down Ravi→Diego, already resolved, protected); PR #198 (error handling if `po_output.csv` is missing, already resolved); `04_app/app.py`, `04_app/pages/1_🔍_Exception_Workbench.py`,
  `04_app/pages/2_📊_Network_Intelligence.py`, `04_app/config.py`

## Context and Problem

`user_personas.md` ([ADR-09](ARD-09.en.md)) documents what each person needs, but it was written before the tier-1/tier-2 contract ([ARD-21](ARD-21.en.md)) existed — its table "what each person consumes" does not include the 8 tier-1 fields or the 9 tier-2 fields. The current app (verified in this unit, not assumed) already implements much of what the persons request: timeline with 7 events, stage/severity/confidence badges, tier-2 hypothesis panel, bar charts (not pie: the prohibition from [ARD-17](ARD-17.en.md) against pie/donut/3D/SHAP/OTIF is already met in the code). There are 2 actual gaps of information remaining and a set of UI/UX tasks grouped in issue #130, without individual nominal attribution on GitHub.

Additionally, G3 (previous unit, closed on 2026-07-19, PR #200) has already decided to document the divergence of LLM-vs-rule severity without exposing dual severity in the UI. This spec does not reopen that decision.

## Considered Options

**Option A — Execute only the literal checklist from #130.** Pros: minimal scope, already drafted.  
Cons: 2 of the 3 actual gaps of information (`excess_*_hrs` unused, absent time trend) are not in #130 as it was written about the state of the app, not against the current data contract or the table of person consumption — they would remain unresolved even though the persons request them.

**Option B — Rebuild both views from scratch.** Pros: opportunity to clean all debt at once.  
Cons: the app is already organized by person (María, #101/#102/#103) and already meets ARD-17 and anti-contamination prohibitions; rebuilding from scratch discards correct work and unnecessarily expands G7's scope.

**Option C — Person-led rework: protect what already meets requirements, close the actual gaps of information, resolve the open decisions from #130, defer what does not apply today (chosen).** Audits the real code against what each person needs, distinguishes "already meets" from "real gap" from "cosmetic from #130", and leaves an explicit non-regression list.

## Decision

### 1. Diego (Exception Workbench) — key information and reasoning

Already protected (not modified in G7 except as listed in section 7):
- Timeline of 7 events with the assigned stage highlighted — primary evidence Diego uses to trust or distrust the diagnosis.
- Stage, severity, and confidence badges, plus the disagreement flag with `REASON_DSC` — prominent by design (ADR-09).
- Tier-2 differential diagnosis panel (main hypothesis + evidence + reasoning, alternate hypothesis + discriminant step, 3-step plan) when it exists; clear placeholder when not (tier-2 is opt-in via `--action-call`, ARD-21).
- Aggravating flags (`HOT_PO_FLAG`, `is_short_ship`).

Gap closed in this round: add the `excess_*_hrs` **of the assigned stage only**, explicitly labeled as excess over the expected window of that stage, not a component that adds to the total delay. Source: tier-1 (ARD-21, #158), already in the contract, currently without any representation in the UI. "Only the assigned stage" aligns with the hierarchy of a single cause per PO (ARD-02); displaying the 3 columns side by side would introduce noise of unassigned stages and the already documented risk of being read as waterfall (`excess_vendor_hrs` + `excess_carrier_hrs` + `excess_dc_hrs` do not sum to `delay_days_calc`).

### 2. Ravi (Network Intelligence) — key information and reasoning

Already protected (not modified in G7 except as listed in section 7):
- Distribution by stage and severity in stacked horizontal bar (already meets ARD-17; no pie/donut in the code) — the systemic pattern Ravi seeks before any individual case.
- Disagreement rate as a first-class KPI (maps to the mentor Reason Code Agreement threshold) — already implemented; format adjusted in section 3a.
- Executive cards and table of consolidated metrics by entity (Vendor/Carrier/DC): risk zone, score, analysis, action — the scorecard directing the report to the correct owner.
- Table of POs with disagreement + drill-down to Diego — already resolved by #197; the bridge "the case validates, the pattern decides" from ADR-09.

Gap closed in this round: time trend section over `PO_DT` — line with direct labeling, encoding that ARD-17 has already set for this task (it was never decided to add the section itself). Closes the step of documented activities of Ravi ("trend vs previous period"), which currently has no temporal view in the app.

### 3. Specific decisions resolved in this spec

a. **Disagreement rate: headline percentage + secondary absolute count** (e.g. "13.8% (34/247)"). The mentor asks to report Reason Code Agreement in %; the pattern "count + %" already exists in the severity KPI (`n_high`/`high_pct`) — it is reused.

b. **Consistency of severity color between the two views: already resolved by design.** ARD-17 centralizes coding in `config.py` (`severity_colors()`/`stage_colors()`); if both views invoke those helpers instead of loose hex values, consistency is automatic. G7 audits that this is the case (item R3), does not decide on a new palette.

c. **`excess_*_hrs` in Diego: only the assigned stage** (detail in section 1).

d. **Time trend in Ravi: added in this round** (detail in section 2).

### 4. Extended design system: typography, spacing, and density

ARD-17 set color, shape, and type of chart, but it did not cover data typography, spacing scale, or information density. This round closes that gap with executable decisions, without reopening ARD-17.

**Typography.** Two families with separate roles: the sans of the theme for prose, labels, and headlines; a monospaced type limited to tabular technical data — timestamps of the timeline, PO identifiers, hour counts (`excess_*_hrs`) and days (`delay_days_calc`) and the percentages of the KPIs. Reason: monospaced digits align by column (eases comparison and scanning figures, the principle of common position that ARD-17 already cites) and visually separates machine data from text written by the LLM. It does not apply to entity names or prose: there it would be noise.

**Spacing and density.** Density goal: the primary content of each view fits without vertical scrolling on a standard laptop — Diego: the 7 events of the timeline and the diagnostic panel; Ravi: the KPIs and distribution by stage. Parity rule: cards in the same row share height and padding (generalizes D1, does not treat as an isolated patch). A consistent spacing scale (multiples of a base unit) is adopted instead of loose values per card, so G7 does not reintroduce the inconsistency that #130 reports. No numerical tokens are fixed here: the scale is deployed in G7 with criteria, not as a closed spec.

**Provenance note.** Footer with the dataset cut-off date and its real origin: the artifact `po_output.csv` from Phase 3 (247 POs from a historical cut). External ingestion sources (ERP/live telemetry) that do not exist in the project are not cited — the app is retrospective over a cut, not a real-time feed.

**Design elements considered and rejected** (with their rationale; reinforce non-regression from section 6):
- "Validate diagnosis" button with "verified" status and audit log — introduces writing/persistence that the read-only architecture does not have; it remains outside this round (not discarded as a future idea, but requires deciding where to persist, a greater scope than the polishing of #130).
- "Export report to Slack/Telegram" drawer — Slack does not exist in the project and the Telegram bot (ARD-20) is of fixed read commands, not an export channel.
- "Last 30 days" sparkline by entity on the scorecards — the dataset is a historical cut, not a rolling feed; the aggregated trend (R1) already covers the temporal need without suggesting a moving window that the data does not support.
- Ishikawa/5-Whys, OTIF, predictive analytics, pie/donut and foreign domain taxonomy are already prohibited by ARD-17 and section 6; they are reiterated as criteria for G7.

### 5. Mapping of issue #130

| Item from #130 | Resolution |
|---|---|
| Height/padding of card "AI vs Human Validation" | Absorbed in G7 (D1, cosmetic) |
| Timeline without scroll on standard screens | Absorbed in G7 (D2, layout) |
| Tooltip on `llm_coincide_con_reason` | Absorbed in G7 (D3, copy in section 7) |
| Drill-down from disagreement table | Already resolved — issue #197, protected |
| Plotly legends with readable names | Absorbed in G7 (R4, cosmetic) |
| Temporal filter (date range) | Deferred — the item conditions it to "if the dataset grows"; with 247 POs it does not add value today |
| % vs absolute count for disagreement | Resolved in this spec (3a) |
| Consistency of severity color | Resolved in this spec (3b) — already guaranteed by ARD-17 |
| Error handling if `po_output.csv` is missing | Already resolved — G1, PR #198 |
| `print()`/debug logs | Verify in G7 if G2 (PR #199) has already covered it (R5) |
| Updated `requirements.txt` | Absorbed in G7 (R7) — no new dependencies expected |
| `styles.css` without orphan styles | Absorbed in G7 (R6) |

### 6. Information that must not be lost (non-regression, criteria for G7)

- Diego: timeline of 7 events with the highlighted segment; stage/severity/confidence badges; prominent disagreement flag with `REASON_DSC`; complete tier-2 panel (hypothesis + evidence + reasoning + alternate + discriminant + 3-step plan) with its placeholder when not present; `HOT_PO_FLAG`/`is_short_ship` flags; PO selector preselected by drill-down.
- Ravi: stacked horizontal bar by stage and severity; disagreement rate as a first-class KPI; executive cards and consolidated table by entity; disagreement table with drill-down to Diego.
- Cross-sectional: Okabe-Ito palette by stage, achromatic ramp + shape by severity, bucket badge for confidence (never raw number) — all from `config.py`, no loose hex values; zero pie/donut/treemap/3D; zero SHAP/OTIF/prediction; zero Ishikawa/5-Whys modal/quantile dotplots; zero writing/validation button with audit log (the app is read-only of the Phase 3 artifact); zero export to Slack/Telegram (Slack does not exist; the ARD-20 bot is for fixed read commands); zero mobile window sparkline by entity (the dataset is a historical cut); zero trilingual or foreign domain content (BOL, Carta Porte, Customs, LTL).

### 7. Executable checklist (direct input from G7)

**Diego — Exception Workbench:**
- D1. Match height/padding of the "AI vs Human Validation" card with the Stage/Severity cards.
- D2. Compress the spacing of the horizontal timeline so that the 7 timestamps fit without scrolling on standard screens.
- D3. Add tooltip/contextual help on `llm_coincide_con_reason` (suggested copy: "Compares LLM's diagnosis against the cause noted by the human in REASON_DSC. A disagreement is a finding to review, not necessarily an error from the LLM.").
- D4. Add the `excess_*_hrs` of the assigned stage, explicitly labeled as excess for that stage (not as a component that adds to the total delay).
- D5. Audit that the confidence badge implements the 3 buckets of ARD-17 (High/Medium/Low); correct if it shows the raw number.
- D6. Remove `04_app/utils/helpers.py` (dead code: no imports in the app, refers to columns from a previous contract that no longer exist).

**Ravi — Network Intelligence:**
- R1. Add time trend section over `PO_DT` (line with direct labeling, ARD-17 encoding); granularity week/month according to data density.
- R2. Disagreement rate: format "% headline + secondary count" (section 3a).
- R3. Audit that both views consume `severity_colors()`/`stage_colors()` from `config.py` without hardcoded hex values.
- R4. Readability of legends for the 2 `px.bar`: names capitalized ("Vendor" instead of "vendor").
- R5. Check if `print()`/debug logs were covered by G2 (PR #199); clean if not.
- R6. Verify `assets/styles.css` without orphan styles from the old entity views.
- R7. Confirm that no new dependencies are needed in `requirements.txt`.

**Cross-sectional — extended design system:**
- T1. Define the monospaced family in the theme/`config.py` and apply it only to timestamps, PO IDs, hours/days, and percentages; the rest remains in the sans of the theme.
- T2. Apply the spacing scale and parity of cards per row (absorbs D1) and confirm the density without scrolling on standard screen (absorbs D2).
- T3. Add provenance footer (cut-off date + source `po_output.csv`), without invented ingestion sources.

**Outside this round (deferred, with reason):**
- Interactive temporal filter — small dataset (247 POs) does not warrant it today.
- Correction of `03_llm_integration/README.md` (contract 16/33 outdated) — documentary synchronization for G8, not G7.
- Hardening the regex parser of `agente1_raw.txt` — known fragility, not blocking for this round; the content it produces is protected (section 6).

## Consequences

**Positive:**
- G7 receives an executable checklist without pending design decisions.
- Resolves the 2 open decisions from #130 without leaving them for G7 to improvise.
- Closes 2 actual gaps of information against the current tier-1 contract (ARD-21) and Ravi's persona (ADR-09), which #130 did not cover as it was written before those documents.
- Closes the gap ARD-17 left in typography, spacing, density, and provenance, and documents as design guardrails the rejected generic elements (writing validation, Slack/Telegram export, mobile window sparkline).
- The explicit non-regression list reduces the risk of G7 breaking the tier-2 panel or already met anti-contamination prohibitions when touching CSS/layout.

**Negative:**
- The temporal filter and synchronization of `03_llm_integration/README.md` remain outside — dependent on the dataset growing or G8 executing.
- The fragility of the regex parser of `agente1_raw.txt` is not resolved here.

## Relation to Other Decisions

Uses [ADR-09](ARD-09.en.md) (personas, extends its consumption table with tier-1/tier-2), [ARD-17](ARD-17.en.md) (visual language — unchanged), [ARD-21](ARD-21.en.md) (tier-1/tier-2 contract — source of `excess_*_hrs`), [ADR-10](ARD-10.en.md) (hybrid severity — not touched; G3's decision not to expose dual severity in UI remains confirmed, not reopened). Section 4 extends [ARD-17](ARD-17.en.md) towards typography/spacing/density without reopening its color rules or chart types. Maps issue #130 point by point (section 5). Protects the resolution of issue #197 (drill-down) and the handling of missing data errors (PR #198). It serves as direct input for G7 (execution) and leaves explicit pending synchronization of `03_llm_integration/README.md` for G8.