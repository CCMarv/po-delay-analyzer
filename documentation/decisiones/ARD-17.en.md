# Visual Language and Color Coding of the Taxonomy

* **Status:** 🟢 **CURRENT** (closed 2026-07-14)
* **Technical Context:** Phase 4 / Design System — visual coding of the taxonomy (stage, severity, and confidence of the LLM) shared by the two consumer surfaces of the app; implementation associated with #159
* **References:** Issue #162; #159 (design system); #163 / #164 (views Diego / Ravi); Munzner (*What–Why–How*), Cleveland–McGill (graphic channel hierarchy), Okabe–Ito (*Color Universal Design*), WCAG 2.1 (§1.4.3 text, §1.4.11 non-textual objects); ADR-09 (people); ADR-10 (hybrid severity); [ADR-07](ARD-07.en.md) (taxonomy of Indeterminate); `04_app/config.py`, `04_app/assets/styles.css`, `04_app/components/badges.py`, `04_app/components/timeline.py`

## Context and Problem

The Phase 4 app exposes three derived variables to two consumers (Diego and Ravi, ADR-09): the **stage** of the delay (Vendor / Carrier / DC / Indeterminate, taxonomy of ADR-07), the **severity** emitted by the LLM and audited by the Phase 2 rule (ADR-10), and the **confidence** of the model (`llm_confidence`, scale 0–1). All three are displayed repeatedly in cards, tables, and graphs; without a unique visual language, each view encodes them differently, and the reader has to relearn the color on each screen.

The previous palette of the app (`#2E86AB`, `#A23B72`, `#F18F01`, `#C73E1D`…) has two defects. First, it is arbitrary: colors chosen for aesthetics, without a framework justifying why each stage receives its hue. Second, it is not safe for color vision deficiency (CVD): ~8% of men have some red-green deficiency, and categorical coding that relies on hue distinctions collapses under deuteranopia/protanopia, making it unreadable for that fraction of the audience.

The underlying problem is not just what colors to use, but **which visual channel encodes each variable**. The stage is nominal (unordered categories), the severity is ordinal (ranked levels), and the confidence is a continuous scalar grouped into ordinal levels. Encoding all three with arbitrary hues confuses the types of variables and causes two color scales to compete for the categorical attention of the reader. A rule—rather than a preference—anchored in a reference framework is needed for the encoding to be reproducible and defensible. The adopted framework is Munzner's (*What–Why–How*: choose the channel based on the task) based on the effectiveness hierarchy of Cleveland–McGill (position and length are decoded with less error than angle, area, or color).

## Considered Options

**Stage Palette — Okabe–Ito (chosen).** The *Color Universal Design* palette of Okabe–Ito is designed to be distinguishable under all three types of color blindness and in grayscale. Pros: accessibility by design, with published backing; stable hues that are reused identically throughout the app. Cons: fixed range (colors are not chosen based on brand preference).

**Stage Palette — previous palette of the app (discarded).** The current hues (`#2E86AB`/`#A23B72`/`#F18F01`/`#C73E1D`) are discarded for not being CVD-safe and lacking a framework: there is no way to defend the choice beyond aesthetics.

**Severity Encoding — achromatic luminance ramp + icon + text (chosen).** Severity is encoded by luminance (ordered channel) reinforced with shape (icon) and text label. Pros: redundancy survives color blindness and gray printing; does not compete with the stage hue. Cons: gives up part of the “at-a-glance” alarm provided by semantic red (mitigated by icon and text).

**Severity Encoding — semantic red-amber-green (discarded).** This is the intuitive mapping of urgency, but it fails in deuteranopia/protanopia (cannot distinguish red from green) and, since it would be a second hue scale, it would compete with stage encoding for the same channel.

**Severity Encoding — single non-neutral hue, e.g. slate blue (discarded).** A single dark-to-light hue ramp would be ordered and CVD-safe, but shares the hue family with Vendor (`#0072B2`) and could be read as related to that stage despite the redundant icon and text. Achromatic gray avoids that semantic collision.

## Decision

1. **Selection Framework.** The channel is chosen based on the task (Munzner) respecting the hierarchy of Cleveland–McGill: position/length over angle/area. Direct consequence: **prohibited** are pie, donut, treemap, and 3D charts; no *chartjunk*; direct labeling on marks instead of remote legends; Lie Factor = 1.0 (the size of the mark proportional to the data).

