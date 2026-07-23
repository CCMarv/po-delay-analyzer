# Intra-Stage Differentiation of Tier-2 Recommendations (#151)

It is measured whether POs of the same stage receive differentiated recommendations, now that tier-2 issues differential signal (hypothesis + evidence + discriminative step + plan). The operationalization follows [ADR-16](../documentation/decisiones/ARD-16.en.md) §Validation/Discrimination: not the lexical diversity of ADR-15 —two POs with the same evidence must converge— but intra-stage lexical convergence read alongside the covariance signal -> hypothesis.

Method in two layers:

1. **Intra-stage lexical convergence.** By stage, Jaccard over content tokens; two POs converge if Jaccard >= θ=0.25. Clusters are formed by leader/neighborhood (each member within θ of the leader, with no transitive chaining). It is measured on `llm_hipotesis` and `llm_accion_inmediata`.
2. **Covariance signal -> hypothesis.** Each convergent cluster is fixed with the MODAL deterministic evidence signature of its members (`is_short_ship`, `HOT_PO_FLAG`, `llm_coincide_con_reason`; the tercile of excess magnitude is graded signal and does not count for the signature). Convergence with a homogeneous modal signature is *justified* (same evidence -> same recommendation) and the **modal purity** measures that fraction. The failure —the cluster that *ignores the evidence* from ADR-16— consists of the POs **out of signature**: those that receive the modal recommendation even though their strong signature differs from the modal one.

**Headline metric:** fraction of POs out of signature (ignored evidence), reported alongside the convergence landscape (% in cluster, modal purity). A 'suspicious cluster' rate is not used because it saturates: with large clusters, almost any of them include some signal variation and would end up flagged, inflating the failure.

Assumptions: θ=0.25 is inherited from wave 1's fixture (calibrated in ADR-16) and is applied to the complete set. In this run `llm_coincide_con_reason` is binary (149 True / 98 False): the 'not evaluable' state does not appear. Population: 247 late POs with populated tier-2.

## Field: Hypothesis (`llm_hipotesis`)

POs out of signature (ignored evidence): **65/247** (26.3%).

| Stage | n | Average Jaccard | Conv. Clusters | Largest | % in Conv. | Modal Purity | Out of Signature |
|---|--:|--:|--:|--:|--:|--:|--:|
| Carrier | 40 | 0.160 | 5 | 18 | 77.5% | 0.71 | 9 (22.5%) |
| DC | 37 | 0.225 | 2 | 28 | 81.1% | 0.57 | 13 (35.1%) |
| Indeterminate | 31 | 0.097 | 2 | 9 | 45.2% | 0.64 | 5 (16.1%) |
| Vendor | 139 | 0.174 | 10 | 70 | 94.2% | 0.71 | 38 (27.3%) |

### Clusters with Ignored Evidence (Hypothesis)

**Carrier** — cluster of 18 POs, modal purity 0.56, 8 out of signature.

> Modal recommendation: Inadequate route planning by the carrier is causing a significant delay in delivery.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100007 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T0 | Failure in route planning by the carrier XPO Logistics that caused the delay in delivery. |
| 100138 | HOT_PO_FLAG | short=False, hot=1, matches=False, mag=T0 | The delay is due to an inefficiency in the carrier's route planning, which led to a late arrival… |
| 100154 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T2 | Inefficient route planning by the carrier (Estes Express), causing delays in delivery. |
| 100256 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T2 | Lack of coordination in route scheduling by the carrier. |
| 100285 | HOT_PO_FLAG | short=False, hot=1, matches=False, mag=T0 | Route planning problems or network congestion at Werner Enterprises that caused the delay in deliv… |
| 100290 | HOT_PO_FLAG | short=False, hot=1, matches=False, mag=T1 | Problems in route planning or carrier scheduling that caused the delay in arrival at the cent… |
| 100343 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, matches=True, mag=T0 | The underlying mechanism is inefficient route planning by UPS Freight, which caused a delay i… |
| 100392 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T0 | Lack of coordination in the carrier's (Carrier) route planning meant the delivery window was not respec… |

**Carrier** — cluster of 5 POs, modal purity 0.80, 1 out of signature.

> Modal recommendation: Deficiency in route planning or execution by the carrier (UPS Freight).

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100278 | HOT_PO_FLAG | short=False, hot=1, matches=False, mag=T1 | Inefficiency in route planning and delivery execution by UPS Freight |

