# The LLM as an Analytical Layer over the Validated Deterministic Baseline

* **Status:** 🔵 **Draft** (to be closed by the team)
* **Technical Context:** Phase 3 / LLM Integration — incorporate model capabilities (pretrained domain knowledge, reasoning, synthesis) above the already validated deterministic logic
* **References:** Feedback from mentors after the validation of main; README of the original mentor's repo (metric *LLM Explanation Quality*); `03_llm_integration/fixtures/eval_quality_20pos_C0_t09.md` / `_kb.md` (evidence of the symptom); ADR-14 (anti-hallucination — its scope is adjusted); ADR-12 (prompt); ADR-10 (hybrid severity); ADR-07 (taxonomy of Indeterminate); [ADR-15](ARD-15.en.md) (conditional KB — superseded by this framework); `03_llm_integration/llm_integration.py`; `03_llm_integration/eval_quality.py` / `eval_diversity.py`

## Context and Problem

The state of main has been reviewed and validated by mentors: the deterministic logic from Phases 1–2 and the explanation per PO were measured as consistent and structured. The subsequent order defines a new task: to enrich the program by allowing the LLM to apply its model's own capabilities — pretrained domain knowledge, reasoning, synthesis — above what the deterministic scripts calculate.

The specific symptom lies in the recommended action. The benchmark fixtures (20 POs) show this: without KB, the 20 actions are variants of the two illustrative lines from the historical prompt ("Open a claim with [X] for the N h...", "Review with the [DC] team..."); with the KB from ADR-15, the phrasing improves, yet the nature persists ("review and ensure your processes," "escalate to investigate the reasons"). The action delegates the search for options to the responsible party instead of proposing measures.

The pattern has two causes. The first is the capture of illustrative lines as templates. The second is structural: the model's diagnosis stops at the stage level, and a concrete measure requires committing to a mechanism below that level (inventory, production capacity, documentation, gate congestion); the current prompt prohibits hypothesizing it. With concrete action required and fine diagnosis banned, the meta-action "review with X" becomes the rational output of the system.

The tightening of ADR-14 ("use ONLY the given figures, do not estimate") was appropriate while auditing fidelity to the data; applied to the new layer, it blocks the use of the model's domain knowledge, which is the requested capability. The README of the original repo asks for "viable action, not generic" and its own examples are generic categories ("contact vendor, escalate to carrier, review DC capacity"); mentor feedback sets a higher standard than the README and grants freedom to modify the output scheme.

Operational test of this ARD: there is model analysis when the conclusion becomes unpredictable by reading the code and the curated artifacts — the mapping evidence → conclusion occurs in the model.

Previous discards with real data, which constrain the available inputs: thresholds per city of the DC (the 8 cities do not differ beyond noise) and estimation of the vendor's distance by city × volume × time (typical cell of ~5 rows per city × vendor).

## Considered Options (role of the LLM in the product)

**Option A — Limited Writer (statu quo).** The LLM writes what is decided by the deterministic logic (ADR-12/14). Corresponds to the validated state in main. Leaves the new request unaddressed.

**Option B — Analyst with Curated Perimeter.** Two calls, versioned playbook, and closed causal repertoire (previous draft of this ARD). Pros: the knowledge used is pre-approved and auditable in the input. Cons: the team defines in advance what knowledge the model can apply; manual curation duplicates knowledge already present in the model and limits analysis to the expected cases. Discarded as the request became clear.

**Option C — Analytical Layer over Verified Facts (chosen).** The factual premises come from the data (ADR-14 is preserved at this point); domain knowledge comes from the model, enabled in the prompt and marked in the output. Cons: higher variance between runs; knowledge applied is no longer pre-approved, and the audit shifts from input to output (see Validation).

## Considered Options (scope of the layer)

**Option A — Only the action per PO.** Minimum scope, close to the current pipeline. Excludes capabilities included in the request (aggregated patterns, synthesis).

**Option B — Three lanes delivered in phases (chosen).** Each lane with its issue; lane 1 reuses the existing pipeline and validates the new perimeter before scaling to the other two.

## Considered Options (mechanisms discarded or deferred for action)

**Few-shot with concrete actions — discarded.** This is the mechanism that produced the capture of templates (history of ADR-14 and evidence of the fixture); action examples tend to become the complete repertoire.

**Web search by PO in production — discarded.** The entities of the dataset are synthetic, and a search by entity returns noise (documented in ADR-15); searching by general domain duplicates pretrained knowledge; the result becomes non-reproducible.

**Offline web search materialized with sources — deferred.** A single run per topic (mentor questions × stages/events), materialized in a versioned document with cited sources, in prior mode. This overlaps with the discarded Option B (curation); it will be decided after wave 2, only with evidence that the model's knowledge falls short.

