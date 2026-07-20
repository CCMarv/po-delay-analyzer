# Fixtures — Phase 3

Human validation records of the quality benchmarks for F3. These are not automated test fixtures: F3 tests use their own stubs, not these files.

## What's Here

- `eval_quality_20pos_C1.md` / `_C2.md` / `_C3.md` — quality benchmark (#94) by few-shot configuration (1/2/3 examples), at the anchor temperature (0.3). C3 won (see [`../README.en.md`](../README.en.md#status-of-few-shot)).
- `eval_quality_20pos_C3_t05.md` / `_t07.md` / `_t09.md` — re-validation of C3 at other temperatures (ADR-13); `_t09.md` is the re-validation at the actual production temperature (20/20, headline figure of the deliverable).
- `eval_quality_20pos_C0_t09.md` — baseline zero-shot at temp 0.9 (comparison, this is not the production figure).
- `eval_quality_20pos_C0_t09_accion_*.md` — quality control of the tier-2 differential diagnosis (ARD-16), by wave of iteration of the action prompt; `_kb.md` is the variant with conditional domain context (ADR-15, superseded).
- `archive/` — intermediate waves of tier-2 quality control, superseded by the version mentioned in README/ARD-16; they are retained for traceability, these are not the current source.
- `mismatches_llm_zeroshot.csv` — raw mismatches from the baseline zero-shot, input for [`../mismatches_ai_vs_humano.en.md`](../mismatches_ai_vs_humano.en.md).

Each benchmark cited as the source of a current figure is linked from [`03_llm_integration/README.md`](../README.en.md), `documentation/metricas-proyecto.md`, or the corresponding ARD (12/13/15/16); this index only indicates which file is which, it does not replace those references.