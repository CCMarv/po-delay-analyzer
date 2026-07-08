"""
test_eval_quality.py — pruebas del nombrado de fixtures del benchmark (eval_quality.py).

Cubren el desacople del #147: la temperatura EFECTIVA de la corrida (override de CLI o, en
su defecto, la de llm_config.json) es la que decide el sufijo del nombre, de modo que una
corrida sin --temperature no pise el baseline 0.3 (el fixture sin sufijo). Es lógica
determinística pura: no toca red, API ni backend (el bug vivía en cómo `main` alimentaba el
sufijo, no en llamar al LLM).

`eval_quality` se importa gracias al pythonpath de pyproject.toml (03_llm_integration) y al
insert de red de seguridad de conftest.py — igual que el resto de la suite.
"""
import pandas as pd
import pytest

from eval_quality import (
    ANCHOR_TEMP, _hipotesis_reconoce_indet, _hyp_tokens, _jaccard, _temp_suffix,
    hypothesis_convergence, resolve_temperature, to_markdown, usa_vocabulario,
)
from llm_integration import load_llm_config


# ════════════════════════════════════════════════════════════════════════════
# A. _temp_suffix — comportamiento crudo
# ════════════════════════════════════════════════════════════════════════════
def test_temp_suffix_ancla_sin_sufijo():
    # El ancla (0.3) es el único punto sin sufijo: su fixture es el baseline reproducible.
    assert _temp_suffix(ANCHOR_TEMP) == ""


def test_temp_suffix_no_ancla_codifica_tNN():
    assert _temp_suffix(0.9) == "_t09"
    assert _temp_suffix(0.5) == "_t05"
    assert _temp_suffix(0.7) == "_t07"


def test_temp_suffix_none_es_vacio():
    # None devuelve "" en crudo: ESTE es justo el comportamiento que causaba el #147 si se
    # invocaba con el argumento sin resolver. El fix es no pasarle None nunca (ver más
    # abajo), no cambiar _temp_suffix.
    assert _temp_suffix(None) == ""


# ════════════════════════════════════════════════════════════════════════════
# B. resolve_temperature — temperatura efectiva (raíz del #147)
# ════════════════════════════════════════════════════════════════════════════
def test_resolve_override_gana():
    # Si se pasó --temperature, esa manda; no se mira el config.
    assert resolve_temperature(0.3) == 0.3
    assert resolve_temperature(0.9) == 0.9


def test_resolve_sin_arg_usa_config():
    # Sin --temperature, la efectiva es la de llm_config.json (la MISMA que usa el backend).
    assert resolve_temperature(None) == load_llm_config()["temperature"]


# ════════════════════════════════════════════════════════════════════════════
# C. El caso del issue: corrida sin --temperature no pisa el baseline 0.3
# ════════════════════════════════════════════════════════════════════════════
def test_no_arg_no_pisa_baseline_cuando_config_no_es_ancla():
    # Con la config en su valor de producción (0.9, distinto del ancla 0.3), una corrida
    # SIN --temperature debe producir un sufijo NO vacío → fixture distinto del baseline.
    config_temp = load_llm_config()["temperature"]
    if config_temp == ANCHOR_TEMP:
        # Defensa de regresión: si alguien volviera a fijar 0.3 en config, este test no
        # aplica (el no-arg sí escribiría el baseline, que es lo correcto a 0.3).
        return
    sufijo = _temp_suffix(resolve_temperature(None))
    assert sufijo != "", (
        "Sin --temperature y con config != 0.3, el fixture debe llevar sufijo para no "
        "pisar el baseline 0.3 sin sufijo (#147)."
    )


def test_temperatura_03_explicita_si_va_al_baseline():
    # La ÚNICA vía que reescribe el ancla histórica es pedir 0.3 explícito.
    assert _temp_suffix(resolve_temperature(0.3)) == ""


# ════════════════════════════════════════════════════════════════════════════
# D. Convergencia léxica intra-etapa (gate de ARD-16 ola 2) — determinística pura
# ════════════════════════════════════════════════════════════════════════════
def test_hyp_tokens_quita_stopwords_y_normaliza():
    toks = _hyp_tokens("La capacidad DEL proveedor es insuficiente")
    assert toks == {"capacidad", "proveedor", "insuficiente"}


def test_jaccard_bordes():
    assert _jaccard(set(), {"a"}) == 0.0
    assert _jaccard({"x", "y"}, {"x", "y"}) == 1.0
    assert _jaccard({"x", "y"}, {"y", "z"}) == pytest.approx(1 / 3)


def test_hypothesis_convergence_identicas_y_distintas():
    # n hipótesis idénticas → clúster n; mecanismos sin solape → 1; vacía → 0.
    assert hypothesis_convergence(["Capacidad del proveedor insuficiente"] * 3) == 3
    distintas = [
        "Capacidad de producción insuficiente del proveedor",
        "Congestión de puertas en el centro de distribución",
        "Documentación de embarque incompleta del transportista",
    ]
    assert hypothesis_convergence(distintas) == 1
    assert hypothesis_convergence([]) == 0