**Live web search as a demonstration — accepted outside the deliverable.** Demo flag, only official backend, queries by mechanism with code guard blocking names of dataset entities, statements with cited sources, 3–5 POs with a count declaration.

**Calendar signals — deferred to lane 2.** Day of the week / week of the month for milestones only enters when the aggregates of lane 2 can confirm the pattern; a loose date invites over-reading.

## Decision

1. **Role of the LLM.** The LLM operates as an analytical layer over the output of Phases 1–2 (stages, excesses, flags, severity audited by ADR-10). That output provides the facts; the model produces the conclusions.
2. **Anti-hallucination perimeter with two rules.** (a) The facts of the PO and of the dataset come only from the data, with figures quoted verbatim; ADR-14 remains intact for the deterministic call and for the factual premises of the layer. (b) The domain generalizations come from the model's knowledge, enabled in the prompt and marked in the writing, separate from what the data shows. The instruction to declare when the data does not suffice to distinguish remains. Inventing premises is prohibited; deriving conclusions is permitted.
3. **Lane 1 — the action call.** The current call remains intact and emits `root_cause`, `severity`, `matches_reason_code`, and `confidence` (of evidence). The second call is designed as follows:
   * **Role:** supply planner with authority to decide the next steps for the PO, instead of an analyst.
   * **Mandatory differential diagnosis:** hypothesis of mechanism under the stage level, with its evidence; alternative hypothesis with the discriminative step (the exact data that separates both and the decision that depends on it).
   * **Output contract (hybrid):** `reasoning` →
     `main_hypothesis {hypothesis, evidence, plan {immediate_action, corrective_action,
     preventive_action}}` → `alternative_hypothesis {hypothesis, discriminative_step}` →
     `confidence` (of hypothesis). The order of keys conditions the plan on the reasoning already generated (autoregressive generation). No limit of one-two lines per field.
   * **Concreteness rules:** meta verbs (review, analyze, investigate, monitor, follow up) do not count as main action; all verification names the exact data and the decision that depends on it. If there was a short-ship, the plan includes the decision of the missing item (re-issue / wait / cancel) with its criteria. When the mechanism of the main hypothesis is not confirmed by data quoted in the evidence (it is inferred from the stage pattern, not from a concrete fact of the PO), the immediate action converges to the `discriminative_step` data instead of a generic request for explanation/report/action plan (refinement post-wave 3; at the end of lane 1 this rule, the meta verb rule, and the Indeterminate case merged into a single rule with two branches — confirmed mechanism → execution or coordination; not confirmed → obtaining the data — because they measured three different positions on whether obtaining a data counts as an action, see Decision 8).
   * **Inputs:** the diagnosis of the first call, the raw facts, today's hidden magnitudes (real fill rate, magnitude of reschedule in hours, order size) and globally comparative facts calculated deterministically (percentile of excess, medians per stage), present in the prompt of every PO — the conditional presentation of a comparative would introduce judgment by selection.
   * **Fallback for the first call:** if the deterministic call does not yield a diagnosis, the action call does not execute and the PO remains marked (`qa_flags = sin_diagnostico_llamada1`), visible and not blocking the pipeline — without validated diagnosis there is no input for the plan.
   * **Domain elicitation:** self-questionnaire prior to the mentor questions (most common causes from the measured stage; shorting impact; causes and consequences of the rescheduling) that the model answers with its knowledge before recommending; open glossary of industry terms (expedite, chargeback, carrier scorecard, re-dock citation, split shipment, safety stock, OTIF) as available vocabulary, loose terms with prohibition of transcribing phrases. *(Both removed at the close of lane 1 due to evidence of almost no use, see Decision 8.)*
   * **Additional signals:** the discrepancy REASON_DSC vs. measured stage enters as a meta-signal from the annotation process —enables process hypotheses (mislabeled handoff) without promoting REASON_DSC to stage (current rule)—, derived deterministically from `reason_group_manual` vs. `stage_primary` (not from the judgment of the first call) and presented unconditionally with three states (matches / disagrees / not evaluable); with `stage_multi` active, the plan accepts multi-actor distribution with the excess figure from each stage and a single immediate action (the bottleneck).
