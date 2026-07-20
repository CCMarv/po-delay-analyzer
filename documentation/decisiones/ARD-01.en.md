# Source of Truth for Flags: calc vs. precalc

* **Status:** 🟢 Current
* **Technical Context:** Phase 2 (Implementation of baseline metrics)
* **References:** Issue #15

## Context and Problem
The data source provides certain precalculated delay flags (`precalc`). However, the initial project brief strictly stipulates that audit timestamps take precedence over any other metrics. We need to define where subsequent pipelines will consume data to avoid inconsistencies in the reporting of delay taxonomy.

## Considered Options

### Option 1: Rely on the precalculated flags from the data source
* **Pros:** Requires less computational effort in the early stages of the pipeline.
* **Cons:** Risk of "black box"; if there is a change in the business logic upstream, we lose traceability and violate the brief's constraint that mandates auditing through timestamps.

### Option 2: Dynamically recalculate all derived metrics from the timestamps (`*_calc`)
* **Pros:** Total alignment with the project brief. Guarantees absolute mathematical consistency as the raw data prevails and is transparently exposed.
* **Cons:** Slightly increases the complexity of the transformation code in the intermediate layer.

## Decision
The **Option 2** was chosen. All derived metrics and delay indicators are dynamically recalculated at runtime from the `*_calc` variables using audit timestamps. The original `precalc` variables are relegated exclusively to secondary cross-checking tasks to alert deviations from the source.

## Consequences
* **Positive:** End-to-end traceability in the delay calculation and compliance with the audit rubric.
* **Negative:** Maintenance and governance must be provided for the logic block of delay calculation in the project pipeline.