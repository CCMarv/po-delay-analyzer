"""
Tests de metrics_core (Fase 2) — validación del clasificador (#46, #47).

metrics_core son funciones PURAS sobre el DataFrame ya clasificado: smoke (contrato:
devuelven el tipo correcto, no mutan) + casos conocidos sobre el fixture sintético, cuyos
escenarios tienen respuesta calculable a mano.

Sobre el fixture (ver conftest.py): los POs con REASON_DSC (CARRIER/DOCK/VENDOR-LATE) están
bien anotados a propósito → agreement 100% y 0 mismatches. Para ejercitar select_mismatches
con un caso positivo se inyecta un mismatch en un DataFrame mínimo dentro del propio test
(no se contamina el fixture compartido).
"""
import pandas as pd

from conftest import row_for
from classifier_core import classify_po_stages
import metrics_core as mc


# ════════════════════════════════════════════════════════════════════════════
# A. Smoke / contrato
# ════════════════════════════════════════════════════════════════════════════
def test_gap_dominante_devuelve_series(df_clean):
    out = classify_po_stages(df_clean)
    dom = mc.gap_dominante(out)
    assert isinstance(dom, pd.Series)
    assert len(dom) == len(out)


def test_gap_dominante_valores_validos(df_clean):
    # Solo etiquetas de etapa o NA (cuando ningún tramo es medible).
    out = classify_po_stages(df_clean)
    dom = mc.gap_dominante(out)
    valores = set(dom.dropna().unique())
    assert valores.issubset({"Vendor", "Carrier", "DC"})


def test_stage_accuracy_devuelve_dict_con_llaves(df_clean):
    out = classify_po_stages(df_clean)
    res = mc.stage_accuracy(out)
    for k in ("accuracy", "threshold", "passes", "n_tardios",
              "n_confiables", "n_evaluables", "matriz"):
        assert k in res


def test_reason_agreement_devuelve_dict_con_llaves(df_clean):
    out = classify_po_stages(df_clean)
    res = mc.reason_agreement(out)
    for k in ("agreement", "n_tardios", "n_clasificable", "n_mismatches", "matriz"):
        assert k in res


# ════════════════════════════════════════════════════════════════════════════
# B. #46 — Gap dominante coincide con stage_primary en casos conocidos
# ════════════════════════════════════════════════════════════════════════════
def test_gap_dominante_vendor_en_sta_push(df_clean):
    # PO-VENDOR-LATE: STA push de días → el tramo STA→APPROVED es el más largo → Vendor.
    out = classify_po_stages(df_clean)
    dom = mc.gap_dominante(out)
    idx = out.index[out["PO_NBR"] == "PO-VENDOR-LATE"][0]
    assert dom[idx] == "Vendor"


def test_gap_dominante_carrier_en_carrier_late(df_clean):
    # PO-CARRIER-LATE: APPROVED→ARRIVE de 14h es el tramo más largo → Carrier.
    out = classify_po_stages(df_clean)
    dom = mc.gap_dominante(out)
    idx = out.index[out["PO_NBR"] == "PO-CARRIER-LATE"][0]
    assert dom[idx] == "Carrier"


def test_stage_accuracy_fixture_perfecto(df_clean):
    # Los 4 evaluables del fixture (PO-TS-STA, CARRIER/DOCK/VENDOR-LATE) tienen el gap
    # dominante alineado con stage_primary → accuracy 1.0 y pasa el umbral >80%.
    out = classify_po_stages(df_clean)
    res = mc.stage_accuracy(out)
    assert res["n_evaluables"] == 4
    assert res["accuracy"] == 1.0
    assert res["passes"] is True


def test_stage_accuracy_indeterminado_fuera_del_denominador(df_clean):
    # PO-NULLTRAILER y PO-HOT-HIGH son tardíos pero Indeterminado → NO cuentan como
    # evaluables (el gap dominante no puede juzgarlos / su stage no es decidible).
    out = classify_po_stages(df_clean)
    res = mc.stage_accuracy(out)
    assert res["n_tardios"] > res["n_evaluables"]   # hay tardíos no evaluables


