"""
test_telegram_auth.py — modo demo del bot de Telegram (ARD-20, DEMO_MODE).

`is_authorized` es fail-closed por default (whitelist vacía = nadie
autorizado). `DEMO_MODE` es una excepción explícita, pensada solo para demos:
si está activo, el bypass es total (cualquier user_id pasa, incluida
whitelist vacía). Aquí se verifica que el bypass funciona y que, sin el flag,
el comportamiento fail-closed original no cambia.

`telegram_bot/` no está en el pythonpath global de pytest (a propósito: su
config.py colisiona de nombre con 04_app/config.py — ver PYTHONPATH aislado
del paso "Import smoke check (telegram bot)" en .github/workflows/ci.yml).
Se inserta su ruta solo dentro de este módulo. `services` también colisiona
(04_app/services/ vs. telegram_bot/services/): si otro test de la suite ya
importó `services` (el de 04_app), Python lo deja cacheado en sys.modules y
`import services.auth` reusaría ese paquete equivocado. Por eso la fixture
purga `config`/`services`/`services.*` de sys.modules antes de importar, y
además recarga tras cada cambio de env var porque DEMO_MODE se fija a nivel
de import.
"""
import importlib
import sys
from pathlib import Path

import pytest

_TELEGRAM_BOT_DIR = Path(__file__).resolve().parent.parent / "04_app" / "telegram_bot"


def _purgar_modulos_en_conflicto():
    for nombre in list(sys.modules):
        if nombre == "config" or nombre == "services" or nombre.startswith("services."):
            del sys.modules[nombre]


@pytest.fixture
def telegram_auth_modules(monkeypatch):
    """Importa config.py/auth.py del bot de Telegram, aislados de sus tocayos
    de 04_app/ y del .env real (ver docstring del módulo).

    Cada test debe fijar las env vars que necesite con monkeypatch ANTES de
    usar los módulos que devuelve esta fixture — el .env real puede traer un
    TELEGRAM_USER_WHITELIST en un formato que config.py no sabe parsear.
    """
    monkeypatch.syspath_prepend(str(_TELEGRAM_BOT_DIR))
    # Neutralizar por adelantado la whitelist real (formato inválido en este
    # repo local) para que el import inicial sea seguro incluso si un test no
    # la toca explícitamente.
    monkeypatch.setenv("TELEGRAM_USER_WHITELIST", "")

    _purgar_modulos_en_conflicto()
    import config as telegram_config
    import services.auth as telegram_auth
    yield telegram_config, telegram_auth

    # Limpieza: los módulos quedan cacheados con el .env de prueba: se purgan
    # para que el próximo import (de este test o de otro) resuelva de nuevo
    # desde sys.path, sin arrastrar el estado de DEMO_MODE de este test.
    _purgar_modulos_en_conflicto()


def test_fail_closed_sin_demo_mode(monkeypatch, telegram_auth_modules):
    monkeypatch.delenv("DEMO_MODE", raising=False)
    monkeypatch.setenv("TELEGRAM_USER_WHITELIST", "")
    config, auth = telegram_auth_modules
    importlib.reload(config)
    importlib.reload(auth)

    assert config.DEMO_MODE is False
    assert auth.is_authorized(999999999) is False


def test_demo_mode_autoriza_cualquier_usuario(monkeypatch, telegram_auth_modules):
    monkeypatch.setenv("DEMO_MODE", "true")
    monkeypatch.setenv("TELEGRAM_USER_WHITELIST", "")
    config, auth = telegram_auth_modules
    importlib.reload(config)
    importlib.reload(auth)

    assert config.DEMO_MODE is True
    assert auth.is_authorized(999999999) is True


@pytest.mark.parametrize("valor", ["1", "true", "True", "TRUE", "yes", "YES"])
def test_parseo_acepta_variantes_de_verdadero(monkeypatch, telegram_auth_modules, valor):
    monkeypatch.setenv("DEMO_MODE", valor)
    config, _ = telegram_auth_modules
    importlib.reload(config)

    assert config.DEMO_MODE is True


@pytest.mark.parametrize("valor", ["", "0", "false", "no", "algo_random"])
def test_parseo_trata_el_resto_como_falso(monkeypatch, telegram_auth_modules, valor):
    monkeypatch.setenv("DEMO_MODE", valor)
    config, _ = telegram_auth_modules
    importlib.reload(config)

    assert config.DEMO_MODE is False
