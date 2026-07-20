# Data Dictionary

This document combines the data dictionary column by column with the business context of the dataset, following a hybrid standard inspired by *Hugging Face Dataset Cards* and *Datasheets for Datasets*.

## 1. Dataset Context (Data Card)

*   **Data Origin:** Synthetic dataset simulating logistics operations. Contains **400 Purchase Orders (POs)** and **39 columns** (verified and validated against the real CSV header).
*   **Physical Location:** Located in `data/raw/` (excluded from version control via `.gitignore`).
*   **Technical Source of Truth:** The **timestamps** of the lifecycle are the only source of truth for segment and delay calculations.
*   **Quality of Human Annotation:** The fields `REASON_CD` and `REASON_DSC` are manual annotations and contain approximately **20% incorrect** or inconsistent classifications. They should be used only as contrast, never as a hard rule.
*   **Known Limitations:** 
    *   There are 12 POs with temporal inversion (`CHECKOUT_DT` < `CHECKIN_DT`). They are flagged in the pipeline with the quality flag `_ts_issue`.
    *   The field `TRAILER_DEPART_DT` occurs on average ~27 hours after receipt (`RECPT_DT`) in 99.8% of cases, thus falling outside the useful operational cycle for measuring delays.

---

## 2. Field Dictionary (39 Columns)

### Group A: Lifecycle Timestamps (Core Rules)
*All fields in this group are parsed to datetime in the pipeline (`errors='coerce'`). If the data is invalid, it is transformed into `NaT`.*

| Column | Type | % Known Nulls | Role in Project / Rules | Description |
| :--- | :--- | :--- | :--- | :--- |
| `PO_DT` | Datetime | 0% | Core Rules | Date of PO placement. Start of the lifecycle. |
| `STA_DT` | Datetime | 0% | Core Rules | Promised arrival date (Scheduled Time of Arrival). Day grain (always midnight). Basis of the tardiness KPI. |
| `APPROVED_DT` | Datetime | 0% | Core Rules | Date and time of the current appointment approval. Alias or equivalent to `DT_APPT_CURRENT_APPROVED`. |
| `DT_APPT_FIRST_APPROVED` | Datetime | 0% | Core Rules | First appointment approval. Its difference with the current one defines if there was a reschedule. |
| `DT_APPT_CURRENT_APPROVED` | Datetime | 0% | Core Rules | Current appointment approval in the system. |
| `TRAILER_ARRIVE_DT` | Datetime | **6.8% (27 POs)** | Core Rules | Arrival of the trailer at the DC. If null, the PO falls into the classification `Indeterminate/sin_datos` (impossible to judge carrier/DC). |
| `CHECKIN_DT` | Datetime | 0% | Core Rules | Start of physical unloading (truck entry to dock). |
| `CHECKOUT_DT` | Datetime | 0% | Core Rules | End of physical unloading. Presents temporal anomalies in 12 records (`CHECKOUT` < `CHECKIN`). |
| `RECPT_DT` | Datetime | 0% | Core Rules | Posted receipt in the system. Closes the operational lifecycle. If `RECPT_DT > STA_DT` $\Rightarrow$ Delayed PO (main KPI). |
| `REQUESTED_DT` | Datetime | 0% | Core Rules | Date of appointment request by the vendor (vendor flow, pre-arrival). |
| `FIRST_SUBMITTED_DT` | Datetime | 0% | Core Rules | First submission of appointment request in the vendor portal. |
| `PREVIOUS_REQUEST_DT` | Datetime | **84.2%** | Avoid in Rules | History of previous requests. Column mostly empty; not suitable for hard logic. |
| `TRAILER_DEPART_DT` | Datetime | 0% | Excluded from Segments | Physical departure of the trailer from the yard. Occurs post-operational receipt; does not map delay windows. |

### Group B: Volume Quantities and Indicators (Short Ship)

| Column | Type | % Nulls | Role in Project / Rules | Description |
| :--- | :--- | :--- | :--- | :--- |
| `NUM_CASES_ORDERED` | int64 | 0% | Rules (Fill Rate) | Quantity of boxes originally requested in the purchase order. |
| `NUM_CASES_SHIPPED` | int64 | 0% | Rules (Fill Rate) | Quantity of boxes shipped by the vendor. If the reason Shipped/Ordered < 0.9 $\Rightarrow$ *Short Ship*. |
| `TOT_ORG_QTY` | int64 | 0% | Context / Control | Total original quantity recorded in the transaction. |
| `TOT_RCVD_QTY` | int64 | 0% | Context / Control | Total physical quantity received at the distribution center. |
| `TOT_ON_ORD_QTY` | int64 | 0% | Context / Control | Total quantity that remains active in active order status. |
| `TOT_ADJ_QTY` | int64 | 0% | Context / Control | Total quantity of adjustments or corrections applied at receipt. |

