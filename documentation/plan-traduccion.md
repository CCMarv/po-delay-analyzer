# Plan de traducción ES→EN de los entregables

Este documento fija el plan de traducción de la documentación del proyecto al inglés. No
traduce nada: define el alcance, el orden, el disparador y el método de mantenimiento, y
deja constancia de que la traducción se difiere de forma deliberada.

La rúbrica de evaluación (audiencia mixta) y el kickoff del mentor piden entregables
bilingües ES + EN; el propio repositorio del mentor publica el kickoff en ambos idiomas como
artefactos paralelos. Hoy toda la documentación está en español. Traducir antes de que los
mentores validen la doc ES duplicaría el trabajo cada vez que se corrija el original, por lo
que la decisión del equipo es diferir la traducción hasta que el fuente ES esté validado y
estable (probable Fase 4). Este plan existe para que ese diferimiento sea una decisión
consciente y no un olvido, y para que la traducción se active en el momento correcto.

## Alcance

El alcance mínimo viable es lo que el mentor lee primero para evaluar:

- Reporte final.
- Presentación.
- README raíz.

El alcance ideal añade, si el tiempo lo permite tras completar el mínimo:

- README de fase.
- Data dictionary (`documentation/data_dictionary.md`).

Queda fuera de alcance la documentación interna de proceso: notas locales de trabajo,
registros de decisiones (ADRs) y el código. Estos sirven al equipo, no a la evaluación
bilingüe, y su traducción no aporta al entregable.

## Orden

La traducción avanza de afuera hacia adentro, empezando por lo que el mentor evalúa primero:

1. Portada / README raíz.
2. Reporte final y presentación.
3. README de fase.
4. Data dictionary.

El orden prioriza que, si el tiempo se agota, lo traducido sea siempre lo más visible y
evaluado, y no un documento interno.

## Disparador (gate)

La traducción no arranca en una fecha fija, sino cuando se cumple una condición: los mentores
validan la documentación en español y hay confianza razonable de que no cambiará. Traducir
antes de esa validación implica re-traducir cada corrección del fuente.

Este gate gobierna la ejecución de la traducción (issue #96) y de todo documento en inglés
del proyecto: ningún `.en.md` se produce antes de que su fuente ES pase el gate. La condición
se estima alcanzable en Fase 4, pero la fecha es consecuencia del gate, no su definición.

## Método de mantenimiento

El español es el idioma fuente canónico y el inglés es una traducción derivada: el `.en.md`
nunca se edita de forma independiente. Cuando el fuente ES cambia después de haberse
traducido, se re-deriva el `.en.md` a partir del ES; ante cualquier discrepancia, el ES
manda.

La convención de nombres es un archivo hermano con sufijo `.en.md` junto al fuente, de modo
que la relación fuente↔traducción sea visible en el árbol del repositorio sin carpetas ni
herramientas adicionales:

- `README.md` → `README.en.md`
- `documentation/metricas-proyecto.md` → `documentation/metricas-proyecto.en.md`
- `documentation/hallazgos-ai-vs-humano.md` → `documentation/hallazgos-ai-vs-humano.en.md`

El trade-off completo de esta elección (fuente canónica + derivación vs. mantenimiento
paralelo independiente vs. tooling i18n) está registrado en
[ADR-18](decisiones/ARD-18.md).

## Estado del issue

El issue #88 documenta este plan pero permanece abierto, en espera de que se cumpla el gate y
se ejecute la traducción. La ejecución vive en el issue #96, que depende de este gate: no se
traduce lo que aún no está escrito ni validado.
