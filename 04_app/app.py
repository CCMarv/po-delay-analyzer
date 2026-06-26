"""Entry point de la aplicación Streamlit — Landing Page con análisis LLM."""
from pathlib import Path
import streamlit as st
import pandas as pd
from config import COLORS, LLM_OUT_CSV
from services.data_service import load_classified_data, load_llm_data
from services.metrics_service import total_pos, total_tardios, pct_tardios
from components.navbar import render_navbar
from components.metrics_cards import metric_card
from utils.helpers import load_css

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
load_css()

# ── Carga de datos ──────────────────────────────────────────────────────────
@st.cache_data
def get_llm_data():
    """Carga datos LLM con caching."""
    return load_llm_data()

# Cargar datos clasificados (para KPIs globales)
df_classified = load_classified_data()

# Cargar datos LLM
try:
    df_llm = get_llm_data()
except FileNotFoundError as e:
    st.error(f"❌ {e}")
    st.stop()

# ── Header con título ──────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-header">
        <h1>🔍 PO Delay Root Cause Analyzer</h1>
        <p style="color: #718096; font-size: 1.1rem;">
            Análisis inteligente de causas raíz con IA
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── KPIs globales (del pipeline completo) ──────────────────────────────────
st.markdown("### 📊 Resumen Global del Pipeline")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(label="POs totales", value=total_pos(df_classified))
with col2:
    st.metric(label="POs tardíos", value=total_tardios(df_classified))
with col3:
    st.metric(label="% tardíos", value=f"{pct_tardios(df_classified):.1f}%")

st.markdown("---")

# ── Selector de PO ─────────────────────────────────────────────────────────
st.markdown("### 🎯 Análisis Detallado por PO")

# Obtener lista única de POs disponibles en el CSV LLM
po_list = sorted(df_llm["PO_NBR"].unique().tolist())

# Selector desplegable
selected_po = st.selectbox(
    "Selecciona un número de PO para ver su análisis:",
    options=po_list,
    format_func=lambda x: f"PO #{x}",
    index=0,  # Default: primer PO
)

# Filtrar datos del PO seleccionado
po_data = df_llm[df_llm["PO_NBR"] == selected_po].iloc[0]

# ── Cards de análisis LLM ──────────────────────────────────────────────────
st.markdown("### 🤖 Análisis de Inteligencia Artificial")

col1, col2, col3, col4, col5 = st.columns(5)

