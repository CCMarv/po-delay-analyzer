"""Carga del artefacto F3->F4 (po_output.csv), compartida entre 04_app/ y
04_app/telegram_bot/. Antes de este modulo, la logica de encodings + fallback
a la muestra versionada + parseo de fechas estaba duplicada linea por linea
en 04_app/services/data_service.py y telegram_bot/services/data_service.py.

No impone Streamlit ni logging: quien llama decide como notificar el
fallback via `on_fallback`. Sin imports relativos a data_contract.py a
proposito: telegram_bot/config.py carga este archivo por ruta explicita
(importlib.util) para no tocar sys.path, y un import relativo fallaria fuera
de un paquete real - por eso DATE_COLUMNS entra como parametro con default.
"""
from pathlib import Path
from typing import Callable, Optional, Sequence

import pandas as pd

_ENCODINGS = ["utf-8", "cp1252", "latin-1", "iso-8859-1"]

_DEFAULT_DATE_COLUMNS = [
    "PO_DT", "STA_DT", "APPROVED_DT", "TRAILER_ARRIVE_DT",
    "CHECKIN_DT", "CHECKOUT_DT", "RECPT_DT",
]


def load_po_output_df(
    primary_path: Path,
    sample_path: Path,
    on_fallback: Optional[Callable[[Path], None]] = None,
    date_columns: Sequence[str] = _DEFAULT_DATE_COLUMNS,
) -> pd.DataFrame:
    """Carga el CSV de salida de Fase 3 (unico input de ambos canales).

    Si no existe el artefacto real, cae a la muestra versionada. Si tampoco
    existe la muestra, lanza un error accionable con las rutas esperadas y el
    comando para regenerar el artefacto completo.

    Args:
        primary_path: ruta al po_output.csv real (artefacto de handoff F3).
        sample_path: ruta a la muestra versionada de fallback.
        on_fallback: callback invocado con `sample_path` si se usa el
            fallback (p. ej. st.warning o logger.warning). No se llama si se
            usa el artefacto real.

    Returns:
        DataFrame con todas las columnas del contrato F3->F4.

    Raises:
        FileNotFoundError: si no existe ni el artefacto real ni la muestra.
    """
    if primary_path.exists():
        target = primary_path
    elif sample_path.exists():
        target = sample_path
        if on_fallback is not None:
            on_fallback(sample_path)
    else:
        raise FileNotFoundError(
            f"No se encontró po_output.csv en:\n{primary_path}\n"
            f"ni la muestra versionada en:\n{sample_path}\n\n"
            "El primero es el artefacto de handoff de Fase 3; la muestra "
            "viene en el repo y no debería faltar salvo que se haya borrado "
            "(restaurarla con: git checkout -- data/samples/po_output_sample.csv).\n\n"
            "Para generar el artefacto completo (gasta API):\n"
            "  cd 03_llm_integration\n"
            "  python llm_integration.py --mode full --backend openai\n"
            "Detalle en 03_llm_integration/README.md."
        )

    df = None
    for enc in _ENCODINGS:
        try:
            df = pd.read_csv(target, low_memory=False, encoding=enc)
            break
        except UnicodeDecodeError:
            continue

    if df is None:
        df = pd.read_csv(target, low_memory=False, encoding="utf-8", errors="replace")

    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    return df
