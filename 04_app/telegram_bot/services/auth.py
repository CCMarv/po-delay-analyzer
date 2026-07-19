"""Autenticación y perfiles de usuario para el bot de Telegram."""
from config import TELEGRAM_USER_WHITELIST, TELEGRAM_RAVI_USER_IDS


def is_authorized(user_id: int) -> bool:
    """Verifica si un user_id de Telegram está autorizado a usar el bot.

    Fail-closed: si la whitelist está vacía, NADIE está autorizado. Solo los
    IDs listados en TELEGRAM_USER_WHITELIST pueden usar el bot.
    """
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
