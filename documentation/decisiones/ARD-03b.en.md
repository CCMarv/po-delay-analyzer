# ADR-03b · VENDOR Stage: Measurement by Direct Signal STA Push

* **Status:** 🟢 **CURRENT** (Replaces [ADR-03a · VENDOR Stage: Initial Measurement by Operational Residual](ARD-03a.en.md))
* **Technical Context:** Phase 2 Closure / Dominant Attribution Modeling
* **References:** Issue #40, Discussion #57, PR #62, PR #64, PR #66 (Validated by mentor on 2026-06-16)

## Context and Problem
After the obsolescence of the residual model (detailed in [ADR-03a](ARD-03a.en.md)), the main challenge was to measure the segment fairly without assuming nonexistent additive behaviors in the chain, ensuring 100% dataset coverage, including the 27 Purchase Orders (POs) that lack trailer records.

## Considered Options

### Option 1: Attribution by Direct Signal STA Push (`APPROVED_DT > STA_DT`) (Chosen)
Direct measurement of the temporal offset using the native business audit events: the date the shipment is approved (`APPROVED_DT`) against the originally planned arrival date (`STA_DT`).
* **Pros:** It is the organically stipulated rule from the project kickoff. It does not depend on the existence of additive segments and resolves the measurement for the 27 critical POs without trailers.
* **Cons:** If applied directly and loosely without a tolerance threshold, it results in massive over-attribution (initially absorbing 62.8% of cases) due to asymmetry with Carrier and DC.

*(Note: The residual model was no longer considered a viable option at this stage due to its structural flaws).*

## Final Decision
**Option 1** was chosen. After validation with the mentor on 2026-06-16, the **Direct Signal STA Push** is adopted as the standard for measuring Vendor. 

To correct the construction asymmetry identified in discussion [#57](https://github.com/CCMarv/po-delay-analyzer/discussions/57), this decision evolved later to integrate a restrictive tolerance threshold (`vendor_gap_hrs = 24h`), which is detailed separately in [ADR-06b](ARD-06b.en.md). The final code was deployed through a stack of Pull Requests ([PR #62](https://github.com/CCMarv/po-delay-analyzer/pull/62), [PR #66](https://github.com/CCMarv/po-delay-analyzer/pull/66), [PR #64](https://github.com/CCMarv/po-delay-analyzer/pull/64)).

## Consequences
* **Positive:** The classifier is robust, secure, and capable of assessing 100% of the POs in the dataset (including the 27 without trailers). It complies with the clean design guidelines validated by mentorship.
* **Negative:** The introduction of the direct signal forced a rethinking of the treatment of edge cases and mathematical ties, necessitating the creation of a new support taxonomy for indeterminate orders (detailed in [ADR-07](ARD-07.en.md)).

## Closing Note (2026-07-22)
The ADR↔repo audit found that the claim above ("resolves the measurement for the 27 POs without
trailer time") did not hold in the code: the `decidible` gate in `classifier_core.py` (and its
replica in `metrics_core.py::_simular_corte`) required carrier or DC to be measurable in order to
attribute any stage, even though vendor's excess (`excess_vendor_hrs`) does not depend on
`TRAILER_ARRIVE_DT`. Of the 15 late POs without a trailer, 8 (22.6-92.5h of excess) fell into
`Indeterminado/sin_datos` by default despite having a clear vendor signal. The gate was fixed to
`decidible = _carrier_medible | _dc_medible | (exc_vendor > 0)` in both files.

Unlike the closing notes of [ADR-11](ARD-11.en.md) or [ADR-06b](ARD-06b.en.md) —which
reconciled code/documentation without touching real classification—, **this fix does change
real classification**: 8 POs move from Indeterminate to Vendor (split over 247 late POs: Vendor
131→139, Indeterminate 39→31; Stage accuracy 208/208→216/216, still 100%; Reason agreement
88.8%→88.7%, no material change). The direct-signal STA-push measurement principle is not
reopened (still **current**, validated by the mentor on 2026-06-16): the correction is confined
to the `decidible` gate's implementation, a construction detail the team itself, unknowingly,
had already brushed against in [ADR-14](ARD-14.en.md) (2026-07-19) from the Phase 3 presentation
angle, without reaching the classifier itself.

The persisted artifacts `data/processed/df_classified.csv`/`po_output.csv` (gitignored, not
versioned) still reflect the previous split; regenerating them correctly —so the Phase 3
explanations for the 8 POs stop narrating "Indeterminate"— requires a full `--mode full` run
(~247 POs against the production backend), pending separate explicit authorization (not
included in this audit correction).