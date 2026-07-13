# Severity Ranking sobre el output del entregable (#98)

Métrica del mentor (README §6): los POs con `HOT_PO_FLAG=1` y `delay_days_calc > 3` deben tener `severity=HIGH` en **>95%** de los casos.

Columna medida: `severity` del entregable (`po_output.csv`), que **es la del LLM** (`severity ← llm_severidad`, [ADR-10](../documentation/decisiones/ARD-10.md), Opción C). La medición es **empírica**: valida si el LLM respetó `hot & delay>3 ⇒ HIGH`.

## Resultado oficial (severidad del LLM)

- POs hot + delay>3 (denominador): **14**
- De ellos con `severity=HIGH`: **14**
- **Severity Ranking = 100.0%**  (umbral del mentor >95%) → **✅ CUMPLE**

> Granularidad: con 14 POs en el denominador, un solo PO no-HIGH baja la métrica a 92.9%, ya por debajo del 95%. El umbral es, en la práctica, todos-HIGH.

Todos los POs del denominador son HIGH: no hay incumplidores.

## Referencia: baseline determinístico (columna de auditoría F2)

La regla determinística de F2 (`flag_hot_late & delay>3 ⇒ HIGH`) asigna HIGH **por construcción**; se conserva como auditoría (ADR-10) y es la referencia contra la que se mide al LLM.

- POs hot + delay>3 en `df_classified.csv`: **14**
- Con `severity=HIGH` (determinística): **14** (100.0%, por construcción)

> Nota de validación: `flag_hot_late` (bandera de F2) cubre un conjunto más amplio que el filtro explícito `HOT_PO_FLAG==1 & delay_days_calc>3` de esta métrica. Aquí se usa el filtro explícito del README §6, no la bandera.

## Reproducir

```bash
# 1) generar el entregable con la severidad del LLM (GASTA API, ~247 llamadas):
python llm_integration.py --mode full --backend openai
# 2) medir (sin API):
python eval_severity_ranking.py
```

Fuente: `data/processed/po_output.csv` (severidad oficial = LLM) · filtro `HOT_PO_FLAG==1 & delay_days_calc>3` · numerador `severity=='HIGH'`. Baseline de auditoría: `data/processed/df_classified.csv` (severidad determinística de F2).
