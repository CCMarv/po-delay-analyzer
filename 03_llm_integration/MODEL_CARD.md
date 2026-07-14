# Model Card — Sistema de explicación de causa raíz (Fase 3)

Ficha del sistema de Fase 3 siguiendo *Model Cards for Model Reporting* (Mitchell et al., 2019). No se entrena un modelo: se usa un LLM preentrenado con un prompt y unos datos de entrada, y ese uso tiene límites declarables. Fase 3 está en curso; esta ficha describe lo estable y marca lo pendiente. El diseño del prompt está en [README §Diseño del prompt](README.md#diseño-del-prompt).

## Detalles del modelo

El sistema es una capa de explicación por PO tardío sobre la salida determinista de las Fases 1-2 (etapas, excesos, flags, severidad auditada). Recibe hechos ya calculados y produce una explicación, una acción y una severidad.

- **Modelo que produjo el entregable:** `gpt-4o-mini` (OpenAI), el backend oficial. Parámetros de inferencia: temperatura 0.9, seed 42 (best-effort de la API de OpenAI), max_tokens 512 en la llamada de diagnóstico y 1536 en la llamada de acción. Prompt: few-shot C3 (ADR-12/#99).
- **Modelos por defecto de los backends alternativos:** `claude-sonnet-4-6` (Anthropic), `deepseek-chat` (DeepSeek), `qwen2.5:7b` (local vía Ollama). Los cuatro comparten la misma interfaz de prompt y parseo; el `po_output.csv` del entregable se generó con OpenAI, no con los demás.
- **Configuración:** versionada en `llm_config.json` (inferencia reproducible) y `.env` (operativo). El prompt lo arma `build_prompt()`, fuente única.
- **Fecha y propietario:** Fase 3 en curso (2026); equipo PO Delay Analyzer. El LLM es el motor del producto, no un asistente de desarrollo.

## Uso previsto

Generar, por PO tardío, una explicación de causa raíz, una acción recomendada al responsable y una severidad, para analistas de cadena de suministro. La app de Fase 4 lee el resultado desde `po_output.csv` (contrato F3→F4). El modelo interpreta métricas ya calculadas; su valor es traducir la señal medida a lenguaje accionable.

## Fuera de alcance

- No clasifica la etapa del retraso: la decide la lógica determinista de F2 (`stage_primary`). El modelo nombra esa etapa, no la re-decide.
- No recalcula fechas, horas ni métricas: el prompt lo prohíbe (ADR-14) y exige citar las cifras dadas.
- No ejecuta ni decide de forma autónoma: la salida es un insumo para revisión humana.
- No juzga entidades reales: el dataset es sintético; los nombres de proveedores y transportistas no corresponden a organizaciones reales.

## Datos de entrada

- Por PO: timeline (fechas clave), exceso por etapa, clasificación de F2, agravantes (hot PO, short ship, reprogramación) y `REASON_DSC`. Detalle en el README.
- Alcance de filas: solo POs tardíos (`delay_days_calc > 0`), 247 en el dataset actual.
- Ejemplos few-shot (C3): tres mismatches auditados de F2 (uno por etapa atribuible), disjuntos del benchmark de evaluación.

## Métricas de evaluación

Métrica *LLM Explanation Quality* (benchmark de 20 POs, muestra estratificada, semilla 42), tres checks binarios por PO: etapa correcta, cuantifica el delay, acción viable.

| Configuración | Veredicto | Fuente |
|---|---|---|
| Zero-shot (C0) | 13/20 (3.25/5) | `eval_quality_20pos.md` |
| Few-shot C3 a temp 0.3 | 19/20 (4.75/5) | `eval_quality_20pos.md` (#99) |
| Few-shot C3 a temp 0.9 (producción) | 20/20 (5/5), validación humana | `fixtures/eval_quality_20pos_C3_t09.md` |

La regla determinista de F2 audita la severidad del LLM contra la meta del mentor (Severity Ranking >95%). La evaluación a nivel dataset que reemplaza al fixture de 20 POs sigue en desarrollo (ARD-16).

## Fuente de la severidad

La severidad oficial del entregable la **emite el LLM** (`llm_severidad` → `severity` en `po_output.csv`), conforme a ADR-10 (opción híbrida): el kickoff la define como output del modelo. La regla determinista de F2 (`flag_hot_late & delay_days_calc > 3`) se conserva como columna de auditoría fuera del entregable y alimenta la métrica Severity Ranking. El prompt entrega las reglas de severidad, pero la decisión es del modelo; la discrepancia LLM-vs-regla es un hallazgo reportable, no un error.

## Límites y riesgos

- **Variancia entre corridas:** la severidad y la redacción no son totalmente reproducibles pese al seed best-effort; la severidad del entregable no es determinista por diseño (ADR-10).
- **Homogeneización de acciones:** a temperatura fija las acciones tienden a converger a una misma forma dentro de cada etapa. La causa medida es falta de contexto por PO, no la temperatura ni el few-shot; queda como trabajo abierto (#151/#122).
- **Interacción C3 × tier-2 sin gate conjunto:** el plan de acción (ARD-16, `--action-call`) se validó con la llamada de diagnóstico en zero-shot. El entregable combina C3 en la llamada 1 con tier-2 sin una medición conjunta de ambas (ARD-16 §9). Es un límite conocido documentado, no un bloqueo.
- **Perímetro anti-alucinación:** los hechos de la PO provienen solo de los datos, con cifras citadas; las generalizaciones de dominio se permiten marcadas en la redacción (ADR-14/ARD-16). El marcado se audita por muestra humana.
- **Dependencia de proveedor:** el entregable usa OpenAI; cambiar de backend cambia la salida y obliga a re-validar.

## Consideraciones éticas

- El sistema es asistivo: las acciones se revisan por una persona antes de usarse; no es decisor.
- El `REASON_DSC` humano es incorrecto en cerca del 20% de los casos. Las discrepancias entre la anotación y la señal temporal medida son hallazgos del proyecto (la medición supera a la anotación), no errores a corregir en silencio.
- Sin datos personales: el dataset es sintético.

## Estado

Fase 3 en curso. Estable: el prompt operativo (`build_prompt`), el few-shot C3, el parseo (`_parse_llm_json`) y los cuatro backends. En desarrollo: la evaluación a nivel dataset y el juez local de calidad (ARD-16). El alcance de este model card con la fase abierta se delibera en la discussion enlazada al issue #87.

## Referencias

Mitchell et al. (2019), *Model Cards for Model Reporting*. Decisiones del proyecto: ADR-10 (severidad híbrida), ADR-12 (diseño del prompt / few-shot), ADR-13 (temperatura), ARD-16 (capa analítica y llamada de acción).
