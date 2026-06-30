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
from eval_quality import ANCHOR_TEMP, _temp_suffix, resolve_temperature
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
