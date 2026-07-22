# Roadmap de trabajo futuro: localización, temas/modo oscuro y chatbot conversacional

* **Estatus:** 🔵 **Borrador** (considerado / diferido — lo cierra el equipo)
* **Contexto Técnico:** Fase 4 / cierre — alcance de mejoras post-entregable; insumo directo
  del roadmap de la presentación final
* **Referencias:** sesión de definición (2026-07-20); [ADR-17](ARD-17.md) (sistema de
  diseño), [ADR-16](ARD-16.md) (#160, carril 3 agéntico), [ADR-20](ARD-20.md) (bot de
  Telegram vs. chatbot diferido), [ADR-18](ARD-18.md) (documentación bilingüe); commit
  `c726f23` (lock a tema claro); `04_app/`

## Contexto y Problema

El entregable evaluado es la app Streamlit (`04_app/`, bloqueada en tema claro, interfaz en
español, solo-lectura sobre CSV congelado) más el bot de Telegram de comandos fijos. Durante
el cierre surgieron tres frentes de mejora que exceden el alcance del entregable pero orientan
su evolución. Declararlos como trabajo futuro en la presentación evita improvisar el roadmap
en vivo y deja trazado por qué quedan fuera del entregable actual. Este registro los define y
dimensiona; no compromete su ejecución.

## Los tres frentes

**1. Localización (app bilingüe ES/EN).** La interfaz está en español; las categóricas
(`severity`, `stage`, `llm_confianza`) ya se almacenan como código/escalar y la app asigna la
etiqueta, por lo que localizarlas es trivial (añadir el catálogo de labels en inglés). El
chrome de la UI (~1–1.5 días de extracción de strings a un catálogo `es/en` con un helper
`t()` y un selector de idioma) funciona bien en Streamlit, ya que un selector sí dispara
rerun. El costo real es el texto libre del LLM (`explanation`, `action`,
razonamiento/hipótesis/acciones), generado en español: una app genuinamente en inglés exige
decidir entre re-generar esos outputs en inglés (cambio de datos, costo de API), traducirlos
offline, o aceptar una interfaz mixta.

**2. Temas / modo oscuro.** La app quedó bloqueada en claro (`c726f23`) porque Streamlit no
permite un toggle manual instantáneo con CSS propio: usa emotion/React sin un hook estable en
el DOM, y cambiar el tema nativo no ejecuta el script Python, por lo que la inyección de
tokens queda desfasada. Un toggle manual claro/oscuro con fidelidad a los mockups requiere una
capa de presentación fuera de Streamlit (exportación estática HTML/CSS/JS, ~3–4 días), donde
el tema se resuelve con `[data-theme]` + `localStorage`.

**3. Chatbot conversacional (#160, carril 3 de [ADR-16](ARD-16.md)).** Distinto del bot de
Telegram ya entregado (comandos fijos de solo-lectura sobre datos pre-calculados, sin LLM en
tiempo de consulta; ver [ADR-20](ARD-20.md)). El chatbot es Q&A en lenguaje libre donde el LLM
razona sobre el dataset en tiempo de consulta, con guardrails contra alucinación y para
acotarse al dataset. Es el frente más grande: exige una capa agéntica/recuperación, estado
conversacional y costo de API por consulta (no batch). Puede evolucionar desde la
infraestructura existente del bot (`bot.py` ya tiene `MessageHandler` para texto libre) o
como una vista nueva en la app.

## Opciones Consideradas

**Opción A — No declarar el trabajo futuro.** Deja la presentación sin roadmap y arriesga que
un evaluador interprete los límites actuales (español, claro, comandos fijos) como carencias
sin dirección. Descartada.

**Opción B — Declararlo como trabajo futuro / mejoras potenciales, sin compromiso de fechas
(elegida).** Presenta los tres frentes como evolución posible del entregable, dejando claro
que lo evaluado es la app actual. Es honesto con el calendario y traza la dirección sin
comprometer entregas.

**Opción C — Roadmap con fechas y prioridades comprometidas.** Descartada: el calendario de
cierre no permite comprometer fechas y elevaría el riesgo de la presentación.

## Decisión

Se declaran los tres frentes como trabajo futuro / mejoras potenciales, sin compromiso de
fechas. Supuestos asumidos para el roadmap: la app bilingüe se fija como objetivo futuro (con
la decisión de contenido del LLM pendiente); el bot de Telegram se presenta como capacidad
entregada y el chatbot conversacional (#160) como evolución futura diferida, coherente con
[ADR-20](ARD-20.md) y [ADR-16](ARD-16.md).

## Consecuencias

**Positivas:** queda un roadmap trazado que alimenta directamente la slide de trabajo futuro
de la presentación y explica los límites del entregable como decisiones, no omisiones.

**Negativas:** permanecen abiertas la decisión sobre el contenido del LLM para i18n
(re-generar vs. traducir vs. mixto) y el costo de API por consulta del chatbot. Se mantiene
como principio de contrato para fases futuras que el dato guarde el código y la app asigne la
etiqueta, lo que abarata la localización de campos categóricos.

**Pendiente:** la consolidación con candidatos adicionales de una sesión exploratoria de
roadmap (vetas sugeridas: despliegue/hosting, performance/caching, cobertura de tests/CI,
accesibilidad más allá del color, exportación/reporte, hardening de auth/seguridad,
observabilidad, carriles 2 agéntico y juez local abiertos en ADR-16, deuda de duplicación de
capa de datos de ADR-20, gap Late Shipment/`VENDOR_SHIP_DT` ya cerrado por
[ADR-24](ARD-24.md)) queda fuera de este registro y se resuelve en una sesión futura; este ARD
documenta únicamente los tres frentes ya decididos.

## Relación con otras decisiones

No supera ningún ARD previo. Consume el sistema de diseño de **ADR-17**, la distinción entre
el bot de Telegram entregado y el chatbot diferido de **ADR-20**/**ADR-16** (carril 3), y la
política de idioma de **ADR-18**. No reabre **ADR-24** (regla Late Shipment, ya cerrada).
