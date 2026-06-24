# Fuente de verdad de las flags: calc vs. precalc

* **Estatus:** 🟢 Vigente
* **Contexto Técnico:** Fase 2 (Implementación de métricas base)
* **Referencias:** Issue #15

## Contexto y Problema
El origen de datos provee ciertas flags de retraso precalculadas (`precalc`). Sin embargo, el brief inicial del proyecto estipula estrictamente que los timestamps de auditoría mandan sobre cualquier otra métrica. Necesitamos definir de dónde consumirán los pipelines posteriores para evitar inconsistencias en el reporte de la taxonomía del retraso.

## Opciones Consideradas

### Opción 1: Confiar en las flags precalculadas del origen de datos
* **Pros:** Requiere menor esfuerzo de cómputo en las etapas tempranas del pipeline.
* **Contras:** Riesgo de "caja negra"; si hay un cambio en la lógica de negocio aguas arriba, perdemos la trazabilidad y violamos la restricción del brief que obliga a auditar mediante timestamps.

### Opción 2: Recalcular de forma dinámica todas las métricas derivadas desde los timestamps (`*_calc`)
* **Pros:** Alineación total con el brief del proyecto. Garantiza consistencia matemática absoluta, ya que el dato crudo manda y se expone de forma transparente.
* **Contras:** Incrementa ligeramente la complejidad del código de transformación en la capa intermedia.

## Decisión
Elegimos la **Opción 2**. Toda métrica derivada e indicador de retraso se recalcula en tiempo de ejecución de manera dinámica desde las variables `*_calc` usando los timestamps de auditoría. Las variables `precalc` originales quedan relegadas exclusivamente a tareas de *cross-check* secundarias para alertar desvíos en el origen.

## Consecuencias
* **Positivas:** Trazabilidad de extremo a extremo en el cálculo del retraso y cumplimiento de la rúbrica de auditoría.
* **Negativas:** Se debe dar mantenimiento y gobernanza al bloque de lógica de cálculo de desfases en el pipeline del proyecto.
