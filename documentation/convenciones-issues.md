# Convenciones y flujo de trabajo — po-delay-analyzer

> Esta guía explica **cómo trabajamos juntos en el repo de principio a fin**: desde que
> detectas algo que hay que hacer hasta que ese cambio vive en `main`. Está escrita
> asumiendo que tienes base de programación pero **poca práctica con git/GitHub y con
> gestión de proyectos** — por eso explica el *porqué* de cada paso, no solo el *cómo*.
>
> Objetivo: que cualquiera sepa de un vistazo qué es un ticket, quién lo tiene y en qué
> estado está — sin abrirlo y sin coordinación en vivo. Y que el resultado sea, además,
> documentación que el mentor pueda revisar.

---

## 0. El ciclo de vida de un cambio (el mapa completo)

Todo cambio en el proyecto recorre el mismo camino. Tenlo en la cabeza; el resto del
documento detalla cada paso.

```
  gap / idea          (detectas algo: un bug, una mejora, un hallazgo, una decisión)
      │
      ▼
  issue(s)            (lo escribes con una plantilla; lo partes y enlazas dependencias)
      │
      ▼
  rama                (creas una rama desde main para trabajarlo)
      │
      ▼
  commits             (avanzas en commits pequeños y descriptivos)
      │
      ▼
  PR + self-review    (abres Pull Request, completas tu propio checklist)
      │
      ▼
  CI en verde         (los tests pasan automáticamente)
      │
      ▼
  merge               (lo integras tú mismo a main — sin esperar a nadie)
      │
      ▼
  issue cerrado       (el "Closes #N" del PR lo cierra solo; main queda al día)
      │
      ▼
  (review cruzada opcional, DESPUÉS, cuando alguien esté disponible)
```

