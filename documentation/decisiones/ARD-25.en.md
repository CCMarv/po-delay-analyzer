# Future Work Roadmap: Localization, Themes/Dark Mode, and Conversational Chatbot

* **Status:** 🔵 **Draft** (considered / deferred — closed by the team)
* **Technical Context:** Phase 4 / closing — scope of post-deliverable improvements; direct
  input for the final presentation's roadmap
* **References:** definition session (2026-07-20); [ADR-17](ARD-17.en.md) (design system),
  [ADR-16](ARD-16.en.md) (#160, agentic track 3), [ADR-20](ARD-20.en.md) (Telegram bot vs.
  deferred chatbot), [ADR-18](ARD-18.en.md) (bilingual documentation); commit `c726f23`
  (light-theme lock); `04_app/`

## Context and Problem

The evaluated deliverable is the Streamlit app (`04_app/`, locked to the light theme,
Spanish-only interface, read-only over a frozen CSV) plus the fixed-command Telegram bot.
Three improvement fronts surfaced during closing that exceed the deliverable's scope but
inform its evolution. Declaring them as future work in the presentation avoids improvising
the roadmap live and traces why they stay out of the current deliverable. This record defines
and scopes them; it does not commit to their execution.

## The Three Fronts

**1. Localization (bilingual ES/EN app).** The interface is Spanish-only; the categorical
fields (`severity`, `stage`, `llm_confianza`) are already stored as a code/scalar with the app
assigning the label, so localizing them is trivial (add the English label catalog). The UI
chrome (~1–1.5 days extracting strings into an `es/en` catalog with a `t()` helper and a
language selector) works fine in Streamlit, since a selector does trigger a rerun. The real
cost is the LLM's free text (`explanation`, `action`, reasoning/hypotheses/actions), generated
in Spanish: a genuinely English app requires deciding between re-generating those outputs in
English (a data change, API cost), translating them offline, or accepting a mixed-language
interface.

**2. Themes / dark mode.** The app was locked to light theme (`c726f23`) because Streamlit
does not allow an instant manual CSS toggle: it uses emotion/React with no stable DOM hook,
and switching the native theme does not re-run the Python script, so token injection falls out
of sync. A manual light/dark toggle faithful to the mockups requires a presentation layer
outside Streamlit (static HTML/CSS/JS export, ~3–4 days), where the theme resolves via
`[data-theme]` + `localStorage`.

**3. Conversational chatbot (#160, track 3 of [ADR-16](ARD-16.en.md)).** Distinct from the
already-delivered Telegram bot (fixed, read-only commands over pre-computed data, no LLM at
query time; see [ADR-20](ARD-20.en.md)). The chatbot is open-ended natural-language Q&A where
the LLM reasons over the dataset at query time, with guardrails against hallucination and to
stay scoped to the dataset. It is the largest front: it requires an agentic/retrieval layer,
conversational state, and per-query (not batch) API cost. It could evolve from the bot's
existing infrastructure (`bot.py` already has a `MessageHandler` for free text) or as a new
app view.

## Options Considered

**Option A — Do not declare future work.** Leaves the presentation without a roadmap and
risks an evaluator reading the current limits (Spanish, light theme, fixed commands) as
undirected gaps. Discarded.

**Option B — Declare it as future work / potential improvements, with no date commitment
(chosen).** Presents the three fronts as possible evolution of the deliverable, making clear
that the current app is what is being evaluated. Honest about the calendar and traces
direction without committing deliveries.

**Option C — Roadmap with committed dates and priorities.** Discarded: the closing calendar
does not allow committing to dates and would raise the presentation's risk.

## Decision

The three fronts are declared as future work / potential improvements, with no date
commitment. Assumptions for the roadmap: the bilingual app is set as a future goal (with the
LLM content decision still open); the Telegram bot is presented as a delivered capability, and
the conversational chatbot (#160) as deferred future evolution, consistent with
[ADR-20](ARD-20.en.md) and [ADR-16](ARD-16.en.md).

## Consequences

**Positive:** a traced roadmap now feeds directly into the presentation's future-work slide
and explains the deliverable's limits as decisions, not omissions.

**Negative:** the LLM content decision for i18n (re-generate vs. translate vs. mixed) and the
chatbot's per-query API cost remain open. It is kept as a contract principle for future
phases that the data holds the code and the app assigns the label, which cheapens the
localization of categorical fields.

**Pending:** consolidating this with additional candidates from an exploratory roadmap
session (suggested veins: deployment/hosting, performance/caching, test/CI coverage,
accessibility beyond color, export/reporting, auth/security hardening, observability, ADR-16's
open agentic track 2 and local judge, ADR-20's data-layer duplication debt, the Late
Shipment/`VENDOR_SHIP_DT` gap already closed by [ADR-24](ARD-24.en.md)) is out of scope for
this record and is resolved in a future session; this ARD documents only the three fronts
already decided.

## Relation to Other Decisions

Does not supersede any prior ARD. Consumes the design system from **ADR-17**, the distinction
between the delivered Telegram bot and the deferred chatbot from **ADR-20**/**ADR-16** (track
3), and the language policy from **ADR-18**. Does not reopen **ADR-24** (Late Shipment rule,
already closed).
