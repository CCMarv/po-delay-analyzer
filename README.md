# PO Delay Root Cause Analyzer 

El **PO Delay Root Cause Analyzer** es una herramienta de Inteligencia Artificial diseñada para analizar Órdenes de Compra (PO) retrasadas dentro de la cadena de suministro. El sistema procesa datos logísticos, identifica la etapa exacta donde ocurrió el desvío mediante reglas de negocio avanzadas y genera explicaciones automatizadas junto con acciones recomendadas utilizando un Modelo de Lenguaje de Gran Escala (LLM).

##  Objetivo Final del Proyecto
Construir una plataforma integral que reciba datos transaccionales de órdenes de compra, detecte inconsistencias operativas y actúe como un auditor inteligente que identifique la causa raíz de los retrasos, contrastando los registros manuales del personal con la realidad de los timestamps logísticos.

---

##  Plan de Desarrollo del Proyecto

El proyecto se estructura en **4 fases secuenciales**:

###  Fase 1 — Data Pipeline (Limpieza y Validación) 📍 [ESTADO ACTUAL]
*"Step zero is data cleaning."* Procesamiento de un dataset inicial de 400 filas y 39 columnas que incluye anomalías intencionales (~10% nulos en `TRAILER_ARRIVE_DT`, ~5% timestamps invertidos y ~20% de desajustes en códigos de razón).
* **Carga y Parseo**: Uso de `pandas` con `errors='coerce'` para evitar rupturas por valores nulos (dejándolos como `NaT`).
* **Auditoría de Calidad**: Detección de tiempos invertidos (ej. `CHECKIN_DT` < `TRAILER_ARRIVE_DT`) marcados bajo la flag `_TIMESTAMP_ISSUE` sin eliminar registros.
* **Cálculo de Métricas Clave (Lead Times)**:
  * `yard_wait` = `CHECKIN` - `TRAILER_ARRIVE`
  * `dock_time` = `CHECKOUT` - `CHECKIN`
  * `carrier_lag` = `TRAILER_ARRIVE` - `APPROVED_DT`
* **Output**: DataFrame limpio, con deltas calculados y banderas de calidad, listo como entrada para las siguientes fases.

###  Fase 2 — Clasificación por Etapa (Reglas de Negocio)
Implementación de un clasificador probabilístico basado en prioridades operativas para resolver la multicausalidad en órdenes retrasadas. Las reglas se evalúan de forma independiente y se consolidan según el ciclo de vida del PO:
1. **Reagendamiento**: Modificación de citas (`CURRENT_APPROVED` != `FIRST_APPROVED`).
2. **Carrier Miss**: Retraso del transportista (`TRAILER_ARRIVE` > `APPROVED_DT` + threshold).
3. **Vendor Delay**: Demora del proveedor (`APPROVED_DT` > `STA_DT`).
4. **Yard Congestion**: Cuello de botella en patio (`yard_wait` > 4h).
5. **Dock Backlog**: Retraso en andén (`dock_time` > 6h).
* **Validación**: Contraste de las banderas frente a las alertas reales (165 POs con `IS_LATE = Y`) para auditar el 20% de error/mismatch en el campo manual `REASON_DSC`.

###  Fase 3 — LLM Root Cause (Integración con Claude API)
Auditoría cognitiva de cada orden retrasada mediante el consumo dinámico de LLMs.
* **Prompt Engineering**: Construcción de un prompt enriquecido por fila con los hitos temporales, deltas de la Fase 1 y clasificaciones de la Fase 2.
* **Tratamiento de Urgencias**: Inyección de criticidad explícita para órdenes marcadas con `HOT_PO_FLAG = 1`.
* **Generación de Variables IA**: El LLM añade al dataset final las columnas:
  * `ai_explanation`: Explicación en lenguaje natural del fallo.
  * `ai_action`: Recomendación operativa concreta.
  * *Análisis de Discrepancia*: Diagnóstico de consistencia entre el `REASON_DSC` manual y la lógica de los datos.

###  Fase 4 — Demo Interactiva
Construcción de una interfaz de usuario para el consumo de resultados del negocio.
* **Consulta Individual**: Selector por `PO_NBR` que renderiza el ciclo de vida completo de la orden, resaltando visualmente la etapa del delay, las conclusiones de la IA y el match/mismatch del código manual.
* **Módulo Agregado**: Tableros de control analíticos organizados por Proveedor (`VENDOR_NAME`) o Centro de Distribución (`DC_FACILITY_CD_ABBREV`) para identificar a los actores con mayor impacto negativo en la operación.

---

##  Tecnologías y Variables Principales

* **Lenguaje principal**: Python 3.x
* **Librerías Core**: `pandas`, `numpy` (Próximamente: `Streamlit`/`ipywidgets`, `anthropic`).
* **Variables Críticas de Control**: `PO_NBR`, `VENDOR_NAME`, `CARRIER_PARTY_NAME`, `DC_FACILITY_CD_ABBREV`, `REASON_DSC`, `HOT_PO_FLAG`.

---
*Nota: Este documento refleja el progreso en tiempo real del desarrollo. Actualmente ejecutando tareas de ingeniería de datos en la Fase 1.*
