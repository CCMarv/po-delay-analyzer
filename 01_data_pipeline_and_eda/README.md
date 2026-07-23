# Fase 1: Data Ingestion, Pipeline Quality & EDA

Este módulo comprende la ingesta, limpieza, validación de consistencia temporal y el análisis exploratorio de datos (EDA) del dataset logístico de órdenes de compra.

---

## 1. Contexto y Arquitectura del Pipeline

El pipeline de datos procesa el archivo crudo de entrada para garantizar que las fases posteriores de clasificación cuenten con datos consistentes y estructurados. 

La lógica principal reside en `pipeline_core.py` y se divide en cinco etapas secuenciales:

| Etapa | Operación del Pipeline | Descripción Técnica |
| :---: | :--- | :--- |
| **0** | **Dataset Crudo** | Ingesta del archivo fuente `po_root_cause_synthetic.csv`. |
| **1** | **Parseo de Timestamps** | Conversión estricta a tipo fecha y manejo de errores con `NaT`. |
| **2** | **Flags de Calidad** | Clasificación de registros confiables sin borrado de filas. |
| **3** | **Deltas (Tramos)** | Cálculo matemático de los tiempos de duración entre hitos. |
| **4** | **Flags Exploratorias** | Inyección de banderas de alerta basadas en límites preliminares. |
| **5** | **Cross-Validation** | Auditoría cruzada final de consistencia antes de la salida. |



### Detalle de Funciones Core

#### `clean_po_data()`
Ejecuta secuencialmente los siguientes pasos de transformación:
1. **Parseo de Timestamps:** Convierte las columnas del ciclo de vida a tipo `datetime64[ns]` utilizando `errors='coerce'`. Cualquier valor alfanumérico inválido o corrupto se transforma de manera segura en un no-dato (`NaT`).
2. **Inyección de Flags de Calidad:** Evalúa el estado del registro sin destruir filas, asignando indicadores binarios de confiabilidad operativa.
3. **Cálculo de Tramos (Deltas):** Genera métricas de duración entre hitos del ciclo de vida logístico para aislar las responsabilidades de la cadena.
4. **Asignación de Flags de Etapa:** Inyecta alertas preliminares basadas en umbrales exploratorios del negocio.

#### `cross_validate_deltas()`
Realiza una auditoría matemática cruzada comparando los tramos calculados en el pipeline contra las columnas precalculadas del CSV origen. Genera reportes automatizados de discrepancias temporales y valida la consistencia lógica antes de exportar el dataframe limpio.

---

## 2. Decisiones de Calidad de Datos

A través del ciclo de desarrollo, se implementaron cinco estrategias de ingeniería de datos para mitigar anomalías del dataset de entrada, vinculadas a sus respectivas decisiones técnicas de diseño:

