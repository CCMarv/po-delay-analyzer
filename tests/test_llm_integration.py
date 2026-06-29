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
import pytest

import llm_integration
from llm_integration import (
    build_prompt,
    _parse_llm_json,
    prepare_classified_df,
    save_llm_output,
    export_deliverable_csv,
    _DELIVERABLE_COLUMNS,
    _MENTOR_COLUMNS,
)


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
        "is_rescheduled": True,
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


def test_build_prompt_prohibe_calcular():
    # Lineamiento del mentor (#91): el modelo INTERPRETA, no calcula. El prompt debe
    # instruir explícitamente que no recalcule/invente y que cite las cifras dadas.
    out = build_prompt(_row_ejemplo())
    assert "INTERPRETAR" in out
    assert "No recalcules" in out or "no recalcules" in out
    assert "no inventes" in out.lower()


def test_build_prompt_incluye_rescheduled_como_contexto():
    # #67: is_rescheduled se cablea como CONTEXTO neutro (Sí/No), no como etapa ni
    # agravante. El fixture tiene is_rescheduled=True → debe verse "Sí".
    out = build_prompt(_row_ejemplo())
    assert "¿Se reprogramó la cita de entrega? Sí" in out


def test_build_prompt_rescheduled_ausente_cae_a_no():
    # Sin la columna, row.get(..., False) → "No" (robustez, no rompe).
    row = pd.Series({"PO_NBR": "PO-MIN"})
    out = build_prompt(row)
    assert "¿Se reprogramó la cita de entrega? No" in out


def test_build_prompt_pide_estructura_de_explicacion():
    # La explicación (causa_raiz) debe pedir 2-3 oraciones con los elementos del mentor:
    # etapa exacta, delay citado, coincidencia con REASON_DSC y agravantes.
    out = build_prompt(_row_ejemplo())
    assert "2-3 oraciones" in out
    assert "etapa exacta" in out
    # la acción debe exigir responsable, no genérica
    assert "responsable" in out


# ── few-shot (#99): el parámetro examples y la curación del ejemplo ───────────
def _ejemplo_dc() -> dict:
    """Ejemplo few-shot mínimo de etapa DC (mismatch: reason culpa al vendor)."""
    return {
        "stage_primary": "DC",
        "delay_days_calc": 0.19,
        "excess_dc_hrs": 4.6,
        "DC_LOC_NAME": "DC-GDL",
        "REASON_DSC": "Vendor delayed shipment",
        "causa_raiz": "La etapa exacta es DC, retraso de 0.19 días; no coincide con el reason.",
        "accion_recomendada": "El equipo del DC-GDL debe revisar el exceso de descarga medido.",
        "severidad": "MEDIUM",
        "coincide_con_reason_code": False,
        "confianza": 0.8,
    }


def test_build_prompt_zero_shot_por_defecto_sin_ejemplos():
    # Sin examples → comportamiento histórico: NO se antepone el bloque de ejemplos.
    out = build_prompt(_row_ejemplo())
    assert "EJEMPLOS DE RAZONAMIENTO" not in out


def test_build_prompt_examples_vacios_equivale_a_zero_shot():
    # Lista vacía es falsy → mismo prompt que zero-shot (no rompe el default).
    assert build_prompt(_row_ejemplo(), examples=[]) == build_prompt(_row_ejemplo())


def test_build_prompt_few_shot_antepone_bloque_antes_de_instrucciones():
    # El bloque de ejemplos va ANTES de INSTRUCCIONES (las reglas se leen al final).
    out = build_prompt(_row_ejemplo(), examples=[_ejemplo_dc()])
    assert "EJEMPLOS DE RAZONAMIENTO" in out
    assert "ANÁLISIS CORRECTO" in out
    assert out.index("EJEMPLOS DE RAZONAMIENTO") < out.index("INSTRUCCIONES:")


def test_build_prompt_ejemplo_nombra_responsable_y_senal():
    # El ejemplo muestra el responsable de la etapa y la señal de exceso que la justifica.
    out = build_prompt(_row_ejemplo(), examples=[_ejemplo_dc()])
    bloque = out[out.index("EJEMPLOS"):out.index("INSTRUCCIONES:")]
    assert "Centro de distribución: DC-GDL" in bloque
    assert "Exceso del centro de distribución: 4.6 horas" in bloque


def test_build_prompt_ejemplo_excluye_timeline():
    # Curación #99/D2.1: el ejemplo NO trae el timeline de fechas (contra #91).
    out = build_prompt(_row_ejemplo(), examples=[_ejemplo_dc()])
    bloque = out[out.index("EJEMPLOS"):out.index("INSTRUCCIONES:")]
    assert "TIMELINE" not in bloque
    assert "Fecha prometida" not in bloque


