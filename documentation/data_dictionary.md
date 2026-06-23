# Data Dictionary

Este documento combina el diccionario de datos columna por columna con el contexto de negocio del dataset, siguiendo un estándar híbrido inspirado en *Hugging Face Dataset Cards* y *Datasheets for Datasets*.

## 1. Contexto del Dataset (Data Card)

*   **Origen de los datos:** Dataset sintético que simula operaciones logísticas. Contiene **400 Órdenes de Compra (POs)** y **39 columnas** (verificadas y validadas contra el header real del CSV).
*   **Ubicación física:** Localizado en `data/raw/` (excluido del control de versiones mediante `.gitignore`).
*   **Fuente de verdad técnica:** Los **timestamps** del ciclo de vida son la única fuente de verdad para los cálculos de tramos y retrasos.
*   **Calidad de la anotación humana:** Los campos `REASON_CD` y `REASON_DSC` son anotaciones manuales y contienen aproximadamente un **20% de clasificaciones incorrectas** o inconsistentes. Deben usarse solo como contraste, nunca como regla dura.
*   **Limitaciones conocidas:** 
    *   Existen 12 POs con inversión temporal (`CHECKOUT_DT` < `CHECKIN_DT`). Son marcadas en el pipeline mediante la flag de calidad `_ts_issue`.
    *   El campo `TRAILER_DEPART_DT` ocurre en promedio ~27 horas después de la recepción (`RECPT_DT`) en el 99.8% de los casos, por lo que queda fuera del ciclo operativo útil para medir retrasos.

---

## 2. Diccionario de Campos (39 Columnas)

### Grupo A: Timestamps del Lifecycle (Núcleo de Reglas)
*Todos los campos de este grupo se parsean a datetime en el pipeline (`errors='coerce'`). Si el dato es inválido, se transforma en `NaT`.*

| Columna | Tipo | % Nulos Conocido | Rol en el Proyecto / Reglas | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `PO_DT` | Datetime | 0% | Núcleo de Reglas | Fecha de colocación de la PO. Inicio del ciclo de vida. |
| `STA_DT` | Datetime | 0% | Núcleo de Reglas | Fecha prometida de llegada (Scheduled Time of Arrival). Grano de día (siempre medianoche). Base del KPI de tardanza. |
| `APPROVED_DT` | Datetime | 0% | Núcleo de Reglas | Fecha y hora de aprobación de la cita vigente. Alias o equivalente a `DT_APPT_CURRENT_APPROVED`. |
| `DT_APPT_FIRST_APPROVED` | Datetime | 0% | Núcleo de Reglas | Primera aprobación de la cita. Su diferencia con la vigente define si hubo reprogramación (*reschedule*). |
| `DT_APPT_CURRENT_APPROVED` | Datetime | 0% | Núcleo de Reglas | Aprobación de la cita vigente en el sistema. |
| `TRAILER_ARRIVE_DT` | Datetime | **6.8% (27 POs)** | Núcleo de Reglas | Llegada del tráiler al DC. Si es nulo, la PO cae en la clasificación `Indeterminado/sin_datos` (imposible juzgar carrier/DC). |
| `CHECKIN_DT` | Datetime | 0% | Núcleo de Reglas | Inicio de la descarga física (entrada del camión al muelle). |
| `CHECKOUT_DT` | Datetime | 0% | Núcleo de Reglas | Fin de la descarga física. Presenta anomalías temporales en 12 registros (`CHECKOUT` < `CHECKIN`). |
| `RECPT_DT` | Datetime | 0% | Núcleo de Reglas | Recepción posteada en el sistema. Cierra el ciclo de vida operativo. Si `RECPT_DT > STA_DT` $\Rightarrow$ PO Tardío (KPI principal). |
| `REQUESTED_DT` | Datetime | 0% | Núcleo de Reglas | Fecha de solicitud de la cita por parte del proveedor (flujo *vendor*, pre-llegada). |
| `FIRST_SUBMITTED_DT` | Datetime | 0% | Núcleo de Reglas | Primera sumisión de solicitud de cita en el portal de proveedores. |
| `PREVIOUS_REQUEST_DT` | Datetime | **84.2%** | Evitar en Reglas | Historial de solicitudes previas. Columna mayoritariamente vacía; no apta para lógicas duras. |
| `TRAILER_DEPART_DT` | Datetime | 0% | Excluido de Tramos | Salida física del tráiler del patio. Ocurre post-recepción operativa; no mapea ventanas de *delay*. |

### Grupo B: Cantidades e Indicadores de Volumen (Short Ship)

