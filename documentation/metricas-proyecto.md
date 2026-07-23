# Métricas del proyecto

Tabla única de las seis métricas cabecera del entregable. Cada cifra es trazable a su
artefacto en disco (columna "Reproducción (fuente)") y cada fila declara su población: los
denominadores difieren entre métricas y no deben mezclarse. Este documento compila cifras ya
medidas; no recalcula nada ni ejecuta el LLM. Alimenta la presentación (#106) y el reporte
final (#105).

| Métrica | Valor | Umbral mentor | Población / denominador | Reproducción (fuente) | Estado |
|---|---|---|---|---|:--:|
| Stage accuracy | 100% (216/216) | > 80% | 216 evaluables = 247 tardíos − 31 Indeterminados sin gap medible | `metrics_core.py` sobre `df_classified` (generado por `classifier_core.py`); `02_clasif_reglas_negocio/README.md` §5.1 | ✅ cumple |
| Reason agreement | 88.7% (180/203) | — (referencia, no umbral) | 203 clasificables (tardíos con `reason_group_manual` no nulo; nulos→"Unknown" fuera) | `metrics_core.py`; `02_clasif_reglas_negocio/README.md` §5.4; 8 de los 23 mismatches narrados en `03_llm_integration/mismatches_ai_vs_humano.md` | hallazgo |
| LLM Explanation Quality | 5/5 (20/20), few-shot C3 @ temp 0.9 (producción) | 4/5 (80%) | 20 POs (muestra estratificada 8/4/4/4, semilla 42) | `eval_quality.py`, backend oficial; `03_llm_integration/fixtures/eval_quality_20pos_C3_t09.md` (validación humana) | ✅ cumple |
| Severity Ranking | 100% (14/14) | > 95% | 14 POs con `HOT_PO_FLAG=1 & delay_days_calc>3`, sobre `po_output.csv` (severidad = LLM) | `eval_severity_ranking.py` (sin API); `po_output.csv` generado por `llm_integration.py --mode full`; `03_llm_integration/eval_severity_ranking.md`; divergencia vs regla F2 en nota abajo | ✅ cumple |
| Diferenciación intra-etapa (#151) | Hipótesis 26.3% fuera de firma (65/247) · Acción 20.6% fuera de firma (51/247) | N/A (hallazgo, no umbral) | 247 tardíos con tier-2 poblado (`llm_hipotesis`/`llm_accion_inmediata`, solo si la corrida usó `--action-call`) | `eval_differentiation.py` (sin API); `03_llm_integration/eval_differentiation.md` | hallazgo |
| Reparto de etapas | Vendor 139 (56.3%) · Carrier 40 (16.2%) · DC 37 (15.0%) · Indeterminado 31 (12.6%) | N/A (descriptivo) | 247 tardíos | `classifier_core.py` imprime el reparto; `02_clasif_reglas_negocio/README.md` "Reparto resultante" | descriptivo |

## Poblaciones (no mezclar denominadores)

Los seis denominadores responden a preguntas distintas y no son intercambiables:

- 216 evaluables (Stage accuracy) = los 247 tardíos menos los 31 Indeterminados, que no tienen
  gap dominante medible.
- 203 clasificables (Reason agreement) = tardíos con anotación humana `reason_group_manual` no
  nula; los nulos se mapean a "Unknown" y quedan fuera del denominador.
- 20 muestreados (LLM Explanation Quality) = muestra estratificada 8/4/4/4
  (Vendor/Carrier/Indeterminado/DC), semilla 42, reproducible.
- 14 hot-late (Severity Ranking) = POs con `HOT_PO_FLAG=1` y `delay_days_calc > 3`.
- 247 tardíos con tier-2 poblado (Diferenciación) = subconjunto de los 247 tardíos con
  `llm_hipotesis`/`llm_accion_inmediata` calculados (requiere corrida `--action-call`).
- 247 tardíos (Reparto) = población completa de POs tardíos.

El Indeterminado del reparto (31) se desglosa en 7 `sin_datos` (sin hora de tráiler) + 24
`sin_causa_dominante` (medibles pero sin exceso sobre ningún umbral). *(Nota de cierre ARD-03b,
2026-07-22: la auditoría ADR↔repo encontró un gate `decidible` que excluía a vendor sin
condición propia; el fix movió 8 POs de `sin_datos` a Vendor. Ver
[ADR-03b](decisiones/ARD-03b.md).)*

## Notas

- La severidad oficial del entregable es la del LLM (`severity ← llm_severidad`, ADR-10); la
  regla determinística de F2 se conserva como línea base de auditoría en el artefacto interno
  y da 14/14 por construcción (mide ranking, no coincidencia con el LLM).
- Reason agreement no tiene umbral del mentor: es la tesis del proyecto. El desacuerdo con la
  anotación humana (~20% incorrecta, dato del kickoff) es esperado y deseado; los 23 mismatches
  son la evidencia de que el cómputo temporal por timestamps supera a la anotación manual.
- LLM Explanation Quality: la cifra titular (5/5, 20/20) corresponde a la configuración de
  producción — few-shot C3 a temperatura 0.9, la que genera `po_output.csv` — con validación
  humana. Es el punto final de una progresión medida contra el mismo benchmark (semilla 42):
  zero-shot 3.25/5 (13/20) → few-shot C3 a temp 0.3 (benchmark de selección de la combinación
  ganadora) 4.75/5 (19/20) → el endurecimiento del prompt en #143 cierra el único fallo
  (PO 100182, etapa Indeterminado) a 5/5 (20/20), aún a temp 0.3 → ADR-13 re-valida esa cifra
  a la temperatura real de producción (0.9) sin regresión. El 4.75/5 no se descarta: es el
  hito que demostró que C3 supera la meta del mentor (4/5) y ganó frente a C1/C2; el 5/5 es la
  cifra que describe lo que el entregable produce hoy.
- Severity: divergencia LLM vs regla F2. Sobre los 247 tardíos, `severity` (LLM, la oficial)
  coincide con la severidad determinística de F2 en 213/247 (86.2%). Las 34 divergencias
  (13.8%) **siempre escalan** — nunca desescalan: 30 casos LOW→MEDIUM, 4 casos MEDIUM→HIGH.
  Lectura: el LLM ejerce juicio adicional sobre agravantes que la regla fija no captura
  (p. ej. combinaciones de hot PO / short ship / retraso borderline), y ese juicio nunca baja
  la alerta frente a la regla — es un hallazgo, no un defecto. Reproducción sin gastar API:
  comparar la columna `severity` de `po_output.csv` (o `llm_severidad` en
  `df_with_llm_full_openai.csv`) contra la `severity` de `df_classified.csv` (F2), por
  `PO_NBR`. Detalle narrativo en `documentation/validacion-y-qa.md`.
- Diferenciación intra-etapa (#151): hallazgo, no umbral del mentor. Sobre los 247 tardíos
  con tier-2 poblado, 65 (26.3%) reciben la hipótesis modal de su etapa aunque su firma de
  evidencia (short-ship, hot PO, coincidencia con REASON_DSC) difiera de esa modal, y 51
  (20.6%) lo mismo en la acción inmediata. Es evidencia ignorada, no error de cómputo: la
  etapa y la severidad siguen siendo correctas. Detalle en
  `03_llm_integration/eval_differentiation.md`.
