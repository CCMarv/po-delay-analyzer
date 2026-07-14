# Hallazgos: el cómputo temporal frente a la anotación humana

Este documento cuenta, como narrativa de negocio, dónde la clasificación automática por
timestamps supera a la anotación humana del reason code, dónde falla, qué implica para las
decisiones del analista y qué haría falta para llevarlo a producción. La tesis que sostiene
es directa: el cómputo temporal por timestamps del lifecycle corrige al reason code humano,
que el mentor reporta como ~20% incorrecto.

Cada afirmación cuantitativa es trazable a un artefacto del repo. Las cifras provienen de la
tabla única de métricas (`documentation/metricas-proyecto.md`), de la narración de mismatches
(`03_llm_integration/mismatches_ai_vs_humano.md`) y del README de Fase 2
(`02_clasif_reglas_negocio/README.md`). Los denominadores difieren entre métricas y no son
intercambiables; cada cifra se cita con su población y no se recalcula aquí.

## 1. Dónde el cómputo supera a la anotación humana

El cómputo temporal coincide con la anotación humana en 88.8% de los POs clasificables
(174/196) y discrepa en el ~11% restante. Ese desacuerdo no es error del método: son las 22
discrepancias donde el reason code heredado se aparta de lo que dicen los timestamps, y la
evidencia apunta a que los timestamps tienen razón. El dato del mentor lo respalda: la
anotación humana es aproximadamente 20% incorrecta, así que un método que discrepa donde la
anotación falla es precisamente lo que se busca.

De esas 22 discrepancias medidas, ocho se narran en detalle como muestra estratificada (tres
Vendor, tres Carrier, dos DC) en la narración de mismatches. Los ocho exhiben un mismo
fenómeno en dos variantes.

En los tres casos Vendor el humano culpa al eslabón visible —donde el PO se atoró
físicamente, sea el carrier o el patio del DC— mientras la aprobación de la cita ya había
llegado tarde desde antes, con un STA push de 87 a 125 horas, y el tramo acusado no registra
exceso alguno. El motivo humano ("ventana de cita perdida", "problema de equipo/tráiler",
"congestión de patio") describe un síntoma corriente abajo, no la causa. El cómputo aísla el
retraso donde efectivamente se produjo: en la aprobación tardía del vendor.

En los cinco casos restantes (Carrier contra DC) el humano confunde dos etapas downstream
contiguas —tránsito frente a procesamiento en el DC— mientras el cómputo mide el exceso en
una sola de las dos y descarta la otra por no tener exceso medible.

Un matiz honesto: en cuatro de los ocho casos el propio LLM marcó coincidencia con el reason
code humano pese al mismatch categórico entre la etapa del cómputo y el grupo anotado. Esto no
debilita la tesis. Ocurre porque el texto del reason code es temáticamente compatible con la
etapa que el cómputo señala, no con la etapa a la que quedó archivado; es decir, incluso la
redacción humana del motivo es ambigua frente a la taxonomía de tres etapas. La fuente de
verdad sigue siendo el timestamp, no la anotación ni la lectura que el LLM hace de ella.

Referencias: reason agreement 88.8% (174/196) y las 22 discrepancias en
`documentation/metricas-proyecto.md` (fila 2 y nota de contexto); el patrón transversal y los
ocho casos en `03_llm_integration/mismatches_ai_vs_humano.md`.

## 2. Dónde el método falla y cuáles son sus límites

El método tiene puntos ciegos, y su valor está en que los declara en lugar de adivinar. De
los 247 POs tardíos, 39 quedan clasificados como Indeterminado porque el cómputo no puede
sostener una causa dominante. Ese 39 se desglosa en dos límites distintos.

Quince POs quedan como `sin_datos`: son tardíos pero carecen de `TRAILER_ARRIVE_DT`, así que
no hay forma de medir los tramos de carrier y DC. Conviene precisar el alcance de este hueco:
en total 27 POs carecen de hora de tráiler, pero la regla que asigna Vendor por STA push
(`APPROVED_DT > STA_DT`) los rescata porque mide la aprobación tardía sin necesitar el
tráiler. Solo los 15 que además no tienen señal de vendor quedan sin diagnóstico. El diseño
recupera la mayoría de los registros con datos faltantes; el punto ciego real son esos 15.

Veinticuatro POs quedan como `sin_causa_dominante`: son medibles, pero ninguno de sus tramos
excede su umbral, de modo que no hay un eslabón al que atribuir el retraso con evidencia. El
método prefiere marcarlos Indeterminado antes que forzar una etiqueta sin respaldo temporal.

