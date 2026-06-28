# Benchmark de calidad de explicación del LLM — 20 POs (#94)

Métrica del mentor *LLM Explanation Quality* (README §6). Muestra estratificada 8/4/4/4 (Vendor/Carrier/Indeterminado/DC), semilla `42` (reproducible; la reusa #99). Backend: el oficial del entregable.

## Criterio (binario por PO; PASA si cumple los 3)
- **(a) etapa correcta:** nombra la etapa = `stage_primary`. Para `Indeterminado`, acierta si lo declara indeterminado (no si copia la etapa del reason code).
- **(b) cuantifica el delay:** cita una cifra y coincide con `delay_days_calc`.
- **(c) acción viable:** nombra responsable y es operable (NO genérica). *Validación humana.*

## Veredicto (validado a mano)
(a) etapa: 19/20 · (b) cuantifica: 20/20 · (c) acción viable: 13/20 · **PASA (a&b&c): 13/20**.

| PO | etapa | delay (d) | REASON_DSC | explicación LLM | acción LLM | (a) | (b) | (c)? | veredicto |
|---|---|--:|---|---|---|:--:|:--:|:--:|:--:|
| 100154 | Carrier | 1.19 | Carrier delivery delay | La etapa exacta del retraso es Carrier, con un retraso cuantificado de 1.19 días. La evidencia coincide con el REASON_DSC del DC, que indica un retraso en la entrega por parte del transportista. No hay agravantes como hot PO o short ship. | El transportista, Estes Express, debe revisar sus procesos de entrega para evitar futuros retrasos y asegurar que se cumplan las fechas prometidas. | ✅ | ✅ | ❌ | no pasa |
| 100278 | Carrier | 1.24 | Weather/road conditions | La etapa exacta del retraso es Carrier, con un retraso cuantificado de 1.24 días. La evidencia no coincide con el REASON_DSC del DC, que menciona condiciones climáticas y de carretera, mientras que el exceso del transportista fue de 29.7 horas. Además, se trata de un Hot PO. | Contactar al transportista UPS Freight para investigar las causas del retraso y asegurar que se tomen medidas correctivas para evitar futuros incidentes, asignando esta tarea al equipo de logística del DC. | ✅ | ✅ | ❌ | no pasa |
| 100146 | Carrier | 1.16 | Equipment/trailer issue | La etapa exacta del retraso es Carrier, con un retraso cuantificado de 1.16 días. La evidencia no coincide con el REASON_DSC del DC, que menciona un problema de equipo/tráiler, mientras que el retraso se clasifica como causado por el transportista. No hay agravantes, ya que no es un hot PO ni un short ship. | El transportista, XPO Logistics, debe investigar y resolver el problema de equipo/tráiler que causó el retraso y asegurar que se tomen medidas para evitar futuros incidentes similares. | ✅ | ✅ | ✅ | **PASA** |
| 100229 | Carrier | 0.35 | Equipment/trailer issue | La etapa exacta del retraso es Carrier, con un retraso cuantificado de 0.35 días. La evidencia no coincide con el REASON_DSC del DC, que menciona un problema con el equipo/tráiler. No hay agravantes como hot PO o short ship. | El transportista, Old Dominion, debe investigar y resolver el problema del equipo/tráiler que causó el retraso en la entrega. | ✅ | ✅ | ✅ | **PASA** |
| 100185 | DC | 0.75 | Yard congestion - no available door | La etapa exacta del retraso es DC, con un retraso cuantificado de 0.75 días. La evidencia coincide con el REASON_DSC del DC, que menciona congestión en el patio debido a la falta de puertas disponibles. No hay agravantes como hot PO o short ship. | El equipo del DC debe optimizar la gestión del patio y asegurar que haya puertas disponibles para evitar congestiones futuras. | ✅ | ✅ | ✅ | **PASA** |
| 100217 | DC | 0.04 | Dock processing backlog | La etapa exacta del retraso es DC, con un retraso de 0.04 días. La evidencia coincide con el REASON_DSC del DC, que indica un 'Dock processing backlog'. No hay agravantes como hot PO o short ship. | El equipo del DC debe revisar y optimizar el proceso de descarga para reducir el backlog en el muelle y evitar retrasos futuros. | ✅ | ✅ | ✅ | **PASA** |
| 100092 | DC | 0.06 | Yard congestion - no available door | La etapa exacta del retraso es el DC, con un retraso cuantificado de 0.06 días. La evidencia coincide con el REASON_DSC del DC, que indica congestión en el patio debido a la falta de puertas disponibles. No hay agravantes, ya que aunque es una Hot PO, el retraso es mínimo. | El equipo del DC debe gestionar mejor la asignación de puertas para evitar congestiones en el patio, asegurando que haya disponibilidad para futuras entregas. | ✅ | ✅ | ✅ | **PASA** |
| 100324 | DC | 0.04 | Yard congestion - no available door | La etapa exacta del retraso es DC, con un retraso cuantificado de 0.04 días. La evidencia coincide con el REASON_DSC del DC, que indica congestión en el patio debido a la falta de puertas disponibles. No hay agravantes como hot PO o short ship. | El equipo del DC debe gestionar mejor la asignación de puertas para evitar congestiones en el patio, asegurando que haya disponibilidad para futuras entregas. | ✅ | ✅ | ✅ | **PASA** |
| 100338 | Indeterminado | 0.40 | Not applicable | La etapa exacta del retraso es indeterminada, ya que no se puede atribuir a un solo responsable. Se registró un retraso de 0.40 días. La evidencia no coincide con el REASON_DSC del DC, que es 'Not applicable'. No hay agravantes como hot PO o short ship. | Se recomienda que el equipo del DC revise los procesos de recepción y descarga para identificar posibles mejoras en la eficiencia, dado que no se identificó un responsable claro del retraso. | ✅ | ✅ | ✅ | **PASA** |
| 100367 | Indeterminado | 0.27 | Not applicable | La etapa exacta del retraso es indeterminada, ya que el retraso cuantificado es de 0.27 días. La evidencia no coincide con el REASON_DSC del DC, que es 'Not applicable'. No hay agravantes como hot PO o short ship. | El equipo del DC debe revisar el proceso de check-in para identificar posibles mejoras en la eficiencia de la descarga, dado que el tiempo de descarga fue de 3.7 horas. | ✅ | ✅ | ✅ | **PASA** |
| 100062 | Indeterminado | 0.04 | Not applicable | La etapa exacta del retraso es indeterminada, con un retraso cuantificado de 0.04 días. La evidencia no coincide con el REASON_DSC del DC, que es 'Not applicable'. No hay agravantes como hot PO o short ship. | El proveedor BIOPLEX debe revisar sus procesos de entrega para asegurar que las próximas entregas se realicen dentro del horario prometido. | ✅ | ✅ | ❌ | no pasa |
| 100182 | Indeterminado | 4.41 | Vendor delayed shipment | La etapa exacta del retraso es Vendor, con un retraso de 4.41 días. La evidencia coincide con el REASON_DSC del DC, que indica un 'Vendor delayed shipment'. No hay agravantes como hot PO o short ship. | El proveedor MEDIQ debe revisar y mejorar su proceso de envío para evitar futuros retrasos en las entregas programadas. | ❌ | ✅ | ❌ | no pasa |
| 100197 | Vendor | 5.64 | Rescheduled by vendor | La etapa exacta del retraso es Vendor, con un retraso de 5.64 días. La evidencia coincide con el REASON_DSC del DC, que indica que el retraso fue 'Rescheduled by vendor'. Además, hay agravantes, ya que se trata de un hot PO y un short ship. | El proveedor SYNCO debe revisar sus procesos de programación y cumplimiento de entregas para evitar futuros retrasos. Se recomienda establecer un plan de contingencia para cumplir con las fechas prometidas en pedidos urgentes. | ✅ | ✅ | ✅ | **PASA** |
| 100158 | Vendor | 2.77 | Rescheduled by vendor | La etapa exacta del retraso es Vendor, con un retraso cuantificado de 2.77 días. La evidencia no coincide con el REASON_DSC del DC, que indica 'Rescheduled by vendor'. No hay agravantes como hot PO o short ship. | El proveedor NOVAPHARM debe mejorar la planificación de sus envíos para evitar reprogramaciones en el futuro. | ✅ | ✅ | ❌ | no pasa |
| 100366 | Vendor | 4.04 | Rescheduled by vendor | La etapa exacta del retraso es Vendor, con un retraso de 4.04 días. La evidencia coincide con el REASON_DSC del DC, que indica que la cita fue reprogramada por el proveedor. No hay agravantes como hot PO o short ship. | El proveedor SYNCO debe mejorar la planificación y cumplimiento de las fechas de entrega para evitar reprogramaciones futuras. | ✅ | ✅ | ❌ | no pasa |
| 100087 | Vendor | 5.24 | Vendor delayed shipment | La etapa exacta del retraso es Vendor, con un retraso cuantificado de 5.24 días. La evidencia coincide con el REASON_DSC del DC, que indica un 'Vendor delayed shipment'. No hay agravantes como hot PO o short ship. | Solicitar al proveedor GREENLEAF una revisión de sus procesos de envío para evitar futuros retrasos, y establecer un plan de acción para mejorar la puntualidad en las entregas. | ✅ | ✅ | ✅ | **PASA** |
| 100063 | Vendor | 5.86 | Rescheduled by vendor | La etapa exacta del retraso es Vendor, con un retraso de 5.86 días. La evidencia coincide con el REASON_DSC del DC, que indica que fue 'Rescheduled by vendor'. Además, hay un agravante, ya que se trata de un short ship. | El proveedor MEDIQ debe revisar su proceso de programación y asegurar que las entregas se realicen en las fechas prometidas para evitar futuros retrasos. | ✅ | ✅ | ❌ | no pasa |
| 100113 | Vendor | 4.45 | Rescheduled by vendor | La etapa exacta del retraso es Vendor, con un retraso de 4.45 días. La evidencia coincide con el REASON_DSC del DC, que indica que la cita fue reprogramada por el proveedor. Además, hay un agravante ya que se trata de un short ship. | El proveedor AKZE debe revisar su proceso de envío y asegurar que las futuras entregas cumplan con las fechas prometidas y la cantidad completa de productos. | ✅ | ✅ | ✅ | **PASA** |
| 100318 | Vendor | 2.86 | nan | La etapa exacta del retraso es Vendor, con un retraso de 2.86 días. La evidencia no coincide con el REASON_DSC del DC, ya que no se registró un motivo específico. Además, hay un agravante, ya que se trata de un short ship. | El proveedor NOVAPHARM debe investigar la causa del envío incompleto y asegurar que los próximos envíos cumplan con las cantidades prometidas. | ✅ | ✅ | ✅ | **PASA** |
| 100157 | Vendor | 5.24 | Rescheduled by vendor | La etapa exacta del retraso es Vendor, con un retraso de 5.24 días. La evidencia coincide con el REASON_DSC del DC, que indica que la cita fue reprogramada por el proveedor. Además, se trata de una Hot PO, lo que agrava la situación. | Solicitar al proveedor MEDIQ una explicación detallada del retraso y un plan de acción para evitar futuros incumplimientos en entregas urgentes. | ✅ | ✅ | ✅ | **PASA** |


## Veredicto de (c) — razonamiento (validado a mano)
Criterio: (c) pasa solo si la acción es **coherente con el reason** (no pide investigar lo
que el reason ya explica) **y operable** (no “revisar/mejorar procesos” a secas). Falla si
es genérica o incoherente.

- **100154** ❌ — “revisar procesos de entrega” genérico
- **100278** ❌ — incoherente: reason "Weather/road conditions" ya da la causa; pide "investigar". Además, clima no es culpa atribuible al carrier
- **100146** ✅ — coherente: un fallo de equipo concreto sí amerita investigar/resolver
- **100229** ✅ — misma lógica (equipo/tráiler)
- **100185** ✅ — ataca la causa dada (puertas disponibles vs congestión de patio)
- **100217** ✅ — específico al backlog de descarga
- **100092** ✅ — coherente con la congestión (asignación de puertas); delay mínimo, acción algo desproporcionada pero pertinente
- **100324** ✅ — igual que 100092 (acción idéntica)
- **100338** ✅ — coherente con la indeterminación: reconoce que no hay responsable claro y propone revisión exploratoria
- **100367** ✅ — ancla en el dato (descarga 3.7h)
- **100062** ❌ — incoherente: etapa Indeterminado pero la acción culpa al proveedor; contradice la propia explicación
- **100182** ❌ — hereda el error de (a): asume Vendor (etapa real Indeterminado) y la acción es genérica
- **100197** ✅ — plan de contingencia para pedidos urgentes (coherente con hot PO)
- **100158** ❌ — “mejorar la planificación” genérico
- **100366** ❌ — genérico (casi idéntico a 100158)
- **100087** ✅ — “solicitar revisión + establecer plan de acción”: operable
- **100063** ❌ — genérico; ignora el short ship
- **100113** ✅ — coherente: atiende retraso + cantidad completa (short ship)
- **100318** ✅ — coherente: reason ausente (nan), aquí "investigar" SÍ procede. Contraste con 100278
- **100157** ✅ — solicitar explicación + plan para entregas urgentes (coherente con hot PO)

## Resultado

### Checks objetivos (pre-evaluados automáticamente)
- **(a) etapa correcta: 19/20.** Único fallo: **PO 100182** (etapa `Indeterminado`, REASON
  humano "Vendor delayed shipment", delay 4.41 d): el LLM nombró la etapa como "Vendor" en
  vez de declararla indeterminada — copió el reason code. Es exactamente el patrón anotado
  en #95: cuando la clasificación es Indeterminado, el reason code no puede "cuadrar" con
  ninguna etapa concreta, y el modelo tiende a adoptar la del reason. Los otros tres
  Indeterminado (100338/100367/100062) sí se declararon indeterminados. Se afina en #95/#99.
- **(b) cuantifica el delay: 20/20.** Todas citan la cifra dada (sin alucinación). La
  instrucción de #91 ("cita la cifra exacta") se cumple de forma consistente.

### Check (c) acción viable: 13/20 (validado a mano)
Criterio aplicado: coherencia reason↔acción + operabilidad. Fallan 7: genéricas (100154,
100158, 100366, 100063) o incoherentes (100278 investiga lo que el reason ya explica;
100062 culpa al vendor pese a etapa Indeterminado; 100182 hereda el error de (a)). El
contraste **100278 vs 100318** resume el problema: mismo verbo "investigar", coherente solo
cuando el reason está vacío (100318), redundante cuando el reason ya da la causa (100278).

### Veredicto final: PASA 13/20 → equivalente 3.25/5
Por debajo de la meta del mentor (**4/5 = 80%**; aquí 65%). El cuello de botella NO es la
clasificación (a: 19/20) ni la cuantificación (b: 20/20), sino la **calidad de la acción**
(c: 13/20). Fallan los mismos 7 que (c), más nada nuevo por (a) (100182 ya contaba).

### Lectura para #99 (few-shot)
La debilidad del prompt zero-shot no está en (a)/(b) —que ya cumplen holgadamente— sino en
la **genericidad de las acciones** (la queja del roadmap #126). Es justo lo que #99 debe
atacar con few-shot, usando este mismo benchmark (semilla 42) como métrica de comparación.