"""Carga de datos desde el artefacto de handoff F3→F4.

La app consume exclusivamente po_output.csv (producido por Fase 3).
No se ejecuta el pipeline de Fase 1 ni Fase 2 en tiempo real.
"""
import pandas as pd
import streamlit as st
from config import PO_OUTPUT_CSV, PO_OUTPUT_SAMPLE_CSV, COL_PO, COL_STAGE, COL_SEVERITY


@st.cache_data(show_spinner=" Cargando datos del artefacto F3→F4...")
def load_po_output() -> pd.DataFrame:
    """Carga el CSV de salida de Fase 3 (único input de la app).

    Si no existe el artefacto real (no se corrió Fase 3 localmente), cae a la
    muestra versionada en data/samples/ para que la app abra igual, con una
    advertencia visible de que las cifras no son las canónicas del entregable.

    Returns:
        DataFrame con todas las columnas del contrato F3→F4.

    Raises:
        FileNotFoundError: Si no existe ni po_output.csv ni la muestra versionada.
    """
    if PO_OUTPUT_CSV.exists():
        target = PO_OUTPUT_CSV
    elif PO_OUTPUT_SAMPLE_CSV.exists():
        target = PO_OUTPUT_SAMPLE_CSV
        st.warning(
            f" Mostrando la muestra versionada ({target.name}, "
            "no el artefacto completo). Las cifras agregadas no son las "
            "canónicas del entregable. El artefacto completo se genera "
            "corriendo la Fase 3 — ver 03_llm_integration/README.md."
        )
    else:
        raise FileNotFoundError(
            f"No se encontró po_output.csv en:\n{PO_OUTPUT_CSV}\n"
            f"ni la muestra versionada en:\n{PO_OUTPUT_SAMPLE_CSV}\n\n"
            "El primero es el artefacto de handoff de Fase 3; la muestra "
            "viene en el repo y no debería faltar salvo que se haya borrado "
            "(restaurarla con: git checkout -- data/samples/po_output_sample.csv).\n\n"
            "Para generar el artefacto completo (gasta API):\n"
            "  cd 03_llm_integration\n"
            "  python llm_integration.py --mode full --backend openai\n"
            "Detalle en 03_llm_integration/README.md."
        )

    # Intentar múltiples codificaciones (Windows-1252 es común en español)
    encodings_to_try = ["utf-8", "cp1252", "latin-1", "iso-8859-1"]

    df = None
    for enc in encodings_to_try:
        try:
            df = pd.read_csv(target, low_memory=False, encoding=enc)
            break
        except UnicodeDecodeError:
            continue

    # Fallback: leer reemplazando errores
    if df is None:
        df = pd.read_csv(
            target,
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