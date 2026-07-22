<!--
BORRADOR PARA CREAR ISSUES DESDE TERMINAL (no es una plantilla de GitHub).
Espejo de .github/ISSUE_TEMPLATE/2-decision.yml para usar con `gh issue create --body-file`.
Uso:
  gh issue create --title "[area] Decidir: ..." --label decisión-equipo --body-file /tmp/issue.md
  (usa --label consulta-mentor si necesita al mentor)
-->

## ¿Quién decide?
<!-- Elige UNA, borra la otra. Define la etiqueta. -->
Entre los 3 (asíncrono, cualquier día) — label decisión-equipo · Necesita al mentor (reunión del lunes) — label consulta-mentor

## Área
<!-- Elige UNA, borra el resto. Va también como --label. -->
pipeline · eda · analisis · infra · docs · llm · app

## Rama sugerida
<!-- Opcional: una Decisión casi nunca abre rama (es una elección, no trabajo). Si la implementación se hará en este mismo issue, propón: `tipo/<nombre>-<tarea-corta>` (tipo = feat · fix · docs · chore; la fase NO va en el nombre). Si no, deja "— sin rama". -->
`tipo/<nombre>-<tarea-corta>`

## La decisión / pregunta
<!-- ¿Qué hay que decidir, exactamente? Una pregunta clara que se pueda responder. -->


## Opciones y trade-offs
<!-- Las alternativas reales, con pros y contras. Estructurar la decisión es la mitad de resolverla — y es lo que el mentor evalúa. -->
**Opción A —**
- A favor:
- En contra:

**Opción B —**
- A favor:
- En contra:

## Recomendación / inclinación actual
<!-- ¿Hacia dónde te inclinas y por qué? Opcional. Aquí también se anota la decisión FINAL una vez tomada. -->


## ¿Qué bloquea esta decisión?
<!-- Issues que no pueden avanzar hasta resolver esto. Enlázalos con #N. -->

