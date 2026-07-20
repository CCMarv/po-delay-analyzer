# User Personas — PO Delay Root Cause Analyzer

> Versioned design document (`documentation/`). Defines the two user profiles that consume the tool and the design decisions (prompt and interface) that each determines. It arises from the mentors' recommendation (sync 2026-06-26) to use user personas to guide the design of Phase 4. Each persona defines a **view** of the program. Spanish version; the English version will be added at the end of development, according to the repository's bilingual convention.

## What are these personas and why two

A persona here is a design tool, not a character sheet: each field exists to force a specific decision about the prompt or the app, and a field that does not change any decision is omitted. The names ("Diego", "Ravi") are interchangeable handle labels, not the substance.

The two profiles are organized by mode of consumption —individual consultation of a PO versus batch reporting— because that axis precisely defines the two surfaces of the tool. Both are internal to the buying organization and both are cause-agnostic (they do not own a single stage). They remain as two distinct personas, and not one with two tasks, because they differ across three simultaneous axes: the unit of work (a late PO versus the population), the temporal direction (validating a case backward versus finding the pattern forward), and the role of the LLM (consuming the prose explanation versus adding structured fields).

The entities measured by the system —vendors and carriers— are not users: they are subjects of measurement and, in the case of the vendor, potential recipients of a derived report (a scorecard). Only the two profiles below operate the tool.

## Comparative View

| Axis | Persona A — Individual Consultation | Persona B — Batch Reporting |
|---|---|---|
| Handle | "Diego" | "Ravi" |
| Role | Inbound Exception Coordinator | Supply-Chain Analyst / Network RCA |
| Unit of Work | A delayed PO | The population of delays |
| Scope of Cause | Cause-agnostic (the 4 stages) | Cause-agnostic, network-scoped (Vendor + Carrier + DC) |
| Temporal Direction | Retrospective: validates the case | Prospective: finds the pattern |
| Central Question | What happened here and is it true? | Where is the systemic pattern? |
| Role of the LLM | Central (consumes the prose) | Marginal (adds structure) |
| Output Action | Closes or routes the exception | Report enabling decisions of others |
| Frequency | High, reactive | Low, proactive |

## Persona A — Inbound Exception Coordinator ("Diego")

- Role: inbound exception coordinator, internal to the buying organization. Cause-agnostic: resolves exceptions of late POs one by one. Implements fixes within reach, validates evidence, routes, and verifies what does not belong to him.
- Objective (JTBD): close each exception with the confirmed correct cause, quickly, without propagating the human coding error to the aggregate.
- Question to the tool: "What exactly happened in this PO, is the cause true, and what should proceed now?"
- Trigger: a late PO enters his queue, or someone queries a specific PO. Reactive, high frequency, case by case.
- What he consumes: the complete PO bundle — reconstructed timeline, `stage_primary`, the explanation in prose (`llm_causa_raiz`), the action (`llm_accion_recomendada`), `llm_severidad`, and critical for validation: `llm_coincide_con_reason` and `llm_confianza`. It is the surface where the prose of the LLM delivers its value.

Activities:

1. Opens the late PO and reads the reconstructed timeline.
2. Checks the classified stage and severity.
3. Contrasts with `REASON_DSC` via `coincide_con_reason`; a mismatch is a finding, not an error.
4. Reads the explanation and action; uses `confianza` to gauge how much to trust.
5. Executes what is within his authority: corrects a poorly loaded master data item, confirms or reschedules an appointment, follows up with the vendor on that shipment.
6. For causes outside his control (DC staffing, carrier SLA): routes to the owner of that stage and verifies that action was taken.
7. Marks the case as validated; this purified stream feeds the batch report.

