# User Personas — PO Delay Root Cause Analyzer

> Documento de diseño versionado (`documentation/`). Define los dos perfiles de usuario que
> consumen la herramienta y las decisiones de diseño (prompt e interfaz) que cada uno
> determina. Surge de la recomendación de los mentores (sync 2026-06-26) de usar user
> personas para guiar el diseño de la Fase 4. Cada persona define una **vista** del
> programa. Versión en español; la versión en inglés se añade al cierre del desarrollo,
> según la convención bilingüe del repo.

## Qué son estas personas y por qué dos

Una persona aquí es una herramienta de diseño, no una ficha de personaje: cada campo existe para forzar una decisión concreta sobre el prompt o la app, y un campo que no cambia ninguna decisión se omite. Los nombres ("Diego", "Ravi") son etiquetas-handle intercambiables, no la sustancia.

Los dos perfiles se organizan por modo de consumo —consulta individual de un PO frente a reporte por lote— porque ese eje es exactamente el que define las dos superficies de la herramienta. Ambos son internos a la organización compradora y ambos son cause-agnostic (no son dueños de una sola etapa). Se mantienen como dos personas distintas, y no una con dos tareas, porque difieren en tres ejes simultáneos: la unidad de trabajo (un PO frente a la población), la dirección temporal (validar un caso hacia atrás frente a encontrar el patrón hacia adelante) y el rol del LLM (consumir la explicación en prosa frente a agregar campos estructurados).

Las entidades medidas por el sistema —proveedores y carriers— no son usuarios: son sujetos de medición y, en el caso del proveedor, posibles destinatarios de un reporte derivado (un scorecard). Solo los dos perfiles de abajo operan la herramienta.

## Vista comparativa

| Eje | Persona A — Consulta individual | Persona B — Reporte por lote |
|---|---|---|
| Handle | "Diego" | "Ravi" |
| Rol | Inbound Exception Coordinator | Supply-Chain Analyst / Network RCA |
| Unidad de trabajo | Un PO tardío | La población de tardíos |
| Scope de causa | Cause-agnostic (las 4 etapas) | Cause-agnostic, network-scoped (Vendor + Carrier + DC) |
| Dirección temporal | Retrospectiva: valida el caso | Prospectiva: encuentra el patrón |
| Pregunta central | ¿Qué pasó aquí y es cierto? | ¿Dónde está el patrón sistémico? |
| Rol del LLM | Central (consume la prosa) | Marginal (agrega estructura) |
| Acción de salida | Cierra o enruta la excepción | Reporte que habilita decisiones de otros |
| Frecuencia | Alta, reactiva | Baja, proactiva |

## Persona A — Inbound Exception Coordinator ("Diego")

- Rol: coordinador de excepciones inbound, interno a la organización compradora. Cause-agnostic: resuelve excepciones de POs tardíos una por una. Implementa los fixes a su alcance, valida la evidencia, enruta y verifica lo que no le corresponde.
- Objetivo (JTBD): cerrar cada excepción con la causa correcta confirmada, rápido, sin propagar el error del código humano hacia el agregado.
- Pregunta a la herramienta: "¿Qué pasó exactamente en este PO, es cierta la causa, y qué procede ahora?"
- Disparador: un PO tardío entra a su cola, o alguien consulta un PO específico. Reactivo, alta frecuencia, caso por caso.
- Qué consume: el bundle por-PO completo — timeline reconstruido, `stage_primary`, la explicación en prosa (`llm_causa_raiz`), la acción (`llm_accion_recomendada`), `llm_severidad`, y crítico para validar: `llm_coincide_con_reason` y `llm_confianza`. Es la superficie donde la prosa del LLM rinde su valor.

Actividades:

1. Abre el PO tardío y lee el timeline reconstruido.
2. Revisa la etapa clasificada y la severidad.
3. Contrasta con `REASON_DSC` vía `coincide_con_reason`; un mismatch es un hallazgo, no un error.
4. Lee la explicación y la acción; usa `confianza` para calibrar cuánto fiarse.
5. Ejecuta lo que está en su autoridad: corrige un dato maestro mal cargado, confirma o reagenda una cita, da seguimiento al proveedor por ese envío.
6. Para causas fuera de su mano (staffing del DC, SLA del carrier): enruta al dueño de esa etapa y verifica que actuó.
7. Marca el caso como validado; ese stream depurado alimenta el reporte de lote.

