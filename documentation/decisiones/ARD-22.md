# Spec de retrabajo de la interfaz F4: información clave por persona y checklist ejecutable

* **Estatus:** 🔵 **BORRADOR** (lo cierra el equipo — ejecutado y verificado por G7)
* **Contexto Técnico:** Fase 4 — retrabajo final de `04_app` (Streamlit); unidad G6 de la
  orquestación de cierre, insumo directo de G7 (ejecución)
* **Referencias:** Issue #130 (feedback post-rediseño); [ADR-09](ARD-09.md) (`../user_personas.md`);
  [ARD-17](ARD-17.md) (lenguaje visual, protegido intacto); [ARD-21](ARD-21.md) (contrato
  tier-1/tier-2, fuente de los campos que se exponen); [ADR-10](ARD-10.md) (severidad híbrida
  — no se toca); Issue #197 (drill-down Ravi→Diego, ya resuelto, protegido); PR #198 (manejo de
  error si falta `po_output.csv`, ya resuelto); `04_app/app.py`, `04_app/pages/1_🔍_Exception_Workbench.py`,
  `04_app/pages/2_📊_Network_Intelligence.py`, `04_app/config.py`

## Contexto y Problema

`user_personas.md` ([ADR-09](ARD-09.md)) documenta qué necesita cada persona, pero se escribió
antes de que el contrato tier-1/tier-2 ([ARD-21](ARD-21.md)) existiera — su tabla "qué consume
cada persona" no incluye los 8 campos tier-1 ni los 9 tier-2. La app actual (verificada en esta
unidad, no asumida) ya implementa gran parte de lo que las personas piden: timeline con 7
eventos, badges de etapa/severidad/confianza, panel de hipótesis tier-2, gráficos de barra (no
pie: la prohibición de [ARD-17](ARD-17.md) contra pie/dona/3D/SHAP/OTIF ya se cumple en el
código). Quedan 2 gaps reales de información y un conjunto de pendientes de UI/UX agrupados en
el issue #130, sin atribución nominal individual en GitHub.