**DC** — cluster of 28 POs, modal purity 0.54, 13 out of signature.

> Modal recommendation: Dock congestion in the DC yard led to the delay in unloading

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100355 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Dock congestion in the DC yard led to the delay in unloading |
| 100058 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T2 | Congestion in the DC yard delaying the unloading of trailers. |
| 100092 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, matches=False, mag=T2 | Lack of efficient management of the unloading docks at the DC, which caused the delay in operations. |
| 100110 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Dock congestion in the DC yard is the main mechanism that caused the delay. |
| 100117 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Dock congestion in the DC yard, which prevented an efficient flow of loading and unloading. |
| 100145 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Congestion at the DC's loading docks causing a delay in processing. |
| 100202 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Congestion at the distribution center's docks |
| 100216 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Yard congestion at the DC is the main cause of the delay, due to the lack of available docks for un… |
| 100221 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, matches=False, mag=T1 | Dock congestion at the distribution center that prevented efficient unloading. |
| 100298 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Congestion in the DC yard due to the lack of available docks caused the recorded delay. |
| 100321 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, matches=False, mag=T1 | Congestion in the DC yard prevented the timely entry of trailers for unloading. |
| 100357 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Dock congestion in the DC yard |
| 100386 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Congestion in the DC yard is the main cause of the delay, resulting from no docks being available for … |

**Indeterminate** — cluster of 9 POs, modal purity 0.56, 4 out of signature.

> Modal recommendation: If the wait time in the yard (4.9 hours) is an indicator of the carrier's delay, then the mechanism is a transportation delay.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100312 | HOT_PO_FLAG | short=False, hot=1, matches=False, mag=T1 | If the wait time in the yard (4.9 hours) is an indicator of the carrier's delay, then the mechanism is … |
| 100205 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T0 | If the wait time in the yard exceeds a specific threshold considered normal (for example, more than 1 hour), the me… |
| 100242 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T2 | If the wait time in the yard is significantly greater than the average, the mechanism is a coordination failure … |
| 100260 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T2 | If the wait time in the yard (1.9 hours) is justified by the lack of available docks, the responsible mechanism … |

**Indeterminate** — cluster of 5 POs, modal purity 0.80, 1 out of signature.

> Modal recommendation: If it is confirmed that the delay was caused by inefficient rescheduling of the appointment by the supplier, then the mechanism was the lack of temporal coordination in the…

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100206 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T2 | If the delay in rescheduling the appointment was due to a lack of load availability by VITAGEN, th… |

**Vendor** — cluster of 70 POs, modal purity 0.73, 19 out of signature.

> Modal recommendation: The supplier's lack of planning capacity has caused the delay in delivery.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100059 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T2 | The supplier had internal planning and management problems, which caused the delay in delivery. |
| 100063 | is_short_ship | short=True, hot=0, matches=True, mag=T2 | Lack of product due to production capacity problems at the supplier MEDIQ. |
| 100073 | is_short_ship, llm_coincide_con_reason | short=True, hot=0, matches=False, mag=T1 | Lack of available product from the supplier GREENLEAF, which resulted in the short ship and the delay in delivery. |
| 100129 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | The specific mechanism is inadequate planning of delivery appointments by the supplier. |
| 100130 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | The delay is due to inefficient planning of delivery appointments by the supplier. |
| 100165 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Lack of supplier capacity to handle the workload at the delivery yard |
| 100188 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T2 | The delay is due to a lack of supplier capacity to meet the scheduled delivery time, possibl… |
| 100197 | is_short_ship, HOT_PO_FLAG | short=True, hot=1, matches=True, mag=T2 | The cause of the delay is the lack of available inventory from the supplier, SYNCO. |
| 100209 | is_short_ship | short=True, hot=0, matches=True, mag=T2 | Lack of inventory capacity at the supplier to fulfill the complete order. |
| 100213 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T2 | Supplier planning or scheduling problems that have led to a rescheduling of the delivery appointment. |
| 100247 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Failure in the supplier's (Vendor) logistics planning that led to the rescheduling of the delivery. |
| 100302 | is_short_ship, HOT_PO_FLAG | short=True, hot=1, matches=True, mag=T1 | The lack of inventory at the supplier MEDIQ caused the delay and the incomplete shipment. |
| 100361 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T0 | The specific mechanism under the diagnosed stage is the supplier's lack of production capacity, which resulted in … |
| 100369 | is_short_ship | short=True, hot=0, matches=True, mag=T0 | Lack of inventory availability at the supplier GREENLEAF, which resulted in a short ship and delay in deliv… |
| 100371 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | The supplier GREENLEAF's lack of attention to appointment windows is causing the delay in delivery. |
| 100375 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Failure in the supplier's planning/logistics that caused the delay in delivery. |
| 100376 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T2 | Lack of coordination in delivery planning by the supplier Greenleaf, which generated a delay in … |
| 100382 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, matches=False, mag=T2 | The supplier AKZE did not adequately manage its delivery capacity, which resulted in a significant delay in the r… |
| 100395 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Inefficient planning of delivery routes by the supplier Healthcorp caused the delay in deliveries. |

