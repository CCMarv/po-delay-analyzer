"""
test_handoff_contract.py — contrato dual del handoff (T4/T3, auditoría de cierre §3-A).

Verifica la "regla de oro" del contrato: el CSV de salida de una fase es IDÉNTICO al
DataFrame que esa fase deja en memoria, de modo que releerlo reconstruye el estado que
la fase siguiente cargaría si corriera la cadena monolítica.

Dos fronteras:
  - F1: clean_po_data() -> save_clean_output() -> releer  ==  df_clean en memoria.
  - F2: classify_po_stages() -> save_classified_output() -> releer  ==  df_classified.

Identidad FUNCIONAL, no de tipado: un CSV escribe las fechas como texto y al releerlas
sin parse quedan como str. El contrato se cumple si el DATO es el mismo valor; por eso el
test reparsea las columnas de fecha de ambos lados antes de comparar (el tipado exacto no
importa, el valor sí). El resto de columnas (números, booleanos, etiquetas) se comparan
directamente. Se usa el fixture sintético de conftest.py (valores conocidos).
"""
import sys
from pathlib import Path

import pandas as pd
import pandas.testing as pdt
import pytest

# pyproject.toml ya pone 01_/02_ en pythonpath; conftest.py los reinserta por si acaso.
from pipeline_core import clean_po_data, save_clean_output, _DATE_INPUT_COLUMNS
from classifier_core import classify_po_stages, save_classified_output

# Columnas de fecha del contrato de F1 (las que el round-trip debe reparsear para que
# texto(CSV) y datetime(memoria) sean comparables). Se toma la fuente de verdad del
# pipeline, no un heurístico de sufijo (DT_APPT_FIRST_APPROVED es fecha y no acaba en _DT).
_DATE_COLS = _DATE_INPUT_COLUMNS


def _normalizar(df: pd.DataFrame) -> pd.DataFrame:
    """Aplana las diferencias de TIPADO que un round-trip CSV introduce, dejando solo el
    VALOR para comparar (identidad funcional, no de dtype — decisión del contrato):
      - fechas: texto(CSV)↔datetime(memoria) → se reparsean a datetime ambos lados.
      - faltantes: <NA>(pandas) / NaN(numpy) / '' representan lo mismo ("no hay dato")
        pero assert_frame_equal los distingue → se unifican a un centinela común.
    """
    out = df.copy()
    for col in _DATE_COLS:
        if col in out.columns:
            out[col] = pd.to_datetime(out[col], errors="coerce")
    # Unificar todas las formas de "faltante" a un único centinela comparable.
    # Incluye el string vacío "": severity usa "" en memoria para los no-tardíos, pero
    # una celda vacía en CSV se relee como NaN. "" y NaN significan lo mismo ("sin valor")
    # → se folden al mismo centinela para comparar por VALOR, no por su representación.
    out = out.astype(object).where(out.notna(), other="<MISSING>")
    return out.replace("", "<MISSING>")


def _assert_funcionalmente_igual(en_memoria: pd.DataFrame, releido: pd.DataFrame) -> None:
    """El df releído del CSV es funcionalmente idéntico al de memoria: mismas columnas
    (nombres + orden), mismo nº de filas, y mismos valores (tras aplanar el tipado)."""
    # (a) Mismas columnas, en el mismo orden (el contrato persiste el df completo).
    assert list(releido.columns) == list(en_memoria.columns)
    # (b) Mismo nº de filas (persistir/leer no filtra ni inventa).
    assert len(releido) == len(en_memoria)
    # (c) Mismos valores tras normalizar tipado (fechas + faltantes). check_dtype=False:
    #     se exige igualdad de VALOR, no de dtype (lo que el contrato garantiza de un CSV).
    pdt.assert_frame_equal(
        _normalizar(releido).reset_index(drop=True),
        _normalizar(en_memoria).reset_index(drop=True),
        check_dtype=False,
        check_like=False,
    )


def test_handoff_f1_csv_identico_a_memoria(df_raw, tmp_path):
    # Frontera F1→F2: el CSV de clean_po_data reconstruye el df limpio en memoria.
    df_clean = clean_po_data(df_raw)
    out = save_clean_output(df_clean, path=tmp_path / "df_clean.csv")
    assert out.exists()
    releido = pd.read_csv(out, low_memory=False)
    _assert_funcionalmente_igual(df_clean, releido)


def test_handoff_f2_csv_identico_a_memoria(df_clean, tmp_path):
    # Frontera F2→F3: el CSV de classify_po_stages reconstruye el df clasificado.
    df_classified = classify_po_stages(df_clean)
    out = save_classified_output(df_classified, path=tmp_path / "df_classified.csv")
    assert out.exists()
    releido = pd.read_csv(out, low_memory=False)
    _assert_funcionalmente_igual(df_classified, releido)


def test_handoff_f2_persiste_todas_las_columnas(df_clean, tmp_path):
    # Parsimonia invertida del contrato: NO se recorta a un subconjunto curado. El CSV
    # trae TODAS las columnas del df clasificado (crudas + F1 + F2), no solo el veredicto.
    df_classified = classify_po_stages(df_clean)
    out = save_classified_output(df_classified, path=tmp_path / "df_classified.csv")
    releido = pd.read_csv(out, low_memory=False)
    assert set(releido.columns) == set(df_classified.columns)
    # Señales clave que el contrato debe arrastrar (consumo F3 + veredicto auditable).
    for col in ("stage_primary", "stage_multi", "severity", "delay_days_calc",
                "excess_vendor_hrs", "REASON_DSC"):
        assert col in releido.columns


def test_save_respeta_env_var(df_clean, tmp_path, monkeypatch):
    # La resolución de ruta respeta la env var (PO_OUTPUT_PATH) como documenta el contrato.
    destino = tmp_path / "via_env.csv"
    monkeypatch.setenv("PO_OUTPUT_PATH", str(destino))
    df_classified = classify_po_stages(df_clean)
    out = save_classified_output(df_classified)   # sin path explícito → usa la env var
    assert out == destino
    assert destino.exists()
