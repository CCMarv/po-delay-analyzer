# Canonical Source Language and Naming Convention for Bilingual Documentation (ES→EN)

* **Status:** 🟢 **CURRENT** (ratified 2026-07-19; draft opened 2026-07-13)
* **Technical Context:** Documentation — Closure and deliverables; translation plan ES→EN
* **References:** Issue #88 (translation plan); Issue #96 (execution of the translation);
  `../plan-traduccion.en.md`; mentor's repo (kickoff ES + EN published as parallel artifacts);
  recognized practice "maintaining bilingual documentation source language"

## Context and Problem

Deliverables must be bilingual ES + EN, but currently all documentation is in Spanish. 
Translating before the source is validated forces re-translation of every correction, and 
without an explicit convention, the language pair diverges: no one knows which version is 
the true one when they differ. It is necessary to establish which is the source language 
and how the derived translation is named and maintained so that ES and EN do not 
separate throughout the project closure.

## Considered Options

### Option A: Independent Parallel Maintenance
Both languages are edited manually and separately, without source-derived relationship.
* **Pros:** Each language can be written with natural reading, without being tethered to the 
  structure of the other.
* **Cons:** The two languages inevitably diverge as the project corrects the content; 
  the correction effort is duplicated; there is no single source of truth to refer to in 
  case of a discrepancy. Discarded.

### Option B: Canonical Source ES + Derived Translation with `.en.md` Suffix
Spanish is the canonical; English is a derived version that is never edited 
independently. The files are siblings in the same folder (`README.md` / `README.en.md`).
* **Pros:** A single source of truth (ES); the `.en.md` is re-derived when the ES changes; 
  the naming convention is simple and makes the source↔translation relationship visible 
  in the repo tree, with no new folders or tools; replicates the mentor's kickoff pattern 
  (ES + EN parallels).
* **Cons:** Depends on human discipline (not editing the `.en.md` directly); the 
  re-derivation with each change from ES is manual.

### Option C: i18n Tooling
Automated extraction and merge with `gettext`/`.po` files, `locale/` folders, or a 
separate branch per language.
* **Pros:** Standard in software with internationalized UI; automates extraction and 
  reconciliation of strings.
* **Cons:** Over-engineering for a set of ~5–7 Markdown documents of an academic deliverable; 
  adds setup and maintenance curve without benefit at this volume. Out of scope; noted 
  as a possible future evolution if volume increases.

## Decision

**Option B** is adopted: canonical source language ES, derived translation EN with sibling 
file naming convention `.en.md`. The operational detail (scope, order, and trigger of 
the translation) resides in `../plan-traduccion.en.md`.

The bilingual scope of the deliverable covers the versioned, human-authored documentation of
the repository (cover page, phase READMEs, `SAD`/`SRS`, ADRs, and the readable Phase 3
evaluation reports) plus the presentation (ES + EN, produced separately). Raw benchmark
fixtures and internal process templates are out of scope, as they do not contribute to the
bilingual evaluation. The outputs the LLM emits per PO —the explanation and recommended
action in `po_output.csv`— are also out of this scope and remain in Spanish: they are
product output, not evaluation documentation, and duplicating them into English would load
API cost and the CSV contract without contributing to the bilingual goal. This is why issue
#96 (bilingual LLM explanations) is discarded; the governing bilingual plan is this decision
and its operational detail in `../plan-traduccion.en.md`.
