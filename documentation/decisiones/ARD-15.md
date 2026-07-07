
# Contexto de dominio condicional por (actor × señal) para diversificar el prompt de Fase 3

* **Estatus:** 📘 **SUPERADO** por [ADR-16](ARD-16.md) (2026-07-06)
* **Contexto Técnico:** Fase 3 / Integración LLM — enriquecimiento del prompt para que `accion_recomendada` varíe entre POs del mismo responsable
* **Referencias:** Issue #151 (madurado desde #143/#154); #94 (benchmark de calidad, 20 POs); ADR-12 (diseño del prompt few-shot); ADR-13 (temperatura — descartó el muestreo como causa/arreglo); ADR-14 (endurecimiento anti-overfitting del prompt, cuyo cierre de CÓMO RAZONAR esta decisión hace condicional); ADR-07 (taxonomía de Indeterminado, sub-etapas reusadas como señal de ruteo); ADR-04b/ADR-06b (umbrales de carrier/vendor, fuente única en `rules_config.json`); `03_llm_integration/llm_integration.py` (`build_prompt`, `select_domain_context`, `_cond_matches`, `_excess_band`); `03_llm_integration/domain_kb.json`; `03_llm_integration/eval_diversity.py`

## Contexto y Problema

Las `accion_recomendada` que el LLM genera por PO retrasada salen correctas y operables, pero homogéneas dentro de cada etapa: apenas se diferencian entre POs del mismo responsable (#143, madurado en #151/#154). ADR-13 descartó que el muestreo (temperatura) sea la causa: el barrido 0.3–0.9 no diversificó lo suficiente por sí solo. El prompt ya trae una guía por actor (`CÓMO RAZONAR`, ADR-14) y aun así el modelo converge a un fraseo canónico por etapa — señal de que falta contexto que distinga un caso de otro dentro de la misma etapa; el conocimiento de dominio general ya está cubierto por esa guía.

Un hallazgo clave orientó el diseño: más conocimiento compartido por actor no diversifica (es idéntico para todas las POs de ese actor; si acaso, homogeneiza más). La diversidad solo puede venir de lo que ya difiere entre POs — las señales por-PO que Fase 2 emite (banda de magnitud del exceso, `is_short_ship`, `is_rescheduled`, `HOT_PO_FLAG`, sub-etapa de DC/Indeterminado).

## Opciones Consideradas (mecanismo de enriquecimiento)

**Opción A — Más contexto de dominio compartido por actor.** Pros: simple. Contras: idéntico para todas las POs del actor → no diversifica; por el diagnóstico anterior, probablemente homogeneiza más.

**Opción B — RAG / recuperación semántica sobre una base de conocimiento.** Pros: escala a una base grande y no estructurada. Contras: la clave de ruteo (actor + señal por-PO) ya la computa Fase 2 de forma determinista, no hay problema de recuperación semántica que resolver; añade una dependencia nueva (embeddings/vector store) sin necesidad; entidades sintéticas (proveedores/transportistas ficticios) hacen que una búsqueda web por entidad devuelva ruido, no señal.

**Opción C — JSON versionado + lookup determinista indexado por (actor × señal por-PO) (elegida).** Pros: la clave de ruteo ya existe; "recuperar" es un lookup de diccionario, no búsqueda; auditable y versionado, consistente con `rules_config.json`/`fewshot_pool.json`. Contras: requiere curar contenido a mano; cobertura limitada a las señales ya modeladas.

## Opciones Consideradas (nivel de contenido dentro del KB)

**Opción A — Repertorio de acciones terminadas.** Pros: salida más predecible. Contras: reduce la llamada al LLM a paráfrasis y solo cambia las palabras exactas de la salida, sin enriquecer el razonamiento de causa ni de acción. Rechazada tras feedback: acota demasiado las respuestas posibles.

**Opción B — Palancas + tensiones de dominio que el LLM sintetiza (elegida).** Pros: el KB entrega insumo (palanca operativa, tensión a sopesar — p. ej. un reschedule puede ser consecuencia de un miss aguas abajo, no causa del proveedor), pero la síntesis de causa y acción ancladas a las cifras de la PO la hace el LLM; preserva el rol analítico de la llamada. Contras: más variancia en la redacción final.

## Opciones Consideradas (arquitectura de llamadas)

**Opción A — 2 llamadas (diferenciar + escribir).** Pros: separa selección de contexto y redacción. Contras: duplica costo/latencia por PO; sin evidencia de que 1 llamada sea insuficiente.

**Opción B — 1 llamada; el ruteo del KB ya varía el prompt (elegida).** Pros: mismo costo que la producción actual. Contras: si `eval_diversity` mostrara que no basta, requeriría escalar (arquitectura de 2 llamadas pre-diseñada, no implementada).

## Decisión

1. **KB como repertorio acotado indexado por (actor × señal).** `domain_kb.json` (versionado) da, por actor (Vendor/Carrier/DC/Indeterminado), un `primer` corto y una lista de `levers`, cada una con un `cond` sobre señales de la PO. `select_domain_context` filtra las que la PO cumple vía `_cond_matches` (determinista, fail-closed ante claves desconocidas).
2. **Bandas de magnitud del exceso.** `_excess_band` deriva bajo/medio/alto de `r = exceso / umbral_Fase2`, cortes en {1, 3} calibrados contra la distribución real. Umbrales de Fase 2 desde `rules_config.json` (fuente única). Indeterminado no tiene banda (exceso retirado de su prompt en ADR-14).
3. **Contenido a nivel "palancas + tensiones", no acciones terminadas.** El bloque inyectado instruye explícitamente "no las transcribas".
4. **1 llamada por PO.** Con `kb=None` (default), el prompt es byte-idéntico al histórico (invariante cubierto por test). Con `kb`, se agrega el bloque `CONTEXTO DE DOMINIO` y el cierre de `CÓMO RAZONAR` sobre la acción se reemplaza por un puntero a las palancas en vez de las dos líneas ilustrativas fijas de ADR-14 (evita competir como plantilla; el camino `kb=None` no se toca).
5. **Ajuste de unidades en el lead-in.** Las palancas están en horas; validación mostró que esto podía empujar a omitir el retraso en días en `causa_raiz`. El lead-in (solo activo con `kb`) ahora recuerda citar también los días.
6. **Cableado opt-in.** `add_llm_explanations` y `eval_quality.py` (`--kb`) aceptan `kb` como parámetro/flag opcional, default apagado.

## Validación

Benchmark de 20 POs estratificado (semilla 42, el de #94/#99), a temperatura de producción (0.9):

| Métrica | sin kb | con kb |
| --- | --- | --- |
| Pre-evaluación automática (a & b) | 16/20 | 17/20 |
| Diversidad (conjunto completo) | 0.772 | 0.817 |
| Diversidad (subconjunto Vendor) | 0.631 | 0.739 |

(c) y el veredicto final por PO quedan a validación humana.

## Consecuencias

**Positivas:** diversidad medible al alza, más marcada en Vendor (el subconjunto del problema original); el comportamiento zero-shot/producción no cambia salvo opt-in explícito; contenido versionado y auditable; sin costo/latencia adicional sobre la producción actual.

**Negativas:** el KB requiere curación manual por (actor × señal); cobertura limitada a las señales ya modeladas hoy; la validación corre sobre 20 POs a una temperatura, no sustituye la regeneración del entregable completo (~247 POs, seguimiento con su propia declaración de API); la interacción `kb` × few-shot (C1–C3) no se probó en esta ronda.

## Relación con otras decisiones

Responde al síntoma documentado en **ADR-13** (el muestreo quedó descartado como arreglo). Vuelve condicional el cierre de `CÓMO RAZONAR` de **ADR-14**, cuyo contenido se mantiene. Reusa la taxonomía de **ADR-07** y los umbrales de **ADR-04b/ADR-06b** vía `rules_config.json`. Se apoya en la infraestructura de prompt de **ADR-12**.

**Superada por [ADR-16](ARD-16.md).** La premisa de esta decisión —diversificar la salida curando conocimiento de dominio por (actor × señal)— quedó revisada por el marco de ADR-16: el pedido de los mentores convirtió al LLM en capa analítica y la diversidad que este KB buscaba la produce el diagnóstico diferencial de la llamada de acción sin conocimiento curado (gate de la ola 2, `03_llm_integration/fixtures/eval_quality_20pos_C0_t09_accion_ola2.md`: la hipótesis-etiqueta desaparece con `kb` inactivo). El código de #151 permanece como capacidad opt-in de la llamada 1 (`kb=None` por default, invariante cubierto por test); no se revierte.
