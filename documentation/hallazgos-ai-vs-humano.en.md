# Findings: Temporal Computation vs. Human Annotation

This document presents, as a business narrative, where automatic classification by timestamps surpasses human annotation of the reason code, where it fails, what it implies for the analyst's decisions, and what is needed to bring it to production. The thesis is straightforward: temporal computation using timestamps corrects the human reason code, which the mentor reports to be ~20% incorrect.

Each quantitative statement is traceable to an artifact in the repo. The figures come from the unique metrics table (`documentation/metricas-proyecto.md`), the narrative of mismatches (`03_llm_integration/mismatches_ai_vs_humano.md`), and the Phase 2 README (`02_clasif_reglas_negocio/README.md`). The denominators differ between metrics and are not interchangeable; each figure is cited along with its population and is not recalculated here.

## 1. Where Computation Surpasses Human Annotation

Temporal computation aligns with human annotation in 88.7% of classifiable POs (180/203) and disagrees in the remaining ~11%. This disagreement is not a method error: these are the 23 discrepancies where the inherited reason code diverges from what the timestamps indicate, and the evidence points to the timestamps being correct. The mentor's data supports this: human annotation is approximately 20% incorrect, so a method that disagrees where annotation fails is precisely what is sought.

Out of these 23 measured discrepancies, eight are detailed as a stratified sample (three Vendor, three Carrier, two DC) in the mismatch narrative. All eight display the same phenomenon in two variants.

In the three Vendor cases, the human blames the visible link — where the PO physically stalled, be it the carrier or the DC yard — while the appointment approval had already arrived late before, with an STA push of 87 to 125 hours, and the accused segment registers no excess. The human reason ("missed appointment window," "equipment/trailer issue," "yard congestion") describes a downstream symptom, not the cause. The computation isolates the delay where it effectively occurred: in the vendor’s late approval.

In the remaining five cases (Carrier vs. DC), the human confuses two contiguous downstream stages — transit vs. processing at the DC — while the computation measures excess in only one of the two and discards the other for not having measurable excess.

An honest nuance: in four of the eight cases, the LLM itself marked coincidence with the human reason code despite the categorical mismatch between the computation stage and the annotated group. This does not weaken the thesis. It occurs because the text of the reason code thematically aligns with the stage that the computation indicates, not with the stage to which it was archived; that is, even the human wording of the reason is ambiguous in light of the taxonomy of three stages. The source of truth remains the timestamp, not the annotation or the reading the LLM makes of it.

References: reason agreement 88.7% (180/203) and the 23 discrepancies in `documentation/metricas-proyecto.md` (row 2 and context note); the cross-sectional pattern and the eight cases in `03_llm_integration/mismatches_ai_vs_humano.md`.

## 2. Where the Method Fails and Its Limits

The method has blind spots, and its value lies in declaring them instead of guessing. Of the 247 late POs, 31 remain classified as Indeterminate because the computation cannot sustain a dominant cause. This 31 breaks down into two distinct limits.

Seven POs remain as `sin_datos`: they are late but lack `TRAILER_ARRIVE_DT`, so there is no way to measure the carrier and DC segments. It is important to clarify the scope of this gap: in total, 27 POs lack trailer time, but the rule that assigns Vendor by STA push (`APPROVED_DT > STA_DT`) rescues them because it measures the late approval without needing the trailer. Only the 7 that also lack vendor signal remain without diagnosis. The design recovers the majority of records with missing data; the real blind spot is those 7.

Twenty-four POs remain as `sin_causa_dominante`: they are measurable, but none of their segments exceed their threshold, so there is no link to attribute the delay with evidence. The method prefers to mark them Indeterminate rather than force a label without temporal support.

The consequence is that stage accuracy of 100% is measured over 216 evaluable POs (247 minus the 31 Indeterminate), not over the entire population. The method does not guess what it cannot measure: it marks it Indeterminate and leaves it for human review.

