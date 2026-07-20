"""
test_qr_service.py — QR del enlace al bot de Telegram en la landing (ARD-20).

`telegram_qr_png` es un helper puro (sin estado de Streamlit fuera del cache):
dado un username, genera un PNG en memoria. Aquí se verifica la forma del dato
(bytes, magic number de PNG, no vacío) y que usernames distintos producen
salidas distintas; el reveal por click (expander en 04_app/app.py) se verifica
a mano con la app corriendo (ver skill /verify).
"""
from services.qr_service import telegram_qr_png

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_devuelve_bytes_png_validos():
    png = telegram_qr_png("po_delay_analyzer_bot")
    assert isinstance(png, bytes)
    assert len(png) > 0
    assert png.startswith(_PNG_MAGIC)


def test_usernames_distintos_producen_qr_distinto():
    png_a = telegram_qr_png("bot_uno")
    png_b = telegram_qr_png("bot_dos")
    assert png_a != png_b
