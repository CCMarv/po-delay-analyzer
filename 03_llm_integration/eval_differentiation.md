# Diferenciación intra-etapa de las recomendaciones tier-2 (#151)

Se mide si POs de la misma etapa reciben recomendaciones diferenciadas, ahora que tier-2 emite señal diferencial (hipótesis + evidencia + paso discriminante + plan). La operacionalización sigue [ADR-16](../documentation/decisiones/ARD-16.md) §Validación/Discriminación: no la diversidad léxica de ADR-15 —dos POs con la misma evidencia deben converger—, sino convergencia léxica intra-etapa leída junto con la covarianza señal -> hipótesis.

Método en dos capas:

1. **Convergencia léxica intra-etapa.** Por etapa, Jaccard sobre tokens de contenido; dos POs convergen si Jaccard >= θ=0.25. Los clústeres se forman por líder/vecindario (cada miembro dentro de θ del líder, sin encadenamiento transitivo). Se mide sobre `llm_hipotesis` y `llm_accion_inmediata`.
2. **Covarianza señal -> hipótesis.** A cada clúster convergente se le fija la firma de evidencia determinista MODAL de sus miembros (`is_short_ship`, `HOT_PO_FLAG`, `llm_coincide_con_reason`; el tercil de magnitud del exceso es señal graduada y no cuenta para la firma). La convergencia con firma modal homogénea es *justificada* (misma evidencia -> misma recomendación) y la **pureza modal** mide esa fracción. El fallo —el clúster que *ignora la evidencia* de ADR-16— son los POs **fuera de firma**: los que reciben la recomendación modal aunque su firma fuerte difiera de la modal.

**Métrica titular:** fracción de POs fuera de firma (evidencia ignorada), reportada junto al paisaje de convergencia (% en clúster, pureza modal). No se usa una tasa de 'clúster sospechoso' porque satura: con clústeres grandes, casi cualquiera incluye algo de variación de señales y quedaría marcado, inflando el fallo.

Supuestos: θ=0.25 se hereda del fixture de ola 1 (calibrado en ADR-16) y se aplica al conjunto completo. En esta corrida `llm_coincide_con_reason` es binaria (149 True / 98 False): no aparece el estado 'no-evaluable'. Población: 247 POs tardíos con tier-2 poblado.

## Campo: hipótesis (`llm_hipotesis`)

POs fuera de firma (evidencia ignorada): **65/247** (26.3%).

| Etapa | n | Jaccard medio | Clústeres conv. | Mayor | % en conv. | Pureza modal | Fuera de firma |
|---|--:|--:|--:|--:|--:|--:|--:|
| Carrier | 40 | 0.160 | 5 | 18 | 77.5% | 0.71 | 9 (22.5%) |
| DC | 37 | 0.225 | 2 | 28 | 81.1% | 0.57 | 13 (35.1%) |
| Indeterminado | 31 | 0.097 | 2 | 9 | 45.2% | 0.64 | 5 (16.1%) |
| Vendor | 139 | 0.174 | 10 | 70 | 94.2% | 0.71 | 38 (27.3%) |

### Clústeres con evidencia ignorada (hipótesis)

**Carrier** — clúster de 18 POs, pureza modal 0.56, 8 fuera de firma.

> Recomendación modal: La falta de planificación adecuada de las rutas del transportista está causando un retraso significativo en la entrega.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100007 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T0 | Fallo en la planificación de rutas del transportista XPO Logistics que provocó el retraso en la entrega. |
| 100138 | HOT_PO_FLAG | short=False, hot=1, coincide=False, mag=T0 | El retraso se debe a una ineficiencia en la planificación de rutas del transportista, lo que llevó a una llegada tardía… |
| 100154 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T2 | Planificación ineficiente de rutas del transportista (Estes Express), lo que provoca retrasos en la entrega. |
| 100256 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T2 | Falta de coordinación en la programación de rutas por parte del transportista. |
| 100285 | HOT_PO_FLAG | short=False, hot=1, coincide=False, mag=T0 | Problemas de planificación de rutas o congestión en la red de Werner Enterprises que provocaron el retraso en la entreg… |
| 100290 | HOT_PO_FLAG | short=False, hot=1, coincide=False, mag=T1 | Problemas en la planificación de rutas o programación del transportista que provocaron el retraso en la llegada al cent… |
| 100343 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, coincide=True, mag=T0 | El mecanismo subyacente es la planificación ineficiente de rutas por parte de UPS Freight, lo que ocasionó un retraso e… |
| 100392 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T0 | La falta de coordinación en la planificación de rutas del transportista (Carrier) llevó a que no se respetara la ventan… |

