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