2. **Stage = categorical hue (Okabe–Ito), identical throughout the app.** The Indeterminate uses a neutral gray, not another color from the scale: its semantics is “without attributable cause” (absence of dominant stage, ADR-07), and gray conveys that without suggesting a fourth category at the same level as the three real ones. The dark theme variant adjusts the **luminance** of each hue for the background, without changing the hue.

   | Channel | Level | Light Theme | Dark Theme |
   | :--- | :--- | :--- | :--- |
   | Stage (hue) | Vendor | `#0072B2` | `#4DA8DB` |
   | | Carrier | `#E69F00` | `#F0B840` |
   | | DC | `#009E73` | `#3FC79A` |
   | | Indeterminate (neutral gray) | `#767676` | `#9B9B9B` |
   | Severity (ordinal + icon) | ■ HIGH | `#3D3D3D` | `#E8E8E8` |
   | | ◆ MEDIUM | `#6B6B6B` | `#A8A8A8` |
   | | ● LOW | `#A8A8A8` | `#6B6B6B` |

3. **Severity = ordinal, does not compete for hue.** It is encoded with an achromatic luminance ramp (charcoal gray) reinforced with shape (■ HIGH / ◆ MEDIUM / ● LOW) and text label, **confined to severity contexts**. In light theme, darker = more urgent (HIGH `#3D3D3D`). In dark theme, the ramp **reverses in luminance** (HIGH `#E8E8E8`) to maintain the same perceptual principle: the HIGH extreme is always the one with the highest contrast against the background. The triple redundancy (luminance + shape + text) makes the encoding robust against color blindness and gray printing.

4. **Confidence (`llm_confianza`, 0–1) = same ordinal mechanism, no icon.** It reuses the luminance ramp of severity, grouped into three buckets: **High** 0.80–1.00 (sufficient evidence), **Medium** 0.50–0.79 (requires human verification), **Low** < 0.50 (insufficient data). It is displayed as a bucket badge, not as raw numbers or a gauge.

5. **WCAG Contrast.** Text is always in the neutral foreground (`--text-primary`: dark in light theme, light in dark theme); **never** is text colored with the stage/severity hue. Color only exists in *swatches*, icons, and graph marks, which as non-textual objects require 3:1 (WCAG §1.4.11) and not the 4.5:1 of text (§1.4.3). The background/mark combinations for both themes were verified through relative luminance calculation; exact values are found in `styles.css`.

6. **Graph Selection by Task** (inherited by views #163 / #164): distribution by stage → **horizontal bar** (replaces the previous `px.pie`); severity → **ordered bar** HIGH > MEDIUM > LOW; LLM disagreement ↔ rule → **KPI + bar by stage**; trend over `PO_DT` → **line with direct labeling**; journey of a PO → **static `px.timeline`** that highlights the section with the highest `excess_*_hrs`; confidence → **bucket badge** (not dotplot, not gauge).

## Consequences

**Positive:** the entire app —both views of Diego (#163) and Ravi (#164)— inherits a single encoding, defined once in `config.py`/`styles.css`, with no hex values scattered outside of those sources. The encoding is accessibility-by-design (color blindness, WCAG contrast, and readability in grayscale) and defensible: each choice refers to a published framework, not to aesthetics. The separation of channels (hue = nominal stage; luminance + shape = ordinal severity) prevents two scales from competing for the reader's attention.

**Negative:** the achromatic severity ramp cedes part of the immediate alarm provided by learned semantic red (mitigated with icon + label). **Known Limitation:** the native *chrome* of Streamlit (sidebar, some widgets) does not respect `prefers-color-scheme`; only custom components (navbar, badges, cards, timeline) respond to the system theme. That *chrome* is outside the reach of `config.py`/`styles.css`/`components/` (#159).

## Relation to Other Decisions

This serves the two consumer surfaces motivated by **ADR-09** (people Diego / Ravi). It maintains **ADR-10**: the official severity is issued by the LLM and audited by the Phase 2 rule; this ARD only fixes its **visual encoding**, not changing its source nor superseding it. It takes from **[ADR-07](ARD-07.en.md)** the taxonomy of Indeterminate, which justifies the treatment in neutral gray (absence of attributable cause, not a peer category to the other three). It does not supersede or chain any previous ARD: it is a new layer of visual encoding over current decisions.

## Closing Note (2026-07-22)

The ADR↔repo audit found that point 5 (WCAG contrast) claimed a relative-luminance
verification that, recalculated against the app's three real backgrounds in `styles.css`, did
not hold for two swatches: Carrier (`#E69F00`, 2.05-2.25:1) and severity/confidence Low
(`#A8A8A8`, 2.16-2.38:1), both below the required 3:1. They were corrected to **`#B88000`**
(Carrier) and **`#8A8A8A`** (Low) — same hue/saturation, only brightness reduced — verified at
≈3.1:1 against `--surface-elevated` (the most demanding of the 3 backgrounds). Additionally,
the timeline's text pill (point 6, Diego's view) was found to be assigned only to the first
highlighted segment of a PO: when Carrier spans 2 segment columns, the second communicated its
stage by hue alone, without the text redundancy the rest of the app otherwise honors. This was
fixed so every highlighted segment carries its pill. The selection framework
(Munzner/Cleveland-McGill/Okabe-Ito), the stage-hue table, and the rest of the encoding are not
reopened — only these two hex values and the pill assignment.