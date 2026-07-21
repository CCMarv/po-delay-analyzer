# Contribution Guide — PO Delay Analyzer

This document gathers in one place how to set up the environment, run the project, and contribute. It does not replace team conventions or the git tutorial: it links them.

- Work agreements (issues, labels, DoD, non-blocking merge rule, Discussions):
  [documentation/convenciones-issues.md](documentation/convenciones-issues.en.md).
- Step by step for git (creating a branch, commits, opening PR, resolving conflicts):
  [Team git guide (Discussion #27)](https://github.com/CCMarv/po-delay-analyzer/discussions/27).

## Reproducibility and Setup

Requirement: Python 3.13.

```bash
# 1. Clone
git clone https://github.com/CCMarv/po-delay-analyzer.git
cd po-delay-analyzer

# 2. Virtual environment
python -m venv .venv
source .venv/bin/activate          # macOS / Linux
# .venv\Scripts\Activate.ps1       # Windows (PowerShell)

# 3. Dependencies
pip install -r requirements.txt

# 4. Environment variables: copy the template and fill in what is needed
cp .env.example .env               # Windows: Copy-Item .env.example .env
```

Data: the raw CSV is not versioned (`data/raw/` is in `.gitignore`). Place it manually in the path that the pipeline expects by default:

```
data/raw/po_root_cause_synthetic.csv
```

Alternative: define `PO_CSV_PATH` in `.env` with an absolute path to the CSV.

Run the pipeline (deterministic, no API cost):

```bash
# Phase 1 — cleaning + validation (writes data/processed/df_clean.csv)
python 01_data_pipeline_and_eda/pipeline_core.py

# Phase 2 — stage classification (recomputes the clean chain and classifies)
python 02_clasif_reglas_negocio/classifier_core.py
```

Run Phase 3 (LLM explanations). The default backend is `local` (Ollama/Qwen) and the default mode is `test` (10 POs); neither uses API credits:

```bash
python 03_llm_integration/llm_integration.py --mode test --backend local
```

The paid backends (`--backend openai|claude|deepseek`) require your API key in `.env` and **use credits** for each run; a `--mode full` run processes all delayed POs. Confirm the provider and the count before launching it.

On Windows, if a Phase 3 script prints emojis and the console fails with `UnicodeEncodeError`, prefix with `PYTHONUTF8=1` (or `set PYTHONUTF8=1` in the session).

### Full Path to the App (Phase 4)

Phase 4 only **reads** artifacts already generated upstream (does not recompute anything). To open the app with the full contract (including the Network Intelligence view), in order:

```bash
# 1-2. Phases 1-2 (offline, see above)

# 3. Phase 3 — diagnosis + production action. USES API (openai backend).
#    --action-call populates the tier-2 columns (differential diagnosis, ARD-16);
#    produces data/processed/po_output.csv (contract F3→F4, 33 columns, ARD-21).
python 03_llm_integration/llm_integration.py --mode full --backend openai --action-call

# 4. Scorecards by entity (offline, without API). Takes two positional arguments:
#    Input CSV and output folder.
python 03_llm_integration/scorecard_core.py data/processed/df_classified.csv data/processed/scorecards

# 5. Executive network synthesis by actor (ADR-19). USES API (multi-agent architecture,
#    openai-agents SDK). Reads the scorecards from step 4; requires --actor all to consolidate
#    the report and write data/processed/agente1_raw.txt, which consumes Network Intelligence.
python 03_llm_integration/llm_integration_network_intelligence_view.py --actor all

# 6. Launch the app (reads po_output.csv + scorecards + agente1_raw.txt)
streamlit run 04_app/app.py
```

Steps 3 and 5 use API credits — confirm the provider and count before launching them (see "Using real API" in `.claude/instructions.md`). Step 4 must run before step 5: the network synthesis reads the JSON scorecards produced by that step. Without running Phase 3 locally, the app falls back to the versioned sample (`data/samples/`); Network Intelligence needs step 5 for its complete panel. Details of the contract and each script can be found in
[`03_llm_integration/README.en.md`](03_llm_integration/README.en.md) and
[`04_app/README.en.md`](04_app/README.en.md).

## Workflow

The cycle of a change: gap → issue → branch → commits → PR + self-review → CI green →
merge (yourself, without waiting for approval) → issue closed. Cross-review exists but is
subsequent and optional.

Complete agreements (when something is an issue/discussion/chat, titles, labels, DoD, the non-blocking merge rule) can be found in
[documentation/convenciones-issues.md](documentation/convenciones-issues.en.md). The step-by-step commands for git are in the
[Team git guide (Discussion #27)](https://github.com/CCMarv/po-delay-analyzer/discussions/27).

## What Not to Commit

- Secrets and API keys: exist only in `.env` (gitignored); the versioned template is
  `.env.example` with empty placeholders. A real key should never be committed.
- The data CSV: `data/raw/` is in `.gitignore`; it is placed manually (see setup).
- Notebook outputs: clean them before committing.

## Tests and CI

```bash
pytest      # 266 tests; configuration in pyproject.toml
```

The suite covers the pipeline (Phase 1), the classifier and metrics (Phase 2), the handoff contract between phases, LLM integration and few-shot (Phase 3), and the Streamlit app and Telegram bot — page smoke tests, the QR service, fail-closed authentication (Phase 4). It does not require API: the LLM tests use fixtures and stubs, not real calls.

The CI (`.github/workflows/ci.yml`) runs `pytest` on every push and every PR. The current merge gate is **self-review + CI green**: you merge yourself when both pass, without waiting for blocking review.

## Changelog

No `CHANGELOG.md` is maintained for now: progress is tracked through issues, milestones, and the decision log (ADRs in `documentation/decisiones/`). Adopting Keep a Changelog + SemVer remains an option for the future if the team decides to mark version milestones.