# ════════════════════════════════════════════════════════════════════════════
# C. #47 — Reason agreement y selección de mismatches
# ════════════════════════════════════════════════════════════════════════════
def test_reason_agreement_fixture_perfecto(df_clean):
    # Los 3 POs con REASON_DSC están bien anotados → agreement 1.0, sin mismatches.
    out = classify_po_stages(df_clean)
    res = mc.reason_agreement(out)
    assert res["n_clasificable"] == 3
    assert res["agreement"] == 1.0
    assert res["n_mismatches"] == 0


def test_select_mismatches_vacio_sin_mismatches(df_clean):
    # Sin mismatches en el fixture → DataFrame vacío (no None, no error).
    out = classify_po_stages(df_clean)
    ms = mc.select_mismatches(out)
    assert isinstance(ms, pd.DataFrame)
    assert len(ms) == 0


def test_select_mismatches_detecta_y_ordena(df_clean):
    # Inyectamos DOS mismatches en una copia: el cómputo (stage_primary) discrepa del
    # humano (reason_group_manual). select_mismatches debe devolverlos ordenados por la
    # fuerza de señal (exceso de la etapa elegida por el cómputo), el más fuerte primero.
    out = classify_po_stages(df_clean).copy()
    # PO-CARRIER-LATE: cómputo Carrier (exc 6h) ; forzamos que el humano dijo "DC".
    i_carrier = out.index[out["PO_NBR"] == "PO-CARRIER-LATE"][0]
    out.loc[i_carrier, "reason_group_manual"] = "DC"
    # PO-VENDOR-LATE: cómputo Vendor (exc 48h, señal mayor) ; humano dijo "Carrier".
    i_vendor = out.index[out["PO_NBR"] == "PO-VENDOR-LATE"][0]
    out.loc[i_vendor, "reason_group_manual"] = "Carrier"

    ms = mc.select_mismatches(out, n=8)
    pos = list(ms["PO_NBR"])
    assert "PO-CARRIER-LATE" in pos
    assert "PO-VENDOR-LATE" in pos
    # El de mayor señal (Vendor, 48h) va antes que el de menor (Carrier, 6h).
    assert pos.index("PO-VENDOR-LATE") < pos.index("PO-CARRIER-LATE")


def test_select_mismatches_respeta_n(df_clean):
    out = classify_po_stages(df_clean).copy()
    # Inyectar 3 mismatches y pedir solo 2.
    for po, reason in (("PO-CARRIER-LATE", "DC"),
                       ("PO-DOCK-LATE", "Vendor"),
                       ("PO-VENDOR-LATE", "Carrier")):
        i = out.index[out["PO_NBR"] == po][0]
        out.loc[i, "reason_group_manual"] = reason
    ms = mc.select_mismatches(out, n=2)
    assert len(ms) == 2


def test_select_mismatches_stratify_cubre_etapas(df_clean):
    # stratify=True con n=3 y un mismatch por etapa → uno de cada etapa (no solo el fuerte).
    out = classify_po_stages(df_clean).copy()
    for po, reason in (("PO-VENDOR-LATE", "Carrier"),   # cómputo Vendor (señal alta)
                       ("PO-CARRIER-LATE", "DC"),       # cómputo Carrier
                       ("PO-DOCK-LATE", "Vendor")):     # cómputo DC
        i = out.index[out["PO_NBR"] == po][0]
        out.loc[i, "reason_group_manual"] = reason
    ms = mc.select_mismatches(out, n=3, stratify=True)
    assert set(ms["stage_primary"]) == {"Vendor", "Carrier", "DC"}


def test_select_mismatches_stratify_no_cambia_default(df_clean):
    # Con un único mismatch, estratificar o no da el mismo resultado (no rompe el default).
    out = classify_po_stages(df_clean).copy()
    i = out.index[out["PO_NBR"] == "PO-VENDOR-LATE"][0]
    out.loc[i, "reason_group_manual"] = "Carrier"
    plano = mc.select_mismatches(out, n=8)
    estrat = mc.select_mismatches(out, n=8, stratify=True)
    assert list(plano["PO_NBR"]) == list(estrat["PO_NBR"])
