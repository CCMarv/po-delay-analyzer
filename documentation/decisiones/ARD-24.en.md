# Late Shipment rule from the README: discarded due to a nonexistent column

* **Status:** 🟢 **Active**
* **Technical Context:** Phase 2 / Classification rule design — a rule inherited from the
  README/kickoff, never implemented
* **References:** README of the mentor's original repo (`VENDOR_SHIP_DT > STA_DT` rule);
  Issue #17 (proxy test and discard); [ADR-03b](ARD-03b.en.md) (STA Push, current vendor
  signal); `.claude/brief_proyecto.md`

## Context and Problem

The mentor's original repo README defines "Late Shipment" as a vendor cause with the rule
`VENDOR_SHIP_DT > STA_DT`. The `VENDOR_SHIP_DT` column does not exist in any of the 39
columns of the real CSV — it appears in the kickoff with no definition and no entry in the
key-fields list, an orphaned rule from the source. The discard already happened de facto
(neither the rule nor a working proxy was ever implemented), but it lived scattered across
the brief and issue #17, with no formal record in `documentation/decisiones/`: an evaluator
looking for this README rule finds no documented discard.

## Options Considered

**Option A — Leave it undocumented (status quo).** Pros: zero effort. Cons: the rule is
still cited in the mentor's README; without an explicit record, it reads as a team oversight
rather than a deliberate, justified discard.

**Option B — Short lead-time proxy (`STA_DT − PO_DT < 3 days`) as a cause classifier.**
Tested in #17: fires on 0% of cases on the real dataset — it discriminates nothing, since it
measures vendor planning, not shipment execution. Discarded as a stage classifier.

**Option C — Formally document the discard, without implementing any variant (chosen).**
Given that the column doesn't exist and the only tested proxy discriminates nothing, there is
no viable version of this rule for the current dataset. The real vendor signal is already
covered by STA Push (ADR-03b/06b), which depends on neither `VENDOR_SHIP_DT` nor the
lead-time proxy.

## Decision

Late Shipment is not implemented as a stage classification rule. Two independent reasons,
either one sufficient on its own:

1. **The column doesn't exist.** `VENDOR_SHIP_DT` is not among the 39 columns of the real
   CSV; there is no way to compute the rule as the mentor's README describes it.
2. **The tested proxy doesn't discriminate.** `STA_DT − PO_DT < 3 days` (a short-lead-time
   approximation) was tested in #17 and fired on 0% of POs — it doesn't separate cases, so it
   doesn't work as a cause signal even if accepted as a substitute for `VENDOR_SHIP_DT`.

Vendor responsibility is already covered by **STA Push** (`APPROVED_DT > STA_DT`,
[ADR-03b](ARD-03b.en.md)/[ADR-06b](ARD-06b.en.md)), which depends on neither column in
question and does have measured discriminating power. `lead_time_days`
(`STA_DT − PO_DT`) is kept only as a potential **severity** input, not a stage input — it is
not implemented in that role here; it remains a future candidate if the team decides to
weigh it.

## Consequences

**Positive:** closes the traceability gap between the mentor's README and the project's
current rules — an evaluator asking about "Late Shipment" gets a citable answer with its
reasoning, not silence. Introduces no code and does not change the current `stage_primary`
distribution.

**Negative:** no variant of the rule remains available even as a secondary stage input; if a
real vendor shipment-date column appears in the future, this ARD should be revisited (not
blindly chained from).

## Relationship to Other Decisions

Does not supersede any prior ARD — it documents a discard that **ADR-03b** (STA Push)
already makes unnecessary as a stage classifier. Does not reopen **ADR-07**'s
(Indeterminate) taxonomy.
