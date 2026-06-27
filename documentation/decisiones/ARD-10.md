# Severidad híbrida: el LLM la emite, la regla de Fase 2 la audita

* **Estatus:** 🔵 **BORRADOR** (pendiente de cierre por el equipo)
* **Contexto Técnico:** Fase 3 / Integración LLM — fuente de la severidad en el output del entregable
* **Referencias:** Issue #92, #93, #97, #98; kickoff (`documentation/kickoff_po_root_cause.html`, secciones 03 y 08); README mentor §6 (Severity Ranking >95%); `02_clasif_reglas_negocio/classifier_core.py` (`_severidad`); ADR-01 (principio determinístico)

## Contexto y Problema
El output del entregable reporta una severidad HIGH/MEDIUM/LOW por PO tardío. Dos fuentes de verdad del proyecto la sitúan en lugares distintos, y el código de andamiaje de la Fase 3 las fusionó de forma incorrecta:

1. El **kickoff** (sección 03, plantilla de prompt del mentor) pone la severidad como **output del LLM**: *"Generate: (1) root cause explanation, (2) recommended action, (3) severity: HIGH/MEDIUM/LOW"*. Es uno de los tres productos que el modelo genera, junto a explicación y acción.
2. La **métrica Severity Ranking** (kickoff sección 08 / README §6) la define con una **regla determinística y una meta cuantitativa**: *"los hot PO con delay > 3 días deben tener severity=HIGH en >95% de los casos"*. Eso solo es evaluable si la relación es reproducible.

El andamiaje inicial dejó al LLM asignando la severidad con una regla escrita en el prompt cuyo umbral (*"retraso > 7 días"*) **no corresponde** ni al kickoff ni al README (ambos fijan **> 3 días**). En paralelo, la Fase 2 ya calcula una columna `severity` determinística con el umbral correcto. Quedaron dos severidades en conflicto y un umbral erróneo en el prompt.

## Opciones Consideradas

### Opción A: La severidad determinística de Fase 2 es la oficial; el LLM solo la explica
* **Pros:** Auditable y reproducible; cumple el >95% por construcción.
* **Contras:** **Desvía del kickoff**, que pide explícitamente la severidad como output del LLM. Vacía de contenido la métrica (se cumple por diseño, no se valida nada).

### Opción B: El LLM emite la severidad y se mide contra la regla
* **Pros:** Fiel al kickoff. La métrica >95% se vuelve una validación real (¿el LLM respeta hot+delay>3d⇒HIGH?).
* **Contras:** La severidad del entregable no es 100% reproducible; hay que medir y reportar el %.

### Opción C (híbrida): El LLM emite la severidad oficial; la regla de Fase 2 la audita
* **Pros:** Honra ambas fuentes. El LLM genera la severidad (kickoff); la regla determinística de Fase 2 queda como columna de control que alimenta la métrica Severity Ranking y el análisis de coincidencia LLM-vs-regla. Convierte la tensión entre las fuentes en un hallazgo medible.
* **Contras:** Mantiene dos columnas y obliga a definir cuál es la oficial y cómo se reporta la discrepancia.

## Decisión
Elegimos la **Opción C (híbrida)**.

1. La columna **oficial** de severidad del CSV-entregable (#97) es la que **emite el LLM** (`llm_severidad` → `severity` en `po_output.csv`), fiel al kickoff que la define como output del modelo.
2. La **regla determinística de Fase 2** (`severity`, `flag_hot_late & delay_days_calc > 3.0`) se conserva como **columna de auditoría**: alimenta la métrica Severity Ranking >95% (#98) y permite reportar dónde el LLM discrepa de la regla.
3. El **umbral del prompt se corrige** del erróneo *"> 7 días"* al del lineamiento oficial: **hot PO + delay > 3 días ⇒ HIGH** (#93). Esta corrección es inequívoca en ambas fuentes y aplica con independencia de la opción elegida.

## Consecuencias
* **Positivas:** El entregable cumple el kickoff (severidad como output del LLM) sin perder auditabilidad: la regla de Fase 2 sigue presente como control y da contenido real a la métrica >95% (mide si el LLM respeta la regla, no la da por sentada). La discrepancia LLM-vs-regla se vuelve un hallazgo reportable, alineado con el espíritu del proyecto ("dónde el AI coincide o no con la referencia").
* **Negativas:** El output arrastra dos columnas de severidad con roles distintos, lo que obliga a documentar con claridad cuál es la oficial y cuál la auditora para no confundir a quien consuma el dato aguas abajo (#97, #100). Si el LLM viola la regla en demasiados casos, el >95% lo expondrá y habrá que iterar el prompt (#93) o reportarlo como límite del modelo.
