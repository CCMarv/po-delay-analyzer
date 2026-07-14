"""Network Intelligence — Vista de Ravi (Supply-Chain Analyst).

Reporte agregado de la población de POs tardíos: distribución por etapa y
severidad, tasa de desacuerdo como métrica de primera clase, tendencia temporal
y scorecards por entidad (Vendor/Carrier/DC). Drill-down master-detail Ravi→Diego
por PO_NBR. Reconstruida sobre el sistema de diseño (ARD-17); reemplaza la versión
con px.pie del ticket #103. Cierra #164.
"""
import json
from pathlib import Path

import streamlit as st
import pandas as pd
import plotly.express as px

from config import (
    SCORECARDS_DIR,
    COL_PO, COL_STAGE, COL_SEVERITY, COL_PO_DT, COL_LLM_COINCIDE,
    stage_colors, severity_colors, plot_theme,
)
from services.data_service import load_po_output
from components.navbar import render_navbar
from components.metrics_cards import metric_card

# ── Configuración de página ─────────────────────────────────────────────────
st.set_page_config(
    page_title="Network Intelligence",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

render_navbar(active_page="ravi")

# ── Cargar CSS del sistema de diseño ────────────────────────────────────────
css_file = Path(__file__).parent.parent / "assets" / "styles.css"
if css_file.exists():
    with open(css_file, encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


# ── Helpers de presentación ─────────────────────────────────────────────────
# El scorecard usa las clases ordinales del sistema (.badge-severity--*), que son
# la rampa acromática de luminancia. El riesgo es ordinal y NO compite por hue con
# los colores de etapa (regla del sistema de diseño), por eso reusa esa rampa.
_RISK_ORDINAL = {"Alto": ("high", "■"), "Medio": ("medium", "◆"), "Bajo": ("low", "●")}


def risk_badge_html(nivel: str) -> str:
    """Badge acromático para el Nivel de Riesgo (Alto/Medio/Bajo)."""
    key, icon = _RISK_ORDINAL.get(nivel, ("medium", "◆"))
    label = nivel if nivel else "Sin datos"
    return (
        f'<span class="badge-severity badge-severity--{key}">'
        f'<span class="badge-severity__icon">{icon}</span>{label}</span>'
    )


def _mini(label: str, value: str) -> str:
    """Indicador compacto (label + valor) con tokens del sistema (theme-aware)."""
    return (
        '<div style="min-width:96px;">'
        f'<div style="color:var(--text-muted); font-size:0.72rem; text-transform:uppercase;'
        f' letter-spacing:0.02em; font-weight:600; margin-bottom:2px;">{label}</div>'
        f'<div style="color:var(--text-primary); font-size:1.15rem; font-weight:700;">{value}</div>'
        "</div>"
    )


def _scorecard_html(name: str, rec: dict, hue: str) -> str:
    """Tarjeta de una entidad: nombre + badge de riesgo + indicadores descriptivos."""
    minis = "".join([
        _mini("POs (total)", f"{rec.get('n_POs_total', 0)}"),
        _mini("Retraso prom. (d)", f"{rec.get('Delay_Prom_sin_shrink', 0.0):.1f}"),
        _mini("Exceso/PO (h)", f"{rec.get('Excess_por_PO_sin_shrink', 0.0):.1f}"),
        _mini("Tasa reschedule", f"{rec.get('Tasa_Reschedule', 0.0):.1f}%"),
        _mini("Score riesgo", f"{rec.get('Score_Riesgo_Normalizado', 0.0):.0f} / 100"),
    ])
    return (
        f'<div class="custom-card" style="border-left:4px solid {hue};">'
        '<div style="display:flex; align-items:center; justify-content:space-between;'
        ' gap:0.5rem; flex-wrap:wrap;">'
        f'<span class="identifier" style="font-size:1.05rem;">{name}</span>'
        f'{risk_badge_html(rec.get("Nivel_Riesgo", "Sin datos"))}'
        "</div>"
        f'<div style="display:flex; gap:1.5rem; flex-wrap:wrap; margin-top:0.75rem;">{minis}</div>'
        "</div>"
    )


def load_scorecards() -> dict | None:
    """Lee los 3 JSON del motor offline. None si falta alguno (no crash)."""
    actors = ("vendors", "carriers", "dcs")
    result = {}
    for actor_key in actors:
        path = SCORECARDS_DIR / f"reporte_{actor_key}.json"
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            result[actor_key] = json.load(f).get(actor_key, {})
    return result


def h_bar(data, value_col, cat_col, color_map, text_col, category_order=None):
    """Barra horizontal del sistema: color categórico + etiquetado directo, sin leyenda."""
    fig = px.bar(
        data, x=value_col, y=cat_col, orientation="h",
        color=cat_col, color_discrete_map=color_map, text=text_col,
    )
    fig.update_traces(
        textposition="outside", cliponaxis=False,
        textfont_color=_PLOT_THEME["font_color"],
    )
    fig.update_layout(
        showlegend=False, height=max(180, 60 * len(data) + 80),
        margin=dict(l=10, r=48, t=10, b=10),
        xaxis_title=None, yaxis_title=None,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color=_PLOT_THEME["font_color"],
    )
    fig.update_xaxes(showgrid=False, showticklabels=False)
    if category_order:
        fig.update_yaxes(categoryorder="array", categoryarray=category_order)
    else:
        fig.update_yaxes(categoryorder="total ascending")
    return fig


# ── Carga de datos ──────────────────────────────────────────────────────────
df = load_po_output()

# Paleta y tokens de Plotly resueltos una sola vez al tema activo (ARD-17):
# Plotly no puede leer variables CSS, así que el hex se resuelve aquí en vez
# de en styles.css. _STAGE_COLORS/_SEVERITY reemplazan a STAGE_COLORS/SEVERITY
# solo dentro de esta página (las claras siguen siendo la fuente para
# badges.py/timeline.py, que resuelven color vía CSS var).
_STAGE_COLORS = stage_colors()
_SEVERITY = severity_colors()
_PLOT_THEME = plot_theme()

# Mapa de color por etapa: los valores del CSV vienen en Title case
# ('Vendor'/'Carrier'/'DC'/'Indeterminado'); las claves de STAGE_COLORS son
# minúsculas. Se resuelve por .lower() con fallback a Indeterminado.
STAGE_COLOR_MAP = {
    s: _STAGE_COLORS.get(str(s).lower(), _STAGE_COLORS["indeterminado"])
    for s in df[COL_STAGE].dropna().unique()
}
SEV_COLOR_MAP = {k: v["color"] for k, v in _SEVERITY.items()}
SEV_ORDER_BOTTOM_UP = ["LOW", "MEDIUM", "HIGH"]  # HIGH arriba en barra horizontal

# ── Header ──────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="page-header">
        <h1>📊 Network Intelligence</h1>
        <p>Reporte agregado — Patrones sistémicos en la población de POs tardíos (Vista de Ravi)</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Sección 1: KPIs ─────────────────────────────────────────────────────────
total_pos = len(df)
stage_counts = df[COL_STAGE].value_counts()
severity_counts = df[COL_SEVERITY].value_counts()

n_high = int(severity_counts.get("HIGH", 0))
n_disagree = int((df[COL_LLM_COINCIDE] == False).sum())  # noqa: E712 (bool col)
disagree_rate = (n_disagree / total_pos * 100) if total_pos else 0.0
top_stage = stage_counts.index[0]
top_stage_pct = stage_counts.iloc[0] / total_pos * 100 if total_pos else 0.0

col1, col2, col3, col4 = st.columns(4)
with col1:
    metric_card("POs Tardíos", f"{total_pos}", icon="📦")
with col2:
    metric_card("Etapa Dominante", f"{top_stage} ({top_stage_pct:.0f}%)", icon="🎯")
with col3:
    metric_card("Severidad Alta", f"{n_high} ({n_high / total_pos * 100:.0f}%)", icon="🚨")
with col4:
    metric_card("Tasa de Desacuerdo", f"{disagree_rate:.1f}%", icon="⚠️")

st.caption(
    f"Denominador: los {total_pos} POs tardíos del contrato F3→F4 "
    "(delay_days_calc > 0). Las cifras describen la población tardía, no la red completa."
)

# ── Sección 2: Distribución por etapa y por severidad ───────────────────────
st.markdown("---")
st.markdown("### Distribución por Etapa y Severidad")

col_stage, col_sev = st.columns(2)

with col_stage:
    st.markdown("**Por etapa** (color = etapa responsable)")
    stage_df = stage_counts.reset_index()
    stage_df.columns = [COL_STAGE, "count"]
    stage_df["label"] = stage_df["count"].astype(str)
    st.plotly_chart(
        h_bar(stage_df, "count", COL_STAGE, STAGE_COLOR_MAP, "label"),
        width="stretch",
    )

with col_sev:
    st.markdown("**Por severidad** (rampa ordinal, HIGH → LOW)")
    sev_df = severity_counts.reset_index()
    sev_df.columns = [COL_SEVERITY, "count"]
    sev_df["label"] = sev_df["count"].astype(str)
    st.plotly_chart(
        h_bar(sev_df, "count", COL_SEVERITY, SEV_COLOR_MAP, "label",
              category_order=SEV_ORDER_BOTTOM_UP),
        width="stretch",
    )

# ── Sección 3: Tasa de desacuerdo (métrica de primera clase) ────────────────
st.markdown("---")
st.markdown("### Tasa de Desacuerdo AI vs Humano")
st.caption(
    "Comparación del diagnóstico del LLM contra el REASON_DSC humano. Mapea al "
    "umbral *Reason Code Agreement* del mentor: un desacuerdo alto en una etapa "
    "señala dónde el reason humano es menos confiable, no un error del modelo."
)

dis_df = (
    df.assign(_disagree=(df[COL_LLM_COINCIDE] == False))  # noqa: E712
    .groupby(COL_STAGE)["_disagree"].mean().mul(100).reset_index()
)
dis_df.columns = [COL_STAGE, "rate"]
dis_df["label"] = dis_df["rate"].map(lambda v: f"{v:.0f}%")

col_dis1, col_dis2 = st.columns([2, 1])
with col_dis1:
    st.markdown("**% de desacuerdo por etapa**")
    st.plotly_chart(
        h_bar(dis_df, "rate", COL_STAGE, STAGE_COLOR_MAP, "label"),
        width="stretch",
    )
with col_dis2:
    st.markdown("**Global**")
    metric_card("Desacuerdos", f"{n_disagree} de {total_pos}", icon="⚠️")
    metric_card("Tasa", f"{disagree_rate:.1f}%")

# ── Sección 4: Tendencia temporal ───────────────────────────────────────────
st.markdown("---")
st.markdown("### Tendencia Temporal (POs tardíos por semana)")

trend = df.dropna(subset=[COL_PO_DT]).copy()
if trend.empty:
    st.info("Sin fechas de PO válidas para construir la tendencia.")
else:
    trend["week"] = trend[COL_PO_DT].dt.to_period("W").dt.start_time
    weekly = trend.groupby("week").size().reset_index(name="count").sort_values("week")
    fig_trend = px.line(weekly, x="week", y="count", markers=True)
    fig_trend.update_traces(
        line_color=_PLOT_THEME["line_color"], marker_color=_PLOT_THEME["line_color"],
    )
    fig_trend.update_layout(
        height=320, margin=dict(l=10, r=40, t=10, b=10),
        xaxis_title=None, yaxis_title="POs tardíos",
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font_color=_PLOT_THEME["font_color"],
    )
    fig_trend.update_xaxes(gridcolor=_PLOT_THEME["gridcolor"])
    fig_trend.update_yaxes(gridcolor=_PLOT_THEME["gridcolor"])
    last = weekly.iloc[-1]
    fig_trend.add_annotation(
        x=last["week"], y=last["count"], text=str(int(last["count"])),
        showarrow=False, yshift=14,
        font=dict(size=13, weight="bold", color=_PLOT_THEME["font_color"]),
    )
    st.plotly_chart(fig_trend, width="stretch")

# ── Sección 5: Scorecards por entidad ───────────────────────────────────────
st.markdown("---")
st.markdown("### Scorecards por Entidad")

scorecards = load_scorecards()
if scorecards is None:
    st.info(
        "Scorecards no encontrados. Genéralos (offline, sin API) desde la raíz del "
        "repo:\n\n"
        "```\npython 03_llm_integration/scorecard_core.py "
        "data/processed/df_classified.csv data/processed/scorecards\n```"
    )
else:
    _NOTE = (
        "El Nivel de Riesgo y el Score (0–100) son un compuesto estadístico "
        "(shrinkage empírico-Bayes + regresión Ridge + cortes GMM): expresan un "
        "ranking relativo dentro del grupo, no una probabilidad. Los demás "
        "indicadores son descriptivos directos. POs (total) cuenta toda la "
        "población de la entidad, no solo los tardíos."
    )
    tabs = st.tabs(["Vendors", "Carriers", "DCs"])
    for tab, actor_key, stage_key in zip(tabs, ("vendors", "carriers", "dcs"),
                                         ("vendor", "carrier", "dc")):
        with tab:
            entities = scorecards.get(actor_key, {})
            if not entities:
                st.info("Sin entidades en este scorecard.")
                continue
            st.caption(_NOTE)
            hue = _STAGE_COLORS[stage_key]
            ordered = sorted(
                entities.items(),
                key=lambda kv: kv[1].get("Score_Riesgo_Normalizado", 0),
                reverse=True,
            )
            for name, rec in ordered:
                st.markdown(_scorecard_html(name, rec, hue), unsafe_allow_html=True)

# ── Drill-down Ravi → Diego ─────────────────────────────────────────────────
st.markdown("---")
st.markdown("### Ver detalle de un PO (Exception Workbench)")

only_disagree = st.checkbox("Solo POs con desacuerdo AI vs humano", value=False)
pool = df[df[COL_LLM_COINCIDE] == False] if only_disagree else df  # noqa: E712
po_options = sorted(pool[COL_PO].unique().tolist())

if not po_options:
    st.info("No hay POs que cumplan el filtro seleccionado.")
else:
    col_dd1, col_dd2 = st.columns([3, 1])
    with col_dd1:
        dd_po = st.selectbox(
            "PO_NBR", options=po_options,
            format_func=lambda x: f"PO #{x}", key="ravi_drill_select",
        )
    with col_dd2:
        st.markdown("<div style='height:1.75rem;'></div>", unsafe_allow_html=True)
        if st.button("Ver en Exception Workbench →", width="stretch"):
            st.session_state["drilldown_po"] = dd_po
            st.switch_page("pages/1_🔍_Exception_Workbench.py")

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
