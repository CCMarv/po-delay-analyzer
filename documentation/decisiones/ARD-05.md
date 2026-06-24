# Reschedule y short-ship: contexto, no etapa

* **Estatus:** 🟢 Vigente
* **Contexto Técnico:** Fase 2 / Refinamiento del Modelo de Atribución
* **Referencias:** Issue #42, Discussion #54

## Contexto y Problema
Durante el análisis operativo, eventos como la reprogramación de fechas (*reschedule*) y los envíos incompletos (*short-ship*) fueron identificados como causantes críticos de fricción. El problema de diseño consistía en si estos eventos debían tratarse como "etapas de retraso" independientes dentro del clasificador dominante o si pertenecían a otra dimensión del modelo de datos, dado que su naturaleza difiere de tramos físicos como Carrier o DC.

## Opciones Consideradas

### Opción 1: Tratar Reschedule y Short-Ship como etapas de atribución primaria
* **Pros:** Permite asignar directamente la culpabilidad del retraso a estos eventos si ocurren en la línea de tiempo del pedido.
* **Contras:** Error conceptual y metodológico. Un *reschedule* describe un evento logístico, pero el dato crudo no especifica qué actor lo solicitó (Proveedor, Cliente o Transportista), por lo que no es una causa raíz. Asignarlo como etapa introduce sesgos insostenibles.

### Opción 2: Modelar Reschedule como flag de contexto y Short-Ship como agravante de severidad
* **Pros:** Separa el "dónde ocurrió el retraso" (etapa) del "qué eventos especiales acompañaron al viaje" (contexto). Mantiene la pureza matemática del clasificador y enriquece la analítica agregada.
* **Contras:** Requiere la creación y mantenimiento de columnas adicionales en el modelo de datos que viajen de forma paralela a las flags de etapa.

## Decisión
Elegimos la **Opción 2**. Tras la validación con el mentor el 2026-06-16, se determina que estos eventos no constituyen etapas. 

El modelo de datos se estructuró bajo las siguientes reglas:
1. El *reschedule* se extrae del clasificador de etapas y se modela estrictamente como una **flag de contexto** independiente llamada `is_rescheduled`.
2. El *short-ship* (heredado del campo `_short_ship` de la Fase 1) se clasifica y procesa exclusivamente como un **agravante de severidad** de la demora, no como una causa raíz.

## Consecuencias
* **Positivas:** El clasificador de etapas se mantiene limpio y conceptualmente sólido (centrado en tramos físicos medibles). El pipeline hereda variables de contexto de alto valor para que la Fase 3 infiera narrativas ricas hacia el LLM sin inyectar sesgos inherentes.
* **Negativas:** La lógica de consumo aguas abajo debe realizar cruces matriciales entre la etapa asignada y estas flags contextuales para explotar todo el valor del dato.
