"""Exception Workbench — Vista de Diego (Inbound Exception Coordinator).

Consulta individual de un PO tardío con timeline, diagnóstico LLM y validación.
"""
from pathlib import Path
import streamlit as st
import pandas as pd
from config import (
    COL_STAGE, COL_SEVERITY,
    COL_PO_DT, COL_STA_DT, COL_APPROVED_DT, COL_TRAILER_ARRIVE_DT,
    COL_CHECKIN_DT, COL_CHECKOUT_DT, COL_RECPT_DT,
    COL_HOT_PO_FLAG, COL_IS_SHORT_SHIP, COL_REASON_DSC, COL_LLM_COINCIDE,
    COL_LLM_CONFIANZA, COL_VENDOR_NAME, COL_CARRIER_NAME, COL_DC_NAME,
    COL_DELAY_DAYS, STAGE_SEGMENT_COLUMNS,
    COL_LLM_RAZONAMIENTO, COL_LLM_HIPOTESIS, COL_LLM_HIPOTESIS_EVIDENCIA,
    COL_LLM_ACCION_INMEDIATA, COL_LLM_ACCION_CORRECTIVA, COL_LLM_ACCION_PREVENTIVA,
    COL_LLM_HIPOTESIS_ALT, COL_LLM_PASO_DISCRIMINANTE, COL_LLM_CONFIANZA_HIPOTESIS,
)
from services.data_service import load_po_output, get_po_by_number, get_unique_po_list
from components.navbar import render_navbar
from components.badges import stage_badge_html, severity_badge_html, confidence_badge_html
from components.timeline import timeline_segment_html
from components.metrics_cards import metric_card

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
    with open(css_file, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# ── Carga de datos ──────────────────────────────────────────────────────────
df = load_po_output()

# ── Header ──────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-header">
        <h1>🔍 Exception Workbench</h1>
        <p>Consulta individual de POs tardíos — Timeline + Diagnóstico + Validación</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Selector de PO ──────────────────────────────────────────────────────────
st.markdown("### Seleccionar PO")

po_list = get_unique_po_list(df)

# Drill-down desde la vista de Ravi: si llega un PO por session_state, se
# preselecciona. Se consume con .pop para no fijar la selección en recargas
# posteriores (una navegación manual vuelve a mandar).
drilldown_po = st.session_state.pop("drilldown_po", None)
default_index = po_list.index(drilldown_po) if drilldown_po in po_list else 0

selected_po = st.selectbox(
    "Número de PO:",
    options=po_list,
    format_func=lambda x: f"PO #{x}",
    index=default_index,
)

# Obtener datos del PO seleccionado
po_data = get_po_by_number(df, selected_po)

stage = po_data[COL_STAGE]
severity = po_data[COL_SEVERITY]
tiene_analisis_llm = pd.notna(severity)

stage_key = stage.lower() if pd.notna(stage) else "indeterminado"
highlighted_cols = STAGE_SEGMENT_COLUMNS.get(stage_key, ())

# ── Contexto rápido del PO ──────────────────────────────────────────────────
col_ctx1, col_ctx2, col_ctx3, col_ctx4 = st.columns(4)
with col_ctx1:
    delay_days = po_data.get(COL_DELAY_DAYS)
    metric_card("Retraso", f"{delay_days:.1f} d" if pd.notna(delay_days) else "N/A", icon="⏱️")
with col_ctx2:
    metric_card("Vendor", po_data.get(COL_VENDOR_NAME, "N/A"), icon="🏭")
with col_ctx3:
    metric_card("Carrier", po_data.get(COL_CARRIER_NAME, "N/A"), icon="🚚")
with col_ctx4:
    metric_card("DC", po_data.get(COL_DC_NAME, "N/A"), icon="🏬")

# ── Panel de diagnóstico ─────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### Diagnóstico del PO")

col_diag1, col_diag2, col_diag3, col_diag4, col_diag5 = st.columns(5)

# Etapa
with col_diag1:
    st.markdown(
        f"""
        <div class="custom-card">
            <h4 style="margin: 0 0 0.5rem 0; color: var(--text-muted);">Etapa</h4>
            {stage_badge_html(stage if pd.notna(stage) else None)}
        </div>
        """,
        unsafe_allow_html=True,
    )

# Severidad
with col_diag2:
    if tiene_analisis_llm:
        cuerpo_severidad = severity_badge_html(severity)
    else:
        cuerpo_severidad = '<p style="margin: 0; color: var(--text-muted); font-size: 0.9rem;">Pendiente de análisis LLM</p>'
    st.markdown(
        f"""
        <div class="custom-card">
            <h4 style="margin: 0 0 0.5rem 0; color: var(--text-muted);">Severidad</h4>
            {cuerpo_severidad}
        </div>
        """,
        unsafe_allow_html=True,
    )

# Confianza
with col_diag3:
    if tiene_analisis_llm:
        cuerpo_confianza = confidence_badge_html(po_data[COL_LLM_CONFIANZA])
    else:
        cuerpo_confianza = '<p style="margin: 0; color: var(--text-muted); font-size: 0.9rem;">Pendiente de análisis LLM</p>'
    st.markdown(
        f"""
        <div class="custom-card">
            <h4 style="margin: 0 0 0.5rem 0; color: var(--text-muted);">Confianza LLM</h4>
            {cuerpo_confianza}
        </div>
        """,
        unsafe_allow_html=True,
    )

# Flag de concordancia (PROMINENTE)
with col_diag4:
    if tiene_analisis_llm:
        coincide = po_data[COL_LLM_COINCIDE]
        if coincide:
            icon, text, color_var = "✅", "Consistente", "var(--ordinal-high)"
        else:
            icon, text, color_var = "⚠️", "Desacuerdo", "var(--ordinal-low)"
        cuerpo_concordancia = (
            f'<p style="margin: 0; font-size: 1.5rem; font-weight: 700; color: {color_var};">'
            f"{icon} {text}</p>"
        )
    else:
        cuerpo_concordancia = '<p style="margin: 0; color: var(--text-muted); font-size: 0.9rem;">Pendiente de análisis LLM</p>'
    st.markdown(
        f"""
        <div class="custom-card" style="min-height: 120px; display: flex; flex-direction: column; justify-content: center;">
            <h4 style="margin: 0 0 0.75rem 0; color: var(--text-muted); font-size: 1rem; font-weight: 600;">
                Validación AI vs Humano
            </h4>
            {cuerpo_concordancia}
        </div>
        """,
        unsafe_allow_html=True,
    )

# Reason humano
with col_diag5:
    reason = po_data.get(COL_REASON_DSC, "N/A")
    st.markdown(
        f"""
        <div class="custom-card">
            <h4 style="margin: 0 0 0.5rem 0; color: var(--text-muted);">Reason Humano</h4>
            <p style="margin: 0; font-size: 0.9rem; color: var(--text-secondary);">
                {reason if pd.notna(reason) else "N/A"}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Flags de agravantes ─────────────────────────────────────────────────────
st.markdown("### Flags de Agravantes")

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
        st.warning("📦 **Short Shipment** — Envío incompleto")
    else:
        st.info("✅ Envío completo")

# ── Timeline del lifecycle ──────────────────────────────────────────────────
st.markdown("---")
st.markdown("### Timeline del Lifecycle")

timeline_events = [
    (COL_PO_DT, "📝", "PO Creada"),
    (COL_STA_DT, "📦", "STA"),
    (COL_APPROVED_DT, "✅", "Cita Aprobada"),
    (COL_TRAILER_ARRIVE_DT, "🚛", "Tráiler Llega"),
    (COL_CHECKIN_DT, "📥", "Check-in"),
    (COL_CHECKOUT_DT, "📤", "Check-out"),
    (COL_RECPT_DT, "📦", "Recepción"),
]

segments_html = []
for col_name, icon, label in timeline_events:
    timestamp = po_data.get(col_name)
    time_str = timestamp.strftime("%Y-%m-%d %H:%M") if pd.notna(timestamp) else "N/A"
    segments_html.append(
        timeline_segment_html(
            label=f"{icon} {label}",
            timestamp=time_str,
            stage=stage_key,
            highlighted=col_name in highlighted_cols,
        )
    )

st.markdown("".join(segments_html), unsafe_allow_html=True)

# ── Diagnóstico diferencial (tier 2) ─────────────────────────────────────────
# Consume la salida híbrida de ARD-16 persistida en el contrato F3→F4 (#161): la
# hipótesis principal y su evidencia, una alternativa con el paso que las
# discrimina, un plan escalonado y una 2ª confianza específica de la hipótesis.
# El HTML se compone por concatenación (sin sangría inicial) al estilo de la vista
# de Ravi; reusa los tokens del sistema de diseño (ARD-17), nunca hex suelto.
st.markdown("---")
st.markdown("### Diagnóstico Diferencial")


def _t2(col: str) -> str:
    """Texto tier-2 seguro: valor limpio, o guion largo si viene vacío/NaN."""
    valor = po_data.get(col)
    return str(valor).strip() if pd.notna(valor) else "—"


def _microlabel(texto: str) -> str:
    """Etiqueta compacta en mayúsculas (mismo estilo que los mini de Ravi)."""
    return (
        '<div style="color:var(--text-muted); font-size:0.72rem; text-transform:uppercase;'
        f' letter-spacing:0.02em; font-weight:600; margin-bottom:2px;">{texto}</div>'
    )


hipotesis_val = po_data.get(COL_LLM_HIPOTESIS)
tiene_tier2 = (
    tiene_analisis_llm
    and pd.notna(hipotesis_val)
    and str(hipotesis_val).strip() not in ("", "—")
)

if tiene_tier2:
    stage_hue = f"var(--stage-{stage_key})"

    # 1) Hipótesis principal + 2ª confianza (bucket) + evidencia + razonamiento
    conf_hip = po_data.get(COL_LLM_CONFIANZA_HIPOTESIS)
    badge_conf = confidence_badge_html(float(conf_hip)) if pd.notna(conf_hip) else ""
    st.markdown(
        '<div class="custom-card">'
        '<div style="display:flex; align-items:center; justify-content:space-between;'
        ' gap:0.5rem; flex-wrap:wrap; margin-bottom:0.75rem;">'
        '<h4 style="margin:0; color:var(--text-primary); font-size:1.05rem;">'
        "Hipótesis principal</h4>"
        '<div style="display:flex; align-items:center; gap:0.4rem;">'
        + _microlabel("Confianza en la hipótesis").replace("margin-bottom:2px;", "")
        + badge_conf + "</div></div>"
        '<p style="margin:0 0 1rem 0; color:var(--text-primary); font-size:1.05rem;'
        f' font-weight:600; line-height:1.5;">{_t2(COL_LLM_HIPOTESIS)}</p>'
        + _microlabel("Evidencia")
        + '<p style="margin:0 0 1rem 0; color:var(--text-secondary); font-size:0.9rem;'
        f' line-height:1.6;">{_t2(COL_LLM_HIPOTESIS_EVIDENCIA)}</p>'
        + _microlabel("Razonamiento")
        + '<p style="margin:0 0 0.5rem 0; color:var(--text-secondary); font-size:0.9rem;'
        f' line-height:1.6;">{_t2(COL_LLM_RAZONAMIENTO)}</p>'
        '<p style="margin:0; color:var(--text-muted); font-size:0.78rem; line-height:1.5;'
        ' font-style:italic;">El razonamiento combina lectura de los datos de este PO con'
        ' generalizaciones de dominio del modelo (frases como &laquo;por regla de'
        ' industria&raquo; o &laquo;típicamente&raquo;). Estas últimas son conocimiento'
        " general del modelo, no evidencia de este caso concreto.</p>"
        "</div>",
        unsafe_allow_html=True,
    )

    # 2) Hipótesis alternativa + paso discriminante (callout elevado: el pivote
    #    accionable del diagnóstico diferencial, el dato a verificar).
    st.markdown(
        '<div class="custom-card">'
        + _microlabel("Hipótesis alternativa")
        + '<p style="margin:0 0 1rem 0; color:var(--text-secondary); font-size:0.95rem;'
        f' line-height:1.6;">{_t2(COL_LLM_HIPOTESIS_ALT)}</p>'
        '<div style="background:var(--surface-elevated); border-left:4px solid var(--accent);'
        ' border-radius:8px; padding:0.75rem 1rem;">'
        + _microlabel("Paso discriminante — el dato que decide entre ambas")
        + '<p style="margin:0; color:var(--text-primary); font-size:0.95rem;'
        f' line-height:1.6;">{_t2(COL_LLM_PASO_DISCRIMINANTE)}</p>'
        "</div></div>",
        unsafe_allow_html=True,
    )

    # 3) Plan escalonado: secuencia ordinal por horizonte temporal (ahora →
    #    corregir → prevenir). Acento de etapa = actor responsable (único uso de
    #    hue en el panel, mismo idiom que los segmentos del timeline).
    pasos = (
        ("1", "Inmediata", COL_LLM_ACCION_INMEDIATA),
        ("2", "Correctiva", COL_LLM_ACCION_CORRECTIVA),
        ("3", "Preventiva", COL_LLM_ACCION_PREVENTIVA),
    )
    pasos_html = "".join(
        '<div style="display:flex; align-items:flex-start; gap:0.75rem; padding:0.75rem 1rem;'
        f' border-left:4px solid {stage_hue}; background:var(--surface-card); border-radius:8px;'
        ' margin-bottom:0.5rem;">'
        '<span style="flex-shrink:0; color:var(--text-muted); font-family:var(--font-mono);'
        f' font-weight:700; font-size:1.1rem;">{num}</span><div style="flex:1;">'
        + _microlabel(f"Acción {label}")
        + '<p style="margin:0; color:var(--text-secondary); font-size:0.92rem;'
        f' line-height:1.6;">{_t2(col)}</p></div></div>'
        for num, label, col in pasos
    )
    st.markdown(
        '<div class="custom-card">'
        '<h4 style="margin:0 0 0.75rem 0; color:var(--text-primary); font-size:1.05rem;">'
        "Plan escalonado</h4>" + pasos_html + "</div>",
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <div class="llm-card">
            <div class="llm-icon">⏳</div>
            <h4>Pendiente de análisis LLM</h4>
            <p class="llm-text">Este PO todavía no tiene diagnóstico diferencial (hipótesis, evidencia, plan escalonado) generado por el análisis de Fase 3.</p>
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
