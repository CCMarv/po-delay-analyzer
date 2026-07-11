"""Network Intelligence — Vista de Ravi (Supply-Chain Analyst).

Reporte agregado de la población de POs tardíos con distribución por etapa,
severidad, y tasa de desacuerdo AI vs humano.
Ticket #103: Panel de métricas agregadas
"""
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from config import COLORS, COL_STAGE, COL_SEVERITY, COL_REASON_DSC, COL_LLM_COINCIDE
from services.data_service import load_po_output
from components.navbar import render_navbar

# ── Configuración de página ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Network Intelligence",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Navbar superior ─────────────────────────────────────────────────────────
render_navbar(active_page="ravi")

# ── Cargar CSS personalizado ────────────────────────────────────────────────
css_file = Path(__file__).parent.parent / "assets" / "styles.css"
if css_file.exists():
    with open(css_file, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ─ Carga de datos ──────────────────────────────────────────────────────────
df = load_po_output()

# ── Header ──────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-header">
        <h1>📊 Network Intelligence</h1>
        <p style="color: #718096; font-size: 1.1rem;">
            Inteligencia agregada de red — Patrones sistémicos en POs tardíos
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── KPIs globales ───────────────────────────────────────────────────────────
st.markdown("### 📈 Resumen de la Red")

total_pos = len(df)
stage_counts = df[COL_STAGE].value_counts()
severity_counts = df[COL_SEVERITY].value_counts()

# Calcular tasa de desacuerdo
coincide_col = COL_LLM_COINCIDE
if coincide_col in df.columns:
    coincide_values = df[coincide_col].dropna()
    total_with_validation = len(coincide_values)
    disagreements = (coincide_values == False).sum()
    agreement_rate = ((coincide_values == True).sum() / total_with_validation * 100) if total_with_validation > 0 else 0
else:
    total_with_validation = 0
    disagreements = 0
    agreement_rate = 0

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="Total POs Tardíos", value=total_pos)
with col2:
    st.metric(label="Etapa #1", value=f"{stage_counts.index[0]} ({stage_counts.iloc[0]})")
with col3:
    st.metric(label="Severidad Alta", value=f"{severity_counts.get('HIGH', 0)} ({severity_counts.get('HIGH', 0)/total_pos*100:.1f}%)")
with col4:
    st.metric(label="Tasa de Acuerdo AI", value=f"{agreement_rate:.1f}%")

st.markdown("---")

# ── Gráfico 1: Distribución por Etapa ──────────────────────────────────────
st.markdown("###  Distribución por Etapa")

col_chart1, col_chart2 = st.columns(2)

with col_chart1:
    # Pie chart
    fig_pie = px.pie(
        stage_counts.reset_index(),
        names='stage',
        values='count',
        title="Reparto de Etapas (Vendor/Carrier/DC/Indeterminado)",
        color='stage',
        color_discrete_map=COLORS
    )
    fig_pie.update_layout(height=400)
    st.plotly_chart(fig_pie, use_container_width=True)

with col_chart2:
    # Bar chart
    fig_bar = px.bar(
        stage_counts.reset_index(),
        x='stage',
        y='count',
        title="Conteo por Etapa",
        color='stage',
        color_discrete_map=COLORS
    )
    fig_bar.update_layout(height=400)
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

# ── Gráfico 2: Distribución por Severidad ─────────────────────────────────
st.markdown("### 🚨 Distribución por Severidad")

col_sev1, col_sev2 = st.columns(2)

# Preparar datos de severidad
severity_counts = df['severity'].value_counts().reset_index()
severity_counts.columns = ['severity', 'count']  # Asegurar nombres correctos

with col_sev1:
    # Pie chart - CORREGIDO
    fig_sev_pie = px.pie(
        severity_counts,
        names='severity',     # ← Columna de categorías
        values='count',       # ← Columna de valores
        title="Distribución de Severidad",
        color='severity',
        color_discrete_map={
            'HIGH': COLORS['high'],
            'MEDIUM': COLORS['medium'],
            'LOW': COLORS['low']
        }
    )
    fig_sev_pie.update_layout(height=400)
    st.plotly_chart(fig_sev_pie, use_container_width=True)

with col_sev2:
    # Tabla de severidad - CORREGIDO
    st.markdown("#### Detalle de Severidad")
    sev_df = severity_counts.copy()
    sev_df.columns = ['Severidad', 'Cantidad']
    sev_df['Porcentaje'] = (sev_df['Cantidad'] / total_pos * 100).round(1)
    st.dataframe(sev_df, use_container_width=True)

# ── Métricas de Validación ──────────────────────────────────────────────────
st.markdown("### ✅ Métricas de Validación")

col_val1, col_val2, col_val3 = st.columns(3)

with col_val1:
    st.markdown(
        f"""
        <div class="custom-card" style="border-left: 4px solid #48bb78;">
            <h4 style="margin: 0 0 0.5rem 0; color: #718096;">Tasa de Acuerdo</h4>
            <p style="margin: 0; font-size: 2rem; font-weight: 700; color: #48bb78;">
                {agreement_rate:.1f}%
            </p>
            <p style="margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #718096;">
                AI vs Reason Humano
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_val2:
    st.markdown(
        f"""
        <div class="custom-card" style="border-left: 4px solid #4299e1;">
            <h4 style="margin: 0 0 0.5rem 0; color: #718096;">POs con Validación</h4>
            <p style="margin: 0; font-size: 2rem; font-weight: 700; color: #4299e1;">
                {total_with_validation}
            </p>
            <p style="margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #718096;">
                de {total_pos} totales
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_val3:
    st.markdown(
        f"""
        <div class="custom-card" style="border-left: 4px solid #f56565;">
            <h4 style="margin: 0 0 0.5rem 0; color: #718096;">Desacuerdos</h4>
            <p style="margin: 0; font-size: 2rem; font-weight: 700; color: #f56565;">
                {disagreements}
            </p>
            <p style="margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #718096;">
                Casos para revisar
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.markdown("---")

# ── Tabla de POs con Desacuerdo ─────────────────────────────────────────────
if disagreements > 0:
    st.markdown("### ⚠️ POs con Desacuerdo AI vs Humano")
    
    df_disagreement = df[df[COL_LLM_COINCIDE] == False].copy()
    
    st.dataframe(
        df_disagreement[[COL_STAGE, COL_SEVERITY, COL_REASON_DSC, COL_LLM_COINCIDE]],
        use_container_width=True
    )

# ── Footer ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
    <div class="simple-footer">
        <p>Network Intelligence · Vista de Ravi (Supply-Chain Analyst)</p>
        <p>Reporte agregado de patrones sistémicos en la red de POs tardíos</p>
    </div>
    """,
    unsafe_allow_html=True,
)