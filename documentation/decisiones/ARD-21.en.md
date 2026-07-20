# Tier-1/Tier-2 Data Contract of `po_output.csv`

* **Status:** 🔵 **DRAFT** (to be concluded by the team)
* **Technical Context:** Phase 3 → Phase 4 — data contract of the only artifact consumed by
  `04_app` (Streamlit and the Telegram bot)
* **References:** Issue #158 (tier 1 — expand the contract with already computed columns), Issue
  #161 (tier 2 — persist the hybrid output of ARD-16), PR #174 (`--action-call`); ADR-09
  (people), ADR-10 (severity), [ARD-16](ARD-16.en.md) (track 1 — hybrid contract of the
  action call); `04_app/config.py` (canonical columns), `04_app/README.md:26-37`
  (exact documentation 33/33), `llm_integration.py` (`_ACTION_COLUMN_MAP`); parallel artifact
  `data/processed/agente1_raw.txt` and its generator
  `03_llm_integration/llm_integration_network_intelligence_view.py`

## Context and Problem

`po_output.csv` is the only input for `04_app` (both channels: Streamlit and the bot of
[ARD-20](ARD-20.en.md)) — without it, the app does not open. It has 33 columns, with no contract
registered in `documentation/decisions/` (`grep -rli tier documentation/decisions/` found no
results before this ARD). Two READMEs documented it differently:
`04_app/README.md:26-37` documents the 33/33 exact columns, while
`03_llm_integration/README.md` only documented 16 out of 33 (it became outdated, prior to
#158/#161) — with no design document declaring what "tier 1" and "tier 2" are conceptually or
why the contract was expanded in two steps.

Additionally, `data/processed/agente1_raw.txt` — the artifact that consumes the Network
Intelligence view (person Ravi) via `llm_integration_network_intelligence_view.py` — is a
real data dependency from Phase 3→Phase 4 that neither the SAD nor any ARD recognized (the SAD
even claimed the contrary). It is not part of `po_output.csv`, but shares lineage and deserves
to be declared in the same contract to keep it complete.

## Considered Options

**Option A — A single README as the source (`04_app/README.md`, already exact), without ARD.**
Pros: it already exists and is correct today. Cons: `documentation/decisions/` is where the
project registers data contracts with their rationale and traceability to the issues that decided
them (#158/#161); a consumption README does not replace that and does not prevent the second
copy (`03_llm_integration/README.md`) from becoming unsynchronized again without anyone
noticing.

**Option B — ARD that formally defines the contract, with `04_app/README.md` as a synchronized
operational copy (chosen).** The ARD establishes the vocabulary (what is tier-1, what is tier-2,
what distinguishes both from the base contract) and its traceability to #158/#161; `04_app/README.md`
remains the operational consumption table, its content is not duplicated here. Cons: a second
copy (`03_llm_integration/README.md`) still exists that must be corrected to avoid maintaining 3
versions of the same contract — correcting this page is a document synchronization task for another
unit (G8), not this ARD.

## Decision

**Tier-1 / Tier-2** is adopted as the official vocabulary of the F3→F4 contract, with this
partition (33 columns, scope: only delayed POs, `delay_days_calc > 0`):

1. **Base contract (16 columns, without tier numbering)** — identity and diagnosis of the mentor
   (`PO_NBR, stage, severity, explanation, action`), timeline (`PO_DT, STA_DT, APPROVED_DT,
   TRAILER_ARRIVE_DT, CHECKIN_DT, CHECKOUT_DT, RECPT_DT`), aggravating factors (`HOT_PO_FLAG,
   is_short_ship`) and agreement with human annotation (`REASON_DSC,
   llm_coincides_with_reason`). Preexisting to #158/#161; not touched here.
2. **Tier-1 (8 columns, #158)** — enrichment with already computed data upstream, without
   additional LLM call: `llm_confianza, VENDOR_NAME, CARRIER_PARTY_NAME, DC_LOC_NAME,
   delay_days_calc, excess_vendor_hrs, excess_carrier_hrs, excess_dc_hrs`. Provides context on
   responsible entities and excess hours per stage to the individual view (Diego).
3. **Tier-2 (9 columns, #161, PR #174)** — the hybrid output of the action call from
   [ARD-16](ARD-16.en.md) track 1: `llm_razonamiento, llm_hipotesis, llm_hipotesis_evidencia,
   llm_accion_inmediata, llm_accion_correctiva, llm_accion_preventiva, llm_hipotesis_alt,
   llm_paso_discriminante, llm_confianza_hipotesis`. Requires `--action-call` (opt-in): without
   that flag, the 9 columns output empty, not absent — the 33-column contract is stable
   regardless of the flag.
4. **`04_app/README.md:26-37` is the current operational copy** of the contract (verified exact
   33/33 against the real CSV); this ARD serves as its design and traceability record, not a
   parallel table to be manually synchronized.
5. **`agente1_raw.txt` is a parallel derived artifact, not part of `po_output.csv`.**
   Same lineage from Phase 3, but from another surface: produced by
   `llm_integration_network_intelligence_view.py` (governed by [ARD-19](ARD-19.en.md)) from
   scorecards, not from the CSV. It is only consumed by the Network Intelligence view (person
   Ravi). It is declared here to keep the F3→F4 data contract complete, although its
   content (narrative text by actor, not tabular columns) does not fit into the tier-1/tier-2
   vocabulary.

## Consequences

**Positive:**
- Provides a citable source for "what is tier-1/tier-2", with traceability to the issues that
  decided them — closes the gap that the closing audit marked as major debt (H3.12).
- Explicitly documents that the 33-column contract is stable with or without
  `--action-call` (prevents someone from interpreting empty columns as missing columns).
- Formally recognizes the dependency on `agente1_raw.txt`, closing the incorrect assertion
  of the SAD regarding the coupling of the Network Intelligence view.

**Negative:**
- `03_llm_integration/README.md` remains with the outdated contract (16/33 columns); this
  ARD does not correct it — it is a documentation synchronization task for another unit, with the risk
  that in the meantime a reader consults that page instead of `04_app/README.md`.
- The tier-1/tier-2 vocabulary names only 17 of the 33 columns; the 16 of the base contract
  lack their own numbering, which may be read as inconsistent if someone expects the entire CSV to be
  "tiered."

## Relation to Other Decisions

Does not supersede any previous ARD. Formalizes the result of #158/#161 (already implemented). Consumes
the output of **ADR-10** (severity) and track 1 of **ARD-16** (hybrid contract of tier-2).
It is the contract that consumes [ARD-20](ARD-20.en.md) (Telegram bot) in addition to the two Streamlit views of
**ADR-09**. Declares the dependency toward [ARD-19](ARD-19.en.md) via `agente1_raw.txt`, although that artifact
does not form part of `po_output.csv`.