# Card 1: Origen del Retraso
with col1:
    st.markdown(
        f"""
        <div class="llm-card" style="border-left: 4px solid #4299e1;">
            <div class="llm-icon">🔍</div>
            <h4>Origen del Retraso</h4>
            <p class="llm-text">{po_data['llm_causa_raiz']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Card 2: Solución Sugerida
with col2:
    st.markdown(
        f"""
        <div class="llm-card" style="border-left: 4px solid #48bb78;">
            <div class="llm-icon">🛠️</div>
            <h4>Solución Sugerida</h4>
            <p class="llm-text">{po_data['llm_accion_recomendada']}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Card 3: Prioridad de Atención
with col3:
    severidad = po_data['llm_severidad']
    color_sev = {
        "HIGH": "#e53e3e",
        "MEDIUM": "#dd6b20",
        "LOW": "#38a169",
    }.get(severidad, "#718096")
    
    st.markdown(
        f"""
        <div class="llm-card" style="border-left: 4px solid {color_sev};">
            <div class="llm-icon">🚨</div>
            <h4>Prioridad de Atención</h4>
            <p class="llm-badge" style="background-color: {color_sev}20; color: {color_sev};">
                {severidad}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Card 4: Consistencia del Proveedor
with col4:
    coincide = po_data['llm_coincide_con_reason']
    icono = "✅" if coincide else "⚠️"
    texto = "Consistente" if coincide else "Inconsistente"
    color = "#48bb78" if coincide else "#f56565"
    
    st.markdown(
        f"""
        <div class="llm-card" style="border-left: 4px solid {color};">
            <div class="llm-icon">{icono}</div>
            <h4>Consistencia del Proveedor</h4>
            <p class="llm-badge" style="background-color: {color}20; color: {color};">
                {texto}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Card 5: Fiabilidad del Diagnóstico
with col5:
    confianza = po_data['llm_confianza']
    confianza_pct = int(confianza * 100) if confianza <= 1 else int(confianza)
    
    # Determinar color según nivel de confianza
    if confianza_pct >= 80:
        color_conf = "#48bb78"  # Verde
    elif confianza_pct >= 60:
        color_conf = "#ecc94b"  # Amarillo
    else:
        color_conf = "#f56565"  # Rojo
    
    st.markdown(
        f"""
        <div class="llm-card" style="border-left: 4px solid {color_conf};">
            <div class="llm-icon">🎯</div>
            <h4>Fiabilidad del Diagnóstico</h4>
            <p class="llm-badge" style="background-color: {color_conf}20; color: {color_conf}; font-size: 1.2rem;">
                {confianza_pct}%
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Información adicional del PO seleccionado ──────────────────────────────
st.markdown("---")
st.markdown("### 📋 Información Complementaria del PO")

col_info1, col_info2, col_info3 = st.columns(3)

with col_info1:
    st.info(f"""
    **Vendor:** {po_data.get('VENDOR_NAME', 'N/A')}  
    **Carrier:** {po_data.get('CARRIER_PARTY_NAME', 'N/A')}  
    **DC:** {po_data.get('DC_LOC_NAME', 'N/A')}
    """)

with col_info2:
    st.info(f"""
    **Status:** {po_data.get('PO_STATUS_CD', 'N/A')}  
    **Delay Days:** {po_data.get('delay_days_calc', 0):.1f} días  
    **Severity:** {po_data.get('severity', 'N/A')}
    """)

with col_info3:
    reason_cd = po_data.get('REASON_CD', 'N/A')
    reason_dsc = po_data.get('REASON_DSC', 'N/A')
    st.info(f"""
    **Reason Code:** {reason_cd}  
    **Description:** {reason_dsc}
    """)

# ── Sección Dashboards ──────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<div class="dashboards-section"><h2>▤ Dashboards Especializados</h2></div>', unsafe_allow_html=True)

st.markdown(
    "Cada dashboard consume el mismo DataFrame clasificado. "
    "Sin duplicar lógica — solo cambia el foco de negocio."
)

# Tarjetas de dashboards en 3 columnas
col_v, col_c, col_d = st.columns(3)

with col_v:
    st.markdown(
        """
        <div class="dashboard-card" style="min-height: 280px; display: flex; flex-direction: column;">
            <h3>📦 Vendor Management</h3>
            <h4>Scorecard de vendors</h4>
            <p style="flex-grow: 1;">
                Ranking objetivo por STA push, short shipments y exceso acumulado.
                Evidencia dura para renegociar SLAs y aplicar chargebacks.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Abrir dashboard →", key="btn_vendor", use_container_width=True):
        st.switch_page("pages/1_📦_Vendor_Management.py")

with col_c:
    st.markdown(
        """
        <div class="dashboard-card" style="min-height: 280px; display: flex; flex-direction: column;">
            <h3>🚛 Carrier Logistics</h3>
            <h4>Carrier adherence</h4>
            <p style="flex-grow: 1;">
                Carrier miss, appointment adherence y heatmap carrier × DC.
                Distingue "miss real" de "sin datos de llegada" (problema de visibilidad).
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Abrir dashboard →", key="btn_carrier", use_container_width=True):
        st.switch_page("pages/2_🚛_Carrier_Logistics.py")

with col_d:
    st.markdown(
        """
        <div class="dashboard-card" style="min-height: 280px; display: flex; flex-direction: column;">
            <h3>🏭 DC Operations</h3>
            <h4>Throughput de muelle</h4>
            <p style="flex-grow: 1;">
                Control de yard congestion y dock backlog. Defensa contra culpas injustas
                cuando el carrier o vendor son los responsables reales.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Abrir dashboard →", key="btn_dc", use_container_width=True):
        st.switch_page("pages/3_🏭_DC_Operations.py")

# ── Footer simple ───────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
    <div class="simple-footer">
        <p>Supply Chain AI · June 2026</p>
        <p>Análisis LLM disponible · 5 POs de muestra</p>
    </div>
    """,
    unsafe_allow_html=True,
)