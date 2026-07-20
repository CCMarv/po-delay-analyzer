# Team Conventions — po-delay-analyzer

> This document collects the **team agreements**: how we name and classify work, what labels we use, when something is an issue / a discussion / a chat message, and under what rule we integrate into `main`. It is the *what we agreed upon*, not the *how to type it*.
>
> 📖 **The step-by-step git/GitHub tutorial** (create branch, commits, open PR, resolve conflicts, command flow) lives in the pinned post in
> [Discussions → 📣 Announcements → "Team Git Guide"](https://github.com/CCMarv/po-delay-analyzer/discussions/27).
> We moved it there because it is material for *operational onboarding*, not project description: the repo describes the product and its decision-making process; the git tutorial lives where the team communicates.
>
> Objective of these agreements: so that anyone can know at a glance what a ticket is, who has it, and in what state it is — without opening it and without live coordination. And that the result is also documentation that the mentor can review.

---

## 0. The Change Lifecycle (the map)

Every change follows the same path. This document covers the **rules** for each stage; the **step-by-step commands** are in the [git guide](https://github.com/CCMarv/po-delay-analyzer/discussions/27).

```
  gap / idea  →  issue(s)  →  branch  →  commits  →  PR + self-review  →  CI green
              →  merge (yourself, without waiting for approval)  →  issue closed
              →  (optional cross-review, AFTER)
```

**The most important thing to understand:** we do not wait for another person's approval to merge (see [§4](#4-the-non-blocking-merge-rule)).

---

## 1. From a Gap to an Issue

A **gap** is anything you detect that the project needs: a bug, an improvement, a missing piece of the pipeline, a finding from the EDA that needs investigation, a pending design decision, technical debt. The first task is to **turn that gap into one or more well-formed issues.**

### Is it one or multiple issues?
An issue should be able to **be closed in half a day to a day**. If when thinking about it you see that there are many steps, that it touches multiple areas, or that it has parts that can advance separately → **break it down**. Large tickets are invisible on the board and difficult to distribute.

Real example: "fix the reproducibility of the pipeline" is not an issue; it is several:
move `requirements.txt` (#8), convert `pipeline_core.py` into a module (#9), load the local CSV (#10), add tests (#12), CI (#13). Each one closes by itself and unlocks the next.

### Dependencies: what awaits what
When you break down a gap, almost always some issues depend on others. Note it in the *Dependencies* field of the issue, linking with `#N`:

- **`Depends on: #N`** — I cannot start (or finish) until `#N` closes.
- **`Blocks: #N`** — others are waiting on me.

This matters **a lot** in an asynchronous team: GitHub draws the blocking graph, so whoever comes in to work sees what is free and what is not, without having to ask. An issue can also **open** others: if while working you discover something new, open an issue for it and link it (do not force it into the current one).

### Is it a task, a bug, or a decision?
This determines which template you use:

| If the gap is… | Template |
|---|---|
| Concrete work to execute (most common) | **Task** |
| Something is wrong and needs fixing | **Bug / Correction** |
| A choice needs to be made before proceeding | **Decision** |

Rule: if you don't know *what to do* but *what to decide*, it is a Decision, not a Task.

---

## 2. Writing the Issue

### Choose the Template
When creating *New issue* in GitHub, you will see three options (blank issues are not allowed, on purpose: the template guides you):

- **Task** — executable work. Asks for area, phase, context, steps, DoD, dependencies.
- **Bug / Correction** — asks for symptom, how to reproduce, expected vs observed, evidence.
- **Decision** — asks who decides, the question, options with trade-offs.

#### If you create the issue from the terminal (`gh`)
The templates above are *Issue Forms* (`.yml`): GitHub only renders them on the web (with their dropdowns and required fields). `gh issue create` in the terminal **cannot** use them. To avoid improvising the issue, there are mirror drafts in 
[`documentation/plantillas-cli/`](plantillas-cli/) (`tarea.md` · `decision.md` · `bug.md`) that reproduce the same sections. The flow:

```
cp documentation/plantillas-cli/tarea.md /tmp/issue.md   # copy and fill in
gh issue create --title "[docs] ..." --label docs \
  --milestone "Phase 1 — Pipeline + EDA" --assignee "@me" --body-file /tmp/issue.md
```

The metadata that the form captures with dropdowns goes here as flags: `--label` (area), `--milestone` (phase), `--assignee` (owner). The only thing lost is the **mandatory validation** of the form: GitHub will not prevent you from creating the issue with empty sections, so filling them out correctly is part of your self-review.

### Title: `[area] Imperative verb + object`
- **`[area]`** in lowercase (the templates already do this): `pipeline` · `eda` ·
  `analysis` · `infra` · `docs` · `llm` · `app`.
- **Verb + concrete object.** No period. Concise.

| Phase | Title |
|------|--------|
| 1 | `[pipeline] Load the CSV from data/raw/ local` |
| 1 | `[infra] Move requirements.txt to the root and create .env.example` |
| 2 | `[analysis] Define stage taxonomy and map rules` |
| 3 | `[llm] Design prompt v1 with few-shot of match/mismatch cases` |
| 4 | `[app] PO selector → classification + explanation + action` |

**Rule:** if you cannot write the title with a clear verb + object, the ticket is probably too large or vague — break it down or clarify it.

### The metadata goes in the GitHub fields, not in the title

| Field | Purpose | How |
|-------|----------|------|
| **Milestone** | the **phase** | `Phase 1 — Pipeline + EDA`, etc. The deadline = the Monday check-in. |
| **Assignee** | the **owner** | You self-assign it when taking it (signal of "I will take care of it"), not when creating. |
| **Labels** | **area** + markers | one from area + 0 or more markers (see below). |
| **Project** | the **status** | column on the board (see below). |

#### The board (4 columns)
The status of each ticket is its column in the *"PO Delay Analyzer — Board"*:

| Column | Meaning |
|---------|-------------|
| **Todo** | In the backlog, no one has taken it. |
| **Assigned** | Has an owner (you self-assigned) but is not being worked on yet. |
| **In Progress** | Is being worked on **now**. It is the signal for asynchronous coordination: it lets others know that the ticket is taken. |
| **Done** | Merged and issue closed. |

> **Cross-review is NOT a column.** The board goes directly from *In Progress* to *Done*
> because we merge without waiting for review (see [§4](#4-the-non-blocking-merge-rule)).
> Cross-review exists, but it is **subsequent and optional**: it happens on `main` already integrated, and if anything is found, it opens a follow-up issue — it is not a step in the flow.

#### Labels (closed list — do not add without agreement)
- **Area (exactly one):** `pipeline` · `eda` · `analysis` · `infra` · `docs` ·
  `llm` · `app`.
- **Markers (zero or more):**
  - `fundamental` — unlocks others or is on the critical path; take first.
  - `team-decision` — trade-off that **we can resolve all three asynchronously**, without waiting for Monday. The Decision template adds this automatically.
  - `mentor-consult` — trade-off that **needs the mentor's input** → goes to the Monday meeting. Use it only when it genuinely requires the mentor's approval; most decisions are resolved among us.

> Two levels of decision: Monday is the meeting with **the mentor** (external stakeholder),
> but the three of us communicate any day. Do not block a decision waiting for Monday
> if we can take it among ourselves — that is `team-decision`. Reserve `mentor-consult`
> for what truly needs their approval.

### The Definition of Done (DoD)
The DoD answers **"When is it REALLY finished?"** with *verifiable* criteria, not with "it looks good." They are written as boxes `- [ ]` so that progress is visible on the board without opening the code.

The last box is the **global DoD** and goes in all work tickets:

> Run in a clean environment (`venv` from `requirements.txt`) · CI green · self-review done · no secrets/data/outputs committed.

---

## 3. Working the Issue: Branch, Commits, and PR

These are the **agreements**; the how is in the
[git guide](https://github.com/CCMarv/po-delay-analyzer/discussions/27).

- **One branch per issue, never work directly on `main`.** Name:
  `type/<name>-<short-task>` (`feat` · `fix` · `docs` · `chore`). E.g.
  `feat/vidaurri-csv-local`. The phase does NOT go in the name. The name is **proposed from the issue** (section *Suggested branch* of the body), so that whoever takes it does not improvise; you can adjust it if needed when starting.
- **Small and frequent commits**, message `area: description in imperative (Closes #N)`.
  The `Closes #N` closes the issue automatically upon merging.
- **Never commit:** secrets / API keys (they go in `.env`, gitignored) · the data CSV (`data/raw/` gitignored) · **outputs from notebooks** (clean them before commit).
- **At the end, open a PR** with the template (it fills itself) and `Closes #N`.

---

## 4. The Non-blocking Merge Rule

**We do not wait for another to review before merging.** Common practice says otherwise,
but **it does not work for us:** we work in very different time zones (Vidaurri at night; María and Isaac in the morning). If Vidaurri finishes something at 2am and has to wait for someone to review it in the morning, that change stays stuck — and **blocks the sequential work** of whoever depends on it. The team is stalled.

That is why the merge gate is **you + CI**:

1. Complete the **self-review** of the PR (runs cleanly, tests pass, no secrets/data/outputs, DoD met).
2. **Wait for CI to pass green.**
3. **Merge yourself**, with *"Create a merge commit"*. Then delete the branch; the issue closes automatically, and `main` remains in its ideal state.

**Cross-review still exists — but it is optional and SUBSEQUENT.** When another member has a moment, they review **already merged** PRs (on `main`). If they find something, **open a follow-up issue** — do not revert or reprimand. This way we keep the second pair of eyes (which the mentor values in the rubric: *Collaboration & Professionalism*) without stalling anyone.

> ⚠️ While **CI does not yet exist** (issues #12 and #13), the temporary gate is:
> self-review + "tests/pipeline pass locally" verified manually. Setting up CI is a priority: it is the safety net that replaces the human reviewer.

The step-by-step for PR, merging, and conflict resolution is in the
[git guide](https://github.com/CCMarv/po-delay-analyzer/discussions/27).

---

## 5. Discussions: Team Memory

Not everything the team communicates is work: there are doubts, debates that have not yet matured, and announcements. Putting that into issues muddies them; leaving it only in chat loses it. That's what **GitHub Discussions** is for: asynchronous communication that **leaves searchable memory**, outside the board and ephemeral chat.

### The three paths — when to use each one

| Path | Purpose | Persistence |
|-----|----------|--------------|
| **Issue** | Work to execute, or a decision already made that leaves actionable trace (board, DoD, `Closes #N`). | Permanent, **on the board**. |
| **Discussion** | A reusable response question · debating a trade-off that **has not matured yet** · an announcement. | Permanent, **searchable**, outside the board. |
| **Chat** | Immediate unblocking, coordination of the moment ("Is anyone working on the notebook?"). | **Ephemeral** — lost when scrolling. |

**Golden Rule:** *if someone will want to find this in a month, it does not go in chat.* And if it is already **concrete work or a posed decision**, it is not a discussion: it is an **issue**.

### The 3 Categories

- **📣 Announcements** — what happens on Monday with the mentor, team agreements, changes in direction.
  This is the bulletin board: it is read, not debated. (This is where the
  [pinned git guide](https://github.com/CCMarv/po-delay-analyzer/discussions/27) lives.)
- **🤔 Decisions (debate)** — think aloud about a trade-off **before** it becomes a formal Decision issue. The thread is the memory of the *why*.
- **❓ Questions / Q&A** — questions with reusable answers. The correct answer is marked so that it is searchable for the next person with the same doubt.

### The Bridge Discussion → Issue (important, avoids overlap)

A reasonable doubt: *if I already have the template [Decision](#1-from-a-gap-to-an-issue), why "🤔 Decisions (debate)" in Discussions?* Because they are two different moments:

- **Discussions = thinking aloud.** The trade-off is still vague, there are no clear options, you are probing with the team. A Decision issue here would be premature (what options do you present if you do not have them yet?).
- **Decision issue = the recorded decision.** When the debate matures — there are options with their trade-offs and something blocks — the thread **graduates**: you open an issue with the template [Decision](../.github/ISSUE_TEMPLATE/2-decision.yml), link the thread in the context, and there remains the formal choice (with its labels `team-decision` / `mentor-consult` and whatever is blocking).

This way, duplication is avoided: Discussions keeps the *how we arrived at the thought*; the issue keeps *what was decided*.

---

## 6. Synchronization of the Team

- **Monday 9:00 = meeting with the mentor** (external stakeholder): sprint review + planning,
  and issues needing `mentor-consult` are resolved.
- **Among the three of us, any day:** asynchronous communication via chat for `team-decision`, unblockings, and quick doubts.
- **The board is the coordination signal.** Moving to *In Progress* before starting alerts the others that someone has taken the ticket. The *Notes* of the issue are the handoff: if you work while others sleep, that is your delivery.

---

## 7. Quick Reference (cheat-sheet)

### Issue, Discussion, or Chat?
| What you are going to communicate… | Path |
|---|---|
| Work to execute or a decision already posed | **Issue** |
| Doubt with reusable answer · debate not yet mature · announcement | **Discussion** |
| Immediate and ephemeral unblocking | **Chat** |

### Which template do I use? (if it is an issue)
| The gap is… | Template |
|---|---|
| Work to execute | **Task** |
| Something is wrong | **Bug / Correction** |
| A choice needs to be made | **Decision** |

### Labels
`pipeline` · `eda` · `analysis` · `infra` · `docs` · `llm` · `app` (area, one) ·
`fundamental` · `team-decision` · `mentor-consult` (markers).

### The How (step-by-step git)
Create branch, commits, PR, merge, and conflicts →
[Team Git Guide (Discussions)](https://github.com/CCMarv/po-delay-analyzer/discussions/27).