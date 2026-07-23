# Guía de contribución — PO Delay Analyzer

Este documento reúne en un solo lugar cómo montar el entorno, correr el proyecto y
contribuir. No reemplaza las convenciones del equipo ni el tutorial de git: los enlaza.

- Acuerdos de trabajo (issues, labels, DoD, regla de merge no bloqueante, Discussions):
  [documentation/convenciones-issues.md](documentation/convenciones-issues.md).
- Paso a paso de git (crear rama, commits, abrir PR, resolver conflictos):
  [Guía de git del equipo (Discussion #27)](https://github.com/CCMarv/po-delay-analyzer/discussions/27).

## Reproducibilidad y setup

Requisito: Python 3.13.

```bash
# 1. Clonar
git clone https://github.com/CCMarv/po-delay-analyzer.git
cd po-delay-analyzer

# 2. Entorno virtual
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\Activate.ps1       # Windows (PowerShell)

# 3. Dependencias
pip install -r requirements.txt

# 4. Variables de entorno: copiar la plantilla y rellenar lo que se necesite
cp .env.example .env               # Windows: Copy-Item .env.example .env
```

Datos: el CSV crudo no se versiona (`data/raw/` está en `.gitignore`). Colócalo a mano en la
ruta que el pipeline espera por defecto:

```
data/raw/po_root_cause_synthetic.csv
```

Alternativa: define `PO_CSV_PATH` en `.env` con una ruta absoluta al CSV.

Correr el pipeline (determinístico, sin costo de API):

```bash
# Fase 1 — limpieza + validación (escribe data/processed/df_clean.csv)
python 01_data_pipeline_and_eda/pipeline_core.py

# Fase 2 — clasificación por etapa (recomputa la cadena limpia y clasifica)
python 02_clasif_reglas_negocio/classifier_core.py
```

Correr la Fase 3 (explicaciones LLM). El backend por defecto es `local` (Ollama/Qwen) y el
modo por defecto es `test` (10 POs); ninguno gasta créditos de API:

```bash
python 03_llm_integration/llm_integration.py --mode test --backend local
```

Los backends de pago (`--backend openai|claude|deepseek`) requieren su API key en `.env` y
**gastan créditos** en cada corrida; una corrida `--mode full` procesa todos los POs
retrasados. Confirma el proveedor y el conteo antes de lanzarla.

En Windows, si un script de Fase 3 imprime emojis y la consola falla con `UnicodeEncodeError`,
antepón `PYTHONUTF8=1` (o `set PYTHONUTF8=1` en la sesión).

### Camino completo hasta la app (Fase 4)

La Fase 4 solo **lee** artefactos ya generados aguas arriba (no recomputa nada). Para abrir la
app con el contrato completo (incluida la vista Network Intelligence), en orden:

```bash
# 1-2. Fases 1-2 (offline, ver arriba)

# 3. Fase 3 — diagnóstico + acción de producción. GASTA API (backend openai).
#    --action-call puebla las columnas tier-2 (diagnóstico diferencial, ARD-16);
#    produce data/processed/po_output.csv (contrato F3→F4, 33 columnas, ARD-21).
python 03_llm_integration/llm_integration.py --mode full --backend openai --action-call

# 4. Scorecards por entidad (offline, sin API). Toma dos argumentos posicionales:
#    CSV de entrada y carpeta de salida.
python 03_llm_integration/scorecard_core.py data/processed/df_classified.csv data/processed/scorecards

# 5. Síntesis ejecutiva de red por actor (ADR-19). GASTA API (arquitectura multi-agente,
#    SDK openai-agents). Lee los scorecards del paso 4; requiere --actor all para consolidar
#    el reporte y escribir data/processed/agente1_raw.txt, que consume Network Intelligence.
python 03_llm_integration/llm_integration_network_intelligence_view.py --actor all

# 6. Lanzar la app (lee po_output.csv + scorecards + agente1_raw.txt)
streamlit run 04_app/app.py
```

Los pasos 3 y 5 gastan créditos de API — confirma proveedor y conteo antes de lanzarlos (ver
"Uso de API real" en `.claude/instructions.md`). El paso 4 debe correr antes que el 5: la
síntesis de red lee los JSON de scorecards que ese paso produce. Sin correr Fase 3 localmente,
la app cae a la muestra versionada (`data/samples/`); Network Intelligence necesita el
paso 5 para su panel completo. Detalle del contrato y de cada script en
[`03_llm_integration/README.md`](03_llm_integration/README.md) y
[`04_app/README.md`](04_app/README.md).

### Bot de Telegram (canal adicional, ADR-20)

El bot es un segundo canal de solo lectura sobre el mismo contrato (`po_output.csv`,
scorecards) — no recomputa nada ni gasta API. Tiene su propio archivo de dependencias
(`04_app/telegram_bot/requirements-bot.txt`, no cubierto por el `pip install` del paso 3 de
arriba) y sus propias variables de entorno en `.env.example` (`TELEGRAM_BOT_TOKEN`,
`TELEGRAM_USER_WHITELIST`, `TELEGRAM_RAVI_USER_IDS`, `DEMO_MODE`). Setup y arranque completos
en [`04_app/telegram_bot/README.md`](04_app/telegram_bot/README.md).

## Flujo de trabajo

El ciclo de un cambio: gap → issue → rama → commits → PR + self-review → CI en verde →
merge (tú mismo, sin esperar aprobación) → issue cerrado. La review cruzada existe pero es
posterior y opcional.

Los acuerdos completos (cuándo algo es issue / discussion / chat, títulos, labels, DoD, la
regla de merge no bloqueante) están en
[documentation/convenciones-issues.md](documentation/convenciones-issues.md). El paso a paso
en comandos de git vive en la
[Guía de git del equipo (Discussion #27)](https://github.com/CCMarv/po-delay-analyzer/discussions/27).

## Qué no se commitea

- Secrets y API keys: viven solo en `.env` (gitignored); la plantilla versionada es
  `.env.example` con placeholders vacíos. Nunca se commitea una key real.
- El CSV de datos: `data/raw/` está en `.gitignore`; se coloca a mano (ver setup).
- Outputs de notebooks: límpialos antes de commitear.

## Tests y CI

```bash
pytest      # 267 tests; configuración en pyproject.toml
```

La suite cubre el pipeline (Fase 1), el clasificador y las métricas (Fase 2), el contrato de
handoff entre fases, la integración LLM y el few-shot (Fase 3), y la app Streamlit y el bot de
Telegram — smoke de páginas, servicio de QR, autenticación fail-closed (Fase 4). No requiere API:
los tests de LLM usan fixtures y stubs, no llamadas reales.

El CI (`.github/workflows/ci.yml`) corre `pytest` en cada push y cada PR. El gate de merge
vigente es **self-review + CI en verde**: mergeas tú mismo cuando ambos pasan, sin esperar
revisión bloqueante.

## Changelog

No se mantiene un `CHANGELOG.md` por ahora: el avance se rastrea por issues, milestones y el
registro de decisiones (ADRs en `documentation/decisiones/`). Adoptar Keep a Changelog +
SemVer queda como opción a futuro si el equipo decide marcar hitos de versión.
