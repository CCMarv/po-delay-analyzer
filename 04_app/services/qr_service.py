"""QR del enlace al bot de Telegram para la landing (ARD-20, card de canal adicional).

El QR es un derivado barato del handle público del bot: se genera en memoria, no se
persiste a `assets/` (evita un artefacto más que mantener sincronizado).
"""
import io

import qrcode
import streamlit as st


@st.cache_data(show_spinner=False)
def telegram_qr_png(username: str) -> bytes:
    """PNG del QR que apunta a `https://t.me/<username>`.

    Colores fijos (negro sobre blanco) independientes del tema claro/oscuro de la
    app: un QR de bajo contraste puede fallar al escanear, así que no sigue la
    paleta de la interfaz (ver `config.STAGE_COLORS` / `current_theme`).

    Cacheado por `username`: mismo bot → mismo PNG, no se regenera en cada rerun.
    """
    url = f"https://t.me/{username}"
    img = qrcode.make(url, box_size=8, border=2)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
