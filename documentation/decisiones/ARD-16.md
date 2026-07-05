# El LLM como capa analítica sobre la base determinista validada

* **Estatus:** 🔵 **BORRADOR** (lo cierra el equipo)
* **Contexto Técnico:** Fase 3 / Integración LLM — incorporar capacidades del modelo (conocimiento de dominio preentrenado, razonamiento, síntesis) por encima de la lógica determinista ya validada
* **Referencias:** Feedback de mentores posterior a la validación de main; README del repo original del mentor (métrica *LLM Explanation Quality*); `03_llm_integration/fixtures/eval_quality_20pos_C0_t09.md` / `_kb.md` (evidencia del síntoma); ADR-14 (anti-alucinación — se ajusta su alcance); ADR-12 (prompt); ADR-10 (severidad híbrida); ADR-07 (taxonomía de Indeterminado); ADR-15 (KB condicional — premisa revisada por este marco, destino pendiente); `03_llm_integration/llm_integration.py`; `03_llm_integration/eval_quality.py` / `eval_diversity.py`

## Contexto y Problema

El estado de main está revisado y validado por los mentores: la lógica determinista de
Fases 1–2 y la explicación por PO se midieron consistentes y estructuradas. El pedido
posterior define una tarea nueva: enriquecer el programa permitiendo que el LLM aplique
capacidades propias del modelo —conocimiento preentrenado de dominio, razonamiento,
síntesis— por encima de lo que los scripts deterministas calculan.

El síntoma concreto está en la acción recomendada. Los fixtures del benchmark (20 POs) lo
muestran: sin KB, las 20 acciones son variantes de las dos líneas ilustrativas del prompt
histórico ("Abrir un reclamo con [X] por las N h…", "Revisar con el equipo del [DC]…"); con
el KB de ADR-15 mejora el fraseo y persiste la naturaleza ("revise y asegure sus procesos",
"escalar para investigar las razones"). La acción delega la búsqueda de opciones al
responsable en lugar de proponer medidas.

El patrón tiene dos causas. La primera es la captura de las líneas ilustrativas como
plantillas. La segunda es estructural: el diagnóstico del modelo se detiene en el nivel
etapa, y una medida concreta exige comprometerse con un mecanismo bajo ese nivel
(inventario, capacidad de producción, documentación, congestión de puertas); el prompt
vigente prohíbe hipotetizarlo. Con acción concreta exigida y diagnóstico fino prohibido, la
meta-acción "revisar con X" es la salida racional del sistema.

El endurecimiento de ADR-14 ("usa ÚNICAMENTE las cifras dadas, no estimes") fue adecuado
mientras se auditaba la fidelidad a los datos; aplicado a la capa nueva, bloquea el uso del
conocimiento de dominio del modelo, que es la capacidad pedida. El README del repo original
pide "acción viable, no genérica" y sus propios ejemplos son categorías genéricas
("contact vendor, escalate to carrier, review DC capacity"); el feedback de los mentores
fija una vara superior a la del README y otorga libertad para modificar el esquema de
salida.

Test operativo de este ARD: hay análisis del modelo cuando la conclusión resulta
impredecible leyendo el código y los artefactos curados — el mapeo evidencia → conclusión
ocurre en el modelo.

Descartes previos con datos reales, que acotan los insumos disponibles: umbrales por ciudad
del DC (las 8 ciudades no difieren más allá del ruido) y estimación de distancia del
proveedor por ciudad × volumen × tiempo (celda típica de ~5 filas por ciudad × proveedor).

## Opciones Consideradas (papel del LLM en el producto)

**Opción A — Redactor acotado (statu quo).** El LLM redacta lo decidido por la lógica
determinista (ADR-12/14). Corresponde al estado validado en main. Deja sin atender el
pedido nuevo.

**Opción B — Analista con perímetro curado.** Dos llamadas, playbook versionado y
repertorio causal cerrado (borrador previo de este ARD). Pros: el conocimiento usado queda
pre-aprobado y auditable en el insumo. Contras: el equipo define por adelantado qué
conocimiento puede aplicar el modelo; la curación manual duplica conocimiento ya presente
en el modelo y limita el análisis a los casos previstos. Descartada al precisarse el
pedido.

