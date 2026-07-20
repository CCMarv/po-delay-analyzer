# 03 — Integración con LLM

Genera explicaciones de causa raíz para Purchase Orders (POs) retrasados, usando un LLM para analizar las métricas calculadas en las fases anteriores y producir un diagnóstico estructurado.

## Qué hace

Toma el DataFrame ya limpio y clasificado (fases 1 y 2), filtra los POs con retraso (`delay_days_calc > 0`), y para cada uno construye un prompt con el contexto completo (fechas, métricas de yard/dock, clasificación automática, reason code del DC) que envía a un LLM. La respuesta se parsea a JSON y se agregan estas columnas al DataFrame (la primera llamada, siempre; con `--action-call` también las de tier-2 — ver [Salida](#salida) para el contrato completo de 33 columnas):

| Columna | Descripción |
|---|---|
| `llm_causa_raiz` | Explicación de 1-2 líneas generada por el modelo |
| `llm_accion_recomendada` | Acción concreta sugerida, con responsable |
| `llm_severidad` | `HIGH`, `MEDIUM` o `LOW` |
| `llm_coincide_con_reason` | `True`/`False` si la causa coincide con el reason code del DC |
| `llm_confianza` | Score de 0.0 a 1.0 |

## Backends soportados

| Backend | Motor | Requiere API key | Costo |
|---|---|---|---|
| `openai` | OpenAI API (`gpt-4o-mini`) | Sí | De pago — **backend oficial del entregable** |
| `local` | Qwen 2.5:7B vía Ollama | No | Gratis (corre en tu máquina) |
| `claude` | Claude (Anthropic API) | Sí | De pago |
| `deepseek` | DeepSeek API | Sí | De pago |

El `po_output.csv` del entregable se genera con `--backend openai`; los demás son alternativas (desarrollo local con `local`, o comparación con `claude`/`deepseek`).

## Requisitos previos

- Python 3.13 con el `.venv` del repo activado
- Dependencias instaladas: `pip install -r ../requirements.txt`
- Si usas `--backend local`: [Ollama](https://ollama.com) corriendo localmente con el modelo descargado:
  ```bash
  ollama pull qwen2.5:7b
  ```
- Si usas `--backend claude`, `--backend openai` o `--backend deepseek`: una API key válida del proveedor correspondiente

## Configuración de API keys

Las keys **nunca** se escriben en el código ni se pasan como argumento en producción. Se guardan en un archivo `.env` en la raíz del repo (mismo nivel que `pyproject.toml`), que está excluido de git vía `.gitignore`.

1. Copia la plantilla (desde la raíz del repo):
   ```bash
   cp .env.example .env
   ```
2. Edita `.env` con tus keys reales (solo las del backend que vayas a usar):
   ```
   ANTHROPIC_API_KEY=sk-ant-...
   OPENAI_API_KEY=sk-...
   DEEPSEEK_API_KEY=sk-...
   ```
3. Confirma que `.env` está en `.gitignore`:
   ```bash
   grep "^\.env$" .gitignore
   ```

El script carga estas variables automáticamente con `load_dotenv()`, así que no necesitas pasar `--api-key` en la terminal una vez configurado el `.env`.

Cada persona usa su **propia** key (no se comparten; el nombre de la variable es estándar por
proveedor). Ante sospecha de fuga, rotar la key de inmediato en el panel del proveedor y avisar
al equipo. El detalle de la política de secretos está en
[ADR-11](../documentation/decisiones/ARD-11.md).

## Uso

Activa el entorno virtual antes de correr cualquier comando (desde la raíz del repo):

```bash
source .venv/bin/activate    # Windows: .venv\Scripts\activate
cd 03_llm_integration
```

### Modo test (10 POs, para validar que todo funciona)

```bash
# Local (Qwen/Ollama)
python llm_integration.py --mode test --backend local

# Claude
python llm_integration.py --mode test --backend claude

# DeepSeek
python llm_integration.py --mode test --backend deepseek
```

### Modo custom (N POs específicos)

```bash
python llm_integration.py --mode custom --limit 50 --backend deepseek
```

### Modo producción (todos los POs retrasados)

```bash
python llm_integration.py --mode full --backend openai
```

### Parámetros adicionales

| Flag | Default | Descripción |
|---|---|---|
| `--mode` | `test` | `test` (10 POs), `full` (todos), `custom` (usa `--limit`) |
| `--limit` | `50` | Cantidad de POs en modo `custom` |
| `--backend` | `local` | `local`, `claude`, `openai` o `deepseek` |
| `--api-key` | `None` | Override manual de la key (no recomendado; usa `.env`) |
| `--claude-model` | `claude-sonnet-4-6` | Modelo de Claude a usar |
| `--deepseek-model` | `deepseek-chat` | Modelo de DeepSeek (`deepseek-chat` o `deepseek-reasoner`) |
| `--ollama-model` | `qwen2.5:7b` | Modelo local en Ollama |
| `--ollama-url` | `http://localhost:11434/api/generate` | URL de la API de Ollama |

## Salida

La corrida produce dos artefactos en `../data/processed/`:

**1. Artefacto interno** — el DataFrame completo con todas las columnas (las de F1/F2 más las `llm_*`), con nombre según modo y backend:

- `df_with_llm_test_{backend}.csv`
- `df_with_llm_full_{backend}.csv`
- `df_with_llm_{limit}_{backend}.csv`

Es el insumo de trabajo y auditoría (incluye, p. ej., la `severity` determinística de F2 junto a la `llm_severidad`). También se generan guardados parciales cada 50 POs (configurable vía `DEFAULT_SAVE_EVERY`) para no perder progreso en corridas largas.

**2. CSV-entregable** — `po_output.csv`, el artefacto del **contrato F3→F4** (#100): el único input de Fase 4. Tiene **33 columnas** en cuatro bloques, en este orden: el contrato base (16, sin numeración tier) y las ampliaciones tier-1/tier-2 que fija [ARD-21](../documentation/decisiones/ARD-21.md). La copia operativa verificada exacta 33/33 vive en [`04_app/README.md`](../04_app/README.md#1-entrada-el-contrato-f3f4-100); esta sección explica el origen, ARD-21 es el registro de diseño.

**Bloque 1 — Contrato del mentor (las 5 columnas que evalúa, primero y en orden):**

| Columna | Origen | Nota |
|---|---|---|
| `PO_NBR` | `PO_NBR` | identidad |
| `stage` | `stage_primary` (F2) | Vendor / Carrier / DC / Indeterminado |
| `severity` | `llm_severidad` (F3) | la severidad **oficial es la del LLM** (ver [ADR-10](../documentation/decisiones/ARD-10.md)); la determinística de F2 queda como auditoría en el artefacto interno, no aquí |
| `explanation` | `llm_causa_raiz` (F3) | explicación en lenguaje natural |
| `action` | `llm_accion_recomendada` (F3) | acción concreta con responsable |

**Bloque 2 — Soporte para la app de Fase 4 (para que LEA, no recompute):**

| Grupo | Columnas | Para qué |
|---|---|---|
| Timeline | `PO_DT, STA_DT, APPROVED_DT, TRAILER_ARRIVE_DT, CHECKIN_DT, CHECKOUT_DT, RECPT_DT` | dibujar el recorrido del PO (selector, #102) |
| Agravantes | `HOT_PO_FLAG, is_short_ship` | marcar hot PO / short ship en la vista |
| Concordancia | `REASON_DSC, llm_coincide_con_reason` | mostrar si el diagnóstico coincide con la anotación humana |

Bloque 1 (5) + Bloque 2 (11) = las **16 columnas del contrato base** (ARD-21). Las siguientes
17 amplían ese contrato en dos rondas:

**Tier-1 (8 columnas, #158)** — enriquecimiento con datos ya computados aguas arriba, sin llamada LLM adicional:

| Columnas | Para qué |
|---|---|
| `llm_confianza, VENDOR_NAME, CARRIER_PARTY_NAME, DC_LOC_NAME, delay_days_calc, excess_vendor_hrs, excess_carrier_hrs, excess_dc_hrs` | confianza del diagnóstico, entidades responsables y exceso de horas por etapa (contexto de la vista individual, Diego) |

**Tier-2 (9 columnas, #161, PR #174)** — salida híbrida de la llamada de acción ([ADR-16](../documentation/decisiones/ARD-16.md) carril 1, opt-in vía `--action-call`; sin el flag estas 9 columnas salen **vacías, no ausentes** — el contrato de 33 es estable con o sin él):

| Columnas | Para qué |
|---|---|
| `llm_razonamiento, llm_hipotesis, llm_hipotesis_evidencia, llm_accion_inmediata, llm_accion_correctiva, llm_accion_preventiva, llm_hipotesis_alt, llm_paso_discriminante, llm_confianza_hipotesis` | hipótesis principal con evidencia y plan escalonado, hipótesis alternativa con su paso discriminante, y una segunda confianza específica de la hipótesis |

**Alcance de filas:** solo los **POs tardíos** (`delay_days_calc > 0`) — los que el LLM explica y los que la app ofrece en el selector. Los on-time no entran.

**Regla del contrato F3→F4:** Fase 4 **lee** `po_output.csv` y nada más; **no recomputa** las reglas de F1/F2 ni vuelve a llamar al LLM. Por eso el artefacto trae ya el timeline y los agravantes: todo lo que la app necesita está en el CSV. (Una demo opcional de "regenerar este PO en vivo" sería la única excepción y va por separado del flujo principal.) El contrato está blindado por `tests/test_handoff_f3.py`.

El `po_output.csv` del entregable se genera con el backend oficial, **OpenAI**. Añade
`--action-call` para poblar también el tier-2 (segunda llamada, gasta API adicional por PO):

```bash
python llm_integration.py --mode full --backend openai --action-call
```

## Síntesis ejecutiva de red (`llm_integration_network_intelligence_view.py`)

Script aparte, gobernado por [ADR-19](../documentation/decisiones/ARD-19.md): no genera
`po_output.csv` ni pertenece a su contrato. Lee los scorecards por entidad ya calculados por
`scorecard_core.py` (`data/processed/scorecards/reporte_{vendors,carriers,dcs}.json`) y corre
tres agentes especializados en secuencia (SDK `openai-agents`, distinto del backend de
`llm_integration.py`), uno por actor (Vendor/Carrier/DC), para producir una síntesis narrativa
de reliability por entidad.

```bash
# --actor: vendor | carrier | dc | all
python llm_integration_network_intelligence_view.py --actor all
```

Solo `--actor all` consolida los tres análisis y escribe
`data/processed/agente1_raw.txt`, el artefacto que consume en producción la página
`Network Intelligence` (`04_app/pages/2_📊_Network_Intelligence.py`, persona Ravi). Es una
dependencia real de Fase 3→Fase 4 —no un componente aislado ni un POC— formalizada en
[ARD-21](../documentation/decisiones/ARD-21.md). Requiere que el paso de scorecards haya
corrido antes (lee sus JSON de entrada) y gasta API en cada corrida.

## Diseño del prompt

El prompt lo arma `build_prompt()` en `llm_integration.py`: es la única fuente del prompt (ADR-12), interpola los datos de cada PO tardío y antepone los ejemplos few-shot de producción. La configuración de producción es **few-shot C3** (tres ejemplos), validada contra el benchmark de calidad; el detalle de la selección está en [Estado del few-shot](#estado-del-few-shot). El model card del sistema, con modelo, uso previsto y límites, está en [MODEL_CARD.md](MODEL_CARD.md).

### Qué entra en el prompt y por qué

El prompt inyecta toda la aritmética ya resuelta por las fases anteriores e instruye al modelo a interpretar sin recalcular. Los bloques, en orden:

| Bloque | Campos | Por qué entra |
|---|---|---|
| DATOS DE LA PO | `PO_NBR`, `VENDOR_NAME`, `DC_LOC_NAME`, `CARRIER_PARTY_NAME` | identifican a los actores que la acción puede nombrar |
| TIMELINE | `STA_DT`, `RECPT_DT`, `APPROVED_DT`, `TRAILER_ARRIVE_DT`, `CHECKIN_DT`, `CHECKOUT_DT` | las fechas crudas; el modelo las lee para contrastar, no para recalcular (#91/ADR-14) |
| MÉTRICAS CALCULADAS | `delay_days_calc`, `yard_wait_calc_hrs`, `dock_calc_hrs`, y el exceso por etapa (`excess_vendor_hrs`, `excess_carrier_hrs`, `excess_dc_hrs`) | la aritmética ya resuelta que el modelo cita textualmente; los excesos se omiten en Indeterminado, donde la atribución se retiró a propósito (ADR-14) |
| CLASIFICACIÓN AUTOMÁTICA | `stage_primary`, `stage_multi` | el veredicto determinista de F2 es la fuente de verdad de la etapa; el modelo no la re-decide |
| CONTEXTO ADICIONAL | `HOT_PO_FLAG`, `_short_ship`, `is_rescheduled`, `indeterminado_substage`, `REASON_DSC` | agravantes y meta-señales; la reprogramación entra como contexto neutro, no como agravante (#67); la subcategoría solo cuando la etapa es Indeterminado (#135) |

Después del contexto, dos bloques de instrucciones cierran el prompt. INSTRUCCIONES prohíbe recalcular fechas u horas e inventar cifras, y exige citar textualmente las dadas. CÓMO RAZONAR (#143) fija que la etapa que el modelo nombre es exactamente la de la clasificación, que el `REASON_DSC` sirve para contrastar y nunca para sustituir la etapa, y describe la combinatoria de las cuatro etapas frente a las tres relaciones posibles con el motivo (coincide / discrepa / vacío). Ese bloque evita que el modelo copie la forma de los ejemplos como plantilla.

### Qué se le pide (contrato JSON)

Se pide un JSON con cinco claves, sin texto adicional:

| Clave | Contenido |
|---|---|
| `causa_raiz` | 2-3 oraciones: etapa exacta, retraso citado de los datos, relación con el `REASON_DSC` y agravantes |
| `accion_recomendada` | acción concreta al responsable de la etapa medida, anclada en los datos del PO |
| `severidad` | `HIGH` / `MEDIUM` / `LOW`; la decide el LLM (ver [MODEL_CARD.md](MODEL_CARD.md) y ADR-10) |
| `coincide_con_reason_code` | `true`/`false` según la causa coincida con el `REASON_DSC` |
| `confianza` | 0.0 a 1.0 |

Las reglas de severidad que el prompt entrega (HIGH para hot PO con retraso alto o short ship; MEDIUM para retraso sin agravantes; LOW para borderline) interpolan los umbrales desde `rules_config.json` (#121), la misma fuente única que usa F2, en vez de valores fijos en el código.

### Cómo se parsea la respuesta

El parseo está centralizado en `_parse_llm_json()` para no duplicar lógica entre backends. Busca el primer bloque `{...}` de la respuesta, lo carga y normaliza las cinco claves (acepta variantes en inglés: `root_cause`, `severity`, etc.). Si el modelo no devuelve JSON usable y `fallback=True`, arma un dict de emergencia con el texto crudo recortado; ese fallback está pensado para el backend `local` (Qwen), que puede responder en texto libre. Los backends cloud (`openai`, `claude`, `deepseek`) esperan JSON válido y no usan el fallback.

### Estado del few-shot

Producción usa **few-shot C3**: tres ejemplos, uno por etapa atribuible (Vendor, Carrier, DC), seleccionados de forma determinista con `select_examples(3, stages=["Vendor","Carrier","DC"])` desde el pool auditado `fewshot_pool.json`. Los ejemplos provienen de mismatches reales de F2 (la clasificación computada discrepa del `REASON_DSC` humano), disjuntos del benchmark de 20 POs para no contaminar la métrica; cada ejemplo es espejo de la forma del prompt pero curado en contenido, y no incluye el timeline de fechas (mostrarlo reenseñaría a recalcular).

C3 ganó el benchmark de calidad (`eval_quality_20pos.md`) y se re-validó a la temperatura de producción: `fixtures/eval_quality_20pos_C3_t09.md` reporta 20/20 con validación humana a temperatura 0.9, sin regresión frente al ancla 0.3. El flag `--zero-shot` desactiva el few-shot y reproduce el baseline C0 para comparaciones. El pool conserva dos ejemplos sintéticos de Indeterminado (para trabajo futuro de selección dinámica); C3 no los selecciona, y la etapa Indeterminado se resuelve por el bloque CÓMO RAZONAR.

### Segunda llamada: plan de acción (tier-2)

Bajo el flag `--action-call` (ARD-16), cada PO recibe una segunda llamada con `build_action_prompt()`: un rol de planner con autoridad de decisión que produce un contrato híbrido (razonamiento → hipótesis principal con su plan → hipótesis alternativa con su paso discriminante → confianza) y pasa por un control de calidad por reglas. La primera llamada diagnostica; esta planifica el mecanismo bajo el nivel etapa. El detalle vive en ARD-16.

### Iteraciones del prompt

| Iteración | Issue / ADR | Qué cambió |
|---|---|---|
| Base zero-shot | #91 / #67 | aritmética pre-resuelta, interpretar sin recalcular, reprogramación como contexto neutro |
| Few-shot | #99 / ADR-12 | ejemplos que enseñan el razonamiento; C3 (tres ejemplos) gana el benchmark |
| Anti-overfitting | #143 / ADR-14 | bloque CÓMO RAZONAR: autoridad de la etapa sobre el `REASON_DSC`, combinatoria de las cuatro etapas |
| Umbral externalizado | #121 | umbrales de severidad interpolados desde `rules_config.json` (fuente única con F2) |
| Subcategoría Indeterminado | #135 | `indeterminado_substage` (sin_datos / sin_causa_dominante) al prompt |
| Contexto de dominio | #151 | bloque opt-in por (actor × señal), apagado por defecto |
| Temperatura validada | ADR-13 | C3 re-validado a 0.9 (`_C3_t09`, 20/20), sin regresión vs 0.3 |

## Manejo de errores

- **401/403 (API key inválida o sin permisos):** el script falla de inmediato sin reintentar y muestra un mensaje claro indicando qué variable de entorno revisar.
- **Otros errores HTTP (429, 500, etc.):** se reintenta hasta 3 veces con una pausa de 2 segundos entre intentos.
- **Errores de red (timeout, conexión):** mismo comportamiento de reintento.
- Si un PO falla tras los reintentos, se marca como `FALLÓ` en la barra de progreso y continúa con el siguiente (no detiene el batch completo).

## Troubleshooting

**`ModuleNotFoundError: No module named 'dotenv'`**
El `.venv` no está activado. Corre `source .venv/bin/activate` (Windows: `.venv\Scripts\activate`) desde la raíz del repo antes de ejecutar el script.

**`Error HTTP 401: ... api key ... is invalid`**
La key en `.env` no es válida o tiene espacios/caracteres extra al copiarla. Verifícala directamente con un `curl` de prueba al endpoint del proveedor, o regenera la key desde su dashboard.

**`CSV no encontrado en ...`**
El script espera el CSV crudo en `../data/raw/po_root_cause_synthetic.csv` relativo a la raíz del repo. Verifica que el archivo exista en esa ruta exacta.

## Notas de diseño

- **Lineamiento del prompt (#91).** `build_prompt()` sigue el template del mentor (kickoff §03 / README §5): toda la aritmética llega ya resuelta (timeline + MÉTRICAS CALCULADAS) y el modelo solo **interpreta**. El prompt prohíbe explícitamente recalcular fechas/horas o inventar cifras, y exige **citar textualmente** las cifras dadas (p. ej. "un retraso de 4.2 días") para que la explicación sea auditable contra los datos. La explicación pedida (`causa_raiz`) son **2-3 oraciones** con los elementos del mentor: etapa exacta del retraso (Vendor/Carrier/DC), delay cuantificado citado, coincidencia con `REASON_DSC` y agravantes (hot PO, short ship); la acción debe ser operable y nombrar al responsable, no genérica. El contrato JSON de salida (5 claves) no cambió. Decisiones de diseño: se exige citar la cifra (auditabilidad); el short ship se mantiene como booleano "Sí/No" (el `{short_ship_pct}%` del template del mentor queda como follow-up). El umbral de severidad sigue en `> 3 días` (ADR-10); externalizarlo a `rules_config.json` es trabajo de #121.
- **Reprogramación de cita como contexto (#67).** El prompt incluye `is_rescheduled` (de F2) como dato de **contexto neutro** ("¿Se reprogramó la cita de entrega? Sí/No"), no como etapa ni como agravante automático. Razón: el mentor (06-16) descartó la reprogramación como *señal de vendor* porque describe un evento, no la causa; meterla como agravante reintroduciría el sesgo pro-vendor que el cierre de F2 corrigió. El LLM la usa para juzgar mejor la coincidencia con `REASON_DSC` (varios reason codes humanos son "Rescheduled by vendor"), sin que la etapa se fuerce a Vendor por ello — la etapa la sigue marcando `stage_primary`.
- **Fuente única del prompt (#99 / ADR-12).** El prompt que se envía al modelo lo arma `build_prompt()` en `llm_integration.py`: es la **única** fuente del prompt, interpola los datos de cada PO y opcionalmente antepone ejemplos few-shot (parámetro `examples`). El antiguo borrador `prompt_template.txt` se **eliminó**: no se cargaba desde el código y había divergido (taxonomía de 6 etapas que no son los 4 estados de F2, instrucciones que invitaban a calcular contra el lineamiento de #91, y un umbral de severidad `> 7 días` contradictorio con ADR-10). Conservarlo arriesgaba que se reutilizara sin contexto y revirtiera decisiones vigentes. El diseño del prompt (few-shot que enseña el razonamiento, fuente única) queda registrado en ADR-12.
- **Few-shot validado (#99).** Contra el benchmark de 20 POs (`eval_quality_20pos.md`, semilla 42) se compararon zero-shot y tres combinaciones few-shot con ejemplos del pool auditado (`fewshot_pool.json`, estratificado: el mismatch más fuerte de cada etapa). Ganó **C3** (3 ejemplos): veredicto **19/20 (4.75/5)** frente a 13/20 del zero-shot, superando la meta del mentor (4/5), sin degradar (a)/(b). El few-shot ataca el déficit de (c): convierte acciones genéricas en acciones específicas que citan la señal medida y dirigen al responsable correcto. **C3 es la configuración de producción**: `main()` puebla `examples` con `select_examples(3, stages=["Vendor","Carrier","DC"])`, `add_llm_explanations` lo pasa a `build_prompt`, y el `po_output.csv` del entregable se genera con C3. El 4.75/5 es el benchmark que seleccionó a C3 frente a C1/C2, no la cifra final: el endurecimiento del prompt en #143 cerró el único fallo restante (aún a temp 0.3), y la re-validación a la temperatura real de producción en `fixtures/eval_quality_20pos_C3_t09.md` confirma **20/20 (5/5)** a 0.9, sin regresión. **La cifra titular del entregable es 5/5** — la que describe la configuración que produce `po_output.csv` hoy; ver [documentation/metricas-proyecto.md](../documentation/metricas-proyecto.md) para la progresión completa con procedencia. El flag `--zero-shot` reproduce el baseline C0. Ver la sección [Diseño del prompt](#diseño-del-prompt).
- El parseo de la respuesta JSON del LLM está centralizado en `_parse_llm_json()` para evitar duplicar lógica entre backends.
- El backend `local` (Qwen) tiene fallback a texto libre si el modelo no devuelve JSON válido; los backends cloud (`claude`, `deepseek`) no, porque se espera que sigan instrucciones de formato de forma más confiable.
- Los tres backends comparten la misma interfaz (`call(prompt, max_retries)`), por lo que agregar un nuevo proveedor solo requiere implementar una clase nueva y registrarla en `create_backend()`.