- Acción de salida: PO con causa confirmada y acción cerrada o enrutada; evidencia de timeline disponible para una eventual disputa.
- Confía cuando: la explicación respeta el orden de timestamps, la evidencia está completa, y la causa es consistente con cómo opera el proceso. Desconfía cuando: la salida es vaga o de caja negra, un evento único arrastra toda la conclusión, o falta data. Implicación de diseño: timeline como evidencia primaria, indicador de confianza visible, flag de desacuerdo (vs. `REASON_DSC`) prominente.
- Fuera de alcance: no agrega, no rankea proveedores, no decide cambios estructurales. Un PO a la vez. Si una decisión requiere el patrón de muchos POs, pertenece a la superficie de Ravi.

## Persona B — Supply-Chain Analyst / Network RCA ("Ravi")

- Rol: analista de supply chain dueño de dashboards, tendencias de causa raíz y reporting para gerencia. Interno a la organización compradora. Cause-agnostic y network-scoped: cubre Vendor + Carrier + DC por igual. No es dueño de ninguna relación operativa; mide la red y la hace legible para quien decide.
- Objetivo (JTBD): convertir el histórico de POs tardíos en inteligencia accionable y auditable, separando el problema estructural del ruido de una sola vez, a través de las tres causas.
- Pregunta a la herramienta: "¿Dónde está el patrón sistémico en la red —qué etapa, qué entidad—, con cuánta evidencia, y es reproducible para defenderlo?"
- Disparador: ciclo de reporting (mensual/trimestral), preparación de una revisión ejecutiva, o una pregunta de gerencia ("¿por qué cayó el inbound reliability?"). Proactivo, baja frecuencia, nivel red.
- Qué consume: agregados estructurados a través de las tres causas — distribución de `stage_primary` (Vendor / Carrier / DC / Indeterminado; hoy 53.0 / 16.2 / 15.0 / 15.8 % sobre 247 tardíos), conteos por entidad (proveedor, carrier, DC), distribución de severidad, tasa de desacuerdo vs. `REASON_DSC`, y tendencia temporal. La prosa del LLM es casi irrelevante; lo que importa es que la atribución sea consistente y reproducible desde timestamps. El lote es agregación determinística.

Actividades:

1. Corre el lote sobre el periodo y revisa el split por etapa (¿la red sigue siendo Vendor-dominante? ¿se movió?).
2. Para cada causa, agrega por entidad: qué proveedor, qué carrier, qué DC concentra los tardíos.
3. Aísla outliers por etapa (proveedor X, lane Y, un DC específico — el EDA ya marcó Phoenix como candidato).
4. Cuantifica: N tardíos, % del bucket, severidad acumulada, tendencia vs. periodo anterior.
5. Audita la calidad de la atribución: ¿la tasa de desacuerdo con el código humano es sistemática (señal) o aleatoria (ruido)?
6. Produce el reporte/dashboard segmentado por causa y los artefactos derivados (incluido un scorecard de proveedor cuando aplica, como uno de varios outputs).
7. Entrega el hallazgo al dueño que puede actuar: Vendor → procurement; Carrier → coordinador de transporte; DC → operaciones del centro. Expone; ellos ejecutan.

- Acción de salida: reporte/dashboard de red, segmentado por causa, que habilita decisiones estructurales de otros — no una acción que Ravi mismo ejecute.
- Confía cuando: la atribución es repetible y explicable a través de muchas órdenes, el desacuerdo se ve sistemático, y la lógica es auditable en el tiempo. Desconfía cuando: las etiquetas son ruidosas o no calibradas, los outputs son inestables, o el desacuerdo se ve aleatorio. Implicación de diseño: agregados, tendencias y tasa de desacuerdo como métrica de primera clase; reproducibilidad visible; drill-down a POs individuales (puente hacia la superficie de Diego) para inspeccionar la evidencia detrás de un número.
- Fuera de alcance: no resuelve excepciones caso por caso (eso es Diego); no toma la acción correctiva (eso es el dueño de la etapa); no opera sobre la prosa de un PO suelto. Su producto es el reporte, no la acción.

## Relación entre las dos personas

Las dos personas no se colapsan en una porque difieren en tres ejes a la vez, y basta uno para distinguirlas: la unidad de trabajo (Diego opera un PO, Ravi la población), la dirección temporal (Diego mira hacia atrás para validar un caso, Ravi mira el histórico para encontrar el patrón hacia adelante) y el producto (Diego cierra o enruta una excepción, Ravi entrega un reporte que otros usan para decidir). Aplicado el contraste directo: ninguno llegaría a la misma decisión mirando la misma pantalla, porque Diego nunca agrega y Ravi nunca opera un caso suelto.

Entre ambas existe un pipeline de dos direcciones, no dos islas. El stream de casos validados por Diego (su paso 7) es el insumo depurado que hace confiable el agregado de Ravi; sin esa validación caso por caso, el lote arrastra el ~20 % de error del código humano. En sentido inverso, el drill-down de Ravi aterriza en la superficie de Diego cuando necesita ver la evidencia detrás de un número agregado. Diego valida hacia arriba; Ravi inspecciona hacia abajo. La síntesis operativa: el caso valida, el patrón decide.