**Opción C — Capa analítica sobre hechos verificados (elegida).** Las premisas factuales
provienen de los datos (ADR-14 se conserva en ese punto); el conocimiento de dominio
proviene del modelo, habilitado en el prompt y marcado en la salida. Contras: mayor
variancia entre corridas; el conocimiento aplicado deja de estar pre-aprobado y la
auditoría se desplaza del insumo a la salida (ver Validación).

## Opciones Consideradas (alcance de la capa)

**Opción A — Solo la acción por PO.** Alcance mínimo, cercano al pipeline actual. Deja
fuera capacidades incluidas en el pedido (patrones agregados, síntesis).

**Opción B — Tres carriles entregados en fases (elegida).** Cada carril con su issue; el
carril 1 reusa el pipeline existente y valida el perímetro nuevo antes de escalar a los
otros dos.

## Opciones Consideradas (mecanismos descartados o diferidos para la acción)

**Few-shot con acciones concretas — descartado.** Es el mecanismo que produjo la captura de
plantillas (historia de ADR-14 y evidencia del fixture); ejemplos de acción tienden a
convertirse en el repertorio completo.

**Búsqueda web por PO en producción — descartada.** Las entidades del dataset son
sintéticas y una búsqueda por entidad devuelve ruido (documentado en ADR-15); la búsqueda
por dominio general duplica el conocimiento preentrenado; el resultado deja de ser
reproducible.

**Búsqueda web offline materializada con fuentes — diferida.** Una corrida única por tema
(las preguntas del mentor × etapas/eventos), materializada en un documento versionado con
fuentes citadas, en modo prior. Colinda con la Opción B descartada (curación); se decide
tras la ola 2, solo con evidencia de que el conocimiento del modelo se queda corto.

**Búsqueda web en vivo como demostración — aceptada fuera del entregable.** Flag de demo,
solo backend oficial, queries por mecanismo con guarda en código que bloquea nombres de
entidades del dataset, afirmaciones con fuente citada, 3–5 POs con declaración de conteo.

**Señales de calendario — diferidas al carril 2.** Día de semana / semana del mes de los
hitos solo entran cuando los agregados del carril 2 puedan confirmar el patrón; una fecha
suelta invita a sobre-lectura.

## Decisión

1. **Papel del LLM.** El LLM opera como capa analítica sobre la salida de Fases 1–2
   (etapas, excesos, flags, severidad auditada por ADR-10). Esa salida provee los hechos;
   las conclusiones las produce el modelo.
2. **Perímetro anti-alucinación con dos reglas.** (a) Los hechos de la PO y del dataset
   provienen solo de los datos, con cifras citadas textualmente; ADR-14 se mantiene íntegro
   para la llamada determinista y para las premisas factuales de la capa. (b) Las
   generalizaciones de dominio provienen del conocimiento del modelo, habilitadas en el
   prompt y marcadas en la redacción, separadas de lo que los datos muestran. Se mantiene
   la instrucción de declarar cuando los datos no alcanzan para distinguir. Inventar
   premisas queda prohibido; derivar conclusiones queda permitido.
