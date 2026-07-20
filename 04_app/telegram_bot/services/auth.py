"""Autenticación y perfiles de usuario para el bot de Telegram."""
from config import TELEGRAM_USER_WHITELIST, TELEGRAM_RAVI_USER_IDS, DEMO_MODE


def is_authorized(user_id: int) -> bool:
    """Verifica si un user_id de Telegram está autorizado a usar el bot.

    Fail-closed por default: si la whitelist está vacía, NADIE está autorizado.
    Solo los IDs listados en TELEGRAM_USER_WHITELIST pueden usar el bot.

    Excepción: si DEMO_MODE está activo, siempre devuelve True — bypass total
    pensado para demos/presentación, no para producción (ver ARD-20).
    """
    if DEMO_MODE:
        return True
    return user_id in TELEGRAM_USER_WHITELIST


def get_profile(user_id: int) -> str:
    """Devuelve el perfil del usuario: 'ravi' o 'diego'.

    Basado en TELEGRAM_RAVI_USER_IDS del .env.
    """
    if TELEGRAM_RAVI_USER_IDS and user_id in TELEGRAM_RAVI_USER_IDS:
        return "ravi"
    return "diego"


def get_profile_name(user_id: int) -> str:
    """Alias de get_profile — devuelve 'ravi' o 'diego'."""
    return get_profile(user_id)
