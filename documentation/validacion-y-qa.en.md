# Validation and QA — the Closure Method

This document explains how the project ensures the correctness of its results and how a reviewer reproduces them on their machine. It is not an inventory of tests: it is the end-to-end validation method, described by the layers a piece of data traverses from cleaning to classification and measurement.

The framework takes two complementary references. From The Turing Way, the criterion of reproducibility is adopted: the same data plus the same code must produce the same result, which requires setting the environment, versioning, and automating verification. From the test plan practice, the structure by levels is adopted: what is tested, at what level (unit, contract, metric, gate), and what the success criteria are. Turing Way provides the why (reproducibility as the goal); the test plan provides how it is organized (layers and criteria). They do not compete with each other.

Validation is organized into four layers. Each one is described with the same three questions: what it guarantees, what it breaks if it fails, and how it is reproduced.

## Layer A — Unit Tests by Phase

What it guarantees. Each function of the pipeline does what it says, isolated from the others. The suite is divided by phase: `tests/test_pipeline_core.py` covers cleaning, quality flags, and F1 deltas; `tests/test_classifier_core.py` covers the primary stage, severity, and F2 subclasses; `tests/test_metrics_core.py` covers stage accuracy, reason agreement, and sensitivity analyses; `tests/test_llm_integration.py` covers the construction of the prompt and parsing of the JSON response of F3 without touching the network; `tests/test_fewshot.py` covers the deterministic selection of the few-shot pool; `tests/test_eval_quality.py` and `tests/test_eval_diversity.py` cover the explanation quality and diversity benchmarks. From F4, `tests/test_app_smoke.py` covers that the Streamlit app pages load without an exception, `tests/test_qr_service.py` covers the bot's QR service, and `tests/test_telegram_auth.py` covers the Telegram bot's fail-closed authentication and demo bypass; `tests/test_sample_artifact.py` covers the shape of the versioned sample the app falls back to when the real artifact is absent. The fixtures are synthetic, with known values, making the expected result deterministic.

What it breaks if it fails. A regression in a function leaves CI red before the merge. Without this layer, a change could alter the breakdown of stages or a header metric without anyone noticing, because the number would continue to "come out."

How it is reproduced.

```
pytest                                  # complete suite
pytest tests/test_classifier_core.py    # one phase in isolation
```

## Layer B — Handoff Contract Between Phases

What it guarantees. The boundary between two phases is a contract, not an assumption. `tests/test_handoff_contract.py` verifies the golden rule: the CSV produced by a phase is functionally identical to the DataFrame that that phase leaves in memory, so the subsequent phase reads it and reconstructs the same state that it would have if the chain had run all at once. It covers the F1→F2 and F2→F3 boundaries; `tests/test_handoff_f3.py` covers the third boundary, F3→F4, over the deliverable CSV `po_output.csv` instead of the full DataFrame. Identity is functional, not of typing: a CSV writes dates as text, so the contract is fulfilled when the value is the same, not when the dtype matches. The test reparses the date columns and unifies missing forms (NaN, empty string) to a common sentinel before comparing the full frame.

What it breaks if it fails. Running the phases separately would yield a different result than running them together, and F3 would read a state that F2 never produced. The contract allows executing the pipeline in segments — or resuming from an intermediate CSV — with the guarantee that the result does not change.

Edge case covered: the label `"Ninguno"` survives the round-trip. The `stage_multi` column uses the sentinel `"Ninguno"` for POs without a secondary stage, and not the literal `"None"` or the empty string. The reason is serialization: `"None"` and `""` are read from the CSV as NaN, causing F3 to lose the signal of "no secondary stage" and confuse it with a missing data point. `"Ninguno"` is a real value and survives intact (see `classifier_core.py`, construction of `stage_multi`). The contract verifies that the full frame — with that label included — reconstructs the state in memory.

How it is reproduced.

```
pytest tests/test_handoff_contract.py
```

## Layer C — Classification Metrics Against Thresholds