3. **Carril 1 — la llamada de acción.** La llamada actual queda intacta y emite
   `causa_raiz`, `severidad`, `coincide_con_reason_code` y `confianza` (de evidencia). La
   segunda llamada se diseña así:
   * **Rol:** planner de abastecimiento con autoridad para decidir los siguientes pasos de
     la PO, en lugar de analista.
   * **Diagnóstico diferencial obligatorio:** hipótesis de mecanismo bajo el nivel etapa,
     con su evidencia; hipótesis alternativa con el paso discriminante (el dato exacto que
     separa ambas y la decisión que depende de él).
   * **Contrato de salida (híbrido):** `razonamiento` →
     `hipotesis_principal {hipotesis, evidencia, plan {accion_inmediata, accion_correctiva,
     accion_preventiva}}` → `hipotesis_alternativa {hipotesis, paso_discriminante}` →
     `confianza` (de hipótesis). El orden de llaves condiciona el plan al razonamiento ya
     generado (generación autoregresiva). Sin límite de una-dos líneas por campo.
   * **Reglas de concreción:** los verbos meta (revisar, analizar, investigar, monitorear,
     dar seguimiento) no cuentan como acción principal; toda verificación nombra el dato
     exacto y la decisión que depende de él. Si hubo short-ship, el plan incluye la
     decisión del faltante (re-emitir / esperar / cancelar) con su criterio.
   * **Insumos:** el diagnóstico de la primera llamada, los hechos crudos, las magnitudes
     hoy ocultas (fill rate real, magnitud del reschedule en horas, tamaño de la orden) y
     hechos comparativos globales calculados determinísticamente (percentil del exceso,
     medianas por etapa), presentes en el prompt de toda PO — la presentación condicional
     de un comparativo introduciría el juicio por selección.
   * **Fallback de la primera llamada:** si la llamada determinista no produce
     diagnóstico, la llamada de acción no se ejecuta y la PO queda marcada
     (`qa_flags = sin_diagnostico_llamada1`), visible y sin bloquear el pipeline — sin
     diagnóstico validado no hay insumo para el plan.
   * **Elicitación del dominio:** auto-cuestionario previo con las preguntas del mentor
     (causas más comunes desde la etapa medida; afectación del shorting; causas y
     consecuencias del rescheduling) que el modelo responde con su conocimiento antes de
     recomendar; glosario abierto de términos de industria (expedite, chargeback, carrier
     scorecard, re-cita de dock, split shipment, safety stock, OTIF) como vocabulario
     disponible, términos sueltos con prohibición de transcribir frases.
   * **Señales adicionales:** la discrepancia REASON_DSC vs. etapa medida entra como
     meta-señal del proceso de anotación —habilita hipótesis de proceso (handoff mal
     registrado) sin promover el REASON_DSC a etapa (regla vigente)—; con
     `stage_multi` activo, el plan admite reparto multi-actor con la cifra de exceso de
     cada etapa y una sola acción inmediata (el cuello de botella).
4. **Carril 2 — patrones entre POs, en dos estadios.** Primero estático: agregados
   precomputados inyectados al prompt (historial del proveedor y del transportista dentro
   del dataset, percentiles, POs con el mismo patrón de señales, detalle del short-ship),
   cada uno con su n para que el modelo pondere la evidencia (celdas chicas documentadas).
   Después agéntico, solo si el benchmark muestra que el modelo ignora los agregados
   inyectados: herramientas de consulta (`historial_proveedor`, `percentil_exceso`,
   `pos_similares`, `detalle_short_ship`) con presupuesto de llamadas y log de preguntas
   persistido por PO como rastro auditable del razonamiento. El estadio agéntico cambia el
   contrato `call(prompt)` de los backends; se difiere hasta tener la evidencia.
5. **Carril 3 — capacidades de producto.** Síntesis ejecutiva del portafolio de retrasos y
   Q&A sobre el dataset, diseñadas junto con las vistas de Fase 4 (user personas de
   ADR-09). Issues propios.
6. **Indeterminado.** Las POs sin causa atribuible pasan por la capa analítica; el análisis
   esperado identifica el dato faltante y el paso de esclarecimiento (taxonomía de ADR-07).
7. **Control de calidad generativo (pase de autocrítica).** Tras la llamada de acción:
   * Checks por regla, en código y sin costo: acción principal sin verbo meta; toda cifra
     de la salida existe en el input; esquema completo; decisión del faltante presente si
     hubo short-ship; etapa nombrada igual a `stage_primary`. Falla → regeneración con el
     defecto citado, máximo 2 reintentos; si persiste, la salida se marca con `qa_flags`
     visibles y no se bloquea.
   * Checks por juicio, con juez LLM en backend local (sin costo de API): coherencia
     hipótesis → acción, validez del paso discriminante, marcado de generalizaciones,
     ejecutabilidad sin decisiones adicionales. El juez se calibra contra etiquetas humanas
     del fixture antes de usarse como pre-filtro de la validación humana.