**Carrier** — clúster de 5 POs, pureza modal 0.80, 1 fuera de firma.

> Recomendación modal: Deficiencia en la planificación de rutas o ejecución del transportista (UPS Freight).

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100278 | HOT_PO_FLAG | short=False, hot=1, coincide=False, mag=T1 | Ineficiencia en la planificación de rutas y ejecución de la entrega por parte de UPS Freight |

**DC** — clúster de 28 POs, pureza modal 0.54, 13 fuera de firma.

> Recomendación modal: Congestión de puertas en el patio del DC llevó al retraso en la descarga

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100355 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Congestión de puertas en el patio del DC llevó al retraso en la descarga |
| 100058 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T2 | Congestión en el patio del DC que retrasa la descarga de los tráileres. |
| 100092 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, coincide=False, mag=T2 | Falta de gestión eficiente de las puertas de descarga en el DC, lo que causó el retraso en las operaciones. |
| 100110 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | La congestión de puertas en el patio del DC es el mecanismo principal que causó el retraso. |
| 100117 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Congestión de puertas en el patio del DC, lo que impidió un flujo eficiente de carga y descarga. |
| 100145 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Congestión en las puertas de carga del DC que causa retraso en el procesamiento. |
| 100202 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Congestión en las puertas del centro de distribución |
| 100216 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | La congestión del patio en el DC es la principal causa del retraso, debido a la falta de puertas disponibles para la de… |
| 100221 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, coincide=False, mag=T1 | Congestión de puertas en el centro de distribución que impidió una descarga eficiente. |
| 100298 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | La congestión en el patio del DC debido a la falta de puertas disponibles provocó el retraso registrado. |
| 100321 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, coincide=False, mag=T1 | La congestión en el patio del DC impidió la entrada oportuna de los tráileres para la descarga. |
| 100357 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Congestión de puertas en el patio del DC |
| 100386 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | La congestión en el patio del DC es la causa principal del retraso, resultado de que no había puertas disponibles para … |

**Indeterminado** — clúster de 9 POs, pureza modal 0.56, 4 fuera de firma.

> Recomendación modal: Si el tiempo de espera en el patio (4.9 horas) es un indicador del retraso del transportista, entonces el mecanismo es un retraso en el transporte.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100312 | HOT_PO_FLAG | short=False, hot=1, coincide=False, mag=T1 | Si el tiempo de espera en el patio (4.9 horas) es un indicador del retraso del transportista, entonces el mecanismo es … |
| 100205 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T0 | Si el tiempo de espera en patio supera un umbral específico que se considera normal (por ejemplo, más de 1 hora), el me… |
| 100242 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T2 | Si el tiempo de espera en patio es significativamente mayor que el promedio, el mecanismo es un fallo de coordinación c… |
| 100260 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T2 | Si el tiempo de espera en patio (1.9 horas) se justifica por la falta de puertas disponibles, el mecanismo responsable … |

**Indeterminado** — clúster de 5 POs, pureza modal 0.80, 1 fuera de firma.

> Recomendación modal: Si se confirma que el retraso fue causado por una reprogramación ineficiente de la cita por parte del proveedor, entonces el mecanismo fue la falta de coordinación temporal en las…

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100206 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T2 | Si el retraso en la reprogramación de la cita se debió a una falta de disponibilidad de carga por parte de VITAGEN, ent… |

**Vendor** — clúster de 70 POs, pureza modal 0.73, 19 fuera de firma.

