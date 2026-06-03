# PO Delay Root Cause Analyzer 

El **PO Delay Root Cause Analyzer** es una herramienta de Inteligencia Artificial diseñada para analizar Órdenes de Compra (PO) retrasadas dentro de la cadena de suministro. El sistema procesa datos logísticos, identifica la etapa exacta donde ocurrió el desvío mediante reglas de negocio avanzadas y genera explicaciones automatizadas junto con acciones recomendadas utilizando un Modelo de Lenguaje de Gran Escala (LLM).

##  Objetivo Final del Proyecto
Construir una plataforma integral que reciba datos transaccionales de órdenes de compra, detecte inconsistencias operativas y actúe como un auditor inteligente que identifique la causa raíz de los retrasos, contrastando los registros manuales del personal con la realidad de los timestamps logísticos.

---

##  Plan de Desarrollo del Proyecto

El proyecto se estructura en **4 fases secuenciales**:

###  Fase 1 — Data Pipeline (Limpieza y Validación) `[ESTADO ACTUAL]`

* Procesamiento de un dataset inicial de 400 filas y 39 columnas que incluye anomalías intencionales.
* "Cargar el CSV, limpiar timestamps, validar datos. EDA: cuantos POs tienen delay? Distribucion por vendor/DC."

* **Carga y Parseo**: Uso de `pandas` con `errors='coerce'` para evitar rupturas por valores nulos (dejándolos como `NaT`).
* **Auditoría de Calidad**: Detección de tiempos invertidos (ej. `CHECKIN_DT` < `TRAILER_ARRIVE_DT`) marcados bajo la flag `_TIMESTAMP_ISSUE` sin eliminar registros.
* **Cálculo de Métricas Clave (Lead Times)**:
  * `yard_wait` = `CHECKIN` - `TRAILER_ARRIVE`
  * `dock_time` = `CHECKOUT` - `CHECKIN`
  * `carrier_lag` = `TRAILER_ARRIVE` - `APPROVED_DT`
* **Output**: DataFrame limpio, con deltas calculados y banderas de calidad, listo como entrada para las siguientes fases.

###  Fase 2 — Clasificación por Etapa (Reglas de Negocio)
Implementación de un clasificador probabilístico basado en prioridades operativas para resolver la multicausalidad en órdenes retrasadas. Las reglas se evalúan de forma independiente y se consolidan según el ciclo de vida del PO. 
"Implementar reglas que asignan vendor/carrier/DC a cada PO. Comparar con REASON_DSC. Documentar matches vs mismatches".

###  Fase 3 — LLM Root Cause (Integración con API)
Auditoría cognitiva de cada orden retrasada mediante el consumo dinámico de LLMs.
* **Prompt Engineering**: Construcción de un prompt enriquecido por fila con los hitos temporales de las fases 1 y 2.
"Disenar prompt, generar root cause explanations para todos los POs delayed. Asignar severidad. Primera evaluacion".

###  Fase 4 — Demo Interactiva + Evaluación Final
Construcción de una interfaz de usuario para el consumo de resultados del negocio.
"Construir notebook/app demo: seleccionar PO > ver timeline, causa, explicacion. Medir metricas. Presentar hallazgos."

---

##  Tecnologías y Variables Principales

* **Lenguaje principal**: Python 3.x
* **Librerías Core**: `pandas`, `numpy` (Próximamente: `Streamlit`/`ipywidgets`, `anthropic`).
* **Variables Críticas de Control**: `PO_NBR`, `VENDOR_NAME`, `CARRIER_PARTY_NAME`, `DC_FACILITY_CD_ABBREV`, `REASON_DSC`, `HOT_PO_FLAG`.

---
*Nota: Este documento refleja el progreso en tiempo real del desarrollo. Actualmente ejecutando tareas de ingeniería de datos en la Fase 1.*
