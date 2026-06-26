"""Widgets de filtro adicionales (fecha, severidad, etc.)."""
import streamlit as st


def severity_filter(key="sev_filter"):
    """Selector de severidad."""
    return st.selectbox("Severidad", ["ALL", "HIGH", "MEDIUM", "LOW"], key=key)


def stage_filter(df, key="stage_filter"):
    """Selector de stage_primary."""
    stages = sorted(df["stage_primary"].dropna().unique().tolist())
    return st.selectbox("Etapa primaria", ["ALL"] + stages, key=key)