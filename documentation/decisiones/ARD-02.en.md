# Hierarchy with Multiple Active Flags

* **Status:** 🟢 Current
* **Technical Context:** Phase 2 / Dominant Attribution Modeling
* **References:** Issue #39, Discussion #52

## Context and Problem
In the operational reality of the supply chain, a single Purchase Order (PO) can experience simultaneous delays across multiple segments (Vendor, Carrier, and DC). Forcing a single artificial cause through static rules conceals the real friction of the business. The challenge lies in structuring the assignment of the primary stage without losing visibility of the ecosystem of accessory causes that impacted the order.

## Considered Options

### Option 1: Static Fixed Priority Model
*   **Pros:** Simple to implement through straightforward conditional structures (e.g., *if Carrier fails, ignore the rest*).
*   **Cons:** Creates a massive artificial bias in the data, obscuring critical inefficiencies of other actors.

### Option 2: Mathematical Criterion of Maximum Excess over the Threshold (`argmax`) with Complementary Vector
*   **Pros:** It is a transparent and fair mathematical approach. It determines the primary stage based on who exceeded their agreed time window most severely, resolving the main root cause without fixed biases.
*   **Cons:** Requires a data architecture capable of supporting structured or matrix storage for the complementary layer.

## Decision
The **Option 2** has been chosen. The primary attribution stage of the delay will be dynamically assigned using the **`argmax`** function, selecting the segment of the chain that shows the **greatest numerical excess in hours over its own parameterized threshold**.

To complement this approach and avoid enforcing a single exclusive cause, a **multi-cause vector as a complementary layer** will be attached to the PO record, preserving the complete history of all activated flags throughout the journey.

## Consequences
*   **Positive:** The model accurately reflects, with scientific precision, the severity of the operational impact of each actor, enabling efficient action plans.
*   **Negative:** The aggregation logic in final reports must consider the multi-cause vector for advanced analyses, which increases the complexity of initial analytical queries.