8. **Secuencia por olas, con medición entre olas.** Cada ola se evalúa contra el fixture de
   20 POs (iteración en backend local) antes de sumar la siguiente, para preservar la
   atribución de mejoras (patrón de ADR-13/ADR-15):
   * Ola 1 (estructural): contrato híbrido, rol, reglas de concreción, checks por regla,
     magnitudes destapadas y comparativos globales.
   * Ola 2 (diagnóstico): diagnóstico diferencial, discrepancia REASON_DSC, multi-actor.
   * Ola 3 (refuerzos): auto-cuestionario, glosario, carril 2 estático.
   * Condicionales: razonamiento extendido o modelo más capaz en la llamada de acción si
     la profundidad no alcanza tras la ola 2; búsqueda offline materializada según
     evidencia tras la ola 2; demo web en vivo como flag independiente.
9. **Pendientes de implementación.** Interacción del contrato nuevo con el few-shot
   (C1–C3); exposición en Fase 4 del razonamiento, las dos confianzas, los `qa_flags` y
   las capacidades del carril 3; calibración del juez local.

## Validación (plan, carril 1)

La auditoría evalúa la salida: qué afirmó el modelo y sobre qué base. Sobre el fixture de
20 POs (#94):

* **Anclaje factual:** toda afirmación sobre la PO o el dataset cita un dato mostrado; toda
  generalización aparece marcada como conocimiento de dominio. Se verifica con los checks
  por regla (cifras ∈ input) y revisión humana muestral.
* **Concreción:** tasa de acciones con verbo meta como acción principal (automatizable con
  la lista cerrada de verbos); meta: cero tras la ola 1.
* **Discriminación:** POs con evidencia distinta producen hipótesis distintas. Se mide la
  covarianza insumos → conclusiones; la diversidad léxica de ADR-15 deja de ser la métrica
  objetivo.
* **Sensibilidad contrafactual:** alterar un solo insumo de una PO real (p. ej. fill rate
  95% → 72%) debe cambiar la conclusión en la dirección esperada. Corre en backend local.
* **Pre-filtro del juez local** para la validación humana: el humano valida una muestra
  más los casos que el juez marca; el contrato híbrido multiplica el texto a validar y el
  pre-filtro mantiene la validación tratable.

Toda corrida contra API de pago declara el conteo de llamadas y solicita permiso previo
(política vigente).

## Consecuencias

**Positivas:** cubre el pedido de los mentores; las acciones pasan de meta-acción a plan
ejecutable con decisión de negocio; la inferencia queda visible y auditable (razonamiento,
paso discriminante, log de agregados consultados en el estadio agéntico); la entrega por
olas preserva la atribución de mejoras.

**Negativas:** mayor variancia entre corridas; ~2× costo y latencia por PO más los
reintentos del pase de autocrítica; el contrato híbrido encarece los tokens de salida y
amplía la superficie de validación humana (mitigado por el pre-filtro); el esquema de
salida cambia y afecta el consumo de Fase 4; el marcado datos/dominio requiere validación
humana muestral.

## Relación con otras decisiones

Ajusta el alcance de **ADR-14**: su restricción se mantiene para la llamada determinista y
para las premisas factuales de la capa; deja de aplicar a las generalizaciones de dominio.
Preserva **ADR-10** (la severidad la emite el LLM y la audita Fase 2) y reusa **ADR-07** y
la infraestructura de **ADR-12**. La premisa de **ADR-15** (corrección de la redacción vía
conocimiento curado) queda revisada por este marco; su destino —mergear como mejora
independiente o encadenar como superado— se decide aparte. Un borrador previo no versionado
de este ARD desarrolló la Opción B (perímetro curado con playbook) y se reemplazó al
precisarse el pedido.
