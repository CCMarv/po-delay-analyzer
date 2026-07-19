"""Badges reutilizables — etapa, severidad, confianza (sistema de diseño, ARD-17).

Devuelven el fragmento HTML (no renderizan) para poder incrustarse dentro de
las tarjetas compuestas por cada página vía `st.markdown(..., unsafe_allow_html=True)`.
"""
from config import STAGE_COLORS, SEVERITY, confidence_bucket


def stage_badge_html(stage: str) -> str:
    """Badge de etapa (hue categórico Okabe-Ito). `stage`: vendor/carrier/dc/indeterminado."""
    key = stage.lower() if stage else "indeterminado"
    if key not in STAGE_COLORS:
        key = "indeterminado"
    return f'<span class="badge-stage badge-stage--{key}">{key.upper()}</span>'


def severity_badge_html(severity: str) -> str:
    """Badge de severidad (rampa de luminancia + ícono/forma + texto). `severity`: HIGH/MEDIUM/LOW."""
    key = severity.upper() if severity else "MEDIUM"
    if key not in SEVERITY:
        key = "MEDIUM"
    entry = SEVERITY[key]
    modifier = key.lower()
    return (
        f'<span class="badge-severity badge-severity--{modifier}">'
        f'<span class="badge-severity__icon">{entry["icon"]}</span>{entry["label"]}'
        f"</span>"
    )


def confidence_badge_html(score: float) -> str:
    """Badge de confianza: bucket ordinal (Alta/Media/Baja) a partir del escalar
    `llm_confianza`. Solo el bucket, sin el % crudo (ARD-23: el número exacto
    sugiere una precisión que el bucket ordinal no pretende — mismo mecanismo
    que severidad, "nunca número crudo" de ARD-22 §6)."""
    bucket = confidence_bucket(score)
    return f'<span class="badge-confidence badge-confidence--{bucket["key"]}">{bucket["label"]}</span>'
