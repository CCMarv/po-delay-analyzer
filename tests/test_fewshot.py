"""
test_fewshot.py — pruebas del pool auditado y su selección estática (#99 / ADR-12).

Cubren la lógica determinística de `fewshot.py`: que el pool versionado carga, que la
selección estática es reproducible y diversa por etapa, y que cada ejemplo trae lo que
`_format_example` necesita. No tocan red ni API.
"""
import json

import pytest

from fewshot import load_pool, select_examples


def test_pool_carga_y_no_esta_vacio():
    pool = load_pool()
    assert isinstance(pool, list) and len(pool) >= 3


def test_cada_ejemplo_tiene_meta_y_salida_ideal():
    # Contrato del pool: metadatos de auditoría + las 5 claves de salida ideal.
    for ej in load_pool():
        assert "_meta" in ej
        assert ej["_meta"].get("auditado") is True
        assert "po_origen" in ej["_meta"]
        for clave in ("causa_raiz", "accion_recomendada", "severidad",
                      "coincide_con_reason_code", "confianza"):
            assert clave in ej, f"falta {clave} en ejemplo {ej['_meta']['po_origen']}"


def test_pool_disjunto_no_aplica_aqui_pero_meta_trazable():
    # Cada ejemplo declara su PO origen (trazabilidad para auditar disjunción con #94).
    origenes = [e["_meta"]["po_origen"] for e in load_pool()]
    assert len(origenes) == len(set(origenes)), "PO origen duplicado en el pool"


def test_select_examples_es_reproducible():
    # Misma llamada → mismo conjunto (orden determinista por po_origen).
    assert select_examples(2) == select_examples(2)


def test_select_examples_respeta_n():
    assert len(select_examples(1)) == 1
    assert len(select_examples(3)) == 3


def test_select_examples_diversidad_por_etapa():
    # C3: una etapa distinta cada uno, en el orden pedido.
    ej = select_examples(3, stages=["DC", "Vendor", "Carrier"])
    etapas = [e["stage_primary"] for e in ej]
    assert etapas == ["DC", "Vendor", "Carrier"]


def test_select_examples_pide_de_mas_lanza():
    # Pedir más de lo que el pool/criterio aporta es un error explícito, no silencioso.
    with pytest.raises(ValueError):
        select_examples(99)


def test_select_examples_acepta_pool_inyectado():
    # Para tests/uso programático: se puede pasar un pool propio.
    pool = [
        {"_meta": {"po_origen": 1}, "stage_primary": "DC"},
        {"_meta": {"po_origen": 2}, "stage_primary": "Vendor"},
    ]
    out = select_examples(1, pool=pool)
    assert out[0]["_meta"]["po_origen"] == 1  # menor po_origen primero