La consecuencia es que la exactitud de etapa de 100% se mide sobre 208 POs evaluables (247
menos los 39 Indeterminados), no sobre la población completa. El método no adivina lo que no
puede medir: lo marca Indeterminado y lo deja para revisión humana.

Del lado del LLM, la calidad de las explicaciones no es gratuita: depende del diseño del
prompt. El baseline zero-shot obtuvo 3.25/5 (13/20) y la variante few-shot ganadora (C3)
subió a 4.75/5 (19/20) contra el mismo benchmark. La diferencia es la ingeniería del prompt,
no el modelo. Esto implica un riesgo operativo: cambiar el prompt puede degradar la calidad
sin aviso, y las explicaciones de baja confianza siguen requiriendo criterio humano.

Referencias: desglose de Indeterminado (15 `sin_datos` + 24 `sin_causa_dominante`) y los 208
evaluables en `documentation/metricas-proyecto.md` (filas 1 y 5, sección de poblaciones); la
regla Vendor por STA push y los 27 sin hora de tráiler en
`02_clasif_reglas_negocio/README.md`; la comparación zero-shot contra few-shot C3 en
`documentation/metricas-proyecto.md` (fila 3).

## 3. Qué implica para las decisiones de negocio

El cómputo temporal cambia qué PO revisa primero el analista y con qué confianza actúa. Tres
efectos concretos.

Ahorro de tiempo del analista. La clasificación automática por timestamps sustituye una
anotación manual que es ~20% incorrecta y entrega, por cada PO, una causa defendible con
evidencia temporal en lugar de una etiqueta que puede estar culpando al eslabón equivocado. El
analista deja de auditar reason codes uno por uno y pasa a atender las excepciones que el
método marca.

Priorización por severidad. La severidad oficial del entregable es la que produce el LLM
(decisión registrada en ADR-10), y su ordenamiento de los casos hot-late acierta en 14/14. El
analista puede confiar en ese ranking para decidir el orden de atención sin recalcular
severidad a mano.

Qué revisar primero. Los POs hot-late (`HOT_PO_FLAG=1` con retraso mayor a tres días) son el
primer frente por su severidad. Después, el grueso del retraso vive en Vendor: 131 de los 247
tardíos (53%) se atribuyen a aprobación tardía, así que ahí está la mayor palanca de mejora
sistémica. Y en paralelo, las 22 discrepancias entre cómputo y anotación marcan exactamente
dónde no confiar en el reason code heredado.

Referencias: severidad LLM y Severity Ranking 14/14 en `documentation/metricas-proyecto.md`
(fila 4) y `documentation/decisiones/ARD-10.md`; reparto de etapas (Vendor 131, 53%) en
`documentation/metricas-proyecto.md` (fila 5).

## 4. Recomendaciones para producción

Lo demostrado corre sobre un dataset sintético. Llevarlo a producción exige tres cosas.

Datos reales. Los umbrales que definen el exceso por tramo (vendor 24 h, carrier 8 h) se
calibraron sobre datos sintéticos; antes de operar hay que validarlos contra histórico real,
porque un umbral mal puesto reasigna etapas en masa. Las decisiones de umbral están
registradas en los ADRs correspondientes y son el primer punto a revisar con datos reales.

Monitoreo. Conviene vigilar la deriva de dos señales como indicador de salud del sistema: el
nivel de agreement con la anotación humana y la tasa de Indeterminado. Un salto en la tasa de
Indeterminado suele significar deterioro en la calidad de los datos entrantes (timestamps
faltantes), no del método.

Governance del prompt. La mejora de zero-shot a few-shot C3 fue una mejora medida, no una
intuición; eso solo se sostiene si el prompt se versiona y cada cambio se re-evalúa contra el
benchmark reproducible (muestra estratificada, semilla 42). Sin ese control, un ajuste de
prompt puede degradar la calidad de las explicaciones sin que nadie lo note.

## Enlaces

- Insumo de mismatches: `03_llm_integration/mismatches_ai_vs_humano.md` (#95).
- Tabla de métricas y fuentes: `documentation/metricas-proyecto.md` (#104).
- Registro de decisiones: `documentation/decisiones/` — en particular `ARD-10.md` (severidad
  = LLM), referenciado en la sección 3.
- Método de validación y QA del cierre (#85): `documentation/validacion-y-qa.md`.
- Consume este documento: presentación final (#106).