## Implicaciones de diseño

Cada persona determina una vista distinta del programa, y de ahí salen los puntos de partida para el diseño de la Fase 4.

La superficie de Diego es una vista de PO individual centrada en la evidencia: timeline reconstruido como elemento primario, etapa y severidad visibles, la explicación y la acción del LLM, el indicador de confianza, y —prominente— el flag de desacuerdo con `REASON_DSC`, que es donde la herramienta agrega valor sobre la anotación humana. Queda como decisión abierta de Fase 4 si esta superficie necesita una noción de estado/seguimiento para soportar el paso de "verificar" (volver al PO a confirmar que la acción aterrizó) o si esa verificación ocurre fuera de la herramienta.

La superficie de Ravi es un reporte/dashboard de población: distribución por etapa, conteos por entidad a través de las tres causas, distribución de severidad, tendencia temporal, y la tasa de desacuerdo vs. `REASON_DSC` elevada a métrica de primera clase —que además mapea directo al umbral del mentor de Reason Code Agreement. Incluye drill-down al PO individual como puente hacia la superficie de Diego. No consume prosa del LLM.

### Qué consume cada persona del artefacto de handoff

El contrato de handoff F3→F4 (issue #100, verificado en `../tests/test_handoff_contract.py`) persiste **todas** las columnas del DataFrame clasificado más las que añade el LLM en Fase 3 —no un subconjunto curado. Cada persona consume un corte distinto de ese artefacto, y ese corte es lo que alimenta su vista:

| Persona | Columnas que consume | Para qué |
|---|---|---|
| Diego (individual) | `PO_DT … RECPT_DT` (timestamps del lifecycle), `stage_primary`, `severity`, `llm_causa_raiz`, `llm_accion_recomendada`, `llm_confianza`, `llm_coincide_con_reason` | Reconstruir el timeline del PO y leer el diagnóstico en prosa + los indicadores de validación |
| Ravi (lote) | `stage_primary`, `VENDOR_NAME` / `CARRIER_PARTY_NAME` / `DC_LOC_NAME`, `severity`, `llm_coincide_con_reason` vs `REASON_DSC` | Split por etapa, conteos por entidad, distribución de severidad y tasa de desacuerdo agregada |

Implicación operativa: la vista de Diego depende de columnas que Fase 3 aún produce (`llm_*`; el `llm_out.csv` todavía no existe en el repo) y de un timeline reconstruido desde los timestamps —que el placeholder actual de la app no arma. La vista de Ravi eleva la tasa de desacuerdo (`llm_coincide_con_reason` agregado) a métrica de primera clase, que mapea directo al umbral del mentor *Reason Code Agreement*. Las personas no piden columnas nuevas al contrato; fijan **qué corte del artefacto rinde valor en cada vista**, y por tanto guían la Fase 4 definitiva una vez que Fase 3 cierre su salida.

## Trazabilidad: persona → vista → issue

Cada persona define una vista del programa. El objetivo de la Fase 4 son dos vistas por modo de consumo (individual y agregada); cómo se acomodan dentro de ellas las pantallas por entidad del placeholder es una decisión abierta del rediseño.

| Persona | Vista | Issue del board | Estado |
|---|---|---|---|
| Diego | Consulta individual de un PO (timeline + diagnóstico + prosa LLM) | #102 (`fundamental`) | Placeholder en `../04_app/app.py`; rehacer tras cerrar Fase 3 |
| Ravi | Reporte agregado por lote (split, conteos, severidad, tasa de desacuerdo) | #103 | Placeholder en dashboards por entidad; rehacer tras cerrar Fase 3 |
| Puente Ravi → Diego | Drill-down de un agregado a un PO individual | Alcance compartido de #102/#103 | Pendiente de diseño |

La app actual (`../04_app/`) es un placeholder adelantado, organizado por entidad de la cadena (Vendor / Carrier / DC), construido para tener un presentable antes de que Fase 3 fije su salida. Estas personas son el criterio con el que esa Fase 4 se rediseñará, no una justificación del placeholder. La decisión que fija este eje se registra en `decisiones/ARD-09.md`.

## Alcance y trazabilidad

Los dos perfiles se derivan del modelo operativo de la cadena de suministro inbound y de los outputs que la propia herramienta produce; no provienen de user research, porque el dataset es sintético y la herramienta no está desplegada. El framing defendible es el de un sistema de soporte a decisiones y auditoría para POs tardíos —retrospectivo, no predictivo—, validado en un entorno controlado. Esa derivación desde el modelo operativo es, en sí misma, el insumo del criterio de relevancia de negocio e insight de stakeholder de la rúbrica.
