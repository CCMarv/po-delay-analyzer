"""Contrato de datos F3->F4 compartido entre 04_app/ (Streamlit) y
04_app/telegram_bot/ (comandos fijos, ARD-20).

Fuente unica de rutas y columnas canonicas de po_output.csv (ARD-21). Antes de
este modulo, 04_app/config.py y telegram_bot/config.py mantenian dos copias
manuales que ya habian divergido (a telegram_bot le faltaban las columnas de
exceso por etapa). No incluye nada de sistema de diseno Streamlit-only
(paleta oscura, Plotly, CONFIDENCE_BUCKETS) ni nada Telegram-only
(TELEGRAM_*, DEMO_MODE, STAGE_LABELS/emoji) - cada lado conserva eso aparte.
"""
from pathlib import Path


def data_processed_dir(repo_root: Path) -> Path:
    return repo_root / "data" / "processed"


def po_output_csv(repo_root: Path) -> Path:
    return data_processed_dir(repo_root) / "po_output.csv"


def po_output_sample_csv(repo_root: Path) -> Path:
    return repo_root / "data" / "samples" / "po_output_sample.csv"


def scorecards_dir(repo_root: Path) -> Path:
    return data_processed_dir(repo_root) / "scorecards"


# -- Columnas canonicas del contrato F3->F4 ---------------------------------
COL_PO = "PO_NBR"
COL_STAGE = "stage"
COL_SEVERITY = "severity"
COL_EXPLANATION = "explanation"
COL_ACTION = "action"

# -- Columnas del timeline (lifecycle del PO) -------------------------------
COL_PO_DT = "PO_DT"
COL_STA_DT = "STA_DT"
COL_APPROVED_DT = "APPROVED_DT"
COL_TRAILER_ARRIVE_DT = "TRAILER_ARRIVE_DT"
COL_CHECKIN_DT = "CHECKIN_DT"
COL_CHECKOUT_DT = "CHECKOUT_DT"
COL_RECPT_DT = "RECPT_DT"

DATE_COLUMNS = [
    COL_PO_DT, COL_STA_DT, COL_APPROVED_DT, COL_TRAILER_ARRIVE_DT,
    COL_CHECKIN_DT, COL_CHECKOUT_DT, COL_RECPT_DT,
]

# -- Columnas de validacion y flags -----------------------------------------
COL_HOT_PO_FLAG = "HOT_PO_FLAG"
COL_IS_SHORT_SHIP = "is_short_ship"
COL_REASON_DSC = "REASON_DSC"
COL_LLM_COINCIDE = "llm_coincide_con_reason"

# -- Columnas de enriquecimiento tier 1 (contrato F3->F4, #158/#167) --------
COL_LLM_CONFIANZA = "llm_confianza"
COL_VENDOR_NAME = "VENDOR_NAME"
COL_CARRIER_NAME = "CARRIER_PARTY_NAME"
COL_DC_NAME = "DC_LOC_NAME"
COL_DELAY_DAYS = "delay_days_calc"
COL_EXCESS_VENDOR_HRS = "excess_vendor_hrs"
COL_EXCESS_CARRIER_HRS = "excess_carrier_hrs"
COL_EXCESS_DC_HRS = "excess_dc_hrs"

# -- Columnas del diagnostico diferencial tier 2 (contrato F3->F4, #161/#175) -
# Salida hibrida de ARD-16: razonamiento + hipotesis principal/alternativa +
# el paso que las discrimina + plan escalonado + una 2a confianza especifica
# de la hipotesis (distinta de COL_LLM_CONFIANZA, que es la del tier 1).
COL_LLM_RAZONAMIENTO = "llm_razonamiento"
COL_LLM_HIPOTESIS = "llm_hipotesis"
COL_LLM_HIPOTESIS_EVIDENCIA = "llm_hipotesis_evidencia"
COL_LLM_ACCION_INMEDIATA = "llm_accion_inmediata"
COL_LLM_ACCION_CORRECTIVA = "llm_accion_correctiva"
COL_LLM_ACCION_PREVENTIVA = "llm_accion_preventiva"
COL_LLM_HIPOTESIS_ALT = "llm_hipotesis_alt"
COL_LLM_PASO_DISCRIMINANTE = "llm_paso_discriminante"
COL_LLM_CONFIANZA_HIPOTESIS = "llm_confianza_hipotesis"

# Etapa -> timestamps que delimitan su tramo de responsabilidad en el
# lifecycle (ver 02_clasif_reglas_negocio/classifier_core.py - Vendor: STA
# push; Carrier: transito; DC: yard+dock consolidados). Indeterminado no
# tiene tramo propio.
STAGE_SEGMENT_COLUMNS = {
    "vendor": (COL_STA_DT, COL_APPROVED_DT),
    "carrier": (COL_APPROVED_DT, COL_TRAILER_ARRIVE_DT),
    "dc": (COL_TRAILER_ARRIVE_DT, COL_CHECKIN_DT, COL_CHECKOUT_DT),
}

# Etapa -> columna de exceso de horas de ESA etapa unicamente (tier 1,
# ARD-21). "Indeterminado" queda fuera a proposito: no tiene tramo propio
# (ARD-22 S7 D4).
STAGE_EXCESS_COLUMN = {
    "vendor": COL_EXCESS_VENDOR_HRS,
    "carrier": COL_EXCESS_CARRIER_HRS,
    "dc": COL_EXCESS_DC_HRS,
}

# -- Paleta base por etapa (Okabe-Ito, ARD-17) ------------------------------
# Comun a Streamlit (tema claro) y al bot; el tema oscuro es Streamlit-only y
# vive en 04_app/config.py.
# Carrier corregido de #E69F00 a #B88000 (nota de cierre ARD-17, 2026-07-22):
# el original no alcanzaba 3:1 (WCAG 2.1 SS1.4.11) contra --surface-elevated.
STAGE_COLORS = {
    "vendor": "#0072B2",         # Blue
    "carrier": "#B88000",        # Orange (oscurecido para 3:1, ARD-17)
    "dc": "#009E73",             # Bluish Green
    "indeterminado": "#767676",  # Gris neutro
}

# -- Paleta de severidad/confianza (rampa acromatica, ARD-17) ---------------
# Comun a Streamlit y al bot, mismo motivo que STAGE_COLORS. Baja/Baja
# corregido de #A8A8A8 a #8A8A8A (nota de cierre ARD-17, 2026-07-22): el
# original no alcanzaba 3:1 contra --surface-elevated.
SEVERITY_COLORS = {
    "alta": "#3D3D3D",
    "media": "#6B6B6B",
    "baja": "#8A8A8A",
}


def dataset_cutoff_date(df):
    """Fecha de corte real del artefacto: maximo timestamp entre las 7
    columnas del lifecycle, tras dropna (ARD-22 S7 T3). Devuelve None si el
    df no trae ninguna fecha valida (guarda para df vacio o columnas
    ausentes)."""
    import pandas as pd

    present = [c for c in DATE_COLUMNS if c in df.columns]
    if not present:
        return None
    max_ts = pd.to_datetime(df[present].stack(), errors="coerce").max()
    return None if pd.isna(max_ts) else max_ts
