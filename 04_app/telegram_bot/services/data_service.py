"""Carga de datos desde el artefacto F3→F4 — reutilizado por el bot.

Misma lógica que 04_app/services/data_service.py pero sin dependencia de
Streamlit ni st.cache_data. Usa caché en memoria (dict con un DataFrame).
"""
import json
from pathlib import Path
from typing import Optional

import pandas as pd

from config import PO_OUTPUT_CSV, SCORECARDS_DIR, COL_PO

# ── Caché en memoria ───────────────────────────────────────────────────────
_cache: dict = {}


def load_po_output(force_reload: bool = False) -> pd.DataFrame:
    """Carga el CSV de salida de Fase 3.

    Args:
        force_reload: Si True, ignora la caché y recarga del disco.

    Returns:
        DataFrame con todas las columnas del contrato F3→F4.
    """
    if not force_reload and "df" in _cache:
        return _cache["df"]

    if not PO_OUTPUT_CSV.exists():
        raise FileNotFoundError(
            f"No se encontró po_output.csv en:\n{PO_OUTPUT_CSV}\n\n"
            "Ejecuta el pipeline de Fase 3 para generarlo."
        )

    # Intentar múltiples codificaciones
    encodings = ["utf-8", "cp1252", "latin-1", "iso-8859-1"]
    df = None
    for enc in encodings:
        try:
            df = pd.read_csv(PO_OUTPUT_CSV, low_memory=False, encoding=enc)
            break
        except UnicodeDecodeError:
            continue

    if df is None:
        df = pd.read_csv(PO_OUTPUT_CSV, low_memory=False, encoding="utf-8", errors="replace")

    # Parsear fechas
    date_cols = [
        "PO_DT", "STA_DT", "APPROVED_DT", "TRAILER_ARRIVE_DT",
        "CHECKIN_DT", "CHECKOUT_DT", "RECPT_DT",
    ]
    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    _cache["df"] = df
    return df


def get_po_by_number(df: pd.DataFrame, po_nbr: int) -> pd.Series:
    """Obtiene un PO específico por número."""
    result = df[df[COL_PO] == po_nbr]
    if result.empty:
        raise ValueError(f"PO {po_nbr} no encontrado en el artefacto")
    return result.iloc[0]


def get_unique_po_list(df: pd.DataFrame) -> list:
    """Retorna lista ordenada de POs únicos."""
    return sorted(df[COL_PO].unique().tolist())


def load_scorecards() -> Optional[dict]:
    """Carga los 3 JSON de scorecards del motor offline.

    Returns:
        Dict con keys 'vendors', 'carriers', 'dcs', o None si falta algún archivo.
    """
    actors = ("vendors", "carriers", "dcs")
    result = {}
    for actor_key in actors:
        path = SCORECARDS_DIR / f"reporte_{actor_key}.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            # Los JSON tienen la estructura: {"vendors": { ... }}
            data = json.load(f)
            result[actor_key] = data.get(actor_key, {})
    return result


def _safe(val, fmt: str = "str") -> str:
    """Valor seguro para mostrar: si es NaN/None, devuelve 'N/A'."""
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "N/A"
    if fmt == "date":
        return val.strftime("%Y-%m-%d %H:%M") if hasattr(val, "strftime") else str(val)
    return str(val)