def test_build_prompt_ejemplo_json_ideal_con_5_claves():
    # El JSON ideal del ejemplo lleva las 5 claves (refuerza que deben existir siempre).
    out = build_prompt(_row_ejemplo(), examples=[_ejemplo_dc()])
    bloque = out[out.index("EJEMPLOS"):out.index("INSTRUCCIONES:")]
    for clave in ("causa_raiz", "accion_recomendada", "severidad",
                  "coincide_con_reason_code", "confianza"):
        assert clave in bloque


def test_build_prompt_indeterminado_substage_aparece_cuando_activo():
    # #135: la sub-categoría se muestra SOLO cuando stage=INDETERMINADO y el campo existe.
    row = _row_ejemplo()
    row["stage_primary"] = "INDETERMINADO"
    row["indeterminado_substage"] = "sin_datos"
    out = build_prompt(row)
    assert "Sub-categoría INDETERMINADO: sin_datos" in out


def test_build_prompt_indeterminado_substage_no_aparece_en_otras_etapas():
    # #135: para Carrier/Vendor/DC el campo no debe aparecer aunque esté en la fila.
    row = _row_ejemplo()   # stage_primary = "Carrier" por defecto
    row["indeterminado_substage"] = "sin_datos"
    out = build_prompt(row)
    assert "Sub-categoría INDETERMINADO" not in out


def test_build_prompt_indeterminado_sin_substage_no_agrega_linea():
    # #135: etapa INDETERMINADO pero campo vacío → no se agrega la línea.
    row = _row_ejemplo()
    row["stage_primary"] = "INDETERMINADO"
    row["indeterminado_substage"] = ""
    out = build_prompt(row)
    assert "Sub-categoría INDETERMINADO" not in out


def test_build_prompt_ejemplo_rescheduled_solo_si_activo():
    # is_rescheduled aparece en el ejemplo SOLO cuando está activo (decisión caso a caso).
    sin = build_prompt(_row_ejemplo(), examples=[_ejemplo_dc()])
    bloque_sin = sin[sin.index("EJEMPLOS"):sin.index("INSTRUCCIONES:")]
    assert "¿Se reprogramó la cita de entrega?" not in bloque_sin

    ej = _ejemplo_dc()
    ej["is_rescheduled"] = True
    con = build_prompt(_row_ejemplo(), examples=[ej])
    bloque_con = con[con.index("EJEMPLOS"):con.index("INSTRUCCIONES:")]
    assert "¿Se reprogramó la cita de entrega? Sí" in bloque_con


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


# ════════════════════════════════════════════════════════════════════════════
# C. Orquestación separada del CLI (#90) — sin red
# ════════════════════════════════════════════════════════════════════════════
# Verifican que la lógica que se sacó de main() es invocable como API y que su
# comportamiento (lectura del handoff, persistencia) no depende del CLI.

def test_prepare_classified_df_lee_handoff_csv(tmp_path):
    # Rama from_csv=True: prepare_classified_df relee el CSV de F2 tal cual, sin
    # recomputar. Se inyecta repo_root al tmp para no tocar data/processed real.
    # El CSV de F2 real trae las 13 columnas de fecha (que se reparsean al leer);
    # el fixture las incluye para reflejar el artefacto real, no uno recortado.
    from pipeline_core import _DATE_INPUT_COLUMNS

    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    df_in = pd.DataFrame({
        "PO_NBR": ["PO-A", "PO-B"],
        "stage_primary": ["Carrier", "Vendor"],
        "delay_days_calc": [2.0, 5.0],
    })
    for col in _DATE_INPUT_COLUMNS:
        df_in[col] = ["2024-01-05 00:00", "2024-01-06 00:00"]
    df_in.to_csv(processed / "df_classified.csv", index=False)

    out = prepare_classified_df(from_csv=True, repo_root=tmp_path)

    assert list(out["PO_NBR"]) == ["PO-A", "PO-B"]
    assert list(out["stage_primary"]) == ["Carrier", "Vendor"]
    # Las columnas de fecha quedan reparseadas a datetime (no strings).
    assert pd.api.types.is_datetime64_any_dtype(out["PO_DT"])


def test_prepare_classified_df_sin_crudo_lanza_filenotfound(tmp_path):
    # from_csv=False (recomputar) pero el CSV crudo no existe en el repo_root
    # inyectado → FileNotFoundError explícito (lo que main() traduce a exit 1).
    with pytest.raises(FileNotFoundError):
        prepare_classified_df(from_csv=False, repo_root=tmp_path)


def test_save_llm_output_roundtrip(tmp_path):
    # save_llm_output persiste el DataFrame completo y se relee idéntico (contrato
    # interno df_with_llm_*.csv). Sin red, sin CLI.
    out_path = tmp_path / "df_with_llm_test.csv"
    df = pd.DataFrame({
        "PO_NBR": ["PO-1", "PO-2"],
        "llm_causa_raiz": ["causa uno", "causa dos"],
        "llm_severidad": ["HIGH", "LOW"],
    })
    save_llm_output(df, out_path)

    assert out_path.exists()
    releido = pd.read_csv(out_path)
    pd.testing.assert_frame_equal(releido, df)