- Output Action: PO with confirmed cause and closed or routed action; evidence of timeline available for any potential dispute.
- Trusts when: the explanation respects the order of timestamps, the evidence is complete, and the cause is consistent with how the process operates. Distrusts when: the output is vague or of a black box, a unique event drags the entire conclusion, or data is missing. Design implication: timeline as primary evidence, visible trust indicator, prominent flag of disagreement (vs. `REASON_DSC`).
- Out of scope: does not aggregate, does not rank vendors, does not decide structural changes. One PO at a time. If a decision requires the pattern of many POs, it belongs to Ravi's surface.

## Persona B — Supply-Chain Analyst / Network RCA ("Ravi")

- Role: supply chain analyst in charge of dashboards, root cause trends, and reporting for management. Internal to the buying organization. Cause-agnostic and network-scoped: covers Vendor + Carrier + DC equally. Does not own any operational relationship; measures the network and makes it clear for decision-makers.
- Objective (JTBD): convert the historical data of late POs into actionable and auditable intelligence, separating the structural problem from the noise at once, through the three causes.
- Question to the tool: "Where is the systemic pattern in the network — which stage, which entity — with how much evidence, and is it reproducible to defend it?"
- Trigger: reporting cycle (monthly/quarterly), preparation of an executive review, or a management question ("Why did inbound reliability fall?"). Proactive, low frequency, network level.
- What he consumes: structured aggregates across the three causes — distribution of `stage_primary` (Vendor / Carrier / DC / Indeterminate; today 53.0 / 16.2 / 15.0 / 15.8 % across 247 delays), counts by entity (vendor, carrier, DC), severity distribution, disagreement rate vs. `REASON_DSC`, and temporal trend. The prose of the LLM is almost irrelevant; what matters is that the attribution is consistent and reproducible from timestamps. The batch is deterministic aggregation.

Activities:

1. Runs the batch over the period and reviews the split by stage (Is the network still Vendor-dominant? Did it shift?).
2. For each cause, adds by entity: which vendor, which carrier, which DC concentrates the delays.
3. Isolates outliers by stage (vendor X, lane Y, a specific DC — the EDA has already marked Phoenix as a candidate).
4. Quantifies: N delays, % of the bucket, accumulated severity, trend vs. previous period.
5. Audits the quality of attribution: Is the disagreement rate with human coding systematic (signal) or random (noise)?
6. Produces the report/dashboard segmented by cause and derived artifacts (including a vendor scorecard when applicable, as one of several outputs).
7. Delivers the finding to the owner who can act: Vendor → procurement; Carrier → transport coordinator; DC → center operations. Presents; they execute.

