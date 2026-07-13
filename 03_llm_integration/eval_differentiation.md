# Diferenciación intra-etapa de las recomendaciones tier-2 (#151)

Se mide si POs de la misma etapa reciben recomendaciones diferenciadas, ahora que tier-2 emite señal diferencial (hipótesis + evidencia + paso discriminante + plan). La operacionalización sigue [ADR-16](../documentation/decisiones/ARD-16.md) §Validación/Discriminación: no la diversidad léxica de ADR-15 —dos POs con la misma evidencia deben converger—, sino convergencia léxica intra-etapa leída junto con la covarianza señal -> hipótesis.

Método en dos capas:

1. **Convergencia léxica intra-etapa.** Por etapa, Jaccard sobre tokens de contenido; dos POs convergen si Jaccard >= θ=0.25. Los clústeres se forman por líder/vecindario (cada miembro dentro de θ del líder, sin encadenamiento transitivo). Se mide sobre `llm_hipotesis` y `llm_accion_inmediata`.
2. **Covarianza señal -> hipótesis.** A cada clúster convergente se le fija la firma de evidencia determinista MODAL de sus miembros (`is_short_ship`, `HOT_PO_FLAG`, `llm_coincide_con_reason`; el tercil de magnitud del exceso es señal graduada y no cuenta para la firma). La convergencia con firma modal homogénea es *justificada* (misma evidencia -> misma recomendación) y la **pureza modal** mide esa fracción. El fallo —el clúster que *ignora la evidencia* de ADR-16— son los POs **fuera de firma**: los que reciben la recomendación modal aunque su firma fuerte difiera de la modal.

**Métrica titular:** fracción de POs fuera de firma (evidencia ignorada), reportada junto al paisaje de convergencia (% en clúster, pureza modal). No se usa una tasa de 'clúster sospechoso' porque satura: con clústeres grandes, casi cualquiera incluye algo de variación de señales y quedaría marcado, inflando el fallo.

Supuestos: θ=0.25 se hereda del fixture de ola 1 (calibrado en ADR-16) y se aplica al conjunto completo. En esta corrida `llm_coincide_con_reason` es binaria (207 True / 40 False): no aparece el estado 'no-evaluable'. Población: 247 POs tardíos con tier-2 poblado.

## Campo: hipótesis (`llm_hipotesis`)

POs fuera de firma (evidencia ignorada): **46/247** (18.6%).

| Etapa | n | Jaccard medio | Clústeres conv. | Mayor | % en conv. | Pureza modal | Fuera de firma |
|---|--:|--:|--:|--:|--:|--:|--:|
| Carrier | 40 | 0.148 | 4 | 20 | 75.0% | 0.53 | 14 (35.0%) |
| DC | 37 | 0.215 | 1 | 29 | 78.4% | 0.83 | 5 (13.5%) |
| Indeterminado | 39 | 0.095 | 5 | 7 | 48.7% | 0.79 | 4 (10.3%) |
| Vendor | 131 | 0.165 | 7 | 60 | 87.0% | 0.80 | 23 (17.6%) |

### Clústeres con evidencia ignorada (hipótesis)

**Carrier** — clúster de 20 POs, pureza modal 0.45, 11 fuera de firma.

> Recomendación modal: Planificación ineficaz de las rutas por parte del transportista.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100290 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Planificación ineficaz de las rutas por parte del transportista. |
| 100024 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Un fallo en la planificación de rutas del transportista ha provocado un exceso de 25.7 horas en el tránsito hacia el ce… |
| 100214 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T2 | Fallas en la planificación de rutas y adaptabilidad del transportista a condiciones climáticas adversas. |
| 100244 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T2 | Planificación de rutas deficiente del transportista, que resulta en tiempos prolongados en tránsito. |
| 100261 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Falla en la planificación de rutas del transportista YRC Worldwide, lo que provocó el incumplimiento de la ventana de l… |
| 100278 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Mala planificación de rutas del transportista (UPS Freight) que resultó en un exceso de tiempo de tránsito. |
| 100285 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, coincide=False, mag=T0 | Fallo en la planificación de rutas del transportista Werner Enterprises, que resultó en un tránsito ineficiente. |
| 100286 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T2 | El mecanismo concreto es la planificación inadecuada de rutas por parte del transportista, lo que condujo a un exceso d… |
| 100343 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T0 | La planificación de rutas ineficiente del transportista está generando retrasos en la entrega. |
| 100380 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | La planificación de rutas del transportista fue ineficaz, lo que llevó a un exceso de tiempo de tránsito de 4.2 horas. |
| 100392 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Planificación ineficiente de las rutas por parte del transportista que lleva a demoras excesivas en el tránsito. |

