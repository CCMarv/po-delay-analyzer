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
pytest      # 244 tests; configuración en pyproject.toml
```

La suite cubre el pipeline (Fase 1), el clasificador y las métricas (Fase 2), el contrato de
handoff entre fases y la integración LLM (Fase 3). No requiere API: los tests de LLM usan
fixtures y stubs, no llamadas reales.

El CI (`.github/workflows/ci.yml`) corre `pytest` en cada push y cada PR. El gate de merge
vigente es **self-review + CI en verde**: mergeas tú mismo cuando ambos pasan, sin esperar
revisión bloqueante.

## Changelog

No se mantiene un `CHANGELOG.md` por ahora: el avance se rastrea por issues, milestones y el
registro de decisiones (ADRs en `documentation/decisiones/`). Adoptar Keep a Changelog +
SemVer queda como opción a futuro si el equipo decide marcar hitos de versión.