On the LLM side, the quality of explanations is not free: it depends on the prompt design. The baseline zero-shot achieved 3.25/5 (13/20), and the winning few-shot variant (C3) rose to 4.75/5 (19/20) against the same benchmark; the subsequent hardening of the prompt (#143) and the re-validation at production temperature (ADR-13) brought that same configuration to 5/5 (20/20), the headline figure of the deliverable today. The difference lies in prompt engineering, not in the model. This implies an operational risk: changing the prompt may degrade quality without notice, and low-confidence explanations still require human judgment.

A second limit lives in the tier-2 action recommendation (#151): when several POs in the same stage share similar evidence, it is correct for them to converge on the same recommendation — but 65 of 247 POs (26.3%) receive their stage's modal hypothesis even though their evidence signature (short-ship, hot PO, match with `REASON_DSC`) differs from that mode, and 51/247 (20.6%) the same for immediate action. This is ignored evidence, not a computation error: stage and severity remain correct — what gets homogenized is the narrated mechanism. Full detail in `03_llm_integration/eval_differentiation.md`.

References: breakdown of Indeterminate (7 `sin_datos` + 24 `sin_causa_dominante`) and the 216 evaluable in `documentation/metricas-proyecto.md` (rows 1 and 5, population section); the Vendor rule by STA push and the 27 without trailer time in `02_clasif_reglas_negocio/README.md`; the zero-shot comparison against few-shot C3 in `documentation/metricas-proyecto.md` (row 3).

## 3. What It Implies for Business Decisions

Temporal computation changes which PO the analyst reviews first and with what confidence they act. Three concrete effects.

Analyst time savings. Automatic classification by timestamps replaces a manual annotation that is ~20% incorrect and delivers, for each PO, a defendable cause with temporal evidence instead of a label that may be blaming the wrong link. The analyst stops auditing reason codes one by one and focuses on the exceptions that the method marks.

Prioritization by severity. The official severity of the deliverable is that produced by the LLM (decision recorded in ADR-10), and its ranking of hot-late cases is accurate in 14/14. The analyst can trust this ranking to decide the order of attention without recalculating severity manually.

What to review first. Hot-late POs (`HOT_PO_FLAG=1` with a delay greater than three days) are the first front due to their severity. After that, the bulk of the delay lies with Vendor: 139 of the 247 late POs (56%) are attributed to late approval, so that is where the greatest systemic improvement leverage lies. In parallel, the 23 discrepancies between computation and annotation mark exactly where to distrust the inherited reason code.

References: LLM severity and Severity Ranking 14/14 in `documentation/metricas-proyecto.md` (row 4) and `documentation/decisiones/ARD-10.md`; breakdown of stages (Vendor 139, 56%) in `documentation/metricas-proyecto.md` (row 5).

## 4. Recommendations for Production

What has been demonstrated operates on a synthetic dataset. Bringing it to production requires three things.

Real data. The thresholds that define excess by segment (vendor 24 h, carrier 8 h) were calibrated on synthetic data; before operating, they must be validated against real historical data, because a poorly set threshold reassigns stages en masse. Threshold decisions are recorded in the corresponding ADRs and are the first point to review with real data.

Monitoring. It is advisable to watch the drift of two signals as an indicator of system health: the level of agreement with human annotation and the rate of Indeterminate. A jump in the Indeterminate rate often signifies deterioration in the quality of incoming data (missing timestamps), not of the method.

Prompt governance. The improvement from zero-shot to few-shot C3 was a measured improvement, not an intuition; this only holds if the prompt is versioned and each change is re-evaluated against the reproducible benchmark (stratified sample, seed 42). Without that control, a prompt adjustment may degrade the quality of explanations without anyone noticing.

## Links

- Input on mismatches: `03_llm_integration/mismatches_ai_vs_humano.md` (#95).
- Metrics and sources table: `documentation/metricas-proyecto.md` (#104).
- Decision log: `documentation/decisiones/` — in particular `ARD-10.md` (severity = LLM), referenced in section 3.
- Validation and QA closure method (#85): `documentation/validacion-y-qa.md`.
- Intra-stage differentiation measurement (#151): `03_llm_integration/eval_differentiation.md`.
- Consume this document: final presentation (#106).