**Carrier** — clúster de 5 POs, pureza modal 0.60, 2 fuera de firma.

> Recomendación modal: Problema con el equipo/tráiler del transportista, lo que resultó en un retraso en la entrega.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100099 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Problema con el equipo/tráiler del transportista, lo que resultó en un retraso en la entrega. |
| 100310 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Problema con el equipo/tráiler del transportista (Carrier) que retrasó el transporte |

**Carrier** — clúster de 3 POs, pureza modal 0.67, 1 fuera de firma.

> Recomendación modal: La planificación de rutas del transportista (UPS Freight) no anticipó adecuadamente las condiciones climáticas adversas, resultando en un exceso de tiempo de tránsito.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100315 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T2 | La planificación de rutas del transportista fue inadecuada debido a condiciones climáticas, lo que llevó a un exceso de… |

**DC** — clúster de 29 POs, pureza modal 0.83, 5 fuera de firma.

> Recomendación modal: La congestión de puertas en el DC está causando el retraso en la descarga y la espera en el patio.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100321 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | La congestión de puertas en el DC está causando el retraso en la descarga y la espera en el patio. |
| 100092 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T2 | congestión en el patio del DC que causó retraso en la recepción de la carga |
| 100123 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T2 | La congestión del patio en el DC impidió una descarga oportuna, resultando en un exceso de 21.4 horas de espera. |
| 100204 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Congestión de puertas en el centro de distribución (DC) provocó la prolongación del tiempo de descarga. |
| 100221 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Congestión en las puertas de descarga en el DC. |

**Indeterminado** — clúster de 4 POs, pureza modal 0.50, 2 fuera de firma.

> Recomendación modal: Si la reprogramación de la cita de entrega fue causada por problemas de planificación del proveedor, entonces el mecanismo es una falta de coordinación en la disponibilidad de car…

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100206 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T2 | Si la reprogramación de la cita fue causada principalmente por un fallo en la planificación del proveedor, entonces el … |
| 100254 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Si la reprogramación de la cita fue causada por problemas logísticos del transportista, entonces el mecanismo podría se… |

**Indeterminado** — clúster de 3 POs, pureza modal 0.67, 1 fuera de firma.

> Recomendación modal: El mecanismo de reprogramación ineficiente por parte del proveedor está detrás de la etapa Indeterminada del retraso.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100375 | HOT_PO_FLAG | short=False, hot=1, coincide=False, mag=T2 | Si se confirma que el proveedor no cumplió con el tiempo de envío acordado, el mecanismo es un retraso en la gestión de… |

**Indeterminado** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: El retraso se debe a una falta de coordinación en el envío entre el proveedor y el transportista, lo que resulta en demoras en el cumplimiento del plazo de entrega.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100249 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T1 | La falta de coordinación entre el proveedor (HEALTHCORP) y el transportista (Old Dominion) provocó el retraso indetermi… |

**Vendor** — clúster de 60 POs, pureza modal 0.75, 15 fuera de firma.

