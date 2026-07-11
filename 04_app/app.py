"""Entry point de la aplicación Streamlit — Landing Page Fase 4 (User Personas)."""
from pathlib import Path
import streamlit as st
from config import COLORS
from services.data_service import load_po_output
from components.navbar import render_navbar

# ── Configuración de página ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Home",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Navbar superior ─────────────────────────────────────────────────────────
render_navbar(active_page="home")

# ── Cargar CSS personalizado ────────────────────────────────────────────────
css_file = Path(__file__).parent / "assets" / "styles.css"
if css_file.exists():
    with open(css_file, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Carga de datos ──────────────────────────────────────────────────────────
df = load_po_output()

# ── Header con título ──────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-header">
        <h1> PO Delay Root Cause Analyzer</h1>
        <p style="color: #718096; font-size: 1.1rem;">
            Herramienta de análisis de causas raíz para POs tardíos
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── KPIs globales ───────────────────────────────────────────────────────────
st.markdown("### 📊 Resumen del Dataset")
col1, col2 = st.columns(2)
with col1:
    st.metric(label="POs tardíos procesados", value=len(df))
with col2:
    # Distribución por severidad
    severity_counts = df["severity"].value_counts()
    high_pct = (severity_counts.get("HIGH", 0) / len(df) * 100) if len(df) > 0 else 0
    st.metric(label="% Severidad Alta", value=f"{high_pct:.1f}%")

st.markdown("---")

# ── Sección de Vistas por User Persona ──────────────────────────────────────
st.markdown(
    """
    <div class="dashboards-section">
        <h2>▤ Vistas de Análisis</h2>
        <p style="color: #4a5568; font-size: 1rem;">
            La herramienta ofrece dos superficies de análisis según el modo de consumo:
            consulta individual de excepciones o inteligencia agregada de red.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Tarjetas de vistas en 2 columnas
col_diego, col_ravi = st.columns(2)

# ── Vista Diego: Exception Workbench ────────────────────────────────────────
with col_diego:
    st.markdown(
        """
        <div class="dashboard-card" style="min-height: 320px; display: flex; flex-direction: column;">
            <h3>🔍 Exception Workbench</h3>
            <h4>Consulta Individual de POs</h4>
            <p style="flex-grow: 1;">
                <strong>Para:</strong> Coordinadores de excepciones inbound<br><br>
                Analiza un PO tardío a la vez: timeline reconstruido, diagnóstico LLM, 
                validación de causa raíz y acciones recomendadas. Ideal para cerrar 
                excepciones caso por caso con evidencia completa.
            </p>
            <ul style="color: #4a5568; font-size: 0.9rem; margin: 1rem 0; padding-left: 1.5rem;">
                <li>Timeline del lifecycle del PO</li>
                <li>Explicación y acción del LLM</li>
                <li>Flag de desacuerdo con reason humano</li>
                <li>Indicador de confianza del diagnóstico</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Abrir Exception Workbench →", key="btn_diego", use_container_width=True):
        st.switch_page("pages/1_🔍_Exception_Workbench.py")

# ── Vista Ravi: Network Intelligence ────────────────────────────────────────
with col_ravi:
    st.markdown(
        """
        <div class="dashboard-card" style="min-height: 320px; display: flex; flex-direction: column;">
            <h3>📊 Network Intelligence</h3>
            <h4>Inteligencia Agregada de Red</h4>
            <p style="flex-grow: 1;">
                <strong>Para:</strong> Analistas de supply chain y reporting<br><br>
                Visualiza patrones sistémicos en la población de POs tardíos: 
                distribución por etapa, severidad, tasa de desacuerdo y tendencias. 
                Genera inteligencia accionable para decisiones estructurales.
            </p>
            <ul style="color: #4a5568; font-size: 0.9rem; margin: 1rem 0; padding-left: 1.5rem;">
                <li>Distribución Vendor/Carrier/DC/Indeterminado</li>
                <li>Scorecards por entidad</li>
                <li>Tasa de desacuerdo AI vs humano</li>
                <li>Drill-down a casos individuales</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Abrir Network Intelligence →", key="btn_ravi", use_container_width=True):
        st.switch_page("pages/2__Network_Intelligence.py")

# ── Footer ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
    <div class="simple-footer">
        <p>Supply Chain AI · Fase 4 — Demo + Evaluación Final</p>
        <p>Artefacto: po_output.csv (247 POs tardíos) · Contrato F3→F4</p>
    </div>
    """,
    unsafe_allow_html=True,
)