Además, G3 (unidad previa, cerrada 2026-07-19, PR #200) ya decidió documentar la divergencia de
severidad LLM-vs-regla sin exponer severidad dual en la UI. Esta spec no reabre esa decisión.

## Opciones Consideradas

**Opción A — Ejecutar solo el checklist literal de #130.** Pros: scope mínimo, ya redactado.
Contras: 2 de los 3 gaps reales de información (`excess_*_hrs` sin usar, tendencia temporal
ausente) no están en #130 porque se escribió sobre el estado de la app, no contra el contrato
de datos vigente ni contra la tabla de consumo de personas — quedarían sin resolver aunque las
personas los piden.

**Opción B — Reconstruir ambas vistas desde cero.** Pros: oportunidad de limpiar toda deuda de
una vez. Contras: la app ya está organizada por persona (María, #101/#102/#103) y ya cumple
ARD-17 y las prohibiciones anti-contaminación; reconstruir desde cero descarta trabajo correcto
y amplía el scope de G7 sin necesidad.

**Opción C — Retrabajo dirigido por personas: proteger lo que ya cumple, cerrar los gaps de
información reales, resolver las decisiones abiertas de #130, diferir lo que no aplica hoy
(elegida).** Audita el código real contra lo que cada persona necesita, distingue "ya cumple" de
"gap real" de "cosmético de #130", y deja una lista de no-regresión explícita.

## Decisión

### 1. Diego (Exception Workbench) — información clave y por qué

Ya protegido (no se toca en G7 salvo lo listado en la sección 7):
- Timeline de 7 eventos con el tramo de la etapa resaltado — evidencia primaria que Diego usa
  para confiar o desconfiar del diagnóstico.
- Badges de etapa, severidad y confianza, más el flag de desacuerdo con `REASON_DSC` —
  prominente por diseño (ADR-09).
- Panel de diagnóstico diferencial tier-2 (hipótesis principal + evidencia + razonamiento,
  hipótesis alterna + paso discriminante, plan de 3 pasos) cuando existe; placeholder claro
  cuando no (tier-2 es opt-in vía `--action-call`, ARD-21).
- Flags de agravantes (`HOT_PO_FLAG`, `is_short_ship`).

Gap cerrado en esta ronda: agregar el `excess_*_hrs` **de la etapa asignada únicamente**, con
etiqueta explícita de que es el exceso sobre la ventana esperada de esa etapa, no un componente
que suma al delay total. Fuente: tier-1 (ARD-21, #158), ya en el contrato, hoy sin ninguna
representación en la UI. "Solo la etapa asignada" es consistente con la jerarquía de una sola
causa por PO (ARD-02); mostrar las 3 columnas lado a lado introduciría ruido de etapas no
asignadas y el riesgo ya documentado de que se lea como waterfall (`excess_vendor_hrs` +
`excess_carrier_hrs` + `excess_dc_hrs` no suman a `delay_days_calc`).

### 2. Ravi (Network Intelligence) — información clave y por qué

Ya protegido (no se toca en G7 salvo lo listado en la sección 7):
- Distribución por etapa y por severidad en barra horizontal apilada (ya cumple ARD-17; sin
  pie/dona en el código) — el patrón sistémico que Ravi busca antes que cualquier caso
  individual.
- Tasa de desacuerdo como KPI de primera clase (mapea al umbral del mentor Reason Code
  Agreement) — ya implementada; se ajusta el formato en la sección 3a.
- Tarjetas ejecutivas y tabla de métricas consolidadas por entidad (Vendor/Carrier/DC): zona de
  riesgo, score, análisis, acción — el scorecard que dirige el reporte al dueño correcto.
- Tabla de POs con desacuerdo + drill-down a Diego — ya resuelto por #197; el puente "el caso
  valida, el patrón decide" de ADR-09.

Gap cerrado en esta ronda: sección de tendencia temporal sobre `PO_DT` — línea con etiquetado
directo, el encoding que ARD-17 ya fijó para esta tarea (nunca se había decidido agregar la
sección en sí). Cierra el paso de las actividades documentadas de Ravi ("tendencia vs periodo
anterior"), que hoy no tiene ninguna vista temporal en la app.

### 3. Decisiones puntuales resueltas en esta spec

a. **Tasa de desacuerdo: porcentaje titular + conteo absoluto secundario** (ej. "13.8%
(34/247)"). El mentor pide reportar Reason Code Agreement en %; el patrón "conteo + %" ya
existe en la KPI de severidad (`n_high`/`high_pct`) — se reusa.

b. **Consistencia de color de severidad entre las dos vistas: ya resuelta por diseño.** ARD-17
centraliza la codificación en `config.py` (`severity_colors()`/`stage_colors()`); si ambas
vistas invocan esos helpers en vez de hex sueltos, la consistencia es automática. G7 audita que
así sea (ítem R3), no decide una paleta nueva.

c. **`excess_*_hrs` en Diego: solo la etapa asignada** (detalle en sección 1).

d. **Tendencia temporal en Ravi: se agrega en esta ronda** (detalle en sección 2).

### 4. Sistema de diseño extendido: tipografía, espaciado y densidad

ARD-17 fijó color, forma y tipo de gráfico, pero no cubrió tipografía de datos, escala de
espaciado ni densidad de información. Esta ronda cierra ese hueco con decisiones ejecutables,
sin reabrir ARD-17.

**Tipografía.** Dos familias con roles separados: la sans del tema para prosa, etiquetas y
titulares; una monoespaciada acotada a datos técnicos tabulares — timestamps del timeline,
identificadores de PO, conteos de horas (`excess_*_hrs`) y días (`delay_days_calc`) y los
porcentajes de las KPIs. Razón: los dígitos monoespaciados alinean por columna (facilita
comparar y escanear cifras, el principio de posición común que ARD-17 ya cita) y separan
visualmente el dato-máquina del texto redactado por el LLM. No se aplica a nombres de entidad ni
a prosa: ahí sería ruido.

**Espaciado y densidad.** Objetivo de densidad: el contenido primario de cada vista cabe sin
scroll vertical en una laptop estándar — Diego: los 7 eventos del timeline y el panel de
diagnóstico; Ravi: las KPIs y la distribución por etapa. Regla de paridad: las cards de una
misma fila comparten alto y padding (generaliza D1, no lo trata como parche aislado). Se adopta
una escala de espaciado consistente (múltiplos de una unidad base) en vez de valores sueltos por
card, para que G7 no reintroduzca la inconsistencia que #130 reporta. No se fijan tokens
numéricos aquí: la escala se instrumenta en G7 con criterio, no como spec cerrada.

**Nota de procedencia.** Pie de página con la fecha del corte del dataset y su origen real: el
artefacto `po_output.csv` de Fase 3 (247 POs de un corte histórico). No se citan fuentes de
ingesta externas (ERP/telemetría en vivo) que no existen en el proyecto — la app es
retrospectiva sobre un corte, no un feed en tiempo real.

**Elementos de diseño considerados y rechazados** (con su razón; refuerzan la no-regresión de la
sección 6):
- Botón "Validar diagnóstico" con estado "verificado" y log de auditoría — introduce
  escritura/persistencia que la arquitectura de solo-lectura no tiene; queda fuera de esta ronda
  (no se descarta como idea futura, pero exige decidir dónde se persiste, alcance mayor que el
  pulido de #130).
- Drawer de "exportar reporte a Slack/Telegram" — Slack no existe en el proyecto y el bot de
  Telegram (ARD-20) es de comandos fijos de lectura, no un canal de exportación.
- Sparkline de "últimos 30 días" por entidad en los scorecards — el dataset es un corte
  histórico, no un feed rodante; la tendencia agregada (R1) ya cubre la necesidad temporal sin
  sugerir una ventana móvil que los datos no soportan.
- Ishikawa/5-Whys, OTIF, analítica predictiva, pie/dona y taxonomía de dominio ajeno ya están
  prohibidos por ARD-17 y la sección 6; se reiteran como criterio para G7.

### 5. Mapeo de issue #130

| Ítem de #130 | Resolución |
|---|---|
| Altura/padding de card "Validación AI vs Humano" | Absorbido en G7 (D1, cosmético) |
| Timeline sin scroll en pantallas estándar | Absorbido en G7 (D2, layout) |
| Tooltip sobre `llm_coincide_con_reason` | Absorbido en G7 (D3, copy en sección 7) |
| Drill-down desde tabla de desacuerdo | Ya resuelto — issue #197, protegido |
| Leyendas de Plotly con nombres legibles | Absorbido en G7 (R4, cosmético) |
| Filtro temporal (rango de fechas) | Diferido — el propio ítem lo condiciona a "si el dataset crece"; con 247 POs no aporta valor hoy |
| % vs conteo absoluto para desacuerdo | Resuelto en esta spec (3a) |
| Consistencia de color de severidad | Resuelto en esta spec (3b) — ya lo garantiza ARD-17 |
| Manejo de error si falta `po_output.csv` | Ya resuelto — G1, PR #198 |
| `print()`/logs de debug | Verificar en G7 si G2 (PR #199) ya lo cubrió (R5) |
| `requirements.txt` actualizado | Absorbido en G7 (R7) — sin dependencias nuevas esperadas |
| `styles.css` sin estilos huérfanos | Absorbido en G7 (R6) |

### 6. Información que no se puede perder (no-regresión, criterio para G7)

- Diego: timeline de 7 eventos con tramo resaltado; badges de etapa/severidad/confianza; flag
  de desacuerdo con `REASON_DSC` prominente; panel tier-2 completo (hipótesis + evidencia +
  razonamiento + alterna + discriminante + plan de 3 pasos) con su placeholder cuando no existe;
  flags `HOT_PO_FLAG`/`is_short_ship`; selector de PO con preselección por drill-down.
- Ravi: barra horizontal apilada por etapa y por severidad; tasa de desacuerdo como KPI de
  primera clase; tarjetas ejecutivas y tabla consolidada por entidad; tabla de desacuerdo con
  drill-down a Diego.
- Transversal: paleta Okabe-Ito por etapa, rampa acromática+forma por severidad, badge de
  bucket para confianza (nunca número crudo) — todo desde `config.py`, sin hex sueltos; cero
  pie/dona/treemap/3D; cero SHAP/OTIF/predicción; cero Ishikawa/5-Whys modal/quantile dotplots;
  cero botón de validación/escritura con log de auditoría (la app es de solo lectura del
  artefacto de Fase 3); cero exportación a Slack/Telegram (Slack no existe; el bot de ARD-20 es
  de comandos fijos de lectura); cero sparkline por entidad de ventana móvil (el dataset es un
  corte histórico); cero contenido trilingüe o de dominio ajeno (BOL, Carta Porte, Aduana, LTL).

### 7. Checklist ejecutable (entrada directa de G7)

**Diego — Exception Workbench:**
- D1. Igualar alto/padding de la card "Validación AI vs Humano" con las cards de Etapa/Severidad.
- D2. Comprimir el espaciado del timeline horizontal para que los 7 timestamps quepan sin
  scroll en pantallas estándar.
- D3. Agregar tooltip/ayuda contextual sobre `llm_coincide_con_reason` (copy sugerido: "Compara
  el diagnóstico del LLM contra la causa anotada por el humano en REASON_DSC. Un desacuerdo es
  un hallazgo a revisar, no necesariamente un error del LLM.").
- D4. Agregar el `excess_*_hrs` de la etapa asignada, etiquetado explícitamente como exceso de
  esa etapa (no como componente que suma al delay total).
- D5. Auditar que el badge de confianza implemente los 3 buckets de ARD-17 (Alta/Media/Baja);
  corregir si muestra el número crudo.
- D6. Eliminar `04_app/utils/helpers.py` (código muerto: sin imports en la app, referencia
  columnas de un contrato anterior que ya no existen).

**Ravi — Network Intelligence:**
- R1. Agregar sección de tendencia temporal sobre `PO_DT` (línea con etiquetado directo,
  encoding de ARD-17); granularidad semana/mes según densidad de datos.
- R2. Tasa de desacuerdo: formato "% titular + conteo secundario" (sección 3a).
- R3. Auditar que ambas vistas consuman `severity_colors()`/`stage_colors()` de `config.py` sin
  hex hardcodeados.
- R4. Legibilidad de leyendas de los 2 `px.bar`: nombres capitalizados ("Vendor" en vez de
  "vendor").
- R5. Verificar si `print()`/logs de debug quedaron cubiertos por G2 (PR #199); limpiar si no.
- R6. Verificar `assets/styles.css` sin estilos huérfanos de las vistas por-entidad antiguas.
- R7. Confirmar que no se necesitan dependencias nuevas en `requirements.txt`.

**Transversal — sistema de diseño extendido:**
- T1. Definir la familia monoespaciada en el tema/`config.py` y aplicarla solo a timestamps,
  IDs de PO, horas/días y porcentajes; el resto queda en la sans del tema.
- T2. Aplicar la escala de espaciado y la paridad de cards por fila (absorbe D1) y confirmar la
  densidad sin scroll en pantalla estándar (absorbe D2).
- T3. Agregar el pie de procedencia (fecha de corte + origen `po_output.csv`), sin fuentes de
  ingesta inventadas.

**Fuera de esta ronda (diferido, con razón):**
- Filtro temporal interactivo — dataset pequeño (247 POs) no lo amerita hoy.
- Corrección de `03_llm_integration/README.md` (contrato 16/33 desactualizado) — sincronización
  documental de G8, no de G7.
- Endurecimiento del parser regex de `agente1_raw.txt` — fragilidad conocida, no bloqueante
  para esta ronda; el contenido que produce está protegido (sección 6).

## Consecuencias

**Positivas:**
- G7 recibe un checklist ejecutable sin decisiones de diseño pendientes.
- Resuelve las 2 decisiones abiertas de #130 sin dejarlas para que G7 improvise.
- Cierra 2 gaps reales de información contra el contrato tier-1 vigente (ARD-21) y la persona
  de Ravi (ADR-09), que #130 no cubría por haberse escrito antes de esos documentos.
- Cierra el hueco que ARD-17 dejó en tipografía, espaciado, densidad y procedencia, y deja
  documentados como guardrails de diseño los elementos genéricos rechazados (validación con
  escritura, exportación Slack/Telegram, sparkline de ventana móvil).
- La lista explícita de no-regresión reduce el riesgo de que G7 rompa el panel tier-2 o las
  prohibiciones anti-contaminación ya cumplidas al tocar CSS/layout.

**Negativas:**
- El filtro temporal y la sincronización de `03_llm_integration/README.md` quedan fuera —
  dependientes de que el dataset crezca o de que G8 se ejecute.
- La fragilidad del parser regex de `agente1_raw.txt` no se resuelve aquí.

## Relación con otras decisiones

Consume [ADR-09](ARD-09.md) (personas, extiende su tabla de consumo con tier-1/tier-2),
[ARD-17](ARD-17.md) (lenguaje visual — protegido intacto), [ARD-21](ARD-21.md) (contrato
tier-1/tier-2 — fuente de `excess_*_hrs`), [ADR-10](ARD-10.md) (severidad híbrida — no se toca;
la decisión de G3 de no exponer severidad dual en UI queda confirmada, no reabierta). La sección
4 extiende [ARD-17](ARD-17.md) hacia tipografía/espaciado/densidad sin reabrir sus reglas de
color ni de tipos de gráfico. Mapea issue #130 punto por punto (sección 5). Protege la
resolución de issue #197 (drill-down) y del manejo de error de datos faltantes (PR #198). Es el
insumo directo de G7 (ejecución) y deja como pendiente explícito para G8 la sincronización de
`03_llm_integration/README.md`.
