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

To correct the construction asymmetry identified in discussion [#57](#), this decision evolved later to integrate a restrictive tolerance threshold (`vendor_gap_hrs = 24h`), which is detailed separately in [ADR-06b](ARD-06b.en.md). The final code was deployed through a stack of Pull Requests ([PR #62](#), [PR #66](#), [PR #64](#)).

## Consequences
* **Positive:** The classifier is robust, secure, and capable of assessing 100% of the POs in the dataset (including the 27 without trailers). It complies with the clean design guidelines validated by mentorship.
* **Negative:** The introduction of the direct signal forced a rethinking of the treatment of edge cases and mathematical ties, necessitating the creation of a new support taxonomy for indeterminate orders (detailed in [ADR-07](ARD-07.en.md)).