> Recomendación modal: Falta de eficiencia en la planificación y programación del proveedor, lo que resultó en un retraso en la cita de entrega.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100063 | is_short_ship | short=True, hot=0, coincide=True, mag=T2 | Falta de producto disponible en el inventario del proveedor que resultó en el short ship y el retraso en la entrega. |
| 100079 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T0 | Fallo en la planificación de la agenda del proveedor que provocó la reprogramación de la cita de entrega. |
| 100086 | is_short_ship | short=True, hot=0, coincide=True, mag=T1 | La causa del retraso es la falta de inventario en el proveedor Synco, lo que resultó en un envío incompleto. |
| 100094 | is_short_ship | short=True, hot=0, coincide=True, mag=T1 | La causa principal del retraso es la falta de inventario en el proveedor, lo que resultó en un short ship. |
| 100129 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | El retraso se debe a un mal manejo en la planificación de entregas del proveedor, causado por una falta de coordinación… |
| 100197 | is_short_ship, HOT_PO_FLAG | short=True, hot=1, coincide=True, mag=T2 | El mecanismo subyacente es la falta de disponibilidad de inventario en el proveedor, lo que causó el retraso en la entr… |
| 100209 | is_short_ship | short=True, hot=0, coincide=True, mag=T2 | La causa principal del retraso es la falta de inventario disponible en el proveedor, lo que resultó en un short ship. |
| 100213 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T2 | Problemas en la planificación y programación del proveedor (AKZE) llevaron a la reprogramación de la cita de entrega, c… |
| 100220 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | El proveedor tuvo problemas de planificación y programación que provocaron la reprogramación de la cita y un exceso en … |
| 100247 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Mala planificación o programación de entrega por parte del proveedor BIOPLEX, que resultó en un exceso de tiempo en la … |
| 100317 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Falta de planificación o coordinación de entregas por parte del proveedor. |
| 100330 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Falta de coordinación en la planificación de la entrega por parte del proveedor. |
| 100371 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Falta de capacidad de programación y coordinación efectiva en el proceso de entrega por parte del proveedor GREENLEAF. |
| 100382 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, coincide=False, mag=T2 | Falta de coordinación en la planificación de envíos por parte del proveedor. |
| 100387 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Fallo en la planificación de envíos del proveedor SYNCO, lo que resultó en el retraso en la entrega. |

**Vendor** — clúster de 21 POs, pureza modal 0.90, 2 fuera de firma.

> Recomendación modal: Planificación y coordinación deficientes en la agenda de entrega por parte del proveedor.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100044 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T0 | La reprogramación de la entrega se debió a fallos en la planificación de rutas o en la gestión de agenda del proveedor … |
| 100157 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T2 | Fallo en la planificación y coordinación de rutas del proveedor |

**Vendor** — clúster de 14 POs, pureza modal 0.86, 2 fuera de firma.

> Recomendación modal: Falta de producto disponible en el inventario del proveedor, que ha producido el short ship y el retraso de la PO.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100148 | HOT_PO_FLAG | short=True, hot=1, coincide=True, mag=T2 | El mecanismo concreto es que el proveedor no tenía suficiente inventario disponible para cumplir con la PO, lo que caus… |
| 100302 | HOT_PO_FLAG | short=True, hot=1, coincide=True, mag=T2 | Falta de inventario o problemas de producción en el proveedor MEDIQ. |

**Vendor** — clúster de 6 POs, pureza modal 0.50, 3 fuera de firma.

> Recomendación modal: El proveedor tuvo problemas con la capacidad de producción o con el inventario disponible para cumplir con la orden en el tiempo prometido.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100232 | HOT_PO_FLAG | short=False, hot=0, coincide=True, mag=T2 | El proveedor tuvo problemas con la capacidad de producción o con el inventario disponible para cumplir con la orden en … |
| 100288 | is_short_ship, HOT_PO_FLAG | short=True, hot=0, coincide=True, mag=T1 | El mecanismo subyacente es la falta de inventario o capacidad de producción del proveedor VITAGEN para cumplir con la c… |
| 100320 | HOT_PO_FLAG | short=False, hot=0, coincide=True, mag=T0 | El proveedor tuvo problemas en la planificación de envíos que resultaron en el retraso en la entrega, a pesar de cumpli… |

**Vendor** — clúster de 3 POs, pureza modal 0.67, 1 fuera de firma.

> Recomendación modal: El mecanismo concreto bajo la etapa diagnosticada es una deficiencia en la gestión de la planificación y programación del proveedor.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100369 | is_short_ship | short=True, hot=0, coincide=True, mag=T0 | El mecanismo concreto bajo la etapa diagnosticada es la falta de inventario adecuado del proveedor, lo que provocó que … |

## Campo: acción inmediata (`llm_accion_inmediata`)

POs fuera de firma (evidencia ignorada): **38/247** (15.4%).

