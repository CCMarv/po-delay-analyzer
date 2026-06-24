# stage_modifiers: concebido y eliminado

* **Estatus:** 📘 Superado (Decisión de diseño descartada antes del despliegue final)
* **Contexto Técnico:** Cierre de Fase 2 / Optimización de Atributos para LLM
* **Referencias:** PR #74

## Contexto y Problema
Durante el diseño intermedio de la Fase 2, se planteó la necesidad de facilitarle el trabajo de interpretación al Modelo de Lenguaje (LLM) que operará en la Fase 3. Para ello, se concibió la creación de una columna unificada de metadatos llamada `stage_modifiers`, cuyo objetivo era consolidar en un solo string o arreglo de texto los eventos especiales del pedido (si era reprogramado, envío incompleto o prioritario). El problema radicaba en evaluar si esta consolidación aportaba valor técnico o si generaba redundancia y sesgos en el pipeline de datos.

## Opciones Consideradas

### Opción 1: Mantener e implementar la columna consolidada `stage_modifiers`
* **Pros:** Entrega un atributo "masticado" y pre-digerido directamente en la tabla final, reduciendo la cantidad de columnas que el LLM debe leer en una misma fila.
* **Contras:** Introduce una capa de abstracción artificial innecesaria. Al empaquetar variables distintas en un solo campo de texto, se oculta el dato puro y se introduce un sesgo de interpretación de ingeniería en el dato antes de que llegue a la IA.

### Opción 2: Eliminar la columna y confiar exclusivamente en las variables nativas limpias
Descartar la columna `stage_modifiers` antes de consolidar la rama principal y exponer las banderas contextuales crudas y separadas.
* **Pros:** Mantiene el modelo de datos limpio y normalizado. Garantiza que la Fase 3 reciba la información de manera transparente y sin sesgos pre-imputados, permitiendo al LLM inferir la narrativa directamente desde los hechos objetivos del dato.
* **Contras:** Obliga al prompt o a la arquitectura de la Fase 3 a mapear e interpretar múltiples columnas booleanas simultáneas (`is_rescheduled`, `is_short_ship`, `HOT_PO_FLAG`).

## Decisión
Elegimos la **Opción 2**. Se decidió **eliminar definitivamente** la columna `stage_modifiers` durante el cierre de la Fase 2, cambio que quedó registrado y ejecutado en el **PR #74**. 

La arquitectura final determina que el contexto operativo ya está perfectamente representado de forma atómica por las variables `is_rescheduled`, `is_short_ship` (derivada de `_short_ship`) y `HOT_PO_FLAG`. La creación de una columna intermedia añadía complejidad al pipeline sin aportar información nueva. Este registro de arquitectura se conserva para dejar constancia histórica de **por qué no existe** dicha columna en el modelo final.

## Consecuencias
* **Positivas:** Simplificación del esquema de la base de datos y del código de transformación del pipeline. Se respeta el principio de "fuente de verdad limpia", garantizando que la Fase 3 genere narrativas basadas en datos puros y no en interpretaciones intermedias sesgadas.
* **Negativas:** La configuración de la Fase 3 del proyecto deberá incluir explícitamente en su contexto de datos el consumo e interpretación del set completo de banderas booleanas independientes.