4. **Lane 2 — patterns between POs, in two stages.** First static: precomputed aggregates injected into the prompt (provider and carrier history within the dataset, percentiles, POs with the same signal pattern, short-ship details), each with its n for the model to weigh the evidence (small documented cells). Then agentic, only if the benchmark shows that the model ignores the injected aggregates: query tools (`provider_history`, `percentile_excess`, `similar_pos`, `short_ship_detail`) with a budget for calls and log of questions persisted by PO as an auditable trail of reasoning. The agentic stage changes the `call(prompt)` contract of the backends; it is deferred until evidence is available.

   Evidence arrived with wave 3: the fixtures measured 0–1/20 POs citing figures from the HISTORY block — the model ignores the injected aggregates. The static stage was removed from the prompt at the closure of lane 1 (the aggregates remain precomputed in `compute_dataset_stats` as future input); the agentic stage remains with favorable evidence but deferred: the next validation instance is the dataset-level evaluation developed by the team, and it is advisable to decide it with that.
5. **Lane 3 — product capabilities.** Executive synthesis of the delay portfolio and Q&A about the dataset, designed along with the Phase 4 views (user personas of ADR-09). Own issues.
6. **Indeterminate.** POs without attributable cause pass through the analytical layer; the expected analysis identifies the missing data and the clarification step (ADR-07 taxonomy).
7. **Generative quality control (self-critique pass).** After the action call:
   * Rule checks, in code and at no cost: main action without meta verb; all figures from the output exist in the input; complete scheme; decision of the missing item present if there was a short-ship; stage named the same as `stage_primary`. Failure → regeneration with the cited defect, maximum 2 retries; if it persists, the output is marked with visible `qa_flags` and does not block.
   * Judgment checks, with LLM judge in local backend (no API cost): coherence hypothesis → action, validity of the discriminative step, marking of generalizations, executability without additional decisions. The judge is calibrated against human labels from the fixture before being used as a pre-filter for human validation.
8. **Wave sequence, with measurement between waves.** Each wave is evaluated against the fixture of 20 POs (in local backend or, without local backend available, in the official backend with count declaration and prior permission) before adding the next one, to preserve the attribution of improvements (ADR-13/ADR-15 pattern):
   * Wave 1 (structural): hybrid contract, role, concreteness rules, rule checks, uncovered magnitudes, and global comparisons.
   * Wave 2 (diagnostic): differential diagnosis, REASON_DSC discrepancy, multi-actor.
   * Wave 3 (reinforcements): self-questionnaire, glossary, lane 2 static.
   * Conditionals: extended reasoning or more capable model in the action call if depth does not reach after wave 2; offline search materialized according to evidence after wave 2; live web demo as an independent flag.

   Result of the gate of wave 2 (`03_llm_integration/fixtures/eval_quality_20pos_C0_t09_accion_ola2.md`, gpt-4o-mini, seed 42): verdict 17/20 → 4.25/5 (mentor goal 4/5, achieved); the hypothesis-label disappears in Vendor (5/8 → 0/8) and the 4 Indeterminate emit conditional hypotheses. The three failures come from call 1 (criterion b). With that evidence, the conditionals do not trigger: the depth reached without extended reasoning or more capable model, and the model's knowledge did not fall short, so the offline search materialized is discarded.

   Human validation of wave 3 (2026-07-08), fixture `03_llm_integration/fixtures/eval_quality_20pos_C0_t09_accion_ola3.md`, criterion (c): 8/20 POs (100158, 100087, 100182, 100092, 100324, 100366, 100367, 100157; crossing Vendor, DC, and Indeterminate) fail by the same pattern — `discriminative_step` already names the exact data that would confirm the mechanism, but `immediate_action` does not reuse it and falls into a generic request. It is not a lack of depth in reasoning or knowledge of the model (the correct data does appear in the output), thus it does not trigger a conditional: it is a specification gap in the contract, closed with the refinement to the Concreteness Rules of Decision 3.

   Closure of lane 1 (2026-07-08). The previous refinement was measured with A/B fixed seed (`seed` from OpenAI API, best-effort, added to `llm_config.json`): moved 2/8 POs — weak signal; one more declarative rule does not correct the pattern when competing with a block of instructions that was already ~73% of a prompt of ~2,450 tokens. With that diagnosis, the closure optimizes the call instead of adding rules:
   * The three reinforcements from wave 3 are removed — self-questionnaire for elicitation (with its key from the contract), glossary and static history — due to high cost with measured use almost null (glossary 1–3/20, history 0–1/20, elicitation ~220 tokens of output per PO in text that the hypotheses do not reuse) and without improvement in the gate (wave 3 did not surpass wave 2).
   * The three positions on immediate action (meta verb rule, refinement post-wave 3, Indeterminate case) merge into one rule with two branches, with a micro version in the description of the `immediate_action` field of the contract; stage instructions (Indeterminate, pointer Vendor, multi-actor) are issued only where applicable.
   * Plumbing that reduces regenerations: `response_format json_object` in the official backend (eliminates parsing failures) and keys from the missing item decision check expanded to stems (false positives observed with "re-issue" / "wait").
   * Result: input ~2,450 → ~1,500 tokens per action call (−~40%) and output −~25%, verified with re-measurement of the fixture (`_ola3-cierre`).
   * Considered and discarded: reordering instructions-first for OpenAI's prompt caching (after the cut, the static prefix remains below the threshold of 1,024 tokens); separating system/user (changes the `call_raw` contract of the four backends, the same cost for which the agentic stage was deferred); semantic check of convergence action↔discriminative step (not lexically calibrable: passes and failures share superficial form — left for the local LLM judge of Decision 7).

   The next quality validation of lane 1 corresponds to the dataset-level evaluation developed by the team, which replaces the fixture of 20 POs as an instrument.
