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
import json

import pandas as pd
import pytest

import llm_integration
from llm_integration import (
    add_llm_explanations,
    build_action_prompt,
    build_prompt,
    call_action_with_qa,
    compute_dataset_stats,
    is_meta_action,
    run_action_checks,
    select_domain_context,
    _action_keys_in_order,
    _excess_band,
    _cond_matches,
    _parse_action_json,
    _parse_llm_json,
    _percentile_rank,
    load_llm_config,
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
    row["stage_primary"] = "Indeterminado"
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
    row["stage_primary"] = "Indeterminado"
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


def test_format_example_indeterminado_muestra_substage():
    # #136: _format_example espeja el comportamiento de build_prompt (#135): el substage
    # aparece en CONTEXTO ADICIONAL del ejemplo cuando stage=INDETERMINADO y el campo existe.
    ej_sin_datos = {
        "stage_primary": "Indeterminado",
        "indeterminado_substage": "sin_datos",
        "delay_days_calc": 2.10,
        "REASON_DSC": "Vendor delivery delay",
        "causa_raiz": "INDETERMINADO por falta de timestamps.",
        "accion_recomendada": "Completar registro de timestamps.",
        "severidad": "MEDIUM",
        "coincide_con_reason_code": False,
        "confianza": 0.5,
    }
    out = build_prompt(_row_ejemplo(), examples=[ej_sin_datos])
    bloque = out[out.index("EJEMPLOS"):out.index("INSTRUCCIONES:")]
    assert "Sub-categoría INDETERMINADO: sin_datos" in bloque


def test_format_example_indeterminado_no_muestra_exceso_ni_responsable():
    # #136: INDETERMINADO no tiene señal de exceso medible → _format_example no debe
    # incluir líneas de responsable ni exceso (cae al branch (None, None) de _STAGE_SIGNAL).
    ej = {
        "stage_primary": "Indeterminado",
        "indeterminado_substage": "sin_causa_dominante",
        "delay_days_calc": 3.40,
        "REASON_DSC": "Multiple delays - carrier and DC",
        "causa_raiz": "Ambigüedad entre Carrier y DC.",
        "accion_recomendada": "Revisión conjunta.",
        "severidad": "MEDIUM",
        "coincide_con_reason_code": True,
        "confianza": 0.65,
    }
    out = build_prompt(_row_ejemplo(), examples=[ej])
    bloque = out[out.index("EJEMPLOS"):out.index("INSTRUCCIONES:")]
    assert "Exceso del" not in bloque
    assert "Sub-categoría INDETERMINADO: sin_causa_dominante" in bloque


# ════════════════════════════════════════════════════════════════════════════
# A2. Contexto de dominio condicional por (actor × señal) (#151)
# ════════════════════════════════════════════════════════════════════════════
def _kb_ejemplo() -> dict:
    """KB mínima de prueba (NO es domain_kb.json real): dos actores, cutoffs {1,3}."""
    return {
        "band_cutoffs": [1, 3],
        "actors": {
            "Carrier": {
                "primer": "El transportista mueve el tráiler del proveedor al DC.",
                "levers": [
                    {"id": "carrier_reschedule", "cond": {"is_rescheduled": True},
                     "lever": "Coordinar nueva cita con el transportista."},
                    {"id": "carrier_alto", "cond": {"excess_band": "alto"},
                     "lever": "Escalar reclamo formal por exceso severo de tránsito."},
                ],
            },
            "Vendor": {
                "primer": "El proveedor controla el envío y la cita.",
                "levers": [
                    {"id": "vendor_base", "cond": {}, "lever": "Contactar al proveedor."},
                ],
            },
        },
    }


# --- _excess_band: banda por exceso/umbral (umbrales reales de rules_config.json) ---
def test_excess_band_vendor_tres_niveles():
    # Umbral vendor = 24h. r = exceso/24 → bajo(≤1) / medio(≤3) / alto(>3).
    bajo = pd.Series({"stage_primary": "Vendor", "excess_vendor_hrs": 12.0})
    medio = pd.Series({"stage_primary": "Vendor", "excess_vendor_hrs": 48.0})
    alto = pd.Series({"stage_primary": "Vendor", "excess_vendor_hrs": 100.0})
    assert _excess_band(bajo, "Vendor") == "bajo"
    assert _excess_band(medio, "Vendor") == "medio"
    assert _excess_band(alto, "Vendor") == "alto"


def test_excess_band_dc_usa_umbral_del_substage():
    # Mismo exceso (5h), distinta sub-etapa → distinta banda: Dock(6h)→bajo, Yard(4h)→medio.
    dock = pd.Series({"stage_primary": "DC", "excess_dc_hrs": 5.0, "dc_substage": "Dock"})
    yard = pd.Series({"stage_primary": "DC", "excess_dc_hrs": 5.0, "dc_substage": "Yard"})
    assert _excess_band(dock, "DC") == "bajo"
    assert _excess_band(yard, "DC") == "medio"


def test_excess_band_indeterminado_y_sin_exceso_es_none():
    # Indeterminado no tiene banda (ADR-14: el exceso se retira). Exceso 0 → None.
    indet = pd.Series({"stage_primary": "Indeterminado", "excess_vendor_hrs": 100.0})
    cero = pd.Series({"stage_primary": "Vendor", "excess_vendor_hrs": 0.0})
    assert _excess_band(indet, "Indeterminado") is None
    assert _excess_band(cero, "Vendor") is None


# --- _cond_matches: AND de condiciones, falla cerrada en clave desconocida ---
def test_cond_matches_vacio_es_true():
    assert _cond_matches({}, _row_ejemplo(), "medio") is True


def test_cond_matches_clave_desconocida_falla_cerrada():
    assert _cond_matches({"no_existe": True}, _row_ejemplo(), "medio") is False


def test_cond_matches_and_de_varias_condiciones():
    row = _row_ejemplo()  # is_rescheduled=True, HOT_PO_FLAG=1
    assert _cond_matches({"is_rescheduled": True, "hot": True}, row, "medio") is True
    assert _cond_matches({"is_rescheduled": True, "hot": False}, row, "medio") is False


def test_cond_matches_excess_band():
    row = _row_ejemplo()
    assert _cond_matches({"excess_band": "medio"}, row, "medio") is True
    assert _cond_matches({"excess_band": "alto"}, row, "medio") is False


# --- select_domain_context: ruteo por actor + filtrado por señal ---
def test_select_domain_context_sin_kb_es_vacio():
    assert select_domain_context(_row_ejemplo(), None) == ""
    assert select_domain_context(_row_ejemplo(), {}) == ""


def test_select_domain_context_actor_ausente_es_vacio():
    row = _row_ejemplo()
    row["stage_primary"] = "On-Time"   # no está en el KB → sin bloque
    assert select_domain_context(row, _kb_ejemplo()) == ""


def test_select_domain_context_filtra_por_senal():
    # _row_ejemplo: Carrier, is_rescheduled=True, exceso 10/8 → banda 'medio'. Solo la
    # palanca de reschedule aplica; la de banda 'alto' se filtra.
    out = select_domain_context(_row_ejemplo(), _kb_ejemplo())
    assert "CONTEXTO DE DOMINIO" in out
    assert "El transportista mueve" in out                       # primer del actor
    assert "Coordinar nueva cita con el transportista." in out   # palanca que aplica
    assert "Escalar reclamo formal" not in out                   # palanca filtrada (banda)


# --- build_prompt con kb: invariante zero-shot y ubicación del bloque ---
def test_build_prompt_kb_none_equivale_a_sin_kb():
    # Invariante: kb=None → prompt byte-idéntico al histórico (no cambia producción).
    assert build_prompt(_row_ejemplo(), kb=None) == build_prompt(_row_ejemplo())


def test_build_prompt_con_kb_inyecta_contexto_de_dominio():
    out = build_prompt(_row_ejemplo(), kb=_kb_ejemplo())
    assert "CONTEXTO DE DOMINIO (relevante a esta PO):" in out
    # Ubicación: después de CONTEXTO ADICIONAL, antes de INSTRUCCIONES.
    assert out.index("CONTEXTO ADICIONAL:") < out.index("CONTEXTO DE DOMINIO")
    assert out.index("CONTEXTO DE DOMINIO") < out.index("INSTRUCCIONES:")
    assert "Coordinar nueva cita con el transportista." in out


# ════════════════════════════════════════════════════════════════════════════
# A3. Llamada de acción (ARD-16, ola 1): stats, prompt, contrato, checks, QA
# ════════════════════════════════════════════════════════════════════════════
def _row_accion() -> pd.Series:
    """Fila de _row_ejemplo + las magnitudes que la llamada de acción destapa."""
    row = _row_ejemplo()
    row["NUM_CASES_ORDERED"] = 250
    row["NUM_CASES_SHIPPED"] = 180
    row["_fill_rate"] = 0.72
    row["DT_APPT_FIRST_APPROVED"] = "2024-01-03 00:00"
    row["DT_APPT_CURRENT_APPROVED"] = "2024-01-04 00:00"
    return row


def _diag_ejemplo() -> dict:
    """Diagnóstico de la llamada 1 (insumo de la llamada 2)."""
    return {
        "causa_raiz": "La etapa Carrier concentra el retraso de 3.00 días.",
        "accion_recomendada": "Contactar al carrier",
        "severidad": "HIGH",
        "coincide_con_reason_code": True,
        "confianza": 0.9,
    }


def _stats_ejemplo() -> dict:
    """Stats globales mínimas (forma de compute_dataset_stats, valores a mano)."""
    return {
        "delay_values": [1.0, 2.0, 3.0, 4.0],
        "delay_median": 2.5,
        "excess": {
            "Vendor": {"values": [30.0, 50.0], "median": 40.0},
            "Carrier": {"values": [5.0, 10.0, 20.0], "median": 10.0},
            "DC": {"values": [7.0], "median": 7.0},
        },
    }


def _prompt_accion() -> str:
    return build_action_prompt(_row_accion(), _diag_ejemplo(), _stats_ejemplo())


def _raw_accion_ok() -> str:
    """Respuesta cruda VÁLIDA del contrato híbrido: llaves en orden, cifras del input
    (3.00 días y 10.0 h están en el prompt de _row_accion), etapa Carrier nombrada,
    acción inmediata concreta (sin verbo meta). La elicitación va primera y SIN
    cifras (regla del cuestionario: una cifra inventada caería en el check)."""
    return json.dumps({
        "elicitacion": "Como patrón de industria, los retrasos del transportista "
                       "suelen venir de planificación de rutas, capacidad de flota o "
                       "clima; un short ship obliga a decidir la reposición del "
                       "faltante; una re-cita suele reflejar problemas de agenda.",
        "razonamiento": "El exceso del transportista de 10.0 horas concentra el "
                        "retraso en la etapa Carrier.",
        "hipotesis_principal": {
            "hipotesis": "Planificación de rutas deficiente del transportista (Carrier).",
            "evidencia": "Exceso del transportista: 10.0 horas; retraso de 3.00 días.",
            "plan": {
                "accion_inmediata": "Exigir a FastFreight un plan correctivo con fecha "
                                    "por las 10.0 horas de exceso de tránsito.",
                "accion_correctiva": "Renegociar la ventana de tránsito con FastFreight.",
                "accion_preventiva": "Incorporar penalización por exceso de tránsito "
                                     "al contrato con el transportista.",
            },
        },
        "hipotesis_alternativa": {
            "hipotesis": "Congestión en el patio del DC que retrasó el registro de llegada.",
            "paso_discriminante": "Obtener el log de llegada del tráiler: si la llegada "
                                  "real fue antes de la cita, reclamar al DC; si no, "
                                  "sostener el reclamo al transportista.",
        },
        "confianza": 0.8,
    }, ensure_ascii=False)


def _raw_accion_meta() -> str:
    """Variante con verbo meta como acción inmediata (debe fallar el check)."""
    d = json.loads(_raw_accion_ok())
    d["hipotesis_principal"]["plan"]["accion_inmediata"] = (
        "Revisar con el equipo del DC el proceso de descarga"
    )
    return json.dumps(d, ensure_ascii=False)


class _ActionBackendStub:
    """Backend falso: devuelve respuestas crudas en secuencia y registra los prompts."""

    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.prompts = []

    def call_raw(self, prompt):
        self.prompts.append(prompt)
        return self.respuestas.pop(0) if self.respuestas else None


# --- compute_dataset_stats / _percentile_rank: comparativos deterministas ---
def test_compute_dataset_stats_filtra_tardios_y_por_etapa():
    df = pd.DataFrame({
        "delay_days_calc": [0.0, 1.0, 2.0, 3.0],
        "stage_primary": ["On-Time", "Vendor", "Vendor", "Carrier"],
        "excess_vendor_hrs": [50.0, 30.0, 40.0, 0.0],
        "excess_carrier_hrs": [0.0, 0.0, 0.0, 12.0],
        "excess_dc_hrs": [0.0, 0.0, 0.0, 0.0],
    })
    stats = compute_dataset_stats(df)
    # Solo tardíos: el on-time (delay 0, exceso vendor 50) queda fuera de TODO.
    assert stats["delay_values"] == [1.0, 2.0, 3.0]
    assert stats["delay_median"] == 2.0
    # Exceso por etapa: solo los POs ATRIBUIDOS a esa etapa.
    assert stats["excess"]["Vendor"]["values"] == [30.0, 40.0]
    assert stats["excess"]["Vendor"]["median"] == 35.0
    assert stats["excess"]["Carrier"]["values"] == [12.0]
    assert stats["excess"]["DC"]["values"] == []
    assert stats["excess"]["DC"]["median"] == 0.0


def test_percentile_rank_es_pct_de_menores():
    assert _percentile_rank([1.0, 2.0, 3.0, 4.0], 3.0) == 50
    assert _percentile_rank([1.0, 2.0, 3.0, 4.0], 5.0) == 100
    assert _percentile_rank([1.0], 0.5) == 0
    assert _percentile_rank([], 1.0) is None


# --- build_action_prompt: contrato, magnitudes, comparativos, perímetro ---
def test_build_action_prompt_contrato_con_llaves_en_orden():
    out = _prompt_accion()
    assert "EN ESTE ORDEN" in out
    assert (out.index('"elicitacion"') < out.index('"razonamiento"')
            < out.index('"hipotesis_principal"')
            < out.index('"hipotesis_alternativa"') < out.index('"confianza"'))
    for campo in ('"accion_inmediata"', '"accion_correctiva"', '"accion_preventiva"',
                  '"paso_discriminante"', '"evidencia"'):
        assert campo in out


def test_build_action_prompt_incluye_diagnostico_de_llamada_1():
    out = _prompt_accion()
    assert "DIAGNÓSTICO VALIDADO" in out
    assert "La etapa Carrier concentra el retraso de 3.00 días." in out
    assert "- Severidad: HIGH" in out


def test_build_action_prompt_magnitudes_destapadas():
    out = _prompt_accion()
    assert "MAGNITUDES DE LA ORDEN:" in out
    assert "Tamaño de la orden: 250 cajas pedidas" in out
    assert "Cajas embarcadas: 180 (fill rate: 72.0%" in out
    assert "por debajo de 90%" in out           # umbral de rules_config.json
    assert "+24.0 horas entre la primera cita aprobada y la vigente" in out


def test_build_action_prompt_sin_reschedule_linea_neutra():
    row = _row_accion()
    row["is_rescheduled"] = False
    out = build_action_prompt(row, _diag_ejemplo(), _stats_ejemplo())
    assert "sin reprogramación (0.0 h)" in out


def test_build_action_prompt_comparativos_globales():
    out = _prompt_accion()
    assert "COMPARATIVOS DEL DATASET" in out
    # delay 3.00 entre [1,2,3,4] → 2 menores de 4 → percentil 50; mediana 2.50.
    assert "percentil 50 de los POs tardíos del dataset (mediana: 2.50 días)" in out
    # exceso carrier 10.0 entre [5,10,20] → 1 menor de 3 → percentil 33.
    assert "percentil 33 de los POs tardíos atribuidos a Carrier" in out
    assert "Medianas de exceso por etapa entre tardíos: Vendor 40.0 h · " \
           "Carrier 10.0 h · DC 7.0 h." in out


def test_build_action_prompt_indeterminado_sin_percentil_de_exceso():
    # ADR-14: en Indeterminado el exceso se retira (regla por etapa) → ni las líneas de
    # exceso ni su percentil; el percentil del delay y las medianas globales sí van.
    row = _row_accion()
    row["stage_primary"] = "Indeterminado"
    out = build_action_prompt(row, _diag_ejemplo(), _stats_ejemplo())
    assert "El exceso de" not in out
    assert "Exceso del transportista" not in out
    assert "percentil 50 de los POs tardíos del dataset" in out
    assert "Medianas de exceso por etapa entre tardíos" in out


def test_build_action_prompt_sin_fewshot_y_con_reglas_de_concrecion():
    # Descartes de ARD-16: sin few-shot de acciones ni playbook; las reglas de
    # concreción y el perímetro datos/dominio van en el texto.
    out = _prompt_accion()
    assert "EJEMPLOS DE RAZONAMIENTO" not in out
    assert "REGLAS DEL PLAN (obligatorias):" in out
    assert "NO cuentan como acción principal" in out
    assert "re-emitir" in out                       # decisión del faltante
    assert "PERÍMETRO DE RAZONAMIENTO:" in out
    assert "márcalo en la redacción" in out          # generalizaciones marcadas


# --- is_meta_action: lista cerrada de ARD-16 (comparte lógica check + métrica) ---
def test_is_meta_action_detecta_lista_cerrada():
    for accion in ("Revisar el muelle 3", "Revise con el equipo",
                   "Analizar las causas del retraso", "Investigue el reschedule",
                   "Monitorear el tránsito", "Dar seguimiento al caso",
                   "Hacer seguimiento con el vendor"):
        assert is_meta_action(accion) is True, accion


def test_is_meta_action_no_dispara_en_acciones_concretas():
    for accion in ("Emitir una orden de reposición por el faltante",
                   "Contactar al proveedor y exigir plan correctivo",
                   "Abrir un reclamo formal con FastFreight",
                   "Re-emitir la PO por las cajas faltantes", ""):
        assert is_meta_action(accion) is False, accion


# --- _parse_action_json / _action_keys_in_order: contrato híbrido ---
def test_parse_action_json_aplana_contrato():
    out = _parse_action_json(_raw_accion_ok())
    assert out["elicitacion"].startswith("Como patrón de industria")
    assert out["hipotesis"].startswith("Planificación")
    assert out["hipotesis_evidencia"].startswith("Exceso del transportista")
    assert out["accion_inmediata"].startswith("Exigir")
    assert out["paso_discriminante"].startswith("Obtener el log")
    assert out["confianza_hipotesis"] == 0.8


def test_parse_action_json_sin_json_devuelve_none():
    assert _parse_action_json("respuesta en texto libre") is None
    assert _parse_action_json("") is None


def test_parse_action_json_llaves_faltantes_dan_vacio():
    out = _parse_action_json('{"razonamiento": "solo esto"}')
    assert out["razonamiento"] == "solo esto"
    assert out["elicitacion"] == ""
    assert out["accion_inmediata"] == ""
    assert out["confianza_hipotesis"] == 0.5    # default documentado del parser


def test_action_keys_in_order_verifica_sobre_el_crudo():
    assert _action_keys_in_order(_raw_accion_ok()) is True
    desordenado = ('{"confianza": 0.8, "elicitacion": "x", "razonamiento": "x", '
                   '"hipotesis_principal": {}, "hipotesis_alternativa": {}}')
    assert _action_keys_in_order(desordenado) is False
    # La elicitación fuera de su lugar (tras el razonamiento) también rompe el orden.
    elicit_tarde = ('{"razonamiento": "x", "elicitacion": "x", '
                    '"hipotesis_principal": {}, "hipotesis_alternativa": {}, '
                    '"confianza": 0.8}')
    assert _action_keys_in_order(elicit_tarde) is False


# --- run_action_checks: cada check con caso que pasa y caso que falla ---
def test_run_action_checks_pasa_limpio():
    raw = _raw_accion_ok()
    parsed = _parse_action_json(raw)
    assert run_action_checks(parsed, raw, _row_accion(), _prompt_accion()) == []


def test_run_action_checks_detecta_verbo_meta():
    parsed = _parse_action_json(_raw_accion_ok())
    parsed["accion_inmediata"] = "Revisar con el equipo del DC el proceso de descarga"
    codigos = [c for c, _ in run_action_checks(
        parsed, _raw_accion_ok(), _row_accion(), _prompt_accion())]
    assert "verbo_meta" in codigos


def test_run_action_checks_detecta_cifra_inventada():
    parsed = _parse_action_json(_raw_accion_ok())
    parsed["hipotesis_evidencia"] = "Un exceso de 99.9 horas fuera de los datos"
    codigos = [c for c, _ in run_action_checks(
        parsed, _raw_accion_ok(), _row_accion(), _prompt_accion())]
    assert "cifra_fuera_de_input" in codigos


def test_run_action_checks_esquema_incompleto():
    parsed = _parse_action_json('{"razonamiento": "solo esto"}')
    codigos = [c for c, _ in run_action_checks(
        parsed, '{"razonamiento": "solo esto"}', _row_accion(), _prompt_accion())]
    assert "esquema_incompleto" in codigos
    assert "orden_de_llaves" in codigos


def test_run_action_checks_short_ship_exige_decision():
    row = _row_accion()
    row["is_short_ship"] = True
    row["_short_ship"] = True
    parsed = _parse_action_json(_raw_accion_ok())
    codigos = [c for c, _ in run_action_checks(
        parsed, _raw_accion_ok(), row, _prompt_accion())]
    assert "sin_decision_faltante" in codigos
    # Con la decisión (re-emitir/esperar/cancelar) en el plan, el check pasa.
    parsed["accion_correctiva"] = ("Re-emitir la orden por el faltante y esperar la "
                                   "confirmación del proveedor")
    codigos2 = [c for c, _ in run_action_checks(
        parsed, _raw_accion_ok(), row, _prompt_accion())]
    assert "sin_decision_faltante" not in codigos2


def test_run_action_checks_etapa_incorrecta():
    parsed = _parse_action_json(_raw_accion_ok())
    parsed["razonamiento"] = "El retraso de 3.00 días viene del proveedor."
    parsed["hipotesis"] = "Retraso del Vendor en producción."
    codigos = [c for c, _ in run_action_checks(
        parsed, _raw_accion_ok(), _row_accion(), _prompt_accion())]
    assert "etapa_incorrecta" in codigos


def test_run_action_checks_indeterminado_acepta_declaracion():
    row = _row_accion()
    row["stage_primary"] = "Indeterminado"
    prompt = build_action_prompt(row, _diag_ejemplo(), _stats_ejemplo())
    parsed = _parse_action_json(_raw_accion_ok())
    parsed["razonamiento"] = "La señal es indeterminada: falta el timestamp que aísle la etapa."
    parsed["hipotesis"] = "Registro incompleto del evento (dato faltante)."
    codigos = [c for c, _ in run_action_checks(parsed, _raw_accion_ok(), row, prompt)]
    assert "etapa_incorrecta" not in codigos


# --- ARD-16 ola 2: concordancia motivo↔etapa (meta-señal determinista) ---
def test_action_prompt_concordancia_coincide():
    row = _row_accion()
    row["reason_group_manual"] = "Carrier"      # = stage_primary
    out = build_action_prompt(row, _diag_ejemplo(), _stats_ejemplo())
    assert "el motivo anotado apunta a la misma etapa medida (Carrier)" in out
    assert "DISCREPA" not in out


def test_action_prompt_concordancia_discrepa_es_meta_senal():
    row = _row_accion()
    row["reason_group_manual"] = "Vendor"       # etapa medida: Carrier
    out = build_action_prompt(row, _diag_ejemplo(), _stats_ejemplo())
    assert ("DISCREPA — el motivo anotado apunta a Vendor y la etapa medida es "
            "Carrier") in out
    assert "PROCESO DE ANOTACIÓN" in out
    # La regla de no promover el REASON_DSC a etapa se preserva en la redacción.
    assert "nunca sustituir la etapa medida" in out


def test_action_prompt_concordancia_incondicional_no_evaluable():
    # Sin reason_group_manual la fila cae a Unknown → "no evaluable"; la línea existe
    # SIEMPRE (incondicional, sin juicio por selección — como la línea de reschedule).
    out = _prompt_accion()
    assert "Concordancia motivo↔etapa: no evaluable" in out


# --- ARD-16 ola 2: diagnóstico diferencial (mecanismo vs etiqueta) ---
def test_action_prompt_diferencial_generico_en_toda_etapa():
    out = _prompt_accion()                       # etapa Carrier
    assert "DIAGNÓSTICO DIFERENCIAL (obligatorio):" in out
    assert "MECANISMO, no una etiqueta" in out
    assert "DISTINTOS y DISTINGUIBLES" in out
    # El pointer de señales (fill rate / reprogramación) es EXCLUSIVO de Vendor.
    assert "separan mecanismos" not in out


def test_action_prompt_diferencial_pointer_solo_vendor():
    row = _row_accion()
    row["stage_primary"] = "Vendor"
    out = build_action_prompt(row, _diag_ejemplo(), _stats_ejemplo())
    assert ("En esta etapa (Vendor), el fill rate y la magnitud de la "
            "reprogramación separan mecanismos") in out


def test_action_prompt_indeterminado_hipotesis_condicional():
    row = _row_accion()
    row["stage_primary"] = "Indeterminado"
    out = build_action_prompt(row, _diag_ejemplo(), _stats_ejemplo())
    assert "NO afirma un mecanismo como causa" in out
    assert "formula el mecanismo en condicional" in out


# --- ARD-16 ola 2: reparto multi-actor con stage_multi ---
def test_action_prompt_multi_actor_solo_con_stage_multi_activo():
    row = _row_accion()
    row["stage_multi"] = "Vendor + Carrier"
    out = build_action_prompt(row, _diag_ejemplo(), _stats_ejemplo())
    assert "Hay causas múltiples activas (Vendor + Carrier)" in out
    assert ("UNA sola, dirigida al cuello de botella (la etapa primaria: "
            "Carrier)") in out
    # Sin " + " (una sola etiqueta o el centinela "Ninguno") el bullet no aparece.
    assert "causas múltiples activas" not in _prompt_accion()
    row2 = _row_accion()
    row2["stage_multi"] = "Ninguno"
    out2 = build_action_prompt(row2, _diag_ejemplo(), _stats_ejemplo())
    assert "causas múltiples activas" not in out2


# --- ARD-16 ola 2: checks nuevos por regla ---
def test_run_action_checks_evidencia_sin_cifra():
    parsed = _parse_action_json(_raw_accion_ok())
    parsed["hipotesis_evidencia"] = "La entrega llegó tarde por el transportista."
    codigos = [c for c, _ in run_action_checks(
        parsed, _raw_accion_ok(), _row_accion(), _prompt_accion())]
    assert "evidencia_sin_cifra" in codigos
    # El caso base cita cifras → pasa (cubierto por test_run_action_checks_pasa_limpio).


def test_run_action_checks_indeterminado_sin_reconocer():
    row = _row_accion()
    row["stage_primary"] = "Indeterminado"
    prompt = build_action_prompt(row, _diag_ejemplo(), _stats_ejemplo())
    parsed = _parse_action_json(_raw_accion_ok())
    parsed["razonamiento"] = "La señal es indeterminada; ninguna etapa domina."
    # Hipótesis afirmativa (el hueco exacto del baseline): el razonamiento declara
    # indeterminación pero la hipótesis afirma un mecanismo → defecto.
    parsed["hipotesis"] = "Congestión en el patio del DC."
    codigos = [c for c, _ in run_action_checks(parsed, _raw_accion_ok(), row, prompt)]
    assert "indeterminado_sin_reconocer" in codigos
    # Hipótesis que reconoce la indeterminación (dato faltante + condicional) → pasa.
    parsed["hipotesis"] = ("Dato faltante: sin el log de llegada no se puede atribuir; "
                           "si se confirma congestión, el mecanismo es de patio.")
    codigos2 = [c for c, _ in run_action_checks(parsed, _raw_accion_ok(), row, prompt)]
    assert "indeterminado_sin_reconocer" not in codigos2
    # Formulación condicional PURA (sin palabra literal de la lista): también pasa —
    # es la forma que el prompt pide y el hueco que mostró el gate de la ola 2.
    parsed["hipotesis"] = ("Si el tiempo de patio refleja congestión, el mecanismo es "
                           "de puertas; si la descarga fue atípica, es del proceso.")
    codigos3 = [c for c, _ in run_action_checks(parsed, _raw_accion_ok(), row, prompt)]
    assert "indeterminado_sin_reconocer" not in codigos3


def test_run_action_checks_etapa_acepta_alias_en_espanol():
    # Falso positivo del gate (100197/100318): el modelo escribe "proveedor" y el check
    # buscaba el literal "Vendor". Los alias por etapa lo corrigen.
    row = _row_accion()
    row["stage_primary"] = "Vendor"
    prompt = build_action_prompt(row, _diag_ejemplo(), _stats_ejemplo())
    parsed = _parse_action_json(_raw_accion_ok())
    parsed["razonamiento"] = "El retraso de 3.00 días se origina antes del tránsito."
    parsed["hipotesis"] = "Falta de producto en inventario del proveedor."
    codigos = [c for c, _ in run_action_checks(parsed, _raw_accion_ok(), row, prompt)]
    assert "etapa_incorrecta" not in codigos


def test_run_action_checks_indeterminado_no_aplica_en_atribuidas():
    # Etapa atribuida (Carrier) con hipótesis afirmativa: el check no aplica.
    parsed = _parse_action_json(_raw_accion_ok())
    codigos = [c for c, _ in run_action_checks(
        parsed, _raw_accion_ok(), _row_accion(), _prompt_accion())]
    assert "indeterminado_sin_reconocer" not in codigos


# --- ARD-16 ola 3: auto-cuestionario de elicitación (campo `elicitacion`) ---
def test_action_prompt_cuestionario_pregunta_por_etapa():
    # La pregunta 1 se parametriza por stage_primary (las otras dos son fijas).
    esperado = {
        "Vendor": "se originan en el proveedor, antes del embarque",
        "Carrier": "se originan en el tránsito del transportista",
        "DC": "recepción del centro de distribución (patio y descarga)",
        "Indeterminado": "suelen quedar sin atribuir cuando los timestamps",
    }
    for etapa, fragmento in esperado.items():
        row = _row_accion()
        row["stage_primary"] = etapa
        out = build_action_prompt(row, _diag_ejemplo(), _stats_ejemplo())
        assert fragmento in out, etapa


def test_action_prompt_cuestionario_bloque_antes_de_la_tarea():
    out = _prompt_accion()
    assert "AUTO-CUESTIONARIO DE DOMINIO" in out
    # Sin cifras: la instrucción previene lo que el check de cifras haría cumplir.
    assert "SIN cifras" in out
    # Las preguntas fijas del mentor (shorting y rescheduling) van en toda PO.
    assert "¿Cómo afecta un short ship" in out
    assert "reprogramación de una cita de entrega" in out
    # El cuestionario se responde ANTES de analizar la PO: bloque previo a TU TAREA.
    assert out.index("AUTO-CUESTIONARIO DE DOMINIO") < out.index("TU TAREA:")


def test_run_action_checks_elicitacion_faltante_es_esquema_incompleto():
    raw = _raw_accion_ok()
    parsed = _parse_action_json(raw)
    parsed["elicitacion"] = ""
    defectos = run_action_checks(parsed, raw, _row_accion(), _prompt_accion())
    detalles = {c: d for c, d in defectos}
    assert "esquema_incompleto" in detalles
    assert "elicitacion" in detalles["esquema_incompleto"]


# --- ARD-16 ola 3: glosario abierto de vocabulario de industria ---
def test_action_prompt_glosario_terminos_sueltos_y_anti_plantilla():
    out = _prompt_accion()
    assert "VOCABULARIO DE INDUSTRIA (disponible, no obligatorio):" in out
    # Términos sueltos, sin definiciones ni frases de ejemplo (lección de ADR-14).
    for termino in ("expedite", "chargeback", "carrier scorecard", "re-cita de dock",
                    "split shipment", "safety stock", "OTIF"):
        assert termino in out, termino
    assert "La lista es abierta" in out
    assert "no transcribas frases de este prompt" in out
    assert out.index("VOCABULARIO DE INDUSTRIA") < out.index("TU TAREA:")


def test_run_action_checks_elicitacion_con_cifra_inventada():
    # El cuestionario pide respuestas sin cifras; un "típicamente N horas" inventado
    # cae en el check de cifras ∈ input (elicitacion es campo de texto del contrato).
    parsed = _parse_action_json(_raw_accion_ok())
    parsed["elicitacion"] = "Típicamente estos retrasos duran 48 horas."
    codigos = [c for c, _ in run_action_checks(
        parsed, _raw_accion_ok(), _row_accion(), _prompt_accion())]
    assert "cifra_fuera_de_input" in codigos


# --- call_action_with_qa: regeneración citando el defecto, tope, sin bloqueo ---
def test_call_action_with_qa_regenera_citando_defecto():
    stub = _ActionBackendStub([_raw_accion_meta(), _raw_accion_ok()])
    parsed, flags = call_action_with_qa(stub, _prompt_accion(), _row_accion())
    assert flags == []
    assert parsed["accion_inmediata"].startswith("Exigir")
    assert len(stub.prompts) == 2
    assert "REGENERACIÓN" in stub.prompts[1]
    assert "verbo meta" in stub.prompts[1]      # el defecto se cita, no se repite a ciegas


def test_call_action_with_qa_respeta_maximo_de_reintentos():
    stub = _ActionBackendStub([_raw_accion_meta()] * 5)
    parsed, flags = call_action_with_qa(stub, _prompt_accion(), _row_accion())
    assert len(stub.prompts) == 3               # 1 llamada + 2 reintentos, no más
    assert flags == ["verbo_meta"]              # qa_flags visible, sin bloquear
    assert parsed["accion_inmediata"].startswith("Revisar")


def test_call_action_with_qa_sin_json_marca_flag():
    stub = _ActionBackendStub(["texto sin json"] * 3)
    parsed, flags = call_action_with_qa(stub, _prompt_accion(), _row_accion())
    assert parsed == {}
    assert flags == ["json_invalido"]
    assert len(stub.prompts) == 3


def test_call_action_with_qa_backend_sin_respuesta():
    stub = _ActionBackendStub([])               # call_raw → None (red agotada)
    parsed, flags = call_action_with_qa(stub, _prompt_accion(), _row_accion())
    assert parsed == {}
    assert flags == ["sin_respuesta"]
    assert len(stub.prompts) == 1               # reintentar el ciclo QA no ayuda


# --- add_llm_explanations: invariante opt-in y cableado del plan ---
class _Backend1Stub:
    """Stub de la llamada 1 (sin red): respuesta fija."""

    def __init__(self, respuesta):
        self.respuesta = respuesta

    def call(self, prompt):
        return self.respuesta


def _df_min_clasificado() -> pd.DataFrame:
    tardia = _row_accion().to_dict()
    ontime = {**tardia, "PO_NBR": "PO-ONTIME", "delay_days_calc": 0.0,
              "stage_primary": "On-Time"}
    return pd.DataFrame([tardia, ontime])


def test_add_llm_explanations_default_sin_columnas_de_accion():
    # Invariante opt-in (patrón ARD-15): sin action_call el DataFrame de salida no
    # cambia — ninguna columna nueva aparece y la llamada 1 se procesa igual.
    out = add_llm_explanations(_df_min_clasificado(),
                               backend=_Backend1Stub(_diag_ejemplo()),
                               delay_between_calls=0)
    for col in ("llm_elicitacion", "llm_razonamiento", "llm_hipotesis",
                "llm_accion_inmediata", "llm_qa_flags", "llm_confianza_hipotesis"):
        assert col not in out.columns
    assert out.loc[0, "llm_causa_raiz"].startswith("La etapa Carrier")


def test_add_llm_explanations_action_call_llena_plan():
    class _Dual(_Backend1Stub):
        def call_raw(self, prompt):
            return _raw_accion_ok()

    out = add_llm_explanations(_df_min_clasificado(),
                               backend=_Dual(_diag_ejemplo()),
                               delay_between_calls=0, action_call=True)
    assert out.loc[0, "llm_accion_inmediata"].startswith("Exigir")
    assert out.loc[0, "llm_paso_discriminante"].startswith("Obtener el log")
    assert out.loc[0, "llm_elicitacion"].startswith("Como patrón de industria")
    assert out.loc[0, "llm_qa_flags"] == ""
    assert out.loc[0, "llm_confianza_hipotesis"] == 0.8
    # El on-time no se procesa (misma regla que la llamada 1).
    assert out.loc[1, "llm_accion_inmediata"] == ""


def test_add_llm_explanations_action_call_sin_diagnostico():
    # Política ola 1 ante fallback de la llamada 1: la llamada 2 NO corre y el
    # qa_flag lo hace visible.
    class _Falla(_Backend1Stub):
        def call_raw(self, prompt):
            pytest.fail("la llamada 2 no debe correr sin diagnóstico de la llamada 1")

    out = add_llm_explanations(_df_min_clasificado(), backend=_Falla(None),
                               delay_between_calls=0, action_call=True)
    assert out.loc[0, "llm_qa_flags"] == "sin_diagnostico_llamada1"
    assert out.loc[0, "llm_accion_inmediata"] == ""


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


# ════════════════════════════════════════════════════════════════════════════
# E. load_llm_config — contrato de config de inferencia (#122)
# ════════════════════════════════════════════════════════════════════════════
def test_load_llm_config_trae_claves_de_inferencia():
    # El JSON versionado expone temperatura/max_tokens/timeout/reintentos y modelos
    # por backend: el código de llamada los lee de aquí, no como literales. Los
    # valores son los del entregable (temperatura 0.9 desde ADR-13 ronda 2, #137).
    cfg = load_llm_config()
    assert cfg["temperature"] == 0.9
    assert cfg["max_tokens"] == 512
    assert cfg["timeout_seconds"] == 60
    assert cfg["max_retries"] == 3
    for backend in ("claude", "local", "deepseek", "openai"):
        assert backend in cfg["models"]


def test_load_llm_config_path_explicito(tmp_path):
    # path override: load_llm_config lee el JSON indicado (no solo el sibling del módulo).
    import json
    p = tmp_path / "llm_config.json"
    p.write_text(json.dumps({"temperature": 0.9}), encoding="utf-8")
    assert load_llm_config(p)["temperature"] == 0.9