### Group C: Business Flags (Exogenous Inputs)
*Native fields from the CSV. They remain fixed and are not recalculated by the pipeline.*

| Column | Type | % Nulls | Role in Project / Rules | Description |
| :--- | :--- | :--- | :--- | :--- |
| `HOT_PO_FLAG` | int64 (0/1) | 0% | Prioritization / Context | Exogenous flag indicating whether the Purchase Order is of high priority for the business. |
| `HOT_APPT_FL` | int64 (0/1) | 0% | Prioritization / Context | Exogenous flag identifying whether the logistics appointment was categorized as critical or priority. |

### Group D: Pre-calculated Fields (For Cross-Check Only)
*⚠️ Attention! Do not use as source of truth. All metrics are recalculated in the pipeline from native timestamps. They only serve to audit discrepancies.*

| Column | Type | Discrepancies / Notes | Role in Project / Rules | Description |
| :--- | :--- | :--- | :--- | :--- |
| `DELAY_DAYS` | Numeric | Audited vs Timestamps | Cross-Check | Pre-calculated days of delay in the source. |
| `YARD_WAIT_HRS` | Numeric | Audited vs Timestamps | Cross-Check | Estimated hours of waiting in the distribution center yard. |
| `DOCK_HRS` | Numeric | Discrepancy in 11 POs (max 8.2h) | Cross-Check | Hours in dock. Discrepancies exactly match with the flag `_ts_issue`. |
| `IS_LATE` | object (Y/N) | Audited vs Timestamps | Cross-Check | Binary textual indicator signaling whether the order arrived late in the source system. |

### Group E: Human Annotation (Reference for Contrast)

| Column | Type | % Known Nulls | Role in Project / Rules | Description |
| :--- | :--- | :--- | :--- | :--- |
| `REASON_CD` | object | **32.8%** | Classification Contrast | Code for the reason of delay manually assigned by operators. |
| `REASON_DSC` | object | **2.2%** | Classification Contrast | Textual description of the cause of delay. (~20% error regarding the reality of the cycle). |

### Group F: Business Entities

| Column | Type | % Nulls | Role in Project / Rules | Description |
| :--- | :--- | :--- | :--- | :--- |
| `PO_NBR` | int64 / object| 0% | Unique Identifier | Unique identification number of the Purchase Order (Logical Primary Key). |
| `VENDOR_NBR` | int64 | 0% | Entity Attribute | Numerical identifier of the vendor that issues and dispatches the order; paired with `VENDOR_NAME`. |
| `VENDOR_NAME` | object | 0% | Entity Attribute | Trade name of the vendor that issues and dispatches the order. |
| `CARRIER_PARTY_NAME`| object | 0% | Entity Attribute | Name of the carrier company responsible for the transport. |
| `TRAILER_NBR` | object | 0% | Entity Attribute | Plate number or physical identification of the logistics box/trailer. |

### Group G: Administrative Columns

| Column | Type | % Nulls | Role in Project / Rules | Description |
| :--- | :--- | :--- | :--- | :--- |
| `PAY_VENDOR_NBR` | int64 | 0% | Administrative | Identification number of the vendor for financial purposes. |
| `PAY_VENDOR_NAME` | object | 0% | Administrative | Legally registered name of the vendor for tax and payment purposes. |
| `DC_ID` | int64 | 0% | Administrative / Entity | Unique identifier of the destination Distribution Center. |
| `DC_LOC_NAME` | object | 0% | Administrative / Entity | Geographic or locality name of the Distribution Center. |
| `DC_FACILITY_CD_ABBREV`| object | 0% | Administrative | Internal abbreviation of the code for the facility or building within the DC. |
| `PO_STATUS_CD` | object | 0% | Administrative | Administrative status of the PO in the source ERP system. |
| `YARD_DROP_FL` | int64 | 0% | Administrative | Indicator of whether the container was left in the yard (*drop* = 1) or not. |