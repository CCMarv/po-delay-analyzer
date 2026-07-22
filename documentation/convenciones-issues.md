# Convenciones del equipo — po-delay-analyzer

> Este documento recoge los **acuerdos del equipo**: cómo nombramos y clasificamos el
> trabajo, qué etiquetas usamos, cuándo algo es un issue / una discussion / un mensaje de
> chat, y bajo qué regla integramos a `main`. Es el *qué acordamos*, no el *cómo se teclea*.
>
> 📖 **El tutorial paso a paso de git/GitHub** (crear rama, commits, abrir PR, resolver
> conflictos, el flujo en comandos) vive en el post fijado de
> [Discussions → 📣 Anuncios → "Guía de git del equipo"](https://github.com/CCMarv/po-delay-analyzer/discussions/27).
> Lo movimos ahí porque es material de *onboarding operativo*, no descripción del
> proyecto: el repo describe el producto y su proceso de decisión; el tutorial de git
> vive donde el equipo se comunica.
>
> Objetivo de estos acuerdos: que cualquiera sepa de un vistazo qué es un ticket, quién
> lo tiene y en qué estado está — sin abrirlo y sin coordinación en vivo. Y que el
> resultado sea, además, documentación que el mentor pueda revisar.

---

## 0. El ciclo de vida de un cambio (el mapa)

Todo cambio recorre el mismo camino. Este documento cubre las **reglas** de cada etapa;
el **paso a paso en comandos** está en la [guía de git](https://github.com/CCMarv/po-delay-analyzer/discussions/27).

```
  gap / idea  →  issue(s)  →  rama  →  commits  →  PR + self-review  →  CI en verde
              →  merge (tú mismo, sin esperar aprobación)  →  issue cerrado
              →  (review cruzada opcional, DESPUÉS)
```

**Lo más importante de entender:** no esperamos aprobación de otra persona para mergear
(ver [§4](#4-la-regla-de-merge-no-bloqueante)).

---

## 1. De un gap a un issue

Un **gap** es cualquier cosa que detectas que el proyecto necesita: un bug, una mejora,
una pieza de pipeline que falta, un hallazgo del EDA que investigar, una decisión de
diseño pendiente, deuda técnica. El primer trabajo es **convertir ese gap en uno o
varios issues bien formados.**

### ¿Es uno o varios issues?
Un issue debería poder **cerrarse en medio día a un día**. Si al pensarlo ves que son
muchos pasos, que toca varias áreas, o que tiene partes que pueden avanzar por separado
→ **pártelo**. Tickets grandes son invisibles en el board y difíciles de repartir.

Ejemplo real: "arreglar la reproducibilidad del pipeline" no es un issue, son varios:
mover `requirements.txt` (#8), convertir `pipeline_core.py` en módulo (#9), cargar el CSV
local (#10), añadir tests (#12), CI (#13). Cada uno se cierra solo y desbloquea al
siguiente.

### Dependencias: qué espera a qué
Cuando partes un gap, casi siempre unos issues dependen de otros. Anótalo en el campo
*Dependencias* del issue, enlazando con `#N`:

- **`Depende de: #N`** — no puedo empezar (o terminar) hasta que `#N` cierre.
- **`Bloquea: #N`** — otros me están esperando a mí.

Esto importa **mucho** en un equipo asíncrono: GitHub dibuja el grafo de bloqueos, así
que quien entra a trabajar ve qué está libre y qué no, sin tener que preguntar. Un issue
también puede **abrir** otros: si mientras trabajas descubres algo nuevo, abre un issue
para ello y enlázalo (no lo metas a presión en el actual).

### ¿Es una tarea, un bug o una decisión?
Esto determina qué plantilla usas:

| Si el gap es… | Plantilla |
|---|---|
| Trabajo concreto a ejecutar (lo más común) | **Tarea** |
| Algo está mal y hay que arreglarlo | **Bug / Corrección** |
| Hay que **elegir** entre caminos antes de seguir | **Decisión** |

Regla: si no sabes *qué hacer* sino *qué decidir*, es una Decisión, no una Tarea.

---

## 2. Escribir el issue

### Elige la plantilla
Al hacer *New issue* en GitHub verás tres opciones (no se permite el issue en blanco, a
propósito: la plantilla te guía):

- **Tarea** — trabajo ejecutable. Pide área, fase, contexto, pasos, DoD, dependencias.
- **Bug / Corrección** — pide síntoma, cómo reproducir, esperado vs observado, evidencia.
- **Decisión** — pide quién decide, la pregunta, opciones con trade-offs.

#### Si creas el issue desde la terminal (`gh`)
Las plantillas de arriba son *Issue Forms* (`.yml`): GitHub solo las renderiza en la web
(con sus desplegables y campos obligatorios). `gh issue create` en terminal **no** puede
usarlas. Para no improvisar el issue, hay borradores espejo en
[`.github/plantillas-cli/`](../.github/plantillas-cli/) (`tarea.md` · `decision.md` · `bug.md`)
que reproducen las mismas secciones. El flujo:

```
cp .github/plantillas-cli/tarea.md /tmp/issue.md   # copia y rellena
gh issue create --title "[docs] ..." --label docs \
  --milestone "Fase 1 — Pipeline + EDA" --assignee "@me" --body-file /tmp/issue.md
```

La metadata que el formulario captura con desplegables va aquí como flags: `--label`
(área), `--milestone` (fase), `--assignee` (dueño). Lo único que se pierde es la
**validación obligatoria** del form: GitHub no te impedirá crear el issue con secciones
vacías, así que llenarlas bien es parte de tu self-review.

### Título: `[área] Verbo imperativo + objeto`
- **`[área]`** en minúsculas (las plantillas ya lo ponen): `pipeline` · `eda` ·
  `analisis` · `infra` · `docs` · `llm` · `app`.
- **Verbo + objeto concreto.** Sin punto final. Conciso.

| Fase | Título |
|------|--------|
| 1 | `[pipeline] Cargar el CSV desde data/raw/ local` |
| 1 | `[infra] Mover requirements.txt a la raíz y crear .env.example` |
| 2 | `[analisis] Definir taxonomía de etapas y mapear reglas` |
| 3 | `[llm] Diseñar prompt v1 con few-shot de casos match/mismatch` |
| 4 | `[app] Selector de PO → clasificación + explicación + acción` |

**Regla:** si no puedes escribir el título con un verbo + objeto claros, el ticket
probablemente es demasiado grande o vago — pártelo o acláralo.

### La metadata va en los campos de GitHub, no en el título

| Campo | Para qué | Cómo |
|-------|----------|------|
| **Milestone** | la **fase** | `Fase 1 — Pipeline + EDA`, etc. La fecha de vencimiento = el check-in del lunes. |
| **Assignee** | el **dueño** | Te lo auto-asignas cuando lo tomas (señal de "yo me encargo"), no al crear. |
| **Labels** | **área** + marcadores | una de área + 0 o más marcadores (ver abajo). |
| **Project** | el **estado** | columna del board (ver abajo). |

#### El board (4 columnas)
El estado de cada ticket es su columna en el board *"PO Delay Analyzer — Tablero"*:

| Columna | Significado |
|---------|-------------|
| **Todo** | En el backlog, nadie lo ha tomado. |
| **Assigned** | Tiene dueño (te auto-asignaste) pero aún no lo estás trabajando. |
| **In Progress** | Se está trabajando **ahora**. Es la señal de coordinación asíncrona: avisa al resto que el ticket está tomado. |
| **Done** | Mergeado e issue cerrado. |

> **La review cruzada NO es una columna.** El board va directo de *In Progress* a *Done*
> porque mergeamos sin esperar revisión (ver [§4](#4-la-regla-de-merge-no-bloqueante)).
> La review cruzada existe, pero es **posterior y opcional**: ocurre sobre `main` ya
> integrado, y si encuentra algo abre un issue de seguimiento — no es un paso del flujo.

#### Labels (lista cerrada — no agregar sin acordar)
- **Área (exactamente una):** `pipeline` · `eda` · `analisis` · `infra` · `docs` ·
  `llm` · `app`.
- **Marcadores (cero o más):**
  - `fundamental` — desbloquea a otros o está en la ruta crítica; tomar primero.
  - `decisión-equipo` — trade-off que **podemos resolver los 3 de forma asíncrona**, sin
    esperar al lunes. La plantilla de Decisión la pone sola.
  - `consulta-mentor` — trade-off que **necesita el criterio del mentor** → va a la
    reunión del lunes. Úsala solo cuando de verdad haga falta el mentor; la mayoría de
    decisiones las resolvemos entre nosotros.

> Dos niveles de decisión: el lunes es la reunión con **el mentor** (stakeholder externo),
> pero los 3 nos comunicamos cualquier día. No bloquees una decisión esperando al lunes
> si la podemos tomar entre nosotros — eso es `decisión-equipo`. Reserva `consulta-mentor`
> para lo que realmente requiere su visto bueno.

### La Definición de hecho (DoD)
La DoD responde **"¿cuándo está REALMENTE terminado?"** con criterios *verificables*, no
con "quedó bien". Se escriben como casillas `- [ ]` para que el progreso se vea en el
board sin abrir el código.

La última casilla es la **DoD global** y va en todos los tickets de trabajo:

> Corre en entorno limpio (`venv` desde `requirements.txt`) · CI en verde · self-review
> hecho · sin secrets/datos/outputs commiteados.

---

## 3. Trabajar el issue: rama, commits y PR

Estos son los **acuerdos**; el cómo está en la
[guía de git](https://github.com/CCMarv/po-delay-analyzer/discussions/27).

- **Una rama por issue, nunca trabajar directo en `main`.** Nombre:
  `tipo/<nombre>-<tarea-corta>` (`feat` · `fix` · `docs` · `chore`). Ej.
  `feat/vidaurri-csv-local`. La fase NO va en el nombre. El nombre se **propone desde el
  issue** (sección *Rama sugerida* del body), para que quien lo tome no lo improvise;
  puedes ajustarlo si hace falta al empezar.
- **Commits pequeños y frecuentes**, mensaje `area: descripción en imperativo (Closes #N)`.
  El `Closes #N` cierra el issue solo al mergear.
- **Nunca se commitea:** secrets / API keys (van en `.env`, gitignored) · el CSV de
  datos (`data/raw/` gitignored) · **outputs de notebooks** (límpialos antes de commit).
- **Al terminar abres un PR** con la plantilla (se rellena sola) y `Closes #N`.

---

## 4. La regla de merge no bloqueante

**No esperamos a que otro revise antes de mergear.** La práctica común dice lo contrario,
pero **para nosotros no funciona:** trabajamos en horarios muy desfasados (Vidaurri de
noche; María e Isaac de mañana). Si Vidaurri termina algo a las 2am y tiene que esperar a
que alguien lo revise en la mañana, ese cambio queda parado — y **bloquea el trabajo
secuencial** de quien depende de él. El equipo se frena.

Por eso el gate de merge eres **tú + CI**:

1. Completas el **self-review** del PR (corre en limpio, tests pasan, sin
   secrets/datos/outputs, DoD cumplida).
2. **Esperas a que CI pase en verde.**
3. **Mergeas tú mismo**, con *"Create a merge commit"*. Luego borras la rama; el issue se
   cierra solo y `main` queda en su estado ideal.

**La review cruzada sigue existiendo — pero es opcional y POSTERIOR.** Cuando otro
integrante tenga un rato, revisa PRs **ya mergeados** (sobre `main`). Si encuentra algo,
**abre un issue de seguimiento** — no revierte ni regaña. Así conservamos el segundo par
de ojos (que el mentor valora en la rúbrica: *Collaboration & Professionalism*) sin
frenar a nadie.

> ⚠️ Mientras **CI todavía no exista** (issues #12 y #13), el gate temporal es:
> self-review + "tests/pipeline pasan en local" verificado a mano. Montar CI es
> prioritario: es la red de seguridad que sustituye al revisor humano.

El paso a paso de PR, merge y resolución de conflictos está en la
[guía de git](https://github.com/CCMarv/po-delay-analyzer/discussions/27).

---

## 5. Discussions: la memoria del equipo

No todo lo que el equipo comunica es trabajo: hay dudas, debates que aún no maduran y
anuncios. Meter eso en issues los ensucia; dejarlo solo en el chat lo pierde. Para eso
está **GitHub Discussions**: comunicación asíncrona que **deja memoria buscable**, fuera
del board y fuera del chat efímero.

### Las tres vías — cuándo usar cada una

| Vía | Para qué | Persistencia |
|-----|----------|--------------|
| **Issue** | Trabajo a ejecutar, o una decisión ya planteada que deja rastro accionable (board, DoD, `Closes #N`). | Permanente, **en el board**. |
| **Discussion** | Una duda con respuesta reutilizable · debatir un trade-off que **aún no madura** · un anuncio. | Permanente, **buscable**, fuera del board. |
| **Chat** | Desbloqueo inmediato, coordinación del momento ("¿alguien está tocando el notebook?"). | **Efímero** — se pierde al scrollear. |

**Regla de oro:** *si dentro de un mes alguien va a querer encontrar esto, no va al
chat.* Y si además ya es **trabajo concreto o una decisión planteada**, no es una
discussion: es un **issue**.

### Las 3 categorías

- **📣 Anuncios** — lo del lunes con el mentor, acuerdos del equipo, cambios de rumbo.
  Es el tablón: se lee, no se debate. (Aquí vive la
  [guía de git fijada](https://github.com/CCMarv/po-delay-analyzer/discussions/27).)
- **🤔 Decisiones (debate)** — pensar en voz alta un trade-off **antes** de que sea un
  issue de Decisión formal. El hilo es la memoria del *porqué*.
- **❓ Dudas / Q&A** — preguntas con respuesta reutilizable. Se marca la respuesta
  correcta para que quede buscable para el siguiente que tenga la misma duda.

### El puente Discussion → Issue (importante, evita el solape)

Una duda razonable: *si ya tengo la plantilla [Decisión](#1-de-un-gap-a-un-issue), ¿para
qué "🤔 Decisiones (debate)" en Discussions?* Porque son dos momentos distintos:

- **Discussions = pensar en voz alta.** El trade-off aún es difuso, no hay opciones
  claras, estás tanteando con el equipo. Un issue de Decisión aquí sería prematuro
  (¿qué opciones pones si todavía no las tienes?).
- **Issue de Decisión = la decisión registrada.** Cuando el debate madura —ya hay
  opciones con sus trade-offs y algo bloquea—, el hilo **se gradúa**: abres un issue con
  la plantilla [Decisión](../.github/ISSUE_TEMPLATE/2-decision.yml), enlazas el hilo en
  el contexto, y ahí queda la elección formal (con sus labels `decisión-equipo` /
  `consulta-mentor` y lo que bloquea).

Así no se duplica: Discussions guarda el *cómo llegamos a pensarlo*; el issue guarda *qué
se decidió*.

---

## 6. Sincronización del equipo

- **Lunes 9:00 = reunión con el mentor** (stakeholder externo): sprint review + planning,
  y se resuelven los issues con `consulta-mentor`.
- **Entre los 3, cualquier día:** comunicación asíncrona por el chat para decisiones
  `decisión-equipo`, desbloqueos y dudas rápidas.
- **El board es la señal de coordinación.** Mover a *In Progress* antes de empezar avisa
  al resto que alguien tomó el ticket. Las *Notas* del issue son el handoff: si trabajas
  mientras los demás duermen, eso es tu entrega.

---

## 7. Referencia rápida (cheat-sheet)

### ¿Issue, Discussion o chat?
| Lo que vas a comunicar… | Vía |
|---|---|
| Trabajo a ejecutar o una decisión ya planteada | **Issue** |
| Duda con respuesta reutilizable · debate aún no maduro · anuncio | **Discussion** |
| Desbloqueo inmediato y efímero | **Chat** |

### ¿Qué plantilla uso? (si es un issue)
| El gap es… | Plantilla |
|---|---|
| Trabajo a ejecutar | **Tarea** |
| Algo está mal | **Bug / Corrección** |
| Hay que elegir | **Decisión** |

### Labels
`pipeline` · `eda` · `analisis` · `infra` · `docs` · `llm` · `app` (área, una) ·
`fundamental` · `decisión-equipo` · `consulta-mentor` (marcadores).

### El cómo (git paso a paso)
Crear rama, commits, PR, merge y conflictos →
[Guía de git del equipo (Discussions)](https://github.com/CCMarv/po-delay-analyzer/discussions/27).