> Recomendación modal: La falta de capacidad de planificación del proveedor ha causado el retraso en la entrega.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100059 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T2 | El proveedor tuvo problemas de planificación y gestión interna, lo que causó el retraso en la entrega. |
| 100063 | is_short_ship | short=True, hot=0, coincide=True, mag=T2 | Falta de producto debido a problemas en la capacidad de producción del proveedor MEDIQ. |
| 100073 | is_short_ship, llm_coincide_con_reason | short=True, hot=0, coincide=False, mag=T1 | Falta de producto disponible por parte del proveedor GREENLEAF, que resultó en el short ship y el retraso en la entrega. |
| 100129 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | El mecanismo concreto es la planificación inadecuada de las citas de entrega por parte del proveedor. |
| 100130 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | El retraso se debe a la planificación ineficiente de las citas de entrega por parte del proveedor. |
| 100165 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Falta de capacidad del proveedor para manejar la carga de trabajo en el patio de entrega |
| 100188 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T2 | El retraso se debe a una falta de capacidad del proveedor para cumplir con el horario de entrega programado, posiblemen… |
| 100197 | is_short_ship, HOT_PO_FLAG | short=True, hot=1, coincide=True, mag=T2 | La causa del retraso es la falta de inventario disponible por parte del proveedor, SYNCO. |
| 100209 | is_short_ship | short=True, hot=0, coincide=True, mag=T2 | Falta de capacidad de inventario en el proveedor para cumplir con el pedido completo. |
| 100213 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T2 | Problemas de planificación o agenda del proveedor que han llevado a una reprogramación de la cita de entrega. |
| 100247 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Fallo en la planificación logística del proveedor (Vendor) que llevó a la reprogramación de la entrega. |
| 100302 | is_short_ship, HOT_PO_FLAG | short=True, hot=1, coincide=True, mag=T1 | La falta de inventario en el proveedor MEDIQ causó el retraso y el envío incompleto. |
| 100361 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T0 | El mecanismo concreto bajo la etapa diagnosticada es la falta de capacidad de producción del proveedor, que resultó en … |
| 100369 | is_short_ship | short=True, hot=0, coincide=True, mag=T0 | Falta de disponibilidad de inventario en el proveedor GREENLEAF, lo que resultó en un short ship y retraso en la entreg… |
| 100371 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | La falta de atención a las ventanas de cita por parte del proveedor GREENLEAF está causando el retraso en la entrega. |
| 100375 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Fallo en la planificación/logística del proveedor que provocó el retraso en la entrega. |
| 100376 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T2 | Falta de coordinación en la planificación de entrega por parte del proveedor Greenleaf, lo que generó un retraso en el … |
| 100382 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, coincide=False, mag=T2 | El proveedor AKZE no gestionó adecuadamente su capacidad de entrega, lo que resultó en un retraso significativo en la r… |
| 100395 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | La planificación ineficiente de las rutas de entrega del proveedor Healthcorp causó el retraso en las entregas. |

**Vendor** — clúster de 24 POs, pureza modal 0.79, 5 fuera de firma.

> Recomendación modal: La reprogramación de la cita de entrega por parte del proveedor fue resultado de una deficiente gestión de horarios y planificación de rutas.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100044 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T0 | Fallo en la planificación y gestión de agenda del proveedor que causó la reprogramación de la cita. |
| 100168 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Problemas en la planificación de rutas o programación de entregas por parte del proveedor GREENLEAF. |
| 100231 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | El retraso se debe a una deficiente planificación y coordinación del proveedor VITAGEN, que no pudo cumplir con el tiem… |
| 100250 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | La planificación de citas por parte del proveedor fue deficiente, lo que llevó a la pérdida de la ventana de entrega ac… |
| 100317 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Falta de coordinación en la planificación de las entregas por parte de GREENLEAF, resultando en la reprogramación de la… |

**Vendor** — clúster de 15 POs, pureza modal 0.73, 4 fuera de firma.

> Recomendación modal: Falta de producto disponible en el inventario del proveedor SYNCO, lo que causó un short ship

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100101 | llm_coincide_con_reason | short=True, hot=0, coincide=False, mag=T2 | El mecanismo concreto bajo la etapa diagnosticada es la falta de producto en inventario en el proveedor, lo que causó u… |
| 100148 | HOT_PO_FLAG | short=True, hot=1, coincide=True, mag=T2 | El mecanismo concreto es la falta de producto en el inventario del proveedor, lo que impidió cumplir con la orden en su… |
| 100288 | llm_coincide_con_reason | short=True, hot=0, coincide=False, mag=T1 | Falta de producto disponible para completar el pedido en el inventario del proveedor. |
| 100318 | llm_coincide_con_reason | short=True, hot=0, coincide=False, mag=T0 | La causa del retraso es la falta de inventario en el proveedor NOVAPHARM, lo que ha llevado a un short ship. |

