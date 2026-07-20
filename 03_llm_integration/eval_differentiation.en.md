# Intra-Stage Differentiation of Tier-2 Recommendations (#151)

It is measured whether POs of the same stage receive differentiated recommendations, now that tier-2 issues differential signals (hypothesis + evidence + discriminative step + plan). The operationalization follows [ADR-16](../documentation/decisiones/ARD-16.en.md) §Validation/Discrimination: not the lexical diversity of ADR-15 —two POs with the same evidence must converge— but intra-stage lexical convergence read alongside the covariance signal -> hypothesis.

Method in two layers:

1. **Intra-stage lexical convergence.** By stage, Jaccard on content tokens; two POs converge if Jaccard >= θ=0.25. Clusters are formed by leader/neighborhood (each member within θ of the leader, with no transitive chaining). It is measured on `llm_hipotesis` and `llm_accion_inmediata`.
2. **Covariance signal -> hypothesis.** Each convergent cluster is fixed with the MODAL deterministic evidence signature of its members (`is_short_ship`, `HOT_PO_FLAG`, `llm_coincide_con_reason`; the tercile of excess magnitude is graded signal and does not count for the signature). Convergence with a homogeneous modal signature is *justified* (same evidence -> same recommendation) and the **modal purity** measures that fraction. The failure —the cluster that *ignores the evidence* from ADR-16— consists of the POs **out of signature**: those that receive the modal recommendation even though their strong signature differs from the modal one.

**Headline metric:** fraction of POs out of signature (ignored evidence), reported alongside the convergence landscape (% in cluster, modal purity). A 'suspicious cluster' rate is not used because it saturates: with large clusters, almost anyone includes some variation of signals and would be flagged, inflating the failure.

Assumptions: θ=0.25 is inherited from wave 1's fixture (calibrated in ADR-16) and is applied to the complete set. In this run, `llm_coincide_con_reason` is binary (207 True / 40 False): the 'not evaluable' state does not appear. Population: 247 late POs with populated tier-2.

## Field: Hypothesis (`llm_hipotesis`)

POs out of signature (ignored evidence): **46/247** (18.6%).

| Stage | n | Average Jaccard | Conv. Clusters | Largest | % in Conv. | Modal Purity | Out of Signature |
|---|--:|--:|--:|--:|--:|--:|--:|
| Carrier | 40 | 0.148 | 4 | 20 | 75.0% | 0.53 | 14 (35.0%) |
| DC | 37 | 0.215 | 1 | 29 | 78.4% | 0.83 | 5 (13.5%) |
| Indeterminate | 39 | 0.095 | 5 | 7 | 48.7% | 0.79 | 4 (10.3%) |
| Vendor | 131 | 0.165 | 7 | 60 | 87.0% | 0.80 | 23 (17.6%) |

### Clusters with Ignored Evidence (Hypothesis)

**Carrier** — cluster of 20 POs, modal purity 0.45, 11 out of signature.

> Modal recommendation: Ineffective route planning by the carrier.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100290 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Ineffective route planning by the carrier. |
| 100024 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | A failure in the carrier's route planning resulted in an excess of 25.7 hours in transit to the… |
| 100214 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T2 | Failures in route planning and adaptability of the carrier to adverse weather conditions. |
| 100244 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T2 | Poor route planning by the carrier, resulting in prolonged transit times. |
| 100261 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Failure in route planning by the carrier YRC Worldwide, resulting in non-compliance with the time window. |
| 100278 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Poor route planning by the carrier (UPS Freight) resulting in excessive transit time. |
| 100285 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, matches=False, mag=T0 | Failure in route planning by the carrier Werner Enterprises, resulting in inefficient transit. |
| 100286 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T2 | The specific mechanism is the carrier's inadequate route planning, which led to an excess of… |
| 100343 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T0 | Inefficient route planning by the carrier is causing delivery delays. |
| 100380 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | The carrier's route planning was ineffective, leading to an excess of 4.2 hours in transit. |
| 100392 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Inefficient planning of routes by the carrier leading to excessive transit delays. |

**Carrier** — cluster of 5 POs, modal purity 0.60, 2 out of signature.

> Modal recommendation: Issue with the carrier's equipment/trailer, resulting in a delay in delivery.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100099 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Issue with the carrier's equipment/trailer, resulting in a delay in delivery. |
| 100310 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Issue with the carrier's equipment/trailer (Carrier) that delayed transportation. |