**Lo más importante de entender:** no esperamos aprobación de otra persona para mergear.
Lo explicamos en el [Paso 5](#5-paso-5--pr-self-review-y-merge-no-bloqueante).

---

## 1. Paso 1 — De un gap a un issue

Un **gap** es cualquier cosa que detectas que el proyecto necesita: un bug, una mejora,
una pieza de pipeline que falta, un hallazgo del EDA que hay que investigar, una decisión
de diseño pendiente, deuda técnica. El primer trabajo es **convertir ese gap en uno o
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
Esto determina qué plantilla usas (ver siguiente paso):

| Si el gap es… | Plantilla |
|---|---|
| Trabajo concreto a ejecutar (lo más común) | **Tarea** |
| Algo está mal y hay que arreglarlo | **Bug / Corrección** |
| Hay que **elegir** entre caminos antes de seguir | **Decisión** |

Regla: si no sabes *qué hacer* sino *qué decidir*, es una Decisión, no una Tarea.

---

## 2. Paso 2 — Escribir el issue

### Elige la plantilla
Al hacer *New issue* en GitHub verás tres opciones (no se permite el issue en blanco, a
propósito: la plantilla te guía):

- **Tarea** — trabajo ejecutable. Pide área, fase, contexto, pasos, DoD, dependencias.
- **Bug / Corrección** — pide síntoma, cómo reproducir, esperado vs observado, evidencia.
- **Decisión** — pide quién decide, la pregunta, opciones con trade-offs.

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
| **Assignee** | el **dueño** | Te lo auto-asignas **al empezar** (señal de "yo me encargo"), no al crear. |
| **Labels** | **área** + marcadores | una de área + 0 o más marcadores (ver abajo). |
| **Project** | el **estado** | columna del board: Todo / In Progress / Review / Done. |

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

## 3. Paso 3 — Crear la rama

**Nunca trabajes directo en `main`.** `main` es la versión "buena" del proyecto; tu
trabajo en curso vive en una **rama** aparte hasta que esté listo. Una rama por issue.

**Convención de nombre:** `tipo/<nombre>-<tarea-corta>`

- **tipo:** `feat` (algo nuevo) · `fix` (arreglo) · `docs` (documentación) · `chore`
  (mantenimiento/infra).
- **nombre:** tu identificador (ej. `vidaurri`, `maria`, `isaac`).
- **tarea-corta:** 2–4 palabras con guiones.

Ejemplos: `feat/vidaurri-csv-local` · `fix/maria-carrier-nan` · `docs/isaac-readme`.
La fase NO va en el nombre (se infiere del milestone y la carpeta).

**Cómo crearla** (siempre desde un `main` actualizado, para no partir de algo viejo):

```bash
git checkout main
git pull                          # traes lo último de main
git checkout -b feat/tu-nombre-tarea-corta
```

---

## 4. Paso 4 — Commits

Un **commit** es una foto guardada de tu avance. Haz commits **pequeños y frecuentes**:
es más fácil entender (y deshacer) cambios chicos que un commit gigante al final.

**Mensajes** — formato corto, alineado con lo que ya hay en el repo:

```
area: descripción breve en imperativo (Closes #N)
```

Ejemplos reales del repo:
- `pipeline: cargar CSV desde data/raw/ local con PO_CSV_PATH (Closes #11)`
- `infra: mover requirements.txt a la raíz, completarlo y crear .env.example`

`Closes #N` en el commit (o en el PR) hace que GitHub **cierre el issue solo** al
mergear. Ponlo en el commit final o en la descripción del PR.

**Qué NO se commitea nunca:**
- Secrets / API keys (van en `.env`, que está en `.gitignore`).
- El CSV de datos (`data/raw/` está gitignored — cada quien coloca el suyo).
- **Outputs de los notebooks** (limpia las salidas antes de commitear — ver
  [conflictos de notebooks](#conflictos-en-notebooks-ipynb)).

---

## 5. Paso 5 — PR, self-review y merge (NO bloqueante)

Cuando tu trabajo está listo, abres un **Pull Request (PR)**: la propuesta de meter tu
rama a `main`. Usa la plantilla de PR (se rellena sola) y pon `Closes #N`.

### Por qué NO esperamos a que otro revise antes de mergear
La práctica común dice "que otro revise tu PR antes de mergear". **Para nosotros eso no
funciona:** trabajamos en horarios muy desfasados (Vidaurri de noche; María e Isaac de
mañana). Si Vidaurri termina algo a las 2am y tiene que esperar a que alguien lo revise
en la mañana, ese cambio queda parado — y **bloquea el trabajo secuencial** de quien
depende de él. El equipo se frena.

Por eso nuestro modelo es **merge no bloqueante**:

1. **El gate de merge eres tú + CI.** Completas el *self-review* del PR (corre en limpio,
   tests pasan, CI en verde, sin secrets/datos/outputs, DoD cumplida).
2. **Esperas a que CI pase en verde** (los tests automáticos).
3. **Mergeas tú mismo.** Sin esperar aprobación.

### La review cruzada sigue existiendo — pero es opcional y POSTERIOR
Que no bloquee no significa que desaparezca. Cuando otro integrante tenga un rato, revisa
PRs **ya mergeados** (sobre `main`). Si encuentra algo, **abre un issue de seguimiento**
— no revierte ni regaña. Así conservamos el segundo par de ojos (que el mentor valora en
la rúbrica: *Collaboration & Professionalism*) sin frenar a nadie.

### Si CI falla o tu self-review detecta algo
No es un rechazo. Empuja más commits de arreglo a **la misma rama** (el PR se actualiza
solo), CI vuelve a correr, y mergeas cuando esté verde.

### Estrategia de merge: **Merge commit**
Al mergear, GitHub ofrece varias opciones; usamos **"Create a merge commit"**. Esto
conserva todos los commits de tu rama y añade un commit de unión (verás
`Merge pull request #N…` en el historial, como ya pasa en el repo). El historial se
"ramifica y vuelve a unir": es más fiel a cómo trabajamos y evita reescribir historia
(que es lo arriesgado para quien empieza).

> ⚠️ Mientras **CI todavía no exista** en el repo (pendiente en los issues #12 y #13), el
> gate temporal es: self-review + "tests/pipeline pasan en local" verificado a mano.
> Montar CI es prioritario justamente porque es la red de seguridad que sustituye al
> revisor humano.

---

## 6. Paso 6 — Resolución de conflictos

### Por qué ocurren
Un conflicto pasa cuando **dos ramas tocan las mismas líneas**, o cuando `main` avanzó
mientras tú trabajabas y git no sabe cuál versión quedarse. Es normal y se resuelve; no
es que hayas roto nada.

### Flujo seguro (para novatos)
La idea: **trae `main` a tu rama**, resuelve ahí, vuelve a probar, y luego mergeas.

```bash
git checkout main
git pull                          # main al día
git checkout tu-rama
git merge main                    # trae main a tu rama; aquí pueden aparecer conflictos
# ...resuelves los conflictos (abajo)...
git add <archivos-resueltos>
git commit                        # cierra el merge
# vuelve a correr tests / pipeline antes de empujar
git push
```

> Usamos `git merge`, **no `git rebase`**. Rebase reescribe la historia y es fácil
> hacerse un lío siendo principiante. Merge es más seguro aunque deje un commit de unión.

### Conflictos en código
Git marca el conflicto dentro del archivo así:

```
<<<<<<< HEAD
   (lo que hay en tu rama)
=======
   (lo que viene de main)
>>>>>>> main
```

Editas el bloque para dejar la versión correcta (la tuya, la de main, o una combinación
de ambas), **borras las líneas de marcadores** `<<<<<<<`, `=======`, `>>>>>>>`, guardas,
y haces `git add`. **Antes de commitear, vuelve a correr los tests / el pipeline**: un
conflicto mal resuelto compila pero rompe la lógica.

### Conflictos en notebooks (.ipynb)
Los notebooks son el caso más feo. **Por qué:** un `.ipynb` no es texto — es un JSON que
guarda el código **y** los outputs **y** metadata de ejecución (números de celda,
imágenes en base64…). Git intenta hacer merge de ese JSON línea por línea y produce un
desastre ilegible. Por eso lo atacamos **previniéndolo**, no resolviéndolo.

**Convención preventiva del equipo:**

1. **Un notebook = un dueño por sesión.** Si vas a tocar un notebook, asegúrate de que
   nadie más lo tiene *In Progress* en el board. Coordínalo en el chat antes de empezar.
   Trabajar el mismo notebook en paralelo es pedir un conflicto.
2. **Limpia los outputs antes de cada commit.** Así el diff es solo de código y se
   reducen los conflictos drásticamente:
   - En Jupyter/VS Code: *Kernel → Restart & Clear All Outputs* antes de guardar.
   - O por terminal: `jupyter nbconvert --clear-output --inplace tu_notebook.ipynb`.
3. **No commitees datos pesados ni imágenes generadas** dentro del notebook.

**Si aun así hay conflicto en un .ipynb:**
- **No edites el JSON a mano.** Te quedas con **una** versión completa del notebook (la
  tuya o la de `main`):
  ```bash
  git checkout --theirs tu_notebook.ipynb   # te quedas con la de main
  # o --ours para quedarte con la tuya
  git add tu_notebook.ipynb
  ```
- Vuelve a aplicar **a mano** los cambios de la otra versión, en las celdas
  correspondientes.
- **Re-ejecuta el notebook limpio** de principio a fin para confirmar que corre.
- **Documenta en las *Notas* del issue** qué versión conservaste y qué reaplicaste, para
  que el equipo sepa qué pasó.

> Opcional (recomendado si tocas notebooks seguido): instala
> [`nbdime`](https://nbdime.readthedocs.io/) — da diffs y merges de notebooks legibles
> (`nbdiff`, `nbmerge`). No es obligatorio.

---

## 7. Paso 7 — Merge, cierre y el estado ideal de `main`

Cuando mergeas (merge commit) con `Closes #N` en el PR:

- El **issue se cierra solo** y pasa a *Done* en el board.
- **Borra la rama** (GitHub ofrece el botón *Delete branch* tras mergear): ya cumplió su
  función.
- `main` queda en su **estado ideal**: completo, reproducible (corre en entorno limpio),
  sin secrets ni datos. Quien parta de `main` parte de algo sano.

La review cruzada, si ocurre, sucede **después** y sobre `main` ya integrado — nunca
bloquea este cierre.

---

## 8. Sincronización del equipo

- **Lunes 9:00 = reunión con el mentor** (stakeholder externo): sprint review + planning,
  y se resuelven los issues con `consulta-mentor`.
- **Entre los 3, cualquier día:** comunicación asíncrona por el chat para decisiones
  `decisión-equipo`, desbloqueos y dudas rápidas.
- **El board es la señal de coordinación.** Mover a *In Progress* antes de empezar avisa
  al resto que alguien tomó el ticket. Las *Notas* del issue son el handoff: si trabajas
  mientras los demás duermen, eso es tu entrega.

---

## 9. Referencia rápida (cheat-sheet)

### ¿Qué plantilla uso?
| El gap es… | Plantilla |
|---|---|
| Trabajo a ejecutar | **Tarea** |
| Algo está mal | **Bug / Corrección** |
| Hay que elegir | **Decisión** |

### Labels
`pipeline` · `eda` · `analisis` · `infra` · `docs` · `llm` · `app` (área, una) ·
`fundamental` · `decisión-equipo` · `consulta-mentor` (marcadores).

### El flujo en comandos
```bash
git checkout main && git pull                 # parte de main al día
git checkout -b feat/tu-nombre-tarea          # rama por issue
# ...trabajas...
git add -A && git commit -m "area: qué hiciste (Closes #N)"
git push -u origin feat/tu-nombre-tarea       # sube la rama
# abres el PR en GitHub (plantilla + Closes #N) → self-review → CI verde → mergeas tú
# borras la rama; el issue se cierra solo
```

### Si hay conflicto
```bash
git checkout main && git pull
git checkout tu-rama && git merge main        # resuelve, borra marcadores, re-prueba
```
Notebooks: un dueño por sesión, limpia outputs antes de commit, no edites el JSON a mano.

---