**Vendor** — cluster of 24 POs, modal purity 0.79, 5 out of signature.

> Modal recommendation: The rescheduling of the delivery appointment by the supplier was the result of poor schedule management and route planning.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100044 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T0 | Failure in the supplier's schedule planning and management that caused the rescheduling of the appointment. |
| 100168 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Problems in route planning or delivery scheduling by the supplier GREENLEAF. |
| 100231 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | The delay is due to poor planning and coordination by the supplier VITAGEN, which was unable to meet the tim… |
| 100250 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | The supplier's appointment planning was poor, which led to the loss of the agreed delivery win… |
| 100317 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Lack of coordination in delivery planning by GREENLEAF, resulting in the rescheduling of the… |

**Vendor** — cluster of 15 POs, modal purity 0.73, 4 out of signature.

> Modal recommendation: Lack of available product in the supplier SYNCO's inventory, which caused a short ship

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100101 | llm_coincide_con_reason | short=True, hot=0, matches=False, mag=T2 | The specific mechanism under the diagnosed stage is the lack of product in the supplier's inventory, which caused a… |
| 100148 | HOT_PO_FLAG | short=True, hot=1, matches=True, mag=T2 | The specific mechanism is the lack of product in the supplier's inventory, which prevented the order from being fully f… |
| 100288 | llm_coincide_con_reason | short=True, hot=0, matches=False, mag=T1 | Lack of available product to complete the order in the supplier's inventory. |
| 100318 | llm_coincide_con_reason | short=True, hot=0, matches=False, mag=T0 | The cause of the delay is the lack of inventory at the supplier NOVAPHARM, which has led to a short ship. |

**Vendor** — cluster of 8 POs, modal purity 0.50, 4 out of signature.

> Modal recommendation: Inefficient planning in the supplier's schedule

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100053 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, matches=False, mag=T2 | The supplier's route planning was inefficient, causing an excess in preparation and dispatch time for the P… |
| 100079 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T0 | Failures in planning and time management by the supplier PRIMECARE |
| 100220 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | The underlying mechanism is inefficient route planning by the supplier, which has led to a significant dela… |
| 100388 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Problems in route planning and coordination of departures by the supplier |

**Vendor** — cluster of 4 POs, modal purity 0.50, 2 out of signature.

> Modal recommendation: The supplier did not adequately manage the scheduling of merchandise departures, which resulted in a delay in shipping.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100159 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | The supplier had problems in its route planning or internal scheduling, which led to the delay in shipping. |
| 100259 | is_short_ship | short=True, hot=0, matches=True, mag=T2 | Lack of inventory at the supplier HEALTHCORP, which resulted in an incomplete shipment and a significant delay. |

**Vendor** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: The delay is due to planning problems in deliveries by the supplier SYNCO, resulting in an excess of 17.1 hours.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100211 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T1 | The rescheduling of the appointment is due to a problem in the supplier's planning or schedule that has led to an exces… |

**Vendor** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: The delay was caused by inadequate appointment and scheduling management by the supplier, which resulted in an excess of time not related to inventory problem…

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100157 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T2 | Inefficient scheduling by the supplier MEDIQ, which led to a rescheduling of the delivery and an excess o… |

**Vendor** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: The mechanism under the diagnosed stage is a deficiency in production capacity or operational inefficiency at the supplier BIOPLEX.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100326 | is_short_ship, HOT_PO_FLAG, llm_coincide_con_reason | short=True, hot=0, matches=True, mag=T2 | The specific mechanism under the diagnosed stage is a capacity or product availability problem at the suppl… |

**Vendor** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: Failures in production planning and scheduling by the supplier SYNCO, which did not meet the agreed delivery times despite having inventory available.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100246 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T2 | The supplier experienced logistical problems that led to a delay in delivery, despite having the necessary inventor… |

