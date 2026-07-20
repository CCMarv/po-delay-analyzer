# Plan de traducción ES→EN de los entregables

Este documento fija el plan de traducción de la documentación del proyecto al inglés: el
alcance, el orden, el disparador y el método de mantenimiento. El alcance descrito abajo ya
se ejecutó; este documento queda como el registro vivo del método (el `.en.md` se re-deriva
cuando su fuente ES cambia).

La rúbrica de evaluación (audiencia mixta) y el kickoff del mentor piden entregables
bilingües ES + EN; el propio repositorio del mentor publica el kickoff en ambos idiomas como
artefactos paralelos. Originalmente la decisión del equipo fue diferir la traducción hasta que
el fuente ES estuviera validado y estable, para no duplicar trabajo re-traduciendo cada
corrección. La traducción se ejecutó como parte del cierre del proyecto, una vez que el ES
alcanzó ese estado estable (ver "Disparador" abajo).

## Alcance

El alcance ejecutado cubre la documentación versionada de autoría humana del repositorio:

- Portada (`README.md`, `CONTRIBUTING.md`).
- READMEs de fase (F1–F4) y model card de Fase 3.
- Reportes legibles de evaluación de Fase 3 (`eval_differentiation.md`, `eval_quality_20pos.md`,
  `eval_severity_ranking.md`, `mismatches_ai_vs_humano.md`).
- Documentación general (`SAD.md`, `SRS.md`, `data_dictionary.md`, `explicacion-proyecto.md`,
  `hallazgos-ai-vs-humano.md`, `metricas-proyecto.md`, `plan-traduccion.md`, `user_personas.md`,
  `validacion-y-qa.md`, `convenciones-issues.md`).
- Registro de decisiones (`decisiones/README.md` + `ARD-01.md` … `ARD-23.md`, 27 archivos).
- Presentación (ES + EN, producida aparte del flujo de este documento).

Queda fuera de alcance: los fixtures crudos de corridas de benchmark
(`03_llm_integration/fixtures/*.md`, salvo su `README.md`), las plantillas internas de
proceso (`documentation/plantillas-cli/*.md`, `.github/pull_request_template.md`), y las
salidas del LLM por PO (explicación y acción recomendada de `po_output.csv`) — ver ADR-18 y
el cierre del issue #96 para el porqué de este último descarte.

## Orden

La traducción avanzó de afuera hacia adentro, empezando por lo que el mentor evalúa primero:
portada → documentación general → decisiones (ADRs) → READMEs de fase y model card →
reportes de evaluación.

## Disparador (gate)

El gate original de este plan era la validación de los mentores sobre la documentación en
español. En la práctica, la traducción se ejecutó como parte del cierre del proyecto (2026-07),
una vez que el ES alcanzó un estado estable tras la síntesis documental de cierre (G0–G8 de la
orquestación de cierre), sin esperar una validación formal explícita de los mentores. El
principio del gate se mantiene para cualquier documento nuevo o remanente: no se deriva un
`.en.md` de un fuente ES que aún esté en discusión activa.

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

El issue #88 (que documentó este plan) está cerrado: su alcance —documentar el plan, no
traducir— se cumplió. El issue #96 (explicaciones bilingües del LLM) se cerró descartado: esa
salida permanece en español (ver ADR-18). Las traducciones del alcance descrito arriba ya
existen como archivos `.en.md` hermanos en el repositorio.
