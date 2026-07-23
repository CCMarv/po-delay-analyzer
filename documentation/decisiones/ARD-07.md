# Taxonomía de Indeterminado

* **Estatus:** 🟢 Vigente
* **Contexto Técnico:** Cierre de Fase 2 / Modelado de Excepciones y Calidad de Datos
* **Referencias:** Consulta de Ronda 2 (Mentor, 2026-06-18), Discussion #57, PR #62

## Contexto y Problema
Al elevar el umbral de Vendor a 24 horas (ver [ADR-06b](ARD-06b.md)) y evaluar pedidos con registros incompletos, surgieron casos donde un pedido se consideraba tardío pero no se le podía imputar responsabilidad directa a ninguno de los tres actores principales (Vendor, Carrier o DC). El reto de diseño consistía en clasificar estos pedidos sin forzar una asignación errónea por descarte, lo cual reintroduciría sesgos en el modelo y alteraría las métricas de negocio.

## Opciones Consideradas

### Opción 1: Enviar los casos ambiguos a Vendor por descarte
* **Pros:** Mantiene un modelo simple con pocas categorías principales.
* **Contras:** Viola la directriz explícita del mentor. Reintroduce de forma silenciosa el sesgo de sobreatribución y penaliza injustamente al Proveedor por problemas de calidad de datos o micro-demoras tolerables.

### Opción 2: Crear una nueva etapa hermana en el nivel superior del clasificador
* **Pros:** Separa visualmente los problemas del resto de los actores en el primer nivel del reporte.
* **Contras:** Rompe la arquitectura del negocio basada en los tres pilares de la cadena de suministro, sobrecomplicando las consultas macro del pipeline.

### Opción 3: Diseñar una sub-taxonomía interna en la categoría "Indeterminado"
Implementar una variable analítica complementaria (`indeterminado_substage`) que segregue la raíz del problema de forma aislada, manteniendo el estado de nivel superior como "Indeterminado".
* **Pros:** Sólido y limpio. Sigue el patrón de diseño ya existente en el proyecto para el Centro de Distribución (`dc_substage`). Fue la recomendación explícita del mentor (Opción B del veredicto del 2026-06-18).
* **Contras:** Obliga al equipo a dar soporte y mantenimiento a una nueva columna y a documentar con precisión matemática sus criterios de activación.

## Decisión
Elegimos la **Opción 3**. Se implementó la columna **`indeterminado_substage`** en el modelo de datos para dividir de forma estricta los 39 pedidos asignados a esta categoría bajo dos criterios mutuamente excluyentes:

1. **`sin_datos`** (15 POs): El pedido presenta un retraso físico medible en las fechas finales, pero carece de datos atómicos en el origen para auditar los tramos (ej. pedidos tardíos sin registro de tráiler / `NaN`).
2. **`sin_causa_dominante`** (24 POs): El pedido cuenta con datos de auditoría 100% completos, pero tras aplicar los umbrales de negocio simétricos (8h Carrier, 4/6h DC, 24h Vendor), **ninguno de los tramos superó su respectiva tolerancia**.

Esta lógica quedó integrada en la arquitectura del clasificador y fue desplegada en el repositorio a través del Pull Request **#62**.

## Consecuencias
* **Positivas:** El clasificador alcanza una pureza conceptual absoluta. Se evita el descarte ciego y se le entrega a la Fase 3 una estructura de datos limpia que permite al LLM entender la diferencia exacta entre "falta de información" y "operación eficiente dentro de las tolerancias permitidas".
* **Negativas:** La reportería final del negocio debe estar consciente de esta sub-taxonomía para no interpretar erróneamente todos los casos "Indeterminados" como fallas críticas del sistema de extracción de datos.

## Nota (2026-07-22)
Los conteos citados arriba (39 pedidos, 15 `sin_datos`, 24 `sin_causa_dominante`) reflejan el
reparto vigente al cerrar esta decisión (2026-06-18). La nota de cierre de
[ADR-03b](ARD-03b.md) (2026-07-22) corrigió un gate del clasificador que excluía a Vendor sin
condición propia: 8 de los 39 pedidos migraron de `sin_datos` a Vendor, dejando el reparto
actual en 31 (7 `sin_datos` + 24 `sin_causa_dominante`). Esta decisión no se reabre — la
sub-taxonomía y sus dos criterios mutuamente excluyentes siguen vigentes tal cual se describen
arriba.