## Field: Immediate Action (`llm_accion_inmediata`)

POs out of signature (ignored evidence): **51/247** (20.6%).

| Stage | n | Average Jaccard | Conv. Clusters | Largest | % in Conv. | Modal Purity | Out of Signature |
|---|--:|--:|--:|--:|--:|--:|--:|
| Carrier | 40 | 0.174 | 4 | 23 | 85.0% | 0.74 | 9 (22.5%) |
| DC | 37 | 0.130 | 4 | 10 | 54.1% | 0.60 | 8 (21.6%) |
| Indeterminate | 31 | 0.077 | 5 | 4 | 38.7% | 0.75 | 3 (9.7%) |
| Vendor | 139 | 0.143 | 16 | 35 | 86.3% | 0.74 | 31 (22.3%) |

### Clusters with Ignored Evidence (Immediate Action)

**Carrier** — cluster of 23 POs, modal purity 0.61, 9 out of signature.

> Modal recommendation: Contact XPO Logistics to obtain a specific report on the reasons for the delay in the delivery of this PO, focusing on route planning.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100007 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T0 | Contact XPO Logistics to obtain a specific report on the reasons for the delay in the delivery of this PO, foc… |
| 100026 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T1 | Contact Estes Express to obtain a specific report on the transport operation for this PO in order to understand… |
| 100138 | HOT_PO_FLAG | short=False, hot=1, matches=False, mag=T0 | Contact Old Dominion to review the route planning and obtain details on the specific cause of the delay… |
| 100154 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T2 | Contact Estes Express to obtain a detailed report on route planning and delivery operations o… |
| 100256 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T2 | Contact J.B. Hunt to obtain a detailed report on route scheduling and the reasons for the delay in de… |
| 100278 | HOT_PO_FLAG | short=False, hot=1, matches=False, mag=T1 | Contact UPS Freight to obtain a detailed report on route planning and the logistical decision… |
| 100290 | HOT_PO_FLAG | short=False, hot=1, matches=False, mag=T1 | Contact XPO Logistics to obtain a detailed report on route planning and arrival tim… |
| 100343 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, matches=True, mag=T0 | Contact UPS Freight today to obtain details on route planning and the reason for the delay in this PO. |
| 100392 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T0 | Contact Schneider National to obtain a detailed explanation of the delay and confirm their planning proced… |

**DC** — cluster of 10 POs, modal purity 0.60, 4 out of signature.

> Modal recommendation: Coordinate with the DC's operations team to obtain a detailed report on dock management and yard wait times today.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100202 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Coordinate with the Charlotte DC's operations team to confirm the current level of dock congestion and o… |
| 100298 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Coordinate with the DC team to review dock availability in real time and resolve the con… |
| 100321 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, matches=False, mag=T1 | Coordinate with the Kansas City DC staff to obtain a detailed report on yard conditions and the avail… |
| 100386 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Coordinate with the Kansas City DC team to obtain a detailed report on the situation of available doc… |

**DC** — cluster of 6 POs, modal purity 0.67, 2 out of signature.

> Modal recommendation: Contact the Dallas DC supervisor to obtain a detailed report on dock availability and confirm whether there are recurring congestion patterns.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100153 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T2 | Contact the Charlotte DC team to obtain a specific report on dock availability and the situat… |
| 100357 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Contact the Atlanta DC yard supervisor to obtain specific data on dock availability duri… |

**DC** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: Coordinate with the Kansas City DC team to ensure sufficient docks are allocated for unloading today and avoid future congestion.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100123 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, matches=True, mag=T2 | Contact the Kansas City DC supervisor to verify the number of available docks and appointment schedul… |

**DC** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: Contact the Los Angeles DC operation to obtain the exact number of available docks and the number of trucks currently waiting.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100216 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Coordinate with the DC team to obtain the exact number of docks currently available and the reason for the con… |

**Indeterminate** — cluster of 4 POs, modal purity 0.75, 1 out of signature.

> Modal recommendation: Contact the carrier XPO Logistics to obtain the average yard wait time at this DC and compare it against the observed time. If the wait time exceeds the ave…

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100021 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Contact XPO Logistics to obtain specific data on the unloading process: if the unloading time exceeds … |

**Indeterminate** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: Contact the supplier NOVAPHARM to obtain details on the need for the rescheduling and whether there were problems with the original appointment; if the rescheduling was not necessary, tak…

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100206 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T2 | Contact VITAGEN to obtain information on the cause of the appointment rescheduling. If the cause is due to prob… |

