# Secret Management and API Key Security (Multi-Vendor LLM)

* **Status:** 🟢 **Current** (closed 2026-07-19; opened 2026-06-27)
* **Technical Context:** Phase 3 / LLM Integration — API provider credentials
* **References:** Best Practices for API Key Safety (OpenAI Help Center, 7 practices);
  `03_llm_integration/llm_integration.py` (backends Claude/OpenAI/DeepSeek, `create_backend`);
  `.env.example`; `.gitignore`; `documentation/convenciones-issues.en.md` (policy "never commit secrets")

## Context and Problem
The deliverable invokes several LLM providers (Claude, OpenAI, DeepSeek; local Ollama without key)
and includes OpenAI as the backend of the CSV deliverable. Each provider requires an API key, a secret
whose leakage exposes the account's quota to charges and abuse. The code already resolves the keys
from environment variables, but a unique, documented policy was needed to establish where each key
lives, how it is named, who owns it, and what to do in the event of a leak. Without this record,
each new provider integration risks reintroducing a key in code, in a versioned CLI argument, or in 
the template.

## Considered Options

### Option A: Key embedded in code or passed via CLI
* **Pros:** Does not require environment setup; starts without prior steps.
* **Cons:** Direct leak vector: the key remains in git history, shell logs, 
  issues, or PRs. Contradicts OpenAI practices #3 and #4. Discarded.

### Option B: Environment variables with `python-dotenv` and `.env` gitignored
* **Pros:** Separates the secret from the code (Twelve-Factor); standard variable name by
  provider, consistent within the team; `.env` excluded from git; `.env.example` template
  versioned with empty placeholders. Covers practices #1–#4 and #6. Already implemented in the
  code (`load_dotenv`, `os.environ.get`).
* **Cons:** Relies on human discipline (not pasting the key in a command that gets committed);
  the `.env` lives in plain text on each individual's machine.

### Option C: Key management service (Vault / AWS Secrets Manager / Google Secret Manager) + IP allowlisting
* **Pros:** Centralized encryption and access control; OpenAI practices #5 and #7. Standard
  for production deployment.
* **Cons:** Overengineering for an academic deliverable that runs locally, without deployment
  infrastructure. Out of scope for now; recorded as future evolution.

## Decision
**Option B** is adopted. API keys are managed via environment variables loaded with
`python-dotenv` from a `.env` file at the root, excluded from git. The name of each variable is the
provider standard (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `DEEPSEEK_API_KEY`). Each person uses their own key; keys are not shared. Keys are never written in code, in versioned CLI arguments, nor in issues/PRs/logs. In case of a suspected leak, the key is immediately rotated in the provider's panel and the team is alerted. The key is never exposed in the client; calls originate from the local backend. Practices #5 (key management service) and #7 (IP allowlisting) are documented as production debt, not implemented within this scope.

## Consequences
* **Positive:** Reproducible and secure for the deliverable's scope without extra infrastructure;
  aligned with OpenAI's 7 applicable practices; the guardrail in
  `.claude/instructions.md` makes it operational for both assistants; adding a new provider
  follows the same pattern (standard variable + placeholder in `.env.example`).
* **Negative:** Security relies on human discipline and a `.env` in plain text per
  machine; no automatic rotation or centralized access control. If the project were to move to
  production, this decision would need to be reopened towards Option C (chain new ADR).

## Closing Note (2026-07-19)
The closing audit detected that `llm_integration.py` was still implementing `--api-key`
—Option A that this ADR marks as "Discarded"— as the main example in its docstring and in
the order of its error messages. The CLI flag has been removed (only the resolution via
`.env` remains), reconciling the code with the decision already made here; no option is reopened.