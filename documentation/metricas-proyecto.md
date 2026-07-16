# Métricas del proyecto

Tabla única de las cinco métricas cabecera del entregable. Cada cifra es trazable a su
artefacto en disco (columna "Reproducción (fuente)") y cada fila declara su población: los
denominadores difieren entre métricas y no deben mezclarse. Este documento compila cifras ya
medidas; no recalcula nada ni ejecuta el LLM. Alimenta la presentación (#106) y el reporte
final (#105).

| Métrica | Valor | Umbral mentor | Población / denominador | Reproducción (fuente) | Estado |
|---|---|---|---|---|:--:|
| Stage accuracy | 100% (208/208) | > 80% | 208 evaluables = 247 tardíos − 39 Indeterminados sin gap medible | `metrics_core.py` sobre `df_classified` (generado por `classifier_core.py`); `02_clasif_reglas_negocio/README.md` §5.1 | ✅ cumple |
| Reason agreement | 88.8% (174/196) | — (referencia, no umbral) | 196 clasificables (tardíos con `reason_group_manual` no nulo; nulos→"Unknown" fuera) | `metrics_core.py`; `02_clasif_reglas_negocio/README.md` §5.4; 8 de los 22 mismatches narrados en `03_llm_integration/mismatches_ai_vs_humano.md` | hallazgo |
| LLM Explanation Quality | 4.75/5 (19/20), few-shot C3; baseline zero-shot 3.25/5 (13/20) | 4/5 (80%) | 20 POs (muestra estratificada 8/4/4/4, semilla 42) | `eval_quality.py`, backend oficial; `03_llm_integration/eval_quality_20pos.md` (+ fixtures C1/C2/C3) | ✅ cumple (C3) |
| Severity Ranking | 100% (14/14) | > 95% | 14 POs con `HOT_PO_FLAG=1 & delay_days_calc>3`, sobre `po_output.csv` (severidad = LLM) | `eval_severity_ranking.py` (sin API); `po_output.csv` generado por `llm_integration.py --mode full`; `03_llm_integration/eval_severity_ranking.md` | ✅ cumple |
| Reparto de etapas | Vendor 131 (53.0%) · Carrier 40 (16.2%) · DC 37 (15.0%) · Indeterminado 39 (15.8%) | N/A (descriptivo) | 247 tardíos | `classifier_core.py` imprime el reparto; `02_clasif_reglas_negocio/README.md` "Reparto resultante" | descriptivo |

## Poblaciones (no mezclar denominadores)

Los cinco denominadores responden a preguntas distintas y no son intercambiables:

- 208 evaluables (Stage accuracy) = los 247 tardíos menos los 39 Indeterminados, que no tienen
  gap dominante medible.
- 196 clasificables (Reason agreement) = tardíos con anotación humana `reason_group_manual` no
  nula; los nulos se mapean a "Unknown" y quedan fuera del denominador.
- 20 muestreados (LLM Explanation Quality) = muestra estratificada 8/4/4/4
  (Vendor/Carrier/Indeterminado/DC), semilla 42, reproducible.
- 14 hot-late (Severity Ranking) = POs con `HOT_PO_FLAG=1` y `delay_days_calc > 3`.
- 247 tardíos (Reparto) = población completa de POs tardíos.

El Indeterminado del reparto (39) se desglosa en 15 `sin_datos` (sin hora de tráiler) + 24
`sin_causa_dominante` (medibles pero sin exceso sobre ningún umbral).

## Notas

- La severidad oficial del entregable es la del LLM (`severity ← llm_severidad`, ADR-10); la
  regla determinística de F2 se conserva como auditoría y da 14/14 por construcción.
- Reason agreement no tiene umbral del mentor: es la tesis del proyecto. El desacuerdo con la
  anotación humana (~20% incorrecta, dato del kickoff) es esperado y deseado; los 22 mismatches
  son la evidencia de que el cómputo temporal por timestamps supera a la anotación manual.
- LLM Explanation Quality: la cifra titular (4.75/5) corresponde a la combinación few-shot
  ganadora C3; el zero-shot (3.25/5) es el baseline de la progresión medida contra el mismo
  benchmark (semilla 42).