**Indeterminate** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: Contact YRC Worldwide to obtain confirmation on the trailer's status, since if the problem is related to the equipment, steps must be taken to ensure that it does not…

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100312 | HOT_PO_FLAG | short=False, hot=1, matches=False, mag=T1 | Contact YRC Worldwide to obtain details on the cause of the delay in the trailer's arrival and confirm whether …|

**Vendor** — cluster of 35 POs, modal purity 0.83, 6 out of signature.

> Modal recommendation: Contact the supplier NOVAPHARM to obtain a specific report on the reasons for the appointment rescheduling and confirm whether there are problems in its route planning.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100053 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, matches=False, mag=T2 | Contact BIOMED to obtain their delivery schedule and confirm whether they are prioritizing PO 100053; assess whether there … |
| 100067 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, matches=False, mag=T0 | Contact the supplier SYNCO to obtain a detailed report on the status of their delivery planning and the caus… |
| 100130 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Contact HEALTHCORP to obtain details on delivery planning and understand the reasons behind the r… |
| 100213 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T2 | Contact the supplier AKZE to obtain precise details on the reasons for the rescheduling and confirm whether it is possibl… |
| 100220 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Contact the supplier PRIMECARE to obtain a detailed report on route planning and delivery capaci… |
| 100231 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Contact the supplier VITAGEN to obtain a report on route planning and resource availability; if the… |

**Vendor** — cluster of 20 POs, modal purity 0.60, 8 out of signature.

> Modal recommendation: Contact GREENLEAF to obtain a detailed inventory report, verifying the availability of the missing boxes.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100073 | llm_coincide_con_reason | short=True, hot=0, matches=False, mag=T1 | Contact GREENLEAF to obtain a detailed inventory report, verifying the availability of the missing bo… |
| 100101 | llm_coincide_con_reason | short=True, hot=0, matches=False, mag=T2 | Contact BIOMED to obtain detailed information on the availability of 48 missing boxes and the specific reas… |
| 100148 | HOT_PO_FLAG | short=True, hot=1, matches=True, mag=T2 | Contact the supplier GREENLEAF to obtain a detailed report on available inventory and confirm whether there is mo… |
| 100197 | HOT_PO_FLAG | short=True, hot=1, matches=True, mag=T2 | Contact SYNCO to obtain an immediate report on inventory availability for PO 100197 and the reason … |
| 100288 | llm_coincide_con_reason | short=True, hot=0, matches=False, mag=T1 | Contact VITAGEN today to obtain the inventory status of the 24 missing boxes and determine whether there is availabil… |
| 100302 | HOT_PO_FLAG | short=True, hot=1, matches=True, mag=T1 | Contact MEDIQ to confirm the exact availability of the 50 missing boxes and obtain a commitment for imme… |
| 100317 | is_short_ship, HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Contact GREENLEAF to obtain a detailed report on the reasons for the appointment rescheduling and the measure… |
| 100318 | llm_coincide_con_reason | short=True, hot=0, matches=False, mag=T0 | Contact NOVAPHARM to obtain confirmation of availability for the missing inventory (47 boxes) and establish a… |

**Vendor** — cluster of 19 POs, modal purity 0.74, 5 out of signature.

> Modal recommendation: Contact the HEALTHCORP representative to obtain specific details on the cause of the rescheduling and confirm their capacity to meet future deliveries on tim…

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100044 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T0 | Contact GREENLEAF to obtain confirmation of availability and capacity to meet future deliver… |
| 100079 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T0 | Contact the supplier PRIMECARE today to obtain details on the cause of the rescheduling and confirm its capaci… |
| 100165 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Contact PRIMECARE to review their current capacity and obtain confirmation of their delivery capacity during peak da… |
| 100188 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T2 | Contact HEALTHCORP to confirm whether there were capacity or congestion problems at their plant that caused the delay,… |
| 100247 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Contact BIOPLEX today to have them provide details on the cause of the delivery rescheduling and confirm the… |

**Vendor** — cluster of 11 POs, modal purity 0.73, 3 out of signature.

> Modal recommendation: Contact PRIMECARE to obtain a detailed report on delivery planning and the specific reasons for the 37.1-hour delay.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100157 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T2 | Contact MEDIQ today to obtain a breakdown of their planning and learn the specific reasons for the resched… |
| 100250 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Contact the supplier AKZE to obtain a report on appointment planning and coordinate measures to improve the… |
| 100382 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, matches=False, mag=T2 | Contact AKZE to obtain a detailed report on the reason for the 87.0-hour delay and the next steps for… |

