# Reschedule and Short-Ship: Context, Not Stage

* **Status:** 🟢 Current
* **Technical Context:** Phase 2 / Attribution Model Refinement
* **References:** Issue #42, Discussion #54

## Context and Problem
During operational analysis, events such as date rescheduling (*reschedule*) and incomplete shipments (*short-ship*) were identified as critical sources of friction. The design problem was whether these events should be treated as independent "delay stages" within the dominant classifier or if they belonged to another dimension of the data model, given that their nature differs from physical segments like Carrier or DC.

## Considered Options

### Option 1: Treat Reschedule and Short-Ship as Primary Attribution Stages
* **Pros:** Allows for direct assignment of blame for the delay to these events if they occur in the timeline of the order.
* **Cons:** Conceptual and methodological error. A *reschedule* describes a logistical event, but the raw data does not specify which actor requested it (Vendor, Customer, or Carrier), so it is not a root cause. Assigning it as a stage introduces unsustainable biases.

### Option 2: Model Reschedule as a Context Flag and Short-Ship as a Severity Aggravator
* **Pros:** Separates "where the delay occurred" (stage) from "what special events accompanied the trip" (context). Maintains the mathematical purity of the classifier and enriches aggregated analytics.
* **Cons:** Requires the creation and maintenance of additional columns in the data model that travel in parallel with the stage flags.

## Decision
The **Option 2** was chosen. After validation with the mentor on 2026-06-16, it was determined that these events do not constitute stages.

The data model was structured under the following rules:
1. The *reschedule* is extracted from the stage classifier and modeled strictly as an independent **context flag** called `is_rescheduled`.
2. The *short-ship* (inherited from the `_short_ship` field of Phase 1) is classified and processed exclusively as a **severity aggravator** of the delay, not as a root cause.

## Consequences
* **Positive:** The stage classifier remains clean and conceptually solid (focused on measurable physical segments). The pipeline inherits high-value context variables for Phase 3 to infer rich narratives toward the LLM without injecting inherent biases.
* **Negative:** Downstream consumption logic must perform matrix crossings between the assigned stage and these contextual flags to extract the full value of the data.