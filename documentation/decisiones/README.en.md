# Architecture Decision Record (ADR Log)

This space contains the historical record, reasoning, and evolution of data engineering design decisions made throughout the project, validated in collaboration with mentor Joseph.

## Resulting Live Distribution (247 Delayed POs)
Following the rigorous application of the criteria from the current ADRs (especially the asymmetric adjustment of thresholds and the new neutral taxonomy), the final distribution of delay attribution in production is:
*   **Vendor:** 131 POs (53.0%)
*   **Carrier:** 40 POs (16.2%)
*   **DC:** 37 POs (15.0%)
*   **Indeterminate:** 39 POs (15.8%) → *Divided into 15 `sin_datos` + 24 `sin_causa_dominante`*

## Decision Index (Chronological Log and Evolution)

| Code | Architecture Decision | Status | Context and Code Links |
| :--- | :--- | :--- | :--- |
| [ADR-01](ARD-01.en.md) | Source of truth for flags: calc vs. precalc | 🟢 Current | Issue #15, PR #44 |
| [ADR-02](ARD-02.en.md) | Hierarchy with multiple active flags | 🟢 Current | Issue #39, Discussion #52 |
| [ADR-03a](ARD-03a.en.md) | VENDOR Stage: Initial measurement by operational residual | 📘 Superseded | PR #59 |
| [ADR-03b](ARD-03b.en.md) | VENDOR Stage: Measurement by direct signal STA push | 🟢 Current | Issue #40, Discussion #57, PR #62, PR #64, PR #66 |
| [ADR-04a](ARD-04a.en.md) | Provisional carrier threshold (4h) | 📘 Superseded | Initial hard-coded setup |
| [ADR-04b](ARD-04b.en.md) | Definitive carrier threshold (8h) | 🟢 Current | Issue #41, Discussion #53, `rules_config.json` |
| [ADR-05](ARD-05.en.md) | Reschedule and short-ship: context, not stage | 🟢 Current | Issue #42, Discussion #54, Variable `_short_ship` |
| [ADR-06a](ARD-06a.en.md) | Vendor-specific threshold: Initial model without threshold | 📘 Superseded | Initial implementation of direct signal |
| [ADR-06b](ARD-06b.en.md) | Vendor-specific threshold: Definitive configuration of 24h | 🟢 Current | Consultation R2 (2026-06-18), Discussion #57, PRs #62, #66, #64 |
| [ADR-07](ARD-07.en.md) | Indeterminate taxonomy | 🟢 Current | Consultation R2 (2026-06-18), Discussion #57, PR #62 |
| [ADR-08](ARD-08.en.md) | `stage_modifiers`: designed and removed | 📘 Superseded | PR #74 |
| [ADR-09](ARD-09.en.md) | User personas as design criteria for Phase 4 | 🟢 Current | Sync mentors 2026-06-26, Issues #102/#103, `../user_personas.en.md` |
| [ADR-10](ARD-10.en.md) | Hybrid severity: the LLM emits it, Phase 2 rule audits it | 🟢 Current | Issue #92, #93, kickoff §03/§08, `_severidad` |
| [ADR-11](ARD-11.en.md) | Handling secrets and security of API keys (multi-vendor LLM) | 🟢 Current | Best Practices OpenAI, `llm_integration.py`, `.env.example`, `.gitignore` |
| [ADR-12](ARD-12.en.md) | Phase 3 prompt design: few-shot that teaches reasoning, with unique source (production winner: C3) | 🟢 Current | Issue #99, #94 (benchmark), #91/#67, ADR-10, `llm_integration.py` (`build_prompt`) |
| [ADR-13](ARD-13.en.md) | LLM inference temperature: evaluation 0.3–0.9 and anchor decision | 🟢 Current | Issue #137, ADR-14 (#143), #94 (benchmark), ADR-12, `eval_diversity.py`, `llm_config.json` |
| [ADR-14](ARD-14.en.md) | Hardened Phase 3 prompt against overfitting to few-shot | 🟢 Current | Issue #143, #137/#144, #94 (benchmark), ADR-12, ADR-07, `llm_integration.py` (`build_prompt`) |
| [ADR-15](ARD-15.en.md) | Conditional domain context by (actor × signal) to diversify the prompt | 📘 Superseded | Superseded by [ADR-16](ARD-16.en.md); Issue #151, #143/#154, #94 (benchmark), ADR-12/13/14, ADR-07, `llm_integration.py` (`select_domain_context`), `domain_kb.json` |
| [ADR-16](ARD-16.en.md) | The LLM as an analytical layer over the validated deterministic baseline | 🔵 Draft (agent track 2 and local judge open) | Mentor feedback (post-validation of main), ADR-14/12/10/07, [ADR-15](ARD-15.en.md) (📘 superseded), `llm_integration.py`; see [ADR-19](ARD-19.en.md) (partial delivery of track 3) |
| [ADR-17](ARD-17.en.md) | Visual language and color coding of the taxonomy | 🟢 Current | Issue #162, #159 (design system), #163/#164; ADR-09/10, [ADR-07](ARD-07.en.md); `config.py`, `styles.css` |
| [ADR-18](ARD-18.en.md) | Canonical source language and naming convention for bilingual documentation (ES→EN) | 🟢 Current | Issue #88, #96 (discarded), `../plan-traduccion.en.md` |
| [ADR-19](ARD-19.en.md) | LLM integration for holistic analysis of root cause and enrichment with statistical scorecard | 🟢 Current | Mentor feedback, ADR-16 (track 3, complementary); `llm_integration_network_intelligence_view.py`, `scorecard_core.py` |
| [ADR-20](ARD-20.en.md) | Telegram bot as an additional consumption channel | 🔵 Draft | PR #193 (bot), PR #194 (SAD/SRS), Issue #196; distinction from Issue #160 (deferred chatbot, track 3 of ADR-16); ADR-09; `04_app/telegram_bot/` |
| [ADR-21](ARD-21.en.md) | Tier-1/tier-2 data contract of `po_output.csv` (incl. `agente1_raw.txt`) | 🔵 Draft | Issue #158 (tier 1), Issue #161 (tier 2), PR #174; ADR-09/10, ADR-16 (track 1); `04_app/config.py`, `llm_integration_network_intelligence_view.py` |
| [ADR-22](ARD-22.en.md) | Spec for rework of F4 interface: key information per person and executable checklist | 🔵 Draft | Issue #130; ADR-09, ARD-17, ARD-21; issue #197 |
| [ADR-23](ARD-23.en.md) | Mockups as design basis for rework of F4 interface and its reconciliation with ARD-17/ARD-22 | 🔵 Draft | Local mockups "Mockups analytics delayed POs"; ARD-22, ARD-17, ARD-20; `04_app/` |
| [ADR-24](ARD-24.en.md) | Late Shipment rule from the README: discarded due to a nonexistent column | 🟢 Current | Issue #17, ADR-03b, README of the mentor's original repo |
| [ADR-25](ARD-25.en.md) | Future work roadmap: localization, themes/dark mode, and conversational chatbot | 🔵 Draft | Definition session (2026-07-20), ADR-16/17/18/20, `04_app/` |

## Process and Integration Notes
*   **Documentation Standard:** The entire technical record of the project is governed by the **MADR (Markdown Architecture Decision Records)** template, formally chosen by the team following the documented debate in discussion [#79](https://github.com/CCMarv/po-delay-analyzer/discussions/79).
*   **Historical Immutability:** According to the adopted standard, superseded decisions (like the initial logic of `ADR-03a`, `ADR-04a`, or `ADR-06a`) are neither edited nor deleted quietly in the repository. Their historical record is preserved (`📘 Superseded`) and linked via relative links to the new records that replace them (`🟢 Current`).

---
*This log directly feeds into the closing deliverables D-4 (root README of the project) and D-5 (Analytical validation of the business).*