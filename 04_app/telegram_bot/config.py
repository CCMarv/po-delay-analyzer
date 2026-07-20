"""Configuración del bot de Telegram — Fase 4.

Lee variables de entorno desde .env (mismo archivo que el resto de Fase 4).
"""
import importlib.util
import os
from pathlib import Path

# ── Token del bot ───────────────────────────────────────────────────────────
# Cargar desde .env en la raíz del repo
from dotenv import load_dotenv

# telegram_bot/ -> 04_app/ -> raíz del repo (tres .parent, no dos: este archivo
# vive un nivel más adentro que 04_app/config.py).
_TELEGRAM_BOT_DIR = Path(__file__).resolve().parent
_APP_DIR = _TELEGRAM_BOT_DIR.parent
_REPO_ROOT = _APP_DIR.parent
_DOTENV_PATH = _REPO_ROOT / ".env"
if _DOTENV_PATH.exists():
    load_dotenv(_DOTENV_PATH)


def _cargar_modulo_shared(nombre_archivo: str):
    """Carga un módulo de shared/ por ruta de archivo explícita, sin tocar
    sys.path. 04_app/ no está en pythonpath cuando corre el bot (CI aísla
    PYTHONPATH a 04_app/telegram_bot precisamente para que `config`/`services`
    no colisionen con sus tocayos de 04_app/) — insertar 04_app/ al sys.path
    aquí reabriría esa colisión. importlib.util evita el problema por
    completo: no requiere que el paquete padre sea importable."""
    ruta = _APP_DIR / "shared" / nombre_archivo
    spec = importlib.util.spec_from_file_location(f"_telegram_bot_shared_{ruta.stem}", ruta)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


_dc = _cargar_modulo_shared("data_contract.py")
load_po_output_df = _cargar_modulo_shared("data_loader.py").load_po_output_df
COL_PO = _dc.COL_PO
COL_STAGE = _dc.COL_STAGE
COL_SEVERITY = _dc.COL_SEVERITY
COL_EXPLANATION = _dc.COL_EXPLANATION
COL_ACTION = _dc.COL_ACTION
COL_PO_DT = _dc.COL_PO_DT
COL_STA_DT = _dc.COL_STA_DT
COL_APPROVED_DT = _dc.COL_APPROVED_DT
COL_TRAILER_ARRIVE_DT = _dc.COL_TRAILER_ARRIVE_DT
COL_CHECKIN_DT = _dc.COL_CHECKIN_DT
COL_CHECKOUT_DT = _dc.COL_CHECKOUT_DT
COL_RECPT_DT = _dc.COL_RECPT_DT
COL_HOT_PO_FLAG = _dc.COL_HOT_PO_FLAG
COL_IS_SHORT_SHIP = _dc.COL_IS_SHORT_SHIP
COL_REASON_DSC = _dc.COL_REASON_DSC
COL_LLM_COINCIDE = _dc.COL_LLM_COINCIDE
COL_LLM_CONFIANZA = _dc.COL_LLM_CONFIANZA
COL_VENDOR_NAME = _dc.COL_VENDOR_NAME
COL_CARRIER_NAME = _dc.COL_CARRIER_NAME
COL_DC_NAME = _dc.COL_DC_NAME
COL_DELAY_DAYS = _dc.COL_DELAY_DAYS
COL_EXCESS_VENDOR_HRS = _dc.COL_EXCESS_VENDOR_HRS
COL_EXCESS_CARRIER_HRS = _dc.COL_EXCESS_CARRIER_HRS
COL_EXCESS_DC_HRS = _dc.COL_EXCESS_DC_HRS
COL_LLM_RAZONAMIENTO = _dc.COL_LLM_RAZONAMIENTO
COL_LLM_HIPOTESIS = _dc.COL_LLM_HIPOTESIS
COL_LLM_HIPOTESIS_EVIDENCIA = _dc.COL_LLM_HIPOTESIS_EVIDENCIA
COL_LLM_ACCION_INMEDIATA = _dc.COL_LLM_ACCION_INMEDIATA
COL_LLM_ACCION_CORRECTIVA = _dc.COL_LLM_ACCION_CORRECTIVA
COL_LLM_ACCION_PREVENTIVA = _dc.COL_LLM_ACCION_PREVENTIVA
COL_LLM_HIPOTESIS_ALT = _dc.COL_LLM_HIPOTESIS_ALT
COL_LLM_PASO_DISCRIMINANTE = _dc.COL_LLM_PASO_DISCRIMINANTE
COL_LLM_CONFIANZA_HIPOTESIS = _dc.COL_LLM_CONFIANZA_HIPOTESIS
STAGE_SEGMENT_COLUMNS = _dc.STAGE_SEGMENT_COLUMNS
STAGE_EXCESS_COLUMN = _dc.STAGE_EXCESS_COLUMN
STAGE_COLORS = _dc.STAGE_COLORS
data_processed_dir = _dc.data_processed_dir
po_output_csv = _dc.po_output_csv
po_output_sample_csv = _dc.po_output_sample_csv
scorecards_dir = _dc.scorecards_dir
dataset_cutoff_date = _dc.dataset_cutoff_date

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
if not TELEGRAM_BOT_TOKEN:
    print("⚠️  TELEGRAM_BOT_TOKEN no definido en .env. El bot no arrancará.")

# ── Whitelist de usuarios autorizados ───────────────────────────────────────
# IDs de Telegram separados por comas. Fail-closed: si está vacía, NADIE puede
# usar el bot (arranca, pero rechaza a todos los comandos); solo los IDs
# listados aquí quedan autorizados.
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

# ── Modo demo (bypass de autorización) ──────────────────────────────────────
# Si está activo, is_authorized() acepta cualquier user_id sin necesidad de
# whitelist — pensado para demos/presentación, NO para producción. Ver
# services/auth.py::is_authorized y ARD-20 (modelo fail-closed).
DEMO_MODE = os.getenv("DEMO_MODE", "").strip().lower() in ("1", "true", "yes")

# ── Rutas de datos (reusando la misma estructura que Fase 4) ────────────────
REPO_ROOT = _REPO_ROOT
DATA_PROCESSED_DIR = data_processed_dir(REPO_ROOT)
PO_OUTPUT_CSV = po_output_csv(REPO_ROOT)
PO_OUTPUT_SAMPLE_CSV = po_output_sample_csv(REPO_ROOT)
SCORECARDS_DIR = scorecards_dir(REPO_ROOT)

# ── Etiquetas para mostrar en Telegram (distintas de STAGE_DISPLAY de
# 04_app/config.py: nombres largos en español + emoji, no Title case) ──────
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