| Columna | Tipo | % Nulos | Rol en el Proyecto / Reglas | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `NUM_CASES_ORDERED` | int64 | 0% | Reglas (Fill Rate) | Cantidad de cajas solicitadas originalmente en la orden de compra. |
| `NUM_CASES_SHIPPED` | int64 | 0% | Reglas (Fill Rate) | Cantidad de cajas enviadas por el proveedor. Si la razón Shipped/Ordered < 0.9 $\Rightarrow$ *Short Ship*. |
| `TOT_ORG_QTY` | int64 | 0% | Contexto / Control | Cantidad total original registrada en la transacción. |
| `TOT_RCVD_QTY` | int64 | 0% | Contexto / Control | Cantidad total física recibida en el centro de distribución. |
| `TOT_ON_ORD_QTY` | int64 | 0% | Contexto / Control | Cantidad total que permanece activa en estado de orden activa. |
| `TOT_ADJ_QTY` | int64 | 0% | Contexto / Control | Cantidad total de ajustes o correcciones aplicadas en el recibo. |

### Grupo C: Flags de Negocio (Inputs Exógenos)
*Campos nativos del CSV. Se mantienen fijos y no son recalculados por el pipeline.*

| Columna | Tipo | % Nulos | Rol en el Proyecto / Reglas | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `HOT_PO_FLAG` | int64 (0/1) | 0% | Priorización / Contexto | Flag exógena que indica si la Orden de Compra es de alta prioridad para el negocio. |
| `HOT_APPT_FL` | int64 (0/1) | 0% | Priorización / Contexto | Flag exógena que identifica si la cita logística fue catalogada como crítica o prioritaria. |

### Grupo D: Campos Precalculados (Solo para Cross-Check)
*⚠️ ¡Atención! No usar como fuente de verdad. Toda métrica se vuelve a calcular en el pipeline desde los timestamps nativos. Solo sirven para auditar discrepancias.*

| Columna | Tipo | Discrepancias / Notas | Rol en el Proyecto / Reglas | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `DELAY_DAYS` | Numeric | Auditado vs Timestamps | Cross-Check | Días de retraso precalculados en el origen. |
| `YARD_WAIT_HRS` | Numeric | Auditado vs Timestamps | Cross-Check | Horas de espera estimadas en el patio del centro de distribución. |
| `DOCK_HRS` | Numeric | Discrepa en 11 POs (máx 8.2h) | Cross-Check | Horas en muelle. Las discrepancias coinciden exactamente con la flag `_ts_issue`. |
| `IS_LATE` | object (Y/N) | Auditado vs Timestamps | Cross-Check | Indicador binario textual que señala si la orden llegó tarde en el sistema origen. |

### Grupo E: Anotación Humana (Referencia de Contraste)

| Columna | Tipo | % Nulos Conocido | Rol en el Proyecto / Reglas | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `REASON_CD` | object | **32.8%** | Contraste de Clasificación | Código de la razón del retraso asignado manualmente por operadores. |
| `REASON_DSC` | object | **2.2%** | Contraste de Clasificación | Descripción textual de la causa del retraso. (~20% de error respecto a la realidad del ciclo). |

### Grupo F: Entidades del Negocio

| Columna | Tipo | % Nulos | Rol en el Proyecto / Reglas | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `PO_NBR` | int64 / object| 0% | Identificador Único | Número único de identificación de la Orden de Compra (Primary Key lógica). |
| `VENDOR_NAME` | object | 0% | Atributo Entidad | Nombre comercial del proveedor que emite y despacha la orden. |
| `CARRIER_PARTY_NAME`| object | 0% | Atributo Entidad | Nombre de la empresa transportista (carrier) encargada del traslado. |
| `TRAILER_NBR` | object | 0% | Atributo Entidad | Número de placa o identificación física de la caja/tráiler logístico. |

### Grupo G: Columnas Administrativas

| Columna | Tipo | % Nulos | Rol en el Proyecto / Reglas | Descripción |
| :--- | :--- | :--- | :--- | :--- |
| `PAY_VENDOR_NBR` | int64 | 0% | Administrativa | Número de identificación del proveedor para efectos financieros. |
| `PAY_VENDOR_NAME` | object | 0% | Administrativa | Nombre legal registrado del proveedor para fines fiscales y de pago. |
| `DC_ID` | int64 | 0% | Administrativa / Entidad | Identificador único del Centro de Distribución de destino. |
| `DC_LOC_NAME` | object | 0% | Administrativa / Entidad | Nombre geográfico o de localidad del Centro de Distribución. |
| `DC_FACILITY_CD_ABBREV`| object | 0% | Administrativa | Abreviación interna del código de la instalación o edificio dentro del DC. |
| `PO_STATUS_CD` | object | 0% | Administrativa | Estado administrativo de la PO en el sistema ERP origen. |
| `YARD_DROP_FL` | int64 | 0% | Administrativa | Indicador de si el contenedor se dejó en patio (*drop* = 1) o no. |

