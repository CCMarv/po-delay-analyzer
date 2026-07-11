"""Tarjeta de métrica reutilizable (sistema de diseño, ARD-17)."""
import streamlit as st


def metric_card(label: str, value, icon: str = "") -> None:
    """Renderiza una tarjeta de métrica con los tokens del sistema de diseño."""
    icon_prefix = f"{icon} " if icon else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <p class="metric-card__label">{icon_prefix}{label}</p>
            <p class="metric-card__value">{value}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )