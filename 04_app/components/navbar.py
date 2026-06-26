"""Navbar superior para navegación entre páginas."""
import streamlit as st


def render_navbar(active_page: str = "home"):
    """Renderiza el navbar superior con navegación entre páginas.
    
    Args:
        active_page: Página activa ('home', 'vendor', 'carrier', 'dc')
    """
    navbar_html = f"""
    <div class="top-navbar">
        <div class="navbar-brand">
            <span>📱</span>
            <span class="navbar-title">PO Delay Root Cause Analyzer</span>
        </div>
        <div class="navbar-links">
            <a href="/" class="nav-link {'active' if active_page == 'home' else ''}">
                🏠 Home
            </a>
            <a href="/Vendor_Management" class="nav-link {'active' if active_page == 'vendor' else ''}">
                📦 Vendor Management
            </a>
            <a href="/Carrier_Logistics" class="nav-link {'active' if active_page == 'carrier' else ''}">
                🚛 Carrier Logistics
            </a>
            <a href="/DC_Operations" class="nav-link {'active' if active_page == 'dc' else ''}">
                🏭 DC Operations
            </a>
        </div>
    </div>
    """
    st.markdown(navbar_html, unsafe_allow_html=True)