**Carrier** — cluster of 3 POs, modal purity 0.67, 1 out of signature.

> Modal recommendation: The carrier's route planning (UPS Freight) did not adequately anticipate adverse weather conditions, resulting in excessive transit time.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100315 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T2 | The carrier's route planning was inadequate due to weather conditions, leading to an excess of… |

**DC** — cluster of 29 POs, modal purity 0.83, 5 out of signature.

> Modal recommendation: Dock congestion at the DC is causing delays in unloading and waiting in the yard.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100321 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Dock congestion at the DC is causing delays in unloading and waiting in the yard. |
| 100092 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T2 | Congestion in the DC yard caused a delay in receiving the load. |
| 100123 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T2 | Yard congestion at the DC prevented timely unloading, resulting in an excess of 21.4 hours of waiting. |
| 100204 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Dock congestion at the distribution center (DC) prolonged unloading time. |
| 100221 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Congestion at unloading docks at the DC. |

**Indeterminate** — cluster of 4 POs, modal purity 0.50, 2 out of signature.

> Modal recommendation: If the rescheduling of the delivery appointment was caused by supplier planning issues, then the mechanism is a lack of coordination in the availability of car…

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100206 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T2 | If the rescheduling of the appointment was primarily caused by a failure in supplier planning, then the… |
| 100254 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | If the rescheduling of the appointment was caused by logistical issues with the carrier, then the mechanism might be… |

**Indeterminate** — cluster of 3 POs, modal purity 0.67, 1 out of signature.

> Modal recommendation: The inefficient rescheduling mechanism by the supplier is behind the Indeterminate stage of the delay.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100375 | HOT_PO_FLAG | short=False, hot=1, matches=False, mag=T2 | If it is confirmed that the supplier did not meet the agreed shipping time, the mechanism is a delay in the management of… |

**Indeterminate** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: The delay is due to a lack of coordination in shipping between the supplier and the carrier, resulting in delays in meeting the delivery deadline.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100249 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T1 | The lack of coordination between the supplier (HEALTHCORP) and the carrier (Old Dominion) caused the indefinite delay… |

**Vendor** — cluster of 60 POs, modal purity 0.75, 15 out of signature.

> Modal recommendation: Lack of efficiency in supplier planning and scheduling, resulting in a delay in the delivery appointment.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100063 | is_short_ship | short=True, hot=0, matches=True, mag=T2 | Lack of available product in the supplier's inventory that resulted in the short ship and delay in delivery. |
| 100079 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T0 | Failure in the supplier's schedule planning that led to the rescheduling of the delivery appointment. |
| 100086 | is_short_ship | short=True, hot=0, matches=True, mag=T1 | The cause of the delay is the lack of inventory at the supplier Synco, resulting in an incomplete shipment. |
| 100094 | is_short_ship | short=True, hot=0, matches=True, mag=T1 | The main cause of the delay is the lack of inventory at the supplier, resulting in a short ship. |
| 100129 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | The delay is due to poor handling in the supplier's delivery planning, caused by a lack of coordination… |
| 100197 | is_short_ship, HOT_PO_FLAG | short=True, hot=1, matches=True, mag=T2 | The underlying mechanism is the lack of inventory availability at the supplier, which caused the delay in the entr… |
| 100209 | is_short_ship | short=True, hot=0, matches=True, mag=T2 | The main cause of the delay is the lack of available inventory at the supplier, resulting in a short ship. |
| 100213 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T2 | Issues in supplier planning and scheduling (AKZE) led to the rescheduling of the delivery appointment, c… |
| 100220 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | The supplier had planning and scheduling issues that led to the rescheduling of the appointment and excess in … |
| 100247 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Poor planning or scheduling of delivery by the supplier BIOPLEX, which resulted in an excess of time in the … |
| 100317 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Lack of planning or coordination of deliveries by the supplier. |
| 100330 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Lack of coordination in the delivery planning by the supplier. |
| 100371 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Lack of scheduling capacity and effective coordination in the delivery process by the supplier GREENLEAF. |
| 100382 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, matches=False, mag=T2 | Lack of coordination in shipping planning by the supplier. |
| 100387 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Failure in shipping planning by the supplier SYNCO, resulting in the delay in delivery. |

**Vendor** — cluster of 21 POs, modal purity 0.90, 2 out of signature.

