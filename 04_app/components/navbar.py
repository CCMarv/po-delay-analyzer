"""Navbar superior para navegación entre páginas — Fase 4 (User Personas)."""
import streamlit as st


def render_navbar(active_page: str = "home"):
    """Renderiza el navbar superior con navegación basada en User Personas.

    La app está bloqueada a tema claro (Fase 1); este navbar no incluye control de tema.

    Args:
        active_page: Página activa ('home', 'diego', 'ravi')
    """
    navbar_html = f"""
    <div class="top-navbar">
        <div class="navbar-brand">
            <span>📱</span>
            <span class="navbar-title">PO Delay Root Cause Analyzer</span>
        </div>
        <div class="navbar-links">
            <a href="/" class="nav-link {'active' if active_page == 'home' else ''}" target="_self">
               🏠 Home
            </a>
            <a href="/Exception_Workbench" class="nav-link {'active' if active_page == 'diego' else ''}" target="_self">
               🔍 Exception Workbench
            </a>
            <a href="/Network_Intelligence" class="nav-link {'active' if active_page == 'ravi' else ''}" target="_self">
               📊 Network Intelligence
            </a>
        </div>
    </div>
    """
    st.markdown(navbar_html, unsafe_allow_html=True)