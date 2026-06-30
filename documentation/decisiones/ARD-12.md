# Diseño del prompt de Fase 3: few-shot que enseña el razonamiento, con fuente única

* **Estatus:** 🔵 **BORRADOR** (lo cierra el equipo)
* **Contexto Técnico:** Fase 3 / Integración LLM — diseño del prompt que genera la explicación y la acción
* **Referencias:** Issue #99; #94 (benchmark de calidad, 20 POs); #91/#67 (prompt base); ADR-10 (severidad y umbral); `03_llm_integration/llm_integration.py` (`build_prompt`, `_format_example`, `_examples_block`); `03_llm_integration/eval_quality.py`

## Contexto y Problema

La explicación del LLM es uno de los entregables que el mentor evalúa (rúbrica, *LLM Integration & Prompt Engineering*). El benchmark de calidad de #94 sobre 20 POs estratificados midió el prompt zero-shot alineado a #91 con tres checks binarios por PO: (a) etapa correcta, (b) cuantifica el delay, (c) acción viable. El resultado dejó un diagnóstico nítido:

* (a) etapa correcta: 19/20.
* (b) cuantifica el delay: 20/20.
* (c) acción viable: 13/20.
* Veredicto (PASA si a&b&c): 13/20 → equivalente 3.25/5, por debajo de la meta del mentor (4/5).

El cuello de botella no es clasificar la etapa ni cuantificar el retraso —ambos cumplen holgado— sino la **calidad de la acción recomendada**. Los siete fallos de (c) son acciones genéricas ("revisar procesos") o incoherentes (piden investigar lo que el `REASON_DSC` ya explica). El contraste canónico es PO 100278 frente a PO 100318: el mismo verbo "investigar" es coherente solo cuando el motivo está vacío (100318) y redundante cuando el motivo ya da la causa (100278).

En paralelo convivían dos artefactos de prompt: `build_prompt()` (operativo, el que corre) y `prompt_template.txt` (un borrador de system prompt que el código no cargaba). Una fuente de verdad dual.

## Opciones Consideradas

### Opción A: Mantener el prompt zero-shot

* **Pros:** Sin cambios; ya cumple (a) y (b).
* **Contras:** No alcanza la meta de (c). El déficit de calidad de la acción es justo lo que evalúa la rúbrica.

### Opción B: Adoptar `prompt_template.txt` como system prompt

* **Pros:** Es un borrador más elaborado (rol senior, contexto de negocio, criterios de calidad).
* **Contras:** Arrastra decisiones ya superadas: una taxonomía de seis etapas (Vendor/Carrier/Scheduling/Yard/Dock/Receiving) que no son los cuatro estados de F2; instrucciones que invitan a examinar timestamps y calcular, en contra del lineamiento de #91 (interpretar, no calcular); y un umbral de severidad `> 7 días` que contradice ADR-10 (`> 3 días`). Adoptarlo revertiría decisiones vigentes.

### Opción C: Few-shot que enseña el razonamiento, con `build_prompt` como fuente única

* **Pros:** Ataca el déficit real (c) con ejemplos que enseñan el mapeo dato→razonamiento→acción: que la etapa sale de la señal temporal medida (no del motivo humano) y que la acción ataca la causa real sin pedir investigar lo que el motivo ya explica. Los ejemplos salen de mismatches reales de F2, disjuntos del set de evaluación para no contaminar la métrica. El número de ejemplos se decide empíricamente contra el benchmark (semilla 42), no por intuición. Fija una sola fuente del prompt.
* **Contras:** Riesgo de copia de plantilla (que el modelo calque la redacción del ejemplo en vez de razonar); más tokens por llamada; obliga a curar los ejemplos con criterio.

## Decisión

Se elige la **Opción C**.

1. El prompt adopta **few-shot que enseña el razonamiento**, no la etiqueta. Los ejemplos se inyectan mediante un parámetro opcional `examples` en `build_prompt`; sin él, el comportamiento zero-shot histórico no cambia.
2. Los ejemplos provienen de **mismatches reales de F2** (la clasificación computada discrepa del `REASON_DSC` humano), verificados como **disjuntos del benchmark de 20 POs** antes de cualquier corrida, para que la métrica no se contamine.
3. Cada ejemplo es **espejo de la forma** del caso real (mismos bloques del prompt) pero **curado en contenido**: solo los campos que enseñan el razonamiento de la acción (la señal de exceso de la etapa elegida, el delay citado, el responsable a nombrar, el motivo en discusión y los agravantes activos). No incluye el timeline de fechas —mostrarlo reenseñaría a recalcular, contra #91— ni campos de ruido. El JSON ideal de cada ejemplo lleva las **cinco claves completas**, para reforzar que las cinco deben existir siempre.
4. `build_prompt()` queda como **fuente única** del prompt y se **elimina** `prompt_template.txt`.
5. La combinación ganadora (cuántos ejemplos) se elige por su tasa de (c) contra el benchmark, sin degradar (a) ni (b).

## Consecuencias

* **Positivas:** El prompt ataca el déficit medido de la acción con una intervención dirigida y evaluable contra el mismo benchmark. La fuente del prompt deja de ser dual, eliminando el riesgo de que un borrador desactualizado se reutilice y revierta #91 o ADR-10. La curación de ejemplos desde mismatches reales conecta el diseño del prompt con la tesis del proyecto (el cómputo temporal supera a la anotación humana).
* **Negativas:** Riesgo de copia de plantilla, que se mitiga con ejemplos de etapas distintas y acciones heterogéneas y con la validación humana de (c) sobre la corrida ganadora. La inclusión de `is_rescheduled` en un ejemplo se decide caso por caso y siempre como contexto neutro (la acción ideal no debe culpar al vendor por la reprogramación, sesgo que ADR-05/#67 corrigieron); cada ejemplo nuevo se audita con ese criterio.

## Relación con otras decisiones

No supera ninguna decisión vigente, por lo que no se encadena como 📘 Superado. **Referencia a ADR-10**: la eliminación de `prompt_template.txt` materializa el umbral `> 3 días` ya vigente (retira el `> 7 días` del borrador), no lo redefine. **Forward a ADR-14**: la mitigación del "riesgo de copia de plantilla" nombrada aquí se ejecuta y refuerza en ADR-14 (#143), que añade el bloque CÓMO RAZONAR, la autoridad de la etapa sobre el REASON_DSC y la presentación del exceso solo para etapas atribuidas.
