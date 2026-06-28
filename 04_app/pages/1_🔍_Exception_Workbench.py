"""Exception Workbench — Vista de Diego (Inbound Exception Coordinator).

Consulta individual de un PO tardío con timeline, diagnóstico LLM y validación.
"""
from pathlib import Path
import streamlit as st
import pandas as pd
from config import COLORS, COL_PO, COL_STAGE, COL_SEVERITY, COL_EXPLANATION, COL_ACTION
from config import COL_PO_DT, COL_STA_DT, COL_APPROVED_DT, COL_TRAILER_ARRIVE_DT
from config import COL_CHECKIN_DT, COL_CHECKOUT_DT, COL_RECPT_DT
from config import COL_HOT_PO_FLAG, COL_IS_SHORT_SHIP, COL_REASON_DSC, COL_LLM_COINCIDE
from services.data_service import load_po_output, get_po_by_number, get_unique_po_list
from components.navbar import render_navbar

# ── Configuración de página ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Exception Workbench",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Navbar superior ─────────────────────────────────────────────────────────
render_navbar(active_page="diego")

# ── Cargar CSS personalizado ────────────────────────────────────────────────
css_file = Path(__file__).parent.parent / "assets" / "styles.css"
if css_file.exists():
    with open(css_file) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Carga de datos ──────────────────────────────────────────────────────────
df = load_po_output()

# ── Header ──────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-header">
        <h1>🔍 Exception Workbench</h1>
        <p style="color: #718096; font-size: 1.1rem;">
            Consulta individual de POs tardíos — Timeline + Diagnóstico + Validación
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Selector de PO ──────────────────────────────────────────────────────────
st.markdown("### 📋 Seleccionar PO")

po_list = get_unique_po_list(df)
selected_po = st.selectbox(
    "Número de PO:",
    options=po_list,
    format_func=lambda x: f"PO #{x}",
    index=0,
)

# Obtener datos del PO seleccionado
po_data = get_po_by_number(df, selected_po)

# ── Panel de diagnóstico (arriba) ───────────────────────────────────────────
st.markdown("---")
st.markdown("### 🎯 Diagnóstico del PO")

col_diag1, col_diag2, col_diag3, col_diag4 = st.columns(4)

