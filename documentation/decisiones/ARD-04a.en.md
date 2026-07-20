# ADR-04a · Provisional Carrier Threshold (4h)

* **Status:** 📘 **SUPERSeded** by the [ADR-04b · Definitive Carrier Threshold (8h)](ARD-04b.en.md)
* **Technical Context:** Phase 1 / Exploratory Data Analysis (EDA)
* **References:** Initial hard-coded configuration

## Context and Problem
The carrier requires a tolerance threshold to activate its delay flag. During Phase 1 and the Exploratory Data Analysis (EDA), a strict provisional limit of 4 hours was adopted with the intention of early alerting to any logistical deviation in shipments.

## Considered Options

### Option 1: Establish a Provisional Threshold of 4 Hours (Initially Chosen)
* **Pros:** Strict criterion that does not allow any micro-delay in transportation.
* **Cons:** When applied to the actual dataset of the project, it proved to be too sensitive for a dataset composed mainly of short routes, generating false positives and operational noise in the business.

## Initial Decision
**Option 1** was provisionally chosen for the first iteration of the pipeline during the EDA of Phase 1.

## Consequences of Its Failure
* **Mass Over-attribution:** The threshold triggered the delay flag in 25.8% of cases (103 POs), over-penalizing the Carrier for insignificant minor delays.
* **Obsolescence:** It was discarded on 2026-06-16 following the mentor's suggestion in discussion #53 to allow for a formal sensitivity analysis.