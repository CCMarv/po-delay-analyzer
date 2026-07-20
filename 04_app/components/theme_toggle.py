"""Inyección del CSS del sistema de diseño (ARD-17).

La app está bloqueada a tema CLARO (Fase 1): los tokens `:root` viven en `styles.css`
junto con las reglas de componentes. El modo oscuro se difiere a la export estática
(Fase 2).
"""
from pathlib import Path
import streamlit as st


def inject_theme_css():
    """Inyecta `styles.css` (tokens `:root` + reglas de componentes)."""
    styles_css_path = Path(__file__).parent.parent / "assets" / "styles.css"
    if styles_css_path.exists():
        with open(styles_css_path, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