> Modal recommendation: Poor planning and coordination in the delivery schedule by the supplier.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100044 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T0 | The rescheduling of delivery was due to failures in route planning or management by the supplier… |
| 100157 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T2 | Failure in the supplier's route planning and coordination. |

**Vendor** — cluster of 14 POs, modal purity 0.86, 2 out of signature.

> Modal recommendation: Lack of available product in the supplier's inventory, which resulted in the short ship and the PO delay.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100148 | HOT_PO_FLAG | short=True, hot=1, matches=True, mag=T2 | The specific mechanism is that the supplier did not have enough available inventory to fulfill the PO, causing… |
| 100302 | HOT_PO_FLAG | short=True, hot=1, matches=True, mag=T2 | Lack of inventory or production issues at the supplier MEDIQ. |

**Vendor** — cluster of 6 POs, modal purity 0.50, 3 out of signature.

> Modal recommendation: The supplier had issues with production capacity or available inventory to fulfill the order on time.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100232 | HOT_PO_FLAG | short=False, hot=0, matches=True, mag=T2 | The supplier had issues with production capacity or available inventory to fulfill the order on time. |
| 100288 | is_short_ship, HOT_PO_FLAG | short=True, hot=0, matches=True, mag=T1 | The underlying mechanism is the lack of inventory or production capacity at the supplier VITAGEN to fulfill the c… |
| 100320 | HOT_PO_FLAG | short=False, hot=0, matches=True, mag=T0 | The supplier had issues in shipping planning that resulted in a delay in delivery, despite fulfilling… |

**Vendor** — cluster of 3 POs, modal purity 0.67, 1 out of signature.

> Modal recommendation: The specific mechanism under the diagnosed stage is a deficiency in the supplier's planning and scheduling management.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100369 | is_short_ship | short=True, hot=0, matches=True, mag=T0 | The specific mechanism under the diagnosed stage is the lack of adequate inventory from the supplier, which caused… |

## Field: Immediate Action (`llm_accion_inmediata`)

POs out of signature (ignored evidence): **38/247** (15.4%).

| Stage | n | Average Jaccard | Conv. Clusters | Largest | % in Conv. | Modal Purity | Out of Signature |
|---|--:|--:|--:|--:|--:|--:|--:|
| Carrier | 40 | 0.151 | 5 | 13 | 70.0% | 0.57 | 12 (30.0%) |
| DC | 37 | 0.138 | 3 | 11 | 48.6% | 0.78 | 4 (10.8%) |
| Indeterminate | 39 | 0.096 | 4 | 9 | 43.6% | 0.65 | 6 (15.4%) |
| Vendor | 131 | 0.135 | 12 | 31 | 82.4% | 0.85 | 16 (12.2%) |

### Clusters with Ignored Evidence (Immediate Action)

**Carrier** — cluster of 13 POs, modal purity 0.62, 5 out of signature.

> Modal recommendation: Contact J.B. Hunt for a detailed report on route planning for this PO to understand the cause of the delay.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100024 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Contact Schneider National today for a detailed report on route planning and any congestion… |
| 100261 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Contact YRC Worldwide for their report on route planning and delivery schedule for this PO. |
| 100286 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T2 | Contact Werner Enterprises for a detailed report on route planning and factors causing delays. |
| 100380 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Contact XPO Logistics for a detailed report on route management that led to this delay, especially… |
| 100392 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Contact Schneider National for a detailed report on the route planning used for this… |

**Carrier** — cluster of 8 POs, modal purity 0.50, 4 out of signature.

> Modal recommendation: Contact YRC Worldwide for a detailed report on the equipment/trailer issue that caused 23.2 hours of excess in delivery.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100099 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Contact Estes Express for a detailed report on the equipment/trailer issue and its causes; if not pr… |
| 100138 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, matches=False, mag=T0 | Contact Old Dominion for a detailed report on the causes of the 1.9 hours excess in the delivery of the… |
| 100239 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T2 | Contact Werner Enterprises for a detailed report on the equipment issue that caused the delay; if… |
| 100310 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Contact Estes Express for detailed information about the equipment/trailer issue that caused the delay. |

**Carrier** — cluster of 3 POs, modal purity 0.67, 1 out of signature.

> Modal recommendation: Contact XPO Logistics for details on the route planning used in the delivery of PO 100290 and confirm if there were congestion problems or last…

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100290 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Contact XPO Logistics for details on the route planning used in the delivery of PO 100290… |

