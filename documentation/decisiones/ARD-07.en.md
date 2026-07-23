# Indeterminate Taxonomy

* **Status:** 🟢 Current
* **Technical Context:** Phase 2 Closure / Exception Modeling and Data Quality
* **References:** Round 2 Query (Mentor, 2026-06-18), Discussion #57, PR #62

## Context and Problem
By raising the Vendor threshold to 24 hours (see [ADR-06b](ARD-06b.en.md)) and evaluating orders with incomplete records, cases emerged where an order was considered late but could not be assigned direct responsibility to any of the three main actors (Vendor, Carrier, or DC). The design challenge was to classify these orders without forcing an incorrect assignment by elimination, which would reintroduce biases into the model and alter business metrics.

## Considered Options

### Option 1: Send ambiguous cases to Vendor by elimination
* **Pros:** Maintains a simple model with few main categories.
* **Cons:** Violates the mentor's explicit guideline. Quietly reintroduces the bias of over-attribution and unfairly penalizes the Vendor for data quality issues or tolerable micro-delays.

### Option 2: Create a new sibling stage at the top level of the classifier
* **Pros:** Visually separates the issues from the rest of the actors at the first level of the report.
* **Cons:** Breaks the business architecture based on the three pillars of the supply chain, overly complicating macro queries of the pipeline.

### Option 3: Design an internal sub-taxonomy within the "Indeterminate" category
Implement a complementary analytical variable (`indeterminado_substage`) that segregates the root cause in isolation, keeping the top-level status as "Indeterminate".
* **Pros:** Solid and clean. Follows the existing design pattern in the project for the Distribution Center (`dc_substage`). It was the mentor's explicit recommendation (Option B from the verdict of 2026-06-18).
* **Cons:** Forces the team to support and maintain a new column and to document its activation criteria with mathematical precision.

## Decision
The **Option 3** was chosen. The **`indeterminado_substage`** column was implemented in the data model to strictly divide the 39 orders assigned to this category under two mutually exclusive criteria:

1. **`sin_datos`** (15 POs): The order exhibits a measurable physical delay in the final dates but lacks atomic data at the source to audit the segments (e.g., late orders without trailer record / `NaN`).
2. **`sin_causa_dominante`** (24 POs): The order has 100% complete audit data, but after applying symmetrical business thresholds (8h Carrier, 4/6h DC, 24h Vendor), **none of the segments exceeded their respective tolerance**.

This logic was integrated into the classifier architecture and was deployed in the repository through Pull Request **#62**.

## Consequences
* **Positive:** The classifier achieves absolute conceptual purity. Blind elimination is avoided, and Phase 3 is provided with a clean data structure that allows the LLM to understand the exact difference between "lack of information" and "efficient operation within permitted tolerances."
* **Negative:** The final business reporting must be aware of this sub-taxonomy to avoid misinterpreting all "Indeterminate" cases as critical failures of the data extraction system.

## Note (2026-07-22)
The counts cited above (39 orders, 15 `sin_datos`, 24 `sin_causa_dominante`) reflect the split
in effect when this decision was closed (2026-06-18). The closing note of
[ADR-03b](ARD-03b.en.md) (2026-07-22) fixed a classifier gate that excluded Vendor without its
own condition: 8 of the 39 orders migrated from `sin_datos` to Vendor, leaving the current
split at 31 (7 `sin_datos` + 24 `sin_causa_dominante`). This decision is not reopened — the
sub-taxonomy and its two mutually exclusive criteria remain current exactly as described
above.