*   **Timestamps como Fuente de Verdad (#15):** Las columnas de origen `YARD_WAIT_HRS`, `DOCK_HRS`, `DELAY_DAYS` e `IS_LATE` fueron descartadas como lógicas duras. El pipeline recalcula cada métrica desde los campos de fecha nativos. *Evidencia:* Se detectaron 11 registros donde `DOCK_HRS` discrepaba en hasta 8.2 horas del cómputo real debido a que el sistema de origen registraba inversiones temporales (`CHECKOUT` < `CHECKIN`) como valores negativos. El pipeline trunca estos tramos físicamente imposibles a `0` horas. `HOT_PO_FLAG` se mantiene intacto al ser un input puro de negocio.
*   **Manejo de Datos Corruptos sin Pérdida de Población (#4, #16, #18):** Para no alterar el volumen estadístico ni inducir sesgos, no se eliminan registros con fechas inconsistentes. En su lugar, se aíslan mediante tres flags:
    *   `_ts_issue`: Registra 12 órdenes con inversiones temporales de muelle.
    *   `_trailer_arrive_null`: Registra 27 órdenes sin tracking de llegada.
    *   `_data_reliable`: Identifica 361 registros totalmente limpios (Población 100% óptima).
*   **Tratamiento del NaN Silencioso en Transportistas (#16):** Al faltar el timestamp `TRAILER_ARRIVE_DT` en 27 casos, la operación matemática del tramo del carrier arrojaba `NaN`. Evaluar esto con operadores tradicionales resultaba en un falso positivo de cumplimiento estadístico. La flag explícita permite remover estas 27 órdenes del denominador de cumplimiento logístico, aislando la métrica de *service level* del *compliance* puro de datos.
*   **Aislamiento de Eventos Post-Recepción (#18):** El análisis de la columna `TRAILER_DEPART_DT` reveló que la salida física del camión ocurre en promedio ~27 horas **después** del cierre operativo en el sistema (`RECPT_DT`) en el 99.8% de los casos. Se excluyó formalmente este campo de las lógicas de tramos útiles de retraso por encontrarse fuera del lifecycle de recepción.
*   **Estructuración de Deltas Operativos (#5):** Se crearon formalmente en código los siguientes tramos de control de tiempos:
    *   `lead_time_days`: Duración total desde colocación hasta fecha prometida (`PO_DT` $\rightarrow$ `STA_DT`).
    *   `carrier_lag_hrs`: Tiempo de tránsito del transportista (`APPROVED_DT` $\rightarrow$ `TRAILER_ARRIVE_DT`).
    *   `yard_wait_calc_hrs`: Estancia en patio de maniobras (`TRAILER_ARRIVE_DT` $\rightarrow$ `CHECKIN_DT`).
    *   `dock_calc_hrs`: Tiempo de descarga física en muelle (`CHECKIN_DT` $\rightarrow$ `CHECKOUT_DT`).
    *   `delay_days_calc`: Retraso final del ciclo de entrega (`RECPT_DT` $-$ `STA_DT`, acotado a $\ge 0$).
    *   `appt_lead_days`: Ventana de reserva del proveedor (`STA_DT` $-$ `APPROVED_DT`).

---

## 3. Umbrales de Fase 1 vs. Reglas de Clasificación

> [!WARNING]
> **Estatus de Umbrales en Fase 1: Exploratorios y Superados**
> Las banderas operativas inyectadas en este módulo (`flag_carrier_miss`, `flag_yard_miss`, `flag_dock_miss`) responden a límites iniciales definidos durante el análisis exploratorio:
> *   **Carrier:** 4 horas
> *   **Yard:** 4 horas
> *   **Dock:** 6 horas
> 
> El umbral de **Carrier de 4 horas ha sido superado** y no rige la clasificación final del negocio. La lógica oficial de producción se encuentra consolidada en la **Fase 2** (`02_clasif_reglas_negocio/`), aplicando un umbral paramétrico definitivo de **8 horas** dictado por el mentor del proyecto en la sesión del 06-16 (parámetro configurable en `rules_config.json`).

---

## 4. Resumen de Hallazgos del EDA (#19, #20)

*   **Mix de Escenarios Reales:** El comportamiento estadístico real del patio discrepa significativamente de las premisas teóricas contempladas en el kickoff. Los cuellos de botella se concentran dinámicamente en tramos específicos de la operación interna del DC en lugar de eventos exógenos generalizados.
*   **Concentración de Tardanzas:** Segmentación analítica del KPI principal de retraso:
    *   *Por Centro de Distribución (DC):* Ciertas localidades geográficas presentan demoras estructurales asociadas a la saturación de muelles.
    *   *Por Vendor/Carrier:* Se identificaron agrupaciones atípicas de baja eficiencia logística asociadas a transportistas específicos en franjas horarias nocturnas.
*   **Inconsistencia de la Anotación Humana:** Primer cruce de variables cuantitativas frente a la columna de texto libre `REASON_DSC`. Se hallaron contradicciones sistémicas en la codificación manual de los operadores del patio, confirmando empíricamente la hipótesis del proyecto: la anotación humana presenta un margen de error del ~20%, justificando la automatización algorítmica de la Fase 2 (la cual alcanza un 88.7% de concordancia de negocio).

---

## 5. Glosario y Estructura de Columnas

Para evitar redundancia de información y garantizar un único punto de verdad técnica, la descripción detallada del tipo de dato, nulos conocidos y roles de negocio de las 39 columnas de entrada se encuentra documentada en el recurso central del repositorio:

📘 [Ver Diccionario de Datos y Ficha Técnica (Data Card)](../documentation/data_dictionary.md)

---

## 6. Cómo Correr

### Prerrequisitos
Asegúrate de contar con el entorno virtual activo y las dependencias instaladas, además del dataset crudo ubicado en la ruta local correspondiente.

```bash
# 1. Asegurar la presencia del archivo de datos (gitignored)
ls data/raw/po_root_cause_synthetic.csv

# 2. Ejecutar el pipeline de Ingesta, Calidad y EDA
python 01_data_pipeline_and_eda/pipeline_core.py
```

### Salidas Esperadas
La ejecución generará en la consola el reporte estadístico de la validación cruzada (`cross_validate_deltas()`) e imprimirá las métricas de consistencia de registros válidos para el consumo del clasificador de Fase 2.
