# Final Presentation — Outline and Script (EN)

This document is the content source for the final colloquium presentation (mentor
deliverable [1], issue #106). It is not a `.pptx` file: it is the slide-by-slide outline
—title, content, and speaker notes— used to build the slides in PowerPoint. It is derived
from the approved Spanish source, `presentacion-final.md`; if the two ever disagree, the
Spanish version governs (ARD-18). It extends `documentation/PO_Delay_Analyzer_v1.pptx`
(commit `abe35e2`, 9 slides, Spanish only): it keeps its skeleton and executive framing, and
adds what was missing against the evaluation rubric and the mentor's demo requirement. The
demo script lives separately in `guion-demo.en.md`.

Every figure cited below traces to an already-versioned artifact —
`documentation/explicacion-proyecto.en.md`, `documentation/metricas-proyecto.en.md`,
`documentation/validacion-y-qa.en.md`, `documentation/hallazgos-ai-vs-humano.en.md`,
`03_llm_integration/mismatches_ai_vs_humano.md`— or the real deliverable CSV
(`data/processed/po_output.csv`). No figure is recalculated or invented here. Note: the
per-PO LLM outputs shown live in the app (explanation, action, hypothesis) stay in Spanish
regardless of presentation language — that scope decision is already in force (ADR-18) and
is not reopened here.

## Audit of v1 against the rubric and the demo requirement

v1 has 9 slides: Cover, Agenda, Summary, Problem, Solution (decoupled architecture), Diego
View, Ravi View, Telegram Integration, Conclusions. It carries no speaker notes. It cites a
single validation figure —"88% agreement rate"— on the Conclusions slide.

| Criterion (weight) | Coverage in v1 |
|---|---|
| Data Ingestion & Pipeline Quality (10%) | Absent. No mention of dataset volume (400 POs, 39 columns), cleaning, quality flags, or cross-validation. |
| Delay Taxonomy & Rule-Based Classification (20%, the highest weight) | Weak. The Problem slide names the symptom (~20% human inconsistency) but never explains the four stages, the thresholds, or the resulting distribution. The highest-weighted criterion is the worst covered. |
| LLM Integration & Prompt Engineering (10%) | Partial. The Solution slide summarizes in one sentence that "the LLM interprets the diagnosis"; no mention of few-shot, temperature, or the output schema. |
| Explanation & Recommendation Quality (10%) | Partial. The Diego View slide describes root cause and action qualitatively; missing the quality benchmark figure (5/5, 20/20). |
| Validation & Analytical Rigor (10%) | Weak. Only reason agreement (88%) appears; missing the two other metrics that also clear their threshold —stage accuracy 100% against >80%, severity ranking 100% against >95%. |
| Demo / Application Usability (10%) | Absent. The Diego View and Ravi View slides describe the screens statically; there is no script for "select a PO and watch the explanation live," which is the kickoff's literal mandate (slide 10 of `kickoff_po_root_cause.html`: "Slides + demo: select a delayed PO and see the AI's explanation live"). |
| Business Relevance & Stakeholder Insight (5%) | Covered. The Diego View and Ravi View slides map to the two usage profiles, though they do not name the formal user-personas exercise behind them. |
| Communication & Documentation (10%) | Weak. The deck is monolingual (the rubric calls for a mixed audience); it does not reference the formal documentation already versioned (SRS, SAD, ADRs). |
| Collaboration & Professionalism (10%) | Not addressable through slide content. This criterion is assessed through team process and behavior, not deck content; no added slide covers it, and this is stated explicitly rather than faking coverage. |
| Innovation & Insight (5%) | Covered. The Problem slide claims cognitive auditing with LLMs as the innovation, and Conclusions closes with "data-driven decisions, not perceptions." The project's central thesis —that the computation corrects the human annotation— appears, but only in one sentence. |

## Choice of demo case: PO #100236

The live demo script (`guion-demo.en.md`) needs a concrete PO that shows a mismatch between
the computation and the human annotation — the DoD of #106 explicitly asks for "a mismatch
case that showcases the thesis." Rather than picking a fresh, unreviewed PO, the demo reuses
one of the eight mismatches already narrated and versioned in
`03_llm_integration/mismatches_ai_vs_humano.md` (an input of
`documentation/hallazgos-ai-vs-humano.en.md`, the project's central evidence for its thesis).

PO #100236: the computed stage is Vendor (BIOPLEX), with a 94.5-hour excess over the
appointment-approval threshold. The DC staff's `REASON_DSC` reads "Equipment/trailer issue"
— blaming the visible link — while the appointment approval had already arrived late before
that. It is one of the three Vendor cases in the "visible link" pattern documented as the
project's central evidence. In addition: `HOT_PO_FLAG=1`, severity HIGH, LLM confidence 0.85,
and a complete tier-2 differential diagnosis in the real CSV — hypothesis, evidence,
alternate hypothesis, discriminant step, and a 3-step plan —, verified without spending any
API against `data/processed/po_output.csv`. It also appears in the "POs with AI vs. Human
Disagreement" table in the Ravi view, which allows a single continuous demo flow (Ravi →
drill-down → Diego) with no lost clicks.

Reusing an already-narrated case instead of introducing a new one keeps the evidence
consistent across the findings, the documented mismatches, and the live demo.

## Note on the two "disagreement" figures (do not conflate in the script)

The project reports two distinct figures under the idea of "disagreement with the human,"
and the presentation and demo script cite them separately so they are not conflated:

- **Reason agreement (the canonical figure, with a mentor threshold):** 88.8% (174/196).
  Computed by `metrics_core.py` in Phase 2, comparing `stage_primary` (the computation)
  against `reason_group_manual` (a curated grouping of `REASON_DSC`). This is the figure
  cited on the Validation & Metrics slide.
- **The "AI Disagreement Rate" KPI seen live in the Ravi view:** currently 38.5% (95/247,
  verified against the real CSV). This is `llm_coincide_con_reason`, a binary judgment the
  LLM itself emits per PO while drafting its explanation — one of the five fields of the
  JSON produced by Phase 3 — not the same computation as the figure above. It is correlated
  with the canonical figure, but not interchangeable with it.

The Validation & Metrics slide cites only the first figure. The demo script, when passing
through the Ravi KPI, clarifies in one sentence that the number on screen measures something
related but distinct.

## Slide outline

Convention: **[kept]** = v1 content unchanged in substance · **[expanded]** = v1 slide with
added content · **[new]**. The bullets are the content to carry onto the slide; the speaker
notes are context for the presenter, not for the screen.

### 1. Cover — [kept]

Unchanged: "PO Delay Root Cause Analyzer / An Executive Approach".

### 2. Agenda — [expanded]

1. Summary
2. Problem
3. Solution: decoupled architecture
4. Taxonomy and classification rules
5. Diego View: individual exception management
6. Ravi View: network intelligence
7. Live demo
8. Telegram integration
9. Validation and metrics
10. Conclusions

### 3. Project Summary — [expanded]

- The PO Delay Root Cause Analyzer is a retrospective audit system that identifies,
  classifies, and explains delays in purchase orders (POs).
- Dataset: 400 POs, 39 columns; 247 turn out to be late and are the population the system
  explains.
- Life-cycle timestamps are the source of truth, not human annotation (`REASON_DSC`): the
  mentor reports that annotation is ~20% incorrect.
- Data quality without dropping rows: 361 fully reliable POs and 39 isolated with flags (12
  temporal inversions + 27 without trailer time).

Speaker notes: the source-of-truth point is the thesis that carries the whole project; it is
worth stating it slowly here, since the rest of the presentation takes it as established.

Source: `documentation/explicacion-proyecto.en.md` (Executive Summary, Phase 1).

### 4. Problem — [kept]

Unchanged: who is at fault and what it implies operationally; noisy data (~20% human
inconsistency); LLMs over raw data generate generic narratives.

### 5. Solution: Decoupled Architecture — [expanded]

- Four-phase architecture that separates statistics from narrative analysis: statistics
  establish the numerical "ground truth"; the LLM acts as the analyst who interprets the
  diagnosis.
- The LLM interprets, it does not recalculate: the prompt explicitly forbids recalculating
  dates or hours and inventing figures, and requires citing the figures it is given verbatim.
- Production configuration: few-shot with 3 examples (one per attributable stage: Vendor,
  Carrier, DC), temperature 0.9, official backend `gpt-4o-mini`.
- Structured output: a 5-key JSON (root cause, recommended action, severity, whether it
  matches the reason code, confidence).

Speaker notes: emphasize the division of labor —rules do all the arithmetic, the LLM only
drafts prose over an already-resolved diagnosis— because that is what makes the explanation
auditable.

Source: `documentation/explicacion-proyecto.en.md` (Phase 3, Per-PO Surface).

### 6. Taxonomy and Classification Rules — [new]

- Four responsible stages: Vendor, Carrier, DC, Indeterminate.
- The stage is decided by excess over an expected window, not raw duration: vendor 24h (late
  appointment approval), carrier 8h, yard 4h, dock 6h. The thresholds are backed by a
  sensitivity analysis, not hand-picked.
- Resulting distribution over the 247 late POs: Vendor 53.0% (131), Carrier 16.2% (40), DC
  15.0% (37), Indeterminate 15.8% (39). Indeterminate breaks down into 15 with no data (no
  trailer time) and 24 with no dominant cause (measurable, but no segment exceeds its
  threshold).
- Deterministic severity: HIGH if the PO is urgent ("hot") and the delay exceeds 3 days; LOW
  if the delay is under 1 day (borderline); MEDIUM for the rest. Distribution: MEDIUM 131,
  LOW 82, HIGH 34.

Speaker notes: the "not hand-picked" point is defensible with the sensitivity table in
`02_clasif_reglas_negocio/README.md` if a panelist asks why 24h and not another number.

Source: `documentation/explicacion-proyecto.en.md` (Phase 2).

### 7. Diego View: Exception Workbench — [expanded]

- Focus: individual management of late POs, case by case.
- Life-cycle timeline (7 events) with the responsible stage's segment highlighted.
- Root cause drafted by the LLM, with evidence and reasoning; recommended action as a
  3-step plan (immediate, corrective, preventive).
- Validation flag against the human `REASON_DSC`, prominent: a disagreement is a finding to
  review, not an LLM error.
- Explanation quality: 5/5 (20/20) in the human-evaluation benchmark, against a mentor
  threshold of 4/5.

Speaker notes: this is the view used in the live demo (slide 9); no need to dwell on it much
in text here, since it will be shown running.

Source: `documentation/user_personas.en.md` (Persona A — Diego); `documentation/metricas-proyecto.en.md`.

### 8. Ravi View: Network Intelligence — [expanded]

- Focus: aggregate analysis of the entire population of late POs, by systemic pattern.
- Three specialized agents (Vendor, Carrier, DC), each with statistical scorecards per
  entity.
- Distribution by stage and by severity; temporal trend of late POs.
- AI vs. human disagreement rate as a first-class KPI (see the note on the two figures
  above: it is not the same figure as Reason Code Agreement).
- Drill-down to an individual PO: the bridge to the Diego view.

Speaker notes: this view is the starting point of the live demo (slide 9); the drill-down
into Diego is literally the flow that will be shown.

Source: `documentation/user_personas.en.md` (Persona B — Ravi).

### 9. Live Demo — [new]

Pure transition slide, with no more content than the entry point into the script:

- Coming up: PO #100236 — BIOPLEX (Vendor), an urgent ("hot") PO, severity HIGH.
- The DC logged "Equipment/trailer issue"; the computation says Vendor, with a 94.5-hour
  excess.
- What will be shown: the aggregate pattern in Ravi → drill-down → the full diagnosis in
  Diego.
- No API calls: everything is read from already-generated artifacts.

Speaker notes: the full step-by-step script lives in `guion-demo.en.md` — this slide is only
the hook before switching to the real application.

### 10. Telegram Integration — [kept]

Unchanged: risk-alert bot; detection of a PO with HIGH severity; automatic message with root
cause; direct link to the web application.

### 11. Validation and Metrics — [new]

| Metric | Value | Mentor threshold |
|---|---|:--:|
| Stage accuracy | 100% (208/208) | > 80% ✅ |
| Reason agreement | 88.8% (174/196) | reference, no threshold (this is the central finding) |
| Severity Ranking | 100% (14/14) | > 95% ✅ |
| LLM Explanation Quality | 5/5 (20/20) | 4/5 (80%) ✅ |

- Test suite: 251 tests passing, merge gate on every PR.
- Denominators are not interchangeable: 208 evaluable, 196 classifiable, 14 hot-late, and 20
  sampled answer different questions (detail in `metricas-proyecto.en.md`).

Speaker notes: this slide replaces the single loose figure v1 carried (an "88%" on
Conclusions) with the three metrics the mentor actually measures the project against, plus
the quality benchmark as a fourth supporting figure.

Source: `documentation/metricas-proyecto.en.md`; `documentation/validacion-y-qa.en.md` (Layer C).

### 12. Conclusions — [expanded]

- Data-driven decisions, not perceptions.
- 88.8% reason agreement between the computation and the human expert (a specific figure,
  no longer a loose "88%").
- Total separation of responsibilities: statistics diagnoses, the LLM interprets.
- The dashboard always serves instant information, without recomputing anything on the fly.
- Every decision cited in this presentation is backed by formal, versioned documentation: the
  requirements specification, the architecture document, and the complete design-decision
  record (ADRs).

Speaker notes: the last bullet is new and closes the point that nothing shown here is
improvised — there is a complete documentation trail behind every figure and every rule.

## Appendix — coverage of the 10 rubric criteria

This table is the verification that all 10 criteria are covered, even though there is no
slide dedicated to each one individually.

| Criterion | Where it is covered |
|---|---|
| 1. Data Ingestion & Pipeline Quality | Slide 3 |
| 2. Delay Taxonomy & Rule-Based Classification | Slide 6 |
| 3. LLM Integration & Prompt Engineering | Slide 5 |
| 4. Explanation & Recommendation Quality | Slide 7 + live demo |
| 5. Validation & Analytical Rigor | Slide 11 |
| 6. Demo / Application Usability | Slide 9 + the demo script executed live |
| 7. Business Relevance & Stakeholder Insight | Slides 7 and 8 |
| 8. Communication & Documentation | Slide 12 + the bilingual ES/EN deck itself |
| 9. Collaboration & Professionalism | Not covered by slide content — assessed through team process, not the deck |
| 10. Innovation & Insight | Slides 4 and 12 |

## Relation to other documents

Draws on `documentation/explicacion-proyecto.en.md` (narrative synthesis by phase),
`documentation/metricas-proyecto.en.md` (single metrics table),
`documentation/validacion-y-qa.en.md` (validation method), and
`documentation/hallazgos-ai-vs-humano.en.md` (business reading of the mismatches). The
step-by-step demo script lives in `guion-demo.en.md`. Closes issue #106.
