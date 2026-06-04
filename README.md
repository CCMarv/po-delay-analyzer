# PO Delay Root Cause Analyzer 

El **PO Delay Root Cause Analyzer** es una herramienta de Inteligencia Artificial diseñada para analizar Órdenes de Compra (PO) retrasadas dentro de la cadena de suministro. El sistema procesa datos logísticos, identifica la etapa exacta donde ocurrió el desvío mediante reglas de negocio avanzadas y genera explicaciones automatizadas junto con acciones recomendadas utilizando un Modelo de Lenguaje de Gran Escala (LLM).

##  Objetivo Final del Proyecto
Construir una plataforma integral que reciba datos transaccionales de órdenes de compra, detecte inconsistencias operativas y actúe como un auditor inteligente que identifique la causa raíz de los retrasos, contrastando los registros manuales del personal con la realidad de los timestamps logísticos.

---

##  Estructura del Proyecto

El repositorio está organizado siguiendo el orden cronológico de las cuatro etapas del ciclo de vida del proyecto, facilitando el seguimiento del progreso desde la investigación hasta el despliegue:

```text
├── documentation/            # Archivos de texto, PDFs y requerimientos
│   └── requirements.txt      # Dependencias y librerías del proyecto
│   └──kickoff_po_root_cause  # Especificaciones del proyecto
├── 01_data_pipeline_and_eda/ # Etapa 1: Análisis exploratorio y limpieza de datos
│   └── data_pipeline.ipynb   # Notebook de data pipeline
│   └── eda_analysis.ipynb    # Notebook de Análisis Exploratorio de Datos
├── 02_clasif_reglas_negocio/ # Etapa 2: Clasificación por etapa (reglas de negocio)
│   ├── clasif_etapa.ipynb    # Experimentación del flujo de datos
│   └── rules_config.json     # Definición de reglas aplicadas
├── 03_llm_integration/       # Etapa 3: Orquestación del modelo de lenguaje
│   ├── llm_testing.ipynb     # Notebook de pruebas de prompts y embeddings
│   └── prompt_templates/     # Plantillas de prompts utilizadas
├── 04_app/                   # Etapa 4: Aplicación funcional de producción
│   ├── src/                  # Módulos de código estables
│   │   ├── pipeline_core.py  # Pipeline migrado a producción
│   │   ├── llm_core.py       # Conector del LLM migrado a producción
│   │   └── utils/            # Herramientas de soporte
│   └── main.py               # Punto de entrada de la aplicación final
└── README.md                 # Descripción general del repositorio
```



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
* **Librerías Core**: `pandas`, `numpy` (Próximamente: `Streamlit`/`ipywidgets`, `API del LLM`).
* **Variables Críticas de Control**: `IS_LATE`, `VENDOR_NAME`, `DELAY_DAYS`, `REQUESTED_DT`, `RECPT_DT`, `REASON_DSC`, `HOT_PO_FLAG`.

---
*Nota: Este documento refleja el progreso en tiempo real del desarrollo. Actualmente ejecutando tareas de ingeniería de datos en la Fase 1.*
