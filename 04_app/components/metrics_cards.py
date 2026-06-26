"""Tarjetas de KPIs reutilizables."""
import streamlit as st


def metric_card(label: str, value, delta=None, icon: str = "📊"):
    """Muestra una tarjeta de métrica estilo dashboard."""
    st.metric(label=label, value=value, delta=delta, help=None)