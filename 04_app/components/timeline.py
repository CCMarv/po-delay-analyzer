"""Segmento de timeline reutilizable (sistema de diseño, ARD-17).

Un segmento = un tramo del lifecycle del PO (p. ej. STA_DT → APPROVED_DT).
`highlighted` marca el tramo con mayor excess_*_hrs / responsable del delay
(T2.2, vista Diego). Devuelve HTML para incrustarse en la página que arma el
timeline completo ordenando los segmentos.
"""
from config import STAGE_COLORS


def timeline_segment_html(label: str, timestamp: str, stage: str, highlighted: bool = False) -> str:
    """HTML de un segmento del timeline. `stage` fija el color del borde (hue de etapa)."""
    key = stage.lower() if stage else "indeterminado"
    if key not in STAGE_COLORS:
        key = "indeterminado"
    state_class = " timeline-segment--highlighted" if highlighted else ""
    return (
        f'<div class="timeline-segment timeline-segment--{key}{state_class}">'
        f'<span class="identifier">{label}</span>'
        f'<span class="timestamp">{timestamp}</span>'
        f"</div>"
    )
