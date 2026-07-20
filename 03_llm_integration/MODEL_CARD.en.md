# Model Card — Root Cause Explanation System (Phase 3)

Card for the Phase 3 system following *Model Cards for Model Reporting* (Mitchell et al., 2019). A model is not trained: a pre-trained LLM is used with a prompt and input data, and that use has definable limits. Phase 3 is ongoing; this card describes what is stable and what is pending. The prompt design is in [README §Prompt Design](README.en.md#prompt-design).

## Model Details

The system is an explanation layer for late POs based on the deterministic output of Phases 1-2 (stages, excesses, flags, audited severity). It receives already calculated facts and produces an explanation, an action, and a severity.

- **Model that produced the deliverable:** `gpt-4o-mini` (OpenAI), the official backend. Inference parameters: temperature 0.9, seed 42 (best-effort from the OpenAI API), max_tokens 512 in the diagnostic call and 1536 in the action call. Prompt: few-shot C3 (ADR-12/#99).
- **Default models from alternative backends:** `claude-sonnet-4-6` (Anthropic), `deepseek-chat` (DeepSeek), `qwen2.5:7b` (local via Ollama). All four share the same prompt and parsing interface; the `po_output.csv` of the deliverable was generated with OpenAI, not with the others.
- **Configuration:** versioned in `llm_config.json` (reproducible inference) and `.env` (operational). The prompt is constructed by `build_prompt()`, the only source.
- **Date and owner:** Phase 3 ongoing (2026); PO Delay Analyzer team. The LLM is the product engine, not a development assistant.

## Intended Use

To generate, for late POs, a root cause explanation, a recommended action for the responsible party, and a severity, for supply chain analysts. The Phase 4 app reads the result from `po_output.csv` (contract F3→F4). The model interprets metrics that have already been calculated; its value is to translate the measured signal into actionable language.

## Out of Scope

- Does not classify the stage of delay: this is decided by the deterministic logic of F2 (`stage_primary`). The model names that stage, it does not re-decide it.
- Does not recalculate dates, times, or metrics: the prompt prohibits it (ADR-14) and requires quoting the provided figures.
- Does not execute or decide autonomously: the output is an input for human review.
- Does not judge real entities: the dataset is synthetic; the names of vendors and carriers do not correspond to real organizations.

## Input Data

- Per PO: timeline (key dates), excess per stage, classification from F2, aggravating factors (hot PO, short ship, reschedule) and `REASON_DSC`. Details in the README.
- Row scope: only late POs (`delay_days_calc > 0`), 247 in the current dataset.
- Few-shot examples (C3): three audited mismatches from F2 (one per attributable stage), disjoint from the evaluation benchmark.

## Evaluation Metrics

*LLM Explanation Quality* metric (benchmark of 20 POs, stratified sample, seed 42), three binary checks per PO: correct stage, quantifies the delay, viable action.

| Configuration | Verdict | Source |
|---|---|---|
| Zero-shot (C0) | 13/20 (3.25/5) | `eval_quality_20pos.en.md` |
| Few-shot C3 at temp 0.3 | 19/20 (4.75/5) | `eval_quality_20pos.en.md` (#99) |
| Few-shot C3 at temp 0.9 (production) | 20/20 (5/5), human validation | `fixtures/eval_quality_20pos_C3_t09.md` |

The deterministic rule of F2 audits the LLM's severity against the mentor's goal (Severity Ranking >95%). The dataset-level evaluation that replaces the 20 POs fixture is under development (ARD-16).

## Source of Severity

The official severity of the deliverable is **issued by the LLM** (`llm_severidad` → `severity` in `po_output.csv`), according to ADR-10 (hybrid option): the kickoff defines it as the model's output. The deterministic rule of F2 (`flag_hot_late & delay_days_calc > 3`) is maintained as an audit column outside of the deliverable and feeds the Severity Ranking metric. The prompt provides the severity rules, but the decision is made by the model; the LLM-vs-rule discrepancy is a reportable finding, not an error.

## Limits and Risks

- **Variability between runs:** severity and wording are not fully reproducible despite the best-effort seed; the severity of the deliverable is not deterministic by design (ADR-10).
- **Homogenization of actions:** at fixed temperature, actions tend to converge to the same form within each stage. The measured cause is lack of context per PO, not the temperature or the few-shot; this remains open work (#151/#122).
- **C3 × tier-2 interaction without combined gating:** the action plan (ARD-16, `--action-call`) was validated with the diagnostic call in zero-shot. The deliverable combines C3 in call 1 with tier-2 without a joint measurement of both (ARD-16 §9). This is a known limit documented, not a blocker.
- **Anti-hallucination perimeter:** PO facts come only from the data, with quoted figures; domain generalizations are allowed marked in the output (ADR-14/ARD-16). The marking is audited by human sample.
- **Vendor dependence:** the deliverable uses OpenAI; changing backends changes the output and requires re-validation.

## Ethical Considerations

- The system is assistive: actions are reviewed by a person before use; it is not a decision-maker.
- The human `REASON_DSC` is incorrect in about 20% of cases. Discrepancies between annotation and measured time signal are findings of the project (measured exceeds annotation), not errors to be silently corrected.
- No personal data: the dataset is synthetic.

## Status

Phase 3 ongoing. Stable: the operational prompt (`build_prompt`), the few-shot C3, the parsing (`_parse_llm_json`) and the four backends. In development: dataset-level evaluation and local quality judge (ARD-16). The scope of this model card with the open phase is debated in the discussion linked to issue #87.

## References

Mitchell et al. (2019), *Model Cards for Model Reporting*. Project decisions: ADR-10 (hybrid severity), ADR-12 (prompt design / few-shot), ADR-13 (temperature), ARD-16 (analytical layer and action call).