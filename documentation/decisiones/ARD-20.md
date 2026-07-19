# Bot de Telegram como canal adicional de consumo

* **Estatus:** 🔵 **BORRADOR** (lo cierra el equipo)
* **Contexto Técnico:** Fase 4 / App — canal de consumo alternativo a Streamlit, vía Telegram
* **Referencias:** PR #193 (alta del bot), PR #194 (SAD/SRS), Issue #196 (documentar el bot como
  canal adicional — retrofit); Issue #160 (chatbot conversacional diferido, distinción con esta
  decisión); ADR-09 (user personas Diego/Ravi); `04_app/telegram_bot/` (`bot.py`, `config.py`,
  `services/auth.py`, `services/data_service.py`, `handlers/diego.py`, `handlers/ravi.py`)

## Contexto y Problema

Streamlit exige abrir una sesión de navegador. Las dos personas de ADR-09 no siempre están frente
a un dashboard: Diego consulta por PO puntual mientras trabaja en otro sistema; Ravi quiere un
vistazo agregado sin abrir la app. Un bot de Telegram (PR #193) llegó por fuera del board
(sin issue previo) implementando exactamente esa necesidad — 13 archivos versionados bajo
`04_app/telegram_bot/`, funcionales, con la misma capa de datos que consume `04_app` — pero sin
ningún ARD ni mención en el README raíz, que declara "Chatbot diferido" en la sección de estado
de fases. Un lector puede razonablemente confundir ese rótulo con el bot ya construido, cuando en
realidad se refiere a una capacidad distinta (ver más abajo). La auditoría de cierre lo marcó
como una decisión de peso viviendo en código sin registro (H3.12, H2.8).

## Distinción con #160 (el "chatbot diferido")

Son dos capacidades distintas que comparten la palabra "bot":

- **#160** — "Chatbot conversacional sobre los diagnósticos". Es Q&A **abierta**: el usuario
  pregunta en lenguaje libre y el LLM razona sobre el dataset en tiempo de consulta. Corresponde
  al carril 3 agéntico de [ARD-16](ARD-16.md) y sigue **explícitamente diferido** — no forma
  parte de este entregable.
- **El bot de Telegram** (este ARD) expone **comandos fijos y estructurados** —
  `/po`, `/timeline`, `/alertas`, `/hot` (perfil Diego); `/kpi`, `/scorecards`, `/distribucion`,
  `/tendencia`, `/mismatches`, `/mismatches_chart` (perfil Ravi); `/start` y `/help` comunes— que
  leen datos **ya calculados** (`po_output.csv`, los scorecards de [ARD-19](ARD-19.md)) sin
  invocar al LLM en tiempo de consulta. No hay razonamiento libre ni conversación abierta: es un
  segundo front-end sobre el mismo contrato de datos de Fase 4.

Confundirlas llevaría a creer que el chatbot conversacional (#160) ya existe, o a que el bot de
Telegram (ya construido) se considere fuera de alcance por error.

## Opciones Consideradas

**Opción A — No documentarlo (tratarlo como exploratorio, fuera del entregable formal).**
Pros: no exige trabajo adicional de documentación. Contras: es código versionado, funcional,
que expone datos reales del dataset con un modelo de autorización propio; ocultarlo no lo hace
desaparecer — un evaluador que explore el repo lo encuentra sin contexto (como ya documentó la
auditoría), y el README seguiría afirmando lo contrario de lo que hay en disco.

**Opción B — Documentarlo como canal de consumo entregable (elegida).** Refleja la realidad del
repo: el bot ya pasó por la corrección de sus dos bugs de autorización (`_REPO_ROOT` resuelto a
la raíz real del repo, `is_authorized` fail-closed cuando la whitelist está vacía — ambos
corregidos en la unidad de robustez previa a este ARD) y es funcional. Documentarlo da
trazabilidad, permite auditar su superficie de datos, y cierra la brecha que #196 pide resolver.
Contras: hace explícita una deuda ya existente — duplica la capa de datos de `04_app/`
(`data_service.py`, lista de columnas canónicas) en vez de compartirla; ver Consecuencias.

## Decisión

El bot de Telegram es un **canal adicional de consumo** de los mismos artefactos que produce la
Fase 3 (`po_output.csv`, scorecards) — no un producto nuevo ni el chatbot conversacional de
#160. Se documenta como entregable:

1. Este ARD registra la arquitectura (comandos por perfil, gate de autorización) y la distinción
   con #160.
2. La propagación a superficies de descubrimiento (README raíz, árbol de directorios, SAD/SRS) es
   trabajo de sincronización documental de otra unidad (G8 del ledger de cierre) — este ARD es la
   fuente de la decisión, no el lugar donde se actualizan esas superficies.
3. Un README propio de `04_app/telegram_bot/` (hoy inexistente) queda como follow-up natural de
   #196, fuera del alcance de esta reconciliación.

## Consecuencias

**Positivas:**
- Cierra la brecha de trazabilidad que detectó la auditoría: una decisión de arquitectura que
  vivía solo en código ahora tiene registro.
- Da un criterio explícito para no confundir este canal con el chatbot conversacional diferido.
- El gate de autorización (`require_auth` + `require_profile`) ya es fail-closed: whitelist vacía
  = nadie autorizado, en vez del fail-open que tenía antes de la corrección de robustez.

**Negativas:**
- **Duplicación de la capa de datos** (deuda, no resuelta aquí): `telegram_bot/services/data_service.py`
  y `telegram_bot/config.py` reimplementan la carga del artefacto y la lista de columnas
  canónicas en vez de compartirlas con `04_app/services/data_service.py` y `04_app/config.py`.
  Las dos copias del contrato divergirán a la primera columna nueva si no se comparten. Candidato
  a refactor futuro, no bloqueante para este entregable.
- Segunda superficie de autorización que mantener sincronizada con las variables de `.env`
  (`TELEGRAM_USER_WHITELIST`, `TELEGRAM_RAVI_USER_IDS`) además del flujo de Streamlit.

## Relación con otras decisiones

No supera ningún ARD previo. Consume el contrato de datos de [ARD-21](ARD-21.md) (tier-1/tier-2
de `po_output.csv`) y los scorecards de [ARD-19](ARD-19.md). Sirve a las personas Diego/Ravi de
**ADR-09** por un canal distinto al de Fase 4 (Streamlit). Se distingue explícitamente del
carril 3 conversacional de **ARD-16** (#160, diferido).
