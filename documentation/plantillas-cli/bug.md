<!--
BORRADOR PARA CREAR ISSUES DESDE TERMINAL (no es una plantilla de GitHub).
Espejo de .github/ISSUE_TEMPLATE/3-bug.yml para usar con `gh issue create --body-file`.
Uso:
  gh issue create --title "[area] Arreglar: ..." --label pipeline --body-file /tmp/issue.md
-->

## Área
<!-- Elige UNA, borra el resto. Va también como --label. -->
pipeline · eda · analisis · infra · docs · llm · app

## Qué pasa (síntoma)
<!-- El problema en una o dos frases, sin teorizar todavía la causa. -->


## Cómo reproducir
<!-- Pasos exactos para llegar al problema. Cuanto más concreto, más rápido se arregla. -->
1.
2.
3.

## Esperado vs observado
**Esperado:**

**Observado:**

## Evidencia
<!-- Traceback, número(s) de PO afectados, celda del notebook, captura, salida de una celda. -->


## Definición de hecho (DoD)
<!-- ¿Cuándo está arreglado de verdad? Idealmente incluye un test que falle antes y pase después. -->
- [ ] El problema ya no se reproduce con los pasos de arriba
- [ ] (si aplica) test que cubre el caso
- [ ] Corre en entorno limpio (`venv` desde `requirements.txt`) · CI en verde · self-review hecho · sin secrets/datos/outputs commiteados
