"""
Smoke test del esqueleto de Fase 2 — classifier_core (issue #43).

#43 es andamio: classifier_core.py todavía NO implementa reglas (la lógica entra en
#44/#45). Por eso este test es deliberadamente mínimo: verifica el CONTRATO del
esqueleto, no comportamiento de clasificación que aún no existe.

  1. El módulo importa y expone las dos piezas públicas (load_rules_config, classify_po_stages).
  2. rules_config.json carga sin error y trae las llaves de umbral que #44/#45 leerán.
  3. classify_po_stages() corre sobre el DataFrame de clean_po_data(), devuelve un
     DataFrame y NO pierde filas (igual que la limpieza: enriquece, no filtra).

El fixture df_clean (df sintético ya pasado por clean_po_data) viene de tests/conftest.py;
pytest lo carga solo. classifier_core se importa gracias al pythonpath de pyproject.toml
(y al insert de red de seguridad en conftest.py).
"""
import pandas as pd
import pytest

from conftest import row_for
from classifier_core import classify_po_stages, load_rules_config

# Llaves de umbral que el config semilla debe exponer (las que #44/#45 leerán por nombre).
EXPECTED_THRESHOLD_KEYS = {
    "yard_wait_hrs",
    "dock_hrs",
    "carrier_lag_hrs",
    "short_ship_fill_rate",
    "severity_delay_days",
}


# ════════════════════════════════════════════════════════════════════════════
# A. Carga de configuración
# ════════════════════════════════════════════════════════════════════════════
def test_load_rules_config_returns_dict():
    # El loader lee el JSON convencional (junto al módulo) sin error.
    rules = load_rules_config()
    assert isinstance(rules, dict)


def test_rules_config_has_expected_threshold_keys():
    # Contrato con #44/#45: los umbrales viven bajo rules["thresholds"][<nombre>] y
    # están las cinco llaves semilla. Si una cambia de nombre, el handoff se rompe y
    # conviene enterarse aquí.
    rules = load_rules_config()
    assert "thresholds" in rules
    assert EXPECTED_THRESHOLD_KEYS.issubset(rules["thresholds"].keys())


def test_each_threshold_has_value():
    # Cada umbral expone al menos un 'value' numérico (la metadata comparison/metric
    # es para #44; aquí solo aseguramos que el valor base está y es número).
    rules = load_rules_config()
    for key in EXPECTED_THRESHOLD_KEYS:
        assert isinstance(rules["thresholds"][key]["value"], (int, float))


# ════════════════════════════════════════════════════════════════════════════
# B. Función de clasificación (esqueleto)
# ════════════════════════════════════════════════════════════════════════════
def test_classify_runs_and_returns_dataframe(df_clean):
    # Corre sobre la salida de clean_po_data() y devuelve un DataFrame.
    out = classify_po_stages(df_clean)
    assert isinstance(out, pd.DataFrame)


def test_classify_preserves_rows(df_clean):
    # No pierde ni inventa filas: clasificar enriquece, no filtra (igual que limpiar).
    out = classify_po_stages(df_clean)
    assert len(out) == len(df_clean)


def test_classify_accepts_injected_rules(df_clean):
    # `rules` es inyectable: pasar un dict controlado evita leer el JSON y es el
    # mecanismo que #44/#45 usarán para testear reglas con umbrales a medida.
    rules = load_rules_config()
    out = classify_po_stages(df_clean, rules=rules)
    assert isinstance(out, pd.DataFrame)
    assert len(out) == len(df_clean)


def test_classify_does_not_mutate_input(df_clean):
    # Trabaja sobre una copia: el DataFrame de entrada no debe cambiar de forma.
    cols_before = list(df_clean.columns)
    _ = classify_po_stages(df_clean)
    assert list(df_clean.columns) == cols_before


# ════════════════════════════════════════════════════════════════════════════
# C. #44 — Flags desde *_calc y máscaras field-level
# ════════════════════════════════════════════════════════════════════════════
def test_flags_calc_columns_exist(df_clean):
    # El port añade las flags recalculadas desde timestamps (no las precalc del CSV).
    out = classify_po_stages(df_clean)
    for col in ("flag_carrier_calc", "flag_yard_calc", "flag_dock_calc",
                "_carrier_medible", "_dc_medible"):
        assert col in out.columns