**Vendor** — clúster de 8 POs, pureza modal 0.50, 4 fuera de firma.

> Recomendación modal: Planificación ineficiente en la agenda del proveedor

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100053 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, coincide=False, mag=T2 | La planificación de rutas del proveedor fue ineficiente, causando un exceso de tiempo de preparación y despacho de la P… |
| 100079 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T0 | Fallas en la planificación y gestión de tiempo del proveedor PRIMECARE |
| 100220 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | El mecanismo subyacente es la planificación ineficiente de rutas del proveedor, que ha llevado a un retraso significati… |
| 100388 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Problemas en la planificación de rutas y coordinación de salidas del proveedor |

**Vendor** — clúster de 4 POs, pureza modal 0.50, 2 fuera de firma.

> Recomendación modal: El proveedor no gestionó adecuadamente la programación de las salidas de mercancía, lo que resultó en un retraso en el envío.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100159 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | El proveedor tuvo problemas en su planificación de rutas o programación interna, lo que llevó al retraso en el envío. |
| 100259 | is_short_ship | short=True, hot=0, coincide=True, mag=T2 | Falta de inventario en el proveedor HEALTHCORP, lo que resultó en un envío incompleto y un retraso significativo. |

**Vendor** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: El retraso se debe a problemas de planificación en las entregas del proveedor SYNCO, que resultan en un exceso de 17.1 horas.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100211 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T1 | La reprogramación de la cita se debe a un problema en la planificación o agenda del proveedor que ha llevado a un exces… |

**Vendor** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: El retraso fue causado por una inadecuada gestión de citas y programación por parte del proveedor, que resultó en un exceso de tiempo que no se relaciona con problemas de inventar…

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100157 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T2 | La programación ineficiente por parte del proveedor MEDIQ, que llevó a una reprogramación de la entrega y a un exceso d… |

**Vendor** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: El mecanismo bajo la etapa diagnosticada es la deficiencia en la capacidad de producción o la ineficiencia operativa del proveedor BIOPLEX.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100326 | is_short_ship, HOT_PO_FLAG, llm_coincide_con_reason | short=True, hot=0, coincide=True, mag=T2 | El mecanismo concreto bajo la etapa diagnosticada es un problema de capacidad o disponibilidad de producto en el provee… |

**Vendor** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: Fallas en la planificación y programación de la producción del proveedor SYNCO, que no cumplieron con los tiempos de entrega acordados a pesar de tener el inventario disponible.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100246 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T2 | El proveedor experimentó problemas logísticos que llevaron a un retraso en la entrega, a pesar de tener el inventario n… |

## Campo: acción inmediata (`llm_accion_inmediata`)

POs fuera de firma (evidencia ignorada): **51/247** (20.6%).

| Etapa | n | Jaccard medio | Clústeres conv. | Mayor | % en conv. | Pureza modal | Fuera de firma |
|---|--:|--:|--:|--:|--:|--:|--:|
| Carrier | 40 | 0.174 | 4 | 23 | 85.0% | 0.74 | 9 (22.5%) |
| DC | 37 | 0.130 | 4 | 10 | 54.1% | 0.60 | 8 (21.6%) |
| Indeterminado | 31 | 0.077 | 5 | 4 | 38.7% | 0.75 | 3 (9.7%) |
| Vendor | 139 | 0.143 | 16 | 35 | 86.3% | 0.74 | 31 (22.3%) |

### Clústeres con evidencia ignorada (acción inmediata)

**Carrier** — clúster de 23 POs, pureza modal 0.61, 9 fuera de firma.