**Vendor** — cluster of 7 POs, modal purity 0.71, 2 out of signature.

> Modal recommendation: Contact MEDIQ to obtain detailed information on the causes of the delay and whether there is any recurring problem in delivery scheduling.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100246 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T2 | Contact the supplier MEDIQ to obtain specific information on the logistical problems that caused the delay… |
| 100387 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Contact the supplier SYNCO to obtain a detailed explanation of the causes of the shipping delay and confir… |

**Vendor** — cluster of 4 POs, modal purity 0.50, 2 out of signature.

> Modal recommendation: Contact NOVAPHARM to obtain a breakdown of their delivery schedules and confirmation of their planning capacity today.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100262 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Coordinate with AKZE today to obtain confirmation of their processing capacity and ensure that the next… |
| 100395 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Contact Healthcorp to obtain details on their route planning and loading schedules, in order to identify … |

**Vendor** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: Contact the supplier SYNCO to obtain the exact schedule of their current shipments and confirm whether there is any congestion or capacity problem preventing them from meeting the pla…

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100361 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T0 | Contact the supplier MEDIQ to confirm their production capacity and availability to meet future shipmen… |

**Vendor** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: Contact the supplier MEDIQ to obtain a detailed analysis of the causes of the inadequate planning and corrective actions to implement today.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100388 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Contact the supplier VITAGEN today to obtain details on their route planning and dispatch logistics fo… |

**Vendor** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: Contact PRIMECARE to request a review of their route planning and shipment management starting from PO 100129.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100159 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, matches=True, mag=T1 | Contact MEDIQ to request a review of their route planning and learn the specific causes of the dela… |

**Vendor** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: Contact GREENLEAF to obtain detailed information on the reason for the delay in the appointment rescheduling. If the cause is due to planning problems, request a…

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100292 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T0 | Contact PRIMECARE today to obtain a breakdown of the reasons behind the appointment rescheduling. If the cause i… |

**Vendor** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: Contact the supplier SYNCO to obtain a clear commitment on improving the planning of upcoming deliveries and review whether there is an updated delivery calendar.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100371 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Contact the supplier GREENLEAF to obtain a clear commitment regarding their future deliveries and appointment managemen… |

## Reading

Intra-stage convergence is high but mostly *justified*: in the largest Vendor cluster (hypothesis) modal purity is ~0.75 —the same supplier-planning hypothesis on POs that share an evidence signature—. The failure is not the convergence but the tail out of signature (~1 in 6 POs), concentrated in Carrier. The convergence of `immediate action` may also be greater by design: the Concretion Rules of ADR-16 make the action converge to `paso_discriminante` when the mechanism is not confirmed; that is why the modal signature absolves that convergence and only the POs out of signature signal ignored evidence.

## Solution Sketch (input for #154)

Residual homogeneity consists of POs whose evidence signature differs from the modal signature of their cluster and still receive the hypothesis/action of the mode. A contrasting deterministic marker, calculated per PO and injected into the action call prompt, tackles that mechanism: it states how the PO deviates from the modal profile of its stage (for example, "atypical for Vendor: incomplete shipment (short-ship)," "critical flagged PO," "the REASON_DSC annotation disagrees with the measured stage"). Unlike a signal -> hypothesis declarative rule —which the closure of Lane-1 showed to have low performance (moves 2/8 POs)—, the marker does not prescribe the conclusion: it forces the model to condition on the signal it currently ignores and lets it derive the hypothesis (consistent with the analytical layer of ADR-16). It is inexpensive (deterministic, no extra call) and its validation surface is this same out-of-signature metric. First target by impact: Carrier (the highest rate, 30-35%). It remains a sketch; the decision and its relationship with the agentic stage of Lane-2 correspond to #154.

## Reproduce

```bash
# 1) generate the deliverable with populated tier-2 (EXPEND API):
python llm_integration.py --mode full --backend openai --action-call
# 2) measure (without API):
python eval_differentiation.py
```

Source: `data/processed/po_output.csv` · grouping by `stage` · Jaccard convergence θ=0.25 on content tokens · deterministic evidence signature (`is_short_ship`, `HOT_PO_FLAG`, `llm_coincide_con_reason`, tercile of magnitude).
