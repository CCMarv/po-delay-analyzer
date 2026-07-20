# Live demo script (EN)

Step-by-step script for the colloquium's live demo, run against the final Phase 4
application (`04_app`). Derived from the approved Spanish source, `guion-demo.md`; if the two
ever disagree, the Spanish version governs (ARD-18). Satisfies the mentor kickoff's literal
mandate ("Slides + demo: select a delayed PO and see the AI's explanation live") and the DoD
of issue #106 ("a mismatch case that showcases the thesis"). Referenced from slide 9 of
`presentacion-final.en.md`.

**Language note:** the application itself is Spanish-only — page headers, button captions,
card titles, checkbox labels, tooltips, and the LLM's own generated text (explanation,
hypothesis, action plan) are all in Spanish. Translating the app's interface was never part
of the bilingual scope (ADR-18 covers versioned documentation and the presentation; the
per-PO LLM outputs are explicitly excluded, and the rest of the UI chrome was never in scope
either). During an English-language delivery, the presenter narrates in English while
pointing at a Spanish-language screen — this script gives the exact Spanish strings to look
for alongside their English meaning, so the presenter is never searching for a label mid-demo.

## Pre-requisites

- The app must already be running **before** the talk starts: `streamlit run 04_app/app.py`
  from the repo root. Do not start it live in front of the panel.
- Zero API calls during the demo: everything shown is already generated on disk
  (`data/processed/po_output.csv`, `data/processed/scorecards/*.json`,
  `data/processed/agente1_raw.txt`). The demo cannot fail on cost or on a downed API — only
  on the app not running, hence this pre-requisite.
- Demo PO: **#100236** (BIOPLEX, Vendor, hot PO, severity HIGH). Rationale for the choice in
  `presentacion-final.en.md` ("Choice of demo case").

## Step 1 — Landing

Entry screen (`app.py`). Point out in one sentence the two available views —Exception
Workbench (Diego) and Network Intelligence (Ravi)— and the Telegram-bot access card. Click
"Abrir Network Intelligence →" (Spanish button label; reads "Open Network Intelligence →").

## Step 2 — Network Intelligence (Ravi's view)

Walk through, in this order:

1. The three KPIs on the left: total late POs (247), % high severity, and the "Tasa de
   Desacuerdo AI" KPI (Spanish label; reads "AI Disagreement Rate"). **When reaching this
   one, clarify in one sentence**: this figure (currently ~38.5%, 95/247) is the LLM's own
   per-PO judgment on whether its diagnosis matches the human `REASON_DSC` — related to, but
   not the same figure as, the 88.8% reason agreement cited on the Validation and Metrics
   slide (that one is computed by the Phase 2 rule against a curated grouping, not by the
   LLM). See the full explanation of why these are two distinct measurements in
   `presentacion-final.en.md`.
2. The distribution by stage and by severity (horizontal bars).
3. The temporal trend of late POs.
4. One executive card from "Diagnóstico Estratégico" (Spanish section title; reads
   "Strategic Diagnosis") for Vendor — the section showing the aggregate reading per entity,
   with its risk level and recommended action.

## Step 3 — Drill-down into Diego

Scroll down to "Ver detalle de un PO (Exception Workbench)" ("View detail of a PO"). Check
the box labeled "Solo POs con desacuerdo AI vs humano" ("Only POs with AI vs. human
disagreement") to narrow the list. In the selector, pick "PO #100236". Click "Ver en
Exception Workbench →" ("View in Exception Workbench →").

## Step 4 — Exception Workbench (Diego's view), PO #100236 already preselected

The app lands directly on the chosen PO (the drill-down preselects it in the "Número de PO:"
selector — "PO number:"). Walk through, in this order:

1. **Quick context**: Delay 5.3 d · Vendor BIOPLEX · Carrier FedEx Freight · DC Phoenix.
2. **The five diagnosis cards**: Etapa (Stage) = Vendor · Severidad (Severity) = HIGH ·
   Confianza LLM (LLM Confidence) = Alta ("High" — the app shows the bucket label, not the
   raw number) · Validación AI vs Humano (AI vs. Human Validation) = "⚠️ Desacuerdo"
   ("Disagreement"), with the caption "un desacuerdo es un hallazgo a revisar, no un error
   del LLM" ("a disagreement is a finding to review, not an LLM error") · Reason Humano
   (Human Reason) = "Equipment/trailer issue" (this one is in English in the source data
   itself).
3. **Exceso de la etapa asignada** ("Excess of the assigned stage"): "Exceso Vendor: 94.5
   hrs" ("Vendor excess: 94.5 hrs"), with the on-screen note that this is the excess over
   that stage's expected window, not a component that adds to the total delay.
4. **Aggravating-factor flags**: the "🔥 HOT PO — Prioridad máxima" pill ("HOT PO — Top
   priority"; this PO is urgent, no short shipment).
5. **7-event timeline** — this is the centerpiece of the demo. Point out that the
   highlighted segment (carrying the "TRAMO VENDOR — etapa responsable" pill, "VENDOR
   SEGMENT — responsible stage") covers exactly the gap between "📦 STA" (2025-04-04) and
   "✅ Cita Aprobada" ("Appointment Approved," 2025-04-08, late at night): almost 5 days of
   waiting there, while the next four events —trailer arrival, check-in, check-out,
   receipt— all happen within the same ~5 hours the following day. The delay sits entirely
   in the appointment approval, not anywhere downstream.
6. **"Diagnóstico Diferencial" panel** ("Differential Diagnosis" — the tier-2 panel) — this
   is the AI's explanation live, the moment the kickoff calls for:
   - Main hypothesis: planning and resource-management problems at vendor BIOPLEX, which did
     not allocate adequate capacity to meet the urgent PO.
   - Evidence: a 5.26-day delay and a 94.5-hour vendor excess, with a 100% fill rate (rules
     out a product shortage).
   - Alternate hypothesis: congestion at the vendor's facilities.
   - Discriminant step: confirm BIOPLEX's space and resource availability on the delay date.
   - Staged plan: immediate action (ask BIOPLEX for a planning report), corrective (provide
     resources or look for alternatives), preventive (a communication protocol to
     prioritize future urgent orders).

## Step 5 — Close

Return to the landing page. Mention the Telegram bot as an additional read-only channel (if
`TELEGRAM_BOT_USERNAME` is configured in the demo environment, show the QR from the
expander).

## If something fails live

Since there are no network calls, the only possible failure is the app not running or its
Streamlit process having restarted. Keep a second tab with the app already open as a backup,
and have PO #100236 written down to type directly into the selector if the drill-down does
not land on its own.
