"""Carga y clasificación de datos en tiempo real.
Ejecuta el pipeline de Fase 1 (clean_po_data) y Fase 2 (classify_po_stages)
cada vez que se lanza la app, con caching de Streamlit para no repetirlo
en cada interacción del usuario.
"""
import sys
from pathlib import Path
import pandas as pd
import streamlit as st
from config import PHASE1_DIR, PHASE2_DIR, PO_RAW_CSV, LLM_OUT_CSV

# ── Añadir fases al path al nivel del módulo ────────────────────────────────
# Necesario para que Pylance resuelva los imports y para que los módulos
# de Fase 1 y Fase 2 sean importables desde cualquier parte de la app.
for _p in (PHASE1_DIR, PHASE2_DIR):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

# Fase 1
from pipeline_core import clean_po_data

# Fase 2
from classifier_core import classify_po_stages, load_rules_config


@st.cache_data(show_spinner="⏳ Ejecutando pipeline de clasificación...")
def load_classified_data() -> pd.DataFrame:
    """Carga el CSV crudo y ejecuta clean_po_data + classify_po_stages.

    Returns:
        DataFrame completo con todas las columnas de Fase 1 + Fase 2.
    """
    # 1. Cargar CSV crudo
    if not PO_RAW_CSV.exists():
        raise FileNotFoundError(
            f"No se encontró el CSV crudo en:\n{PO_RAW_CSV}\n\n"
            "Coloca el archivo 'po_root_cause_synthetic.csv' en data/raw/ "
            "o define PO_CSV_PATH en el .env."
        )

    df_raw = pd.read_csv(PO_RAW_CSV, low_memory=False)

    # 2. Limpiar (Fase 1)
    df_clean = clean_po_data(df_raw)

    # 3. Clasificar (Fase 2)
    rules = load_rules_config()
    df_classified = classify_po_stages(df_clean, rules)

    return df_classified


def get_tardios(df: pd.DataFrame) -> pd.DataFrame:
    """Filtra solo los POs tardíos (delay_days_calc > 0)."""
    return df[df["delay_days_calc"] > 0].copy()


def get_por_etapa(df: pd.DataFrame, etapa: str) -> pd.DataFrame:
    """Filtra por stage_primary."""
    return df[df["stage_primary"] == etapa].copy()


# ── Funciones para datos LLM ──────────────────────────────────────────────

def load_llm_data() -> pd.DataFrame:
    """Carga el CSV con análisis LLM desde data/processed/llm_out.csv."""
    if not LLM_OUT_CSV.exists():
        raise FileNotFoundError(
            f"No se encontró llm_out.csv en:\n{LLM_OUT_CSV}\n\n"
            "Asegúrate de tener el archivo en data/processed/"
        )
    
    df_llm = pd.read_csv(LLM_OUT_CSV, low_memory=False)
    
    # Validar columnas requeridas
    required_cols = [
        "PO_NBR",
        "llm_causa_raiz",
        "llm_accion_recomendada",
        "llm_severidad",
        "llm_coincide_con_reason",
        "llm_confianza",
    ]
    
    missing = [col for col in required_cols if col not in df_llm.columns]
    if missing:
        raise ValueError(f"Columnas faltantes en llm_out.csv: {missing}")
    
    return df_llm

# ── Funciones para datos LLM ──────────────────────────────────────────────

def load_llm_data() -> pd.DataFrame:
    """Carga el CSV con análisis LLM desde data/processed/llm_out.csv.
    
    Intenta varias codificaciones (utf-8, cp1252, latin-1) porque el archivo
    suele venir en Windows-1252 desde entornos en español.
    """
    if not LLM_OUT_CSV.exists():
        raise FileNotFoundError(
            f"No se encontró llm_out.csv en:\n{LLM_OUT_CSV}\n\n"
            "Asegúrate de tener el archivo en data/processed/"
        )
    
    # Lista de codificaciones a intentar, en orden de preferencia
    encodings_to_try = ["utf-8", "cp1252", "latin-1", "iso-8859-1"]
    
    df_llm = None
    last_error = None
    
    for enc in encodings_to_try:
        try:
            df_llm = pd.read_csv(LLM_OUT_CSV, low_memory=False, encoding=enc)
            # Si llegamos aquí, la lectura fue exitosa
            break
        except UnicodeDecodeError as e:
            last_error = e
            continue
    
    # Fallback: si ninguna codificación funcionó, leer reemplazando errores
    if df_llm is None:
        df_llm = pd.read_csv(
            LLM_OUT_CSV, 
            low_memory=False, 
            encoding="utf-8", 
            errors="replace"
        )
    
    # Validar columnas requeridas
    required_cols = [
        "PO_NBR",
        "llm_causa_raiz",
        "llm_accion_recomendada",
        "llm_severidad",
        "llm_coincide_con_reason",
        "llm_confianza",
    ]
    
    missing = [col for col in required_cols if col not in df_llm.columns]
    if missing:
        raise ValueError(f"Columnas faltantes en llm_out.csv: {missing}")
    
    return df_llm