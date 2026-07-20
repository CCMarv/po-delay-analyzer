# Inference Temperature of the LLM: Evaluation 0.3–0.9 and Anchor Decision

* **Status:** 🟢 **Current** (closed 2026-07-19)
* **Technical Context:** Phase 3 / LLM Integration — temperature parameter in `llm_config.json`
* **References:** Issue #137; #94 (quality benchmark, 20 POs); #143 / ADR-14 (hardening of the few-shot prompt); ADR-12 (design of the few-shot prompt); `03_llm_integration/llm_config.json`; `03_llm_integration/eval_quality.py` (scaffold `--temperature`); `03_llm_integration/eval_diversity.py` (diversity metric); `03_llm_integration/fixtures/eval_quality_20pos_C3*.md`

## Context and Problem

The inference temperature controls the randomness of token sampling: low values (≈ 0.0–0.3) favor the most probable response (greater coherence and reproducibility); high values (≈ 0.7–1.0) increase diversity but may degrade adherence to the required JSON format.

The F3 prompt requires structured JSON output with five fixed keys (`stage`, `delay_days`, `root_cause`, `recommended_action`, `severity`). `llm_config.json` set 0.3 as a provisional anchor when configuring the inference layer (#120–#123). Issue #137 designed an experiment to validate whether a higher temperature provided useful diversity in the recommended actions, where the identified quality deficit was concentrated, as noted in ADR-12.

## Experiment — Two Rounds

The temperature was varied over the C3 combination (3 few-shot examples: Vendor + Carrier + DC) against the same 20 POs from the benchmark (#94, seed 42), backend `openai` (`gpt-4o-mini`), at 0.3 / 0.5 / 0.7 / 0.9. Each round added 60 calls (3 temperatures × 20 POs; point 0.3 is reused as an anchor). What changes between rounds is the prompt.

### Round 1 — Prompt Without Hardening (pre-#143)

The four temperatures scored 19/20 in (a & b) with no observable difference between them. Variance was minimal because the few-shot anchored the response template; two symptoms were identified: the phrase reflects "the evidence does not match the REASON_DSC" written mechanically (even when it matched, e.g., PO 100154) and an almost identical Carrier action between POs. The conclusion was that the diversity problem was a prompt design issue, not randomness of sampling: recalibrating the temperature before correcting the overfitting did not yield measurable improvement. The provisional decision was to maintain 0.3 and defer recalibration until resolving #143.

### Round 2 — Hardened Prompt (post-#143)

The sweep was repeated over the prompt that ADR-14 hardened (HOW TO REASON block, stage authority over the REASON_DSC, excess only for attributed stages). A diversity metric was added to measure what checks (a)/(b)/(c) did not capture.

#### Diversity Metric

It is documented within this ADR, without its own record, because it serves this decision and does not guide the product on its own. It is implemented in `eval_diversity.py`, which operates offline (does not consume API): it reads the already generated fixtures `.md` and measures `diversity = 1 − avg_pair_similarity`, where the similarity between two actions is the Jaccard index over their token sets. It is reported for the complete set of actions and for the Vendor subset, where homogeneity is concentrated. It is a lexical proxy —two rewritten but equivalent actions count as diverse— so it is accompanied by a qualitative reading of the actions side by side; it is not a semantic measure.

#### Results

| Temperature | div(set) | div(Vendor) | (a & b) auto | Observation |
|---|---|---|---|---|
| 0.3 (anchor) | 0.691 | 0.312 | 20/20 | (c) validated manually (#143); reproducible baseline |
| 0.5 | 0.706 | 0.375 | 20/20 | slightly more varied, no regression or loss of coherence |
| 0.7 | 0.708 | 0.458 | 19/20 | returns (a) in 100182 (copies the stage from the reason code) |
| 0.9 | 0.765 | 0.567 | 20/20 | maximum diversity; more lax causal rewrites |

## Findings (Round 2)

1. The hardened prompt unlocked the temperature sensitivity that Round 1 did not see: the diversity of Vendor actions increased monotonically (0.312 → 0.567). #143 was the missing condition for the temperature to have a measurable effect.
2. The gain is modest and resides in the causal tail, not in the skeleton. The mold "Request a recovery plan from the vendor with a firm date, as the delay originates from their…" persists in all eight Vendor actions at all temperatures; the temperature varies the cited cause, not the structure. The residual homogeneity is structural (prompt/few-shot design), not sampling.
3. Increasing the temperature changes diversity for reliability. At 0.7 the PO 100182 (Indeterminate with REASON_DSC "Vendor delayed shipment") failed (a): the model copied the stage from the reason code —the failure mode that ADR-14 corrects— and dragged an incoherent action. At 0.9 that case occurs again, but the automatic verification is noisy at high temperature, and more lax causal rewrites appear ("excess management," "late shipping") which are less precise than the measured "excess transit."
4. The canonical case that motivated #137 (PO 100278, Carrier / "Weather/road conditions") is coherent at all temperatures (formal claim to UPS Freight for the 29.7 h excess, corrective plan with date): it was resolved by #143, not the temperature.

## Decision

**0.9** is established as the inference temperature in `llm_config.json`, prioritizing the diversity of the actions —the objective of #137— now that #143 has made it sensitive to temperature. 0.9 achieves the greatest diversity from the sweep (div Vendor 0.567), maintaining (a & b) automatic at 20/20 over the benchmark.

The decision explicitly accepts these costs:

* Lower reproducibility than 0.3 in the production run (#97, 247 POs).
* Risk, evidenced at 0.7 over PO 100182, that some Indeterminate whose REASON_DSC names a stage may recur in the failure of (a) that ADR-14 corrects; at 0.9 the benchmark did not show this, but high temperature sampling does not guarantee it.
* More lax causal rewrites in some Vendor actions ("excess management," "late shipping"), to be monitored in the validation of (c).
* (c) over the 0.9 fixture was not fully validated manually when setting the anchor (only 0.3 was). **Closure (2026-07-19):** manual validation was completed (#148, commit `51afebb`, `eval_quality_20pos_C3_t09.md`) and it is the same measurement that sets the headline quality figure of the deliverable (5/5, 20/20) in `documentation/metricas-proyecto.md`.

## Consequences

* Positive: the recommended actions gain real lexical variation over the conservative anchor; the decision is supported by a reproducible metric (`eval_diversity.py`) in addition to qualitative reading.
* Negative: lower reproducibility and adherence to the format; the new anchor shifts the burden of verifying (c) over the 0.9 fixture to the reader.
* Derived work: the structural homogeneity of the Vendor skeleton is not resolved by temperature; it remains for prompt/few-shot design or hyperparameter probing (`top_p`, `frequency_penalty`, `presence_penalty`) that #137 noted as out of scope.

## Relation to Other Decisions

It supersedes the provisional decision of Round 1 (maintain 0.3 until correcting #143), which has been fulfilled. It consumes **ADR-14** (#143 unlocked the measured temperature sensitivity here) and **ADR-12** (design of the few-shot prompt). It does not reopen **ADR-03b / ADR-06b** (Vendor measurement).