What it guarantees. The header figures of the deliverable are calculated from the lifecycle timestamps, not from human annotation, and are contrasted against the mentor's acceptance thresholds. The module `02_clasif_reglas_negocio/metrics_core.py` produces them: `stage_accuracy` (#46), `reason_agreement` (#47), and the severity and sensitivity functions.

| Metric            | Value             | Mentor Threshold | Denominator                                                |
|-------------------|-------------------|:----------------:|----------------------------------------------------------|
| Stage accuracy     | 100% (216/216)    | > 80%            | 216 evaluable (247 late − 31 Indeterminate with no measurable gap) |
| Reason agreement   | 88.7% (180/203)   | reference, not threshold | 203 classifiable (late with non-null human annotation)   |
| Severity ranking   | 100% (14/14)      | > 95%            | 14 hot-late (`HOT_PO_FLAG=1` and `delay_days_calc > 3`), on `po_output.csv` (severity = LLM) |

Stage accuracy compares the stage by excess over threshold (`stage_primary`) against the dominant gap (the segment of longest gross duration): it measures whether the classification rule aligns with where the PO actually spent more time. Reason agreement compares the temporal computation against the human annotation `REASON_DSC`, and here the <100% is expected and desired: the human annotation is approximately 20% incorrect, so the 23 mismatches are evidence of the project's thesis — the computation through timestamps corrects the inherited reason code — not a failure of the method. The severity ranking is measured against the official severity of the deliverable, which **is that of the LLM** (`severity ← llm_severidad`, ADR-10), not the deterministic rule of F2. Therefore, the measurement is empirical — it validates if the LLM respected `hot & delay>3 ⇒ HIGH`, not assuming it — and can in principle yield less than 100%; that it gives 14/14 is an observed result, not a guarantee "by construction." The F2 rule is preserved as an auditing baseline (that does give 14/14 by construction, by design) and is the reference against which the LLM is contrasted (see "LLM Severity Divergence vs Rule" below).

What it breaks if it fails. If one of these figures moves outside the threshold, the classifier has deviated from the timestamps (the source of truth) without notice, and the traceability of the figures supporting the report is lost.

How it is reproduced. Run `classifier_core.py` to generate `df_classified`, and on it the functions of `metrics_core.py`. The figures and their exact source are compiled in `documentation/metricas-proyecto.md` (single table, column "Reproduction (source)"); this document cites them, it does not recalculate them.

## Layer D — CI as Merge Gate

What it guarantees. `.github/workflows/ci.yml` runs on every pull request and on every push to main five isolated import-smoke steps (`pipeline_core`, `classifier_core`, `llm_integration`, `llm_integration_network_intelligence_view`, and the Telegram bot) followed by `pytest`. The team convention allows merging without waiting for blocking human review, so the merge gate is the green checkmark: it replaces "it works on my machine."

What it breaks if it fails. The check remains red if a module fails to import — due to a missing dependency, for example — or if any test fails, and the PR should not be merged. The CI does not include a lint, format, or type-check gate; that absence is a conscious decision for the scope of the project, documented in the workflow itself, not an oversight.

How it is reproduced. Locally, `pytest` reproduces the same criteria as the gate. Remotely, each PR triggers the workflow; the environment fixes Python 3.13 and installs from `requirements.txt`.

## Anchor Figures and How to Regenerate Them

A reviewer reproduces the live figures in a clean environment (a `venv` from `requirements.txt`, with the dataset in `data/raw/`) by executing:

```
python 01_data_pipeline_and_eda/pipeline_core.py      # F1 → df_clean
python 02_clasif_reglas_negocio/classifier_core.py    # F2 → breakdown + df_classified
pytest                                                 # 267 passed
```

The anchor figures that must be obtained:

- Test suite: 267 passing. The suite grew with each phase (from 57 to 99 to 114 to 244 to 251 to 267); the current value is 267.
- Stage accuracy 100% (216/216), reason agreement 88.7% (180/203), severity ranking 100% (14/14, severity = LLM).
- Breakdown of stages over the 247 late: Vendor 139 (56.3%), Carrier 40 (16.2%), DC 37 (15.0%), Indeterminate 31 (12.6%).
- LLM Explanation Quality 5/5 (20/20), few-shot C3 at temperature 0.9 (production configuration; requires API — see detail and progression in `documentation/metricas-proyecto.md`).
- LLM Severity Divergence vs Rule F2: 213/247 (86.2%) match; 34/247 (13.8%) diverge, always scaling (see section above).

