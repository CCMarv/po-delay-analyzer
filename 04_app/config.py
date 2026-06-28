"""Configuración global de la aplicación Streamlit — Fase 4."""
from pathlib import Path

# ─ Rutas del proyecto ──────────────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent
DATA_PROCESSED_DIR = REPO_ROOT / "data" / "processed"

# ── Artefacto de handoff F3→F4 (único input de la app) ─────────────────────
PO_OUTPUT_CSV = DATA_PROCESSED_DIR / "po_output.csv"

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

# ── Paleta de colores ─────────────────────────────────────────────────────
COLORS = {
    "vendor": "#2E86AB",
    "carrier": "#A23B72",
    "dc": "#F18F01",
    "indeterminado": "#C73E1D",
    "on_time": "#6A994E",
    "high": "#E63946",
    "medium": "#F4A261",
    "low": "#2A9D8F",
}