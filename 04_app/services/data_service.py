"""Carga de datos desde el artefacto de handoff F3→F4.

La app consume exclusivamente po_output.csv (producido por Fase 3).
No se ejecuta el pipeline de Fase 1 ni Fase 2 en tiempo real.
"""
import pandas as pd
import streamlit as st
from config import PO_OUTPUT_CSV, COL_PO, COL_STAGE, COL_SEVERITY


@st.cache_data(show_spinner=" Cargando datos del artefacto F3→F4...")
def load_po_output() -> pd.DataFrame:
    """Carga el CSV de salida de Fase 3 (único input de la app).
    
    Returns:
        DataFrame con todas las columnas del contrato F3→F4.
    
    Raises:
        FileNotFoundError: Si no existe po_output.csv en data/processed/
    """
    if not PO_OUTPUT_CSV.exists():
        raise FileNotFoundError(
            f"No se encontró po_output.csv en:\n{PO_OUTPUT_CSV}\n\n"
            "Este archivo es el artefacto de handoff de Fase 3.\n"
            "Ejecuta el pipeline de Fase 3 para generarlo."
        )
    
    # Intentar múltiples codificaciones (Windows-1252 es común en español)
    encodings_to_try = ["utf-8", "cp1252", "latin-1", "iso-8859-1"]
    
    df = None
    for enc in encodings_to_try:
        try:
            df = pd.read_csv(PO_OUTPUT_CSV, low_memory=False, encoding=enc)
            break
        except UnicodeDecodeError:
            continue
    
    # Fallback: leer reemplazando errores
    if df is None:
        df = pd.read_csv(
            PO_OUTPUT_CSV,
            low_memory=False,
            encoding="utf-8",
            errors="replace"
        )
    
    # Parsear columnas de fecha para el timeline
    date_cols = [
        "PO_DT", "STA_DT", "APPROVED_DT", "TRAILER_ARRIVE_DT",
        "CHECKIN_DT", "CHECKOUT_DT", "RECPT_DT"
    ]
    
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    
    return df


def get_po_by_number(df: pd.DataFrame, po_nbr: int) -> pd.Series:
    """Obtiene un PO específico por número."""
    result = df[df[COL_PO] == po_nbr]
    if result.empty:
        raise ValueError(f"PO {po_nbr} no encontrado en el artefacto")
    return result.iloc[0]


def get_unique_po_list(df: pd.DataFrame) -> list:
    """Retorna lista ordenada de POs únicos para el selector."""
    return sorted(df[COL_PO].unique().tolist())