# Prompt Hardening of Phase 3 Against Overfitting in Few-Shot

* **Status:** 🟢 **Current** (closed 2026-07-19)
* **Technical Context:** Phase 3 / LLM Integration — prompt rules to reason by PO instead of just mirroring the example or human reason
* **References:** Issue #143; #137 / PR #144 (temperature experiment that surfaced it); #94 (quality benchmark, 20 POs); ADR-12 (few-shot prompt design that named the risk); ADR-07 (taxonomy of Indeterminate); ADR-03b / ADR-06b (Vendor measurement, not reopened); ADR-13 (temperature); `03_llm_integration/llm_integration.py` (`build_prompt`, `_format_example`)

## Context and Problem

ADR-12 adopted a few-shot that teaches reasoning and registered the "template copying" risk, to be mitigated with heterogeneous examples. The temperature experiment from #137 confirmed that the risk materialized: with the C3 combination (Vendor+Carrier+DC examples, the three cases of discrepancy reason↔stage), the model mechanically wrote "the evidence does not match REASON_DSC" even when it did match (PO 100154) and repeated a nearly identical Carrier action between POs. Recalibrating the temperature does not correct it; the cause is the prompt design.

Upon correcting the former and reviewing the complete output of Phase 2 (39 indeterminates), a more subtle and independent flaw appeared: for an Indeterminate PO whose REASON_DSC names a stage ("Vendor delayed shipment"), the model adopts the reason as the stage and ignores the "Indeterminate" classification. The pattern was isolated: the three indeterminates in the sample with REASON_DSC "Not applicable" were explained as indeterminate; only the one with a reason naming a stage failed. Concurrently, 8 of the 15 `sin_datos` retain a measurable `excess_vendor_hrs` (up to 92.5 h) that the classifier did not use to attribute —`decidable` requires measurable carrier or DC, "no vendor by elimination" in `classifier_core.py`—, so displaying that number in the prompt invited overwriting the Phase 2 verdict.

## Considered Options (presentation of excess by stage in Indeterminate)

### Option A: Always show the excess by stage

* **Pros:** A single form of the metrics block; the few-shot Vendor example cites that number and the actual PO receives it.
* **Cons:** In the 8 `sin_datos`, the vendor excess contradicts the verdict; the sub-category line competes against it and loses (100182 confirms it).

### Option B: Show the excess by stage only when a stage is attributed (chosen)

* **Pros:** Aligns the prompt with what Phase 2 concluded; removes the misleading signal at its root; consistent with few-shot examples, which no longer show excess for indeterminate; the actual Vendor/Carrier/DC retain their excess.
* **Cons:** One more conditional branch in `build_prompt`.

### Option C: Show the excess labeled as "not attributable"

* **Pros:** Keeps the number visible for honesty.
* **Cons:** Verbose, and the tempting number remains present.

## Decision

1. **HOW TO REASON Block.** The prompt teaches the domain combinatorics that the examples do not show —the four stages and the three relationships with the REASON_DSC (matches / disagrees / empty)—, with illustrative lines of action marked as range, not as a template. The JSON field descriptions refer to that guide.
2. **Authority of the stage.** The stage that the model reports must be exactly the `stage_primary` of the classification, the source of truth by temporal signal. The REASON_DSC is contrasted but never replaces the stage nor is promoted to a stage even if it names one. For Indeterminate, the explanation declares it indeterminate and explains why (`sin_datos` / `sin_causa_dominante`).
3. **The excess by stage is a signal of attribution (Option B).** Excess lines are shown only for attributed stages (`stage_primary` ≠ Indeterminate); for Indeterminate, the raw yard/dock times plus the sub-category are shown. The Vendor measurement is not reopened (ADR-03b / ADR-06b current): it is a presentation decision for Phase 3.
4. **Canonicalization of casing.** Phase 3 consumes `stage_primary == "Indeterminado"` (titlecase, the value emitted by the classifier per ADR-07) as the only convention; the uppercase variant that coexisted in the prompt code, the pool, and tests is removed, latent source of the bug for which the sub-category line never triggered for real POs.
5. **Rewriting of the examples in the pool.** The Carrier example (and those of Vendor and DC) do not open with the negation formula; they model the reasoned discrepancy and actions that cite concrete figures.

## Consequences

* **Positive:** The prompt reasons by PO. The reinforcement lives in `build_prompt`, thus covering production zero-shot and the benchmark alike. The correction of the presentation of excess is systemic for the 8 `sin_datos` with vendor excess, not just the benchmark case.
* **Negative:** More text in the prompt, more tokens per call. Robustness is validated against the same benchmark, not guaranteed by construction. The canonicalized casing requires that all new Phase 3 code uses "Indeterminado" in titlecase.

## Relation to Other Decisions

Forward from **ADR-12**: executes and reinforces its named mitigation of the template copying risk, without surpassing it (the few-shot remains current). Consumes **ADR-07** (taxonomy of Indeterminate) and links with **ADR-13** (#143 unlocked the closure of #137, which set 0.9 as a temperature anchor in its round 2). Does not surpass or reopen **ADR-03b / ADR-06b** (Vendor measurement).

**Note (2026-07-22):** the 8 `sin_datos` POs with measurable `excess_vendor_hrs` that this ADR documented from the presentation angle (Decision point 3) actually had a root cause in the classifier: the `decidible` gate in `classifier_core.py` excluded them from Vendor attribution. The closing note of [ADR-03b](ARD-03b.en.md) (2026-07-22) fixes that gate; the 8 POs move to Vendor. This ADR is not reopened — Option B (showing excess only for attributed stages) remains current and correct for real Vendor/Carrier/DC POs.