All are traceable to `documentation/metricas-proyecto.md`, which documents the population and the source of each one. The denominators differ between metrics and are not interchangeable.

## Edge Cases and Failure Modes That Validation Covers

Validation not only confirms the happy path; it covers edge cases where the data is partial or anomalous, and the design prefers to declare the limit rather than guess.

27 POs without trailer time. They lack `TRAILER_ARRIVE_DT`, making the carrier and DC segments not measurable. The rule that assigns Vendor by STA push (`APPROVED_DT > STA_DT`) rescues 20 of them, as it measures late approval without needing the trailer; the remaining 7 remain as `sin_datos` within Indeterminate. *(Before the `decidible` gate fix from [ARD-03b](decisiones/ARD-03b.en.md), 2026-07-22, only 12 were rescued: the gate excluded 8 POs with measurable excess from Vendor attribution by not requiring that condition on its own.)* The quality flag that marks them is covered by `tests/test_pipeline_core.py`, and the breakdown is in `documentation/metricas-proyecto.md`.

12 temporal inversions. The flag `_ts_issue` marks 12 POs where `CHECKOUT_DT < CHECKIN_DT`, a sequence anomaly recorded in `documentation/data_dictionary.md`. The pipeline truncates the affected segment to zero (`clip ≥ 0`) instead of propagating a negative duration. Of those 12, 11 are the subset with a dock discrepancy greater than one hour compared to the precalculated column. Coverage is in `tests/test_pipeline_core.py`.

Round-trip CSV preserving `"Ninguno"`. Described in Layer B: the choice of sentinel `"Ninguno"` over `"None"` or the empty string prevents the signal of "no secondary stage" from being lost as NaN during serialization. Verified by `tests/test_handoff_contract.py`.

F1 population (39) and F2 population (31) that should not be confused. They come from different sets; before the `decidible` gate fix from ARD-03b (2026-07-22) they numerically coincided at 39, which made them easier to conflate — that coincidence is gone, but they still should not be mixed:

- In F1, 39 unreliable POs = 12 temporal inversions + 27 without trailer time, with zero overlap between the two groups, out of the 400 POs in the dataset. Baseline metrics are reported on the remaining 361 reliable ones.
- In F2, 31 Indeterminate POs = 7 `sin_datos` + 24 `sin_causa_dominante`, out of the 247 late POs. It is the population subtracted from the 247 to obtain the 216 evaluable for stage accuracy.

These are two different sets that coincidentally match in number; the document keeps them separate intentionally.

## LLM Severity Divergence vs Rule

The official severity of the deliverable is that of the LLM (ADR-10); the deterministic rule of F2 is preserved in the internal artifact as an auditing baseline, not as the source of truth. The two do not always match, and the discrepancy is a documented finding, not an error from either source.

Among the 247 late POs, `severity` (LLM) matches the severity of F2 in 213/247 (86.2%). The 34 divergences (13.8%) **always scale** — none descaled: 30 cases LOW→MEDIUM and 4 cases MEDIUM→HIGH. Interpretation: the LLM applies judgment over combinations of aggravating factors (hot PO, short ship, delay near the threshold) that the fixed rule does not distinguish, and that additional judgment never relaxes the alert against the rule — it always sustains or increases it.

Reproduction without spending API (both columns already live in generated artifacts):

```
# severity (LLM) vs severity (rule F2), by PO_NBR
# LLM:   data/processed/po_output.csv → column `severity`
#        (or data/processed/df_with_llm_full_openai.csv → column `llm_severidad`)
# Rule: data/processed/df_classified.csv → column `severity`
```

## Relation to the Rest of the Documentation

This document describes the method; the live figures and their sources are in `documentation/metricas-proyecto.md`, and the business reading of the mismatches is in `documentation/hallazgos-ai-vs-humano.md`. The root README will link this document as the validation section of the closure (pending wiring in #84).