# Stage
with col_diag1:
    stage = po_data[COL_STAGE]
    color_stage = COLORS.get(stage.lower() if pd.notna(stage) else "indeterminado", "#718096")
    st.markdown(
        f"""
        <div class="custom-card" style="border-left: 4px solid {color_stage};">
            <h4 style="margin: 0 0 0.5rem 0; color: #718096;">Etapa</h4>
            <p style="margin: 0; font-size: 1.25rem; font-weight: 700; color: {color_stage};">
                {stage if pd.notna(stage) else "N/A"}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Severidad
with col_diag2:
    severity = po_data[COL_SEVERITY]
    color_sev = COLORS.get(severity.lower() if pd.notna(severity) else "medium", "#718096")
    st.markdown(
        f"""
        <div class="custom-card" style="border-left: 4px solid {color_sev};">
            <h4 style="margin: 0 0 0.5rem 0; color: #718096;">Severidad</h4>
            <p style="margin: 0; font-size: 1.25rem; font-weight: 700; color: {color_sev};">
                {severity if pd.notna(severity) else "N/A"}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Flag de desacuerdo (PROMINENTE)
with col_diag3:
    coincide = po_data.get(COL_LLM_COINCIDE, None)
    if pd.notna(coincide):
        if coincide:
            icon = "✅"
            text = "Consistente"
            color = "#48bb78"
        else:
            icon = "⚠️"
            text = "Desacuerdo"
            color = "#f56565"
    else:
        icon = "❓"
        text = "N/A"
        color = "#718096"
    
    st.markdown(
        f"""
        <div class="custom-card" style="border-left: 4px solid {color}; min-height: 120px; display: flex; flex-direction: column; justify-content: center;">
            <h4 style="margin: 0 0 0.75rem 0; color: #718096; font-size: 1rem; font-weight: 600;">
                Validación AI vs Humano
            </h4>
            <p style="margin: 0; font-size: 1.5rem; font-weight: 700; color: {color};">
                {icon} {text}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# Reason humano
with col_diag4:
    reason = po_data.get(COL_REASON_DSC, "N/A")
    st.markdown(
        f"""
        <div class="custom-card">
            <h4 style="margin: 0 0 0.5rem 0; color: #718096;">Reason Humano</h4>
            <p style="margin: 0; font-size: 0.9rem; color: #4a5568;">
                {reason if pd.notna(reason) else "N/A"}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Flags de agravantes ─────────────────────────────────────────────────────
st.markdown("### 🚨 Flags de Agravantes")

col_flags1, col_flags2 = st.columns(2)

with col_flags1:
    hot_po = po_data.get(COL_HOT_PO_FLAG, 0)
    if hot_po:
        st.warning("🔥 **HOT PO** — Prioridad máxima")
    else:
        st.info("✅ PO estándar")

with col_flags2:
    short_ship = po_data.get(COL_IS_SHORT_SHIP, False)
    if short_ship:
        st.warning(" **Short Shipment** — Envío incompleto")
    else:
        st.info("✅ Envío completo")

# ── Timeline del lifecycle ──────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 📅 Timeline del Lifecycle")

# Lista de eventos del timeline
timeline_events = [
    ("PO_DT", "📝", "PO Creada"),
    ("STA_DT", "📦", "STA"),
    ("APPROVED_DT", "✅", "Cita Aprobada"),
    ("TRAILER_ARRIVE_DT", "🚛", "Tráiler Llega"),
    ("CHECKIN_DT", "📥", "Check-in"),
    ("CHECKOUT_DT", "📤", "Check-out"),
    ("RECPT_DT", "📦", "Recepción"),
]

# Crear columnas horizontales (una por evento)
cols = st.columns(len(timeline_events))

for i, (col_name, icon, label) in enumerate(timeline_events):
    with cols[i]:
        timestamp = po_data.get(col_name, None)
        
        if pd.notna(timestamp):
            time_str = timestamp.strftime("%Y-%m-%d %H:%M")
            st.success(f"{icon}")
            st.caption(f"**{label}**")
            st.caption(time_str)
        else:
            st.write(f"⚪")
            st.caption(f"**{label}**")
            st.caption("N/A")
        
        # Línea conectora (excepto en el último)
        if i < len(timeline_events) - 1:
            st.markdown("→")

# ── Diagnóstico LLM ─────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🤖 Diagnóstico de Inteligencia Artificial")

col_llm1, col_llm2 = st.columns(2)

with col_llm1:
    explanation = po_data.get(COL_EXPLANATION, "N/A")
    st.markdown(
        f"""
        <div class="custom-card" style="border-left: 4px solid #4299e1;">
            <h4 style="margin: 0 0 0.75rem 0; color: #2d3748;">🔍 Causa Raíz</h4>
            <p style="margin: 0; color: #4a5568; line-height: 1.6;">
                {explanation if pd.notna(explanation) else "N/A"}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_llm2:
    action = po_data.get(COL_ACTION, "N/A")
    st.markdown(
        f"""
        <div class="custom-card" style="border-left: 4px solid #48bb78;">
            <h4 style="margin: 0 0 0.75rem 0; color: #2d3748;">🛠️ Acción Recomendada</h4>
            <p style="margin: 0; color: #4a5568; line-height: 1.6;">
                {action if pd.notna(action) else "N/A"}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Footer ──────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
    <div class="simple-footer">
        <p>Exception Workbench · Vista de Diego (Inbound Exception Coordinator)</p>
        <p>Consulta individual de POs tardíos con evidencia completa</p>
    </div>
    """,
    unsafe_allow_html=True,
)