- Output Action: network report/dashboard, segmented by cause, enabling structural decisions of others — not an action that Ravi himself carries out.
- Trusts when: the attribution is repeatable and explainable across many orders, the disagreement is systematic, and the logic is auditable over time. Distrusts when: the labels are noisy or uncalibrated, the outputs are unstable, or the disagreement appears random. Design implication: aggregates, trends, and disagreement rate as first-class metrics; visible reproducibility; drill-down to individual POs (bridge to Diego's surface) to inspect the evidence behind a number.
- Out of scope: does not resolve exceptions case by case (that is Diego); does not take corrective action (that is the owner of the stage); does not operate on the prose of an isolated PO. His product is the report, not the action.

## Relationship between the Two Personas

The two personas do not collapse into one because they differ on three axes simultaneously, and just one is enough to distinguish them: the unit of work (Diego operates a PO, Ravi the population), the temporal direction (Diego looks back to validate a case, Ravi looks at the history to find the pattern forward), and the product (Diego closes or routes an exception, Ravi delivers a report that others use to decide). A direct contrast applied: neither would arrive at the same decision looking at the same screen, because Diego never aggregates and Ravi never operates a loose case.

A two-way pipeline exists between them, not two islands. The stream of cases validated by Diego (his step 7) is the purified input that makes Ravi's aggregate trustworthy; without that case-by-case validation, the batch drags the ~20% error of human coding. In the opposite direction, Ravi's drill-down lands on Diego's surface when he needs to see the evidence behind an aggregated number. Diego validates upward; Ravi inspects downward. The operational synthesis: the case validates, the pattern decides.

## Design Implications

Each persona defines a distinct view of the program, and from there spring the starting points for the design of Phase 4.

Diego's surface is a view of an individual PO focused on evidence: reconstructed timeline as the primary element, stage and severity visible, the explanation and action from the LLM, the trust indicator, and —prominently— the flag of disagreement with `REASON_DSC`, which is where the tool adds value over human annotation. It remains an open decision for Phase 4 whether this surface needs a status/tracking notion to support the step of "verifying" (going back to the PO to confirm that the action landed) or if that verification occurs outside the tool.

Ravi's surface is a report/dashboard of the population: distribution by stage, counts by entity across the three causes, severity distribution, temporal trend, and the disagreement rate vs. `REASON_DSC` elevated to first-class metric — which additionally maps directly to the threshold of the Reason Code Agreement mentor. It includes drill-down to the individual PO as a bridge to Diego's surface. It does not consume prose from the LLM.

### What Each Persona Consumes from the Handoff Artifact

The handoff contract F3→F4 (issue #100, verified in `../tests/test_handoff_contract.py`) persists **all** columns of the classified DataFrame plus those added by the LLM in Phase 3 —not a curated subset. Each persona consumes a distinct cut of that artifact, and that cut is what feeds their view:

| Persona | Columns Consumed | Purpose |
|---|---|---|
| Diego (individual) | `PO_DT … RECPT_DT` (timestamps of the lifecycle), `stage_primary`, `severity`, `llm_causa_raiz`, `llm_accion_recomendada`, `llm_confianza`, `llm_coincide_con_reason` | Reconstruct the PO timeline and read the diagnosis in prose + validation indicators |
| Ravi (batch) | `stage_primary`, `VENDOR_NAME` / `CARRIER_PARTY_NAME` / `DC_LOC_NAME`, `severity`, `llm_coincide_con_reason` vs `REASON_DSC` | Split by stage, counts by entity, severity distribution, and aggregated disagreement rate |

Operational implication: Diego’s view depends on columns that Phase 3 still produces (`llm_*`; the `llm_out.csv` does not yet exist in the repo) and a reconstructed timeline from the timestamps — which the current app placeholder does not compile. Ravi’s view elevates the disagreement rate (`llm_coincide_con_reason` aggregated) to a first-class metric, which maps directly to the threshold of the Reason Code Agreement mentor. The personas do not request new columns to the contract; they establish **which cut of the artifact delivers value for each view**, and thus guide the final Phase 4 once Phase 3 closes its output.

## Traceability: persona → view → issue

Each persona defines a view of the program. The objective of Phase 4 is two views by mode of consumption (individual and aggregated); how the screens by entity of the placeholder fit within them is an open redesign decision.

| Persona | View | Board Issue | Status |
|---|---|---|---|
| Diego | Individual consultation of a PO (timeline + diagnosis + LLM prose) | #102 (`fundamental`) | Placeholder in `../04_app/app.py`; to be redone after closing Phase 3 |
| Ravi | Aggregated batch report (split, counts, severity, disagreement rate) | #103 | Placeholder in dashboards by entity; to be redone after closing Phase 3 |
| Bridge Ravi → Diego | Drill-down from an aggregate to an individual PO | Shared scope of #102/#103 | Pending design |

The current app (`../04_app/`) is an advanced placeholder, organized by entity of the chain (Vendor / Carrier / DC), built to have a presentable output before Phase 3 sets its output. These personas are the criteria by which Phase 4 will be redesigned, not a justification for the placeholder. The decision that fixes this axis is recorded in `decisiones/ARD-09.en.md`.

## Scope and Traceability

The two profiles stem from the operational model of the inbound supply chain and the outputs that the tool itself produces; they do not come from user research, as the dataset is synthetic and the tool is not deployed. The defensible framing is that of a decision support and auditing system for late POs — retrospective, not predictive — validated in a controlled environment. This derivation from the operational model is, in itself, the input for business relevance criteria and stakeholder insight of the rubric.