**Carrier** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: Contact Werner Enterprises for data on route planning and how they responded to specific weather conditions in this case; if it is confirmed that not…

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100285 | HOT_PO_FLAG | short=False, hot=1, matches=False, mag=T0 | Contact Werner Enterprises for detailed information on route planning and confirm if the weather conditions… |

**Carrier** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: Contact UPS Freight for specific data on route planning and conditions faced during transit; if the response reveals failures in planning…

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100315 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T2 | Contact UPS Freight to request specific details on the route planning that led to the delay, co… |

**DC** — cluster of 11 POs, modal purity 0.73, 3 out of signature.

> Modal recommendation: Coordinate with the DC team to obtain a report on door availability today and confirm if congestion in the yard persisted.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100123 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T2 | Coordinate with the DC team to obtain a report on door availability today and confirm if congestion… |
| 100204 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Contact the DC manager to confirm if there is congestion at the unloading docks and obtain the number of trucks… |
| 100321 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Coordinate with the DC team to obtain a report on available doors and truck scheduling, par… |

**DC** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: Coordinate with the DC to obtain data on the number of doors available and vehicle flow for the day of receipt; if it is confirmed that there are not enough doors di…

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100221 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Coordinate with the reception staff at Charlotte DC to obtain data on the number of receipts and the allocation d… |

**Indeterminate** — cluster of 9 POs, modal purity 0.56, 4 out of signature.

> Modal recommendation: Contact the supplier NOVAPHARM for accurate information on trailer arrival time and confirm if the appointment rescheduling caused the delay.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100072 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T0 | Contact supplier NOVAPHARM for clarity on the specific reasons behind the rescheduling of the… |
| 100164 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T1 | Contact supplier HEALTHCORP for specific information on the logistical difficulties that caused the… |
| 100273 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T1 | Obtain specific information on trailer arrival time: if significant waiting time is documented… |
| 100300 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T2 | Contact SYNCO for accurate information on the reasons for the rescheduling of the delivery appointment, specifically… |

**Indeterminate** — cluster of 4 POs, modal purity 0.75, 1 out of signature.

> Modal recommendation: Contact Old Dominion for specific information on the delivery of this PO and confirm if there were logistical problems on their side that caused the delay.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100249 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T1 | Contact supplier HEALTHCORP to confirm if there were coordination or communication problems with Old Dominion that … |

**Indeterminate** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: Contact the supplier for specific details on the reason for rescheduling the delivery and verify if it is a production capacity issue.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100242 | llm_coincide_con_reason | short=False, hot=0, matches=True, mag=T2 | Contact supplier BIOMED for clarity on the specific reason for the rescheduling of the appointment; if the reason… |

**Vendor** — cluster of 31 POs, modal purity 0.84, 5 out of signature.

> Modal recommendation: Contact supplier GREENLEAF for specific details on the cause of the rescheduling and to confirm their operational capacity for future deliveries.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100129 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T1 | Contact PRIMECARE to review the specific details of their delivery planning and understand why they n… |
| 100213 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T2 | Contact supplier AKZE today for detailed information on the cause of the rescheduling of the appointment and c… |
| 100247 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Coordinate with BIOPLEX to obtain specific details on the reason for the rescheduling and the criteria they use p… |
| 100317 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Contact supplier GREENLEAF for a detailed report on the cause of the rescheduling, specifically… |
| 100361 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T0 | Contact supplier MEDIQ to confirm the specific reason behind the delay in delivery and obtain a comprom… |

**Vendor** — cluster of 24 POs, modal purity 0.88, 3 out of signature.

> Modal recommendation: Contact supplier SYNCO for a detailed report on the planning and the reason for the delay in shipping this PO.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100387 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T1 | Contact supplier SYNCO for a detailed report on the planning and the reason for the delay in the shipment… |
| 100063 | is_short_ship | short=True, hot=0, matches=True, mag=T2 | Contact supplier MEDIQ for a detailed report on inventory availability and production ac… |
| 100073 | is_short_ship | short=True, hot=0, matches=True, mag=T1 | Contact Greenleaf for a detailed report on inventory availability and the production of PO… |

**Vendor** — cluster of 14 POs, modal purity 0.86, 2 out of signature.

