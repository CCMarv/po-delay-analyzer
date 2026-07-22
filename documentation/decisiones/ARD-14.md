# Endurecimiento del prompt de Fase 3 contra el overfitting al few-shot

* **Estatus:** 🟢 **Vigente** (cerrado 2026-07-19)
* **Contexto Técnico:** Fase 3 / Integración LLM — reglas del prompt para que razone por PO en vez de calcar el ejemplo o el motivo humano
* **Referencias:** Issue #143; #137 / PR #144 (experimento de temperatura que lo surfaceó); #94 (benchmark de calidad, 20 POs); ADR-12 (diseño del prompt few-shot, que nombró el riesgo); ADR-07 (taxonomía de Indeterminado); ADR-03b / ADR-06b (medición de Vendor, no se reabre); ADR-13 (temperatura); `03_llm_integration/llm_integration.py` (`build_prompt`, `_format_example`)

## Contexto y Problema

ADR-12 adoptó un few-shot que enseña el razonamiento y registró como riesgo la "copia de plantilla", a mitigar con ejemplos heterogéneos. El experimento de temperatura de #137 confirmó que el riesgo se materializó: con la combinación C3 (ejemplos Vendor+Carrier+DC, los tres casos de discrepancia reason↔etapa) el modelo escribía mecánicamente "la evidencia no coincide con el REASON_DSC" aun cuando sí coincidía (PO 100154) y repetía una acción Carrier casi idéntica entre POs. Recalibrar la temperatura no lo corrige; la causa es el diseño del prompt.

Al corregir lo anterior y revisar la salida completa de Fase 2 (39 indeterminados) apareció una falla más sutil e independiente: para un PO Indeterminado cuyo REASON_DSC nombra una etapa ("Vendor delayed shipment"), el modelo adopta el motivo como etapa e ignora la clasificación "Indeterminado". El patrón quedó aislado: los tres indeterminados del sample con REASON_DSC "Not applicable" se explicaron como indeterminados; solo falló el único con un motivo que nombra etapa. En paralelo, 8 de los 15 `sin_datos` conservan un `excess_vendor_hrs` medible (hasta 92.5 h) que el clasificador no usó para atribuir —`decidible` exige carrier o DC medibles, "no vendor por descarte" en `classifier_core.py`—, de modo que mostrar ese número en el prompt invitaba a sobre-escribir el veredicto de Fase 2.

## Opciones Consideradas (presentación del exceso por etapa en Indeterminado)

### Opción A: Mostrar el exceso por etapa siempre

* **Pros:** Una sola forma del bloque de métricas; el ejemplo few-shot Vendor cita ese número y el PO real lo recibe.
* **Contras:** En los 8 `sin_datos` el exceso de vendor contradice el veredicto; la línea de sub-categoría compite contra él y pierde (100182 lo confirma).

### Opción B: Mostrar el exceso por etapa solo cuando hay etapa atribuida (elegida)

* **Pros:** Alinea el prompt con lo que Fase 2 concluyó; retira la señal engañosa de raíz; consistente con los ejemplos few-shot, que ya no muestran exceso para indeterminado; los Vendor/Carrier/DC reales conservan su exceso.
* **Contras:** Una rama condicional más en `build_prompt`.

### Opción C: Mostrar el exceso etiquetado como "no atribuible"

* **Pros:** Mantiene el número visible por honestidad.
* **Contras:** Verboso y el número tentador sigue presente.

## Decisión

1. **Bloque CÓMO RAZONAR.** El prompt enseña la combinatoria de dominio que los ejemplos no muestran —las cuatro etapas y las tres relaciones con el REASON_DSC (coincide / discrepa / vacío)—, con líneas de acción ilustrativas marcadas como rango, no como plantilla. Las descripciones de campo del JSON remiten a esa guía.
2. **Autoridad de la etapa.** La etapa que el modelo reporta debe ser exactamente la `stage_primary` de la clasificación, fuente de verdad por señal temporal. El REASON_DSC se contrasta pero nunca sustituye la etapa ni se promueve a etapa aunque nombre una. Para Indeterminado, la explicación lo declara indeterminado y explica por qué (`sin_datos` / `sin_causa_dominante`).
3. **El exceso por etapa es señal de atribución (Opción B).** Las líneas de exceso se muestran solo para etapas atribuidas (`stage_primary` ≠ Indeterminado); para Indeterminado se muestran los tiempos crudos de yard/dock más la sub-categoría. No se reabre la medición de Vendor (ADR-03b / ADR-06b vigentes): es una decisión de presentación de Fase 3.
4. **Canonicalización del casing.** Fase 3 consume `stage_primary == "Indeterminado"` (titlecase, el valor que emite el clasificador por ADR-07) como única convención; se retira la variante en mayúsculas que convivía en el código del prompt, el pool y los tests, fuente latente del bug por la que la línea de sub-categoría nunca se disparaba para POs reales.
5. **Reescritura de los ejemplos del pool.** El ejemplo Carrier (y los de Vendor y DC) no abren con la fórmula de negación; modelan la discrepancia razonada y acciones que citan cifras concretas.

## Consecuencias

* **Positivas:** El prompt razona por PO. El refuerzo vive en `build_prompt`, así que cubre el zero-shot de producción y el benchmark por igual. La corrección de la presentación del exceso es sistémica para los 8 `sin_datos` con exceso de vendor, no solo el caso del benchmark.
* **Negativas:** Más texto en el prompt, más tokens por llamada. La robustez se valida contra el mismo benchmark, no queda garantizada por construcción. El casing canonicalizado obliga a que todo código nuevo de Fase 3 use "Indeterminado" en titlecase.

## Relación con otras decisiones

Forward de **ADR-12**: ejecuta y refuerza su mitigación nombrada del riesgo de copia de plantilla, sin superarla (el few-shot sigue vigente). Consume **ADR-07** (taxonomía de Indeterminado) y se enlaza con **ADR-13** (#143 desbloqueó el cierre de #137, que fijó 0.9 como ancla de temperatura en su ronda 2). No supera ni reabre **ADR-03b / ADR-06b** (medición de Vendor).

**Nota (2026-07-22):** los 8 `sin_datos` con `excess_vendor_hrs` medible que este ADR documentó desde el ángulo de presentación (punto 3 de Decisión) tenían, en realidad, una causa raíz en el clasificador: el gate `decidible` de `classifier_core.py` los excluía de la atribución a Vendor. La nota de cierre de [ADR-03b](ARD-03b.md) (2026-07-22) corrige ese gate; los 8 POs pasan a Vendor. Este ADR no se reabre — la Opción B (presentación del exceso solo para etapas atribuidas) sigue vigente y correcta para Vendor/Carrier/DC reales.
