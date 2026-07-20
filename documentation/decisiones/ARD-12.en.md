# Phase 3 Prompt Design: Few-shot that Teaches Reasoning, with Single Source

* **Status:** 🟢 **Current** (closed 2026-07-19)
* **Technical Context:** Phase 3 / LLM Integration — prompt design that generates explanation and action
* **References:** Issue #99; #94 (quality benchmark, 20 POs); #91/#67 (base prompt); ADR-10 (severity and threshold); `03_llm_integration/llm_integration.py` (`build_prompt`, `_format_example`, `_examples_block`); `03_llm_integration/eval_quality.py`

## Context and Problem

The explanation from the LLM is one of the deliverables evaluated by the mentor (rubric, *LLM Integration & Prompt Engineering*). The quality benchmark from #94 on 20 stratified POs measured the zero-shot prompt aligned with #91 through three binary checks per PO: (a) correct stage, (b) quantifies the delay, (c) viable action. The result provided a clear diagnosis:

* (a) correct stage: 19/20.
* (b) quantifies the delay: 20/20.
* (c) viable action: 13/20.
* Verdict (PASS if a&b&c): 13/20 → equivalent to 3.25/5, below the mentor's target (4/5).

The bottleneck is not classifying the stage or quantifying the delay —both are comfortably met— but rather the **quality of the recommended action**. The seven failures in (c) are generic actions ("review processes") or incoherent (ask to investigate what the `REASON_DSC` already explains). The canonical contrast is PO 100278 versus PO 100318: the same verb "investigate" is coherent only when the reason is empty (100318) and redundant when the reason already provides the cause (100278).

At the same time, two prompt artifacts coexisted: `build_prompt()` (operational, the one that runs) and `prompt_template.txt` (a draft of a system prompt that the code did not load). A dual source of truth.

## Considered Options

### Option A: Maintain the zero-shot prompt

* **Pros:** No changes; already meets (a) and (b).
* **Cons:** Does not meet the target of (c). The quality deficit of the action is precisely what the rubric evaluates.

### Option B: Adopt `prompt_template.txt` as the system prompt

* **Pros:** It is a more elaborate draft (senior role, business context, quality criteria).
* **Cons:** It carries outdated decisions: a taxonomy of six stages (Vendor/Carrier/Scheduling/Yard/Dock/Receiving) that are not the four states of F2; instructions that invite examining timestamps and calculating, contrary to the guideline of #91 (interpret, not calculate); and a severity threshold `> 7 days` that contradicts ADR-10 (`> 3 days`). Adopting it would revert current decisions.

### Option C: Few-shot that teaches reasoning, with `build_prompt` as the single source

* **Pros:** Directly addresses the actual deficit (c) with examples that teach the mapping data→reasoning→action: that the stage comes from the measured temporal signal (not the human reason) and that the action addresses the real cause without asking to investigate what the reason already explains. The examples come from real mismatches from F2, separate from the evaluation set to avoid contaminating the metric. The number of examples is empirically decided against the benchmark (seed 42), not by intuition. It establishes a single source for the prompt.
* **Cons:** Risk of template copying (the model mimicking the wording of the example instead of reasoning); more tokens per call; requires curating the examples with criteria.

## Decision

**Option C** is chosen.

1. The prompt adopts **few-shot that teaches reasoning**, not the label. Examples are injected via an optional `examples` parameter in `build_prompt`; without it, the historical zero-shot behavior remains unchanged.
2. The examples come from **actual mismatches from F2** (the computed classification disagrees with the human `REASON_DSC`), verified as **disjoint from the benchmark of 20 POs** before any run, so that the metric does not become contaminated.
3. Each example is **a mirror of the form** of the real case (same blocks of the prompt) but **curated in content**: only the fields that teach the reasoning behind the action (the excess signal of the chosen stage, the cited delay, the person responsible to name, the reason in discussion, and the active aggravating factors). It does not include the timeline of dates —showing it would retrain on recalculating, against #91— nor noise fields. The ideal JSON for each example carries the **five complete keys**, to reinforce that all five must always exist.
4. `build_prompt()` remains the **single source** of the prompt and `prompt_template.txt` is **eliminated**.
5. The winning combination (how many examples) is chosen based on its rate of (c) against the benchmark, without degrading (a) or (b). **Recorded winner (closure, 2026-07-19):** C3 — 3 few-shot examples, one for each stage (Vendor + Carrier + DC) — is the production configuration, validated 20/20 in (c) at temperature 0.9 with seed 42 (`03_llm_integration/fixtures/eval_quality_20pos_C3_t09.md`), wired in `llm_integration.py` (`select_examples(3, stages=["Vendor", "Carrier", "DC"])`).

## Consequences

* **Positive:** The prompt targets the measured deficit of action with a directed and assessable intervention against the same benchmark. The prompt source ceases to be dual, eliminating the risk that an outdated draft is reused and reverts #91 or ADR-10. The curation of examples from real mismatches connects the prompt design with the thesis of the project (the temporal computation surpasses human annotation).
* **Negative:** Risk of template copying, mitigated by examples from different stages and heterogeneous actions and by the human validation of (c) over the winning run. The inclusion of `is_rescheduled` in an example is decided on a case-by-case basis and always as neutral context (the ideal action should not blame the vendor for rescheduling, a bias corrected by ADR-05/#67); each new example is audited with this criterion.

## Relation to Other Decisions

It does not surpass any current decision, so it is not chained as 📘 Superseded. **Reference to ADR-10:** the elimination of `prompt_template.txt` materializes the threshold `> 3 days` already in place (removing the `> 7 days` from the draft), it does not redefine it. **Forward to ADR-14:** the mitigation of the "risk of template copying" mentioned here is executed and reinforced in ADR-14 (#143), which adds the HOW TO REASON block, the authority of the stage over the REASON_DSC, and the presentation of excess only for attributed stages.