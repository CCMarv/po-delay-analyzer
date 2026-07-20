"""Entry point de la aplicación Streamlit — Landing Page Fase 4 (User Personas).

Restilada desde el mockup "Home Landing" (ARD-23): hero con KPIs, 2 cards de
vista con acento superior, card de canal adicional (Telegram, ARD-20) y pie
de procedencia (ARD-22 §7 T3).
"""
from pathlib import Path
import streamlit as st
from config import COL_SEVERITY, TELEGRAM_BOT_USERNAME, dataset_cutoff_date
from services.data_service import load_po_output
from services.qr_service import telegram_qr_png
from components.navbar import render_navbar
from components.theme_toggle import inject_theme_css

# ── Configuración de página ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Home",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Navbar superior ─────────────────────────────────────────────────────────
render_navbar(active_page="home")

# ── CSS de tema (tokens del sistema de diseño, ARD-17) ──────────────────────
inject_theme_css()

# ── Carga de datos ──────────────────────────────────────────────────────────
df = load_po_output()

# ── Header con título ──────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-header" style="text-align:center;">
        <h1>PO Delay Root Cause Analyzer</h1>
        <p style="color: var(--text-muted); font-size: 1.1rem;">
            Herramienta de análisis de causas raíz para POs tardíos
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── KPIs globales (hero) ────────────────────────────────────────────────────
total_pos = len(df)
severity_counts = df[COL_SEVERITY].value_counts()
high_pct = (severity_counts.get("HIGH", 0) / total_pos * 100) if total_pos > 0 else 0.0

col1, col2 = st.columns(2)
with col1:
    st.markdown(
        f"""
        <div class="landing-kpi">
            <div class="landing-kpi__value">{total_pos}</div>
            <div class="landing-kpi__label">POs tardíos procesados</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        f"""
        <div class="landing-kpi">
            <div class="landing-kpi__value">{high_pct:.0f}%</div>
            <div class="landing-kpi__label">% Severidad Alta</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Sección de Vistas por User Persona ──────────────────────────────────────
st.markdown(
    """
    <div class="dashboards-section">
        <h2>Vistas de Análisis</h2>
        <p style="color: var(--text-secondary); font-size: 1rem;">
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
        <div class="dashboard-card">
            <h3>🔍 Exception Workbench</h3>
            <h4>Consulta Individual de POs · Diego, coordinador de excepciones inbound</h4>
            <p style="flex-grow: 1;">
                Revisión caso por caso de cada PO tardío: qué pasó, dónde y qué explica el LLM.
            </p>
            <ul style="color: var(--text-secondary); font-size: 0.9rem; margin: 1rem 0; padding-left: 1.5rem;">
                <li>Timeline del lifecycle del PO</li>
                <li>Explicación y acción sugerida del LLM</li>
                <li>Flag de desacuerdo con el reason humano</li>
                <li>Indicador de confianza</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Abrir Exception Workbench →", key="btn_diego", width="stretch"):
        st.switch_page("pages/1_🔍_Exception_Workbench.py")

# ── Vista Ravi: Network Intelligence ────────────────────────────────────────
with col_ravi:
    stage_bullet = " / ".join(
        f'<span class="stage-chip"><span class="stage-chip__dot stage-chip__dot--{key}"></span>{label}</span>'
        for key, label in (
            ("vendor", "Vendor"), ("carrier", "Carrier"),
            ("dc", "DC"), ("indeterminado", "Indeterminado"),
        )
    )
    st.markdown(
        f"""
        <div class="dashboard-card">
            <h3>📊 Network Intelligence</h3>
            <h4>Inteligencia Agregada de Red · Ravi, analista de supply chain</h4>
            <p style="flex-grow: 1;">
                Patrones sistémicos sobre toda la población de POs tardíos del corte.
            </p>
            <ul style="color: var(--text-secondary); font-size: 0.9rem; margin: 1rem 0; padding-left: 1.5rem;">
                <li>Distribución {stage_bullet}</li>
                <li>Scorecards por entidad</li>
                <li>Tasa de desacuerdo AI vs humano</li>
                <li>Drill-down a casos individuales</li>
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button("Abrir Network Intelligence →", key="btn_ravi", width="stretch"):
        st.switch_page("pages/2_📊_Network_Intelligence.py")

# ── Canal adicional: bot de Telegram (ARD-20, enlace de solo lectura) ───────
if TELEGRAM_BOT_USERNAME:
    telegram_link = (
        f'<a href="https://t.me/{TELEGRAM_BOT_USERNAME}" target="_blank" '
        f'class="telegram-card__link">Consultar por Telegram</a>'
    )
else:
    telegram_link = ""

st.markdown(
    f"""
    <div class="telegram-card">
        <span style="font-size:1.5rem;">✈️</span>
        <div style="flex:1;">
            <div class="telegram-card__title">Canal adicional: bot de Telegram</div>
            <div class="telegram-card__desc">
                Comandos fijos de lectura para consultar un PO o métricas del corte desde
                Telegram. No es un chat conversacional.
            </div>
        </div>
        {telegram_link}
    </div>
    """,
    unsafe_allow_html=True,
)
if TELEGRAM_BOT_USERNAME:
    with st.expander("Mostrar QR para abrir el bot en Telegram"):
        st.image(telegram_qr_png(TELEGRAM_BOT_USERNAME), width=160)

# ── Footer de procedencia (ARD-22 §7 T3) ────────────────────────────────────
cutoff = dataset_cutoff_date(df)
cutoff_str = cutoff.strftime("%Y-%m-%d") if cutoff is not None else "N/A"
st.markdown(
    f"""
    <div class="simple-footer simple-footer--split">
        <span>Corte del dataset: <span class="timestamp">{cutoff_str}</span> ·
            Origen: po_output.csv (Fase 3, corte histórico)</span>
        <span>Solo lectura</span>
    </div>
    """,
    unsafe_allow_html=True,
)
