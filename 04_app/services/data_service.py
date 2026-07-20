"""Carga de datos desde el artefacto de handoff F3→F4.

La app consume exclusivamente po_output.csv (producido por Fase 3).
No se ejecuta el pipeline de Fase 1 ni Fase 2 en tiempo real.
"""
import pandas as pd
import streamlit as st
from config import PO_OUTPUT_CSV, PO_OUTPUT_SAMPLE_CSV, COL_PO, COL_STAGE, COL_SEVERITY
from shared.data_loader import load_po_output_df


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
    def _avisar_fallback(sample_path):
        st.warning(
            f" Mostrando la muestra versionada ({sample_path.name}, "
            "no el artefacto completo). Las cifras agregadas no son las "
            "canónicas del entregable. El artefacto completo se genera "
            "corriendo la Fase 3 — ver 03_llm_integration/README.md."
        )

    return load_po_output_df(PO_OUTPUT_CSV, PO_OUTPUT_SAMPLE_CSV, on_fallback=_avisar_fallback)


def get_po_by_number(df: pd.DataFrame, po_nbr: int) -> pd.Series:
    """Obtiene un PO específico por número."""
    result = df[df[COL_PO] == po_nbr]
    if result.empty:
        raise ValueError(f"PO {po_nbr} no encontrado en el artefacto")
    return result.iloc[0]


def get_unique_po_list(df: pd.DataFrame) -> list:
    """Retorna lista ordenada de POs únicos para el selector."""
    return sorted(df[COL_PO].unique().tolist())