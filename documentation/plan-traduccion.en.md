# ES→EN Translation Plan for the Deliverables

This document fixes the ES→EN translation plan for the project's documentation: the scope,
the order, the trigger, and the maintenance method. The scope described below has already
been executed; this document remains as the living record of the method (the `.en.md` is
re-derived when its ES source changes).

The evaluation rubric (mixed audience) and the mentor's kickoff request bilingual ES + EN
deliverables; the mentor's own repository publishes the kickoff in both languages as parallel
artifacts. Originally the team's decision was to defer translation until the ES source was
validated and stable, so as not to duplicate work re-translating every correction. The
translation was executed as part of the project closure, once the ES reached that stable
state (see "Trigger" below).

## Scope

The executed scope covers the versioned, human-authored documentation of the repository:

- Cover page (`README.md`, `CONTRIBUTING.md`).
- Phase READMEs (F1–F4) and the Phase 3 model card.
- Readable Phase 3 evaluation reports (`eval_differentiation.md`, `eval_quality_20pos.md`,
  `eval_severity_ranking.md`, `mismatches_ai_vs_humano.md`).
- General documentation (`SAD.md`, `SRS.md`, `data_dictionary.md`, `explicacion-proyecto.md`,
  `hallazgos-ai-vs-humano.md`, `metricas-proyecto.md`, `plan-traduccion.md`, `user_personas.md`,
  `validacion-y-qa.md`, `convenciones-issues.md`).
- Decision log (`decisiones/README.md` + `ARD-01.md` … `ARD-23.md`, 27 files).
- Presentation (ES + EN, produced separately from this document's flow).

Out of scope: raw benchmark run fixtures (`03_llm_integration/fixtures/*.md`, except its
`README.md`), internal process templates (`documentation/plantillas-cli/*.md`,
`.github/pull_request_template.md`), and the LLM outputs per PO (explanation and recommended
action from `po_output.csv`) — see ADR-18 and the closure of issue #96 for why this last one
was discarded.

## Order

The translation moved from the outside in, starting with what the mentor evaluates first:
cover page → general documentation → decisions (ADRs) → phase READMEs and model card →
evaluation reports.

## Trigger (gate)

This plan's original gate was the mentors' validation of the Spanish documentation. In
practice, the translation was executed as part of the project's closure (2026-07), once the
ES reached a stable state after the closure documentation synthesis (G0–G8 of the closure
orchestration), without waiting for explicit formal validation from the mentors. The gate's
principle still holds for any new or remaining document: no `.en.md` is derived from an ES
source that is still under active discussion.

## Maintenance method

Spanish is the canonical source language and English is a derived translation: the `.en.md`
is never edited independently. When the ES source changes after having been translated, the
`.en.md` is re-derived from the ES; in case of any discrepancy, the ES governs.

The naming convention is a sibling file with the `.en.md` suffix next to the source, so that
the source↔translation relationship is visible in the repository tree without additional
folders or tools:

- `README.md` → `README.en.md`
- `documentation/metricas-proyecto.md` → `documentation/metricas-proyecto.en.md`
- `documentation/hallazgos-ai-vs-humano.md` → `documentation/hallazgos-ai-vs-humano.en.md`

The complete trade-off of this choice (canonical source + derivation vs. independent parallel
maintenance vs. i18n tooling) is recorded in
[ADR-18](decisiones/ARD-18.en.md).

## Issue status

Issue #88 (which documented this plan) is closed: its scope —document the plan, not
translate— was fulfilled. Issue #96 (bilingual LLM explanations) was closed as discarded: that
output remains in Spanish (see ADR-18). The translations of the scope described above already
exist as sibling `.en.md` files in the repository.
