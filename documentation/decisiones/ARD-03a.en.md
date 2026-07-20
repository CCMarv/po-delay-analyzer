# ADR-03a · VENDOR Stage: Initial Measurement by Operational Residual

* **Status:** 📘 **SUPERSeded** by the [ADR-03b · VENDOR Stage: Measurement by Direct Signal STA push](ARD-03b.en.md)
* **Technical Context:** Phase 2 / First Delay Attribution Model
* **References:** PR #59 (Released on June 15, 2026)

## Context and Problem
The initial model required a methodology to accurately attribute the delay corresponding to the Vendor. A mathematical approach was sought to explain the total deviation within the data pipeline.

## Considered Options

### Option 1: Vendor Attribution by Operational Residual (Initially Chosen)
Calculation based on subtracting the total demerit time from the times attributable to the Carrier and Distribution Center (DC): `Delay − Carrier − DC`.
* **Pros:** Allows for an exact mathematical closure where the sum of the parts equals the total delay of the order.
* **Cons:** Incorrectly assumes that all segments of the chain are perfectly additive and mutually exclusive. Completely fails for the 27 POs that have no trailer record, breaking the integrity of the pipeline.

### Option 2: Attribution by Direct Signal STA push (`APPROVED_DT > STA_DT`)
Direct measurement of the time offset using the business's native audit events: the date when the shipment is approved (`APPROVED_DT`) against the originally planned arrival date (`STA_DT`).
* **Pros:** Does not depend on the existence of additive segments and resolves measurement for the 27 critical POs without trailers.
* **Cons:** If applied directly and loosely without a tolerance threshold, it generates massive overattribution.

## Initial Decision
**Option 1** was chosen due to the simplicity of the additive mathematical closure. It was provisionally implemented in [PR #59](#).

## Consequences of Its Failure
* **Integrity Failure:** It was found that the assumption of additive segments breaks the analysis in the 27 POs without trailers. 
* **Obsolescence:** The rule was discarded after the review session with the mentor to transition to a model based on direct signals.