> Recomendación modal: Contactar a XPO Logistics para obtener un informe específico sobre los motivos del retraso en la entrega de esta PO, centrándose en la planificación de rutas.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100007 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T0 | Contactar a XPO Logistics para obtener un informe específico sobre los motivos del retraso en la entrega de esta PO, ce… |
| 100026 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T1 | Contactar a Estes Express para obtener un informe específico sobre la operación del transporte en esta PO para entender… |
| 100138 | HOT_PO_FLAG | short=False, hot=1, coincide=False, mag=T0 | Contactar a Old Dominion para revisar la planificación de rutas y obtener detalles sobre la causa del retraso específic… |
| 100154 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T2 | Contactar a Estes Express para obtener un informe detallado sobre la planificación de rutas y operaciones de entrega de… |
| 100256 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T2 | Contactar a J.B. Hunt para obtener un informe detallado de la programación de la ruta y las razones del retraso en la e… |
| 100278 | HOT_PO_FLAG | short=False, hot=1, coincide=False, mag=T1 | Contactar a UPS Freight para obtener un informe detallado sobre la planificación de la ruta y las decisiones logísticas… |
| 100290 | HOT_PO_FLAG | short=False, hot=1, coincide=False, mag=T1 | Contactar a XPO Logistics para obtener un informe detallado sobre la planificación de la ruta y los tiempos de llegada … |
| 100343 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, coincide=True, mag=T0 | Contactar a UPS Freight hoy para obtener detalles sobre la planificación de rutas y el motivo del retraso en esta PO. |
| 100392 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T0 | Contactar a Schneider National para obtener una explicación detallada del retraso y confirmar sus procedimientos de pla… |

**DC** — clúster de 10 POs, pureza modal 0.60, 4 fuera de firma.

> Recomendación modal: Coordinar con el equipo de operaciones del DC para obtener un informe detallado sobre la gestión de puertas y tiempos de espera en el patio hoy mismo.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100202 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Coordinar con el equipo de operaciones del Charlotte DC para confirmar el nivel de congestión actual en las puertas y o… |
| 100298 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Coordinar con el equipo del DC para que se revisen las disponibilidades de puertas en tiempo real y se solucione la con… |
| 100321 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, coincide=False, mag=T1 | Coordinar con el personal del Kansas City DC para obtener un informe detallado sobre las condiciones del patio y la dis… |
| 100386 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Coordinar con el equipo del Kansas City DC para obtener un informe detallado sobre la situación de las puertas disponib… |

**DC** — clúster de 6 POs, pureza modal 0.67, 2 fuera de firma.

> Recomendación modal: Contactar al supervisor del Dallas DC para obtener un informe detallado sobre la disponibilidad de puertas y confirmar si hay patrones de congestión recurrentes.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100153 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T2 | Contactar al equipo del Charlotte DC para obtener un informe específico sobre la disponibilidad de puertas y la situaci… |
| 100357 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Contactar al supervisor del patio del Atlanta DC para obtener datos específicos sobre la disponibilidad de puertas dura… |

**DC** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: Coordinar con el equipo del Kansas City DC para asegurar que se asignen suficientes puertas para la descarga hoy y evitar congestiones futuras.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100123 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, coincide=True, mag=T2 | Contactar al supervisor del Kansas City DC para verificar la cantidad de puertas disponibles y la programación de citas… |

**DC** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: Contactar a la operación del DC de Los Ángeles para obtener el número exacto de puertas disponibles y la cantidad de camiones en espera en este momento.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100216 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Coordinar con el equipo del DC para obtener el número exacto de puertas disponibles en este momento y la razón de la co… |

**Indeterminado** — clúster de 4 POs, pureza modal 0.75, 1 fuera de firma.

> Recomendación modal: Contactar al transportista XPO Logistics para obtener el tiempo promedio de espera en patio en este DC y contrastarlo con el tiempo observado. Si el tiempo de espera excede el pro…

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100021 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Contactar a XPO Logistics para obtener datos específicos sobre el proceso de descarga: si el tiempo de descarga excede … |

**Indeterminado** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: Contactar al proveedor NOVAPHARM para obtener detalles sobre la necesidad de la reprogramación y si hubo problemas en la cita original; si la reprogramación no era necesaria, toma…

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100206 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T2 | Contactar a VITAGEN para obtener información sobre la causa de la reprogramación de la cita. Si la causa obedece a prob… |

