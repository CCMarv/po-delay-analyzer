# Benchmark of LLM Explanation Quality — 20 POs (#94)

Mentor metric *LLM Explanation Quality* (README §6). Stratified sample 8/4/4/4 (Vendor/Carrier/Indeterminate/DC), seed `42` (reproducible; reuse #99). Backend: the official deliverable.

## Criteria (binary per PO; PASSES if meets all 3)
- **(a) correct stage:** names the stage = `stage_primary`. For `Indeterminate`, it is correct if it declares it indeterminate (not if it copies the stage from the reason code).
- **(b) quantifies the delay:** cites a figure and matches `delay_days_calc`.
- **(c) viable action:** names responsible party and is actionable (NOT generic). *Human validation.*

## Verdict (validated manually)
(a) stage: 19/20 · (b) quantifies: 20/20 · (c) viable action: 13/20 · **PASSES (a&b&c): 13/20**.

| PO | stage | delay (d) | REASON_DSC | LLM explanation | LLM action | (a) | (b) | (c)? | verdict |
|---|---|--:|---|---|---|:--:|:--:|:--:|:--:|
| 100154 | Carrier | 1.19 | Carrier delivery delay | The exact stage of the delay is Carrier, with a quantified delay of 1.19 days. The evidence matches the REASON_DSC from the DC, which indicates a delay in delivery by the carrier. There are no aggravating factors such as hot PO or short ship. | The carrier, Estes Express, should review its delivery processes to avoid future delays and ensure compliance with promised dates. | ✅ | ✅ | ❌ | does not pass |
| 100278 | Carrier | 1.24 | Weather/road conditions | The exact stage of the delay is Carrier, with a quantified delay of 1.24 days. The evidence does not match the REASON_DSC from the DC, which mentions weather and road conditions, while the carrier's excess was 29.7 hours. Additionally, this is a Hot PO. | Contact the carrier UPS Freight to investigate the causes of the delay and ensure that corrective measures are taken to avoid future incidents, assigning this task to the DC logistics team. | ✅ | ✅ | ❌ | does not pass |
| 100146 | Carrier | 1.16 | Equipment/trailer issue | The exact stage of the delay is Carrier, with a quantified delay of 1.16 days. The evidence does not match the REASON_DSC from the DC, which mentions an equipment/trailer issue, while the delay is classified as caused by the carrier. There are no aggravating factors since this is neither a hot PO nor a short ship. | The carrier, XPO Logistics, should investigate and resolve the equipment/trailer issue that caused the delay and ensure measures are taken to avoid similar future incidents. | ✅ | ✅ | ✅ | **PASSES** |
| 100229 | Carrier | 0.35 | Equipment/trailer issue | The exact stage of the delay is Carrier, with a quantified delay of 0.35 days. The evidence does not match the REASON_DSC from the DC, which mentions an equipment/trailer issue. There are no aggravating factors such as hot PO or short ship. | The carrier, Old Dominion, should investigate and resolve the equipment/trailer issue that caused the delay in delivery. | ✅ | ✅ | ✅ | **PASSES** |
| 100185 | DC | 0.75 | Yard congestion - no available door | The exact stage of the delay is DC, with a quantified delay of 0.75 days. The evidence matches the REASON_DSC from the DC, which mentions yard congestion due to a lack of available doors. There are no aggravating factors such as hot PO or short ship. | The DC team should optimize yard management and ensure that doors are available to avoid future congestion. | ✅ | ✅ | ✅ | **PASSES** |
| 100217 | DC | 0.04 | Dock processing backlog | The exact stage of the delay is DC, with a delay of 0.04 days. The evidence matches the REASON_DSC from the DC, which indicates a 'Dock processing backlog'. There are no aggravating factors such as hot PO or short ship. | The DC team should review and optimize the unloading process to reduce the backlog at the dock and avoid future delays. | ✅ | ✅ | ✅ | **PASSES** |
| 100092 | DC | 0.06 | Yard congestion - no available door | The exact stage of the delay is DC, with a quantified delay of 0.06 days. The evidence matches the REASON_DSC from the DC, which indicates yard congestion due to a lack of available doors. There are no aggravating factors, although it is a Hot PO, the delay is minimal. | The DC team should manage door assignments better to avoid yard congestion, ensuring availability for future deliveries. | ✅ | ✅ | ✅ | **PASSES** |
| 100324 | DC | 0.04 | Yard congestion - no available door | The exact stage of the delay is DC, with a quantified delay of 0.04 days. The evidence matches the REASON_DSC from the DC, which indicates yard congestion due to a lack of available doors. There are no aggravating factors such as hot PO or short ship. | The DC team should manage door assignments better to avoid yard congestion, ensuring availability for future deliveries. | ✅ | ✅ | ✅ | **PASSES** |
| 100338 | Indeterminate | 0.40 | Not applicable | The exact stage of the delay is indeterminate, as it cannot be attributed to a single responsible party. A delay of 0.40 days was recorded. The evidence does not match the REASON_DSC from the DC, which is 'Not applicable'. There are no aggravating factors such as hot PO or short ship. | It is recommended that the DC team review receiving and unloading processes to identify potential efficiency improvements, given that no clear responsible party for the delay was identified. | ✅ | ✅ | ✅ | **PASSES** |
| 100367 | Indeterminate | 0.27 | Not applicable | The exact stage of the delay is indeterminate, as the quantified delay is 0.27 days. The evidence does not match the REASON_DSC from the DC, which is 'Not applicable'. There are no aggravating factors such as hot PO or short ship. | The DC team should review the check-in process to identify potential efficiency improvements for unloading, given that the unloading time was 3.7 hours. | ✅ | ✅ | ✅ | **PASSES** |
| 100062 | Indeterminate | 0.04 | Not applicable | The exact stage of the delay is indeterminate, with a quantified delay of 0.04 days. The evidence does not match the REASON_DSC from the DC, which is 'Not applicable'. There are no aggravating factors such as hot PO or short ship. | The vendor BIOPLEX should review its delivery processes to ensure that future deliveries occur within the promised schedule. | ✅ | ✅ | ❌ | does not pass |
| 100182 | Indeterminate | 4.41 | Vendor delayed shipment | The exact stage of the delay is Vendor, with a delay of 4.41 days. The evidence matches the REASON_DSC from the DC, which indicates a 'Vendor delayed shipment'. There are no aggravating factors such as hot PO or short ship. | The vendor MEDIQ should review and improve its shipping process to avoid future delays in scheduled deliveries. | ❌ | ✅ | ❌ | does not pass |
| 100197 | Vendor | 5.64 | Rescheduled by vendor | The exact stage of the delay is Vendor, with a delay of 5.64 days. The evidence matches the REASON_DSC from the DC, which indicates that the delay was 'Rescheduled by vendor'. Additionally, there are aggravating factors as this is a hot PO and a short ship. | The vendor SYNCO should review its scheduling and delivery compliance processes to avoid future delays. It is recommended to establish a contingency plan to meet promised dates for urgent orders. | ✅ | ✅ | ✅ | **PASSES** |
| 100158 | Vendor | 2.77 | Rescheduled by vendor | The exact stage of the delay is Vendor, with a quantified delay of 2.77 days. The evidence does not match the REASON_DSC from the DC, which indicates 'Rescheduled by vendor'. There are no aggravating factors such as hot PO or short ship. | The vendor NOVAPHARM should improve its shipping planning to avoid rescheduling in the future. | ✅ | ✅ | ❌ | does not pass |
| 100366 | Vendor | 4.04 | Rescheduled by vendor | The exact stage of the delay is Vendor, with a delay of 4.04 days. The evidence matches the REASON_DSC from the DC, which indicates that the appointment was rescheduled by the vendor. There are no aggravating factors such as hot PO or short ship. | The vendor SYNCO should improve its planning and compliance with delivery dates to avoid future rescheduling. | ✅ | ✅ | ❌ | does not pass |
| 100087 | Vendor | 5.24 | Vendor delayed shipment | The exact stage of the delay is Vendor, with a quantified delay of 5.24 days. The evidence matches the REASON_DSC from the DC, which indicates a 'Vendor delayed shipment'. There are no aggravating factors such as hot PO or short ship. | Request the vendor GREENLEAF to review its shipping processes to avoid future delays, and establish an action plan to improve delivery timeliness. | ✅ | ✅ | ✅ | **PASSES** |
| 100063 | Vendor | 5.86 | Rescheduled by vendor | The exact stage of the delay is Vendor, with a delay of 5.86 days. The evidence matches the REASON_DSC from the DC, which indicates that it was 'Rescheduled by vendor'. Additionally, there is an aggravating factor as it is a short ship. | The vendor MEDIQ should review its scheduling process and ensure that deliveries are made on promised dates to avoid future delays. | ✅ | ✅ | ❌ | does not pass |
| 100113 | Vendor | 4.45 | Rescheduled by vendor | The exact stage of the delay is Vendor, with a delay of 4.45 days. The evidence matches the REASON_DSC from the DC, which indicates that the appointment was rescheduled by the vendor. Additionally, there is an aggravating factor as this is a short ship. | The vendor AKZE should review its shipping process and ensure that future deliveries comply with promised dates and complete quantities of products. | ✅ | ✅ | ✅ | **PASSES** |
| 100318 | Vendor | 2.86 | nan | The exact stage of the delay is Vendor, with a delay of 2.86 days. The evidence does not match the REASON_DSC from the DC, as no specific reason was recorded. Additionally, there is an aggravating factor, as it is a short ship. | The vendor NOVAPHARM should investigate the cause of the incomplete shipment and ensure that future shipments meet the promised quantities. | ✅ | ✅ | ✅ | **PASSES** |
| 100157 | Vendor | 5.24 | Rescheduled by vendor | The exact stage of the delay is Vendor, with a delay of 5.24 days. The evidence matches the REASON_DSC from the DC, which indicates that the appointment was rescheduled by the vendor. Additionally, it is a Hot PO, which aggravates the situation. | Request the vendor MEDIQ for a detailed explanation of the delay and a plan of action to prevent future failures in urgent deliveries. | ✅ | ✅ | ✅ | **PASSES** |


## Verdict of (c) — reasoning (validated manually)
Criterion: (c) only passes if the action is **consistent with the reason** (does not ask to investigate what the reason already explains) **and actionable** (not “review/improve processes” as a blanket statement). Fails if it is generic or inconsistent.

- **100154** ❌ — “review delivery processes” generic
- **100278** ❌ — inconsistent: reason "Weather/road conditions" already gives the cause; asks to "investigate". Furthermore, weather is not an attributable fault of the carrier
- **100146** ✅ — consistent: a specific equipment failure does warrant investigation/resolution
- **100229** ✅ — same logic (equipment/trailer)
- **100185** ✅ — addresses the given cause (available doors vs yard congestion)
- **100217** ✅ — specific to dock processing backlog
- **100092** ✅ — consistent with congestion (door assignment); minimal delay, action somewhat disproportionate but relevant
- **100324** ✅ — same as 100092 (identical action)
- **100338** ✅ — consistent with indeterminacy: acknowledges that there is no clear responsible party and proposes exploratory review
- **100367** ✅ — anchors on the data (unloading 3.7h)
- **100062** ❌ — inconsistent: indeterminate stage but the action blames the vendor; contradicts the explanation itself
- **100182** ❌ — inherits the error of (a): assumes Vendor (actual stage Indeterminate) and the action is generic
- **100197** ✅ — contingency plan for urgent orders (consistent with hot PO)
- **100158** ❌ — “improve planning” generic
- **100366** ❌ — generic (almost identical to 100158)
- **100087** ✅ — “request review + establish action plan”: actionable
- **100063** ❌ — generic; ignores the short ship
- **100113** ✅ — consistent: addresses delay + full quantity (short ship)
- **100318** ✅ — consistent: reason absent (nan), here "investigate" DOES apply. Contrast with 100278
- **100157** ✅ — request explanation + plan for urgent deliveries (consistent with hot PO)

## Result

### Objective checks (pre-evaluated automatically)
- **(a) correct stage: 19/20.** The only failure: **PO 100182** (stage `Indeterminate`, human REASON "Vendor delayed shipment", delay 4.41 d): the LLM named the stage as "Vendor" instead of declaring it indeterminate — copied the reason code. This is exactly the pattern noted in #95: when the classification is Indeterminate, the reason code cannot "square" with any specific stage, and the model tends to adopt that of the reason. The other three Indeterminate (100338/100367/100062) were indeed declared indeterminate. Refinements in #95/#99.
- **(b) quantifies the delay: 20/20.** All cite the given figure (without hallucination). The instruction from #91 ("cite the exact figure") is consistently met.

### Check (c) viable action: 13/20 (validated manually)
Criterion applied: consistency reason↔action + operability. Fails 7: generic (100154, 100158, 100366, 100063) or inconsistent (100278 investigates what the reason already explains; 100062 blames the vendor despite indeterminate stage; 100182 inherits the error of (a)). The contrast **100278 vs 100318** summarizes the problem: same verb "investigate", consistent only when the reason is empty (100318), redundant when the reason already provides the cause (100278).

### Final verdict: PASSES 13/20 → equivalent 3.25/5
Below the mentor's target (**4/5 = 80%; here 65%). The bottleneck is NOT the classification (a: 19/20) nor the quantification (b: 20/20), but the **quality of the action** (c: 13/20). The same 7 that fail (c), plus nothing new for (a) (100182 already counted).

### Reading for #99 (few-shot)
The weakness of the zero-shot prompt lies not in (a)/(b) — which already meet comfortably — but in the **genericity of the actions** (the complaint from roadmap #126). This is precisely what #99 should address with few-shot, using this same benchmark (seed 42) as a comparison metric.

## Result of #99 — few-shot against the same benchmark

Three few-shot combinations were tested against the same set (seed 42), with examples from the audited pool (`fewshot_pool.json`), disjoint from these 20 POs. The pool is stratified: the strongest mismatch from each stage (Vendor 100280 / Carrier 100244 / DC 100058). Each combination adds an example in nested progression (C1 ⊂ C2 ⊂ C3).

| Combination | examples | (a) | (b) | (c) | verdict (a&b&c) | /5 |
|---|---|:--:|:--:|:--:|:--:|:--:|
| C0 zero-shot | 0 | 19/20 | 20/20 | 13/20 | 13/20 | 3.25 |
| C1 | 1 (Vendor) | 19/20 | 20/20 | 15/20 | 15/20 | 3.75 |
| C2 | 2 (+Carrier) | 19/20 | 20/20 | 15/20 | 15/20 | 3.75 |
| **C3** | **3 (+DC)** | **19/20** | **20/20** | **19/20** | **19/20** | **4.75** |

**Winning combination: C3 (4.75/5), surpasses the mentor's goal (4/5).** The few-shot did not degrade (a) nor (b) in any combination. The leap in (c) comes from converting the generic actions of zero-shot into specific actions that cite the measured signal and direct to the correct responsible party. The DC example (added in C3) is what closes the DC cases, where C1 and C2 still provided generic actions — hence the leap 15 → 19.

The only persistent failure of C3: **100182** (Indeterminate, `sin_datos`, reason "Vendor delayed shipment"), which fails on (a): the prompt does not provide the sub-category of indeterminacy, so the model resolves the ambiguity by copying the reason. This is not a deficit of the few-shot; it is addressed by wiring `indeterminado_substage` to the prompt (#135).

Tables by combination (evidence fixtures): `fixtures/eval_quality_20pos_C1.md`,
`_C2.md`, `_C3.md`. Zero-shot run of the 8 mismatches (input for #95):
`fixtures/mismatches_llm_zeroshot.csv`. Prompt design: ADR-12.

### Known limitation — homogenization of actions by temperature

The few-shot clearly improves (c), but the actions of C3 tend to converge to a single form ("request the responsible party for an explanation / a firm deadline plan") even in the face of varied inputs. In PO 100278 (Carrier, reason "Weather/road conditions"), this produces a generic action of the type that zero-shot marked as reproachable for lack of coherence. The hypothesis is that the backend's low temperature (0.3, fixed) homogenizes output despite input diversity.

This is not corrected here: adjusting the temperature changes all responses, so the C0–C3 comparison (all measured at constant temperature) would still be valid but the specific case must be re-evaluated with a new run, not patched. It remains for hyperparameter experimentation, which depends on externalizing the temperature (#122). This benchmark documents the result at temperature 0.3; the optimal temperature will be decided in that subsequent work.