# ADR-06a · Vendor-specific threshold: Initial model without threshold

* **Status:** 📘 **Superseded** by [ADR-06b · Vendor-specific threshold: Final configuration of 24h](ARD-06b.en.md)
* **Technical Context:** Phase 2 / Classification by Business Rules
* **References:** Initial implementation of the direct signal (`APPROVED_DT > STA_DT`)

## Context and Problem
When implementing the deterministic classifier based on the direct signal of Phase 2, a model was assumed where the Vendor did not require an initial tolerance. The problem was to purely measure any positive numerical deviation in the data pipeline.

## Considered Options

### Option 1: Keep Vendor without tolerance threshold (Initially chosen)
* **Pros:** Rawly reflects any minute delay in the approval of the order.
* **Cons:** Generates a severe artificial over-attribution (initially absorbing 62.8% of cases). Introduces a systemic bias that unfairly penalizes Vendor for insignificant delays, while Carrier and DC operated protected by strict thresholds (8h and 4/6h).

## Initial Decision
**Option 1** was adopted for the first functional iteration of the classifier, under the premise that late approval was mandatory by definition in the brief.

## Consequences of Its Fall
* **Construction Asymmetry:** During Round 2 of consultations (answered on 2026-06-18), the mentor pointed out that the model was unbalanced due to the lack of a threshold in Vendor that equated the rules of Carrier and DC.
* **Obsolescence:** It was immediately discarded to migrate towards an analytical study that determined a mathematically justified tolerance.