**Indeterminado** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: Contactar a YRC Worldwide para obtener confirmación sobre el estado del tráiler, ya que si el problema está relacionado con el equipo, se debe tomar medidas para asegurar que no v…

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100312 | HOT_PO_FLAG | short=False, hot=1, coincide=False, mag=T1 | Contactar a YRC Worldwide para obtener detalles sobre la causa del retraso en la llegada del tráiler y confirmar si se … |

**Vendor** — clúster de 35 POs, pureza modal 0.83, 6 fuera de firma.

> Recomendación modal: Contactar al proveedor NOVAPHARM para obtener un informe específico sobre los motivos de la reprogramación de la cita y confirmar si hay problemas en su planificación de rutas.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100053 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, coincide=False, mag=T2 | Contactar a BIOMED para obtener su cronograma de entrega y confirmar si están priorizando la PO 100053; evaluar si hay … |
| 100067 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, coincide=False, mag=T0 | Contactar al proveedor SYNCO para obtener un informe detallado sobre el estado de su planificación de entregas y las ca… |
| 100130 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Contactar a HEALTHCORP para obtener detalles sobre la planificación de la entrega y entender las razones detrás de la r… |
| 100213 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T2 | Contactar al proveedor AKZE para obtener detalles precisos sobre los motivos de la reprogramación y confirmar si se pue… |
| 100220 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Contactar al proveedor PRIMECARE para obtener un informe detallado sobre la planificación de rutas y capacidad de entre… |
| 100231 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Contactar al proveedor VITAGEN para obtener un informe de la planificación de rutas y disponibilidad de recursos; si el… |

**Vendor** — clúster de 20 POs, pureza modal 0.60, 8 fuera de firma.

> Recomendación modal: Contactar a GREENLEAF para obtener un informe de inventario detallado, verificando la disponibilidad de las cajas faltantes.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100073 | llm_coincide_con_reason | short=True, hot=0, coincide=False, mag=T1 | Contactar a GREENLEAF para obtener un informe de inventario detallado, verificando la disponibilidad de las cajas falta… |
| 100101 | llm_coincide_con_reason | short=True, hot=0, coincide=False, mag=T2 | Contactar a BIOMED para obtener información detallada sobre la disponibilidad de 48 cajas faltantes y el motivo específ… |
| 100148 | HOT_PO_FLAG | short=True, hot=1, coincide=True, mag=T2 | Contactar al proveedor GREENLEAF para obtener un informe detallado sobre el inventario disponible y confirmar si hay má… |
| 100197 | HOT_PO_FLAG | short=True, hot=1, coincide=True, mag=T2 | Contactar a SYNCO para obtener un informe inmediato sobre la disponibilidad de inventario para la PO 100197 y la razón … |
| 100288 | llm_coincide_con_reason | short=True, hot=0, coincide=False, mag=T1 | Contactar a VITAGEN hoy para obtener el estatus del inventario de las 24 cajas faltantes y determinar si hay disponibil… |
| 100302 | HOT_PO_FLAG | short=True, hot=1, coincide=True, mag=T1 | Contactar a MEDIQ para confirmar la disponibilidad exacta de las 50 cajas faltantes y obtener un compromiso de envío in… |
| 100317 | is_short_ship, HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Contactar a GREENLEAF para obtener un informe detallado sobre las razones de la reprogramación de la cita y las medidas… |
| 100318 | llm_coincide_con_reason | short=True, hot=0, coincide=False, mag=T0 | Contactar a NOVAPHARM para obtener la confirmación de disponibilidad del inventario faltante (47 cajas) y establecer un… |

**Vendor** — clúster de 19 POs, pureza modal 0.74, 5 fuera de firma.

> Recomendación modal: Contactar al representante de HEALTHCORP para obtener detalles específicos sobre la causa de la reprogramación y confirmar su capacidad de cumplir con las futuras entregas en tiem…

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100044 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T0 | Contactar a GREENLEAF para obtener la confirmación de la disponibilidad y la capacidad para cumplir con futuras entrega… |
| 100079 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T0 | Contactar al proveedor PRIMECARE hoy para obtener detalles sobre la causa de la reprogramación y confirmar su capacidad… |
| 100165 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Contactar a PRIMECARE para revisar su capacidad actual y obtener confirmación sobre su capacidad de entrega en días pic… |
| 100188 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T2 | Contactar a HEALTHCORP para confirmar si hubo problemas de capacidad o congestión en su planta que causaron el retraso,… |
| 100247 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Contactar a BIOPLEX hoy para que proporcionen detalles sobre la causa de la reprogramación de la entrega y confirmar su… |

