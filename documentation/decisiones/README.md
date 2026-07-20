# Registro de Decisiones de Arquitectura (ADR Log)

Este espacio contiene el registro histórico, razonamiento y evolución de las decisiones de diseño de ingeniería de datos tomadas a lo largo del proyecto, validadas en conjunto con el mentor Joseph.

## Reparto Vivo Resultante (247 Pedidos Tardíos)
Tras la aplicación rigurosa de los criterios de los ADRs vigentes (especialmente el ajuste asimétrico de umbrales y la nueva taxonomía neutral), la distribución final de atribución de retrasos en producción es:
*   **Vendor (Proveedor):** 131 POs (53.0%)
*   **Carrier (Transportista):** 40 POs (16.2%)
*   **DC (Centro de Distribución):** 37 POs (15.0%)
*   **Indeterminado:** 39 POs (15.8%) → *Dividido en 15 `sin_datos` + 24 `sin_causa_dominante`*

## Índice de Decisiones (Log Cronológico y de Evolución)

| Código | Decisión de Arquitectura | Estado | Enlaces de Contexto y Código |
| :--- | :--- | :--- | :--- |
| [ADR-01](ARD-01.md) | Fuente de verdad de las flags: calc vs. precalc | 🟢 Vigente | Issue #15, PR #44 |
| [ADR-02](ARD-02.md) | Jerarquía con múltiples flags activas | 🟢 Vigente | Issue #39, Discussion #52 |
| [ADR-03a](ARD-03a.md) | Etapa VENDOR: Medición inicial por residuo operativo | 📘 Superado | PR #59 |
| [ADR-03b](ARD-03b.md) | Etapa VENDOR: Medición por señal directa STA push | 🟢 Vigente | Issue #40, Discussion #57, PR #62, PR #64, PR #66 |
| [ADR-04a](ARD-04a.md) | Umbral de carrier provisional (4h) | 📘 Superado | Configuración inicial de código duro |
| [ADR-04b](ARD-04b.md) | Umbral de carrier definitivo (8h) | 🟢 Vigente | Issue #41, Discussion #53, `rules_config.json` |
| [ADR-05](ARD-05.md) | Reschedule y short-ship: contexto, no etapa | 🟢 Vigente | Issue #42, Discussion #54, Variable `_short_ship` |
| [ADR-06a](ARD-06a.md) | Umbral propio de vendor: Modelo inicial sin umbral | 📘 Superado | Implementación inicial de señal directa |
| [ADR-06b](ARD-06b.md) | Umbral propio de vendor: Configuración definitiva de 24h | 🟢 Vigente | Consulta R2 (2026-06-18), Discussion #57, PRs #62, #66, #64 |
| [ADR-07](ARD-07.md) | Taxonomía de Indeterminado | 🟢 Vigente | Consulta R2 (2026-06-18), Discussion #57, PR #62 |
| [ADR-08](ARD-08.md) | `stage_modifiers`: concebido y eliminado | 📘 Superado | PR #74 |
| [ADR-09](ARD-09.md) | User personas como criterio de diseño de la Fase 4 | 🟢 Vigente | Sync mentores 2026-06-26, Issues #102/#103, `../user_personas.md` |
| [ADR-10](ARD-10.md) | Severidad híbrida: el LLM la emite, la regla de Fase 2 la audita | 🟢 Vigente | Issue #92, #93, kickoff §03/§08, `_severidad` |
| [ADR-11](ARD-11.md) | Manejo de secretos y seguridad de API keys (multi-proveedor LLM) | 🟢 Vigente | Best Practices OpenAI, `llm_integration.py`, `.env.example`, `.gitignore` |
| [ADR-12](ARD-12.md) | Diseño del prompt de Fase 3: few-shot que enseña el razonamiento, con fuente única (ganador de producción: C3) | 🟢 Vigente | Issue #99, #94 (benchmark), #91/#67, ADR-10, `llm_integration.py` (`build_prompt`) |
| [ADR-13](ARD-13.md) | Temperatura de inferencia del LLM: evaluación 0.3–0.9 y decisión de ancla | 🟢 Vigente | Issue #137, ADR-14 (#143), #94 (benchmark), ADR-12, `eval_diversity.py`, `llm_config.json` |
| [ADR-14](ARD-14.md) | Endurecimiento del prompt de Fase 3 contra el overfitting al few-shot | 🟢 Vigente | Issue #143, #137/#144, #94 (benchmark), ADR-12, ADR-07, `llm_integration.py` (`build_prompt`) |
| [ADR-15](ARD-15.md) | Contexto de dominio condicional por (actor × señal) para diversificar el prompt | 📘 Superado | Superado por [ADR-16](ARD-16.md); Issue #151, #143/#154, #94 (benchmark), ADR-12/13/14, ADR-07, `llm_integration.py` (`select_domain_context`), `domain_kb.json` |
| [ADR-16](ARD-16.md) | El LLM como capa analítica sobre la base determinista validada | 🔵 Borrador (carril 2 agéntico y juez local abiertos) | Feedback mentores (post-validación de main), ADR-14/12/10/07, [ADR-15](ARD-15.md) (📘 superado), `llm_integration.py`; ver [ADR-19](ARD-19.md) (entrega parcial del carril 3) |
| [ADR-17](ARD-17.md) | Lenguaje visual y codificación de color de la taxonomía | 🟢 Vigente | Issue #162, #159 (sistema de diseño), #163/#164; ADR-09/10, [ADR-07](ARD-07.md); `config.py`, `styles.css` |
| [ADR-18](ARD-18.md) | Idioma fuente canónico y convención de nombres para documentación bilingüe (ES→EN) | 🟢 Vigente | Issue #88, #96 (descartado), `../plan-traduccion.md` |
| [ADR-19](ARD-19.md) | Integración LLM para análisis holístico de root cause y enriquecimiento con scorecard estadístico | 🟢 Vigente | Feedback mentores, ADR-16 (carril 3, complementario); `llm_integration_network_intelligence_view.py`, `scorecard_core.py` |
| [ADR-20](ARD-20.md) | Bot de Telegram como canal adicional de consumo | 🔵 Borrador | PR #193 (bot), PR #194 (SAD/SRS), Issue #196; distinción con Issue #160 (chatbot diferido, carril 3 de ADR-16); ADR-09; `04_app/telegram_bot/` |
| [ADR-21](ARD-21.md) | Contrato de datos tier-1/tier-2 de `po_output.csv` (incl. `agente1_raw.txt`) | 🔵 Borrador | Issue #158 (tier 1), Issue #161 (tier 2), PR #174; ADR-09/10, ADR-16 (carril 1); `04_app/config.py`, `llm_integration_network_intelligence_view.py` |
| [ADR-22](ARD-22.md) | Spec de retrabajo de la interfaz F4: información clave por persona y checklist ejecutable | 🔵 Borrador | Issue #130; ADR-09, ARD-17, ARD-21; issue #197 |
| [ADR-23](ARD-23.md) | Mockups como base de diseño del retrabajo de interfaz F4 y su reconciliación con ARD-17/ARD-22 | 🔵 Borrador | Mockups locales "Mockups analítica POs tardíos"; ARD-22, ARD-17, ARD-20; `04_app/` |
| [ADR-24](ARD-24.md) | Regla Late Shipment del README: descartada por columna inexistente | 🟢 Vigente | Issue #17, ADR-03b, README del repo original del mentor |

## Notas de Proceso e Integración
*   **Estándar de Documentación:** Todo el registro técnico del proyecto se rige bajo la plantilla **MADR (Markdown Architecture Decision Records)**, elegida formalmente por el equipo tras el debate documentado en la discusión [#79](#).
*   **Inmutabilidad Histórica:** Conforme al estándar adoptado, las decisiones superadas (como la lógica inicial de `ADR-03a`, `ADR-04a` o `ADR-06a`) no se editan ni se borran en silencio en el repositorio. Se conserva su registro histórico (`📘 Superado`) y se encadenan mediante enlaces relativos hacia los nuevos registros que las reemplazan (`🟢 Vigente`).

---
*Este log alimenta directamente los entregables de cierre D-4 (README raíz del proyecto) y D-5 (Validación analítica del negocio).*