> Modal recommendation: Contact Synco for information on inventory availability and confirm if they can re-issue the 23 missing boxes (80 boxes ordered - 57 boxes shipped) ho…

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100197 | HOT_PO_FLAG | short=True, hot=1, matches=True, mag=T2 | Contact supplier SYNCO for specific information on inventory availability and the reasons for… |
| 100302 | HOT_PO_FLAG | short=True, hot=1, matches=True, mag=T2 | Contact supplier MEDIQ to confirm inventory availability and obtain a production plan that ensures… |

**Vendor** — cluster of 12 POs, modal purity 0.75, 3 out of signature.

> Modal recommendation: Contact NOVAPHARM for a detailed breakdown of their route planning that led to the rescheduling of the delivery appointment.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100157 | HOT_PO_FLAG | short=False, hot=1, matches=True, mag=T2 | Contact MEDIQ for specific information on the cause of the delay in scheduling and the rescheduling… |
| 100220 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Contact PRIMECARE for a detailed report on the cause of the excess of 27.4 hours in delivery and the rescheduling… |
| 100236 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, matches=False, mag=T2 | Contact BIOPLEX for a detailed breakdown of their current production planning and inventory availability… |

**Vendor** — cluster of 3 POs, modal purity 0.67, 1 out of signature.

> Modal recommendation: Contact VITAGEN today for a detailed report of their current inventory and production capacity regarding PO 100288.

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100288 | is_short_ship | short=True, hot=0, matches=True, mag=T1 | Contact VITAGEN today for a detailed report of their current inventory and production capacity regarding… |

**Vendor** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: Contact HEALTHCORP for specific details about their delivery capacity and the reasons behind the rescheduling of the appointment, and confirm that no further rescheduling…

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100130 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Contact HEALTHCORP for the specific reason that caused the excess in the rescheduling of the appointment and evaluate… |

**Vendor** — cluster of 2 POs, modal purity 0.50, 1 out of signature.

> Modal recommendation: Contact AKZE for detailed information on their route planning that led to an excess of 31.2 hours, and confirm if there are changes to prevent it from happening again…

| PO Out of Signature | Differs In | Evidence Signature | Recommendation |
|---|---|---|---|
| 100330 | llm_coincide_con_reason | short=False, hot=0, matches=False, mag=T0 | Contact PRIMECARE for information on the cause of the excess of 20.8 hours in their delivery process and coordinate… |

## Reading

Intra-stage convergence is high but mostly *justified*: in the largest Vendor cluster (hypothesis) modal purity is ~0.75 —the same planning hypothesis of the supplier on POs that share evidence signature—. The failure is not convergence but the tail out of signature (~1 in 6 POs), concentrated in Carrier. The convergence of `immediate action` may also be greater by design: the Concretion Rules of ADR-16 converge action to the `discriminative_step` when the mechanism is not confirmed; therefore, the modal signature absolves that convergence and only the POs out of signature signal ignored evidence.

## Solution Sketch (input for #154)

Residual homogeneity consists of POs whose evidence signature differs from the modal signature of their cluster and still receive the hypothesis/action of the mode. A contrasting deterministic marker, calculated per PO and injected into the action call prompt, tackles that mechanism: it states how the PO deviates from the modal profile of its stage (for example, "atypical for Vendor: incomplete shipment (short-ship)," "critical flagged PO," "the REASON_DSC annotation disagrees with the measured stage"). Unlike a signal -> hypothesis declarative rule—which the closure of Lane-1 showed to have low performance (moves 2/8 POs)—the marker does not prescribe the conclusion: it forces the model to condition on the signal it currently ignores and allows it to derive the hypothesis (consistent with the analytical layer of ADR-16). It is inexpensive (deterministic, no extra call) and its validation surface is this same out of signature metric. First target by impact: Carrier (the highest rate, 30-35%). It remains as a sketch; the decision and its relationship with the agentic stage of Lane-2 correspond to #154.

## Reproduce

```bash
# 1) generate the deliverable with populated tier-2 (EXPEND API):
python llm_integration.py --mode full --backend openai --action-call
# 2) measure (without API):
python eval_differentiation.py
```

Source: `data/processed/po_output.csv` · grouping by `stage` · Jaccard convergence θ=0.25 on content tokens · deterministic evidence signature (`is_short_ship`, `HOT_PO_FLAG`, `llm_coincide_con_reason`, tercile of magnitude).