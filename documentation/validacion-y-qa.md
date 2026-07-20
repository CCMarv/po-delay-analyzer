# Validación y QA — el método de cierre

Este documento explica cómo el proyecto garantiza la correctitud de sus resultados y cómo un
revisor los reproduce en su máquina. No es un inventario de tests: es el método de validación
de extremo a extremo, descrito por las capas que atraviesa un dato desde que se limpia hasta
que se clasifica y se mide.

El encuadre toma dos referencias complementarias. De The Turing Way se adopta el criterio de
reproducibilidad: mismo dato más mismo código deben producir el mismo resultado, lo que exige
fijar el entorno, versionar y automatizar la verificación. De la práctica de test plan se
adopta la estructura por niveles: qué se prueba, a qué nivel (unitario, contrato, métrica,
gate) y cuál es el criterio de éxito. Turing Way aporta el porqué (reproducibilidad como
objetivo); el test plan aporta el cómo se organiza (capas y criterios). No compiten.

La validación se organiza en cuatro capas. Cada una se describe con las mismas tres
preguntas: qué garantiza, qué rompe si falla, y cómo se reproduce.

## Capa A — Tests unitarios por fase

Qué garantiza. Cada función del pipeline hace lo que dice, aislada de las demás. La suite se
reparte por fase: `tests/test_pipeline_core.py` cubre la limpieza, las flags de calidad y los
deltas de F1; `tests/test_classifier_core.py` cubre la etapa primaria, la severidad y las
subclases de F2; `tests/test_metrics_core.py` cubre stage accuracy, reason agreement y los
análisis de sensibilidad; `tests/test_llm_integration.py` cubre la construcción del prompt y
el parseo del JSON de respuesta de F3 sin tocar la red. Los fixtures son sintéticos, con
valores conocidos, de modo que el resultado esperado es determinístico.

Qué rompe si falla. Una regresión en una función deja el CI en rojo antes del merge. Sin esta
capa, un cambio podría alterar el reparto de etapas o una métrica cabecera sin que nadie lo
advierta, porque el número seguiría "saliendo".

Cómo se reproduce.

```
pytest                                  # suite completa
pytest tests/test_classifier_core.py    # una fase en aislamiento
```

## Capa B — Contrato de handoff entre fases

Qué garantiza. La frontera entre dos fases es un contrato, no un supuesto. `tests/test_handoff_contract.py`
verifica la regla de oro: el CSV que produce una fase es funcionalmente idéntico al DataFrame
que esa fase deja en memoria, de modo que la fase siguiente lo relee y reconstruye el mismo
estado que tendría si la cadena corriera de una sola vez. Cubre las dos fronteras, F1→F2 y
F2→F3. La identidad es funcional, no de tipado: un CSV escribe las fechas como texto, así que
el contrato se cumple cuando el valor es el mismo, no cuando el dtype coincide. El test
reparsea las columnas de fecha y unifica las formas de faltante (NaN, cadena vacía) a un
centinela común antes de comparar el frame completo.

Qué rompe si falla. Correr las fases por separado daría un resultado distinto a correrlas
juntas, y F3 leería un estado que F2 nunca produjo. El contrato es lo que permite ejecutar el
pipeline por tramos —o retomar desde un CSV intermedio— con la garantía de que el resultado no
cambia.

Edge case cubierto: la etiqueta `"Ninguno"` sobrevive el round-trip. La columna `stage_multi`
usa el centinela `"Ninguno"` para los POs sin etapa secundaria, y no el literal `"None"` ni la
cadena vacía. La razón es de serialización: `"None"` y `""` se leen desde el CSV como NaN, con
lo que F3 perdería la señal de "no hay segunda etapa" y la confundiría con un dato ausente.
`"Ninguno"` es un valor real y sobrevive intacto (ver `classifier_core.py`, construcción de
`stage_multi`). El contrato verifica que el frame completo —con esa etiqueta incluida—
reconstruye el estado en memoria.

Cómo se reproduce.

```
pytest tests/test_handoff_contract.py
```

## Capa C — Métricas de clasificación contra umbrales

