# AI vs Human Mismatches — Evidence Narrative (#95)

Document the eight cases where the classification by timestamps (`stage_primary`) disagrees with the `REASON_DSC` annotated by the DC staff and the computation turns out to be more defensible. These are the central evidence of the project's thesis: human annotation is ~20% incorrect (mentor's data); the lifecycle timestamps are not.

Primary source: `fixtures/mismatches_llm_zeroshot.csv`, the already frozen zero-shot run of the 8 mismatches selected in Phase 2 by `metrics_core.select_mismatches(df, n=8, stratify=True)` (3 Vendor / 3 Carrier / 2 DC). This document does not call the LLM again: it reuses that run as a versioned artifact. The detail of excesses by segment refers to `02_clasif_reglas_negocio/README.md` §5.4/§6 and to `metrics_core.select_mismatches`.

## The Eight Cases

| PO | Stage (computation) | REASON_DSC (human) | Temporal Evidence | LLM Explanation | Why the Computation is More Accurate |
|---|---|---|---|---|---|
| 100280 | Vendor | Carrier — "Missed appointment window" | STA push 124.6 h (excess 100.6 h over threshold 24h); carrier excess = 0 | Vendor, 5.54 d; the LLM marks a match with REASON_DSC | Approval was delayed 124.6 h before the PO reached the carrier; the carrier segment has no measured excess — "missed appointment window" is a downstream symptom, not the cause |
| 100236 | Vendor | Carrier — "Equipment/trailer issue" | STA push 118.5 h (excess 94.5 h); carrier excess = 0 | Vendor, 5.26 d; the LLM marks NO match and notes hot PO | Same pattern: approval push precedes any carrier segment; "equipment/trailer issue" lacks temporal backing |
| 100382 | Vendor | DC — "Yard congestion - no available door" | STA push 111.0 h (excess 87.0 h); yard/dock excess = 0 | Vendor, 5.01 d; the LLM marks NO match and notes hot PO | Approval arrived late before the PO reached the yard; no measured excess in yard/dock |
| 100024 | Carrier | DC — "Dock processing backlog" | Carrier excess 25.7 h; dock excess = 0 | Carrier, 1.07 d; the LLM marks NO match | The excess exists in transit, not in dock processing, which shows no measured backlog |
| 100244 | Carrier | DC — "Yard congestion - no available door" | Carrier excess 30.8 h; yard/dock excess = 0 | Carrier, 1.63 d; the LLM marks NO match | Same as 100024: the signal is in transit, not in yard/door of the DC |
| 100138 | Carrier | DC — "Dock processing backlog" | Carrier excess 1.9 h (weakest signal of the batch, barely above threshold of 8h); dock excess = 0 | Carrier, 0.43 d; the LLM marks NO match | Even with a smaller delay, the identifiable excess remains in carrier, not in dock |
| 100058 | DC | Carrier — "Equipment/trailer issue" | DC excess 19.3 h; carrier excess = 0 | DC, 0.82 d; the LLM marks a match | The excess is measured in the DC segment, not in carrier transit; "equipment/trailer issue" lacks temporal backing in carrier |
| 100230 | DC (subclass yard/dock not confirmed — the fixture does not bring `dc_substage`) | Carrier — "Equipment/trailer issue" | DC excess 19.0 h; carrier excess = 0 | DC, 0.75 d; the LLM marks a match | Same pattern as 100058 (same REASON_DSC and reason_group_manual); the excess resides in DC, not in carrier |

## Cross-Cutting Pattern

The eight mismatches exhibit two variants of the same phenomenon. In the three Vendor cases (100280, 100236, 100382), the human blames the link where the PO got physically stuck —carrier or DC yard— while the approval had already arrived late beforehand (STA push of 87–125 h) and the accused segment shows no excess: this is the "visible link" pattern already documented in the Phase 2 README. In the remaining five cases (Carrier↔DC), the human confuses two contiguous downstream stages —transit vs. processing in the DC— while the computation isolates the excess in one of the two.

An honest nuance: in 3 of the 8 cases (100280, 100058, 100230), the LLM itself marked a match with the REASON_DSC despite the categorical mismatch between `stage_primary` and `reason_group_manual`. This does not weaken the thesis: it occurs because the text of the REASON_DSC is thematically compatible with the stage identified by the computation, not with the stage to which it was archived — meaning, even the human wording of the reason is ambiguous when faced with the three-stage taxonomy used by the classifier.

## Subsequent Use

This document is input for the findings document of the final report (#105) and for the closure validation (#85). It does not open work for either of the two issues.

*(Closing note, 2026-07-22: the `fixtures/mismatches_llm_zeroshot.csv` artifact was regenerated
(8 real calls to gpt-4o-mini via `eval_mismatches.py --backend openai`) after the fix to the
`decidible` gate in [ADR-03b](../documentation/decisiones/ARD-03b.en.md). The selection of 8
PO_NBR did not change — none of the 8 were among the 8 POs reclassified from Indeterminate to
Vendor by that fix, and their per-segment excess values are identical to the previous run
(commit `3d8e1297`, 2026-07-13). The only substantive change is that the LLM, in this new run,
marked `llm_coincide_con_reason=False` for 100382 (previously True) — a case of non-determinism
between zero-shot runs at temperature 0.9, not an effect of the fix. The table and the "honest
nuance" count (4→3 cases with a marked match) were updated accordingly.)*