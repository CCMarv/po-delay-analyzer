# Mockups as the Design Basis for the Interface Retake of F4 and Its Reconciliation with ARD-17/ARD-22

* **Status:** 🔵 **DRAFT** (to be closed by the team — executed by G7)
* **Technical Context:** Phase 4 / App — visual retake of `04_app` (Streamlit); G7 unit for the
  closing orchestration, executed on the checklist of ARD-22 §7
* **References:** [ARD-22](ARD-22.en.md) (spec of information by person and executable checklist —
  still current in WHAT; this ARD establishes HOW visually); [ARD-17](ARD-17.en.md) (visual language,
  protected except as reviewed below); [ARD-21](ARD-21.en.md) (tier-1/tier-2 contract); [ARD-20](ARD-20.en.md)
  (Telegram bot, fixed command reading channel); Issue #130; local mockups
  "Mockups analytics Late POs" (`Home Landing.dc.html`, `Exception Workbench.dc.html`,
  `Network Intelligence.dc.html`, light and dark theme); `04_app/app.py`,
  `04_app/pages/1_🔍_Exception_Workbench.py`, `04_app/pages/2_📊_Network_Intelligence.py`,
  `04_app/config.py`, `04_app/components/`, `04_app/assets/styles.css`

## Context and Problem

G7 started with a plan that treated a visual reference generated in claude.ai/design as a non-contractual guide: the ARD-22 §7 checklist mandated; any mockup introducing anything from
the ARD-17/ARD-22 §6 prohibitions list was discarded as a non-reference. Upon reviewing the three
complete mockups (landing + 2 views, light/dark) with the team, the instruction changed: the
mockups **are the initial truth** of the retake — the base design to implement — and the contract is
reconciled against them, not the other way around. Where a mockup clashes with an existing rule, the rule is
reviewed here; the mockup is not adapted to the contract unless the original reason for the rule (not the
rule itself) continues to apply directly.

## Considered Options

**Option A — Maintain the mockup as a non-contractual reference (original plan of G7).**
Pros: zero risk of reopening already closed decisions of ARD-17/ARD-22. Cons: it is not what the
team requested; leaves unresolved why the mockup differs from the contract on several specific points
instead of explicitly deciding which prevails.

**Option B — Mockup prevails without exception, including the colored stage wording on the landing
(literal fidelity).** Pros: zero ambiguity of criteria. Cons: reopens the original reason of
ARD-17 §5 (WCAG contrast) without the mockup providing a new reason to invalidate it — the text
Carrier (#E69F00) on a white background falls to ≈2.2:1, well below the minimum text (4.5:1); it is
the same problem that motivated the rule, not a different case.

**Option C — Mockup prevails; each real clash is documented and adapted only where the original
reason for the rule directly counters the mockup (chosen).** It preserves the intent of "the
mockup is the truth" for everything that is indeed a design decision (typography, density, layout,
what is shown), and reserves adaptation to a single case with an objective technical reason
(accessibility), not preference.

## Decision

The three mockups of "Analytics Late POs Mockups" are the base design of G7. Fully audited, **they do not introduce any hard prohibitions** of ARD-17/ARD-22 §6: they retain the Okabe-Ito color palette by stage, the achromatic ramp + icon/shape (■◆●) for severity and risk, horizontal stacked bars (not pie/donut/3D), line with direct labeling (not legend), monospaced typography for technical data, and the app remains read-only. They are, essentially, a denser and polished restyle of content that ARD-22 §7 had already specified (D1–D4, R1–R2, T1–T3), plus the landing (outside of §7) with secondary access to the Telegram bot.

### a. Revisions to the contract imposed by the mockup (the mockup wins)

1. **Trust badge without `%`.** The mockup shows only the bucket ("High"), without the raw number
   in parentheses. More stringent than the original wording of ARD-22 §7 D5 (which left the `%` as an acceptable secondary) and aligned with the general principle of §6 ("bucket badge for trust, never raw number") — it closes the ambiguity in favor of the stricter reading. `components/badges.py::confidence_badge_html` stops interpolating `{score:.0%}`.
2. **Numerical risk score eliminated from Ravi's executive cards.** The previous code
   (`render_exec_card_v3`) displayed a line "Risk Score: 100.0/50.0/0.0" which was a literal recoding of the same ordinal that the zone badge already carries (High=100, Medium=50, Low=0, fixed in `parse_informe_completo`). The mockup does not include it. It is removed: the badge is already the signal; the number did not add information, it simply duplicated it on another scale.
3. **Conditional aggravating flags with explicit empty state.** The previous code always showed
   two affirmative lines ("✅ Standard PO" / "✅ Full Shipment") when the flags did not apply. The
   mockup only displays the pills when the flag is active, with the caption "Shown only when applicable to the PO." This pattern is adopted, adding a state "No active aggravations" for when none apply — it avoids losing the signal of "no aggravations" without duplicating two lines of confirmation that did not provide new reading.
