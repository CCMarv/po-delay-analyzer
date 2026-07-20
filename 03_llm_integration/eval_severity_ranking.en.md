# Severity Ranking on Deliverable Output (#98)

Mentor Metric (README §6): POs with `HOT_PO_FLAG=1` and `delay_days_calc > 3` must have `severity=HIGH` in **>95%** of cases.

Measured column: `severity` of the deliverable (`po_output.csv`), which **is that of the LLM** (`severity ← llm_severidad`, [ADR-10](../documentation/decisiones/ARD-10.en.md), Option C). The measurement is **empirical**: it validates whether the LLM respected `hot & delay>3 ⇒ HIGH`.

## Official Result (LLM Severity)

- Hot POs + delay>3 (denominator): **14**
- Of those with `severity=HIGH`: **14**
- **Severity Ranking = 100.0%** (mentor threshold >95%) → **✅ COMPLIES**

> Granularity: with 14 POs in the denominator, a single non-HIGH PO drops the metric to 92.9%, below 95%. The threshold is, in practice, all-HIGH.

All POs in the denominator are HIGH: there are no non-compliers.

## Reference: Deterministic Baseline (Audit Column F2)

The deterministic rule of F2 (`flag_hot_late & delay>3 ⇒ HIGH`) assigns HIGH **by construction**; it is maintained as an audit (ADR-10) and is the reference against which the LLM is measured.

- Hot POs + delay>3 in `df_classified.csv`: **14**
- With `severity=HIGH` (deterministic): **14** (100.0%, by construction)

> Validation Note: `flag_hot_late` (F2 flag) covers a broader set than the explicit filter `HOT_PO_FLAG==1 & delay_days_calc>3` of this metric. Here, the explicit filter from README §6 is used, not the flag.

## Reproduce

```bash
# 1) generate the deliverable with LLM severity (USES API, ~247 calls):
python llm_integration.py --mode full --backend openai
# 2) measure (without API):
python eval_severity_ranking.py
```

Source: `data/processed/po_output.csv` (official severity = LLM) · filter `HOT_PO_FLAG==1 & delay_days_calc>3` · numerator `severity=='HIGH'`. Audit baseline: `data/processed/df_classified.csv` (deterministic severity of F2).