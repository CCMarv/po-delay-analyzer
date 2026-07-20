# Phase 1: Data Ingestion, Pipeline Quality & EDA

This module includes the ingestion, cleaning, temporal consistency validation, and exploratory data analysis (EDA) of the logistic purchase order dataset.

---

## 1. Context and Pipeline Architecture

The data pipeline processes the raw input file to ensure that subsequent classification phases have consistent and structured data.

The main logic resides in `pipeline_core.py` and is divided into five sequential stages:

| Stage | Pipeline Operation | Technical Description |
| :---: | :--- | :--- |
| **0** | **Raw Dataset** | Ingestion of the source file `po_root_cause_synthetic.csv`. |
| **1** | **Timestamp Parsing** | Strict conversion to date type and error handling with `NaT`. |
| **2** | **Quality Flags** | Classification of reliable records without row deletion. |
| **3** | **Deltas (Segments)** | Mathematical calculation of durations between milestones. |
| **4** | **Exploratory Flags** | Injection of alert flags based on preliminary thresholds. |
| **5** | **Cross-Validation** | Final cross-audit of consistency before output. |



### Core Functions Detail

#### `clean_po_data()`
Sequentially executes the following transformation steps:
1. **Timestamp Parsing:** Converts lifecycle columns to `datetime64[ns]` type using `errors='coerce'`. Any invalid or corrupted alphanumeric value is safely transformed into a no-data (`NaT`).
2. **Injection of Quality Flags:** Evaluates the status of the record without destroying rows, assigning binary operational reliability indicators.
3. **Calculation of Segments (Deltas):** Generates duration metrics between logistical lifecycle milestones to isolate supply chain responsibilities.
4. **Stage Flags Assignment:** Injects preliminary alerts based on exploratory business thresholds.

#### `cross_validate_deltas()`
Performs a cross-mathematical audit comparing the segments calculated in the pipeline against the precalculated columns of the source CSV. Generates automated reports of temporal discrepancies and validates logical consistency before exporting the clean dataframe.

---

## 2. Data Quality Decisions

Throughout the development cycle, five data engineering strategies were implemented to mitigate anomalies from the input dataset, linked to their respective technical design decisions:

*   **Timestamps as Source of Truth (#15):** The source columns `YARD_WAIT_HRS`, `DOCK_HRS`, `DELAY_DAYS`, and `IS_LATE` were discarded as hard logic. The pipeline recalculates each metric from the native date fields. *Evidence:* 11 records were detected where `DOCK_HRS` differed by up to 8.2 hours from the actual computation due to the source system recording time investments (`CHECKOUT` < `CHECKIN`) as negative values. The pipeline truncates these physically impossible segments to `0` hours. `HOT_PO_FLAG` remains intact as a pure business input.
*   **Handling Corrupted Data without Population Loss (#4, #16, #18):** To avoid altering the statistical volume or inducing biases, records with inconsistent dates are not deleted. Instead, they are isolated using three flags:
    *   `_ts_issue`: Records 12 orders with temporal investments in the dock.
    *   `_trailer_arrive_null`: Records 27 orders without arrival tracking.
    *   `_data_reliable`: Identifies 361 completely clean records (100% optimal Population).
*   **Handling Silent NaN in Carriers (#16):** With the `TRAILER_ARRIVE_DT` timestamp missing in 27 cases, the mathematical operation of the carrier segment yielded `NaN`. Evaluating this with traditional operators resulted in a false positive of statistical compliance. The explicit flag allows these 27 orders to be removed from the logistics compliance denominator, isolating the *service level* metric from the pure data *compliance*.
*   **Isolation of Post-Reception Events (#18):** The analysis of the `TRAILER_DEPART_DT` column revealed that the physical truck departure occurs on average ~27 hours **after** the operational closure in the system (`RECPT_DT`) in 99.8% of cases. This field was formally excluded from the useful delay segment logics as it is outside the reception lifecycle.
*   **Structuring Operational Deltas (#5):** The following time control segments were formally created in code:
    *   `lead_time_days`: Total duration from placement to promised date (`PO_DT` $\rightarrow$ `STA_DT`).
    *   `carrier_lag_hrs`: Transit time of the carrier (`APPROVED_DT` $\rightarrow$ `TRAILER_ARRIVE_DT`).
    *   `yard_wait_calc_hrs`: Stay in the maneuvering yard (`TRAILER_ARRIVE_DT` $\rightarrow$ `CHECKIN_DT`).
    *   `dock_calc_hrs`: Physical unloading time at dock (`CHECKIN_DT` $\rightarrow$ `CHECKOUT_DT`).
    *   `delay_days_calc`: Final delay of the delivery cycle (`RECPT_DT` $-$ `STA_DT`, capped at $\ge 0$).
    *   `appt_lead_days`: Supplier reservation window (`STA_DT` $-$ `APPROVED_DT`).

---

## 3. Phase 1 Thresholds vs. Classification Rules

> [!WARNING]
> **Threshold Status in Phase 1: Exploratory and Superseded**
> The operational flags injected in this module (`flag_carrier_miss`, `flag_yard_miss`, `flag_dock_miss`) respond to initial limits defined during the exploratory analysis:
> *   **Carrier:** 4 hours
> *   **Yard:** 4 hours
> *   **Dock:** 6 hours
> 
> The **4-hour Carrier threshold has been superseded** and does not govern the final business classification. The official production logic is consolidated in **Phase 2** (`02_clasif_reglas_negocio/`), applying a definitive parametric threshold of **8 hours** dictated by the project mentor in the 06-16 session (configurable parameter in `rules_config.json`).

---

## 4. Summary of EDA Findings (#19, #20)

*   **Mix of Real Scenarios:** The actual statistical behavior of the yard significantly diverges from the theoretical premises considered in the kickoff. Bottlenecks dynamically concentrate in specific segments of the internal operation of the DC rather than generalized exogenous events.
*   **Concentration of Delays:** Analytical segmentation of the main delay KPI:
    *   *By Distribution Center (DC):* Certain geographic locations exhibit structural delays associated with dock saturation.
    *   *By Vendor/Carrier:* Unusual groupings of low logistical efficiency were identified associated with specific carriers during nighttime hours.
*   **Inconsistency of Human Annotation:** The first cross of quantitative variables against the free text column `REASON_DSC`. Systemic contradictions were found in the manual coding of yard operators, empirically confirming the project's hypothesis: human annotation presents an error margin of ~20%, justifying the algorithmic automation of Phase 2 (which reaches an 88.8% business concordance).

---

## 5. Glossary and Column Structure

To avoid redundancy of information and ensure a single point of technical truth, the detailed description of the data type, known nulls, and business roles of the 39 input columns is documented in the central resource of the repository:

📘 [See Data Dictionary and Technical Sheet (Data Card)](../documentation/data_dictionary.en.md)

---

## 6. How to Run

### Prerequisites
Ensure that the virtual environment is active and the dependencies are installed, along with the raw dataset located in the corresponding local path.

```bash
# 1. Ensure the presence of the data file (gitignored)
ls data/raw/po_root_cause_synthetic.csv

# 2. Run the Ingestion, Quality and EDA pipeline
python 01_data_pipeline_and_eda/pipeline_core.py
```

### Expected Outputs
Execution will generate in the console the statistical report of the cross-validation (`cross_validate_deltas()`) and print the consistency metrics of valid records for consumption by the Phase 2 classifier.