Qué garantiza. Las cifras cabecera del entregable se calculan desde los timestamps del
lifecycle, no desde la anotación humana, y se contrastan contra los umbrales de aceptación del
mentor. El módulo `02_clasif_reglas_negocio/metrics_core.py` las produce: `stage_accuracy`
(#46), `reason_agreement` (#47) y las funciones de severidad y sensibilidad.

| Métrica | Valor | Umbral mentor | Denominador |
|---|---|:--:|---|
| Stage accuracy | 100% (208/208) | > 80% | 208 evaluables (247 tardíos − 39 Indeterminados sin gap medible) |
| Reason agreement | 88.8% (174/196) | referencia, no umbral | 196 clasificables (tardíos con anotación humana no nula) |
| Severity ranking | 100% (14/14) | > 95% | 14 hot-late (`HOT_PO_FLAG=1` y `delay_days_calc > 3`), sobre `po_output.csv` (severidad = LLM) |

Stage accuracy compara la etapa por exceso sobre umbral (`stage_primary`) contra el gap
dominante (el tramo de mayor duración bruta): mide si la regla de clasificación coincide con
dónde el PO realmente pasó más tiempo. Reason agreement compara el cómputo temporal contra la
anotación humana `REASON_DSC`, y aquí el <100% es esperado y deseado: la anotación humana es
aproximadamente 20% incorrecta, así que los 22 mismatches son la evidencia de la tesis del
proyecto —el cómputo por timestamps corrige al reason code heredado—, no un fallo del método.
El severity ranking se mide sobre la severidad oficial del entregable, que **es la del LLM**
(`severity ← llm_severidad`, ADR-10), no la regla determinística de F2. Por eso la medición es
empírica —valida si el LLM respetó `hot & delay>3 ⇒ HIGH`, no lo da por sentado— y puede en
principio dar menos de 100%; que dé 14/14 es un resultado observado, no una garantía "por
construcción". La regla de F2 se conserva como línea base de auditoría (esa sí da 14/14 por
construcción, por diseño) y es la referencia contra la que se contrasta al LLM (ver
"Divergencia de severidad LLM vs regla" más abajo).

Qué rompe si falla. Si una de estas cifras se mueve fuera de umbral, el clasificador se ha
alejado de los timestamps (la fuente de verdad) sin aviso, y se pierde la trazabilidad de las
cifras que sostienen el reporte.

Cómo se reproduce. Correr `classifier_core.py` para generar `df_classified`, y sobre él las
funciones de `metrics_core.py`. Las cifras y su fuente exacta están compiladas en
`documentation/metricas-proyecto.md` (tabla única, columna "Reproducción (fuente)"); este
documento las cita, no las recalcula.

## Capa D — CI como gate de merge

Qué garantiza. `.github/workflows/ci.yml` corre en cada pull request y en cada push a main un
smoke de import de los tres módulos (`pipeline_core`, `classifier_core`, `llm_integration`)
seguido de `pytest`. La convención del equipo permite mergear sin esperar revisión humana
bloqueante, así que el gate de merge es la palomita verde: reemplaza al "en mi compu sí jala".

Qué rompe si falla. El check queda en rojo si un módulo no importa —por una dependencia
faltante, por ejemplo— o si cualquier test falla, y el PR no se debe mergear. El CI no incluye
gate de lint, formato o type-check; esa ausencia es una decisión consciente para el alcance del
proyecto, documentada en el propio workflow, no un olvido.

Cómo se reproduce. Localmente, `pytest` reproduce el mismo criterio que el gate. En remoto,
cada PR dispara el workflow; el entorno fija Python 3.13 e instala desde `requirements.txt`.

## Cifras ancla y cómo regenerarlas

Un revisor reproduce las cifras vivas en entorno limpio (un `venv` desde `requirements.txt`,
con el dataset en `data/raw/`) ejecutando:

```
python 01_data_pipeline_and_eda/pipeline_core.py      # F1 → df_clean
python 02_clasif_reglas_negocio/classifier_core.py    # F2 → reparto + df_classified
pytest                                                 # 251 passed
```

Las cifras ancla que debe obtener:

- Suite de tests: 251 pasando. La suite creció con cada fase (de 57 a 99 a 114 a 244 a 251);
  el valor vigente es 251.
- Stage accuracy 100% (208/208), reason agreement 88.8% (174/196), severity ranking 100%
  (14/14, severidad = LLM).
- Reparto de etapas sobre los 247 tardíos: Vendor 131 (53.0%), Carrier 40 (16.2%), DC 37
  (15.0%), Indeterminado 39 (15.8%).