def test_hypothesis_convergence_theta_controla_el_agrupamiento():
    # Solape parcial (Jaccard ≈ 0.43): converge con θ laxo, se separa con θ estricto.
    pareja = [
        "Capacidad del proveedor insuficiente para cumplir plazos",
        "Capacidad del proveedor limitada para cumplir la carga",
    ]
    assert hypothesis_convergence(pareja, theta=0.2) == 2
    assert hypothesis_convergence(pareja, theta=0.9) == 1


def test_hipotesis_reconoce_indet_usa_lista_compartida():
    # La MISMA función del check indeterminado_sin_reconocer (llm_integration): métrica
    # y check no pueden discrepar. Reconoce claves literales Y la formulación
    # condicional (hueco de vocabulario detectado en el gate de la ola 2: las 4
    # hipótesis salieron condicionales sin palabra literal).
    assert _hipotesis_reconoce_indet("Dato faltante: el log de llegada del tráiler") is True
    assert _hipotesis_reconoce_indet("No se puede atribuir sin el timestamp") is True
    assert _hipotesis_reconoce_indet(
        "Si el tiempo de espera se debe a congestión, el mecanismo es de patio"
    ) is True
    assert _hipotesis_reconoce_indet("Congestión en el patio del DC") is False
    # "análisis" contiene 'si' como subcadena pero NO como token: no cuenta.
    assert _hipotesis_reconoce_indet("Congestión detectada en el análisis del patio") is False


# ════════════════════════════════════════════════════════════════════════════
# E. Tabla del benchmark en modo acción (ARD-16 ola 3) — determinística pura
# ════════════════════════════════════════════════════════════════════════════
def _df_eval_accion_min() -> pd.DataFrame:
    """Una fila con TODAS las columnas del modo acción (forma de evaluate())."""
    return pd.DataFrame([{
        "PO_NBR": "100001", "stage_primary": "Vendor", "delay_days_calc": 2.5,
        "REASON_DSC": "Vendor fill rate", "llm_causa_raiz": "La etapa Vendor...",
        "llm_accion": "", "llm_elicitacion": "Como patrón de industria, faltas de "
        "inventario y capacidad de producción.", "llm_hipotesis": "Falta de producto",
        "llm_hipotesis_alt": "Agenda", "llm_accion_inmediata": "Emitir reposición",
        "llm_accion_correctiva": "x", "llm_accion_preventiva": "y",
        "llm_paso_discriminante": "z", "qa_flags": "",
        "chk_a_etapa": True, "chk_b_cuantifica": True, "chk_meta": False,
        "chk_c_accion_viable": "", "veredicto": "", "usa_vocab": True,
    }])


def test_usa_vocabulario_detecta_terminos_normalizados():
    # Claves acortadas sobre texto normalizado: "scorecard" caza la mención parcial,
    # OTIF es case-insensitive vía _norm. Sin término del glosario → False.
    assert usa_vocabulario(["Solicitar un expedite del faltante al proveedor"]) is True
    assert usa_vocabulario(["", "Aplicar el chargeback contractual", ""]) is True
    assert usa_vocabulario(["Registrar el evento en el scorecard del transportista"]) is True
    assert usa_vocabulario(["Medir el OTIF del proveedor cada mes"]) is True
    assert usa_vocabulario(["Contactar al proveedor y exigir plan correctivo"]) is False
    assert usa_vocabulario([]) is False


def test_to_markdown_accion_reporta_tasa_de_vocabulario_con_guard():
    md = to_markdown(_df_eval_accion_min())
    assert "Uso de vocabulario de industria en el plan: 1/1" in md
    # Guard por columna: un df de modo acción SIN la métrica no rompe ni reporta.
    sin_col = _df_eval_accion_min().drop(columns=["usa_vocab"])
    md2 = to_markdown(sin_col)
    assert "Uso de vocabulario de industria" not in md2


def test_to_markdown_accion_incluye_columna_elicitacion():
    md = to_markdown(_df_eval_accion_min())
    encabezado = next(l for l in md.splitlines() if l.startswith("| PO |"))
    assert "| elicitación |" in encabezado
    # La celda de la fila lleva el texto de la elicitación, antes de la hipótesis.
    fila = next(l for l in md.splitlines() if l.startswith("| 100001 |"))
    assert fila.index("Como patrón de industria") < fila.index("Falta de producto")
    # El separador de la tabla tiene el mismo número de columnas que el encabezado.
    separador = md.splitlines()[md.splitlines().index(encabezado) + 1]
    assert encabezado.count("|") == separador.count("|")