9. **Pending implementation (updated at closure, 2026-07-19).**
   ~~Interaction of the new contract with the few-shot (C1–C3)~~ — **resolved**: C3 is the production config (ADR-12, `llm_integration.py`). ~~Exposure in Phase 4 of reasoning, the two confidences~~ — **resolved**: the 9 tier-2 columns are populated 247/247 and consumed by the app (see [ARD-21](ARD-21.en.md)). `qa_flags` **remains outside the deliverable, by explicit audit decision** (`llm_integration.py`: "llm_qa_flags does NOT enter"), not due to lack of time. The capabilities of lane 3 remain **partially delivered** by [ARD-19](ARD-19.en.md) (executive synthesis; the conversational Q&A remains deferred, #160). Genuinely pending: **calibration of the local judge** and the agentic stage of lane 2 (Decision 4), deferred to the dataset-level evaluation of the team.

## Validation (plan, lane 1)

The audit evaluates the output: what the model asserted and on what basis. On the fixture of 20 POs (#94):

* **Factual anchoring:** all assertions about the PO or the dataset quote a shown data; all generalizations appear marked as domain knowledge. Verified with rule checks (figures ∈ input) and sample human review.
* **Concreteness:** rate of actions with meta verb as main action (automatable with the closed list of verbs); goal: zero after wave 1.
* **Discrimination:** POs with distinct evidence produce distinct hypotheses. The covariance inputs → conclusions is measured; the lexical diversity of ADR-15 ceases to be the target metric. Operationalization (wave 2): intra-stage lexical convergence (Jaccard on content tokens, θ=0.25 calibrated against wave 1 fixture), read along with the covariance signal → hypothesis: a cluster aligned to shared evidence (e.g. short-ship → lack of inventory) does not count as a failure; the failure is the cluster that ignores the evidence.
* **Counterfactual sensitivity:** altering a single input of a real PO (e.g. fill rate 95% → 72%) should change the conclusion in the expected direction. Runs in local backend.
* **Local judge pre-filter** for human validation: the human validates a sample plus the cases marked by the judge; the hybrid contract multiplies the text to validate and the pre-filter keeps validation manageable.

Every run against the paid API declares the call count and requests prior permission (current policy).

## Consequences

**Positive:** covers the request of the mentors; actions move from meta-action to executable plan with business decision; inference remains visible and auditable (reasoning, discriminative step, log of consulted aggregates in the agentic stage); the wave delivery preserves the attribution of improvements.

**Negative:** greater variance between runs; ~2× cost and latency per PO plus retries of the self-critique pass; the hybrid contract raises the output token cost and expands the surface of human validation (mitigated by the pre-filter); the output scheme changes and affects the consumption of Phase 4; the data/domain marking requires sample human validation.

## Relation to Other Decisions

Adjusts the scope of **ADR-14**: its restriction remains for the deterministic call and for the factual premises of the layer; it no longer applies to domain generalizations. Preserves **ADR-10** (the severity is issued by the LLM and audited Phase 2) and reuses **ADR-07** and the infrastructure of **ADR-12**. **[ADR-15](ARD-15.en.md)** (correction of wording via curated knowledge) is superseded by this framework (📘, chained): the diversity that its KB sought is produced by the differential diagnosis of the action call without curated knowledge; the opt-in flag of #151 remains in call 1 and is not reversed. An unversioned previous draft of this ARD developed Option B (curated perimeter with playbook) and was replaced as the request became clear.

**[ARD-19](ARD-19.en.md)** (2026-07-17, executive synthesis per actor on scorecards) delivers part of lane 3 reserved in Decision 5 (executive synthesis of the portfolio); it does not surpass this decision, whose lane 1 remains active in production and whose agentic lane 2 and local judge calibration (Decision 7) remain unresolved — for this reason, this ARD remains 🔵 Draft with explicit reason, instead of closing to 🟢, even though lane 1 is implemented and in production.