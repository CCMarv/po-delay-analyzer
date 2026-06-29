# Temperatura de inferencia del LLM: evaluación 0.3–0.9 y decisión de ancla

* **Estatus:** 🔵 **BORRADOR** (lo cierra el equipo)
* **Contexto Técnico:** Fase 3 / Integración LLM — parámetro de temperatura en `llm_config.json`
* **Referencias:** Issue #137; #94 (benchmark de calidad, 20 POs); #143 (corregir overfitting del few-shot); ADR-12 (diseño del prompt few-shot); `03_llm_integration/llm_config.json`; `03_llm_integration/fixtures/eval_quality_20pos_C3*.md`

## Contexto y Problema

La temperatura de inferencia controla la aleatoriedad del muestreo de tokens: valores bajos (≈ 0.0–0.3) favorecen la respuesta más probable (mayor coherencia y reproducibilidad); valores altos (≈ 0.7–1.0) aumentan la diversidad pero pueden degradar la adherencia al formato JSON requerido.

El prompt de F3 requiere salida JSON estructurada con cinco claves fijas (`etapa`, `delay_dias`, `causa_raiz`, `accion_recomendada`, `severidad`). `llm_config.json` fijó 0.3 como ancla provisional al configurar la capa de inferencia (#120–#123). El issue #137 diseñó un experimento para validar si una temperatura mayor aportaba diversidad útil en las acciones recomendadas, donde se concentraba el déficit de calidad identificado en ADR-12.

## Experimento

Se corrió la combinación C3 (3 ejemplos few-shot: Vendor + Carrier + DC) contra los mismos 20 POs del benchmark (#94, semilla 42) con cuatro temperaturas: 0.3 (ancla ya existente), 0.5, 0.7 y 0.9. Cada corrida usó el backend `openai` (`gpt-4o-mini`). 60 llamadas adicionales (3 temperaturas × 20 POs).

## Opciones Evaluadas

| Temperatura | (a & b) automático | Observación |
|---|---|---|
| 0.3 (ancla) | 19/20 | Acciones homogéneas; frase refleja en REASON_DSC |
| 0.5 | 19/20 | Sin diferencia observable frente al ancla |
| 0.7 | 19/20 | Sin diferencia observable frente al ancla |
| 0.9 | 19/20 | Sin diferencia observable frente al ancla |

## Hallazgo

La varianza entre temperaturas es mínima porque el few-shot ancla la plantilla de la respuesta. Se identificaron dos síntomas:

1. **Frase refleja en REASON_DSC:** el modelo escribe "la evidencia no coincide con el REASON_DSC del DC ('X')" de forma mecánica, incluso cuando X coincide con la etapa medida (ej. PO 100154: `REASON_DSC = "Carrier delivery delay"`, `stage_primary = Carrier`). La estructura proviene del ejemplo few-shot, no de un razonamiento sobre el caso concreto.

2. **Acción homogénea en Carrier:** la recomendación "contactar al transportista X para que explique el exceso de tránsito y comprometa una mejora" es casi idéntica en todos los POs Carrier, independientemente de la temperatura. El ejemplo Carrier del pool fijó la plantilla; la temperatura mueve tokens marginales dentro de esa plantilla, no su estructura.

Conclusión: el problema de diversidad y de frase refleja es de diseño del few-shot (o del prompt base), no de aleatoriedad del muestreo. Recalibrar temperatura antes de corregir el overfitting no aporta mejora medible.

## Decisión

Se mantiene **0.3** como temperatura de inferencia en `llm_config.json`. No se recalibra hasta que el overfitting del few-shot quede corregido (#143). Una vez aplicada esa corrección, el experimento de temperatura puede repetirse sobre un prompt que efectivamente permita varianza en la acción.

## Consecuencias

* **Positivas:** `llm_config.json` permanece sin cambio; la corrida completa (#97) usa el ancla de referencia conservadora, que maximiza reproducibilidad y adherencia al formato JSON.
* **Negativas:** La recalibración de temperatura queda diferida; el impacto real del parámetro sobre la diversidad de acciones no se puede medir hasta resolver #143.
* **Trabajo derivado:** Issue #143 (corregir overfitting del few-shot: frase refleja de REASON_DSC y acción homogénea en Carrier). El cierre de #137 queda bloqueado por #143.
