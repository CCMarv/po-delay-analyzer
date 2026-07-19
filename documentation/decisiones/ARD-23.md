# Mockups como base de diseño del retrabajo de interfaz F4 y su reconciliación con ARD-17/ARD-22

* **Estatus:** 🔵 **BORRADOR** (lo cierra el equipo — ejecutado por G7)
* **Contexto Técnico:** Fase 4 / App — retrabajo visual de `04_app` (Streamlit); unidad G7 de la
  orquestación de cierre, ejecuta sobre el checklist de ARD-22 §7
* **Referencias:** [ARD-22](ARD-22.md) (spec de información por persona y checklist ejecutable —
  sigue vigente en el QUÉ; este ARD fija el CÓMO visual); [ARD-17](ARD-17.md) (lenguaje visual,
  protegido salvo lo revisado abajo); [ARD-21](ARD-21.md) (contrato tier-1/tier-2); [ARD-20](ARD-20.md)
  (bot de Telegram, canal de comandos fijos de lectura); Issue #130; mockups locales
  "Mockups analítica POs tardíos" (`Home Landing.dc.html`, `Exception Workbench.dc.html`,
  `Network Intelligence.dc.html`, tema claro y oscuro); `04_app/app.py`,
  `04_app/pages/1_🔍_Exception_Workbench.py`, `04_app/pages/2_📊_Network_Intelligence.py`,
  `04_app/config.py`, `04_app/components/`, `04_app/assets/styles.css`

## Contexto y Problema

G7 arrancó con un plan que trataba una referencia visual generada en claude.ai/design como guía
no-contractual: el checklist de ARD-22 §7 mandaba, y cualquier mockup que introdujera algo de la
lista de prohibiciones de ARD-17/ARD-22 §6 se descartaba como no-referencia. Al revisar los tres
mockups completos (landing + 2 vistas, claro/oscuro) con el equipo, la instrucción cambió: los
mockups **son la verdad inicial** del retrabajo — el diseño base a implementar — y el contrato se
reconcilia contra ellos, no al revés. Donde un mockup choque con una regla existente, la regla se
revisa aquí; el mockup no se adapta al contrato salvo que la razón original de la regla (no la
regla en sí) siga aplicando de forma directa.

## Opciones Consideradas

**Opción A — Mantener el mockup como referencia no-contractual (plan original de G7).**
Pros: cero riesgo de reabrir decisiones ya cerradas de ARD-17/ARD-22. Contras: no es lo que el
equipo pidió; deja sin resolver por qué el mockup difiere del contrato en varios puntos concretos
en vez de decidir explícitamente cuál gana.

**Opción B — Mockup manda sin excepción, incluida la palabra coloreada por etapa en la landing
(fidelidad literal).** Pros: cero ambigüedad de criterio. Contras: reabre la razón original de
ARD-17 §5 (contraste WCAG) sin que el mockup aporte una razón nueva que la invalide — el texto
Carrier (#E69F00) sobre fondo blanco cae a ≈2.2:1, muy por debajo del mínimo de texto (4.5:1); es
el mismo problema que motivó la regla, no un caso distinto.

**Opción C — Mockup manda; se documenta cada choque real y se adapta solo donde la razón
original de la regla contraataca directamente al mockup (elegida).** Preserva la intención de "el
mockup es la verdad" para todo lo que sí es una decisión de diseño (tipografía, densidad, layout,
qué se muestra), y reserva la adaptación a un único caso con una razón técnica objetiva
(accesibilidad), no de preferencia.

## Decisión

Los tres mockups de "Mockups analítica POs tardíos" son el diseño base de G7. Auditados en
completo, **no introducen ninguna prohibición dura** de ARD-17/ARD-22 §6: conservan la paleta
Okabe-Ito por etapa, la rampa acromática + ícono/forma (■◆●) para severidad y riesgo, barras
apiladas horizontales (no pie/dona/3D), línea con etiquetado directo (no leyenda), tipografía
monoespaciada para datos técnicos, y la app se mantiene de solo lectura. Son, en esencia, un
restyle más denso y pulido de contenido que ARD-22 §7 ya había especificado (D1–D4, R1–R2,
T1–T3), más la landing (fuera de §7) con acceso secundario al bot de Telegram.

### a. Revisiones al contrato que el mockup impone (el mockup gana)

