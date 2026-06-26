"""Configuración global de la aplicación Streamlit."""
from pathlib import Path

# ── Rutas del proyecto ──────────────────────────────────────────────────────
APP_DIR = Path(__file__).resolve().parent
REPO_ROOT = APP_DIR.parent

DATA_RAW_DIR = REPO_ROOT / "data" / "raw"
DATA_PROCESSED_DIR = REPO_ROOT / "data" / "processed"

# CSV crudo de entrada (Fase 1)
PO_RAW_CSV = DATA_RAW_DIR / "po_root_cause_synthetic.csv"

# Rutas a módulos de fases anteriores
PHASE1_DIR = REPO_ROOT / "01_data_pipeline_and_eda"
PHASE2_DIR = REPO_ROOT / "02_clasif_reglas_negocio"

# ── Columnas clave del DataFrame clasificado ────────────────────────────────
COL_PO = "PO_NBR"
COL_VENDOR = "VENDOR_NAME"
COL_CARRIER = "CARRIER_PARTY_NAME"
COL_DC = "DC_LOC_NAME"
COL_STAGE_PRIMARY = "stage_primary"
COL_DC_SUBSTAGE = "dc_substage"
COL_SEVERITY = "severity"
COL_DELAY_DAYS = "delay_days_calc"
COL_EXCESS_VENDOR = "excess_vendor_hrs"
COL_EXCESS_CARRIER = "excess_carrier_hrs"
COL_EXCESS_YARD = "excess_yard_hrs"
COL_EXCESS_DOCK = "excess_dock_hrs"
COL_EXCESS_DC = "excess_dc_hrs"
COL_IS_RESCHEDULED = "is_rescheduled"
COL_IS_SHORT_SHIP = "is_short_ship"
COL_IS_SHORT_LEAD = "is_short_lead"
COL_STAGE_MULTI = "stage_multi"
COL_REASON_MANUAL = "reason_group_manual"
COL_APPT_LEAD_DAYS = "appt_lead_days"
COL_CARRIER_MEDIBLE = "_carrier_medible"
COL_DC_MEDIBLE = "_dc_medible"
COL_INDETERMINADO_SUB = "indeterminado_substage"

# ── Umbrales de severidad (coinciden con rules_config.json) ─────────────────
SEVERITY_HIGH_DAYS = 3.0
SEVERITY_LOW_DAYS = 1.0

# ── Paleta de colores ───────────────────────────────────────────────────────
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


# ── Archivo LLM Output ───────────────────────────────────────────────────
LLM_OUT_CSV = DATA_PROCESSED_DIR / "llm_out.csv"

# Columnas LLM
COL_LLM_CAUSA_RAIZ = "llm_causa_raiz"
COL_LLM_ACCION = "llm_accion_recomendada"
COL_LLM_SEVERIDAD = "llm_severidad"
COL_LLM_COINCIDE = "llm_coincide_con_reason"
COL_LLM_CONFIANZA = "llm_confianza"