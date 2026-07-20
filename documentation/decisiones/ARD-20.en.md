# Telegram Bot as an Additional Consumption Channel

* **Status:** 🔵 **DRAFT** (closed by the team)
* **Technical Context:** Phase 4 / App — alternate consumption channel to Streamlit, via Telegram
* **References:** PR #193 (bot deployment), PR #194 (SAD/SRS), Issue #196 (documenting the bot as
  an additional channel — retrofit); Issue #160 (deferred conversational chatbot, distinction with this
  decision); ADR-09 (user personas Diego/Ravi); `04_app/telegram_bot/` (`bot.py`, `config.py`,
  `services/auth.py`, `services/data_service.py`, `handlers/diego.py`, `handlers/ravi.py`)

## Context and Problem

Streamlit requires opening a browser session. The two individuals from ADR-09 are not always in front
of a dashboard: Diego queries for specific POs while working in another system; Ravi wants an
aggregate view without opening the app. A Telegram bot (PR #193) was developed outside the board
(without a prior issue) fulfilling exactly that need — 13 versioned files under
`04_app/telegram_bot/`, functional, with the same data layer that is consumed by `04_app` — but without
any ARD or mention in the root README, which states "Deferred Chatbot" in the phase status section. A
reader could reasonably confuse that label with the already built bot when it actually refers to a
different capability (see below). The closure audit marked it as a significant decision residing in code
without documentation (H3.12, H2.8).

## Distinction from #160 (the "deferred chatbot")

These are two distinct capabilities sharing the word "bot":

- **#160** — "Conversational Chatbot for diagnostics." It is open Q&A: the user
  asks in natural language and the LLM reasons about the dataset at query time. It corresponds
  to the agentic track 3 of [ARD-16](ARD-16.en.md) and is explicitly deferred — it is not part
  of this deliverable.
- **The Telegram bot** (this ARD) exposes **fixed and structured commands** —
  `/po`, `/timeline`, `/alerts`, `/hot` (Diego's profile); `/kpi`, `/scorecards`, `/distribution`,
  `/trend`, `/mismatches`, `/mismatches_chart` (Ravi's profile); `/start` and `/help` common— that
  read **already calculated** data (`po_output.csv`, scorecards from [ARD-19](ARD-19.en.md)) without
  invoking the LLM at query time. There is no free reasoning or open conversation: it is a
  second front-end over the same data contract of Phase 4.

Confusing them would lead one to believe that the conversational chatbot (#160) already exists, or that the
Telegram bot (already built) is mistakenly considered out of scope.

## Considered Options

**Option A — Do not document it (treat it as exploratory, outside the formal deliverable).**
Pros: does not require additional documentation work. Cons: it is versioned code, functional,
that exposes real dataset data with a proprietary authorization model; hiding it does not make
it disappear — an evaluator exploring the repo finds it without context (as the audit already documented),
and the README would still claim the opposite of what is on disk.

**Option B — Document it as a deliverable consumption channel (chosen).** It reflects the reality of
the repo: the bot has already passed the correction of its two authorization bugs (`_REPO_ROOT` resolved
to the actual repo root, `is_authorized` fail-closed when the whitelist is empty — both corrected in the
robustness unit prior to this ARD) and is functional. Documenting it provides traceability, allows auditing
its data surface, and closes the gap that #196 asks to resolve. Cons: makes an existing debt explicit —
duplicates the data layer of `04_app/`
(`data_service.py`, canonical column list) instead of sharing it; see Consequences.

## Decision

The Telegram bot is an **additional consumption channel** for the same artifacts produced by Phase 3
(`po_output.csv`, scorecards) — not a new product nor the conversational chatbot from #160. It is documented as a deliverable:

1. This ARD records the architecture (commands by profile, authorization gate) and the distinction
   from #160.
2. The propagation to discovery surfaces (root README, directory tree, SAD/SRS) is
   document synchronization work from another unit (G8 of the closing ledger) — this ARD is the
   source of the decision, not the place where those surfaces are updated.
3. A dedicated README for `04_app/telegram_bot/` (currently nonexistent) stands as a natural follow-up to
   #196, outside the scope of this reconciliation.

## Consequences

**Positive:**
- Closes the traceability gap detected by the audit: an architectural decision that
  only existed in code now has a record.
- Provides an explicit criterion to avoid confusing this channel with the deferred conversational chatbot.
- The authorization gate (`require_auth` + `require_profile`) is already fail-closed: empty whitelist
  = no one authorized, instead of the fail-open it had before the robustness correction.

**Negative:**
- **Duplication of the data layer** (debt, not resolved here): `telegram_bot/services/data_service.py`
  and `telegram_bot/config.py` reimplement the artifact loading and the canonical column list instead of
  sharing them with `04_app/services/data_service.py` and `04_app/config.py`.
  The two copies of the contract will diverge at the first new column if they are not shared. A candidate
  for future refactor, not blocking for this deliverable.
- A second authorization surface that must be kept synchronized with the variables in `.env`
  (`TELEGRAM_USER_WHITELIST`, `TELEGRAM_RAVI_USER_IDS`) in addition to the Streamlit flow.

## Relation to Other Decisions

It does not supersede any previous ARD. It consumes the data contract from [ARD-21](ARD-21.en.md) (tier-1/tier-2
of `po_output.csv`) and the scorecards from [ARD-19](ARD-19.en.md). It serves the individuals Diego/Ravi of
**ADR-09** through a different channel than Phase 4 (Streamlit). It is explicitly distinguished from the
conversational track 3 of **ARD-16** (#160, deferred).