1. **Badge de confianza sin `%`.** El mockup muestra solo el bucket ("Alta"), sin el número
   crudo entre paréntesis. Más estricto que la redacción original de ARD-22 §7 D5 (que dejaba el
   `%` como secundario aceptable) y alineado con el principio general de §6 ("badge de bucket
   para confianza, nunca número crudo") — se cierra la ambigüedad a favor de la lectura más
   estricta. `components/badges.py::confidence_badge_html` deja de interpolar `{score:.0%}`.
2. **Score de riesgo numérico eliminado de las cards ejecutivas de Ravi.** El código anterior
   (`render_exec_card_v3`) mostraba una línea "Score de Riesgo: 100.0/50.0/0.0" que era una
   re-codificación literal del mismo ordinal que el badge de zona ya porta (Alto=100, Medio=50,
   Bajo=0, fijo en `parse_informe_completo`). El mockup no la incluye. Se retira: el badge ya es
   la señal; el número no agregaba información, solo la duplicaba en otra escala.
3. **Flags de agravantes condicionales con estado vacío explícito.** El código anterior mostraba
   siempre dos líneas afirmativas ("✅ PO estándar" / "✅ Envío completo") cuando los flags no
   aplicaban. El mockup solo pinta las pills cuando el flag está activo, con la caption "Se
   muestran solo cuando aplican al PO." Se adopta ese patrón, agregando un estado "Sin agravantes
   activos" para cuando ninguno aplica — evita perder la señal de "no hay agravantes" sin
   duplicar dos líneas de confirmación que no aportaban lectura nueva.
4. **Hue de etapa solo en el tramo resaltado del timeline.** Antes, los 7 segmentos llevaban su
   borde coloreado por la etapa del PO completo (redundante en 6 de 7 eventos). El mockup solo
   colorea el borde del tramo responsable; el resto usa un borde neutro (`--border-subtle`). El
   color vuelve a señalar "cuál tramo importa" en vez de decorar los 7 por igual.
   `components/timeline.py::timeline_segment_html` gana un parámetro `tramo_label` para la pill
   "TRAMO {ETAPA} — etapa responsable" que el mockup agrega junto al primer segmento resaltado.
5. **Landing con card de acceso secundario al bot de Telegram.** Fuera del checklist original de
   ARD-22 §7 (que solo tocaba `app.py` por el pie de procedencia), el mockup la incluye como
   parte del diseño base de la landing. Consistente con [ARD-20](ARD-20.md): enlace a un canal de
   comandos fijos de lectura, no chat embebido ni exportación (protegido por §6). El handle del
   bot no es secreto (a diferencia del token) pero tampoco está documentado como dato público en
   ARD-20; se resuelve vía `TELEGRAM_BOT_USERNAME` en `.env` (placeholder en `.env.example`) — si
   falta, la card describe el canal sin botón activo, sin inventar un handle.

### b. Única adaptación al mockup (el contrato gana)

**Palabras de etapa coloreadas como texto → chips con punto de color.** El mockup de la landing
pinta "Vendor"/"Carrier"/"DC"/"Indeterminado" como texto en el hue de su etapa. Carrier
(`#E69F00`) sobre fondo blanco da ≈2.2:1 de contraste, muy por debajo del mínimo WCAG para texto
(4.5:1) — exactamente la razón que motivó ARD-17 §5 ("el color vive en la marca, no en el texto").
Se adapta a un chip (punto de color + texto en tinta neutra), el mismo idiom que ya usan las
leyendas de distribución del propio mockup (Network Intelligence) — no es una invención, es
generalizar un patrón que el mockup ya usa en otro lugar. Reusable vía `.stage-chip` en
`styles.css`.

### c. Guardas de datos (el mockup es ilustrativo, no la fuente)

Las cifras de los tres mockups (247 POs, 13.8% de desacuerdo, nombres de entidad, la fecha de
corte "2025-11-30" / "30 abr 2026") son ilustrativas del diseño, no datos reales del artefacto.
Todo valor renderizado en `04_app` se sigue computando del `df` cargado (`load_po_output`) o de
los JSON de scorecards reales — ninguna cifra del mockup se hardcodea. La fecha de corte usa
`config.dataset_cutoff_date(df)` (máximo timestamp de las 7 columnas del lifecycle), no una fecha
fija. Las columnas de las tablas consolidadas por actor son las que trae cada JSON real, no las
que ilustra el mockup.

### d. Desviaciones menores declaradas (no requieren reabrir nada)

- Las tablas consolidadas por actor y la tabla de POs con desacuerdo quedan en `st.dataframe`
  (funcional, ordenable, data-driven) en vez de la tabla HTML estática del mockup — mismo
  contenido, motor distinto por ser el idiomático de Streamlit para datos tabulares reales.
- El pie de procedencia usa formato de fecha ISO (`YYYY-MM-DD`) en las 3 páginas, incluida la
  landing (el mockup de landing usa "30 abr 2026" en español; los otros dos mockups ya usan ISO).
  Se unifica a ISO por consistencia entre las 3 páginas y para no depender del locale del sistema
  operativo para nombres de mes en español.

## Consecuencias

**Positivas:**
- El retrabajo de interfaz F4 queda fiel a un diseño concreto y ya revisado por el usuario, no a
  una interpretación textual del checklist de ARD-22 §7.
- Las revisiones al contrato quedan documentadas con su razón, no aplicadas en silencio — un
  lector futuro entiende por qué el badge de confianza ya no muestra `%` o por qué el timeline
  cambió su regla de color.
- La única adaptación al mockup tiene una razón objetiva (accesibilidad), no de preferencia, y
  reusa un patrón que el propio mockup ya emplea.
- La landing entra a scope con una decisión explícita sobre el acceso a Telegram (enlace
  condicional, sin handle inventado), en vez de quedar diferida sin resolver.

**Negativas:**
- Dos componentes que ARD-22 §7 marcaba como "no tocar" (`badges.py`, `timeline.py`) entran a
  scope de G7 — alcance mayor al planeado originalmente, aunque acotado a los cambios descritos
  arriba.
- La landing pasa a depender de una variable de entorno operativa nueva (`TELEGRAM_BOT_USERNAME`)
  que el equipo debe fijar para que el botón de Telegram aparezca; sin ella, la card queda
  informativa sin acción.

## Relación con otras decisiones

Ejecuta y extiende [ARD-22](ARD-22.md) (que sigue vigente en qué información se muestra por
persona); ARD-22 §7 queda como el checklist de contenido, este ARD como el registro de las
revisiones visuales que su ejecución (G7) encontró necesarias. Revisa puntualmente
[ARD-17](ARD-17.md) §5 en los tres puntos de la sección "a" (badge de confianza, score
redundante, hue del timeline), sin reabrir su paleta Okabe-Ito, su rampa de severidad ni sus
prohibiciones de tipo de gráfico. Consume [ARD-20](ARD-20.md) para el acceso a Telegram desde la
landing (enlace, no el canal en sí). No reabre [ADR-10](ARD-10.md) ni [ARD-21](ARD-21.md).
