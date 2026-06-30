"""
test_eval_diversity.py — pruebas del analizador OFFLINE de diversidad (eval_diversity.py).

Cubren la lógica determinística pura: la métrica de diversidad (1 − Jaccard media por
pares), el conteo de acciones distintas y el parser que localiza las columnas de la tabla
del fixture POR NOMBRE de encabezado. No tocan red, API ni los fixtures reales (la tabla
de prueba va embebida en un string).

`eval_diversity` se importa gracias al pythonpath de pyproject.toml (03_llm_integration)
y al insert de red de seguridad de conftest.py — igual que el resto de la suite.
"""
import math

import pytest

from eval_diversity import (
    tokenize,
    jaccard,
    mean_pairwise_similarity,
    diversity,
    count_distinct,
    parse_fixture_text,
    analyze_rows,
)


# ════════════════════════════════════════════════════════════════════════════
# A. Métrica de diversidad
# ════════════════════════════════════════════════════════════════════════════
def test_acciones_identicas_diversidad_cero():
    # Dos acciones idénticas → Jaccard 1.0 → diversidad 1 − 1 = 0.0.
    acciones = ["Solicitar al proveedor un plan", "Solicitar al proveedor un plan"]
    assert diversity(acciones) == 0.0


def test_acciones_disjuntas_diversidad_uno():
    # Tokens totalmente disjuntos → Jaccard 0.0 → diversidad 1 − 0 = 1.0.
    acciones = ["abrir reclamo carrier", "revisar muelle distribucion"]
    assert diversity(acciones) == 1.0


def test_tres_acciones_promedio_por_pares_a_mano():
    # Jaccard calculada a mano sobre 3 acciones (conjuntos de tokens):
    #   A = {a, b}
    #   B = {a, c}      → J(A,B) = |{a}| / |{a,b,c}| = 1/3
    #   C = {a, b, c}   → J(A,C) = |{a,b}| / |{a,b,c}| = 2/3
    #                     J(B,C) = |{a,c}| / |{a,b,c}| = 2/3
    # similitud media = (1/3 + 2/3 + 2/3) / 3 = (5/3)/3 = 5/9
    # diversidad = 1 − 5/9 = 4/9
    acciones = ["a b", "a c", "a b c"]
    sim = mean_pairwise_similarity(acciones)
    assert math.isclose(sim, 5 / 9, rel_tol=1e-9)
    assert math.isclose(diversity(acciones), 4 / 9, rel_tol=1e-9)


def test_jaccard_y_tokenize_basicos():
    # tokenize: minúsculas, corta por no-alfanuméricos, sin vacíos.
    assert tokenize("Abrir, reclamo!") == {"abrir", "reclamo"}
    # jaccard de conjuntos con solape parcial.
    assert jaccard({"a", "b"}, {"b", "c"}) == 1 / 3


# ════════════════════════════════════════════════════════════════════════════
# B. Casos borde
# ════════════════════════════════════════════════════════════════════════════
def test_subconjunto_menor_a_dos_es_na_sin_excepcion():
    # <2 acciones → no hay parejas → diversidad indefinida (None), sin reventar.
    assert diversity([]) is None
    assert diversity(["una sola accion"]) is None
    assert mean_pairwise_similarity(["una sola accion"]) is None


# ════════════════════════════════════════════════════════════════════════════
# C. Conteo de distintas (normalización ligera)
# ════════════════════════════════════════════════════════════════════════════
def test_count_distinct_normaliza_ligero():
    # Difieren solo en mayúsculas, espacios colapsables y puntuación de borde →
    # cuentan como UNA sola distinta.
    acciones = [
        "Solicitar plan al proveedor.",
        "solicitar  plan al proveedor",
        "  Solicitar plan al proveedor  ",
    ]
    assert count_distinct(acciones) == 1
    # Una variante con puntuación INTERNA distinta sí es otra.
    assert count_distinct(["plan, firme", "plan firme"]) == 2


# ════════════════════════════════════════════════════════════════════════════
# D. Parser por nombre de encabezado
# ════════════════════════════════════════════════════════════════════════════
# Tabla de prueba: columnas en orden NO trivial para probar que el parser las
# localiza por nombre, no por posición. Incluye una celda con pipe escapado '\|'.
_TABLA_MD = """\
# Encabezado de prueba

Texto introductorio que no es tabla.

| PO | acción LLM | etapa | delay (d) |
|---|---|---|--:|
| 1 | Solicitar al proveedor SYNCO un plan | Vendor | 5.6 |
| 2 | Solicitar al proveedor SYNCO un plan | Vendor | 4.0 |
| 3 | Abrir reclamo con el carrier (ruta A \\| B) | Carrier | 1.2 |

## Resultado
- texto de cierre que no es tabla.
"""


def test_parser_localiza_columnas_por_encabezado():
    rows = parse_fixture_text(_TABLA_MD)
    # Tres filas de datos (la separadora '---' y las secciones de texto se ignoran).
    assert len(rows) == 3
    # Localizó 'acción LLM' y 'etapa' pese al orden y a la columna 'PO' intercalada.
    assert rows[0] == {"etapa": "Vendor", "accion": "Solicitar al proveedor SYNCO un plan"}
    # El pipe escapado '\|' se des-escapa a '|' dentro de la celda, no parte la fila.
    assert rows[2]["etapa"] == "Carrier"
    assert rows[2]["accion"] == "Abrir reclamo con el carrier (ruta A | B)"


def test_parser_sin_columnas_requeridas_falla():
    # Una tabla sin las columnas necesarias debe avisar (no devolver vacío en silencio).
    tabla = "| PO | otra |\n|---|---|\n| 1 | x |\n"
    with pytest.raises(ValueError):
        parse_fixture_text(tabla)


def test_analyze_rows_filtra_vendor_por_etapa_verdadera():
    rows = parse_fixture_text(_TABLA_MD)
    m = analyze_rows(rows)
    assert m["n_all"] == 3
    assert m["n_vendor"] == 2          # solo las dos filas con etapa 'Vendor'
    # Las dos acciones Vendor son idénticas → diversidad Vendor 0.0 y 1 distinta.
    assert m["div_vendor"] == 0.0
    assert m["distinct_vendor"] == 1
