# ADR-06b · Vendor's own threshold: Final configuration of 24h

* **Status:** 🟢 **CURRENT** (Replaces [ADR-06a · Vendor's own threshold: Initial model without threshold](ARD-06a.en.md))
* **Technical Context:** Phase 2 Closure / Sensitivity Analysis and Calibration
* **References:** Mentor Round 2 consultation (2026-06-18), Discussion #57, PR Stack #62, #66, and #64

## Context and Problem
After detecting the asymmetry in the construction of the initial model (detailed in [ADR-06a](ARD-06a.en.md)), it was necessary to balance the classifier with a symmetric threshold for Vendor that eliminated insignificant micro-delays, but without artificially altering the actual distribution of the business.

## Considered Options

### Option 1: Implement an adaptive threshold through sensitivity analysis (Selected)
Run a test matrix evaluating thresholds of 6, 12, 18, 24, 48, and 72 hours to identify the actual behavior of the raw data and its impact on assignments.
* **Pros:** Scientifically grounded. Allows discovery of hidden business patterns and decouples tolerance in centralized configuration files.
* **Cons:** Requires secondary development effort to assess the sensitivity of the volume of affected orders.

## Final Decision
The **Option 1** was chosen. After conducting sensitivity analysis on 247 late POs, it was discovered that the Vendor delay distribution is **bimodal**: 12 POs cluster in micro-delays (≤ 6h), 141 POs present critical delays (≥ 18h), and there is a **complete empty gap between 6h and 18h**.

It was definitively set **`vendor_gap_hrs = 24h`** in the **`rules_config.json` (v3)** file due to:
1. **Natural aggregation level of the data:** The planned variable `STA_DT` is recorded at midnight without hour breakdown. 24 hours represents a full calendar day (the real unit of the problem).
2. **Mathematical robustness:** Falling exactly within the empty gap of the distribution (6-18h), any minor adjustment to the threshold does not destabilize or alter the final distribution.
3. **Respect for the data:** The model organically reduces Vendor attribution to 53.0% (131 POs), complying with the mentor’s directive not to force an "artificial 20% kickoff".

The calculation of the variable `_primary_stage` was normalized to `max(0, push − 24)`, making it symmetric with other actors and releasing changes through the PR stack [#62](https://github.com/CCMarv/po-delay-analyzer/pull/62), [#66](https://github.com/CCMarv/po-delay-analyzer/pull/66), and [#64](https://github.com/CCMarv/po-delay-analyzer/pull/64).

## Consequences
* **Positive:** Definitive elimination of the construction asymmetry and high stability of the pipeline. It was verified that hardening the threshold increased agreement with human annotation (*Reason agreement*) from 88.7% to 89.7%.
* **Negative:** Orders excluded by the 24h threshold are no longer assigned to Vendor; as demonstrated through the migration analysis that they did not belong to Carrier or DC, they required a new neutral classification structure (detailed in [ADR-07](ARD-07.en.md)).

## Closing Note (2026-07-22)
The ADR↔repo audit found that the figure cited above ("from 88.7% to 89.7%") corresponds to the 72h scenario of the sensitivity grid, not the 24h threshold actually adopted. Recalculating `agreement_por_umbral()` on the real dataset, the 24h threshold yields **88.7%** (matching `02_clasif_reglas_negocio/README.md` §5.4; figure recalculated after the `decidible` gate fix from [ADR-03b](ARD-03b.en.md), applied the same day — before that fix it was 88.8%). The definitive 24h threshold does not change; only the reinforcing figure cited in Consequences is corrected — no option is reopened.

Additionally, the same `decidible` gate fix that corrected the agreement figure above also made the distribution figure in item 3 of "Final Decision" stale: "Vendor at 53.0% (131 POs)" becomes **56.3% (139 POs)**. The 24h threshold does not change — this is a downstream consequence of the classification fix in [ADR-03b](ARD-03b.en.md), not a revision of the threshold.