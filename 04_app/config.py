"""Configuración global de la aplicación Streamlit — Fase 4."""
from pathlib import Path

# ─ Rutas del proyecto ──────────────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
DATA_PROCESSED_DIR = REPO_ROOT / "data" / "processed"

# ── Artefacto de handoff F3→F4 (único input de la app) ─────────────────────
PO_OUTPUT_CSV = DATA_PROCESSED_DIR / "po_output.csv"

# ── Scorecards por entidad (JSON del motor offline scorecard_core.py) ──────
# Regenerables y gitignored; la app los lee, no recomputa la capa estadística.
SCORECARDS_DIR = DATA_PROCESSED_DIR / "scorecards"

# ── Columnas canónicas del contrato F3→F4 ─────────────────────────────────
COL_PO = "PO_NBR"
COL_STAGE = "stage"
COL_SEVERITY = "severity"
COL_EXPLANATION = "explanation"
COL_ACTION = "action"

# ─ Columnas del timeline (lifecycle del PO) ───────────────────────────────
COL_PO_DT = "PO_DT"
COL_STA_DT = "STA_DT"
COL_APPROVED_DT = "APPROVED_DT"
COL_TRAILER_ARRIVE_DT = "TRAILER_ARRIVE_DT"
COL_CHECKIN_DT = "CHECKIN_DT"
COL_CHECKOUT_DT = "CHECKOUT_DT"
COL_RECPT_DT = "RECPT_DT"

# ── Columnas de validación y flags ─────────────────────────────────────────
COL_HOT_PO_FLAG = "HOT_PO_FLAG"
COL_IS_SHORT_SHIP = "is_short_ship"
COL_REASON_DSC = "REASON_DSC"
COL_LLM_COINCIDE = "llm_coincide_con_reason"

# ── Columnas de enriquecimiento tier 1 (contrato F3→F4, #158/#167) ────────
COL_LLM_CONFIANZA = "llm_confianza"
COL_VENDOR_NAME = "VENDOR_NAME"
COL_CARRIER_NAME = "CARRIER_PARTY_NAME"
COL_DC_NAME = "DC_LOC_NAME"
COL_DELAY_DAYS = "delay_days_calc"
COL_EXCESS_VENDOR_HRS = "excess_vendor_hrs"
COL_EXCESS_CARRIER_HRS = "excess_carrier_hrs"
COL_EXCESS_DC_HRS = "excess_dc_hrs"

# Etapa → timestamps que delimitan su tramo de responsabilidad en el lifecycle
# (ver 02_clasif_reglas_negocio/classifier_core.py — Vendor: STA push; Carrier:
# tránsito; DC: yard+dock consolidados). Indeterminado no tiene tramo propio.
STAGE_SEGMENT_COLUMNS = {
    "vendor": (COL_STA_DT, COL_APPROVED_DT),
    "carrier": (COL_APPROVED_DT, COL_TRAILER_ARRIVE_DT),
    "dc": (COL_TRAILER_ARRIVE_DT, COL_CHECKIN_DT, COL_CHECKOUT_DT),
}

# ── Sistema de diseño — paleta (ARD-17) ─────────────────────────────────────
# Etapa: hue categórico Okabe-Ito (CUD), idéntico en toda la app. Indeterminado
# usa gris neutro (no un hue) porque señala "sin causa atribuible", no una
# categoría más de la taxonomía.
STAGE_COLORS = {
    "vendor": "#0072B2",         # Blue
    "carrier": "#E69F00",        # Orange
    "dc": "#009E73",             # Bluish Green
    "indeterminado": "#767676",  # Gris neutro
}

# Severidad: ordinal, NO compite por hue con la etapa — rampa de luminancia
# acromática (gris-carbón) + ícono/forma + etiqueta de texto. La codificación
# por color es redundante, no la única señal.
SEVERITY = {
    "HIGH":   {"color": "#3D3D3D", "icon": "■", "label": "Alta"},
    "MEDIUM": {"color": "#6B6B6B", "icon": "◆", "label": "Media"},
    "LOW":    {"color": "#A8A8A8", "icon": "●", "label": "Baja"},
}

# Confianza (llm_confianza, escalar 0–1): mismo mecanismo ordinal que
# severidad (rampa acromática), sin ícono — solo bucket + texto.
CONFIDENCE_BUCKETS = [
    {"key": "alta", "min": 0.80, "max": 1.00, "color": "#3D3D3D", "label": "Alta",
     "description": "Evidencia suficiente"},
    {"key": "media", "min": 0.50, "max": 0.79, "color": "#6B6B6B", "label": "Media",
     "description": "Requiere verificación humana"},
    {"key": "baja", "min": 0.00, "max": 0.49, "color": "#A8A8A8", "label": "Baja",
     "description": "Datos insuficientes"},
]


def confidence_bucket(score: float) -> dict:
    """Mapea un score de confianza escalar (0-1) a su bucket ordinal."""
    for bucket in CONFIDENCE_BUCKETS:
        if bucket["min"] <= score <= bucket["max"]:
            return bucket
    return CONFIDENCE_BUCKETS[-1]


# Vista plana (retrocompat): las páginas actuales resuelven color por etapa o
# severidad con `COLORS.get(clave.lower(), ...)`. Se consolida aquí para que
# no haya una segunda fuente de verdad de hex.
COLORS = {
    **STAGE_COLORS,
    "high": SEVERITY["HIGH"]["color"],
    "medium": SEVERITY["MEDIUM"]["color"],
    "low": SEVERITY["LOW"]["color"],
}