# Phase 2 — Stage Classification (Business Rules)

> Methodology document (#50). For now **only in Spanish**; the English version will
> be added at the end of the development. The figures are based on the real dataset (400 POs, 247 late POs).

This phase assigns each late PO the **responsible stage** for the delay (Vendor / Carrier /
DC / Indeterminate), a **subclass of DC** (Yard / Dock), and a **deterministic severity**,
and validates those assignments against two independent references. All logic resides in
reusable functions from `classifier_core.py` and `metrics_core.py`; the notebook only presents it.

## 1. Flow

```
Raw CSV
  └─ clean_po_data()          [pipeline_core.py, Phase 1]  → deltas *_calc + quality flags
       └─ classify_po_stages() [classifier_core.py]        → stage_primary, severity, dc_substage, …
            ├─ save_classified_output()                    → data/processed/df_classified.csv (#49)
            └─ metrics_core.py                              → validation (#46, #47)
```

`classify_po_stages` orchestrates four steps: `_flags_por_umbral` (#44) → `_etapa_primaria`
(#45) → `_capa_complementaria` (context flags) → `_severidad` (#48).

## 2. Mentor Taxonomy and Decisions

The taxonomy and thresholds were finalized with the mentor (2026-06-16) and refined after an
attribution consultation (2026-06-17). Each decision with its reasoning:

| # | Decision | Reason |
|---|----------|---------|
| #39 | **Four stages**: Vendor / Carrier / DC / Indeterminate. | "Indeterminate" is a valid and auditable category: forcing an attribution without evidence would be inventing causality. |
| #40 | **Vendor by STA push** (`APPROVED_DT > STA_DT`), NOT by residual. | The residual (delay − carrier − DC) assumes that the segments are additive and mutually exclusive; in practice, there are overlaps. The direct signal is more robust and **works for the 27 POs without trailer time** (does not need carrier/DC to be measured). |
| #41 | **Carrier threshold = 8h** (not 4h), with sensitivity table. | The median of `gap_carrier` is approximately 3h and the p75 approximately 4.4h; 8h produces a carrier proportion consistent with a dataset of short journeys. What matters is **traceability** (section 5). |
| #42 | **Rescheduled and short-ship = context / aggravating factor**, not stage. | A reschedule describes an *event*, not a root cause; the classifier responds *who* caused the delay, not *what* occurred. As a context flag, it adds more to the LLM (Phase 3). |
| #40b | **DC = consolidated Yard + Dock**, with subclass `dc_substage`. | The final responsible party is the same (CD operations); the detail Yard/Dock is preserved as informative subclassification. |
| 06-17 (b) | The **14 late POs without any signal** → Indeterminate. | Complete data but no thresholds exceeded (small delays, median 3.2h): there is no one to attribute with evidence. It honors "not inventing causality" even though it expands the definition of Indeterminate. |

### How `stage_primary` is Decided (`_etapa_primaria`, #45)

1. **Excess per measurable segment** = `max(0, observed − mentor threshold)`, in hours
   (carrier 8h, yard 4h, dock 6h). A non-measurable segment (field-level mask set to False) contributes
   0 to the argmax, but the mask records that "measurement could not be made".
2. **Vendor by STA push over threshold** = `max(0, −appt_lead_days × 24 − 24h)`, where
   `appt_lead_days = STA − APPROVED` (days); it is negative when `APPROVED > STA`, so the
   push in hours is positive. The push only counts as excess **above `vendor_gap_hrs`
   = 24h**, just as carrier/DC have their threshold (mentor consultation 06-17; see §3 and §5.3).
3. **Primary stage** = argmax of `{Vendor, Carrier, DC}`.
4. **Indeterminate** (with subclass `indeterminado_substage`, mirror of `dc_substage`): (a)
   **`sin_datos`** = the PO is late but not measurable (missing `TRAILER_ARRIVE_DT`); (b)
   **`sin_causa_dominante`** = it is measurable, but no segment exceeds its threshold (including that of
   vendor). The top label is `Indeterminate`; the specific reason resides in the subclass.

### Resulting Distribution (247 late POs)

| Stage | % | n |
|-------|---|---|
| Vendor | 56.3% | 139 |
| Carrier | 16.2% | 40 |
| DC | 15.0% | 37 |
| Indeterminate | 12.6% | 31 |

The 31 Indeterminates break down into **7 `sin_datos`** (without trailer time) + **24
`sin_causa_dominante`** (measurable but with no excess over threshold). *(ADR-03b closing
note, 2026-07-22: the `decidible` gate excluded vendor without its own condition — 8 POs
without trailer time but with measurable vendor excess (22.6-92.5h) fell into `sin_datos` by
default; see [ADR-03b](../documentation/decisiones/ARD-03b.en.md).)*

Vendor dominates (56%) above the ~20% from the kickoff. After the mentor consultation (06-17),
vendor has its **own threshold (24h)** to correct the *construction asymmetry*: previously,
it triggered with any positive push while carrier/DC required 8/4/6h, thus absorbing by
default. The 56% **is supported by the data, not the trigger rule**: the distribution of push is
**bimodal** — 12 POs with nearly zero push (≤6h) and 141 with push in days (median 3.1 days), with a
**void gap between 6h and 18h** (no POs). Late orders are almost always late because the
appointment was approved late. *(The push↔total delay correlation is high by construction —an early delay
propagates— and is NOT evidence of causality; what matters is the excess per segment.)*

## 3. Thresholds (`rules_config.json`)

The thresholds are read by name from the JSON (never hardcoded); recalibrating involves editing the
JSON, not the code.

| Key | Value | Use |
|-----|-------|-----|
| `vendor_gap_hrs` | 24.0 h | Vendor excess (STA push) over this threshold. 24h = natural granularity of the data (STA at day level). |
| `carrier_lag_hrs` | 8.0 h | Carrier excess over this threshold (confirmed by the mentor). |
| `yard_wait_hrs` | 4.0 h | Yard excess. |
| `dock_hrs` | 6.0 h | Dock excess. |
| `short_ship_fill_rate` | 0.9 | Below → short-ship (context flag). |
| `severity_delay_days` | 3.0 d | HIGH gate of severity. |
| `severity_low_days` | 1.0 d | LOW (borderline) cutoff of severity. |

> The `expected_leg_times` block was removed (seed budgets of 3/1.5/2.5 h): they were never
> validated, and the method now measures excess over the mentor's thresholds, not over budgets.

## 4. Severity (`_severidad`, #48)

Severity is **deterministic** (not decided by the LLM; that is a separate narrative layer in Phase 3).
The rubric requires an auditable ranking, and the computation from reliable columns is defensible.

- **HIGH** = `flag_hot_late` (HOT_PO_FLAG=1 and IS_LATE) **and** `delay_days_calc > 3.0`.
- **LOW** = `delay_days_calc < 1.0` (borderline, almost on time, <~24 h).
- **MEDIUM** = the rest of the late POs.
- **(empty)** = not late (not included in the ranking).

**Aggravating factors** (decisions #40/#42): `is_short_lead` or `is_short_ship` raise **one level**
(LOW→MEDIUM, MEDIUM→HIGH); HIGH remains unchanged (ceiling). A borderline order with short lead
is no longer borderline. They do not accumulate beyond HIGH: the real HIGH gate remains HOT + strong delay.

Distribution (247 late POs): MEDIUM 131 · LOW 82 · HIGH 34.

## 5. Validation (`metrics_core.py`)

| Metric | Result | Threshold | Status |
|--------|--------|-----------|--------|
| **Stage accuracy** (#46) | 100% (216/216 evaluable) | > 80% | ✅ |
| **Reason agreement** (#47) | 88.7% (180/203 classifiable) | — (reference) | finding |
| **Severity ranking** (#48) | deterministic, auditable | > 95% | ✅ |

### 5.1 Stage accuracy (#46): dominant gap vs `stage_primary`

`stage_primary` measures **excess over threshold**; the **dominant gap** measures **gross duration** of
the longest segment. They are **intentionally distinct metrics** — comparing them validates that the excess
attribution does not diverge from where the time was physically spent, without forcing them to match.

The dominant gap is measured over the **attributable sequence**, segmented so that downtime does not enter into the calculation (mentor instruction):

```
STA → APPROVED → TRAILER_ARRIVE → CHECKIN → CHECKOUT
```

The lead time `PO→STA` (median 192 h: standard purchase time, not delay) and everything after CHECKOUT are **excluded**: `TRAILER_DEPART` occurs **after** `RECPT` in **99.8%**
of POs (verified), meaning outside the reception cycle.

Denominator = **evaluable** (216): late POs with decidable stage and measurable gap. The
Indeterminates are excluded (the dominant gap cannot judge a PO without trailer). With the vendor
threshold (24h), the agreement is **total (216/216)**: by requiring a push of at least one day, cases previously multi-causal (small push + internal segment) are no longer classified as Vendor, thus the attribution by excess coincides with the longest gross duration segment in all evaluable cases.

### 5.2 Sensitivity of the Carrier Threshold (4 / 6 / 8 / 12 h)

Distribution = Vendor / Carrier / DC / Indeterminate (% of late POs, with `vendor_gap_hrs`=24 active).

| Threshold | `flag_carrier_calc` | `stage_primary` Distribution |
|-----------|---------------------|------------------------------|
| 4 h | 25.8% (103) | 56.3 / 17.4 / 15.0 / 11.3 |
| 6 h | 12.8% (51) | 56.3 / 16.2 / 15.0 / 12.6 |
| **8 h** | **12.8% (51)** | **56.3 / 16.2 / 15.0 / 12.6** |
| 12 h | 11.2% (45) | 56.3 / 14.6 / 15.0 / 14.2 |

**Reading:** the carrier threshold moves the *raw flag* `flag_carrier_calc` significantly (from 25.8% to
~12% when increasing from 4h to 8h, just as the mentor predicted), but barely affects `stage_primary`,
because the vendor signal dominates the argmax, and the carrier threshold only reorders the few cases
where carrier competes closely. 8h is the confirmed value.

### 5.3 Sensitivity of the Vendor Threshold (6 / 12 / 18 / 24 / 48 / 72 h)

Decide `vendor_gap_hrs` with the same analysis as the carrier (mentor instruction 06-17).
Distribution = Vendor / Carrier / DC / sin_datos / sin_causa_dominante (counts on 247 late POs).

| Threshold | Vendor | %Vendor | Distribution |
|-----------|--------|---------|--------------|
| 0 (no threshold) | 151 | 61.1 | 151 / 40 / 37 / 5 / 14 |
| 6 h | 141 | 57.1 | 141 / 40 / 37 / 7 / 22 |
| 12 h | 141 | 57.1 | 141 / 40 / 37 / 7 / 22 |
| 18 h | 141 | 57.1 | 141 / 40 / 37 / 7 / 22 |
| **24 h** | **139** | **56.3** | **139 / 40 / 37 / 7 / 24** |
| 48 h | 121 | 49.0 | 121 / 40 / 37 / 8 / 41 |
| 72 h | 81 | 32.8 | 81 / 40 / 37 / 10 / 79 |

**Reading:** 6/12/18h are equivalent (the push distribution has a void gap between 6h
and 18h). **24h** is the chosen value for three reasons: (1) it is the **natural granularity of the data** —
`STA_DT` is at day level (without sub-day resolution), so measuring the push against a full day is the unit in which the problem is expressed; (2) it falls in the **empty zone** of the distribution → robust to perturbations; (3) it does not force the distribution toward the ~20% from the kickoff (which the mentor advised against). POs that stop being Vendor when the threshold rises migrate to `sin_causa_dominante` (most of them) or to `sin_datos` (those without trailer whose push falls below the new threshold) — **none to Carrier/DC** → the threshold does not reattribute, it only separates the diffuse pushes. Detail of the analysis: [`documentation/decisiones/ARD-06b.md`](../documentation/decisiones/ARD-06b.en.md).

*(ADR-03b closing note, 2026-07-22: before this fix, `sin_datos` was constant at 15 across the
7 scenarios in this table — a signal, in hindsight, that the vendor threshold never reached
those POs due to the broken `decidible` gate. It now varies correctly with the threshold:
5/7/7/7/7/8/10.)*

### 5.4 Reason Agreement (#47): the Project Thesis

Agreement = 88.7% on 203 classifiable (`stage_primary` vs `reason_group_manual`, the mapping
from human annotation `REASON_DSC`; the nulls among late POs → "Unknown", outside the denominator).

The agreement < 100% is **expected and desired**: human annotation is ~20% incorrect (data from
the kickoff). The **23 mismatches** are evidence that the temporal computation surpasses the
human annotation — available as possible few-shot input for Phase 3 (see status in §6).

## 6. Selected Mismatches (#47) — Temporal Evidence

Eight cases where the timestamps contradict the human reason code and the computation is defensible.
They cover the three types of discrepancy. ("STA push" = raw push `APPROVED − STA` in hours, evidence of the phenomenon; the argmax uses excess over the 24h threshold, which is 24h lower but does not alter the attribution: all exceed the day comfortably.)

| PO | Computation | Human (REASON_DSC) | Temporal Evidence |
|----|-------------|---------------------|--------------------|
| 100280 | Vendor | Carrier ("Missed appointment window") | STA push 124.6 h; carrier/DC excess = 0 |
| 100382 | Vendor | DC ("Yard congestion") | STA push 111.0 h; yard/dock excess = 0 |
| 100236 | Vendor | Carrier ("Equipment/trailer issue") | STA push 118.5 h; carrier excess = 0 |
| 100262 | Vendor | DC ("Dock processing backlog") | STA push 81.0 h; dock excess = 0 |
| 100073 | Vendor | Carrier ("Weather/road conditions") | STA push 93.5 h; carrier excess = 0 |
| 100024 | Carrier | DC ("Dock processing backlog") | carrier excess 25.7 h; dock excess = 0 |
| 100058 | DC (Yard) | Carrier ("Equipment/trailer issue") | yard excess 19.3 h; carrier excess = 0 |
| 100204 | DC (Dock) | Vendor ("Vendor delayed shipment") | dock excess 9.0 h; STA push = 0 |

Star pattern (the first five): the human blamed the visible link (carrier/yard) while the
appointment had been approved days late, and that segment had no excess at all. Internal pattern (last three): the computation detects an excess segment that human annotation confused.

`metrics_core.select_mismatches(df, n)` returns this ranking by signal strength. With
`stratify=True`, it distributes `n` among the present stages (Vendor/Carrier/DC) and takes the strongest from each, instead of the `n` strongest in raw form: since the universe of mismatches is dominated by Vendor, the flat ranking tends to be almost all Vendor, and stratified selection ensures that the few-shot (#99) and mismatch narrative (#95) cover all three stages. The default (`stratify=False`) preserves the historical flat ranking.

> **Status of the few-shot (at the end of Phase 2).** These mismatches are **available** as
> possible few-shot, but **the Phase 3 prompt is currently zero-shot**: it still does NOT consume them. The
> wiring (injecting these examples into the prompt) is a design decision for the prompt, pending
> in Phase 3. Here, only the input is produced and justified; using it or not is decided by F3.

## 7. How to Run

```bash
# From the root of the repo, with the CSV in data/raw/ (or PO_CSV_PATH pointing to it):
PYTHONPATH=01_data_pipeline_and_eda PO_CSV_PATH=data/raw/po_root_cause_synthetic.csv \
  python 02_clasif_reglas_negocio/classifier_core.py
# → prints the distribution and writes data/processed/df_classified.csv (gitignored).

# Tests:
python -m pytest -q
```

The output (`data/processed/df_classified.csv`) **is not versioned**; it is regenerated by running the module.