| Etapa | n | Jaccard medio | Clústeres conv. | Mayor | % en conv. | Pureza modal | Fuera de firma |
|---|--:|--:|--:|--:|--:|--:|--:|
| Carrier | 40 | 0.151 | 5 | 13 | 70.0% | 0.57 | 12 (30.0%) |
| DC | 37 | 0.138 | 3 | 11 | 48.6% | 0.78 | 4 (10.8%) |
| Indeterminado | 39 | 0.096 | 4 | 9 | 43.6% | 0.65 | 6 (15.4%) |
| Vendor | 131 | 0.135 | 12 | 31 | 82.4% | 0.85 | 16 (12.2%) |

### Clústeres con evidencia ignorada (acción inmediata)

**Carrier** — clúster de 13 POs, pureza modal 0.62, 5 fuera de firma.

> Recomendación modal: Contactar a J.B. Hunt para obtener un informe detallado de la planificación de rutas en esta PO para entender la causa del retraso.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100024 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Contactar a Schneider National hoy para obtener un informe detallado de la planificación de rutas y cualquier congestió… |
| 100261 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Contactar a YRC Worldwide para obtener su reporte de planificación de rutas y cronograma de entregas para esta PO. |
| 100286 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T2 | Contactar a Werner Enterprises para obtener un informe detallado sobre la planificación de la ruta y los factores que c… |
| 100380 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Contactar a XPO Logistics para obtener un informe detallado sobre la gestión de rutas que llevaron a este retraso, espe… |
| 100392 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Contactar a Schneider National para obtener un informe detallado sobre la planificación de la ruta utilizada para esta … |

**Carrier** — clúster de 8 POs, pureza modal 0.50, 4 fuera de firma.

> Recomendación modal: Contactar a YRC Worldwide para obtener un informe detallado del problema del equipo/tráiler que causó 23.2 horas de exceso en la entrega.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100099 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Contactar a Estes Express para obtener un informe detallado sobre el problema del equipo/tráiler y sus causas; si no pr… |
| 100138 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, coincide=False, mag=T0 | Contactar a Old Dominion para obtener un informe detallado sobre las causas del exceso de 1.9 horas en la entrega de la… |
| 100239 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T2 | Contactar a Werner Enterprises para obtener un informe detallado sobre el problema del equipo que causó el retraso; si … |
| 100310 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Contactar a Estes Express para obtener información detallada sobre el problema del equipo/tráiler que causó el retraso. |

**Carrier** — clúster de 3 POs, pureza modal 0.67, 1 fuera de firma.

> Recomendación modal: Contactar a XPO Logistics para obtener el detalle de la planificación de rutas utilizada en la entrega de la PO 100290 y confirmar si hubo problemas de congestión o cambios de últ…

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100290 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Contactar a XPO Logistics para obtener el detalle de la planificación de rutas utilizada en la entrega de la PO 100290 … |

**Carrier** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: Contactar a Werner Enterprises para obtener datos sobre la planificación de rutas y cómo respondieron a las condiciones climáticas específicas en este caso; si se confirma que no …

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100285 | HOT_PO_FLAG | short=False, hot=1, coincide=False, mag=T0 | Contactar a Werner Enterprises para obtener información detallada sobre la planificación de rutas y confirmar si las co… |

**Carrier** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: Contactar a UPS Freight para obtener datos específicos sobre la planificación de rutas y condiciones enfrentadas durante el tránsito; si la respuesta revela fallas en la planifica…

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100315 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T2 | Contactar a UPS Freight para solicitar detalles específicos sobre la planificación de rutas que llevaron al retraso, co… |

**DC** — clúster de 11 POs, pureza modal 0.73, 3 fuera de firma.

> Recomendación modal: Coordinación con el equipo del DC para obtener un informe sobre la disponibilidad de puertas hoy y confirmar si persistió la congestión en el patio.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100123 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T2 | Coordinación con el equipo del DC para obtener un informe sobre la disponibilidad de puertas hoy y confirmar si persist… |
| 100204 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Contactar al gerente del DC para confirmar si hay congestión en las puertas de descarga y obtener el número de camiones… |
| 100321 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Coordinar con el equipo del DC para obtener un informe sobre las puertas disponibles y la programación de camiones, par… |

