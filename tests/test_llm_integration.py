"""
test_llm_integration.py — pruebas PURAS de Fase 3 (T5 · C·H4).

Cubren las dos funciones de F3 que NO tocan la red: el armado del prompt (build_prompt)
y el parseo de la respuesta del LLM (_parse_llm_json). Los backends (Qwen/Claude/DeepSeek)
hacen llamadas HTTP y NO se prueban aquí (requieren red/credenciales); lo que se prueba es
la lógica determinística alrededor de esas llamadas, que es la que puede romperse en un
refactor sin que nadie se entere.

Qué NO se prueba y por qué:
  - backend.call() de cada backend: hace requests.post → necesita red. Fuera de alcance.
  - add_llm_explanations end-to-end: orquesta llamadas reales al LLM. Fuera de alcance.

llm_integration se importa gracias al pythonpath de pyproject.toml (03_llm_integration)
y al insert de red de seguridad de conftest.py.
"""
import pandas as pd

from llm_integration import build_prompt, _parse_llm_json


# ════════════════════════════════════════════════════════════════════════════
# A. build_prompt — armado del prompt desde una fila clasificada
# ════════════════════════════════════════════════════════════════════════════
def _row_ejemplo() -> pd.Series:
    """Fila mínima con los campos que build_prompt lee (de un PO clasificado)."""
    return pd.Series({
        "PO_NBR": "PO-TEST-1",
        "VENDOR_NAME": "ACME Corp",
        "DC_LOC_NAME": "DC-Guadalajara",
        "CARRIER_PARTY_NAME": "FastFreight",
        "STA_DT": "2024-01-05 00:00",
        "RECPT_DT": "2024-01-08 00:00",
        "APPROVED_DT": "2024-01-04 00:00",
        "TRAILER_ARRIVE_DT": "2024-01-06 00:00",
        "CHECKIN_DT": "2024-01-06 03:00",
        "CHECKOUT_DT": "2024-01-06 09:00",
        "delay_days_calc": 3.0,
        "yard_wait_calc_hrs": 3.0,
        "dock_calc_hrs": 6.0,
        "excess_carrier_hrs": 10.0,
        "excess_dc_hrs": 0.0,
        "stage_primary": "Carrier",
        "stage_multi": "Carrier",
        "HOT_PO_FLAG": 1,
        "_short_ship": False,
        "REASON_DSC": "Carrier delivery delay",
    })


def test_build_prompt_devuelve_str_no_vacio():
    out = build_prompt(_row_ejemplo())
    assert isinstance(out, str)
    assert len(out) > 0


def test_build_prompt_incluye_datos_de_la_po():
    # El prompt debe llevar la identidad y la clasificación de la PO al modelo.
    out = build_prompt(_row_ejemplo())
    assert "PO-TEST-1" in out
    assert "ACME Corp" in out
    assert "Carrier" in out                 # stage_primary
    assert "Carrier delivery delay" in out  # REASON_DSC


def test_build_prompt_hot_flag_se_traduce_a_si():
    # HOT_PO_FLAG=1 → "Sí" en el bloque de contexto (la lógica que build_prompt aplica).
    out = build_prompt(_row_ejemplo())
    assert "¿Es Hot PO (urgente)? Sí" in out


def test_build_prompt_tolera_campos_ausentes():
    # build_prompt usa row.get(..., default): una fila incompleta no debe reventar
    # (robustez: el prompt es texto, los faltantes caen a 'N/A'/0 sin KeyError).
    row = pd.Series({"PO_NBR": "PO-MIN"})
    out = build_prompt(row)
    assert isinstance(out, str)
    assert "PO-MIN" in out


def test_build_prompt_pide_json_estricto():
    # El prompt instruye responder SOLO con JSON (contrato de salida del LLM, H5).
    out = build_prompt(_row_ejemplo())
    assert "JSON" in out


# ════════════════════════════════════════════════════════════════════════════
# B. _parse_llm_json — extracción/normalización de la respuesta del LLM
# ════════════════════════════════════════════════════════════════════════════
def test_parse_json_limpio_en_espanol():
    raw = (
        '{"causa_raiz": "Retraso del transportista", '
        '"accion_recomendada": "Contactar al carrier", '
        '"severidad": "high", "coincide_con_reason_code": true, "confianza": 0.9}'
    )
    out = _parse_llm_json(raw, fallback=False)
    assert out is not None
    assert out["causa_raiz"] == "Retraso del transportista"
    assert out["severidad"] == "HIGH"          # se normaliza a mayúsculas
    assert out["coincide_con_reason_code"] is True
    assert out["confianza"] == 0.9


def test_parse_json_acepta_alias_en_ingles():
    # El parseo acepta llaves alternativas (root_cause/severity/...) y las normaliza.
    raw = (
        '{"root_cause": "Carrier issue", "recommended_action": "Call carrier", '
        '"severity": "medium", "matches_reason": false, "confidence": 0.4}'
    )
    out = _parse_llm_json(raw, fallback=False)
    assert out["causa_raiz"] == "Carrier issue"
    assert out["severidad"] == "MEDIUM"
    assert out["coincide_con_reason_code"] is False
    assert out["confianza"] == 0.4


def test_parse_json_extrae_de_texto_envolvente():
    # El modelo a veces envuelve el JSON en texto; el regex {…} debe extraerlo igual.
    raw = 'Aquí está el análisis:\n{"causa_raiz": "X", "severidad": "low"}\nFin.'
    out = _parse_llm_json(raw, fallback=False)
    assert out is not None
    assert out["causa_raiz"] == "X"
    assert out["severidad"] == "LOW"


def test_parse_json_malformado_sin_fallback_devuelve_none():
    # Sin JSON parseable y fallback=False (modo Claude/DeepSeek estricto) → None.
    out = _parse_llm_json("esto no es json", fallback=False)
    assert out is None


def test_parse_json_malformado_con_fallback_devuelve_dict_emergencia():
    # fallback=True (modo local, texto libre) → dict de emergencia, no None.
    out = _parse_llm_json("respuesta en texto libre sin json", fallback=True)
    assert out is not None
    assert out["severidad"] == "MEDIUM"
    assert out["confianza"] == 0.3            # marca de baja confianza del fallback


def test_parse_json_defaults_cuando_faltan_campos():
    # JSON válido pero incompleto: los campos ausentes caen a sus defaults documentados.
    out = _parse_llm_json('{"causa_raiz": "solo causa"}', fallback=False)
    assert out["causa_raiz"] == "solo causa"
    assert out["severidad"] == "MEDIUM"       # default
    assert out["coincide_con_reason_code"] is False
    assert out["confianza"] == 0.5            # default
