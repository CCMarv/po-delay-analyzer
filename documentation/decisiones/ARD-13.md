# Temperatura de inferencia del LLM: evaluación 0.3–0.9 y decisión de ancla

* **Estatus:** 🟢 **Vigente** (cerrado 2026-07-19)
* **Contexto Técnico:** Fase 3 / Integración LLM — parámetro de temperatura en `llm_config.json`
* **Referencias:** Issue #137; #94 (benchmark de calidad, 20 POs); #143 / ADR-14 (endurecimiento del prompt few-shot); ADR-12 (diseño del prompt few-shot); `03_llm_integration/llm_config.json`; `03_llm_integration/eval_quality.py` (andamio `--temperature`); `03_llm_integration/eval_diversity.py` (métrica de diversidad); `03_llm_integration/fixtures/eval_quality_20pos_C3*.md`

## Contexto y Problema

La temperatura de inferencia controla la aleatoriedad del muestreo de tokens: valores bajos (≈ 0.0–0.3) favorecen la respuesta más probable (mayor coherencia y reproducibilidad); valores altos (≈ 0.7–1.0) aumentan la diversidad pero pueden degradar la adherencia al formato JSON requerido.

El prompt de F3 requiere salida JSON estructurada con cinco claves fijas (`etapa`, `delay_dias`, `causa_raiz`, `accion_recomendada`, `severidad`). `llm_config.json` fijó 0.3 como ancla provisional al configurar la capa de inferencia (#120–#123). El issue #137 diseñó un experimento para validar si una temperatura mayor aportaba diversidad útil en las acciones recomendadas, donde se concentraba el déficit de calidad identificado en ADR-12.

## Experimento — dos rondas

La temperatura se barrió sobre la combinación C3 (3 ejemplos few-shot: Vendor + Carrier + DC) contra los mismos 20 POs del benchmark (#94, semilla 42), backend `openai` (`gpt-4o-mini`), a 0.3 / 0.5 / 0.7 / 0.9. Cada ronda añadió 60 llamadas (3 temperaturas × 20 POs; el punto 0.3 se reutiliza como ancla). Lo que cambia entre rondas es el prompt.

### Ronda 1 — prompt sin endurecer (pre-#143)

Las cuatro temperaturas dieron 19/20 en (a & b) sin diferencia observable entre sí. La varianza fue mínima porque el few-shot anclaba la plantilla de la respuesta; se identificaron dos síntomas: la frase refleja "la evidencia no coincide con el REASON_DSC" escrita de forma mecánica (aun cuando coincidía, p. ej. PO 100154) y una acción Carrier casi idéntica entre POs. La conclusión fue que el problema de diversidad era de diseño del prompt, no de aleatoriedad del muestreo: recalibrar la temperatura antes de corregir el overfitting no aportaba mejora medible. La decisión provisional fue mantener 0.3 y diferir la recalibración hasta resolver #143.

### Ronda 2 — prompt endurecido (post-#143)

El barrido se repitió sobre el prompt que ADR-14 endureció (bloque CÓMO RAZONAR, autoridad de la etapa sobre el REASON_DSC, exceso solo para etapas atribuidas). Se añadió una métrica de diversidad para medir lo que los checks (a)/(b)/(c) no capturan.

#### Métrica de diversidad

Se documenta dentro de este ADR, sin registro propio, porque sirve esta decisión y no orienta el producto por sí sola. La implementa `eval_diversity.py`, que opera offline (no gasta API): lee los fixtures `.md` ya generados y mide `diversidad = 1 − similitud_media_por_pares`, donde la similitud de dos acciones es el índice de Jaccard sobre sus conjuntos de tokens. Se reporta para el conjunto completo de acciones y para el subconjunto Vendor, donde se concentra la homogeneidad. Es un proxy léxico —dos acciones reescritas pero equivalentes cuentan como diversas—, por lo que se acompaña de la lectura cualitativa de las acciones lado a lado; no es una medida semántica.

#### Resultados

| Temperatura | div(set) | div(Vendor) | (a & b) auto | Observación |
|---|---|---|---|---|
| 0.3 (ancla) | 0.691 | 0.312 | 20/20 | (c) validado a mano (#143); baseline reproducible |
| 0.5 | 0.706 | 0.375 | 20/20 | algo más variada, sin regresión ni pérdida de coherencia |
| 0.7 | 0.708 | 0.458 | 19/20 | regresa (a) en 100182 (copia la etapa del reason code) |
| 0.9 | 0.765 | 0.567 | 20/20 | máxima diversidad; reescrituras causales más laxas |

## Hallazgos (ronda 2)

1. El prompt endurecido destrabó la sensibilidad a la temperatura que la ronda 1 no veía: la diversidad de las acciones Vendor sube de forma monótona (0.312 → 0.567). El #143 era la condición que faltaba para que la temperatura tuviera efecto medible.
2. La ganancia es modesta y vive en la cola causal, no en el esqueleto. El molde "Solicitar al proveedor un plan de recuperación con fecha firme, dado que el retraso se origina en su…" persiste en las ocho acciones Vendor a todas las temperaturas; la temperatura varía la causa citada, no la estructura. La homogeneidad residual es estructural (diseño del prompt/few-shot), no de muestreo.
3. Subir la temperatura cambia diversidad por fiabilidad. A 0.7 el PO 100182 (Indeterminado con REASON_DSC "Vendor delayed shipment") falló (a): el modelo copió la etapa del reason code —el modo de fallo que ADR-14 corrige— y arrastró una acción incoherente. A 0.9 ese caso vuelve a pasar, pero la verificación automática es ruidosa a temperatura alta y aparecen reescrituras causales más laxas ("exceso de gestión", "envío tardío") menos precisas que el "exceso de tránsito" medido.
4. El caso canónico que motivó #137 (PO 100278, Carrier / "Weather/road conditions") es coherente a todas las temperaturas (reclamo formal a UPS Freight por las 29.7 h de exceso, plan correctivo con fecha): lo resolvió #143, no la temperatura.

## Decisión

Se fija **0.9** como temperatura de inferencia en `llm_config.json`, priorizando la diversidad de las acciones —objetivo de #137— ahora que #143 la hizo sensible a la temperatura. 0.9 alcanza la mayor diversidad del barrido (div Vendor 0.567) manteniendo (a & b) automático en 20/20 sobre el benchmark.

La decisión acepta de forma explícita estos costos:

* Menor reproducibilidad que 0.3 en la corrida de producción (#97, 247 POs).
* Riesgo, evidenciado a 0.7 sobre el PO 100182, de que algún Indeterminado cuyo REASON_DSC nombre una etapa reincida en el fallo de (a) que ADR-14 corrige; a 0.9 el benchmark no lo mostró, pero el muestreo a temperatura alta no lo garantiza.
* Reescrituras causales más laxas en algunas acciones Vendor ("exceso de gestión", "envío tardío"), a vigilar en la validación de (c).
* (c) sobre el fixture 0.9 no se validó a mano de forma completa al fijar el ancla (solo 0.3 lo estaba). **Cierre (2026-07-19):** la validación manual se completó (#148, commit `51afebb`, `eval_quality_20pos_C3_t09.md`) y es la misma medición que fija la cifra titular de calidad del entregable (5/5, 20/20) en `documentation/metricas-proyecto.md`.

## Consecuencias

* Positivas: las acciones recomendadas ganan variación léxica real frente al ancla conservadora; la decisión se apoya en una métrica reproducible (`eval_diversity.py`) además de la lectura cualitativa.
* Negativas: menor reproducibilidad y adherencia al formato; el ancla nueva traslada al lector la verificación de (c) sobre el fixture 0.9.
* Trabajo derivado: la homogeneidad estructural del esqueleto Vendor no la resuelve la temperatura; queda para el diseño del prompt/few-shot o el sondeo de hiperparámetros (`top_p`, `frequency_penalty`, `presence_penalty`) que #137 dejó anotado fuera de alcance.

## Relación con otras decisiones

Supera la decisión provisional de la ronda 1 (mantener 0.3 hasta corregir #143), ya cumplida. Consume **ADR-14** (#143 destrabó la sensibilidad a la temperatura medida aquí) y **ADR-12** (diseño del prompt few-shot). No reabre **ADR-03b / ADR-06b** (medición de Vendor).