**DC** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: Coordinar con el DC para obtener datos sobre el número de puertas disponibles y el flujo de vehículos para el día de la recepción; si se confirma que no hay suficientes puertas di…

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100221 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Coordinar con el personal de recepción del Charlotte DC para obtener datos sobre el número de recibos y la asignación d… |

**Indeterminado** — clúster de 9 POs, pureza modal 0.56, 4 fuera de firma.

> Recomendación modal: Contactar al proveedor NOVAPHARM para obtener información precisa sobre el tiempo de llegada del tráiler y confirmar si la reprogramación de la cita causó el retraso.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100072 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T0 | Contactar al proveedor NOVAPHARM para obtener claridad sobre las razones específicas detrás de la reprogramación de la … |
| 100164 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T1 | Contactar al proveedor HEALTHCORP para obtener información específica sobre las dificultades logísticas que causaron la… |
| 100273 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T1 | Obtener información específica sobre el tiempo de llegada del tráiler: si se documenta un tiempo de espera significativ… |
| 100300 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T2 | Contactar a SYNCO para obtener información precisa sobre las razones de la reprogramación de la cita de entrega, especí… |

**Indeterminado** — clúster de 4 POs, pureza modal 0.75, 1 fuera de firma.

> Recomendación modal: Contactar con Old Dominion para obtener información específica sobre la entrega de esta PO y confirmar si hubo problemas logísticos en su lado que causaran el retraso.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100249 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T1 | Contactar al proveedor HEALTHCORP para confirmar si hubo problemas de coordinación o comunicación con Old Dominion que … |

**Indeterminado** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: Contactar al proveedor para obtener detalles específicos sobre la razón de la reprogramación de la entrega y verificar si se trata de un problema de capacidad de producción.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100242 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T2 | Contactar al proveedor BIOMED para obtener claridad sobre la razón específica de la reprogramación de la cita; si la ra… |

**Vendor** — clúster de 31 POs, pureza modal 0.84, 5 fuera de firma.

> Recomendación modal: Contactar al proveedor GREENLEAF para obtener detalles específicos sobre la causa de la reprogramación y confirmar su capacidad operativa para futuras entregas.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100129 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Contactar a PRIMECARE para revisar los detalles específicos de la planificación de sus entregas y entender por qué se n… |
| 100213 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T2 | Contactar al proveedor AKZE hoy para obtener información detallada sobre la causa de la reprogramación de la cita y con… |
| 100247 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Coordinar con BIOPLEX para obtener detalles específicos sobre el motivo de la reprogramación y los criterios que usan p… |
| 100317 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Contactar al proveedor GREENLEAF para obtener un informe detallado sobre la causa de la reprogramación, específicamente… |
| 100361 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T0 | Contactar al proveedor MEDIQ para confirmar la razón específica detrás del retraso en la entrega y obtener un compromis… |

**Vendor** — clúster de 24 POs, pureza modal 0.88, 3 fuera de firma.

> Recomendación modal: Contactar al proveedor SYNCO para obtener un informe detallado sobre la planificación y el motivo del retraso en el envío de esta PO.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100387 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Contactar al proveedor SYNCO para obtener un informe detallado sobre la planificación y el motivo del retraso en el env… |
| 100063 | is_short_ship | short=True, hot=0, coincide=True, mag=T2 | Contactar al proveedor MEDIQ para obtener un informe detallado sobre la disponibilidad de inventario y la producción ac… |
| 100073 | is_short_ship | short=True, hot=0, coincide=True, mag=T1 | Contactar a Greenleaf para obtener un informe detallado sobre la disponibilidad de inventario y la producción de la PO … |

**Vendor** — clúster de 14 POs, pureza modal 0.86, 2 fuera de firma.

> Recomendación modal: Contactar a Synco para obtener información sobre la disponibilidad de inventario y confirmar si pueden re-emitir las 23 cajas faltantes (80 cajas pedidas - 57 cajas embarcadas) ho…

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100197 | HOT_PO_FLAG | short=True, hot=1, coincide=True, mag=T2 | Contactar al proveedor SYNCO para obtener información específica sobre la disponibilidad de inventario y las razones de… |
| 100302 | HOT_PO_FLAG | short=True, hot=1, coincide=True, mag=T2 | Contactar al proveedor MEDIQ para confirmar la disponibilidad de inventario y obtener un plan de producción que asegure… |

