# ADR-09 · User personas como criterio de diseño de la Fase 4

* **Estatus:** 🔵 **BORRADOR** (pendiente de cierre por el equipo)
* **Contexto Técnico:** Diseño de la Fase 4 (Demo + aplicación) / Relevancia de negocio
* **Referencias:** Recomendación de mentores (sync 2026-06-26); Issues #102, #103; contrato de handoff #100; `../user_personas.md`

## Contexto y Problema
Los mentores recomendaron usar *user personas* para guiar el diseño. La Fase 4 ya tiene una app placeholder (`../../04_app/`) organizada por entidad de la cadena (Vendor/Carrier/DC), construida para tener un presentable antes de que la Fase 3 fije su salida. Falta un criterio explícito y defendible que oriente el rediseño de la Fase 4 cuando el contrato F3→F4 (#100) cierre, y que conecte las vistas de la app con un modelo de usuario, no con una organización por sujeto de medición. El problema: ¿sobre qué eje se define la herramienta de cara al usuario, y cómo se traza ese eje hasta el artefacto de datos y el board?

## Opciones Consideradas

### Opción 1: Dos personas por modo de consumo — individual vs. lote (Elegida)
Definir dos perfiles —Diego (consulta individual de un PO, consume la prosa del LLM) y Ravi (reporte agregado por lote, consume métricas y drill-down)— y derivar de ellos las dos vistas de la herramienta.
* **Pros:** El eje "modo de consumo" mapea 1:1 a las dos vistas que el mentor pide (vista individual #102, vista agregada #103). Es cause-agnostic, así que no se confunde con la taxonomía de etapas. Hace auditable qué columnas del artefacto consume cada vista, conectando con el contrato #100.
* **Contras:** No coincide con la organización por entidad del placeholder actual; obliga a reconocer que ese placeholder se rediseñará.

### Opción 2: Perfiles por entidad de la cadena (Vendor/Carrier/DC)
Tratar a cada dueño de etapa como un usuario y organizar la herramienta por entidad, como hace el placeholder.
* **Pros:** Coincide con la app ya construida; no exige retrabajo inmediato.
* **Contras:** Confunde sujeto de medición con usuario —el vendor y el carrier son medidos, no operan la herramienta—. No distingue el modo de consumo (individual vs. lote), que es el eje real de las dos vistas. Multiplica pantallas por entidad en vez de las dos vistas por modo de consumo.

## Decisión
Se elige la **Opción 1**. Las dos personas (Diego, Ravi), definidas por modo de consumo, son el criterio de diseño de la Fase 4 definitiva: dos personas, dos vistas del programa. El detalle vive en `../user_personas.md`; este registro fija la decisión y su porqué. La app actual queda como placeholder; su rediseño se hará contra estas personas una vez cerrado el contrato F3→F4 (#100). El destino de las pantallas por entidad del placeholder (si sobreviven como secciones, filtros o drill-down dentro de la vista agregada) queda como decisión abierta del rediseño, no comprometida aquí.

## Consecuencias
* **Positivas:** Trazabilidad persona→vista→issue (#102/#103) y persona→columnas del artefacto. Cubre directamente la rúbrica *Business Relevance & Stakeholder Insight*. Da un criterio para no retrabajar la entrada de Fase 4 a ciegas.
* **Negativas:** Reconoce explícitamente que el placeholder por entidad se rediseñará; el puente drill-down Ravi→Diego queda como diseño pendiente.
