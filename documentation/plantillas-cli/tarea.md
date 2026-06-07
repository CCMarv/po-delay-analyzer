<!--
BORRADOR PARA CREAR ISSUES DESDE TERMINAL (no es una plantilla de GitHub).
Espejo de .github/ISSUE_TEMPLATE/1-tarea.yml para usar con `gh issue create --body-file`.
Quien crea por WEB no usa esto: usa el formulario (dropdowns + validación).
Uso:
  1. Copia este archivo:  cp documentation/plantillas-cli/tarea.md /tmp/issue.md
  2. Rellénalo (borra estos comentarios y las opciones que no apliquen).
  3. Crea el issue:
     gh issue create --title "[docs] Verbo + objeto" --label docs --body-file /tmp/issue.md
  Nota: GitHub NO valida que llenaste los campos (eso lo hacía el form .yml).
  El gate pasa a tu self-review: no abras el issue con secciones vacías.
-->

## Área
<!-- Elige UNA, borra el resto. Es la misma que pones en --label. -->
pipeline · eda · analisis · infra · docs · llm · app

## Fase (milestone)
<!-- Ponla también en el campo Milestone del issue (no se puede por CLI: hazlo en la web tras crear, o con --milestone "Fase 1 — Pipeline + EDA"). -->
Fase 1 — Pipeline + EDA · Fase 2 — Clasificación por etapa (reglas) · Fase 3 — LLM (prompt, explicaciones, severidad) · Fase 4 — Demo + evaluación final

## Contexto
<!-- ¿Por qué existe esta tarea? El gap, hallazgo o mejora que la motiva. 1–3 líneas. Esto es lo que el mentor lee para entender el porqué. -->


## Tarea (pasos concretos)
<!-- Qué hay que hacer, en pasos marcables. Si pasan de ~5, parte el issue. -->
- [ ]
- [ ]

## Definición de hecho (DoD)
<!-- ¿Cuándo está REALMENTE terminado? Criterios verificables. La última línea es la DoD global del equipo: déjala siempre. -->
- [ ] Criterio verificable y específico
- [ ]
- [ ] Corre en entorno limpio (`venv` desde `requirements.txt`) · CI en verde · self-review hecho · sin secrets/datos/outputs commiteados

## Dependencias
<!-- Enlaza otros issues con #N. 'Depende de' = no puedo empezar hasta que ese cierre. 'Bloquea' = otros me esperan. -->


## Notas / hallazgos
<!-- Se llena MIENTRAS trabajas. Tu handoff asíncrono: qué decidiste, qué descubriste, qué necesita saber quien siga. -->


<!-- Ownership: cuando empieces, auto-asígnate y mueve el issue a *In Progress*. -->