**Vendor** — clúster de 12 POs, pureza modal 0.75, 3 fuera de firma.

> Recomendación modal: Contactar a NOVAPHARM para obtener un desglose detallado de su planificación de rutas que llevó a la reprogramación de la cita de entrega.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100157 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T2 | Contactar a MEDIQ para obtener información específica sobre la causa del retraso en la programación y la reprogramación… |
| 100220 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Contactar a PRIMECARE para obtener un informe detallado sobre la causa del exceso de 27.4 horas en la entrega y la repr… |
| 100236 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, coincide=False, mag=T2 | Contactar a BIOPLEX para obtener un desglose detallado de su planificación de producción actual y la disponibilidad de … |

**Vendor** — clúster de 3 POs, pureza modal 0.67, 1 fuera de firma.

> Recomendación modal: Contactar a VITAGEN hoy para obtener un informe detallado de su inventario actual y la capacidad de producción respecto a la PO 100288.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100288 | is_short_ship | short=True, hot=0, coincide=True, mag=T1 | Contactar a VITAGEN hoy para obtener un informe detallado de su inventario actual y la capacidad de producción respecto… |

**Vendor** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: Contactar a HEALTHCORP para obtener un detalle específico sobre su capacidad de entrega y las razones detrás de la reprogramación de la cita, y confirmar que no ocurrirán más repr…

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100130 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Contactar a HEALTHCORP para obtener el motivo específico que causó el exceso en la reprogramación de la cita y evaluar … |

**Vendor** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: Contactar a AKZE para obtener información detallada sobre su planificación de rutas que llevó a un exceso de 31.2 horas, y confirmar si existen cambios para evitar que se repita e…

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100330 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Contactar a PRIMECARE para obtener información sobre la causa del exceso de 20.8 horas en su proceso de entrega y coord… |

## Lectura

La convergencia intra-etapa es alta pero mayormente *justificada*: en el clúster mayor de Vendor (hipótesis) la pureza modal es ~0.75 —la misma hipótesis de planificación del proveedor sobre POs que comparten firma de evidencia—. El fallo no es la convergencia sino la cola fuera de firma (~1 de cada 6 POs), concentrada en Carrier. La convergencia de `acción inmediata` puede además ser mayor por diseño: las Reglas de concreción de ADR-16 hacen converger la acción al `paso_discriminante` cuando el mecanismo no está confirmado; por eso la firma modal absuelve esa convergencia y solo los POs fuera de firma señalan evidencia ignorada.

## Boceto de solución (insumo para #154)

La homogeneidad residual son POs cuya firma de evidencia difiere de la firma modal de su clúster y que aun así reciben la hipótesis/acción del modo. Un marcador contrastivo determinista, calculado por PO e inyectado al prompt de la llamada de acción, ataca ese mecanismo: declara en qué se aparta el PO del perfil modal de su etapa (por ejemplo «atípico para Vendor: envío incompleto (short-ship)», «PO marcado crítico», «la anotación REASON_DSC discrepa de la etapa medida»). A diferencia de una regla señal -> hipótesis declarativa —que el cierre del Carril-1 mostró de bajo rendimiento (mueve 2/8 POs)—, el marcador no prescribe la conclusión: fuerza al modelo a condicionar sobre la señal que hoy ignora y le deja derivar la hipótesis (coherente con la capa analítica de ADR-16). Es barato (determinista, sin llamada extra) y su superficie de validación es esta misma métrica de fuera de firma. Primer objetivo por impacto: Carrier (la tasa más alta, 30-35%). Queda como boceto; la decisión y su relación con el estadio agéntico del Carril-2 corresponden a #154.

## Reproducir

```bash
# 1) generar el entregable con tier-2 poblado (GASTA API):
python llm_integration.py --mode full --backend openai --action-call
# 2) medir (sin API):
python eval_differentiation.py
```

Fuente: `data/processed/po_output.csv` · agrupación por `stage` · convergencia Jaccard θ=0.25 sobre tokens de contenido · firma de evidencia determinista (`is_short_ship`, `HOT_PO_FLAG`, `llm_coincide_con_reason`, tercil de magnitud).