**Vendor** — clúster de 11 POs, pureza modal 0.73, 3 fuera de firma.

> Recomendación modal: Contactar a PRIMECARE para obtener un informe detallado sobre la planificación de la entrega y las razones específicas del retraso de 37.1 horas.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100157 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T2 | Contactar a MEDIQ hoy para obtener un desglose de su planificación y conocer las razones específicas de la reprogramaci… |
| 100250 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Contactar al proveedor AKZE para obtener un informe sobre la planificación de citas y coordinar medidas para mejorar la… |
| 100382 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, coincide=False, mag=T2 | Contactar a AKZE para obtener un informe detallado sobre el por qué del retraso de 87.0 horas y los próximos pasos para… |

**Vendor** — clúster de 7 POs, pureza modal 0.71, 2 fuera de firma.

> Recomendación modal: Contactar a MEDIQ para obtener información detallada sobre las causas del retraso y si hay algún problema recurrente en la programación de entregas.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100246 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T2 | Contactar al proveedor MEDIQ para obtener información específica sobre los problemas logísticos que causaron el retraso… |
| 100387 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Contactar al proveedor SYNCO para obtener una explicación detallada sobre las causas de la demora en el envío y confirm… |

**Vendor** — clúster de 4 POs, pureza modal 0.50, 2 fuera de firma.

> Recomendación modal: Contactar a NOVAPHARM para obtener un desglose de sus horarios de entrega y confirmación de su capacidad de planificación hoy mismo.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100262 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Coordinar hoy con AKZE para obtener confirmación sobre su capacidad de procesamiento y asegurar que se respete la próxi… |
| 100395 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T1 | Contactar a Healthcorp para obtener detalles sobre su planificación de rutas y horarios de carga, a fin de identificar … |

**Vendor** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: Contactar al proveedor SYNCO para obtener la programación exacta de sus envíos actuales y confirmar si hay alguna congestión o problema de capacidad que impida cumplir con los pla…

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100361 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T0 | Contactar al proveedor MEDIQ para confirmar su capacidad de producción y disponibilidad para cumplir con futuros envíos… |

**Vendor** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: Contactar al proveedor MEDIQ para obtener un análisis detallado de las causas de la planificación inadecuada y acciones correctivas a implementar hoy.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100388 | llm_coincide_con_reason | short=False, hot=0, coincide=False, mag=T0 | Contactar al proveedor VITAGEN hoy para obtener detalles sobre su planificación de rutas y logística de despacho para e… |

**Vendor** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: Contactar a PRIMECARE para solicitar la revisión de su planificación de rutas y gestión de envíos a partir de la PO 100129.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100159 | HOT_PO_FLAG, llm_coincide_con_reason | short=False, hot=1, coincide=True, mag=T1 | Contactar a MEDIQ para solicitar la revisión de su planificación de rutas y conocer las causas específicas de la demora… |

**Vendor** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: Contactar a GREENLEAF para obtener información detallada sobre la razón del retraso en la reprogramación de la cita. Si la causa se debe a problemas de planificación, solicitar un…

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100292 | llm_coincide_con_reason | short=False, hot=0, coincide=True, mag=T0 | Contactar a PRIMECARE hoy para obtener un desglose de las razones detrás de la reprogramación de la cita. Si la causa s… |

**Vendor** — clúster de 2 POs, pureza modal 0.50, 1 fuera de firma.

> Recomendación modal: Contactar al proveedor SYNCO para obtener un compromiso claro sobre la mejora en la planificación de las próximas entregas y revisar si hay un calendario de entregas actualizado.

| PO fuera de firma | difiere en | firma de evidencia | recomendación |
|---|---|---|---|
| 100371 | HOT_PO_FLAG | short=False, hot=1, coincide=True, mag=T1 | Contactar al proveedor GREENLEAF para obtener un compromiso claro respecto a sus futuras entregas y la gestión de citas… |

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
