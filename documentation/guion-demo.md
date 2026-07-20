# Guion de demo en vivo (ES)

Guion paso a paso para la demo en vivo del colloquium, sobre la aplicación final de Fase 4
(`04_app`). Satisface el mandato literal del kickoff del mentor ("Slides + demo: seleccionar
un PO delayed y ver la explicación del AI en vivo") y el DoD del issue #106 ("un caso de
mismatch que luzca la tesis"). Referenciado desde la slide 9 de `presentacion-final.md`.

## Pre-requisitos

- La app debe estar corriendo **antes** de empezar a presentar: `streamlit run 04_app/app.py`
  desde la raíz del repo. No arrancarla en vivo frente al panel.
- Cero llamadas a API durante la demo: todo lo que se muestra ya está generado en disco
  (`data/processed/po_output.csv`, `data/processed/scorecards/*.json`,
  `data/processed/agente1_raw.txt`). La demo no puede fallar por costo ni por una API caída;
  solo por que la app no esté corriendo, de ahí este pre-requisito.
- PO de la demo: **#100236** (BIOPLEX, Vendor, HOT PO, severidad HIGH). Justificación de la
  elección en `presentacion-final.md` ("Elección del caso de demo").

## Paso 1 — Landing

Pantalla de entrada (`app.py`). Señalar en una frase las dos vistas disponibles —Exception
Workbench (Diego) y Network Intelligence (Ravi)— y la tarjeta de acceso al bot de Telegram.
Click en "Abrir Network Intelligence →".

## Paso 2 — Network Intelligence (vista de Ravi)

Recorrer, en este orden:

1. Los tres KPIs de la izquierda: total de POs tardíos (247), % de severidad alta, y la KPI
   "Tasa de Desacuerdo AI". **Al llegar a esta última, aclarar en una frase**: esta cifra
   (hoy ~38.5%, 95/247) es el juicio propio del LLM por PO sobre si su diagnóstico coincide
   con el `REASON_DSC` humano — está relacionada, pero no es la misma cifra que el reason
   agreement de 88.8% que se cita en la slide de Validación y Métricas (esa la calcula la
   regla de la Fase 2 contra una agrupación curada, no el LLM). Ver el detalle de por qué son
   dos mediciones distintas en `presentacion-final.md`.
2. La distribución por etapa y por severidad (barras horizontales).
3. La tendencia temporal de POs tardíos.
4. Una tarjeta ejecutiva de "Diagnóstico Estratégico" para Vendor (la sección que muestra la
   lectura agregada por entidad, con su nivel de riesgo y acción recomendada).

## Paso 3 — Drill-down hacia Diego

Bajar hasta "Ver detalle de un PO (Exception Workbench)". Marcar el checkbox "Solo POs con
desacuerdo AI vs humano" para acotar la lista. En el selector, elegir "PO #100236". Click en
"Ver en Exception Workbench →".

## Paso 4 — Exception Workbench (vista de Diego), PO #100236 ya preseleccionado

La app aterriza directo en el PO elegido (el drill-down lo preselecciona en el selector
"Número de PO:"). Recorrer, en este orden:

1. **Contexto rápido**: Retraso 5.3 d · Vendor BIOPLEX · Carrier FedEx Freight · DC Phoenix.
2. **Las cinco cards de diagnóstico**: Etapa = Vendor · Severidad = HIGH · Confianza LLM =
   Alta (la app muestra el bucket, no el número crudo) · Validación AI vs Humano = "⚠️
   Desacuerdo", con la nota "un desacuerdo es un hallazgo a revisar, no un error del LLM" ·
   Reason Humano = "Equipment/trailer issue".
3. **Exceso de la etapa asignada**: "Exceso Vendor: 94.5 hrs", con la aclaración en pantalla
   de que es el exceso sobre la ventana esperada de esa etapa, no un componente que suma al
   retraso total.
4. **Flags de agravantes**: el pill "🔥 HOT PO — Prioridad máxima" (este PO es urgente; no
   trae short shipment).
5. **Timeline de 7 eventos** — este es el punto central de la demo. Señalar que el tramo
   resaltado (con la pill "TRAMO VENDOR — etapa responsable") cubre justo el hueco entre
   "📦 STA" (2025-04-04) y "✅ Cita Aprobada" (2025-04-08, tarde en la noche): casi 5 días de
   espera ahí, mientras que los cuatro eventos siguientes —tráiler, check-in, check-out,
   recepción— ocurren todos dentro de las mismas ~5 horas del día siguiente. El retraso está
   concentrado enteramente en la aprobación de la cita, no en nada corriente abajo.
6. **Panel "Diagnóstico Diferencial"** — la explicación del AI en vivo que pide el kickoff:
   - Hipótesis principal: problemas de planificación y gestión de recursos del proveedor
     BIOPLEX, que no asignó la capacidad adecuada para cumplir con la PO urgente.
   - Evidencia: retraso de 5.26 días y exceso de proveedor de 94.5 horas, con fill rate del
     100% (descarta que haya sido falta de producto).
   - Hipótesis alterna: congestión en las instalaciones del proveedor.
   - Paso discriminante: confirmar la disponibilidad de espacio y recursos de BIOPLEX en la
     fecha del retraso.
   - Plan escalonado: acción inmediata (pedir a BIOPLEX un informe de planificación),
     correctiva (proveer recursos o buscar alternativas), preventiva (protocolo de
     comunicación para priorizar futuras órdenes urgentes).

## Paso 5 — Cierre

Volver a la landing. Mencionar el bot de Telegram como canal adicional de solo lectura (si
`TELEGRAM_BOT_USERNAME` está configurado en el entorno de la demo, mostrar el QR del
expansor).

## Si algo falla en vivo

Como no hay llamadas a red, la única falla posible es que la app no esté corriendo o que se
haya reiniciado el proceso de Streamlit. Tener una segunda pestaña con la app ya abierta como
respaldo, y el PO #100236 anotado a mano para poder teclearlo directo en el selector si el
drill-down no aterriza solo.
