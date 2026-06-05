# Convención de issues — po-delay-analyzer

> Estándar para crear tickets en **todas las fases**. Objetivo: que cualquiera sepa
> de un vistazo qué es un ticket, quién lo tiene y en qué estado está — sin abrirlo y
> sin necesidad de coordinación en vivo.

---

## 1. Título: `[área] Verbo imperativo + objeto`

- **`[área]`** en minúsculas: `pipeline` · `eda` · `analisis` · `infra` · `docs` · `llm` · `app`.
- **Verbo imperativo + objeto concreto.** Sin punto final. Conciso.

Ejemplos (una por fase, para ver que la convención escala):

| Fase | Título |
|------|--------|
| 1 | `[pipeline] Convertir pipeline_core.py en módulo importable` |
| 1 | `[infra] Cerrar la higiene del repo (master, requirements, .env.example)` |
| 2 | `[analisis] Definir taxonomía de etapas y mapear reglas` |
| 3 | `[llm] Diseñar prompt v1 con few-shot de casos match/mismatch` |
| 4 | `[app] Selector de PO → clasificación + explicación + acción` |

**Regla:** si no puedes escribir el título con un verbo + objeto claros, el ticket
probablemente es demasiado grande o demasiado vago — pártelo o acláralo.

---

## 2. La metadata va en los campos de GitHub, no en el título

| Campo | Para qué | Cómo |
|-------|----------|------|
| **Milestone** | la **fase** | `Fase 1 — Pipeline + EDA`, etc. Fecha de vencimiento = el check-in del lunes. |
| **Assignee** | el **dueño** | Te lo auto-asignas **al empezar** (señal de "yo me encargo"). |
| **Labels** | **área** + marcadores | una de área + 0 o más marcadores (ver abajo). |
| **Project** | el **estado** | columna del board: Todo / In Progress / Done. |

### Labels (lista cerrada — no agregar sin acordar)

- **Área (exactamente una):** `pipeline` · `eda` · `analisis` · `infra` · `docs` · `llm` · `app`
- **Marcadores (cero o más):**
  - `fundamental` — desbloquea a otros o está en la ruta crítica; tomar primero.
  - `decisión-equipo` — implica un trade-off de diseño; resolver en la reunión del lunes.

---

## 3. Estructura del cuerpo (plantilla)

```markdown
## Contexto
_Por qué existe este ticket (1–3 líneas). Borrar si es obvio por el título._

## Tarea
- [ ] Paso concreto 1
- [ ] Paso concreto 2

## Definición de hecho
- [ ] Criterio verificable y específico
- [ ] (otro criterio)
- [ ] Corre en entorno limpio (`venv` desde `requirements.txt`) · review cruzada · sin secrets/datos commiteados

## Dependencias
Depende de: #
Bloquea: #

## Notas / hallazgos
_Se llena mientras se trabaja. Es el handoff asíncrono: lo que decidiste,
lo que descubriste, lo que el siguiente necesita saber._
```

- **Definición de hecho con `- [ ]`:** se ven como casillas marcables → progreso visible
  sin abrir el código. La última línea es la *DoD global*, va en todos los tickets.
- **Dependencias con `#`:** enlazar issues (`Depende de: #12`) hace que GitHub muestre el
  grafo de bloqueos. Clave para que un equipo asíncrono no choque.
- **Notas:** si trabajas mientras los demás duermen, esto es tu entrega.

---

## 4. Flujo de trabajo (asíncrono)

1. **Tomar = auto-asignarte + mover a *In Progress*.** ANTES de empezar, no después.
2. **Rama por tarea:** `feat/<inicial>-<tarea-corta>` (ej. `feat/vid-pipeline-core-modulo`).
   La fase se infiere de la carpeta y del milestone, no del nombre de la rama.
3. **PR cierra el issue:** pon `Closes #N` en la descripción del PR → al mergear, el issue
   se cierra y pasa a *Done* solo.
4. **Review cruzada obligatoria** antes de mergear a `main`.
5. **Lunes 9:00 = review + planning:** revisar lo hecho, resolver los `decisión-equipo`,
   dejar claro el backlog de la semana.

---

## 5. Tamaño de un ticket (cuándo partir)

Un ticket debería poder cerrarse en **medio día a un día** de trabajo. Si la "Tarea"
tiene más de ~5 pasos o toca varias áreas, pártelo. Tickets grandes = invisibles en el
board y difíciles de repartir.
