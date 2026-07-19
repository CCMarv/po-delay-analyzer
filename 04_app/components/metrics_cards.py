"""Tarjeta de métrica reutilizable (sistema de diseño, ARD-17)."""
from html import escape
import streamlit as st


def metric_card(label: str, value, icon: str = "") -> None:
    """Renderiza una tarjeta de métrica con los tokens del sistema de diseño.

    label/value se escapan: value recibe nombres de VENDOR/CARRIER/DC del
    dataset, que no son un vocabulario cerrado y se interpolan sin sanitizar.
    """
    icon_prefix = f"{icon} " if icon else ""
    label_html = escape(str(label))
    value_html = escape(str(value))
    st.markdown(
        f"""
        <div class="metric-card">
            <p class="metric-card__label">{icon_prefix}{label_html}</p>
            <p class="metric-card__value">{value_html}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )