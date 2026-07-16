"""Configuración del bot de Telegram — Fase 5.

Lee variables de entorno desde .env (mismo archivo que Fase 4).
"""
import os
from pathlib import Path

# ── Token del bot ───────────────────────────────────────────────────────────
# Cargar desde .env en la raíz del repo
from dotenv import load_dotenv

_REPO_ROOT = Path(__file__).resolve().parent.parent
_DOTENV_PATH = _REPO_ROOT / ".env"
if _DOTENV_PATH.exists():
    load_dotenv(_DOTENV_PATH)

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
if not TELEGRAM_BOT_TOKEN:
    print("⚠️  TELEGRAM_BOT_TOKEN no definido en .env. El bot no arrancará.")

# ── Whitelist de usuarios autorizados ───────────────────────────────────────
# IDs de Telegram separados por comas (opcional: si está vacío, cualquiera usa
# el bot; si tiene valores, solo esos IDs pueden ejecutar comandos).
# Formato en .env: TELEGRAM_USER_WHITELIST=12345678,87654321
_WHITELIST_STR = os.getenv("TELEGRAM_USER_WHITELIST", "")
TELEGRAM_USER_WHITELIST = (
    {int(uid.strip()) for uid in _WHITELIST_STR.split(",") if uid.strip()}
    if _WHITELIST_STR
    else set()
)

# ── Perfiles de usuario ────────────────────────────────────────────────────
# IDs de Telegram que tienen perfil "Ravi" (analista). El resto son "Diego"
# (coordinador de excepciones). Si está vacío, todos son Diego.
_RAVI_STR = os.getenv("TELEGRAM_RAVI_USER_IDS", "")
TELEGRAM_RAVI_USER_IDS = (
    {int(uid.strip()) for uid in _RAVI_STR.split(",") if uid.strip()}
    if _RAVI_STR
    else set()
)

# ── Rutas de datos (reusando la misma estructura que Fase 4) ────────────────
REPO_ROOT = _REPO_ROOT
DATA_PROCESSED_DIR = REPO_ROOT / "data" / "processed"
PO_OUTPUT_CSV = DATA_PROCESSED_DIR / "po_output.csv"
SCORECARDS_DIR = DATA_PROCESSED_DIR / "scorecards"

# ── Columnas canónicas (mismas que 04_app/config.py) ────────────────────────
COL_PO = "PO_NBR"
COL_STAGE = "stage"
COL_SEVERITY = "severity"
COL_EXPLANATION = "explanation"
COL_ACTION = "action"

COL_PO_DT = "PO_DT"
COL_STA_DT = "STA_DT"
COL_APPROVED_DT = "APPROVED_DT"
COL_TRAILER_ARRIVE_DT = "TRAILER_ARRIVE_DT"
COL_CHECKIN_DT = "CHECKIN_DT"
COL_CHECKOUT_DT = "CHECKOUT_DT"
COL_RECPT_DT = "RECPT_DT"

COL_HOT_PO_FLAG = "HOT_PO_FLAG"
COL_IS_SHORT_SHIP = "is_short_ship"
COL_REASON_DSC = "REASON_DSC"
COL_LLM_COINCIDE = "llm_coincide_con_reason"
COL_LLM_CONFIANZA = "llm_confianza"
COL_VENDOR_NAME = "VENDOR_NAME"
COL_CARRIER_NAME = "CARRIER_PARTY_NAME"
COL_DC_NAME = "DC_LOC_NAME"
COL_DELAY_DAYS = "delay_days_calc"

COL_LLM_RAZONAMIENTO = "llm_razonamiento"
COL_LLM_HIPOTESIS = "llm_hipotesis"
COL_LLM_HIPOTESIS_EVIDENCIA = "llm_hipotesis_evidencia"
COL_LLM_ACCION_INMEDIATA = "llm_accion_inmediata"
COL_LLM_ACCION_CORRECTIVA = "llm_accion_correctiva"
COL_LLM_ACCION_PREVENTIVA = "llm_accion_preventiva"
COL_LLM_HIPOTESIS_ALT = "llm_hipotesis_alt"
COL_LLM_PASO_DISCRIMINANTE = "llm_paso_discriminante"
COL_LLM_CONFIANZA_HIPOTESIS = "llm_confianza_hipotesis"

# ── Etiquetas para mostrar en Telegram ─────────────────────────────────────
STAGE_LABELS = {
    "vendor": "Proveedor",
    "carrier": "Transportista",
    "dc": "Centro de Distribución",
    "indeterminado": "Sin responsable identificado",
}

SEVERITY_EMOJI = {
    "HIGH": "🔴",
    "MEDIUM": "🟠",
    "LOW": "🟢",
}

STAGE_EMOJI = {
    "vendor": "🏭",
    "carrier": "🚛",
    "dc": "🏬",
    "indeterminado": "❓",
}

STAGE_COLORS = {
    "vendor": "#0072B2",
    "carrier": "#E69F00",
    "dc": "#009E73",
    "indeterminado": "#767676",
}
