# PO Delay Root Cause Analyzer 

El **PO Delay Root Cause Analyzer** es una herramienta de Inteligencia Artificial diseñada para analizar Órdenes de Compra (PO) retrasadas dentro de la cadena de suministro. El sistema procesa datos logísticos, identifica la etapa exacta donde ocurrió el desvío mediante reglas de negocio avanzadas y genera explicaciones automatizadas junto con acciones recomendadas utilizando un Modelo de Lenguaje de Gran Escala (LLM).

##  Objetivo Final del Proyecto
Construir una plataforma integral que reciba datos transaccionales de órdenes de compra, detecte inconsistencias operativas y actúe como un auditor inteligente que identifique la causa raíz de los retrasos, contrastando los registros manuales del personal con la realidad de los timestamps logísticos.

---

## 📄 Registro de Decisiones de Arquitectura (ADR)
Para conocer el rastro histórico, la justificación de las reglas de negocio avanzadas, la evolución de los umbrales y los debates del equipo técnicos validados por la mentoría, consulta el **[Log Índice de ADRs](documentation/decisiones/README.md)**.

---

##  Estructura del Proyecto

El repositorio está organizado siguiendo el orden cronológico de las cuatro etapas del ciclo de vida del proyecto, facilitando el seguimiento del progreso desde la investigación hasta el despliegue:

> **Nota:** este árbol refleja el **estado real del repo hoy**. Fases 1 y 2 implementadas
> y cerradas; Fase 3 (integración LLM) implementada y en curso; Fase 4 (demo/app) pendiente.

```text
├── documentation/                      # Textos, PDFs, convenciones del equipo
│   ├── decisiones/                     # Historial de decisiones de arquitectura (ADR)
│   │   ├── README.md                   # Log índice de decisiones tomadas (ADR Log)
│   │   ├── ADR-01.md                   # ADRs individuales (versiones vigentes y superadas)
│   │   └── ...
│   ├── kickoff_po_root_cause.html      # Especificaciones del proyecto (mentor)
│   ├── convenciones-issues.md          # Acuerdos de gestión del equipo
│   └── plantillas-cli/                 # Borradores de issues para `gh`
├── data/                               # raw/ y processed/ (gitignored; solo .gitkeep)
├── 01_data_pipeline_and_eda/           # Fase 1: pipeline + EDA
│   ├── data_pipeline_and_EDA.ipynb     # Notebook combinado (pipeline + EDA)
│   └── pipeline_core.py                # clean_po_data() + cross_validate + save_clean_output
├── 02_clasif_reglas_negocio/           # Fase 2: clasificación por etapa (implementada)
│   ├── clasif_etapa.ipynb              # Notebook de presentación de la fase
│   ├── classifier_core.py              # classify_po_stages() + severidad + persistencia
│   ├── metrics_core.py                 # Validación: stage accuracy + reason agreement
│   └── rules_config.json               # Umbrales externalizados (leídos por nombre)
├── 03_llm_integration/                 # Fase 3: integración LLM (implementada, en curso)
│   ├── llm_integration.py              # build_prompt + backends (Qwen/Claude/DeepSeek)
│   └── prompt_template.txt             # Borrador de system prompt (ver README de la fase)
├── 04_app/                             # Fase 4: demo / app (pendiente)
├── tests/                              # Suite de pytest (pipeline, clasificador, métricas,
│   │                                   #   handoff, LLM); fixtures de valores conocidos
│   ├── conftest.py
│   ├── test_pipeline_core.py
│   ├── test_classifier_core.py
│   ├── test_metrics_core.py
│   ├── test_handoff_contract.py
│   └── test_llm_integration.py
├── requirements.txt                    # Dependencias (en la raíz)
├── pyproject.toml                      # Config de pytest (pythonpath, testpaths)
├── .env.example                        # Plantilla de variables de entorno
└── README.md                           # Descripción general del repositorio
```



---

##  Plan de Desarrollo del Proyecto

El proyecto se estructura en **4 fases secuenciales**:

###  Fase 1 — Data Pipeline (Limpieza y Validación) `[cerrada]`

* Procesamiento de un dataset inicial de 400 filas y 39 columnas que incluye anomalías intencionales.
* "Cargar el CSV, limpiar timestamps, validar datos. EDA: cuantos POs tienen delay? Distribucion por vendor/DC."

* **Carga y Parseo**: Uso de `pandas` con `errors='coerce'` para evitar rupturas por valores nulos (dejándolos como `NaT`).
* **Auditoría de Calidad**: Detección de tiempos invertidos (ej. `CHECKIN_DT` < `TRAILER_ARRIVE_DT`) marcados bajo la flag `_ts_issue` sin elimin registros.
* **Cálculo de Métricas Clave (Lead Times)**:
  * `yard_wait` = `CHECKIN` - `TRAILER_ARRIVE`
  * `dock_time` = `CHECKOUT` - `CHECKIN`
  * `carrier_lag` = `TRAILER_ARRIVE` - `APPROVED_DT`
* **Output**: DataFrame limpio, con deltas calculados y banderas de calidad, listo como entrada para las siguientes fases.

###  Fase 2 — Clasificación por Etapa (Reglas de Negocio) `[cerrada]`
Implementación de un clasificador **determinístico** basado en el exceso sobre el umbral de cada etapa (no probabilístico): la etapa primaria es el tramo de mayor exceso sobre su umbral del mentor, con vendor por señal directa de STA push. Las reglas se evalúan de forma reproducible y los umbrales viven externalizados en `rules_config.json`.
"Implementar reglas que asignan vendor/carrier/DC a cada PO. Comparar con REASON_DSC. Documentar matches vs mismatches".

###  Fase 3 — LLM Root Cause (Integración con API) `[implementada, en curso]`
Auditoría cognitiva de cada orden retrasada mediante el consumo dinámico de LLMs.
* **Prompt Engineering**: Construcción de un prompt enriquecido por fila con los hitos temporales de las fases 1 y 2.
"Disenar prompt, generar root cause explanations para todos los POs delayed. Asignar severidad. Primera evaluacion".

###  Fase 4 — Demo Interactiva + Evaluación Final `[pendiente]`
Construcción de una interfaz de usuario para el consumo de resultados del negocio.
"Construir notebook/app demo: seleccionar PO > ver timeline, causa, explicacion. Medir metricas. Presentar hallazgos."

---

##  Tecnologías y Variables Principales

* **Lenguaje principal**: Python 3.x
* **Librerías Core**: `pandas`, `numpy` (Próximamente: `Streamlit`/`ipywidgets`, `API del LLM`).
* **Variables Críticas de Control**: `IS_LATE`, `VENDOR_NAME`, `DELAY_DAYS`, `REQUESTED_DT`, `RECPT_DT`, `REASON_DSC`, `HOT_PO_FLAG`.

---
*Nota: Este documento refleja el progreso en tiempo real del desarrollo. Fases 1 y 2 cerradas; Fase 3 (integración LLM) en curso.*
