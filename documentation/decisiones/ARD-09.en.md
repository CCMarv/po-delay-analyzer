# ADR-09 · User Personas as Design Criteria for Phase 4

* **Status:** 🟢 **CURRENT** (closed 2026-06-27)
* **Technical Context:** Phase 4 Design (Demo + application) / Business Relevance
* **References:** Mentor recommendation (sync 2026-06-26); Issues #102, #103; handoff contract #100; `../user_personas.en.md`

## Context and Problem
Mentors recommended using *user personas* to guide the design. Phase 4 already has a placeholder app (`../../04_app/`) organized by entity in the chain (Vendor/Carrier/DC), created to have a presentable before Phase 3 establishes its output. An explicit and defensible criterion is needed to guide the redesign of Phase 4 once the F3→F4 contract (#100) closes, connecting the app views with a user model, not with an organization by measurement subject. The problem: what axis defines the user-facing tool, and how is that axis traced to the data artifact and the board?

## Considered Options

### Option 1: Two personas by mode of consumption — individual vs. batch (Selected)
Define two profiles —Diego (individual consultation of a PO, consumes the prose of the LLM) and Ravi (aggregated report by batch, consumes metrics and drill-down)— and derive from them the two views of the tool.
* **Pros:** The "mode of consumption" axis maps 1:1 to the two views that the mentor requests (individual view #102, aggregated view #103). It is cause-agnostic, so it does not get confused with the taxonomy of stages. It makes auditable which columns of the artifact each view consumes, connecting to contract #100.
* **Cons:** Does not match the organization by entity of the current placeholder; forces acknowledgment that this placeholder will be redesigned.

### Option 2: Profiles by entity in the chain (Vendor/Carrier/DC)
Treat each stage owner as a user and organize the tool by entity, as the placeholder does.
* **Pros:** Matches the already constructed app; does not require immediate rework.
* **Cons:** Confuses measurement subject with user —the vendor and the carrier are measured, not operating the tool—. Does not distinguish the mode of consumption (individual vs. batch), which is the real axis of the two views. Multiplies screens by entity instead of two views by mode of consumption.

## Decision
**Option 1** is chosen. The two personas (Diego, Ravi), defined by mode of consumption, are the design criteria for the final Phase 4: two personas, two views of the program. The detail resides in `../user_personas.en.md`; this record establishes the decision and its rationale. The current app remains as a placeholder; its redesign will be done against these personas once the F3→F4 contract (#100) is closed. The fate of the screens by entity in the placeholder (whether they survive as sections, filters, or drill-down within the aggregated view) remains an open decision in the redesign, not committed here.

## Consequences
* **Positive:** Traceability persona→view→issue (#102/#103) and persona→columns of the artifact. Directly covers the rubric *Business Relevance & Stakeholder Insight*. Provides a criterion to avoid reworking the input for Phase 4 blindly.
* **Negative:** Explicitly acknowledges that the entity placeholder will be redesigned; the drill-down bridge Ravi→Diego remains as pending design.

## Closure (2026-06-27)
Ratified as the design criterion for Phase 4: the individual view (#102) responds to Diego (PO consultation, consumes the prose of the LLM) and the aggregated view (#103) to Ravi (batch report, consumes metrics and drill-down). The F3→F4 contract (#100) is now closed, so the redesign of the app against these personas —and the migration of their input to the artifact `po_output.csv`— can proceed without further delay. The detail of the personas resides in `../user_personas.en.md`. The decision moves from Draft to Current.