def test_add_llm_explanations_es_api_sin_cli():
    # La integración LLM se importa y referencia como función pública, sin pasar
    # por main()/argparse. (Smoke: el refactor de #90 no la dejó acoplada al CLI.)
    assert callable(llm_integration.add_llm_explanations)
    assert callable(llm_integration.prepare_classified_df)
    assert callable(llm_integration.save_llm_output)


# ════════════════════════════════════════════════════════════════════════════
# D. CSV-entregable del mentor (#97) — 5 columnas exactas, solo tardíos
# ════════════════════════════════════════════════════════════════════════════
def _df_con_llm() -> pd.DataFrame:
    """DataFrame mínimo con la clasificación de F2 y las columnas llm_* de F3:
    dos POs tardíos y uno on-time (que NO debe salir al entregable). Incluye las
    columnas de soporte (timeline, agravantes, concordancia) del artefacto ampliado."""
    base = {
        "PO_NBR": ["PO-1", "PO-2", "PO-ONTIME"],
        "stage_primary": ["Vendor", "Carrier", "On-Time"],
        "delay_days_calc": [4.0, 1.5, 0.0],
        "llm_severidad": ["HIGH", "MEDIUM", ""],
        "llm_causa_raiz": ["cita aprobada tarde", "tránsito lento", ""],
        "llm_accion_recomendada": ["contactar vendor", "escalar carrier", ""],
        # soporte: agravantes y concordancia
        "HOT_PO_FLAG": [1, 0, 0],
        "is_short_ship": [False, True, False],
        "REASON_DSC": ["Vendor late appt", "Carrier delay", ""],
        "llm_coincide_con_reason": [True, False, False],
        # columna interna que NO debe aparecer en el entregable:
        "severity": ["HIGH", "LOW", ""],
        "llm_confianza": [0.9, 0.5, 0.0],
    }
    # soporte: timeline (7 timestamps)
    for col in ("PO_DT", "STA_DT", "APPROVED_DT", "TRAILER_ARRIVE_DT",
                "CHECKIN_DT", "CHECKOUT_DT", "RECPT_DT"):
        base[col] = ["2024-01-05 00:00", "2024-01-06 00:00", "2024-01-04 00:00"]
    return pd.DataFrame(base)


def test_export_deliverable_columnas_exactas_y_orden(tmp_path):
    out_path = tmp_path / "po_output.csv"
    export_deliverable_csv(_df_con_llm(), out_path)
    releido = pd.read_csv(out_path)
    # El artefacto trae las columnas declaradas, en orden.
    assert list(releido.columns) == _DELIVERABLE_COLUMNS
    # Las 5 del mentor van PRIMERO y en orden (contrato canónico inamovible).
    assert list(releido.columns[:5]) == _MENTOR_COLUMNS
    assert _MENTOR_COLUMNS == ["PO_NBR", "stage", "severity", "explanation", "action"]
    # Columnas internas que NO deben filtrarse al artefacto (no aportan a la app).
    assert "llm_confianza" not in releido.columns
    assert "stage_primary" not in releido.columns   # se canoniza a 'stage'


def test_export_deliverable_incluye_soporte_app(tmp_path):
    # El artefacto ampliado (contrato F3→F4 #100) trae timeline + agravantes +
    # concordancia para que la app NO recompute.
    out_path = tmp_path / "po_output.csv"
    export_deliverable_csv(_df_con_llm(), out_path)
    releido = pd.read_csv(out_path)
    for col in ("PO_DT", "RECPT_DT", "HOT_PO_FLAG", "is_short_ship",
                "REASON_DSC", "llm_coincide_con_reason"):
        assert col in releido.columns


def test_export_deliverable_solo_tardios(tmp_path):
    out_path = tmp_path / "po_output.csv"
    out = export_deliverable_csv(_df_con_llm(), out_path)
    # El on-time (delay=0) se excluye: solo los 2 tardíos.
    assert len(out) == 2
    assert list(out["PO_NBR"]) == ["PO-1", "PO-2"]
    assert "PO-ONTIME" not in set(out["PO_NBR"])


def test_export_deliverable_severity_es_la_del_llm(tmp_path):
    # ADR-10: la severity oficial del entregable es la del LLM (llm_severidad),
    # no la determinística de F2. El fixture las hace distinguibles (PO-2: LLM
    # dice MEDIUM, F2 dice LOW) para comprobar de cuál se toma.
    out_path = tmp_path / "po_output.csv"
    out = export_deliverable_csv(_df_con_llm(), out_path)
    assert list(out["severity"]) == ["HIGH", "MEDIUM"]      # = llm_severidad
    # dominio válido
    assert set(out["severity"]).issubset({"HIGH", "MEDIUM", "LOW"})
