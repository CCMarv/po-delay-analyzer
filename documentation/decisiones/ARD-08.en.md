# stage_modifiers: conceived and eliminated

* **Status:** 📘 Superseded (Design decision discarded before final deployment)
* **Technical Context:** Phase 2 Closure / Attribute Optimization for LLM
* **References:** PR #74

## Context and Problem
During the intermediate design of Phase 2, the need to facilitate the interpretation work for the Language Model (LLM) that will operate in Phase 3 was raised. To this end, the creation of a unified metadata column called `stage_modifiers` was conceived, with the aim of consolidating special PO events (whether it was rescheduled, short shipped, or prioritized) into a single string or text array. The problem lay in evaluating whether this consolidation provided technical value or if it generated redundancy and biases in the data pipeline.

## Considered Options

### Option 1: Maintain and implement the consolidated column `stage_modifiers`
* **Pros:** Delivers a "chewed" and pre-digested attribute directly in the final table, reducing the number of columns that the LLM must read in a single row.
* **Cons:** Introduces an unnecessary artificial layer of abstraction. By packaging distinct variables into a single text field, the pure data is obscured, and an engineering interpretation bias is introduced into the data before it reaches the AI.

### Option 2: Eliminate the column and rely exclusively on clean native variables
Discard the `stage_modifiers` column before consolidating the main branch and expose the raw and separate contextual flags.
* **Pros:** Maintains a clean and normalized data model. Ensures that Phase 3 receives information transparently and without pre-imputed biases, allowing the LLM to infer the narrative directly from the objective facts of the data.
* **Cons:** Forces the prompt or architecture of Phase 3 to map and interpret multiple simultaneous boolean columns (`is_rescheduled`, `is_short_ship`, `HOT_PO_FLAG`).

## Decision
**Option 2** was chosen. It was decided to **definitively eliminate** the `stage_modifiers` column during the closure of Phase 2, a change that was recorded and executed in **PR #74**.

The final architecture determines that the operational context is already perfectly represented atomically by the variables `is_rescheduled`, `is_short_ship` (derived from `_short_ship`), and `HOT_PO_FLAG`. The creation of an intermediate column added complexity to the pipeline without providing new information. This architectural record is preserved to document historically **why this column does not exist** in the final model.

## Consequences
* **Positive:** Simplification of the database schema and the transformation code of the pipeline. The principle of "clean source of truth" is respected, ensuring that Phase 3 generates narratives based on pure data and not on biased intermediate interpretations.
* **Negative:** The configuration of the Phase 3 project must explicitly include in its data context the consumption and interpretation of the complete set of independent boolean flags.