- LLM Explanation Quality 5/5 (20/20), few-shot C3 a temperatura 0.9 (configuración de
  producción; requiere API — ver detalle y progresión en `documentation/metricas-proyecto.md`).
- Divergencia de severidad LLM vs regla F2: 213/247 (86.2%) coinciden; 34/247 (13.8%)
  divergen, siempre escalando (ver sección arriba).

Todas son trazables a `documentation/metricas-proyecto.md`, que documenta la población y la
fuente de cada una. Los denominadores difieren entre métricas y no son intercambiables.

## Edge cases y failure modes que la validación cubre

La validación no solo confirma el camino feliz; cubre los casos límite donde el dato es parcial
o anómalo, y el diseño prefiere declarar el límite antes que adivinar.

27 POs sin hora de tráiler. Carecen de `TRAILER_ARRIVE_DT`, con lo que los tramos de carrier y
DC no son medibles. La regla que asigna Vendor por STA push (`APPROVED_DT > STA_DT`) rescata 12
de ellos, porque mide la aprobación tardía sin necesitar el tráiler; los 15 restantes quedan
como `sin_datos` dentro de Indeterminado. La flag de calidad que los marca está cubierta por
`tests/test_pipeline_core.py`, y el desglose está en `documentation/metricas-proyecto.md`.

12 inversiones temporales. La flag `_ts_issue` marca 12 POs donde `CHECKOUT_DT < CHECKIN_DT`,
una anomalía de secuencia registrada en `documentation/data_dictionary.md`. El pipeline trunca
el tramo afectado a cero (`clip ≥ 0`) en lugar de propagar una duración negativa. De esos 12,
11 son el subconjunto con discrepancia de dock mayor a una hora frente a la columna
precalculada. La cobertura está en `tests/test_pipeline_core.py`.

Round-trip CSV que preserva `"Ninguno"`. Descrito en la Capa B: la elección del centinela
`"Ninguno"` sobre `"None"` o la cadena vacía es lo que evita que la señal de "sin etapa
secundaria" se pierda como NaN al serializar. Verificado por `tests/test_handoff_contract.py`.

Dos poblaciones de 39 que no deben confundirse. La cifra 39 aparece dos veces sobre conjuntos
distintos, y mezclarlas llevaría a una lectura errónea:

- En F1, 39 POs no confiables = 12 inversiones temporales + 27 sin hora de tráiler, con
  solapamiento cero entre ambos grupos, sobre los 400 POs del dataset. Las métricas baseline se
  reportan sobre los 361 confiables restantes.
- En F2, 39 POs Indeterminado = 15 `sin_datos` + 24 `sin_causa_dominante`, sobre los 247 POs
  tardíos. Es la población que se resta a los 247 para obtener los 208 evaluables del stage
  accuracy.

Son dos conjuntos diferentes que coinciden en el número; el documento los mantiene separados a
propósito.

## Divergencia de severidad LLM vs regla

La severidad oficial del entregable es la del LLM (ADR-10); la regla determinística de F2 se
conserva en el artefacto interno como línea base de auditoría, no como fuente de verdad. Las
dos no siempre coinciden, y la discrepancia es un hallazgo documentado, no un error de una de
las dos fuentes.

Sobre los 247 POs tardíos, `severity` (LLM) coincide con la severidad de F2 en 213/247
(86.2%). Las 34 divergencias (13.8%) **siempre escalan** — ninguna desescala: 30 casos
LOW→MEDIUM y 4 casos MEDIUM→HIGH. Lectura: el LLM aplica juicio sobre combinaciones de
agravantes (hot PO, short ship, retraso cerca del umbral) que la regla fija no distingue, y ese
juicio adicional nunca relaja la alerta frente a la regla — siempre la sostiene o la sube.

Reproducción sin gastar API (ambas columnas ya viven en artefactos generados):

```
# severity (LLM) vs severity (regla F2), por PO_NBR
# LLM:   data/processed/po_output.csv → columna `severity`
#        (o data/processed/df_with_llm_full_openai.csv → columna `llm_severidad`)
# Regla: data/processed/df_classified.csv → columna `severity`
```

## Relación con el resto de la documentación

Este documento describe el método; las cifras vivas y sus fuentes están en
`documentation/metricas-proyecto.md`, y la lectura de negocio de los mismatches en
`documentation/hallazgos-ai-vs-humano.md`. El README raíz enlazará este documento como la
sección de validación del cierre (pendiente de cablear en #84).