4. **Stage hue only on the highlighted segment of the timeline.** Previously, the 7 segments had their
   colored border by the stage of the full PO (redundant in 6 out of 7 events). The mockup only colors
   the border of the responsible segment; the rest use a neutral border (`--border-subtle`). The
   color again signals "which segment matters" instead of decorating all 7 equally.
   `components/timeline.py::timeline_segment_html` gains a parameter `segmented_label` for the pill
   "SEGMENT {STAGE} — responsible stage" that the mockup adds next to the first highlighted segment.
5. **Landing with a card for secondary access to the Telegram bot.** Outside the original checklist of
   ARD-22 §7 (which only touched `app.py` for the source footer), the mockup includes it as part of the base design of the landing. Consistent with [ARD-20](ARD-20.en.md): link to a fixed command reading channel, not an embedded chat or export (protected by §6). The bot handle is not secret (unlike the token) but is also not documented as public data in ARD-20; it is resolved via `TELEGRAM_BOT_USERNAME` in `.env` (placeholder in `.env.example) — if absent, the card describes the channel without an active button, without inventing a handle.

### b. Sole adaptation to the mockup (the contract wins)

**Colored stage words as text → chips with colored dot.** The mockup of the landing paints "Vendor"/"Carrier"/"DC"/"Indeterminate" as text in the hue of its stage. Carrier
(`#E69F00`) on a white background gives ≈2.2:1 contrast, well below the minimum WCAG for text
(4.5:1) — exactly the reason that motivated ARD-17 §5 ("color lives in branding, not text"). It is adapted to a chip (color dot + text in neutral ink), the same idiom that the distribution legends of the mockup itself (Network Intelligence) already use — it is not an invention, it is generalizing a pattern that the mockup already uses elsewhere. Reusable via `.stage-chip` in `styles.css`.

### c. Data guards (the mockup is illustrative, not the source)

The figures of the three mockups (247 POs, 13.8% disagreement, entity names, cutoff date "2025-11-30" / "April 30, 2026") are illustrative of the design, not actual data from the artifact.
All rendered values in `04_app` continue to be computed from the loaded `df` (`load_po_output`) or from the real JSON scorecards — no figures from the mockup are hardcoded. The cutoff date uses `config.dataset_cutoff_date(df)` (maximum timestamp of the 7 columns of the lifecycle), not a fixed date. The columns of the consolidated tables by actor are those brought by each real JSON, not those illustrated by the mockup.

### d. Minor deviations declared (do not require reopening anything)

- The consolidated tables by actor and the table of POs with disagreement remain in `st.dataframe`
  (functional, sortable, data-driven) instead of the static HTML table of the mockup — same
  content, different engine for being the idiomatic Streamlit for real tabular data.
- The source footer uses ISO date format (`YYYY-MM-DD`) on the 3 pages, including the landing (the landing mockup uses "April 30, 2026" in Spanish; the other two mockups already use ISO).
  It is unified to ISO for consistency across the 3 pages and to avoid relying on the operating system's locale for month names in Spanish.

## Consequences

**Positive:**
- The retake of interface F4 remains faithful to a concrete design already reviewed by the user, not to
  a textual interpretation of the ARD-22 §7 checklist.
- Revisions to the contract are documented with their reason, not applied silently — a future reader understands why the trust badge no longer shows `%` or why the timeline changed its color rule.
- The sole adaptation to the mockup has an objective reason (accessibility), not preference, and reuses a pattern that the mockup itself already employs.
- The landing comes into scope with an explicit decision regarding access to Telegram (conditional link, without invented handle), instead of remaining deferred unresolved.

**Negative:**
- Two components that ARD-22 §7 marked as "do not touch" (`badges.py`, `timeline.py`) come into
  the scope of G7 — greater scope than originally planned, although limited to the changes described
  above.
- The landing becomes dependent on a new operational environment variable (`TELEGRAM_BOT_USERNAME`)
  that the team must set for the Telegram button to appear; without it, the card remains informative without action.

## Relation to Other Decisions

Executes and extends [ARD-22](ARD-22.en.md) (which remains current on what information is shown by person); ARD-22 §7 remains as the content checklist, this ARD as the record of the visual revisions that its execution (G7) found necessary. It specifically reviews
[ARD-17](ARD-17.en.md) §5 on the three points of section "a" (trust badge, redundant score, hue of the timeline), without reopening its Okabe-Ito palette, its severity ramp, or its graph type prohibitions. It consumes [ARD-20](ARD-20.en.md) for access to Telegram from the landing (link, not the channel itself). It does not reopen [ADR-10](ARD-10.en.md) or [ARD-21](ARD-21.en.md).