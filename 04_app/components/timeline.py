"""Segmento de timeline reutilizable (sistema de diseño, ARD-17/ARD-23).

Un segmento = un tramo del lifecycle del PO (p. ej. STA_DT → APPROVED_DT).
`highlighted` marca el tramo con mayor excess_*_hrs / responsable del delay
(T2.2, vista Diego). Devuelve HTML para incrustarse en la página que arma el
timeline completo ordenando los segmentos.

ARD-23 revisa el idiom: el hue de etapa solo vive en el/los tramo(s)
resaltado(s) — los no-responsables llevan borde neutro (`--border-subtle`),
para que el color vuelva a ser señal ("qué tramo importa") y no decoración
repetida en los 7 eventos. `tramo_label`, si se da, agrega la pill
"TRAMO {ETAPA} — etapa responsable" (mockup Exception Workbench).
"""
from config import STAGE_COLORS


def timeline_segment_html(
    label: str,
    timestamp: str,
    stage: str,
    highlighted: bool = False,
    tramo_label: str | None = None,
) -> str:
    """HTML de un segmento del timeline.

    `stage` determina el hue solo cuando `highlighted=True`; los segmentos no
    resaltados usan un borde neutro. `tramo_label`, si se pasa, añade la pill
    de tramo responsable junto al timestamp — en todos los segmentos
    resaltados de un PO (nota de cierre ARD-17, 2026-07-22: limitarla al
    primero dejaba a los demás comunicando su etapa solo por hue).
    """
    key = stage.lower() if stage else "indeterminado"
    if key not in STAGE_COLORS:
        key = "indeterminado"
    state_class = " timeline-segment--highlighted" if highlighted else ""
    stage_class = f" timeline-segment--{key}" if highlighted else ""

    pill_html = ""
    if tramo_label:
        pill_html = (
            f'<span class="timeline-pill">'
            f'<span class="timeline-pill__dot timeline-pill__dot--{key}"></span>'
            f"{tramo_label}</span>"
        )

    return (
        f'<div class="timeline-segment{stage_class}{state_class}">'
        f'<span class="identifier">{label}</span>'
        f"{pill_html}"
        f'<span class="timestamp">{timestamp}</span>'
        f"</div>"
    )
