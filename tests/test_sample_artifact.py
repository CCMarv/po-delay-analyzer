"""
test_sample_artifact.py — blinda la muestra versionada de la app (G1, T2/T3).

`data/samples/po_output_sample.csv` es el fallback que usa la app de Fase 4
(`04_app/services/data_service.py`) cuando no se corrió Fase 3 localmente y no
existe el artefacto real `data/processed/po_output.csv` (gitignored). Es un
recorte estratificado (stage × severity) del artefacto real, versionado en el
repo para que un clon fresco pueda abrir la app sin gastar API.

Qué blinda este test: que la muestra sigue el MISMO contrato F3→F4 que el
artefacto real (mismas columnas, mismo orden), que no hay filas duplicadas ni
vacías, y que conserva cobertura de al menos una fila por combinación
stage × severity que existía en la fuente al generarla — si alguien la
regenera mal o a mano, el test lo detecta.

El camino de fallback en sí (cuál archivo elige `load_po_output`, el warning
de Streamlit) se verifica en vivo con la app, no aquí: este test solo cubre la
forma del dato, no el código que lo consume.
"""
from pathlib import Path

import pandas as pd
import pytest

from llm_integration import _DELIVERABLE_COLUMNS, _MENTOR_COLUMNS

_SAMPLE_PATH = (
    Path(__file__).resolve().parent.parent / "data" / "samples" / "po_output_sample.csv"
)
_SEVERITY_DOMAIN = {"HIGH", "MEDIUM", "LOW"}

# Combinaciones stage × severity presentes en el artefacto real al generar la
# muestra (2026-07-18). Si el artefacto real cambia de forma sustancial, este
# test señala que la muestra quedó desalineada, no que algo esté roto.
_STRATA_ESPERADAS = {
    ("Carrier", "MEDIUM"), ("DC", "LOW"), ("DC", "MEDIUM"),
    ("Indeterminado", "HIGH"), ("Indeterminado", "LOW"), ("Indeterminado", "MEDIUM"),
    ("Vendor", "HIGH"), ("Vendor", "MEDIUM"),
}


@pytest.fixture(scope="module")
def df_sample() -> pd.DataFrame:
    assert _SAMPLE_PATH.exists(), f"Falta la muestra versionada en {_SAMPLE_PATH}"
    return pd.read_csv(_SAMPLE_PATH, low_memory=False)


def test_muestra_respeta_contrato_f3_columnas_y_orden(df_sample):
    assert list(df_sample.columns) == _DELIVERABLE_COLUMNS
    assert list(df_sample.columns[:5]) == _MENTOR_COLUMNS


def test_muestra_no_vacia(df_sample):
    assert len(df_sample) > 0


def test_muestra_po_nbr_unico(df_sample):
    assert df_sample["PO_NBR"].is_unique


def test_muestra_dominio_severity_valido(df_sample):
    assert set(df_sample["severity"].unique()) <= _SEVERITY_DOMAIN


def test_muestra_cobertura_stage_severity(df_sample):
    presentes = set(zip(df_sample["stage"], df_sample["severity"]))
    faltantes = _STRATA_ESPERADAS - presentes
    assert not faltantes, f"La muestra perdió cobertura de: {faltantes}"