def test_mascara_carrier_false_cuando_trailer_null(df_clean):
    # PO-NULLTRAILER no tiene hora de llegada → carrier NO es medible. La máscara lo
    # hace explícito (vs la flag, que quedaría silenciosamente False).
    out = classify_po_stages(df_clean)
    r = row_for(out, "PO-NULLTRAILER")
    assert r["_carrier_medible"] == False   # noqa: E712
    assert r["_dc_medible"] == False        # noqa: E712  (yard depende del arribo)


def test_mascara_medible_en_po_limpio(df_clean):
    # PO-CLEAN tiene todos los timestamps en orden → ambos tramos medibles.
    out = classify_po_stages(df_clean)
    r = row_for(out, "PO-CLEAN")
    assert r["_carrier_medible"] == True    # noqa: E712
    assert r["_dc_medible"] == True         # noqa: E712


# ════════════════════════════════════════════════════════════════════════════
# D. #45 — Etapa primaria por gap dominante (exceso sobre lo esperado)
# ════════════════════════════════════════════════════════════════════════════
def test_stage_primary_carrier_domina(df_clean):
    # PO-CARRIER-LATE: carrier_lag=14h (exc 11) supera el residual vendor (1) → Carrier.
    out = classify_po_stages(df_clean)
    r = row_for(out, "PO-CARRIER-LATE")
    assert r["stage_primary"] == "Carrier"
    # La magnitud del exceso queda expuesta (para severidad futura y validación).
    assert r["excess_carrier_hrs"] == pytest.approx(11.0)


def test_stage_primary_dc_domina(df_clean):
    # PO-DOCK-LATE: dock=10h (exc 7.5) supera el residual vendor (4.5) → DC.
    out = classify_po_stages(df_clean)
    r = row_for(out, "PO-DOCK-LATE")
    assert r["stage_primary"] == "DC"
    assert r["excess_dc_hrs"] == pytest.approx(7.5)


def test_stage_primary_on_time_si_no_tardio(df_clean):
    # PO-CLEAN llega a tiempo (delay_days_calc=0) → no recibe etapa de retraso.
    out = classify_po_stages(df_clean)
    assert row_for(out, "PO-CLEAN")["stage_primary"] == "On-Time"


def test_indeterminado_intercepta_a_vendor(df_clean):
    # PO-NULLTRAILER es TARDÍO pero ni carrier ni DC son medibles. Por el residual
    # crudo todo el delay caería en vendor; la regla de Indeterminado lo intercepta
    # ANTES del argmax: no se le endosa a vendor por descarte ciego.
    out = classify_po_stages(df_clean)
    r = row_for(out, "PO-NULLTRAILER")
    assert r["delay_days_calc"] > 0          # es tardío
    assert r["stage_primary"] == "Indeterminado"
    assert r["stage_primary"] != "Vendor"    # el punto del diseño


def test_universo_tardios_sin_clase_es_cero(df_clean):
    # Contrato de la métrica del mentor: todo tardío (delay_days_calc>0) recibe una
    # clase primaria de retraso; ninguno se queda como 'On-Time'.
    out = classify_po_stages(df_clean)
    tardios = out[out["delay_days_calc"] > 0]
    assert (tardios["stage_primary"] == "On-Time").sum() == 0


# ════════════════════════════════════════════════════════════════════════════
# E. Capa complementaria — multi-causa, reason_group_manual, modificadores
# ════════════════════════════════════════════════════════════════════════════
def test_reason_group_manual_mapea_reason_dsc(df_clean):
    # REASON_DSC del staff se mapea a grupo de responsable (para mismatch #47 futuro).
    out = classify_po_stages(df_clean)
    assert row_for(out, "PO-CARRIER-LATE")["reason_group_manual"] == "Carrier"
    assert row_for(out, "PO-DOCK-LATE")["reason_group_manual"] == "DC"


def test_modificador_rescheduled_cuando_primary_no_vendor(df_clean):
    # PO-RESCHED tiene _rescheduled=True. Reschedule es MODIFICADOR, no etapa: si el
    # primario no es Vendor, aparece como sufijo narrativo, no cambia stage_primary.
    out = classify_po_stages(df_clean)
    r = row_for(out, "PO-RESCHED")
    if r["stage_primary"] != "Vendor":
        assert "vendor_rescheduled" in r["stage_modifiers"]


def test_columnas_complementarias_existen(df_clean):
    out = classify_po_stages(df_clean)
    for col in ("stage_multi", "reason_group_manual", "stage_modifiers"):
        assert col in out.columns
