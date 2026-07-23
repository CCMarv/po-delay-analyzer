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

# Llaves de umbral que el config debe exponer (las que #44/#45/#48 leen por nombre).
EXPECTED_THRESHOLD_KEYS = {
    "vendor_gap_hrs",
    "yard_wait_hrs",
    "dock_hrs",
    "carrier_lag_hrs",
    "short_ship_fill_rate",
    "severity_delay_days",
    "severity_low_days",
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
# D. #45 — Etapa primaria: STA push (vendor) + exceso sobre umbral del mentor
# ════════════════════════════════════════════════════════════════════════════
def test_stage_primary_carrier_domina(df_clean):
    # PO-CARRIER-LATE: carrier_lag=14h sobre umbral 8h → exc 6h. APPROVED<STA → push 0.
    # carrier (6) supera a yard/dock (0) y vendor (0) → Carrier. El ganador NO cambió
    # respecto al config viejo; solo la MAGNITUD (presupuesto 3 → umbral 8).
    out = classify_po_stages(df_clean)
    r = row_for(out, "PO-CARRIER-LATE")
    assert r["stage_primary"] == "Carrier"
    assert r["excess_carrier_hrs"] == pytest.approx(6.0)


def test_stage_primary_dc_domina(df_clean):
    # PO-DOCK-LATE: dock=10h sobre umbral 6h → exc 4h. yard 1h (exc 0). exc_dc=4.
    # APPROVED<STA → push 0 → gana DC. Magnitud recalculada (7.5 → 4.0).
    out = classify_po_stages(df_clean)
    r = row_for(out, "PO-DOCK-LATE")
    assert r["stage_primary"] == "DC"
    assert r["excess_dc_hrs"] == pytest.approx(4.0)


def test_stage_primary_vendor_domina(df_clean):
    # PO-VENDOR-LATE: APPROVED(01-06) > STA(01-04) → STA push 48h; carrier/yard/dock
    # bajo umbral (exc 0). El vendor por señal directa domina → Vendor. Es el caso que
    # el método residual NO distinguía bien y que la decisión del mentor habilita.
    # Con vendor_gap_hrs=24 (consulta 06-17), el EXCESO es push − umbral = 48 − 24 = 24h
    # (el push de 48h supera el umbral, así que sigue siendo Vendor).
    out = classify_po_stages(df_clean)
    r = row_for(out, "PO-VENDOR-LATE")
    assert r["stage_primary"] == "Vendor"
    assert r["excess_vendor_hrs"] == pytest.approx(24.0)


def test_excess_yard_dock_expuestos(df_clean):
    # #48/#46 necesitan el desglose yard vs dock (no solo el agregado DC). PO-DOCK-LATE:
    # yard 1h bajo umbral 4h → exc 0; dock 10h sobre umbral 6h → exc 4.
    out = classify_po_stages(df_clean)
    for col in ("excess_yard_hrs", "excess_dock_hrs"):
        assert col in out.columns
    r = row_for(out, "PO-DOCK-LATE")
    assert r["excess_yard_hrs"] == pytest.approx(0.0)
    assert r["excess_dock_hrs"] == pytest.approx(4.0)


def test_dc_substage_dock_cuando_dock_domina(df_clean):
    # Subclase del DC: PO-DOCK-LATE tiene exc_dock(4) > exc_yard(0) → 'Dock'.
    # Y dc_substage solo se llena cuando el primario es DC (None en otros casos).
    out = classify_po_stages(df_clean)
    assert row_for(out, "PO-DOCK-LATE")["dc_substage"] == "Dock"
    # Un caso NO-DC no debe tener subclase.
    assert pd.isna(row_for(out, "PO-CARRIER-LATE")["dc_substage"])


def test_stage_primary_on_time_si_no_tardio(df_clean):
    # PO-CLEAN llega a tiempo (delay_days_calc=0) → no recibe etapa de retraso.
    out = classify_po_stages(df_clean)
    assert row_for(out, "PO-CLEAN")["stage_primary"] == "On-Time"


def test_indeterminado_intercepta_a_vendor(df_clean):
    # PO-NULLTRAILER es TARDÍO pero ni carrier ni DC son medibles. Con APPROVED=STA
    # (push 0) no hay señal de vendor tampoco → Indeterminado, no vendor por descarte.
    # Sin tramos medibles → subclase 'sin_datos' (no 'sin_causa_dominante').
    out = classify_po_stages(df_clean)
    r = row_for(out, "PO-NULLTRAILER")
    assert r["delay_days_calc"] > 0          # es tardío
    assert r["stage_primary"] == "Indeterminado"
    assert r["stage_primary"] != "Vendor"    # el punto del diseño
    assert r["indeterminado_substage"] == "sin_datos"


def test_vendor_domina_sin_trailer_si_hay_exceso(df_clean):
    # Nota de cierre ARD-03b (2026-07-22): PO-NULLTRAILER-VENDOR no tiene tráiler
    # (carrier/DC no medibles) PERO su push de vendor (72h) supera el umbral de 24h
    # (exc=48h). excess_vendor_hrs NO depende de TRAILER_ARRIVE_DT, así que el gate
    # `decidible` debe reconocerlo como decidible por vendor y no mandarlo a
    # Indeterminado por descarte — el bug que la auditoría encontró.
    out = classify_po_stages(df_clean)
    r = row_for(out, "PO-NULLTRAILER-VENDOR")
    assert r["delay_days_calc"] > 0
    assert r["excess_vendor_hrs"] == pytest.approx(48.0)
    assert r["stage_primary"] == "Vendor"
    assert pd.isna(r["indeterminado_substage"])


def test_indeterminado_sin_causa_dominante(df_clean):
    # PO-HOT-HIGH es TARDÍO y DECIDIBLE (tramos medibles) pero ningún tramo supera su
    # umbral: carrier 2h/yard 3h/dock 4h bajo 8/4/6, y APPROVED<STA (push 0, < 24h).
    # Datos completos pero sin causa dominante → subclase 'sin_causa_dominante' (la rama
    # que la consulta 06-17 separó de 'sin_datos'). Antes habría caído en vendor por default.
    out = classify_po_stages(df_clean)
    r = row_for(out, "PO-HOT-HIGH")
    assert r["delay_days_calc"] > 0
    assert r["stage_primary"] == "Indeterminado"
    assert r["indeterminado_substage"] == "sin_causa_dominante"


def test_indeterminado_substage_na_si_no_indeterminado(df_clean):
    # Espejo de dc_substage: la subclase solo se llena cuando el primario es Indeterminado.
    # Un caso Vendor/Carrier/DC no debe traerla.
    out = classify_po_stages(df_clean)
    assert pd.isna(row_for(out, "PO-VENDOR-LATE")["indeterminado_substage"])


def test_universo_tardios_sin_clase_es_cero(df_clean):
    # Contrato de la métrica del mentor: todo tardío (delay_days_calc>0) recibe una
    # clase primaria de retraso; ninguno se queda como 'On-Time'. Debe seguir verde
    # tras quitar la "Rama 2" (el efecto se conserva en la intercepción del argmax).
    out = classify_po_stages(df_clean)
    tardios = out[out["delay_days_calc"] > 0]
    assert (tardios["stage_primary"] == "On-Time").sum() == 0


# ════════════════════════════════════════════════════════════════════════════
# E. Capa complementaria — multi-causa, reason_group_manual, flags de contexto
# ════════════════════════════════════════════════════════════════════════════
def test_reason_group_manual_mapea_reason_dsc(df_clean):
    # REASON_DSC del staff se mapea a grupo de responsable (para mismatch #47 futuro).
    out = classify_po_stages(df_clean)
    assert row_for(out, "PO-CARRIER-LATE")["reason_group_manual"] == "Carrier"
    assert row_for(out, "PO-DOCK-LATE")["reason_group_manual"] == "DC"


def test_is_rescheduled_es_flag_de_contexto(df_clean):
    # Decisión del mentor: rescheduled es contexto (un evento), no señal de vendor.
    # Se expone SIEMPRE como flag propia, reflejando _rescheduled del pipeline.
    out = classify_po_stages(df_clean)
    assert bool(row_for(out, "PO-RESCHED")["is_rescheduled"]) is True
    assert bool(row_for(out, "PO-CLEAN")["is_rescheduled"]) is False


def test_stage_multi_no_incluye_reschedule(df_clean):
    # PO-RESCHED reprograma la cita pero NO tiene STA push (APPROVED<STA) ni exceso de
    # tramo → su stage_multi NO debe contener 'Vendor' por el reschedule (el mentor lo
    # sacó de la señal de etapa). On-time y sin causa → 'Ninguno' (centinela que sobrevive
    # el round-trip CSV; ver T4: el literal 'None' colisionaba con los nulos de pandas).
    out = classify_po_stages(df_clean)
    r = row_for(out, "PO-RESCHED")
    assert "Vendor" not in r["stage_multi"]
    assert r["stage_multi"] == "Ninguno"


def test_stage_multi_vendor_respeta_umbral_24h(df_clean):
    # T7 (coherencia interna, VERIF-2): stage_multi mide el MISMO concepto que stage_primary.
    # PO-VENDOR-SUBUMBRAL tiene STA push positivo de 12h, BAJO el umbral de 24h → no es
    # exceso atribuible → excess_vendor_hrs=0 y stage_multi NO debe contener 'Vendor'.
    # Con la señal vieja (appt_lead_days<0) sí lo habría puesto: ese es el caso que el
    # doble umbral introducía y que T7 elimina. Sin exceso en ningún tramo → 'Ninguno'.
    out = classify_po_stages(df_clean)
    r = row_for(out, "PO-VENDOR-SUBUMBRAL")
    assert r["delay_days_calc"] > 0                 # es tardío
    assert r["excess_vendor_hrs"] == pytest.approx(0.0)   # push 12h - 24h, clip 0
    assert "Vendor" not in r["stage_multi"]         # el punto de T7
    assert r["stage_multi"] == "Ninguno"            # centinela sin-causa (no 'None')


def test_columnas_contexto_existen(df_clean):
    out = classify_po_stages(df_clean)
    for col in ("stage_multi", "reason_group_manual",
                "is_rescheduled", "is_short_ship", "is_short_lead"):
        assert col in out.columns


# ════════════════════════════════════════════════════════════════════════════
# F. #48 — Severidad determinística (HIGH/MEDIUM/LOW) + agravantes
# ════════════════════════════════════════════════════════════════════════════
def test_severity_high_para_hot_con_delay_fuerte(df_clean):
    # PO-HOT-HIGH: HOT_PO_FLAG=1, IS_LATE=Y, delay=4d (>3) → gate HIGH del mentor.
    out = classify_po_stages(df_clean)
    assert row_for(out, "PO-HOT-HIGH")["severity"] == "HIGH"


def test_severity_medium_para_tardio_normal(df_clean):
    # PO-VENDOR-LATE: delay=3d, no es hot, sin agravantes (lead largo, fill 100%) →
    # MEDIUM (tardío normal, ni borderline ni gate HIGH).
    out = classify_po_stages(df_clean)
    assert row_for(out, "PO-VENDOR-LATE")["severity"] == "MEDIUM"


def test_severity_low_para_borderline(df_clean):
    # PO-CARRIER-LATE: delay=0.5d (<1) → borderline = LOW. No tiene agravantes
    # (lead 4d largo, fill 100%), así que no sube de nivel.
    out = classify_po_stages(df_clean)
    assert row_for(out, "PO-CARRIER-LATE")["severity"] == "LOW"


def test_severity_vacia_para_on_time(df_clean):
    # PO-CLEAN no es tardío → severity vacía (no entra al ranking de #48).
    out = classify_po_stages(df_clean)
    assert row_for(out, "PO-CLEAN")["severity"] == ""


def test_severity_columna_existe_y_valores_validos(df_clean):
    out = classify_po_stages(df_clean)
    assert "severity" in out.columns
    assert set(out["severity"].unique()).issubset({"HIGH", "MEDIUM", "LOW", ""})
